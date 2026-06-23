<!-- Language switcher -->
**English** · [Español](README.es.md)

# custom-skills

A personal repository of **AI agent skills**. Goal: turn the common problems the team hits during AI-assisted development into versioned, reusable, shareable knowledge — instead of each person solving it from scratch in their head or on their own machine.

This repo is the **single source of truth** for the skills. Projects that use them (e.g. the ERP) consume/sync from here; they do not keep their own diverging copy.

## Structure

This repo is dedicated to skills — there is no app — so skills live at the root under `skills/`, not nested under `.agents/`.

```
skills/<name>/
├── SKILL.md          # required — frontmatter + guide
├── assets/           # optional — templates, schemas, examples
└── references/       # optional — local docs
```

## Available skills

| Skill | What for | When to use | Owner |
|-------|----------|-------------|-------|
| `psql-cli` | Guide the agent to use the PostgreSQL CLI (`psql`) safely and non-interactively: never open the REPL (it hangs), `ON_ERROR_STOP=1`, `PGPASSWORD` instead of `-W`, parseable output, schema inspection | When the agent needs to run `psql`, query Postgres from the terminal, inspect schema, or script SQL | @KritiusOne |
| `obsidian-vault` | Manage notes in an Obsidian vault (plain-markdown folder): fixed structure (`knowledge/`, `tasks/`, `templates/`), task naming `<YYYYMMDDHHmm>-<slug>.md`, canonical frontmatter, `[[wiki]]`/`./relative.md` links, and a stdlib-only `new_task.py` helper — no plugin, fully offline | When creating, naming, or organizing notes/tasks in an Obsidian vault, writing task/knowledge frontmatter, wiring links, or bootstrapping a vault's templates/script | @KritiusOne |

## Installing a skill in your agent

The directories `.agents/skills/` and `.claude/skills/` are **generated outputs** — never hand-edit them.
After any change to `skills/`, regenerate them with:

```bash
python scripts/sync_skills.py
```

| Agent | Reads directory | Install command |
|-------|-----------------|-----------------|
| GitHub Copilot | `.agents/skills/` | `npx skills add KritiusOne/skills --skill psql-cli` |
| opencode | `.agents/skills/` | `gh skill install KritiusOne/skills psql-cli` |
| Claude Code | `.claude/skills/` | `gh skill install KritiusOne/skills psql-cli` |

> **Note — Claude Code reads `.claude/skills/`, NOT `.agents/skills/`.**
> The `gh skill install` command above copies the skill into `.claude/skills/` on your machine.
> If you are consuming this repo as a source clone, run `python scripts/sync_skills.py` once
> to populate both `.agents/skills/` and `.claude/skills/` locally.
>
> **Note — `npx skills add` flag shape:** the `--skill <name>` form is assumed based on the
> `skills` npm package documentation. If your version uses a positional argument
> (`npx skills add KritiusOne/skills psql-cli`), use that instead.

## Conventions

- **Location**: skills live in `skills/<name>/SKILL.md`, versioned (they travel with the clone). When consumed by a project that uses the `.agents/skills/` layout (e.g. the ERP), the sync step maps `skills/<name>/` → that project's `.agents/skills/<name>/`.
- **Author**: `KritiusOne` in the frontmatter. Do NOT use the skill-creator template default `gentleman-programming`.
- **allowed-tools**: declare in the frontmatter to pre-authorize binaries (e.g. `Bash(psql:*)`).
- **Naming**: generic skills use the technology name (`psql-cli`, `playwright-cli`).
