"""
security_lint.py — Supply-chain security heuristics for skill files.

Heuristics:
  S1  HTML-comment instructions (prompt injection)
  S2  curl/wget pipe to shell (download-and-exec)
  S3  undeclared network references (URLs, IPs)
  S4  suspicious base64 blobs
  S5  invisible unicode characters
  S6  undeclared executable artifacts
  S7  advisory: skill ships executables but no allowed-tools declared (non-fatal)
  S8  writes to agent identity files (AGENTS.md, MEMORY.md, CLAUDE.md, .claude/) without
      an explicit declaration of purpose in SKILL.md

Usage:
    python scripts/security_lint.py [paths...]
    # Default: scan every file under skills/*/

Exit codes:
    0  clean
    1  any S1-S6/S8 finding
"""

from __future__ import annotations

import base64
import binascii
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_binary(data: bytes) -> bool:
    return b'\x00' in data


def _read_text_safe(path: Path) -> Tuple[str | None, bytes]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, b''
    if _is_binary(raw):
        return None, raw  # binary — None signals skip
    try:
        return raw.decode('utf-8', errors='replace'), raw
    except Exception:
        return None, raw


def _has_exec_bit(path: Path) -> bool:
    """True if path has any executable bit set (POSIX only; no-op on Windows)."""
    try:
        import stat
        mode = path.stat().st_mode
        return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Allowlist builder
# ---------------------------------------------------------------------------
# S3 policy:
#   - URLs/IPs in SKILL.md frontmatter are ALWAYS declared (they appear in
#     the metadata that the skill author explicitly wrote).
#   - URLs/IPs in SKILL.md BODY must also appear in the frontmatter (or be
#     well-known, unambiguous documentation hosts already present in the file)
#     to be considered declared.  A URL that only appears in the body but NOT
#     in the frontmatter is flagged as undeclared.
#   - Associated files (non-SKILL.md) are checked against the full allowlist
#     built from both frontmatter and body.
#
# This means a malicious URL added only to the body of SKILL.md will be
# flagged, while legitimate URLs that appear in frontmatter fields
# (e.g. homepage, repository) are allowed.

_URL_RE = re.compile(r'https?://([^\s)"\'<>]+)')
_IP_RE = re.compile(r'\b((?:\d{1,3}\.){3}\d{1,3})\b')

# Frontmatter delimiter helpers
_FM_START = re.compile(r'^---\s*$', re.MULTILINE)


def _split_frontmatter_body(skill_md_text: str):
    """Return (frontmatter_text, body_text) from a SKILL.md string."""
    lines = skill_md_text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return '', skill_md_text
    # Find the closing ---
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            fm = ''.join(lines[1:i])
            body = ''.join(lines[i + 1:])
            return fm, body
    # No closing --- found — treat whole file as body
    return '', skill_md_text


def _extract_hosts(text: str) -> Set[str]:
    hosts: Set[str] = set()
    for m in _URL_RE.finditer(text):
        raw = m.group(1).split('/')[0].split('?')[0].split('#')[0]
        hosts.add(raw.lower())
    return hosts


def _extract_ips(text: str) -> Set[str]:
    return {m.group(1) for m in _IP_RE.finditer(text)}


def _build_allowlist(skill_md_text: str) -> Set[str]:
    """
    Build the full allowlist for ASSOCIATED files (not SKILL.md body itself).
    Includes all hosts/IPs from both frontmatter and body, plus filenames.
    """
    allowed: Set[str] = set()
    fm_text, body_text = _split_frontmatter_body(skill_md_text)

    allowed.update(_extract_hosts(fm_text))
    allowed.update(_extract_hosts(body_text))
    allowed.update(_extract_ips(fm_text))
    allowed.update(_extract_ips(body_text))

    # Simple filenames/words (for S6 executable check)
    for m in re.finditer(r'\b[\w.-]+\.(?:sh|bash|ps1|py|exe|bin|bat|cmd|jar|wasm)\b', skill_md_text):
        allowed.add(m.group(0).lower())

    return allowed


def _build_body_allowlist(skill_md_text: str) -> Set[str]:
    """
    Build the allowlist for SKILL.md body URLs/IPs.
    Only frontmatter hosts/IPs are pre-declared; body URLs must match these
    to be considered declared.
    """
    fm_text, _ = _split_frontmatter_body(skill_md_text)
    allowed: Set[str] = set()
    allowed.update(_extract_hosts(fm_text))
    allowed.update(_extract_ips(fm_text))
    return allowed


