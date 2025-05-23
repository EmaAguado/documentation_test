#!/usr/bin/env python3
"""
gen_addon_docs.py — Genera documentación de cada addon en docs/dev:
  - Lee addons.json para saber qué addons procesar
  - Para cada addon habilitado:
    * Copia index.md y examples.md si la fuente es más nueva
    * Genera un .md por cada .py (recursivamente) con bloques ::: para mkdocstrings, solo si el .py cambió (omite __init__.py)
    * Genera modules.md como índice, solo si cambia
"""
import json
from pathlib import Path


# Configuración
REPO_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = Path(__file__).parent.resolve()
ADDONS_JSON = SCRIPTS_DIR / "addons.json"
DEST_ROOT = REPO_ROOT / "docs" / "dev"

# Opciones por defecto para mkdocstrings
# MKDS_OPTS = {
    # "members": True,
    # "undoc-members": False,
    # "show-inheritance": True,
# }

def format_opts(opts):
    # Indenta las opciones bajo 'options:'
    return "\n".join(f"        {k}: {'true' if v else 'false'}" for k, v in opts.items())

def load_addons():
    data = json.loads(ADDONS_JSON.read_text(encoding="utf-8"))
    return [a for a in data if a.get("enabled")]

def is_newer(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    return not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime

changed = False
for addon in load_addons():
    name = addon["name"]
    addon_dir = (REPO_ROOT / addon["path"]).resolve()
    dest_base = DEST_ROOT / name
    dest_base.mkdir(parents=True, exist_ok=True)

    # 1) Copiar index.md y examples.md
    # for fname in ("index.md", "examples.md", "readme.md"):
    for src in Path(addon_dir / "docs").rglob('*.md'):
        idx = src.parts.index("docs")
        dst = Path(dest_base).joinpath(*src.parts[idx+1:])
        if is_newer(src, dst):
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            changed = True

    # 2) Recolectar .py recursivamente, excluyendo docs/ y __init__.py
    module_paths = []
    for py in addon_dir.rglob('*.py'):
        if 'docs' in py.parts or py.name == '__init__.py':
            continue
        rel = py.relative_to(addon_dir).with_suffix('')
        module_paths.append((rel, py))

    # 3) Generar md por cada módulo
    for rel, src_py in sorted(module_paths):
        title_name = rel.parts[-1]
        mod_name = '.'.join(rel.parts)
        md_path = dest_base.joinpath(*rel.parts).with_suffix('.md')
        if is_newer(src_py, md_path):
            md_path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                f"# `{title_name}`\n\n"
                f"::: {mod_name}\n"
            )
            md_path.write_text(content, encoding="utf-8")
            changed = True

    # 4) Generar modules.md
    modules_md = dest_base / "modules.md"
    lines = [
        "# Índice de Módulos", "", 
        "Este archivo se genera automáticamente. No editar.", "", 
        "## Módulos", ""
    ]
    for rel, _ in sorted(module_paths):
        name_mod = '.'.join(rel.parts)
        link = f"{rel.as_posix()}.md"
        lines.append(f"- [{name_mod}]({link})")
    lines.append("")
    new_content = "\n".join(lines)
    if not modules_md.exists() or modules_md.read_text(encoding="utf-8") != new_content:
        modules_md.write_text(new_content, encoding="utf-8")
        changed = True

# Mensaje final
if changed:
    print("✅ Documentación de addons actualizada en docs/dev")
else:
    print("ℹ️ No hubo cambios en la documentación de addons")
