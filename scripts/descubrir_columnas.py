# ============================================================================
# DESCUBRIR_COLUMNAS.PY — Script PUNTUAL (de un solo uso)
# ============================================================================
# Propósito: leer los 2 Excel originales del proyecto y volcar a consola:
#   - Nombre de cada hoja
#   - Lista de columnas
#   - Tipos de datos detectados (dtype)
#   - Número de filas
#   - Muestra de 2 primeras filas (para entender el contenido)
#
# Salida: TODO por consola (no genera ficheros).
#
# Uso:
#   conda activate tfm_abandono
#   cd C:\FF\AU_UJI_v2
#   python descubrir_columnas.py
#
# Después: copiar el output completo y pegarlo en el chat.
#
# ⚠️ IMPORTANTE: este script NO modifica nada. Solo LEE los Excel.
# ⚠️ Una vez usado, se puede borrar (no forma parte del proyecto).
# ============================================================================

import sys
from pathlib import Path

# --- ROOT robusto: sube niveles hasta encontrar src/ ---
# Patrón estándar del proyecto V2
ROOT = Path(__file__).resolve().parent
while not (ROOT / 'src').exists():
    if ROOT.parent == ROOT:
        # Llegamos a la raíz del disco sin encontrar src/
        raise RuntimeError("No se ha encontrado la carpeta src/ subiendo niveles")
    ROOT = ROOT.parent

# Inserta ROOT (no ROOT/'src') para poder hacer 'from src.config import ...'
sys.path.insert(0, str(ROOT))

# --- Imports del proyecto (constantes ya definidas, no inventar) ---
from src.config_entorno import (
    EXCEL_PRINCIPAL,
    EXCEL_PREINSCRIPCION,
    HOJAS_EXCEL_PRINCIPAL,
)

import pandas as pd


# ============================================================================
# Función auxiliar: imprimir la información de una hoja
# ============================================================================

def inspeccionar_hoja(ruta_excel: Path, nombre_hoja: str) -> None:
    """
    Lee una hoja de un Excel y vuelca su estructura a consola.

    Parameters
    ----------
    ruta_excel : Path
        Ruta al fichero .xlsx
    nombre_hoja : str
        Nombre exacto de la hoja a leer (case-sensitive)

    Notes
    -----
    Si la hoja no existe o falla la lectura, muestra el error pero NO aborta
    (así el script termina de inspeccionar todas las demás hojas).
    """
    print(f"\n{'='*78}")
    print(f"📑 HOJA: '{nombre_hoja}'  (en {ruta_excel.name})")
    print(f"{'='*78}")

    try:
        # nrows=5 → solo 5 filas para muestrear (rapidez y privacidad mínima)
        df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja, nrows=5)
    except Exception as e:
        print(f"❌ ERROR al leer la hoja: {e}")
        return

    # --- Resumen estructural ---
    print(f"\n  • Nº columnas detectadas: {len(df.columns)}")
    print(f"  • Filas leídas (muestra): {len(df)}")

    # --- Lista de columnas con dtype ---
    print(f"\n  📋 COLUMNAS (nombre → dtype):")
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        print(f"     - {col!r}  →  {dtype_str}")

    # --- Muestra de las 2 primeras filas (transpuesta para legibilidad) ---
    print(f"\n  🔍 MUESTRA (2 primeras filas):")
    try:
        # to_string evita truncado de pandas; .head(2).T transpone para ver mejor
        print(df.head(2).T.to_string(max_colwidth=40))
    except Exception as e:
        print(f"     (no se pudo mostrar muestra: {e})")


# ============================================================================
# Función auxiliar: contar filas totales sin cargar todo en memoria
# ============================================================================

def contar_filas_totales(ruta_excel: Path, nombre_hoja: str) -> int:
    """
    Cuenta filas totales de una hoja leyendo solo la columna 0.
    Más rápido que cargar el dataframe completo.
    """
    try:
        # usecols=[0] → solo lee la primera columna (mucho más rápido)
        df_count = pd.read_excel(ruta_excel, sheet_name=nombre_hoja, usecols=[0])
        return len(df_count)
    except Exception:
        return -1


