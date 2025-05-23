# scripts/gen_ref_pages.py

import os
from pathlib import Path

# Paquetes a documentar
src_roots = ["addon_a", "addon_b", "plugin_a", "plugin_b"]

for root in src_roots:
    src_dir = Path(root)
    docs_dir = src_dir / "docs"
    api_dir = docs_dir / f"{src_dir}_api"

    # Asegúrate de que api_dir existe
    api_dir.mkdir(parents=True, exist_ok=True)

    # Recorre todos los .py fuera de la carpeta docs
    for path in sorted(src_dir.rglob("*.py")):
        if "docs" in path.parts:
            continue

        # Calcula el módulo Python: e.g. 'addon_a/ui/check_page.py' → 'ui.check_page'
        relative = path.relative_to(src_dir).with_suffix("")
        parts = list(relative.parts)
        if relative.name == "__init__":
            parts = parts[:-1]
        module_path = ".".join(parts)

        # Ruta real al .md que vamos a crear
        target_path = api_dir.joinpath(*parts).with_suffix(".md")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Contenido del stub
        content = f"# Módulo `{module_path}`\n\n::: {module_path}\n"

        # Escribe el fichero al disco
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        # (Opcional) imprime para debug
        print(f"Generado: {target_path}")
