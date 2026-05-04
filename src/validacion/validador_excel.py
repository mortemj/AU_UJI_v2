# ============================================================================
# VALIDADOR_EXCEL.PY — Validación N1-N5 de los Excel originales
# ============================================================================
# TFM: Predicción de Abandono Universitario UJI
#
# PROPÓSITO
# ---------
# Verifica que los 2 Excel originales (proporcionados por OPP / UADTI de la UJI)
# cumplen el contrato definido en `contrato_excel.py` ANTES de que se ejecute
# Fase 1. Detectar problemas estructurales aquí evita horas de depuración
# posterior en F1-F7.
#
# 5 NIVELES DE VALIDACIÓN
# -----------------------
#   N1 🔴 EXISTENCIA   : los 2 ficheros existen, son legibles, tamaño>0
#   N2 🔴 HOJAS        : el Excel principal tiene exactamente las 8 hojas
#                        esperadas (case-sensitive en nombres de hoja)
#   N3 🔴 COLUMNAS     : cada hoja tiene las columnas obligatorias
#                        (case-INsensitive en nombres de columna)
#   N4 🟡 TIPOS        : los dtypes detectados coinciden con lo esperado
#   N5 🟡 VOLUMEN+CRUCES: filas razonables y cruces de IDs entre hojas OK
#
# Las funciones N1-N3 son BLOQUEANTES: si fallan, el orquestador NO debería
# continuar. N4 y N5 son WARNINGS: avisan pero no bloquean.
#
# FORMATO DE RETORNO
# ------------------
# Cada función devuelve un dict:
#   {
#       "nivel": "N1",
#       "tipo": "bloqueante",       # o "warning"
#       "pasa": True/False,
#       "mensajes_ok": [...],       # lo que SÍ pasó
#       "mensajes_error": [...],    # lo que NO pasó (si aplica)
#       "detalles": {...},          # info adicional para informe HTML
#   }
# ============================================================================

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.config_entorno import (
    EXCEL_PRINCIPAL,
    EXCEL_PREINSCRIPCION,
)
from src.validacion.contrato_excel import (
    CONTRATO_EXCEL,
    CRUCES_ESPERADOS,
    TIPO_NUMERICO,
    TIPO_TEXTO,
    TIPO_FECHA,
    TIPO_MIXTO,
    hojas_esperadas,
)


# ============================================================================
# UTILIDADES INTERNAS
# ============================================================================

def _normalizar(nombre: str) -> str:
    """
    Normaliza un nombre de columna para comparación case-insensitive.
    Solo se aplica a NOMBRES DE COLUMNA (no a nombres de hoja).
    """
    return nombre.strip().lower()


def _existe_columna_case_insensitive(
    columnas_reales: List[str],
    columna_buscada: str,
) -> Optional[str]:
    """
    Busca una columna ignorando mayúsculas/minúsculas.

    Returns
    -------
    str o None
        Si existe, devuelve el nombre REAL tal como está en el Excel.
        Si no existe, devuelve None.
    """
    objetivo = _normalizar(columna_buscada)
    for col_real in columnas_reales:
        if _normalizar(col_real) == objetivo:
            return col_real
    return None


def _dtype_pandas_a_categoria(dtype_pd) -> str:
    """
    Mapea un dtype de pandas a una de las 4 categorías del contrato.
    """
    dtype_str = str(dtype_pd)
    if "int" in dtype_str or "float" in dtype_str:
        return TIPO_NUMERICO
    if "datetime" in dtype_str:
        return TIPO_FECHA
    if "object" in dtype_str or "string" in dtype_str:
        return TIPO_TEXTO
    return TIPO_MIXTO  # bool, category, etc.


def _ruta_de_fichero(clave_fichero: str) -> Path:
    """Devuelve la ruta del Excel según la clave del contrato."""
    if clave_fichero == "principal":
        return EXCEL_PRINCIPAL
    if clave_fichero == "preinscripcion":
        return EXCEL_PREINSCRIPCION
    raise ValueError(f"clave_fichero desconocido: {clave_fichero!r}")


# ============================================================================
# N1 — EXISTENCIA (🔴 bloqueante)
# ============================================================================

