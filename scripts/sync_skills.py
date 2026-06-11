"""
sync_skills.py — Copy skills/*/  into .agents/skills/*/ and .claude/skills/*/
                 verbatim (byte-for-byte). Idempotent. Removes stale entries.

Usage:
    python scripts/sync_skills.py           # sync (mutate disk)
    python scripts/sync_skills.py --check   # report drift only (exit 2 if any)

Exit codes:
    0  in-sync / sync succeeded
    2  drift detected (--check mode only)
    1  unexpected IO error
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
TARGETS = [
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / ".claude" / "skills",
]

Action = str  # "copy" | "delete_file" | "delete_dir" | "mkdir"


def plan_sync(repo_root: Path) -> List[Tuple[Action, Path, Path | None]]:
    """
    Compute what sync WOULD do without touching the filesystem.

    Returns a list of (action, src_or_target_path, dst_path_or_None):
      ("copy",        src_file,  dst_file)   — dst missing or bytes differ
      ("delete_file", dst_file,  None)        — dst has no corresponding src
      ("delete_dir",  dst_dir,   None)        — stale skill dir in target
      ("mkdir",       dst_dir,   None)        — target skill dir must be created
    """
    skills_dir = repo_root / "skills"
    targets = [
        repo_root / ".agents" / "skills",
        repo_root / ".claude" / "skills",
    ]

    plan: List[Tuple[Action, Path, Path | None]] = []

    # Source skills: every subdir of skills/ that contains a SKILL.md
    source_skills: dict[str, Path] = {}
    if skills_dir.exists():
        for entry in sorted(skills_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                source_skills[entry.name] = entry

    for target_root in targets:
        # --- stale skill dirs in target that have no source ---
        if target_root.exists():
            for tentry in sorted(target_root.iterdir()):
                if tentry.is_dir() and tentry.name not in source_skills:
                    plan.append(("delete_dir", tentry, None))

        # --- for each source skill ---
        for skill_name, skill_src in source_skills.items():
            skill_dst = target_root / skill_name

            # collect all source files recursively
            src_files: list[Path] = sorted(
                f for f in skill_src.rglob("*") if f.is_file()
            )

            # ensure skill dir exists in target
            if not skill_dst.exists():
                plan.append(("mkdir", skill_dst, None))

            for src_file in src_files:
                rel = src_file.relative_to(skill_src)
                dst_file = skill_dst / rel

                # ensure parent dir
                if not dst_file.parent.exists():
                    plan.append(("mkdir", dst_file.parent, None))

                needs_copy = True
                if dst_file.exists():
                    if dst_file.read_bytes() == src_file.read_bytes():
                        needs_copy = False

                if needs_copy:
                    plan.append(("copy", src_file, dst_file))

            # stale files inside an existing skill dir
            if skill_dst.exists():
                for dst_file in sorted(skill_dst.rglob("*")):
                    if not dst_file.is_file():
                        continue
                    rel = dst_file.relative_to(skill_dst)
                    src_file = skill_src / rel
                    if not src_file.exists():
                        plan.append(("delete_file", dst_file, None))

    return plan


def sync(repo_root: Path) -> None:
    """Materialise the sync plan on disk."""
    plan = plan_sync(repo_root)

    for action, path_a, path_b in plan:
        if action == "mkdir":
            path_a.mkdir(parents=True, exist_ok=True)
        elif action == "copy":
            path_b.parent.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
            shutil.copy2(str(path_a), str(path_b))
            print(f"  copy  {path_a.relative_to(repo_root)}  ->  {path_b.relative_to(repo_root)}")  # type: ignore[union-attr]
        elif action == "delete_file":
            path_a.unlink()
            print(f"  del   {path_a.relative_to(repo_root)}")
        elif action == "delete_dir":
            shutil.rmtree(str(path_a))
            print(f"  rmdir {path_a.relative_to(repo_root)}")

    if not any(a in ("copy", "delete_file", "delete_dir") for a, _, _ in plan):
        print("sync_skills: already in sync, nothing to do.")


def check(repo_root: Path) -> int:
    """Report drift without mutating disk. Returns 0 (clean) or 2 (drift)."""
    plan = plan_sync(repo_root)
    drift = [item for item in plan if item[0] in ("copy", "delete_file", "delete_dir")]

    if not drift:
        print("sync_skills --check: OK (no drift)")
        return 0

    print(f"sync_skills --check: DRIFT detected ({len(drift)} item(s))")
    for action, path_a, path_b in drift:
        if action == "copy":
            print(f"  MISSING/CHANGED  {path_b}")  # type: ignore[union-attr]
        elif action == "delete_file":
            print(f"  STALE_FILE       {path_a}")
        elif action == "delete_dir":
            print(f"  STALE_DIR        {path_a}")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync skills/ into agent target dirs.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift only; exit 2 if any drift found. Does NOT mutate disk.",
    )
    args = parser.parse_args()

    try:
        if args.check:
            return check(REPO_ROOT)
        else:
            sync(REPO_ROOT)
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"sync_skills: unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