# ============================================================================
# MAIN — Ejecución principal
# ============================================================================

def main() -> None:
    """
    Inspecciona los 2 Excel del proyecto y vuelca toda la información necesaria
    para construir el contrato de validación sin inventar nombres de columnas.
    """
    print("\n" + "█"*78)
    print("  DESCUBRIDOR DE COLUMNAS — Excel originales del proyecto AU_UJI_v2")
    print("█"*78)
    print(f"\n  ROOT detectado: {ROOT}")
    print(f"  Excel principal:      {EXCEL_PRINCIPAL.name}")
    print(f"  Excel preinscripción: {EXCEL_PREINSCRIPCION.name}")

    # --- Verificar existencia ---
    if not EXCEL_PRINCIPAL.exists():
        print(f"\n❌ NO EXISTE: {EXCEL_PRINCIPAL}")
        return
    if not EXCEL_PREINSCRIPCION.exists():
        print(f"\n❌ NO EXISTE: {EXCEL_PREINSCRIPCION}")
        return

    print(f"\n✅ Ambos Excel existen, procedo a inspeccionar...\n")

    # ========================================================================
    # PARTE 1 — Excel principal (8 hojas conocidas)
    # ========================================================================
    print("\n" + "▓"*78)
    print(f"  EXCEL 1 DE 2: {EXCEL_PRINCIPAL.name}")
    print("▓"*78)

    # Primero verificamos qué hojas existen REALMENTE en el fichero
    # (puede que haya hojas extra no esperadas, o falten algunas)
    try:
        xls = pd.ExcelFile(EXCEL_PRINCIPAL)
        hojas_reales = xls.sheet_names
        print(f"\n  📚 Hojas encontradas en el fichero: {len(hojas_reales)}")
        for h in hojas_reales:
            n_filas = contar_filas_totales(EXCEL_PRINCIPAL, h)
            marca = "✅" if h in HOJAS_EXCEL_PRINCIPAL else "⚠️ EXTRA"
            print(f"     {marca}  {h!r}  ({n_filas} filas)")

        # Detectar hojas esperadas que faltan
        faltan = set(HOJAS_EXCEL_PRINCIPAL) - set(hojas_reales)
        if faltan:
            print(f"\n  ❌ HOJAS ESPERADAS QUE FALTAN: {faltan}")
    except Exception as e:
        print(f"\n❌ ERROR abriendo el fichero: {e}")
        return

    # Inspeccionar cada hoja esperada (las del MAPEO_HOJAS)
    for hoja in HOJAS_EXCEL_PRINCIPAL:
        if hoja in hojas_reales:
            inspeccionar_hoja(EXCEL_PRINCIPAL, hoja)

    # ========================================================================
    # PARTE 2 — Excel de preinscripción (1 hoja)
    # ========================================================================
    print("\n\n" + "▓"*78)
    print(f"  EXCEL 2 DE 2: {EXCEL_PREINSCRIPCION.name}")
    print("▓"*78)

    try:
        xls_pre = pd.ExcelFile(EXCEL_PREINSCRIPCION)
        hojas_pre = xls_pre.sheet_names
        print(f"\n  📚 Hojas encontradas: {len(hojas_pre)} → {hojas_pre}")

        for h in hojas_pre:
            n_filas = contar_filas_totales(EXCEL_PREINSCRIPCION, h)
            print(f"     • {h!r}  ({n_filas} filas)")
            inspeccionar_hoja(EXCEL_PREINSCRIPCION, h)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

    # --- Cierre ---
    print("\n\n" + "█"*78)
    print("  ✅ INSPECCIÓN COMPLETADA")
    print("█"*78)
    print("\n  📋 SIGUIENTE PASO:")
    print("     1. Copiar TODO el output anterior (desde el primer █ hasta aquí)")
    print("     2. Pegarlo en el chat")
    print("     3. Construiremos el contrato sin inventar nombres\n")


if __name__ == "__main__":
    main()
