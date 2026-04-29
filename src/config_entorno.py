# ============================================================================
# CONFIG_ENTORNO.PY — Entorno y rutas del proyecto
# ============================================================================
# TFM: Predicción de Abandono Universitario
#
# Este archivo es la FUENTE ÚNICA de verdad para:
#   1. Detectar desde dónde se ejecuta el proyecto (Colab, Kaggle, Local)
#   2. Definir TODAS las rutas de archivos y carpetas
#   3. Definir el mapeo de hojas del Excel original
#
# ¿Cómo funciona la detección de entorno?
#   - Google Colab: busca en Google Drive la carpeta AU_UJI
#   - Kaggle: busca en /kaggle/working/
#   - Local: sube niveles desde la carpeta actual hasta encontrar src/
#
# IMPORTANTE: Si renombras carpetas de datos, SOLO hay que cambiar aquí.
# Todos los notebooks importan estas rutas vía src/config.py.
# ============================================================================

from pathlib import Path
from typing import Tuple
import os
import sys


# ============================================================================
# 1. DETECCIÓN DE ENTORNO
# ============================================================================

def detectar_entorno() -> Tuple[Path, str]:
    """
    Detecta el entorno de ejecución y devuelve la ruta base del proyecto.

    Returns
    -------
    Tuple[Path, str]
        (ruta_base, nombre_entorno)
        Ejemplo: (Path('/home/user/AU_UJI'), 'Local')

    Entornos soportados
    -------------------
    - Google Colab: /content/drive/MyDrive/AU_UJI
    - Kaggle: /kaggle/working/AU_UJI
    - Azure Notebooks: /home/azureuser/AU_UJI
    - Local (Windows/Mac/Linux): busca hacia arriba hasta encontrar src/
    """
    # --- Google Colab ---
    if 'google.colab' in sys.modules:
        return Path('/content/drive/MyDrive/AU_UJI'), 'Colab'

    # --- Kaggle ---
    if os.path.exists('/kaggle'):
        return Path('/kaggle/working/AU_UJI'), 'Kaggle'

    # --- Azure Notebooks ---
    if 'AZURE_NOTEBOOKS' in os.environ:
        return Path('/home/azureuser/AU_UJI'), 'Azure'

    # --- Local ---
    # Sube niveles desde la carpeta actual hasta encontrar la que tiene src/
    current = Path.cwd()
    for parent in current.parents:
        if (parent / 'src').exists():
            return parent, 'Local'

    # Fallback: si no encuentra src/, usa la carpeta actual
    return current, 'Local'


BASE_PATH, ENTORNO = detectar_entorno()


# ============================================================================
# 2. RUTAS DEL PROYECTO
# ============================================================================
# Estructura de carpetas de datos:
#
#   data/
#   ├── 00_raw/          ← Excel originales (datos de la universidad)
#   ├── 01_interim/      ← Parquets individuales (1 por hoja, Fase 1)
#   ├── 02_processed/    ← df_alumno.parquet (dataset unificado, Fase 1)
#   ├── 03_features/     ← df_expediente_features.parquet (Fase 3)
#   ├── automl/          ← Dataset y resultados AutoML (Fase 3.5)
#   ├── 05_modelado/     ← X_test, y_test, modelos .pkl, resultados_maestro (Fase 5)
#   └── 06_evaluacion/   ← meta_test, meta_test_app, metricas_modelo.json (Fase 6)

# --- Datos ---
RUTA_RAW = BASE_PATH / 'data' / '00_raw'
RUTA_INTERIM = BASE_PATH / 'data' / '01_interim'
RUTA_PROCESSED = BASE_PATH / 'data' / '02_processed'
RUTA_FEATURES = BASE_PATH / 'data' / '03_features'
RUTA_AUTOML = BASE_PATH / 'data' / 'automl'
RUTA_MODELADO = BASE_PATH / 'data' / '05_modelado'
RUTA_EVALUACION = BASE_PATH / 'data' / '06_evaluacion'

# --- Documentación y HTML ---
RUTA_HTML = BASE_PATH / 'docs' / 'html'
RUTA_EDA = BASE_PATH / 'docs' / 'eda'
RUTA_REPORTES = BASE_PATH / 'docs' / 'reportes'
RUTA_ASSETS = BASE_PATH / 'docs' / 'assets'
RUTA_DOCS = BASE_PATH / 'docs'

