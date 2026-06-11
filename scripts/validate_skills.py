"""
validate_skills.py — Validate SKILL.md frontmatter fields.

Checks:
  V1  frontmatter block present and parseable
  V2  'name' key present and non-empty
  V3  'description' key present; string length 1..1024 (after resolving block scalar)
  V4  'name' == parent folder name (byte-exact)
  V5  'name' matches ^[a-z0-9]+(-[a-z0-9]+)*$
  +   R7  description contains at least one trigger indicator
  +   R8  description contains a "NOT for" clause
  +   R31 if skill ships executables (allowed-tools present), key must exist

Usage:
    python scripts/validate_skills.py [paths...]
    # Default: all skills/*/SKILL.md relative to repo root

Exit codes:
    0  all valid
    1  any failure
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Hand-rolled frontmatter parser
# ---------------------------------------------------------------------------
# Handles:
#   - key: scalar value (quoted or unquoted)
#   - key: > or key: |  (folded / literal block scalar, indented continuation)
#   - metadata:\n  sub-key: value  (one level of nested mapping)
#   - allowed-tools: value  (plain scalar or list item)
#   - # comments (ignored)
#   - blank lines
# Returns (dict, body_str, error_or_None)
# ---------------------------------------------------------------------------

_SCALAR_RE = re.compile(r'^([A-Za-z0-9_-]+)\s*:\s*(.*)$')
_BLOCK_SCALAR_RE = re.compile(r'^([A-Za-z0-9_-]+)\s*:\s*([>|])\s*$')
_NESTED_KEY_RE = re.compile(r'^\s{2,}([A-Za-z0-9_-]+)\s*:\s*(.*)$')
_LIST_ITEM_RE = re.compile(r'^\s*-\s+(.+)$')


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """
    Parse YAML-like frontmatter from a SKILL.md string.

    Returns:
        (frontmatter_dict, body_str, error_message_or_None)
    """
    lines = text.splitlines(keepends=False)
    if not lines or lines[0].strip() != '---':
        return {}, text, "frontmatter parse error: file does not begin with '---'"

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return {}, text, "frontmatter parse error: no closing '---' found"

    fm_lines = lines[1:end_idx]
    body = '\n'.join(lines[end_idx + 1:])
    result: Dict[str, Any] = {}
    error: Optional[str] = None

    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]

        # skip blank lines and comments
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            i += 1
            continue

        # block scalar: key: > or key: |
        bm = _BLOCK_SCALAR_RE.match(line)
        if bm:
            key = bm.group(1)
            style = bm.group(2)
            i += 1
            block_lines: List[str] = []
            # collect indented continuation lines
            while i < len(fm_lines):
                cont = fm_lines[i]
                if cont == '' or cont.startswith('  ') or cont.startswith('\t'):
                    block_lines.append(cont.strip())
                    i += 1
                else:
                    break
            # folded (>) joins with space, squashing blank lines into paragraphs
            if style == '>':
                parts: List[str] = []
                current: List[str] = []
                for bl in block_lines:
                    if bl == '':
                        if current:
                            parts.append(' '.join(current))
                            current = []
                        parts.append('')
                    else:
                        current.append(bl)
                if current:
                    parts.append(' '.join(current))
                value = '\n'.join(parts).strip()
            else:  # literal |
                value = '\n'.join(block_lines).rstrip()
            result[key] = value
            continue

        # nested mapping (indented key: value) — only if last key was a mapping key
        nm = _NESTED_KEY_RE.match(line)
        if nm and result:
            # belongs to the most recently inserted mapping key
            parent_key = list(result.keys())[-1]
            if not isinstance(result[parent_key], dict):
                # treat the parent as a mapping container
                result[parent_key] = {}
            sub_key = nm.group(1)
            sub_val = _strip_quotes(nm.group(2))
            result[parent_key][sub_key] = sub_val
            i += 1
            continue

        # list item
        lm = _LIST_ITEM_RE.match(line)
        if lm and result:
            parent_key = list(result.keys())[-1]
            if not isinstance(result[parent_key], list):
                result[parent_key] = []
            result[parent_key].append(lm.group(1).strip())
            i += 1
            continue

        # plain scalar: key: value
        sm = _SCALAR_RE.match(line)
        if sm:
            key = sm.group(1)
            val_raw = sm.group(2).strip()
            # check if this is the start of a nested mapping (value is empty → dict follows)
            if val_raw == '':
                result[key] = {}
            else:
                result[key] = _strip_quotes(val_raw)
            i += 1
            continue

        # unrecognised line
        error = f"frontmatter parse error: unsupported YAML construct on line: {line!r}"
        i += 1

    return result, body, error


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

# Trigger indicators: action verbs, file extensions, specific keyword patterns
_TRIGGER_WORDS = re.compile(
    r'\b(trigger|when|use when|activate|detect|run|execute|query|inspect|script|'
    r'guide|parse|lint|format|generate|build|test|deploy|sync|connect|'
    r'\.[a-z0-9]{1,6}|psql|bash|git|docker|kubectl|npm|yarn|pip)\b',
    re.IGNORECASE,
)

_NOT_FOR_RE = re.compile(r'NOT\s+for', re.IGNORECASE)


def resolve_description(fm: Dict[str, Any]) -> str:
    """Return description as a plain string regardless of how it was stored."""
    desc = fm.get('description', '')
    if isinstance(desc, str):
        return desc.strip()
    return str(desc).strip()


def validate_skill(path: Path) -> List[str]:
    """Run all checks on one SKILL.md. Returns list of 'path:rule_id: message' strings."""
    failures: List[str] = []

    try:
        text = path.read_text(encoding='utf-8')
    except OSError as e:
        return [f"{path}:V1: cannot read file: {e}"]

    fm, body, parse_error = parse_frontmatter(text)

    # V1 — frontmatter present and parseable
    if parse_error:
        failures.append(f"{path}:V1: {parse_error}")
        return failures  # cannot proceed with further checks

    # V2 — 'name' present
    name_val = fm.get('name', None)
    if not name_val:
        failures.append(f"{path}:V2: missing field: name")

    # V3 — 'description' present and length 1..1024
    desc = resolve_description(fm)
    if 'description' not in fm:
        failures.append(f"{path}:V3: missing field: description")
    elif len(desc) == 0:
        failures.append(f"{path}:V3: description is empty (length 0)")
    elif len(desc) > 1024:
        failures.append(f"{path}:V3: description too long ({len(desc)} chars, max 1024)")

    # V4 — name == parent folder
    folder_name = path.parent.name
    if name_val and name_val != folder_name:
        failures.append(
            f"{path}:V4: name mismatch — folder is '{folder_name}' but name is '{name_val}'"
        )

    # V5 — name matches regex
    if name_val and not _NAME_RE.match(name_val):
        failures.append(
            f"{path}:V5: name does not match required regex "
            f"'^[a-z0-9]+(-[a-z0-9]+)*$' — got '{name_val}'"
        )

    # R7 — description contains trigger indicator
    if desc and not _TRIGGER_WORDS.search(desc):
        failures.append(
            f"{path}:R7: description missing trigger indicators "
            f"(add a keyword, file extension, or action verb that tells the agent when to activate)"
        )

    # R8 — description contains "NOT for" clause
    if desc and not _NOT_FOR_RE.search(desc):
        failures.append(
            f"{path}:R8: description missing NOT-for clause "
            f"(add a sentence starting with 'NOT for' to define negative boundaries)"
        )

    # R31 — if skill body mentions executables, allowed-tools should be present
    # Check: if allowed-tools is explicitly set, it must be present (no over-broad check here)
    # The check is: if SKILL.md runs a binary (psql, bash, etc.) it must declare allowed-tools.
    # We detect "runs binary" by looking for bash code blocks in body or keywords.
    _EXEC_HINT = re.compile(
        r'```\s*bash|`[a-z]+\s+[^`]+`|\bpsql\b|\bsh\b|\bbash\b|\bpython\b|\bnpx\b|\bnpm\b',
        re.IGNORECASE
    )
    if _EXEC_HINT.search(body) and 'allowed-tools' not in fm:
        failures.append(
            f"{path}:R31: skill invokes system commands but 'allowed-tools' key is missing "
            f"from frontmatter (add 'allowed-tools: Bash(psql:*)' or equivalent)"
        )

    # R34 — every SKILL.md must declare the resources it touches.
    # Satisfied by EITHER:
    #   (a) an 'allowed-tools' key in frontmatter, OR
    #   (b) a section/line in the body explicitly listing resources
    #       (heading: "Resources", "Resources touched", "Resources used", etc.)
    # This is a pragmatic check: we look for either signal.
    _RESOURCES_RE = re.compile(
        r'(?im)^#{1,6}\s*resources?\b'          # ## Resources / # Resources touched
        r'|^resources?\s+(?:touched|used|accessed)\s*[:\-]'  # Resources touched:
        r'|^resources?\s*[:\-]',                 # Resources:
    )
    has_resources_decl = (
        'allowed-tools' in fm
        or bool(_RESOURCES_RE.search(body))
    )
    if not has_resources_decl:
        failures.append(
            f"{path}:R34: missing resources declaration — add EITHER an 'allowed-tools' "
            f"frontmatter field OR a '## Resources' section in the body listing files, "
            f"network, shell, and secrets this skill touches (use 'none' if it touches nothing)"
        )

    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def collect_paths(args: List[str]) -> List[Path]:
    if args:
        return [Path(p) for p in args]
    return sorted(REPO_ROOT.glob("skills/*/SKILL.md"))


def main() -> int:
    paths = collect_paths(sys.argv[1:])
    if not paths:
        print("validate_skills: no SKILL.md files found.")
        return 0

    total = len(paths)
    failed = 0
    for p in paths:
        issues = validate_skill(p)
        for msg in issues:
            print(msg)
        if issues:
            failed += 1

    print(f"{total} checked, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