def validar_n1_existencia() -> Dict[str, Any]:
    """
    Verifica que los 2 ficheros Excel existen, son legibles y tamaño > 0.
    """
    resultado: Dict[str, Any] = {
        "nivel": "N1",
        "titulo": "Existencia de ficheros",
        "tipo": "bloqueante",
        "pasa": True,
        "mensajes_ok": [],
        "mensajes_error": [],
        "detalles": {},
    }

    for clave, ruta in [("principal", EXCEL_PRINCIPAL),
                        ("preinscripcion", EXCEL_PREINSCRIPCION)]:
        # 1) Existe
        if not ruta.exists():
            resultado["pasa"] = False
            resultado["mensajes_error"].append(
                f"❌ No existe: {ruta}"
            )
            resultado["detalles"][clave] = {"existe": False, "tamano_bytes": 0}
            continue

        # 2) Tamaño > 0
        tamano = ruta.stat().st_size
        if tamano == 0:
            resultado["pasa"] = False
            resultado["mensajes_error"].append(
                f"❌ Fichero vacío (0 bytes): {ruta.name}"
            )
            resultado["detalles"][clave] = {"existe": True, "tamano_bytes": 0}
            continue

        # 3) Legible (intentamos abrir con pandas)
        try:
            _ = pd.ExcelFile(ruta)
        except Exception as e:
            resultado["pasa"] = False
            resultado["mensajes_error"].append(
                f"❌ No se puede abrir {ruta.name}: {e}"
            )
            resultado["detalles"][clave] = {
                "existe": True, "tamano_bytes": tamano, "error_lectura": str(e),
            }
            continue

        # OK
        resultado["mensajes_ok"].append(
            f"✅ {ruta.name} existe, legible, {tamano:,} bytes"
        )
        resultado["detalles"][clave] = {
            "existe": True, "tamano_bytes": tamano, "ruta": str(ruta),
        }

    return resultado


# ============================================================================
# N2 — HOJAS DEL EXCEL PRINCIPAL (🔴 bloqueante)
# ============================================================================

def validar_n2_hojas() -> Dict[str, Any]:
    """
    Verifica que cada Excel tenga las hojas esperadas según el contrato.
    Comparación case-sensitive en nombres de hoja.
    """
    resultado: Dict[str, Any] = {
        "nivel": "N2",
        "titulo": "Estructura de hojas",
        "tipo": "bloqueante",
        "pasa": True,
        "mensajes_ok": [],
        "mensajes_error": [],
        "detalles": {},
    }

    for clave_fichero in ("principal", "preinscripcion"):
        ruta = _ruta_de_fichero(clave_fichero)
        esperadas = set(hojas_esperadas(clave_fichero))

        try:
            xls = pd.ExcelFile(ruta)
            reales = set(xls.sheet_names)
        except Exception as e:
            resultado["pasa"] = False
            resultado["mensajes_error"].append(
                f"❌ No se pueden listar hojas de {ruta.name}: {e}"
            )
            continue

        faltantes = esperadas - reales
        extras = reales - esperadas

        if faltantes:
            resultado["pasa"] = False
            for h in sorted(faltantes):
                resultado["mensajes_error"].append(
                    f"❌ [{ruta.name}] Hoja esperada NO encontrada: {h!r}"
                )

        if extras:
            # Las hojas extra NO bloquean, solo informamos
            for h in sorted(extras):
                resultado["mensajes_ok"].append(
                    f"⚠️  [{ruta.name}] Hoja extra (no esperada, no bloquea): {h!r}"
                )

        if not faltantes:
            resultado["mensajes_ok"].append(
                f"✅ [{ruta.name}] Todas las hojas esperadas están presentes "
                f"({len(esperadas)})"
            )

        resultado["detalles"][clave_fichero] = {
            "esperadas": sorted(esperadas),
            "reales": sorted(reales),
            "faltantes": sorted(faltantes),
            "extras": sorted(extras),
        }

    return resultado


# ============================================================================
# N3 — COLUMNAS OBLIGATORIAS (🔴 bloqueante)
# ============================================================================

