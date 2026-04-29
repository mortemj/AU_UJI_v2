# ============================================================================
# CONFIG.PY — Hub central de configuración
# ============================================================================
# TFM: Predicción de Abandono Universitario
#
# Este archivo es el PUNTO DE ENTRADA de toda la configuración.
# No define nada propio: solo importa y reexporta desde los módulos
# especializados. Así los notebooks pueden hacer:
#
#   from src.config import RUTA_RAW, AUTORA, TABLAS_INFO, info_entorno
#
# sin tener que saber en qué archivo está cada cosa.
#
# ¿Por qué está organizado así?
#   - config_entorno.py → Rutas de archivos y detección de entorno
#   - config_proyecto.py → Autora, GitHub, versión, colores, fases
#   - config_datos.py → Diccionarios y constantes de los datos
#   - config_utils.py → Funciones de diagnóstico (info_entorno, etc.)
# ============================================================================

# --- Entorno y rutas ---
from .config_entorno import (
    BASE_PATH, ENTORNO,
    RUTA_RAW, RUTA_INTERIM, RUTA_PROCESSED,
    RUTA_FEATURES, RUTA_AUTOML,
    RUTA_MODELADO, RUTA_EVALUACION,
    RUTA_HTML, RUTA_EDA, RUTA_REPORTES, RUTA_ASSETS, RUTA_DOCS,
    RUTA_NOTEBOOKS, RUTA_TESTS,
    EXCEL_PRINCIPAL, EXCEL_PREINSCRIPCION,
    DATASET_FINAL_PARQUET, DATASET_FINAL_CSV,
    DATASET_MODELADO,           # Dataset de producción Fase 5 — data/03_features/
    DATASET_MODELADO_LEGACY,    # Alias temporal — data/automl/ — eliminar tras Chat 3/4/8
    ARCHIVO_LOG,
    MAPEO_HOJAS, HOJAS_EXCEL_PRINCIPAL, NOMBRES_PARQUET,
    # Ramas de conocimiento y features (refactor SRC↔APP)
    # Antes solo accesibles vía 'from .config_entorno import ...' en notebooks
    # Ahora reexportados aquí para uso unificado: 'from src.config import ...'
    RAMAS_NOMBRES,
    COLORES_RAMAS,
    COLORES_RAMAS_ABR,
    COLORES_SEXO,
    NOMBRES_LEGIBLES_FEATURES,
)

# --- Identidad del proyecto ---
from .config_proyecto import (
    AUTORA, EMAIL_UOC, EMAIL_UJI,
    GITHUB_REPO, GITHUB_NOTEBOOKS, GITHUB_PAGES,
    URL_APP_STREAMLIT,
    VERSION_DATOS,
    COLORES, ColoresTFM,
    FASES_CONFIG
)

# --- Diccionarios y constantes de datos ---
from .config_datos import (
    TABLAS_INFO,
    DICCIONARIO_COLUMNAS,
    DICCIONARIO_RAMAS,
    DICCIONARIO_FORMA_PAGO,
    VALORES_NULOS,
    CURSO_REFERENCIA,
    FECHA_REFERENCIA,
    VALORES_VACIOS,
    DICCIONARIO_CP_PROVINCIA,
    ETIQUETAS_VARIABLES,
    # Mapas de encoding — fuente única de verdad para M04a y config_app.py
    VIA_ACCESO_MAP,
    RAMA_MAP,
    SEXO_MAP,
    PROVINCIA_MAP,
    PAIS_NOMBRE_MAP,
    UNIVERSIDAD_ORIGEN_MAP,
    SITUACION_LABORAL_MAP,
    CUPO_MAP,
    EGRESADO_MAP,
    VIA_ACCESO_INV,
    RAMA_INV,
    SEXO_INV,
    SITUACION_LABORAL_INV,
    UNIVERSIDAD_ORIGEN_INV,
    UNIVERSIDAD_ORIGEN_NOMBRES,
)

# --- Funciones de diagnóstico ---
from .config_utils import (
    info_entorno,
    verificar_directorios,
    resumen_tablas,
    resumen_columnas,
    diagnostico_proyecto
)
