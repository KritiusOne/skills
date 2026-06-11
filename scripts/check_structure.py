"""
check_structure.py — Structural integrity checks for the custom-skills repo.

Checks:
  C1  folder↔name: every skills/<name>/SKILL.md has 'name' == <name>
  C2  gitignore integrity: .gitignore contains .agents/skills/ and .claude/skills/
  C3  sync-drift: generated dirs match source (via plan_sync from sync_skills)
  C4  no orphans: every dir under .agents/skills/ and .claude/skills/ has a source

Usage:
    python scripts/check_structure.py

Exit codes:
    0  all checks pass
    1  any violation
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path-safe import of sync_skills.plan_sync
# ---------------------------------------------------------------------------
import importlib.util
import os

_SCRIPTS_DIR = Path(__file__).parent
_SYNC_SKILLS_PATH = _SCRIPTS_DIR / "sync_skills.py"

spec = importlib.util.spec_from_file_location("sync_skills", _SYNC_SKILLS_PATH)
_sync_module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(_sync_module)  # type: ignore[union-attr]
plan_sync = _sync_module.plan_sync

# Also import the frontmatter parser from validate_skills for C1
_VALIDATE_PATH = _SCRIPTS_DIR / "validate_skills.py"
_vspec = importlib.util.spec_from_file_location("validate_skills", _VALIDATE_PATH)
_vmodule = importlib.util.module_from_spec(_vspec)  # type: ignore[arg-type]
_vspec.loader.exec_module(_vmodule)  # type: ignore[union-attr]
parse_frontmatter = _vmodule.parse_frontmatter

# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
TARGETS = [
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / ".claude" / "skills",
]
# ---------------------------------------------------------------------------


def check_c1() -> list[str]:
    """C1: every skills/<name>/SKILL.md has 'name' == <name>."""
    errors: list[str] = []
    if not SKILLS_SRC.exists():
        return errors
    for skill_md in sorted(SKILLS_SRC.glob("*/SKILL.md")):
        folder = skill_md.parent.name
        try:
            text = skill_md.read_text(encoding='utf-8')
        except OSError as e:
            errors.append(f"C1: cannot read {skill_md}: {e}")
            continue
        fm, _, parse_error = parse_frontmatter(text)
        if parse_error:
            errors.append(f"C1: {skill_md}: {parse_error}")
            continue
        name_val = fm.get('name', None)
        if not name_val:
            errors.append(f"C1: {skill_md}: 'name' field missing")
        elif name_val != folder:
            errors.append(
                f"C1: {skill_md}: folder is '{folder}' but name field is '{name_val}'"
            )
    return errors


def check_c2() -> list[str]:
    """C2: .gitignore contains .agents/skills/ and .claude/skills/ entries."""
    errors: list[str] = []
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        errors.append("C2: .gitignore does not exist")
        return errors
    content = gitignore.read_text(encoding='utf-8')
    for expected in [".agents/skills/", ".claude/skills/"]:
        if expected not in content:
            errors.append(
                f"C2: .gitignore is missing entry for '{expected}' — generated dirs must be gitignored"
            )
    return errors


def check_c3() -> list[str]:
    """C3: no sync drift — generated dirs match source."""
    errors: list[str] = []
    plan = plan_sync(REPO_ROOT)
    drift = [item for item in plan if item[0] in ("copy", "delete_file", "delete_dir")]
    for action, path_a, path_b in drift:
        if action == "copy":
            errors.append(f"C3: sync drift — {path_b} is missing or differs from source")
        elif action == "delete_file":
            errors.append(f"C3: sync drift — stale file in generated dir: {path_a}")
        elif action == "delete_dir":
            errors.append(f"C3: sync drift — stale dir in generated dir: {path_a}")
    return errors


def check_c4() -> list[str]:
    """C4: no orphan dirs in generated targets."""
    errors: list[str] = []
    source_names: set[str] = set()
    if SKILLS_SRC.exists():
        for d in SKILLS_SRC.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                source_names.add(d.name)

    for target in TARGETS:
        if not target.exists():
            continue
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and entry.name not in source_names:
                errors.append(
                    f"C4: orphan dir '{entry}' has no corresponding source in skills/"
                )
    return errors


def main() -> int:
    all_errors: list[str] = []

    c1 = check_c1()
    c2 = check_c2()
    c3 = check_c3()
    c4 = check_c4()

    all_errors.extend(c1)
    all_errors.extend(c2)
    all_errors.extend(c3)
    all_errors.extend(c4)

    if not all_errors:
        print("check_structure: OK (all checks pass)")
        return 0

    for err in all_errors:
        print(f"ERROR: {err}")
    print(f"check_structure: {len(all_errors)} violation(s) found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