def validar_n3_columnas() -> Dict[str, Any]:
    """
    Verifica que cada hoja tenga las columnas obligatorias del contrato.
    Comparación case-INsensitive en nombres de columna.
    """
    resultado: Dict[str, Any] = {
        "nivel": "N3",
        "titulo": "Columnas obligatorias",
        "tipo": "bloqueante",
        "pasa": True,
        "mensajes_ok": [],
        "mensajes_error": [],
        "detalles": {},
    }

    for nombre_hoja, contrato in CONTRATO_EXCEL.items():
        ruta = _ruta_de_fichero(contrato["fichero"])

        try:
            # Solo leemos cabecera (nrows=0) para velocidad
            df = pd.read_excel(ruta, sheet_name=nombre_hoja, nrows=0)
            columnas_reales = list(df.columns)
        except Exception as e:
            resultado["pasa"] = False
            resultado["mensajes_error"].append(
                f"❌ [{nombre_hoja}] No se pueden leer columnas: {e}"
            )
            continue

        faltantes: List[str] = []
        encontradas_con_nombre_real: Dict[str, str] = {}

        for col_esperada in contrato["columnas_obligatorias"]:
            nombre_real = _existe_columna_case_insensitive(
                columnas_reales, col_esperada
            )
            if nombre_real is None:
                faltantes.append(col_esperada)
            else:
                encontradas_con_nombre_real[col_esperada] = nombre_real

        # Avisar si hubo diferencia case (esperada vs real)
        diferencias_case: List[Tuple[str, str]] = [
            (esp, real)
            for esp, real in encontradas_con_nombre_real.items()
            if esp != real
        ]

        if faltantes:
            resultado["pasa"] = False
            for col in faltantes:
                resultado["mensajes_error"].append(
                    f"❌ [{nombre_hoja}] Columna obligatoria NO encontrada: "
                    f"{col!r}"
                )
        else:
            resultado["mensajes_ok"].append(
                f"✅ [{nombre_hoja}] {len(contrato['columnas_obligatorias'])} "
                f"columnas obligatorias presentes"
            )

        # Avisar de diferencias de mayús/minús (no bloquean)
        for esp, real in diferencias_case:
            resultado["mensajes_ok"].append(
                f"⚠️  [{nombre_hoja}] Columna {esp!r} se encontró como {real!r} "
                f"(diferencia de mayúsculas, no bloquea)"
            )

        resultado["detalles"][nombre_hoja] = {
            "columnas_reales": columnas_reales,
            "faltantes": faltantes,
            "diferencias_case": diferencias_case,
        }

    return resultado


# ============================================================================
# N4 — TIPOS DE DATOS (🟡 warning)
# ============================================================================

def validar_n4_tipos(filas_muestra: int = 1000) -> Dict[str, Any]:
    """
    Verifica que los dtypes detectados coincidan con las categorías del
    contrato. NO bloquea: solo emite warnings si hay desajustes.

    Parameters
    ----------
    filas_muestra : int
        Número de filas a leer para detectar dtypes (default 1000).
        Más filas = detección más fiable, pero más lento.
    """
    resultado: Dict[str, Any] = {
        "nivel": "N4",
        "titulo": "Tipos de datos",
        "tipo": "warning",
        "pasa": True,  # nunca bloquea
        "mensajes_ok": [],
        "mensajes_error": [],
        "detalles": {},
    }

    for nombre_hoja, contrato in CONTRATO_EXCEL.items():
        ruta = _ruta_de_fichero(contrato["fichero"])

        try:
            df = pd.read_excel(ruta, sheet_name=nombre_hoja, nrows=filas_muestra)
        except Exception as e:
            resultado["mensajes_error"].append(
                f"⚠️  [{nombre_hoja}] No se ha podido leer muestra: {e}"
            )
            continue

        desajustes: List[Dict[str, str]] = []

        for col_esperada, tipo_esperado in contrato["tipos_esperados"].items():
            # Buscar el nombre real (case-insensitive) — N3 ya validó que existe
            nombre_real = _existe_columna_case_insensitive(
                list(df.columns), col_esperada
            )
            if nombre_real is None:
                continue  # ya lo reportó N3

            tipo_detectado = _dtype_pandas_a_categoria(df[nombre_real].dtype)

            # MIXTO acepta cualquier tipo
            if tipo_esperado == TIPO_MIXTO:
                continue

            if tipo_detectado != tipo_esperado:
                desajustes.append({
                    "columna": col_esperada,
                    "esperado": tipo_esperado,
                    "detectado": tipo_detectado,
                    "dtype_real": str(df[nombre_real].dtype),
                })

        if desajustes:
            for d in desajustes:
                resultado["mensajes_error"].append(
                    f"⚠️  [{nombre_hoja}] Columna {d['columna']!r}: "
                    f"esperado {d['esperado']}, detectado {d['detectado']} "
                    f"(dtype real: {d['dtype_real']})"
                )
        else:
            resultado["mensajes_ok"].append(
                f"✅ [{nombre_hoja}] Todos los tipos coinciden"
            )

        resultado["detalles"][nombre_hoja] = {"desajustes": desajustes}

    return resultado


