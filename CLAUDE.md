# CLAUDE.md

This project's agent instructions live in **[AGENTS.md](./AGENTS.md)** — read it first.

It covers the repo's purpose, structure, skill-authoring conventions (author `KritiusOne`,
`name`/`description` rules, `allowed-tools`, resource declaration), the add-a-skill
workflow, and the CI validation gate.

Claude Code reads skills from `.claude/skills/` (generated, gitignored). After any change
to `skills/`, regenerate with `python scripts/sync_skills.py` and run the validation gate
before committing.
