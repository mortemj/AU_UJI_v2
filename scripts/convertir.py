"""
=============================================================================
convertir.py

Convierte TODOS los notebooks .ipynb del proyecto a ficheros markdown (.md),
para poder pasarlos facilmente a NotebookLM u otras herramientas de texto.

Por cada notebook genera un .md con el mismo nombre, junto al original:
  - las celdas markdown se copian tal cual,
  - las celdas de codigo se envuelven en un bloque ```python ... ```.

La raiz del proyecto se detecta dinamicamente (sube niveles hasta encontrar
la carpeta src/), no esta escrita a mano: asi funciona en cualquier equipo.

Uso:
    python scripts/convertir.py
=============================================================================
"""

import json
import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Localizar la raiz del proyecto (sube hasta encontrar la carpeta src/)
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
while not (ROOT / "src").exists():
    if ROOT.parent == ROOT:
        raise RuntimeError("No se ha encontrado la carpeta src/ subiendo niveles")
    ROOT = ROOT.parent

base_dir = str(ROOT)

# Marca de cierre de un bloque de codigo markdown (tres comillas invertidas).
# Se guarda en una variable para no romper el f-string al escribirla.
CIERRE_CODIGO = "```"

for root, dirs, files in os.walk(base_dir):
    # Ignorar carpetas que no interesan (checkpoints, control de versiones, cache)
    if ".ipynb_checkpoints" in root or ".git" in root or "__pycache__" in root:
        continue

    for file in files:
        if file.endswith(".ipynb"):
            ipynb_path = os.path.join(root, file)
            md_path = ipynb_path.replace(".ipynb", ".md")

            try:
                with open(ipynb_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                md_content = f"# Cuaderno: {file}\n\n"
                for cell in data.get("cells", []):
                    cell_type = cell.get("cell_type", "")
                    source = "".join(cell.get("source", []))

                    if cell_type == "markdown":
                        md_content += f"{source}\n\n"
                    elif cell_type == "code":
                        md_content += f"```python\n{source}\n{CIERRE_CODIGO}\n\n"

                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"Convertido con exito: {file}")

            except Exception as e:
                print(f"Error en {file}: {str(e)}")