# ============================================================================
# N5 — VOLUMEN Y CRUCES (🟡 warning)
# ============================================================================

def validar_n5_volumen_y_cruces(
    sample_size: int = 1000,
) -> Dict[str, Any]:
    """
    Verifica:
      a) Volumen: cada hoja tiene >= min_filas según contrato
      b) Cruces: los IDs de `Expedientes` aparecen en otras hojas

    NO bloquea. Útil para detectar Excel "vacíos" o desincronizados.

    Parameters
    ----------
    sample_size : int
        Tamaño del sample para validar cruces (default 1000 IDs).
    """
    resultado: Dict[str, Any] = {
        "nivel": "N5",
        "titulo": "Volumen y cruces de IDs",
        "tipo": "warning",
        "pasa": True,
        "mensajes_ok": [],
        "mensajes_error": [],
        "detalles": {"volumen": {}, "cruces": {}},
    }

    # ------------------------------------------------------------------------
    # a) VOLUMEN
    # ------------------------------------------------------------------------
    for nombre_hoja, contrato in CONTRATO_EXCEL.items():
        ruta = _ruta_de_fichero(contrato["fichero"])
        min_filas = contrato.get("min_filas", 0)

        try:
            # Leer solo 1 columna para contar filas más rápido
            df_count = pd.read_excel(ruta, sheet_name=nombre_hoja, usecols=[0])
            n_filas = len(df_count)
        except Exception as e:
            resultado["mensajes_error"].append(
                f"⚠️  [{nombre_hoja}] No se pueden contar filas: {e}"
            )
            continue

        if n_filas < min_filas:
            resultado["mensajes_error"].append(
                f"⚠️  [{nombre_hoja}] Solo {n_filas:,} filas "
                f"(mínimo esperado: {min_filas:,})"
            )
        else:
            resultado["mensajes_ok"].append(
                f"✅ [{nombre_hoja}] {n_filas:,} filas (≥ {min_filas:,})"
            )

        resultado["detalles"]["volumen"][nombre_hoja] = {
            "n_filas": n_filas,
            "min_esperado": min_filas,
        }

    # ------------------------------------------------------------------------
    # b) CRUCES — sample de IDs entre hojas
    # ------------------------------------------------------------------------
    # Para acelerar, leemos solo la columna de cruce de cada hoja involucrada.
    cache_columnas: Dict[Tuple[str, str], pd.Series] = {}

    def _cargar_columna(hoja: str, columna: str) -> Optional[pd.Series]:
        """Carga una columna de una hoja, con caché para evitar relecturas."""
        clave = (hoja, _normalizar(columna))
        if clave in cache_columnas:
            return cache_columnas[clave]

        ruta_hoja = _ruta_de_fichero(CONTRATO_EXCEL[hoja]["fichero"])
        try:
            # Primero leemos cabecera para encontrar el nombre real
            df_cab = pd.read_excel(ruta_hoja, sheet_name=hoja, nrows=0)
            nombre_real = _existe_columna_case_insensitive(
                list(df_cab.columns), columna
            )
            if nombre_real is None:
                return None

            df_col = pd.read_excel(
                ruta_hoja, sheet_name=hoja, usecols=[nombre_real]
            )
            serie = df_col[nombre_real].dropna()
            cache_columnas[clave] = serie
            return serie
        except Exception:
            return None

    for cruce in CRUCES_ESPERADOS:
        origen = cruce["origen"]
        destino = cruce["destino"]
        columna = cruce["columna"]
        umbral = cruce["umbral_pct"]

        serie_origen = _cargar_columna(origen, columna)
        serie_destino = _cargar_columna(destino, columna)

        if serie_origen is None or serie_destino is None:
            resultado["mensajes_error"].append(
                f"⚠️  Cruce {origen}→{destino} por {columna!r}: "
                f"no se ha podido cargar la columna"
            )
            continue

        # Sample de IDs únicos del origen
        ids_origen_unicos = serie_origen.unique()
        n_total_origen = len(ids_origen_unicos)
        if n_total_origen == 0:
            continue

        sample = pd.Series(ids_origen_unicos).sample(
            n=min(sample_size, n_total_origen),
            random_state=42,
        )

        # ¿Cuántos están en destino?
        set_destino = set(serie_destino.unique())
        encontrados = sum(1 for x in sample if x in set_destino)
        pct_match = 100.0 * encontrados / len(sample)

        cruce_detalle = {
            "origen": origen,
            "destino": destino,
            "columna": columna,
            "sample": int(len(sample)),
            "encontrados": int(encontrados),
            "pct_match": round(pct_match, 2),
            "umbral_pct": umbral,
        }
        resultado["detalles"]["cruces"][f"{origen}→{destino}"] = cruce_detalle

        if pct_match >= umbral:
            resultado["mensajes_ok"].append(
                f"✅ Cruce {origen}→{destino} por {columna!r}: "
                f"{pct_match:.1f}% de match (≥{umbral}%)"
            )
        else:
            resultado["mensajes_error"].append(
                f"⚠️  Cruce {origen}→{destino} por {columna!r}: "
                f"solo {pct_match:.1f}% de match (esperado ≥{umbral}%)"
            )

    return resultado