# --- Código y notebooks ---
RUTA_SRC = BASE_PATH / 'src'
RUTA_TESTS = BASE_PATH / 'tests'
RUTA_NOTEBOOKS = BASE_PATH / 'notebooks'

# --- Archivos específicos ---
EXCEL_PRINCIPAL = RUTA_RAW / 'datos_proyecto_sin_preinscrip.xlsx'
EXCEL_PREINSCRIPCION = RUTA_RAW / 'preinscripcion_si.xlsx'

DATASET_FINAL_PARQUET = RUTA_PROCESSED / 'df_alumno.parquet'
DATASET_FINAL_CSV = RUTA_PROCESSED / 'df_alumno.csv'

# Dataset de producción para modelado supervisado
# Generado por Fase 3 (f3_m05_dataset_modelado.ipynb) tras auditoría de leakage
# 33.621 expedientes × 24 features + target `abandono`
# Ubicación definitiva: data/03_features/ (movido desde data/automl/ — ver Chat 3)
# FUENTE ÚNICA: todos los notebooks de Fase 5, AutoML y App deben usar esta constante
DATASET_MODELADO = RUTA_FEATURES / 'dataset_final_tfm.parquet'

# Alias de compatibilidad — eliminar cuando Fase 3 y AutoML estén actualizados
# TODO Chat 3: mover fichero físico de data/automl/ a data/03_features/
# TODO Chat 4: actualizar notebooks AutoML para usar DATASET_MODELADO
# TODO Chat 8: actualizar config_app.py para usar DATASET_MODELADO
DATASET_MODELADO_LEGACY = RUTA_AUTOML / 'dataset_final_tfm.parquet'

ARCHIVO_LOG = BASE_PATH / 'logs' / 'tfm_abandono.log'


# ============================================================================
# 3. MAPEO DE HOJAS DEL EXCEL
# ============================================================================
# El Excel principal tiene 8 hojas con nombres "oficiales" (de la universidad).
# Internamente usamos nombres más cortos y descriptivos.
#
# Ejemplo: La hoja "Nac-Sexo_Nacionalidad" se convierte en el parquet
#          "demograficos.parquet" en data/01_interim/

MAPEO_HOJAS = {
    'Titulaciones': 'titulaciones',
    'Recibos': 'recibos',
    'Domicilios': 'domicilios',
    'Expedientes': 'expedientes',
    'Nac-Sexo_Nacionalidad': 'demograficos',
    'Circunstancias': 'becas',
    'Trabajo': 'trabajo',
    'Notas': 'notas',
}

# Listas derivadas (para iterar cómodamente en los notebooks)
HOJAS_EXCEL_PRINCIPAL = list(MAPEO_HOJAS.keys())
NOMBRES_PARQUET = list(MAPEO_HOJAS.values())


# ============================================================================
# 4. RAMAS DE CONOCIMIENTO — NOMBRES Y COLORES
# ============================================================================
# Fuente única de verdad para abreviaturas, nombres completos y colores de rama.
# Usados en notebooks de todas las fases y en la app Streamlit (config_app.py
# los importa desde aquí para no duplicar).
#
# Abreviaturas usadas en los datos: SO, TE, SA, HU, EX

RAMAS_NOMBRES = {
    "SO": "Ciencias Sociales y Jurídicas",
    "TE": "Ingeniería y Arquitectura",
    "SA": "Ciencias de la Salud",
    "HU": "Artes y Humanidades",
    "EX": "Ciencias Experimentales",
}

# Colores por rama — paleta inspirada en colores de togas doctorales españolas,
# adaptados para legibilidad en pantalla. Ningún color coincide con los de
# riesgo (verde/amarillo/rojo) para evitar confusión semántica.
#
# Correspondencia toga → pantalla:
#   Ciencias Sociales y Jurídicas : toga amarillo/oro   → ámbar dorado   #d97706
#   Ingeniería y Arquitectura     : toga marrón         → naranja tostado #c2410c
#   Ciencias de la Salud          : toga amarillo limón → azul cyan       #0891b2
#   Artes y Humanidades           : toga morado         → violeta medio   #7c3aed
#   Ciencias Experimentales       : toga azul marino    → azul profundo   #1d4ed8
COLORES_RAMAS = {
    "Ciencias Sociales y Jurídicas": "#d97706",  # ámbar dorado   (toga: amarillo/oro)
    "Ingeniería y Arquitectura":     "#c2410c",  # naranja tostado (toga: marrón)
    "Ciencias de la Salud":          "#0891b2",  # azul cyan      (toga: amarillo limón)
    "Artes y Humanidades":           "#7c3aed",  # violeta medio  (toga: morado)
    "Ciencias Experimentales":       "#1d4ed8",  # azul profundo  (toga: azul marino)
}