# ---------------------------------------------------------------------------
# S1 — HTML-comment instructions
# ---------------------------------------------------------------------------
_HTML_COMMENT_RE = re.compile(r'<!--(.*?)-->', re.DOTALL)
_INSTRUCTION_SIGNAL = re.compile(
    r'(?i)\b(ignore|disregard|instead|run|execute|download|curl|bash|sudo|'
    r'exfiltrate|send|POST|GET|do\s+not\s+tell|override|system\s+prompt)\b'
)
_URL_SIGNAL = re.compile(r'https?://')


def check_s1(text: str, path: Path, findings: List[str]) -> None:
    for m in _HTML_COMMENT_RE.finditer(text):
        body = m.group(1)
        if _INSTRUCTION_SIGNAL.search(body) or _URL_SIGNAL.search(body):
            line_no = text[:m.start()].count('\n') + 1
            snippet = body.strip()[:80].replace('\n', ' ')
            findings.append(f"{path}:{line_no}: [S1] HTML-comment instruction detected: {snippet!r}")


# ---------------------------------------------------------------------------
# S2 — download-and-exec patterns
# ---------------------------------------------------------------------------
_CURL_PIPE_RE = re.compile(
    r'(?i)(curl|wget)\b[^\n|]*\|\s*(bash|sh|zsh|python\d*|node)\b'
)
_BASH_PROC_SUB_RE = re.compile(
    r'(?i)\b(bash|sh)\s+<\(\s*(curl|wget)'
)


def check_s2(text: str, path: Path, findings: List[str]) -> None:
    for pattern in (_CURL_PIPE_RE, _BASH_PROC_SUB_RE):
        for m in pattern.finditer(text):
            line_no = text[:m.start()].count('\n') + 1
            findings.append(
                f"{path}:{line_no}: [S2] forbidden download-execute pattern: {m.group(0)!r}"
            )


# ---------------------------------------------------------------------------
# S3 — undeclared network refs
# ---------------------------------------------------------------------------

def check_s3(text: str, path: Path, allowlist: Set[str], findings: List[str]) -> None:
    # URLs
    for m in _URL_RE.finditer(text):
        raw_host = m.group(1).split('/')[0].split('?')[0].split('#')[0].lower()
        if raw_host not in allowlist:
            line_no = text[:m.start()].count('\n') + 1
            findings.append(
                f"{path}:{line_no}: [S3] undeclared network ref — host '{raw_host}' "
                f"not declared in SKILL.md (add it to the skill's description or body)"
            )

    # Bare IPv4
    for m in _IP_RE.finditer(text):
        ip = m.group(1)
        if ip not in allowlist:
            line_no = text[:m.start()].count('\n') + 1
            findings.append(
                f"{path}:{line_no}: [S3] undeclared IP address '{ip}'"
            )


# ---------------------------------------------------------------------------
# S4 — suspicious base64 blobs
# ---------------------------------------------------------------------------
_B64_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{40,}={0,2})(?![A-Za-z0-9+/=])')
_HEX_ONLY_RE = re.compile(r'^[0-9a-fA-F]+$')
_S1S2_IN_DECODED = re.compile(
    r'(?i)(curl|wget|bash|sh|ignore|override|system\s+prompt|exfiltrate)'
)


def check_s4(text: str, path: Path, findings: List[str]) -> None:
    for m in _B64_TOKEN_RE.finditer(text):
        token = m.group(1)
        # Exempt pure hex
        if _HEX_ONLY_RE.match(token):
            continue
        # Attempt decode
        # Pad to multiple of 4
        padded = token + '=' * ((4 - len(token) % 4) % 4)
        try:
            decoded = base64.b64decode(padded)
        except (binascii.Error, ValueError):
            continue

        suspicious = False
        try:
            decoded_text = decoded.decode('utf-8', errors='replace')
            non_printable = sum(1 for c in decoded if c < 32 and c not in (9, 10, 13))
            ratio = non_printable / max(len(decoded), 1)
            if ratio > 0.30:
                suspicious = True
            elif _S1S2_IN_DECODED.search(decoded_text):
                suspicious = True
        except Exception:
            suspicious = True

        if suspicious:
            line_no = text[:m.start()].count('\n') + 1
            findings.append(
                f"{path}:{line_no}: [S4] possible hidden payload in base64 blob "
                f"(token length {len(token)}): {token[:20]}..."
            )


