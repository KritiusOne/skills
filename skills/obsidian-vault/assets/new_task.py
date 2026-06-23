#!/usr/bin/env python3
"""Crea una task en el vault siguiendo el template y el naming canónico.

Uso:
    python _scripts/new_task.py "Título de la task" [opciones]

Opciones:
    --prioridad {P1,P2,P3}                     (default: P3)
    --estado {TODO,IN_PROGRESS,BLOCKED,WAITING,DONE}  (default: TODO)
    --area AREA                                (default: Development)
    --tags "tag1,tag2"                         (default: vacío)

Genera tasks/<YYYYMMDDHHmm>-<slug>.md desde templates/task.md, con el
frontmatter completo (incluido `created` ISO). Imprime la ruta creada.
Sin dependencias externas: solo stdlib. No requiere Obsidian abierto.
"""
import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

PRIORIDADES = ("P1", "P2", "P3")
ESTADOS = ("TODO", "IN_PROGRESS", "BLOCKED", "WAITING", "DONE")

VAULT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = VAULT_ROOT / "templates" / "task.md"
TASKS_DIR = VAULT_ROOT / "tasks"


def slugify(text: str) -> str:
    """Pasa un título a slug ascii: minúsculas, sin acentos, separado por guiones."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-")


def parse_args(argv):
    p = argparse.ArgumentParser(description="Crea una task en el vault.")
    p.add_argument("title", help="Título humano de la task")
    p.add_argument("--prioridad", choices=PRIORIDADES, default="P3")
    p.add_argument("--estado", choices=ESTADOS, default="TODO")
    p.add_argument("--area", default="Development")
    p.add_argument("--tags", default="", help='Lista separada por comas: "ci,devops"')
    return p.parse_args(argv)


def render(template: str, **fields) -> str:
    out = template
    for key, value in fields.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def main(argv):
    args = parse_args(argv)

    if not TEMPLATE.exists():
        sys.exit(f"ERROR: no existe el template {TEMPLATE}")

    slug = slugify(args.title)
    if not slug:
        sys.exit("ERROR: el título no produjo un slug válido")

    now = datetime.now()
    stamp = now.strftime("%Y%m%d%H%M")          # para el nombre de archivo
    created = now.strftime("%Y-%m-%dT%H:%M")     # para el frontmatter

    tags = ", ".join(t.strip() for t in args.tags.split(",") if t.strip())

    TASKS_DIR.mkdir(exist_ok=True)
    dest = TASKS_DIR / f"{stamp}-{slug}.md"
    if dest.exists():
        sys.exit(f"ERROR: ya existe {dest}")

    content = render(
        TEMPLATE.read_text(encoding="utf-8"),
        title=args.title,
        created=created,
        prioridad=args.prioridad,
        estado=args.estado,
        area=args.area,
        tags=tags,
    )
    dest.write_text(content, encoding="utf-8")
    print(dest)


if __name__ == "__main__":
    main(sys.argv[1:])
