"""
Motor de linaje de datos del TFM (AU_UJI_v2).

Registra el linaje (data lineage) a dos niveles intercambiables y con el MISMO
esquema para todas las fases (F1-F7):

    - nivel 'notebook' : una transicion por notebook (frontera entrada -> salida).
    - nivel 'funcion'  : una transicion por funcion/operacion dentro del notebook.

Principios (innegociables en este proyecto):
    - SOLO LECTURA. Los conteos se leen del valor LITERAL de los parquet
      canonicos; nunca se deduce por suma/resta. No re-ejecuta el pipeline v63.
    - Cuando un parquet existe en disco, los conteos se leen del fichero.
      Cuando no existe (p. ej. datos originales de F1 fuera del repo), se
      registran como valores DECLARADOS y se marca su procedencia.
    - El JSON de salida sigue el esquema OpenLineage (Job / Run / Dataset +
      facets), para ser estandar-compatible sin servidor ni dependencias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json


# --------------------------------------------------------------------------- #
# Modelo de datos
# --------------------------------------------------------------------------- #
@dataclass
class Dataset:
    """Un conjunto de datos (fichero o estado intermedio) con su esquema."""
    nombre: str
    n_filas: Optional[int] = None
    n_cols: Optional[int] = None
    columnas: list[str] = field(default_factory=list)
    clave: Optional[str] = None          # clave/grano, p. ej. 'per_id_ficticio'
    fichero: Optional[str] = None        # ruta canonica si aplica
    tipo: str = "parquet"                # 'excel' | 'parquet' | 'intermedio'
    procedencia: str = "literal"         # 'literal' (leido) | 'declarado'


@dataclass
class Paso:
    """Una transicion entrada(s) -> salida con su diff documentado."""
    id: str
    nivel: str                           # 'notebook' | 'funcion'
    notebook: str                        # notebook responsable
    operacion: str                       # 'limpieza'|'merge'|'filtro'|'dedup'|...
    entradas: list[str]                  # nombres de Dataset de entrada
    salida: str                          # nombre de Dataset de salida
    funcion: Optional[str] = None        # funcion responsable (nivel 'funcion')
    motivo_filas: str = ""               # POR QUE cambia (o no) el nº de filas
    cols_add: list[str] = field(default_factory=list)
    cols_del: list[str] = field(default_factory=list)
    motivo_cols: str = ""
    dtypes_cambiados: list[str] = field(default_factory=list)
    claves_join: list[str] = field(default_factory=list)
    modo: str = "diff"                   # 'diff' (cadena) | 'aporte' (provenance)
    nota: str = ""

    # --- diffs derivados (se calculan con los Dataset asociados) ---
    def delta_filas(self, datasets: dict[str, Dataset]) -> Optional[int]:
        """Δ filas = filas(salida) - filas(entrada principal). Literal, no inventado.
        En modo 'aporte' no aplica (entrada y salida no son comparables por filas)."""
        if self.modo == "aporte":
            return None
        sal = datasets.get(self.salida)
        if not self.entradas or sal is None or sal.n_filas is None:
            return None
        ent = datasets.get(self.entradas[0])
        if ent is None or ent.n_filas is None:
            return None
        return sal.n_filas - ent.n_filas

    def _cols_entrada(self, datasets: dict[str, Dataset]) -> list[str]:
        cols: list[str] = []
        for e in self.entradas:
            d = datasets.get(e)
            if d and d.columnas:
                cols += [c for c in d.columnas if c not in cols]
        return cols

    def cols_anadidas(self, datasets: dict[str, Dataset]) -> list[str]:
        """Columnas en la salida que no estaban en ninguna entrada. DINÁMICO:
        se derivan comparando los esquemas REALES leídos del parquet.
        En modo 'aporte': columnas de la fuente (entrada) que acaban en la salida,
        excluyendo las claves de unión. Si se pasó `cols_add` a mano, manda."""
        if self.cols_add:
            return self.cols_add
        sal = datasets.get(self.salida)
        if not sal or not sal.columnas:
            return []
        if self.modo == "aporte":
            fuente = datasets.get(self.entradas[0]) if self.entradas else None
            if not fuente or not fuente.columnas:
                return []
            claves = set(self.claves_join) | ({fuente.clave} if fuente.clave else set())
            return [c for c in fuente.columnas if c in sal.columnas and c not in claves]
        ent = self._cols_entrada(datasets)
        if not ent:
            return []
        return [c for c in sal.columnas if c not in ent]

    def cols_eliminadas(self, datasets: dict[str, Dataset]) -> list[str]:
        """Columnas que estaban en la entrada y desaparecen en la salida."""
        if self.cols_del:
            return self.cols_del
        sal = datasets.get(self.salida)
        ent = self._cols_entrada(datasets)
        if not sal or not sal.columnas or not ent:
            return []
        return [c for c in ent if c not in sal.columnas]


# --------------------------------------------------------------------------- #
# Acumulador de linaje por fase
# --------------------------------------------------------------------------- #
class Linaje:
    """Acumula Datasets y Pasos de una fase, a un nivel dado, y exporta."""

    def __init__(self, fase: str, nivel: str, titulo: str = ""):
        assert nivel in ("notebook", "funcion"), "nivel: 'notebook' | 'funcion'"
        self.fase = fase
        self.nivel = nivel
        self.titulo = titulo or f"Linaje {fase} (nivel {nivel})"
        self.datasets: dict[str, Dataset] = {}
        self.pasos: list[Paso] = []
        self.generado = datetime.now(timezone.utc).isoformat()

    # ---- alta de datasets ------------------------------------------------- #
    def declarar(self, nombre: str, n_filas: int, n_cols: int,
                 columnas: Optional[list[str]] = None, clave: Optional[str] = None,
                 fichero: Optional[str] = None, tipo: str = "parquet") -> Dataset:
        """Registra un dataset con valores LITERALES declarados (procedencia conocida)."""
        ds = Dataset(nombre=nombre, n_filas=n_filas, n_cols=n_cols,
                     columnas=columnas or [], clave=clave, fichero=fichero,
                     tipo=tipo, procedencia="declarado")
        self.datasets[nombre] = ds
        return ds

    def leer_parquet(self, nombre: str, ruta: str | Path,
                     clave: Optional[str] = None) -> Dataset:
        """Lee un parquet en SOLO LECTURA y registra sus conteos LITERALES.

        Solo se usa cuando el fichero existe en disco. No modifica nada.
        """
        import pyarrow.parquet as pq
        ruta = Path(ruta)
        pf = pq.ParquetFile(ruta)                      # no carga datos en memoria
        n_filas = pf.metadata.num_rows                 # literal del metadato
        columnas = list(pf.schema_arrow.names)
        ds = Dataset(nombre=nombre, n_filas=n_filas, n_cols=len(columnas),
                     columnas=columnas, clave=clave, fichero=str(ruta),
                     tipo="parquet", procedencia="literal")
        self.datasets[nombre] = ds
        return ds

    # ---- alta de pasos ---------------------------------------------------- #
    def paso(self, **kwargs) -> Paso:
        kwargs.setdefault("nivel", self.nivel)
        p = Paso(**kwargs)
        self.pasos.append(p)
        return p

    # ---- exportadores (delegan en exporters.py) --------------------------- #
    def a_json(self, ruta: str | Path) -> Path:
        from .exporters import a_json
        return a_json(self, ruta)

    def a_markdown(self, ruta: str | Path) -> Path:
        from .exporters import a_markdown
        return a_markdown(self, ruta)

    def a_xlsx(self, ruta: str | Path) -> Path:
        from .exporters import a_xlsx
        return a_xlsx(self, ruta)

    def a_html(self, ruta: str | Path, ruta_style: str = "../style.css") -> Path:
        from .exporters import a_html
        return a_html(self, ruta, ruta_style=ruta_style)

    def exportar_todo(self, carpeta: str | Path, base: str,
                      ruta_style: str = "../style.css") -> dict[str, Path]:
        """Genera los 4 entregables con el mismo nombre base."""
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        return {
            "json": self.a_json(carpeta / f"{base}.json"),
            "md":   self.a_markdown(carpeta / f"{base}.md"),
            "xlsx": self.a_xlsx(carpeta / f"{base}.xlsx"),
            "html": self.a_html(carpeta / f"{base}.html", ruta_style=ruta_style),
        }
