<!-- Language switcher -->
**English** · [Español](README.es.md)

# custom-skills

A personal repository of **AI agent skills**. Goal: turn the common problems the team hits during AI-assisted development into versioned, reusable, shareable knowledge — instead of each person solving it from scratch in their head or on their own machine.

This repo is the **single source of truth** for the skills. Projects that use them (e.g. the ERP) consume/sync from here; they do not keep their own diverging copy.

## Structure

```
.agents/skills/<name>/
├── SKILL.md          # required — frontmatter + guide
├── assets/           # optional — templates, schemas, examples
└── references/       # optional — local docs
```

## Available skills

| Skill | What for | Trigger |
|-------|----------|---------|
| `psql-cli` | Guide the agent to use the PostgreSQL CLI (`psql`) safely and non-interactively: never open the REPL (it hangs), `ON_ERROR_STOP=1`, `PGPASSWORD` instead of `-W`, parseable output, schema inspection | The agent needs to run `psql`, query Postgres from the terminal, inspect schema, or script SQL |

## Conventions

- **Location**: skills live in `.agents/skills/<name>/SKILL.md`, versioned (they travel with the clone).
- **Author**: `KritiusOne` in the frontmatter. Do NOT use the skill-creator template default `gentleman-programming`.
- **allowed-tools**: declare in the frontmatter to pre-authorize binaries (e.g. `Bash(psql:*)`).
- **Naming**: generic skills use the technology name (`psql-cli`, `playwright-cli`).
