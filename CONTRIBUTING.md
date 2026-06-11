# Contributing to custom-skills

## Adding a new skill

1. Create a folder under `skills/` using a lowercase hyphenated name:

   ```
   skills/<name>/
   └── SKILL.md   # required
   ```

   The folder name must match the `name` field in `SKILL.md` exactly (case-sensitive).

2. Write `SKILL.md` with the required frontmatter block:

   ```yaml
   ---
   name: <name>
   description: >
     One or two sentences describing what the skill does, when to activate it
     (trigger: keyword, file extension, or action verb), and a NOT for clause
     stating what it must NOT be used for.
   allowed-tools: Bash(<binary>:*)   # required if the skill invokes system commands
   license: MIT                       # or Apache-2.0, etc.
   metadata:
     author: <your-github-handle>
     version: "1.0"
   ---
   ```

   Required fields:
   - `name` — must equal the folder name, lowercase alphanumeric with hyphens, e.g. `psql-cli`
   - `description` — 1–1024 characters; must include a trigger indicator AND a "NOT for" clause
   - `allowed-tools` — required if the skill invokes any system binary or shell command

3. Run `scripts/sync_skills.py` to propagate your changes to the generated agent directories:

   ```bash
   python scripts/sync_skills.py
   ```

   **Never hand-edit `.agents/skills/` or `.claude/skills/`** — they are generated outputs.
   Changes made directly there will be overwritten on the next sync.

---

## Running the four checks locally

Before opening a PR, run all four checks from the repo root:

```bash
# 1. Sync (generate .agents/skills/ and .claude/skills/ from source)
python scripts/sync_skills.py

# 2. Validate frontmatter
python scripts/validate_skills.py

# 3. Security lint
python scripts/security_lint.py

# 4. Check structure and sync integrity
python scripts/check_structure.py
```

All four must exit 0. A PR is **not mergeable** if any of these CI steps fail.

---

## What CI checks and what must pass

The GitHub Actions workflow (`.github/workflows/validate-skills.yml`) runs on every PR
and every push to `main`. It runs these steps as **hard gates** (failure = red build):

1. `python scripts/sync_skills.py` — generates agent dirs on the runner
2. `python scripts/validate_skills.py` — frontmatter validity, name/folder match, description rules
3. `python scripts/security_lint.py` — HTML-comment injection, download-exec patterns, undeclared URLs, suspicious base64, invisible unicode, undeclared executables
4. `python scripts/check_structure.py` — folder↔name integrity, `.gitignore` entries, sync drift, orphan dirs

A fifth step (`gh skill publish --dry-run`) runs best-effort (`continue-on-error: true`)
because the `gh skill` extension may not be available on all runners. It does NOT block merge
if the extension is unavailable, but DOES block if the extension is present and the dry-run fails.

---

## Advisory notes (not yet automated)

### R13 — Dependency pinning

If you add a helper script inside a skill folder that installs or downloads packages,
pin every dependency to a specific version or hash. Example:

```
# good
pip install requests==2.31.0
# bad — range installs can pull malicious updates
pip install requests>=2
```

There is no automated enforcement of this rule in CI yet. It is your responsibility to follow it.

### R14 — Agent identity files

Skills MUST NOT write to agent identity files (`AGENTS.md`, `MEMORY.md`, `.claude/CLAUDE.md`,
or equivalent). If a skill's documented purpose IS managing agent memory or identity,
that purpose must be stated explicitly in the `description` field.

There is no automated enforcement of this rule in CI yet. Reviewers should flag any skill
that references writes to identity files without a clear justification.

---

## Governance

- `CODEOWNERS` (`.github/CODEOWNERS`) assigns a named owner to every skill folder.
- Any PR touching `skills/<name>/` requires approval from that skill's code owner before merge.
- The default owner for all files is `@KritiusOne`.
