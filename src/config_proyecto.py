# ============================================================================
# CONFIG_PROYECTO.PY — Información general del proyecto
# ============================================================================
# TFM: Predicción de Abandono Universitario
#
# Este archivo centraliza toda la información "de identidad" del proyecto:
#   - Autora y contacto
#   - Repositorio GitHub
#   - Versión de los datos
#   - Paleta de colores corporativa
#   - Configuración de las fases del proyecto
#
# ¿Por qué existe este archivo?
#   Antes esta información estaba repartida en 3 archivos distintos
#   (config_autora.py, utils/config.py, constantes.py), lo que provocaba
#   duplicaciones y riesgo de inconsistencias. Ahora hay UNA SOLA fuente.
#
# ¿Quién lo importa?
#   - src/config.py (hub central) lo reexporta para que los notebooks
#     puedan hacer: from src.config import AUTORA, GITHUB_REPO, etc.
#   - src/html/render.py lo usa para generar el footer de las páginas HTML
# ============================================================================


# ============================================================================
# 1. AUTORA Y CONTACTO
# ============================================================================
# Si cambias de universidad o de email, solo hay que tocarlo aquí.

AUTORA = "María José Morte"
EMAIL_UOC = "mjmorteruiz@uoc.edu"
EMAIL_UJI = "morte@uji.es"


# ============================================================================
# 2. REPOSITORIO GITHUB Y APP DESPLEGADA
# ============================================================================
# Se usa en los HTML generados para enlazar al notebook original
# y a la aplicación Streamlit desplegada en Streamlit Cloud.
#
# NOTA V2 — AU_UJI Dinámico (actualizado 2026-05-04):
# Este proyecto es la versión 2 (dinámica) del TFM. La V1 estable sigue
# en https://tfm-abandono.streamlit.app y https://github.com/mortemj/AU_UJI
# Las URLs de aquí abajo apuntan SIEMPRE a V2.

GITHUB_REPO = "https://github.com/mortemj/AU_UJI_v2"
GITHUB_NOTEBOOKS = f"{GITHUB_REPO}/blob/main/notebooks"
GITHUB_PAGES = "https://mortemj.github.io/AU_UJI_v2/"

URL_APP_STREAMLIT = "https://tfm-abandono-dinamico.streamlit.app/"


# ============================================================================
# 3. VERSIÓN DE LOS DATOS
# ============================================================================
# Se guarda como metadato en los parquets generados.

VERSION_DATOS = "1.0.0"


# ============================================================================
# 4. PALETA DE COLORES CORPORATIVA
# ============================================================================
# Colores consistentes en todo el proyecto: gráficos matplotlib, HTML, CSS.
#
# Uso en notebooks:
#   from src.config import COLORES
#   plt.bar(x, y, color=COLORES.PRINCIPAL)

class ColoresTFM:
    """Paleta de colores del proyecto."""

    # Color principal (azul UJI)
    PRINCIPAL = "#3182ce"

    # Escala secuencial (de claro a oscuro) — para heatmaps, gradientes
    SECUENCIAL = [
        "#ebf8ff", "#bee3f8", "#90cdf4", "#63b3ed", "#4299e1",
        "#3182ce", "#2b6cb0", "#2c5282", "#1a365d"
    ]

    # Colores categóricos (para gráficos con varias categorías)
    CATEGORICA = ["#3182ce", "#e53e3e", "#38a169", "#ed8936", "#805ad5"]

    # Estados
    OK = "#38a169"       # Verde — todo correcto
    ALERTA = "#ed8936"   # Naranja — advertencia
    ERROR = "#e53e3e"    # Rojo — error
    PENDIENTE = "#a0aec0" # Gris — fase aún no ejecutada


# Instancia global para importar directamente
COLORES = ColoresTFM


# ============================================================================
# 5. CONFIGURACIÓN DE FASES
# ============================================================================
# Metadatos de cada fase del proyecto. Se usa en HTML y en el runner.

FASES_CONFIG = {
    "fase1": {
        "nombre": "Transformación",
        "descripcion": "Limpieza y preparación de datos"
    },
    "fase2": {
        "nombre": "EDA Datos Originales",
        "descripcion": "Análisis Exploratorio de Datos originales"
    },
    "fase3": {
        "nombre": "Feature Engineering",
        "descripcion": "Ingeniería de variables"
    },
    "fase4": {
        "nombre": "EDA Final",
        "descripcion": "Análisis del dataset de features"
    },
    "fase5": {
        "nombre": "Modelado",
        "descripcion": "Entrenamiento de modelos"
    },
    "fase6": {
        "nombre": "Evaluación",
        "descripcion": "Evaluación y comparación de modelos"
    },
    "fase7": {
        "nombre": "Aplicación",
        "descripcion": "Dashboard y despliegue"
    },
}