# Colores directamente por abreviatura (para gráficos matplotlib)
COLORES_RAMAS_ABR = {
    abr: COLORES_RAMAS[nombre]
    for abr, nombre in RAMAS_NOMBRES.items()
}

# Colores por sexo — convención visual estándar alineada con ODS 5.
# Independientes de COLORES_RAMAS para que un cambio en la paleta de ramas
# no altere los colores de sexo involuntariamente.
COLORES_SEXO = {
    "Mujer":  "#db2777",  # rosa medio  — convención universal, ODS 5
    "Hombre": "#2563eb",  # azul medio  — convención universal
    "Total":  "#475569",  # gris pizarra — neutro para línea agregada
}


# ============================================================================
# 5. FEATURES DEL MODELO — CLASIFICACIÓN POR TIPO
# ============================================================================
# 27 features de X_test_prep (24 originales + 3 indicadores _missing).
# Definidas aquí para que todos los notebooks las usen de forma consistente
# sin riesgo de incluir columnas de contexto (rama, titulacion, tipo, etc.)
# que se añaden después y causarían TypeError al llamar .mean().

# Features numéricas del modelo (las que acepta predict/SHAP/.mean())
FEATURES_NUM_MODELO = [
    'cred_superados_anio_1er', 'cupo', 'pais_nombre', 'provincia',
    'universidad_origen', 'edad_entrada', 'anios_gap', 'nota_1er_anio',
    'nota_acceso', 'nota_selectividad', 'via_acceso', 'rama',
    'n_anios_beca', 'anios_sin_beca', 'situacion_laboral', 'n_anios_trabajando',
    'max_pagos', 'orden_preferencia', 'cred_repetidos', 'tasa_repeticion',
    'n_anios_sin_notas', 'tasa_abandono_titulacion', 'sexo',
    'indicador_interrupcion', 'nota_1er_anio_missing',
    'nota_acceso_missing', 'nota_selectividad_missing',
]

# Features de contexto recuperadas por join (NO están en X_test_prep)
FEATURES_CONTEXTO = ['titulacion', 'rama_nombre', 'per_id_ficticio']

# Nombres legibles para gráficos (sin guiones bajos)
NOMBRES_LEGIBLES_FEATURES = {
    'cred_superados_anio_1er':  'Créditos superados 1er año',
    'cupo':                     'Cupo de acceso',
    'pais_nombre':              'País de origen',
    'provincia':                'Provincia',
    'universidad_origen':       'Universidad origen',
    'edad_entrada':             'Edad de entrada',
    'anios_gap':                'Años de gap',
    'nota_1er_anio':            'Nota 1er año',
    'nota_acceso':              'Nota de acceso',
    'nota_selectividad':        'Nota selectividad',
    'via_acceso':               'Vía de acceso',
    'rama':                     'Rama de conocimiento',
    'n_anios_beca':             'Años con beca',
    'anios_sin_beca':           'Años sin beca',
    'situacion_laboral':        'Situación laboral',
    'n_anios_trabajando':       'Años trabajando',
    'max_pagos':                'Máx. pagos por curso',
    'orden_preferencia':        'Orden de preferencia',
    'cred_repetidos':           'Créditos repetidos',
    'tasa_repeticion':          'Tasa de repetición',
    'n_anios_sin_notas':        'Años sin notas',
    'tasa_abandono_titulacion': 'Tasa abandono titulación',
    'sexo':                     'Sexo',
    'indicador_interrupcion':   'Interrupción formal',
    'nota_1er_anio_missing':    'Nota 1er año (ausente)',
    'nota_acceso_missing':      'Nota acceso (ausente)',
    'nota_selectividad_missing':'Nota selectividad (ausente)',
}