# ---------------------------------------------------------------------------
# S5 — invisible unicode
# ---------------------------------------------------------------------------
_INVISIBLE_RANGES = [
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x00AD, 0x00AD),
    (0x180E, 0x180E),
    (0xE0000, 0xE007F),
]
_FEFF = 0xFEFF


def check_s5(text: str, path: Path, findings: List[str]) -> None:
    lines = text.splitlines(keepends=True)
    for line_no, line in enumerate(lines, start=1):
        for col_no, ch in enumerate(line, start=1):
            cp = ord(ch)
            # Allow BOM only at very start of file (line 1, col 1)
            if cp == _FEFF and line_no == 1 and col_no == 1:
                continue
            invisible = cp == _FEFF  # non-BOM position
            if not invisible:
                for lo, hi in _INVISIBLE_RANGES:
                    if lo <= cp <= hi:
                        invisible = True
                        break
            if invisible:
                findings.append(
                    f"{path}:{line_no}: [S5] invisible unicode character U+{cp:04X} "
                    f"at column {col_no}"
                )


# ---------------------------------------------------------------------------
# S6 — undeclared executable artifact
# ---------------------------------------------------------------------------
_EXEC_EXTS = {'.sh', '.bash', '.ps1', '.py', '.exe', '.bin', '.bat', '.cmd', '.jar', '.wasm'}


def check_s6(
    skill_dir: Path, skill_md_text: str, allowlist: Set[str], findings: List[str]
) -> bool:
    """Returns True if any executable artifact was found (for S7)."""
    has_executable = False
    for f in skill_dir.rglob('*'):
        if not f.is_file():
            continue
        if f.name.lower() == 'skill.md':
            continue
        is_exec_ext = f.suffix.lower() in _EXEC_EXTS
        is_exec_bit = _has_exec_bit(f)
        if is_exec_ext or is_exec_bit:
            has_executable = True
            if f.name.lower() not in allowlist:
                findings.append(
                    f"{f}:1: [S6] undeclared executable artifact: {f.name!r} "
                    f"not mentioned in SKILL.md body (add justification)"
                )
    return has_executable


# ---------------------------------------------------------------------------
# S7 — advisory: executable but no allowed-tools
# ---------------------------------------------------------------------------

def check_s7(
    skill_md_path: Path, fm_text: str, has_executable: bool
) -> None:
    if has_executable and 'allowed-tools' not in fm_text:
        print(
            f"INFO [{skill_md_path}]: [S7] skill ships executable artifacts but "
            f"'allowed-tools' is not declared in frontmatter (advisory only)"
        )


# ---------------------------------------------------------------------------
# S8 — writes to agent identity files without explicit declaration
# ---------------------------------------------------------------------------
# Agent identity files that must NOT be written to unless the skill's purpose
# is explicitly managing agent memory/identity.
_IDENTITY_FILES = re.compile(
    r'\b(AGENTS\.md|MEMORY\.md|CLAUDE\.md|AGENT\.md|\.claude[/\\])\b'
)
# Patterns that indicate a WRITE operation (not a read reference)
_WRITE_OP_RE = re.compile(
    r'(?i)'
    # shell redirects: echo ... >> FILE or > FILE
    r'(?:>>?\s*["\']?(?:AGENTS\.md|MEMORY\.md|CLAUDE\.md|AGENT\.md|\.claude[/\\])'
    r'|'
    # tee/write calls
    r'(?:tee|write_file|open\s*\(["\'](?:AGENTS\.md|MEMORY\.md|CLAUDE\.md|AGENT\.md|\.claude[/\\]))["\']?\s*[,\)]?\s*["\']?w'
    r'|'
    # PowerShell: Set-Content, Add-Content, Out-File targeting identity files
    r'(?:Set-Content|Add-Content|Out-File)[^|&;\n]*(?:AGENTS\.md|MEMORY\.md|CLAUDE\.md|AGENT\.md|\.claude[/\\])'
    r')'
)
# Explicit exception: SKILL.md declares it manages agent memory/identity
_IDENTITY_PURPOSE_RE = re.compile(
    r'(?i)'
    r'(?:writes?\s+to\s+(?:AGENTS\.md|MEMORY\.md|CLAUDE\.md|AGENT\.md|\.claude)'
    r'|manages?\s+agent\s+(?:memory|identity)'
    r'|purpose\s*:\s*agent\s+(?:memory|identity)\s+manager)'
)


