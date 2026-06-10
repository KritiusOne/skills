<!-- Language switcher -->
[English](README.md) · **Español**

# custom-skills

Repositorio propio de **skills para agentes de AI**. Objetivo: convertir los problemas comunes que el equipo enfrenta en el desarrollo asistido por AI en conocimiento versionado, reutilizable y compartible — en vez de que cada quien lo resuelva de cero en su cabeza o en su máquina.

Este repo es la **fuente única de verdad** de las skills. Los proyectos que las usen (ej. el ERP) las consumen/sincronizan desde acá; no mantienen su propia copia divergente.

## Estructura

Este repo está dedicado a skills — no hay app — así que las skills viven en el root bajo `skills/`, no anidadas en `.agents/`.

```
skills/<nombre>/
├── SKILL.md          # requerido — frontmatter + guía
├── assets/           # opcional — templates, schemas, ejemplos
└── references/       # opcional — docs locales
```

## Skills disponibles

| Skill | Para qué | Trigger |
|-------|----------|---------|
| `psql-cli` | Dirigir al agente a usar el CLI de PostgreSQL (`psql`) de forma segura y no-interactiva: nunca abrir el REPL (cuelga), `ON_ERROR_STOP=1`, `PGPASSWORD` en vez de `-W`, output parseable, inspección de schema | El agente necesita correr `psql`, consultar Postgres desde la terminal, inspeccionar schema o scriptear SQL |

## Convenciones

- **Ubicación**: las skills viven en `skills/<nombre>/SKILL.md`, versionadas (viajan con el clone). Cuando las consume un proyecto que usa el layout `.agents/skills/` (ej. el ERP), el paso de sync mapea `skills/<nombre>/` → el `.agents/skills/<nombre>/` de ese proyecto.
- **Author**: `KritiusOne` en el frontmatter. NO usar el default `gentleman-programming` del template del skill-creator.
- **allowed-tools**: declarar en el frontmatter para pre-autorizar binarios (ej. `Bash(psql:*)`).
- **Naming**: skills genéricas usan el nombre de la tecnología (`psql-cli`, `playwright-cli`).
