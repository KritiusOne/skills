---
name: psql-cli
description: >
  Guide any AI agent to use the PostgreSQL CLI (psql) safely and non-interactively from a shell.
  Trigger: When the agent needs to run psql, query a Postgres database from the terminal, inspect schema, or script SQL.
  NOT for interactive REPL sessions, GUI database clients, ORMs, non-PostgreSQL databases, or any context where psql is not the intended execution path.
allowed-tools: Bash(psql:*)
license: Apache-2.0
metadata:
  author: KritiusOne
  version: "1.0"
---

## When to Use

- The agent must run `psql` from a non-interactive shell (Bash tool, CI, scripts).
- Inspecting schema, tables, columns, indexes, or running ad-hoc SELECTs.
- Scripting SQL where interactive prompts would hang the session.
- Connecting with explicit credentials instead of relying on a logged-in shell.

## Critical Patterns

**1. NEVER run psql interactively from an agent shell.** Bare `psql` opens a REPL that waits for input and HANGS the tool call. Always pass the SQL inline.

| Goal | Use |
|------|-----|
| Run one query | `psql "$CONN" -c "SELECT 1;"` |
| Run a SQL file | `psql "$CONN" -f script.sql` |
| Fail the command on SQL error | add `-v ON_ERROR_STOP=1` |
| Quiet, script-friendly output | `-q` (quiet) + `-A -t` (unaligned, tuples-only) |
| Clean CSV out | `--csv` |
| Don't read `~/.psqlrc` | `-X` (reproducible, no surprise settings) |

**2. Always pass `ON_ERROR_STOP=1` in scripts.** Without it, psql keeps going after a failed statement and exits 0 — silent failures.

**3. Prefer a connection URI over scattered flags.** `postgresql://user:pass@host:5432/dbname?sslmode=require`. Put it in an env var, never inline secrets into committed files.

**4. Use `PGPASSWORD` env var, not `-W`.** `-W` forces an interactive password prompt → hangs. Set `PGPASSWORD` (or a `.pgpass` file) instead.

**5. Wide rows: use expanded mode.** Add `-x` (or `\x` inside SQL) so a row prints as key/value lines instead of an unreadable wide table.

**6. Read-only by default.** For inspection, connect with a read-only role or wrap writes in an explicit transaction. Never run destructive DML/DDL without confirming intent and scope.

## Code Examples

```bash
# One-off query, fail loudly, no rc file
psql -X -v ON_ERROR_STOP=1 "$DATABASE_URL" -c "SELECT count(*) FROM users;"

# Tuples-only, unaligned → easy to pipe/parse
psql -X -A -t -c "SELECT id, email FROM users LIMIT 5;" "$DATABASE_URL"

# Clean CSV
psql -X --csv -c "SELECT * FROM orders WHERE total > 100;" "$DATABASE_URL"

# Wide row, expanded output
psql -X -x -c "SELECT * FROM users WHERE id = 1;" "$DATABASE_URL"

# Run a migration/script and stop on first error
PGPASSWORD="$PW" psql -X -v ON_ERROR_STOP=1 -h db.host -U app -d erp -f migration.sql
```

## Schema Inspection (meta-commands via -c)

```bash
psql -X -c "\dt"                 "$DATABASE_URL"   # list tables
psql -X -c "\d+ tablename"       "$DATABASE_URL"   # describe table (cols, indexes, FKs)
psql -X -c "\dn"                 "$DATABASE_URL"   # list schemas
psql -X -c "\di"                 "$DATABASE_URL"   # list indexes
psql -X -c "\df"                 "$DATABASE_URL"   # list functions
psql -X -c "\l"                  "$DATABASE_URL"   # list databases
```

Prefer `information_schema` / `pg_catalog` queries when you need to parse output programmatically — meta-command output format is not stable.

## Platform Notes

| Shell | Gotcha |
|-------|--------|
| PowerShell (Windows) | Use double quotes for `-c "..."`; `$env:PGPASSWORD="..."` to set the password; `$null` not `/dev/null`. |
| Bash / POSIX | Single-quote the SQL to avoid `$` expansion: `-c 'SELECT ...'`. |
| Any | If the connection string has special chars (`@`, `:`, `/`), URL-encode them in the URI. |

## Commands

```bash
psql --version                                  # confirm client is installed
psql -X -c "SELECT version();" "$DATABASE_URL"  # confirm connectivity + server version
psql -X -c "SELECT current_database(), current_user;" "$DATABASE_URL"
```

## Resources

| Resource | Type | Scope |
|----------|------|-------|
| `psql` binary | Shell | Bash(psql:*) — scoped, no other binaries |
| PostgreSQL endpoint (host/port/database) | Network | Outbound TCP to whatever `$DATABASE_URL` / `-h` resolves to; no hardcoded endpoint |
| `PGPASSWORD` environment variable | Secrets | Read-only at runtime; never written to files by this skill |
| Local SQL files (`-f script.sql`) | File | Read-only input; skill never writes project files |

## Safety Checklist Before Writes

- [ ] Connection target is the intended environment (not prod by accident).
- [ ] `ON_ERROR_STOP=1` is set for any multi-statement script.
- [ ] Destructive statements (`DELETE`/`UPDATE`/`DROP`/`TRUNCATE`) have a `WHERE` and a known blast radius.
- [ ] Secrets come from env/`.pgpass`, never hardcoded into committed files.
