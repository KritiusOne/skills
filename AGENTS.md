# AGENTS.md

Instructions for AI agents working **in this repository**. This repo is the single
source of truth for a catalog of AI agent skills. There is no application code.

## What this repo is

A versioned directory of [Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills).
Each skill is a `SKILL.md` (frontmatter + operational guide) that travels with the clone.
Consuming projects sync skills from here; they do not keep diverging copies.

## Structure

```
skills/<name>/
├── SKILL.md          # required — YAML frontmatter + step-by-step guide
├── assets/           # optional — templates, schemas, examples
└── references/       # optional — local docs
```

`.agents/skills/` and `.claude/skills/` are **generated outputs** — gitignored, never
hand-edited. They are produced from `skills/` by the sync script.

## Conventions (non-negotiable)

- **Author** in frontmatter is `KritiusOne`. NEVER the skill-creator default `gentleman-programming`.
- **`name`** must equal the folder name and match `^[a-z0-9]+(-[a-z0-9]+)*$`.
- **`description`** is 1–1024 chars, with concrete triggers (keywords, file types, action verbs)
  AND an explicit "NOT for…" clause.
- **`allowed-tools`** is declared whenever the skill invokes a binary (least privilege),
  e.g. `allowed-tools: Bash(psql:*)`.
- **Resource declaration**: every skill declares the resources it touches (shell, network,
  secrets, files) — via `allowed-tools` and/or a `## Resources` section.
- **Naming**: generic skills use the technology name (`psql-cli`, `playwright-cli`).
- **Docs are bilingual**: `README.md` (English) + `README.es.md` (Spanish) stay in parity.

## Adding or changing a skill

1. Create/edit `skills/<name>/SKILL.md` following the conventions above.
2. Regenerate the agent-specific dirs:
   ```bash
   python scripts/sync_skills.py
   ```
3. Run the full validation gate locally — all four must exit 0:
   ```bash
   python scripts/validate_skills.py
   python scripts/security_lint.py
   python scripts/check_structure.py
   python scripts/sync_skills.py --check
   ```
4. Update the README tables (`README.md` + `README.es.md`) and `.github/CODEOWNERS`.
5. Open a PR. CI (`.github/workflows/validate-skills.yml`) re-runs the gate; the repo is
   **invalid if any check fails**.

## Validation gate (what CI enforces)

| Script | Enforces |
|--------|----------|
| `validate_skills.py` | Frontmatter parseable; `name`==folder + regex; `description` 1–1024 + triggers + "NOT for"; resource declaration |
| `security_lint.py` | No hidden-instruction HTML comments, `curl\|bash`, undeclared URLs/IPs, suspicious base64, invisible unicode, undeclared executables, or writes to agent identity files |
| `check_structure.py` | Folder↔`name` correspondence; `.gitignore` integrity; sync drift |
| `sync_skills.py --check` | Generated dirs match source (no drift) |

See `CONTRIBUTING.md` for the full add-a-skill workflow.

## Herramientas de AI custom

| Skill | Para qué |
|-------|----------|
| `psql-cli` | Usar el CLI de PostgreSQL de forma segura y no-interactiva (sin REPL, `ON_ERROR_STOP=1`, `PGPASSWORD`, output parseable, inspección de schema). |
