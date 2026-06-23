---
name: obsidian-vault
description: >
  Manage notes in an Obsidian vault (plain-markdown folder) following a fixed structure:
  knowledge/ notes, tasks/ with timestamp+slug naming, templates/, and a _scripts/new_task.py helper.
  Trigger: When creating, naming, or organizing notes/tasks in an Obsidian vault; writing task or
  knowledge frontmatter; wiring [[wiki]] or ./relative.md links; or bootstrapping a vault's templates/script.
  NOT for Obsidian plugin development (TypeScript API), Dataview/Templater query authoring, the Local REST
  API plugin, the obsidian:// URI scheme, or any vault that is open and must be driven through the running app.
allowed-tools: Bash(python:*)
license: Apache-2.0
metadata:
  author: KritiusOne
  version: "1.0"
---

## When to Use

- Creating a new task or knowledge note in a vault that follows this structure.
- You need deterministic naming + complete frontmatter without hand-typing it.
- Normalizing or wiring links between notes (`[[wiki]]` or `./relative.md`).
- Bootstrapping `templates/` + `_scripts/new_task.py` into a fresh vault.

## Core Principle

**An Obsidian vault is a plain folder of markdown files.** `.obsidian/` is only UI config —
Obsidian does NOT need to be open. Manipulate the vault with file tools or a script, never via a
plugin/CLI dependency. The helper script handles the mechanical work (timestamp, slug, frontmatter)
so the agent stops hand-writing it (and stops introducing placeholder bugs like `estado: status`).

## Vault Structure

```
vault/
├── 00_Index.md            # MOC / index — links to knowledge + tracks objetivos
├── pendings.md            # tracker: "P<n> | <Area> | <ESTADO>" + links to tasks
├── knowledge/             # architecture / module design notes (NN_PascalCase_Con_Guiones.md)
├── tasks/                 # operational tasks — naming: <YYYYMMDDHHmm>-<slug>.md
├── templates/             # task.md + knowledge.md
└── _scripts/
    └── new_task.py        # task generator (stdlib only, headless)
```

## Critical Patterns

**1. Tasks are created with the script, never by hand.** Hand-writing frontmatter is how
`estado: status` placeholders and naming drift get in. Run the helper:

```bash
python _scripts/new_task.py "Título de la task" --prioridad P2 --area Legal --tags "crm,bug"
```

It computes the timestamp, slugifies the title (ascii, no accents), writes
`tasks/<YYYYMMDDHHmm>-<slug>.md` from `templates/task.md`, and prints the path.

**2. Task frontmatter is the canonical schema — no other shape.**

```yaml
---
title: "<título humano>"
created: 2026-06-23T14:30      # ISO datetime, set by the script
prioridad: P3                 # P1 | P2 | P3
estado: TODO                  # TODO | IN_PROGRESS | BLOCKED | WAITING | DONE
area: Development              # Development | DevOps | Legal | RRHH | TI | Ventas | Admin
tags: []
# limite: 2026-06-30          # optional deadline
# parent: "[[<task>]]"        # optional, for subtasks
---
```

**3. Filenames carry BOTH timestamp and slug.** `<YYYYMMDDHHmm>-<slug>.md` → native chronological
sort + readable slug. The same timestamp also lives in `created`. Never rename a task to a bare slug.

**4. Links: pick the right style.**
- Between notes anywhere in the vault → `[[<filename-without-ext>]]` (wiki-links resolve by basename,
  so moving a note between folders does NOT break them).
- Inside a task's `## Subtareas` / `## Relacionadas` → `[Texto](./<timestamp>-slug.md)` relative links.
- If you rename a note, rewrite every reference to it (longest-match first to avoid partial replaces).

**5. Knowledge notes are manual and numbered.** `knowledge/NN_PascalCase_Con_Guiones.md` from
`templates/knowledge.md`. They are rare and curated — no script.

**6. `pendings.md` is the human triage view.** Format `P<n> | <Area> | <ESTADO>` with links to tasks.
Keep its `<ESTADO>` label consistent with each task's `estado` frontmatter.

## Commands

```bash
# Create a task (most common operation)
python _scripts/new_task.py "Arreglar login que no persiste sesión" --prioridad P1 --area Development --tags "auth,bug"

# Defaults: --prioridad P3  --estado TODO  --area Development  --tags ""
python _scripts/new_task.py "Documentar el módulo de ventas"

# Bootstrap a fresh vault: copy the shipped template + script into place
#   assets/task.md      -> templates/task.md
#   assets/knowledge.md -> templates/knowledge.md
#   assets/new_task.py  -> _scripts/new_task.py
```

## Resources

| Resource | Type | Scope |
|----------|------|-------|
| `python` interpreter | Shell | `Bash(python:*)` — runs the stdlib-only helper, no other binaries |
| Vault markdown files (`tasks/`, `templates/`, `knowledge/`) | File | Read/write under the vault root only |
| `templates/task.md` | File | Read-only input consumed by `new_task.py` |
| Network | — | None. No plugin, no REST API, no `obsidian://`; works fully offline |
| Secrets | — | None |

## Bootstrap Assets

- **Templates**: [assets/task.md](assets/task.md), [assets/knowledge.md](assets/knowledge.md)
- **Helper**: [assets/new_task.py](assets/new_task.py) — copy to `_scripts/` at the vault root
