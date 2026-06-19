"""
Inventario de notebooks de una fase: lee los .ipynb y deduce, de forma dinámica,
el rol, las funciones, qué lee y qué produce cada uno. Sin nada pegado: si cambias
un notebook, el inventario cambia.
"""
from __future__ import annotations
from pathlib import Path
import json
import re


def _titulo(j: dict) -> str:
    """Título del notebook = primer encabezado H1 de la primera celda markdown."""
    for c in j.get("cells", []):
        if c.get("cell_type") == "markdown":
            s = "".join(c.get("source", []))
            m = re.search(r"^#\s+(.+)", s, re.M)
            if m:
                return re.sub(r"\*+", "", m.group(1)).strip()
    return ""


def _rol(nombre: str, funcs: set, merges: int, html: int, writes: set) -> str:
    n = nombre.lower()
    if "indice" in n or "ejecucion" in n or "dataset_final" in n:
        return "orquestación"
    if "reportes_raw" in n:
        return "reporte (datos originales)"
    if "reportes_clean" in n:
        return "reporte (datos limpios)"
    if "trazabilidad" in n:
        return "trazabilidad/reporte"
    if "dashboard" in n:
        return "dashboard"
    if "grafo" in n:
        return "grafo"
    if "limpieza" in n:
        return "transformación · limpieza"
    if "correccion" in n:
        return "transformación · corrección"
    if "union" in n or merges > 0:
        return "transformación · unión"
    if html > 0:
        return "reporte"
    return "auxiliar"


def parsear_fase(carpeta_notebooks: str | Path, patron: str = "*.ipynb") -> list[dict]:
    """Devuelve un dict por notebook con su metadata deducida."""
    carpeta = Path(carpeta_notebooks)
    salida = []
    for nb in sorted(carpeta.glob(patron)):
        try:
            j = json.load(open(nb, encoding="utf-8"))
        except Exception:
            continue
        funcs, reads, writes = set(), set(), set()
        lee, produce = set(), set()
        merges = html = 0
        for c in j.get("cells", []):
            if c.get("cell_type") != "code":
                continue
            s = "".join(c.get("source", []))
            funcs |= set(re.findall(r"^\s*def\s+(\w+)\s*\(", s, re.M))
            merges += len(re.findall(r"\.merge\(|pd\.merge\(", s))
            # --- ENTRADAS: ficheros leídos ---
            for m in re.findall(r"read_parquet\([^)]*?['\"]?([\w./-]+\.parquet)['\"]?", s):
                lee.add(("parquet", Path(m).name))
            for m in re.findall(r"read_excel\([^)]*?['\"]?([\w./-]+\.xlsx?)['\"]?", s):
                lee.add(("excel", Path(m).name))
            for m in re.findall(r"RUTA_\w+\s*/\s*f?['\"]([\w{}.-]+\.parquet)['\"]", s):
                if "read_parquet" in s:
                    lee.add(("parquet", m))
            # --- SALIDAS: ficheros producidos (tipados) ---
            for m in re.findall(r"to_parquet\([^)]*?['\"]?([\w./-]+\.parquet)['\"]?", s):
                produce.add(("parquet", Path(m).name))
            for m in re.findall(r"RUTA_\w+\s*/\s*f?['\"]([\w{}.-]+\.parquet)['\"]", s):
                if "to_parquet" in s:
                    produce.add(("parquet", m))
            if re.search(r"\.to_csv\(|/\s*['\"][\w.-]+\.csv['\"]", s):
                produce.add(("csv", ""))
            if "render_pagina" in s or "render_base_html" in s or ".html'" in s:
                produce.add(("html", ""))
            if "savefig" in s or re.search(r"\.png['\"]|\.jpg['\"]", s):
                produce.add(("png", ""))
            if ".to_excel(" in s or re.search(r"\.xlsx['\"]", s):
                produce.add(("xlsx", ""))
            if "render_pagina" in s or "render_base_html" in s:
                html += 1
        funcs = {f for f in funcs if not f.startswith("_")}
        transforma = bool(re.search(r"limpieza|union|correccion", nb.name)) or merges > 0
        salida.append({
            "notebook": nb.stem,
            "titulo": _titulo(j),
            "rol": _rol(nb.name, funcs, merges, html, writes),
            "funciones": sorted(funcs),
            "merges": merges,
            "genera_html": bool(html),
            "transforma": transforma,
            "lee": sorted(lee),
            "produce": sorted(produce),
        })
    return salida


def funciones_de(inventario: list[dict]) -> list[dict]:
    """Aplana las funciones reales encontradas, con su notebook y rol."""
    filas = []
    for nb in inventario:
        for f in nb["funciones"]:
            filas.append({"funcion": f, "notebook": nb["notebook"], "rol": nb["rol"]})
        if nb["merges"]:
            filas.append({"funcion": f"pd.merge ×{nb['merges']}",
                          "notebook": nb["notebook"], "rol": nb["rol"]})
    return filas


def grafo_fase(inventario: list[dict]) -> dict:
    """Fuente ÚNICA del grafo: nodos (notebooks + ficheros) y aristas (lee/produce).

    De aquí beben tanto el render Mermaid (estático) como el interactivo.
    """
    import re as _re
    nodos: dict[str, dict] = {}
    aristas: list[dict] = []

    def sid(x: str) -> str:
        return _re.sub(r"\W", "_", x)

    def nodo_fichero(nb_stem, tipo, nombre):
        # parquet/excel: nodo compartido por nombre real (muestra el linaje común).
        # html/png/csv/xlsx sin nombre: nodo propio del notebook (no se fusionan).
        if nombre:
            nid = sid(f"f_{nombre}")
            label = nombre
        else:
            nid = sid(f"f_{nb_stem}_{tipo}")
            label = tipo
        nodos.setdefault(nid, {"id": nid, "label": label, "tipo": tipo, "clase": "fichero"})
        return nid

    for nb in inventario:
        nid = sid(f"nb_{nb['notebook']}")
        nodos[nid] = {"id": nid, "label": nb["notebook"], "tipo": "notebook",
                      "clase": "notebook", "rol": nb["rol"]}
        for tipo, nombre in nb["lee"]:
            fid = nodo_fichero(nb["notebook"], tipo, nombre)
            aristas.append({"src": fid, "dst": nid, "rel": "lee"})
        for tipo, nombre in nb["produce"]:
            fid = nodo_fichero(nb["notebook"], tipo, nombre)
            aristas.append({"src": nid, "dst": fid, "rel": "produce"})
    return {"nodos": list(nodos.values()), "aristas": aristas}