def check_s8(text: str, path: Path, findings: List[str]) -> None:
    """
    Flag write operations targeting agent identity files.
    Skipped if SKILL.md contains an explicit declaration of purpose.
    """
    # Read the SKILL.md of the containing skill to check for exception declaration
    skill_md = path if path.name.lower() == 'skill.md' else (path.parent / 'SKILL.md')
    skill_md_text = ''
    if skill_md.exists():
        try:
            skill_md_text = skill_md.read_text(encoding='utf-8', errors='replace')
        except OSError:
            pass

    # If SKILL.md declares identity management purpose, skip this check entirely
    if _IDENTITY_PURPOSE_RE.search(skill_md_text):
        return

    for m in _WRITE_OP_RE.finditer(text):
        line_no = text[:m.start()].count('\n') + 1
        snippet = m.group(0).strip()[:80].replace('\n', ' ')
        findings.append(
            f"{path}:{line_no}: [S8] unauthorized write to agent identity file: "
            f"{snippet!r} — add 'writes to AGENTS.md' (or equivalent) with justification "
            f"to SKILL.md if this is intentional"
        )


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_skill(skill_dir: Path) -> List[str]:
    """Scan one skill directory. Returns list of finding strings."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir}:1: [S6] missing SKILL.md in skill directory"]

    skill_md_text, _ = _read_text_safe(skill_md)
    if skill_md_text is None:
        return [f"{skill_md}:1: [S1] SKILL.md is binary — cannot scan"]

    # Full allowlist (frontmatter + body) for associated files
    allowlist = _build_allowlist(skill_md_text)
    # Body-only allowlist for SKILL.md S3 check:
    # frontmatter hosts are pre-declared; body URLs not in frontmatter are flagged
    body_allowlist = _build_body_allowlist(skill_md_text)

    findings: List[str] = []

    # Scan SKILL.md itself for S1, S2, S3 (body only), S4, S5, S8
    check_s1(skill_md_text, skill_md, findings)
    check_s2(skill_md_text, skill_md, findings)
    # S3 on SKILL.md body: URLs not declared in frontmatter are flagged.
    # We scan the body text against the frontmatter-only allowlist so that
    # a URL present only in the body (but not frontmatter) is caught.
    _, body_text = _split_frontmatter_body(skill_md_text)
    if body_text.strip():
        check_s3(body_text, skill_md, body_allowlist, findings)
    check_s4(skill_md_text, skill_md, findings)
    check_s5(skill_md_text, skill_md, findings)
    check_s8(skill_md_text, skill_md, findings)

    # Scan all other files in the skill dir
    for f in sorted(skill_dir.rglob('*')):
        if not f.is_file():
            continue
        if f.resolve() == skill_md.resolve():
            continue

        text, raw = _read_text_safe(f)
        if text is None:
            # binary file — skip text heuristics but S6 will catch it
            continue

        check_s1(text, f, findings)
        check_s2(text, f, findings)
        check_s3(text, f, allowlist, findings)
        check_s4(text, f, findings)
        check_s5(text, f, findings)
        check_s8(text, f, findings)

    # S6 — undeclared executables
    has_exec = check_s6(skill_dir, skill_md_text, allowlist, findings)

    # S7 — advisory
    check_s7(skill_md, skill_md_text, has_exec)

    return findings


def collect_skill_dirs(args: List[str]) -> List[Path]:
    if args:
        return [Path(a) if Path(a).is_dir() else Path(a).parent for a in args]
    return sorted(
        d for d in (REPO_ROOT / "skills").iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ) if (REPO_ROOT / "skills").exists() else []


def main() -> int:
    skill_dirs = collect_skill_dirs(sys.argv[1:])
    if not skill_dirs:
        print("security_lint: no skill directories found.")
        return 0

    all_findings: List[str] = []
    for skill_dir in skill_dirs:
        all_findings.extend(scan_skill(skill_dir))

    for finding in all_findings:
        print(finding)

    if all_findings:
        print(f"security_lint: {len(all_findings)} finding(s) — FAIL")
        return 1

    print("security_lint: OK (no findings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