# ============================================================================
# ORQUESTADOR — Ejecuta todas las validaciones
# ============================================================================

def ejecutar_validacion_completa(
    detener_si_bloqueante: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta N1-N5 en orden y devuelve resultado consolidado.

    Parameters
    ----------
    detener_si_bloqueante : bool
        Si True (default), detiene la cadena al primer fallo de N1, N2 o N3.
        Si False, ejecuta los 5 niveles igualmente (útil para diagnóstico).
    verbose : bool
        Si True, imprime progreso por consola.

    Returns
    -------
    Dict con:
      - resultados : list de los 5 dicts (N1-N5)
      - bloqueante_fallido : bool — algún N1/N2/N3 falló
      - todos_ok : bool — todos pasaron sin warnings
      - resumen_corto : str — texto para imprimir en consola
    """
    resultados: List[Dict[str, Any]] = []
    bloqueante_fallido = False

    pasos = [
        ("N1", validar_n1_existencia),
        ("N2", validar_n2_hojas),
        ("N3", validar_n3_columnas),
        ("N4", validar_n4_tipos),
        ("N5", validar_n5_volumen_y_cruces),
    ]

    for nombre, funcion in pasos:
        if verbose:
            print(f"  → Ejecutando {nombre}...")

        # Si se ha pedido detener y un bloqueante anterior falló, saltar
        if detener_si_bloqueante and bloqueante_fallido and nombre in ("N4", "N5"):
            if verbose:
                print(f"    (saltado por fallo bloqueante anterior)")
            resultados.append({
                "nivel": nombre,
                "titulo": f"{nombre} (no ejecutado)",
                "tipo": "warning",
                "pasa": None,  # None = no ejecutado
                "mensajes_ok": [],
                "mensajes_error": [
                    f"{nombre} no se ha ejecutado por fallo en validación bloqueante anterior"
                ],
                "detalles": {},
            })
            continue

        try:
            res = funcion()
        except Exception as e:
            res = {
                "nivel": nombre,
                "titulo": f"{nombre} (error de ejecución)",
                "tipo": "bloqueante",
                "pasa": False,
                "mensajes_ok": [],
                "mensajes_error": [f"❌ Error inesperado en {nombre}: {e}"],
                "detalles": {"excepcion": str(e)},
            }

        resultados.append(res)

        if res["tipo"] == "bloqueante" and not res["pasa"]:
            bloqueante_fallido = True
            if verbose:
                print(f"    ❌ {nombre} FALLÓ (bloqueante)")

            if detener_si_bloqueante:
                # Continuamos con los demás bloqueantes pero no con warnings
                pass
        else:
            if verbose and res["pasa"] is True:
                print(f"    ✅ {nombre} OK")
            elif verbose and res["mensajes_error"]:
                print(f"    ⚠️  {nombre} con avisos")

    todos_ok = all(
        r.get("pasa") is True and not r.get("mensajes_error")
        for r in resultados
    )

    # Resumen corto en formato lista
    lineas_resumen = []
    for r in resultados:
        icono = "✅" if r.get("pasa") is True else (
            "❌" if r.get("pasa") is False else "⏸️"
        )
        n_ok = len(r.get("mensajes_ok", []))
        n_err = len(r.get("mensajes_error", []))
        lineas_resumen.append(
            f"  {icono} {r['nivel']} ({r['titulo']}): {n_ok} OK, {n_err} avisos/errores"
        )

    return {
        "resultados": resultados,
        "bloqueante_fallido": bloqueante_fallido,
        "todos_ok": todos_ok,
        "resumen_corto": "\n".join(lineas_resumen),
    }
