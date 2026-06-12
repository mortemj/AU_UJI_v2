# ============================================================================
# RENDER.PY — Renderizado de páginas HTML con Jinja2
# ============================================================================
# TFM: Predicción de Abandono Universitario
#
# Este módulo expone TRES funciones para generar páginas HTML del proyecto.
# Elige la que mejor encaje con tu caso:
#
#   1. render_base_html(titulo, subtitulo, nav_fases, nav_modulos, contenido, ...)
#      → Nivel bajo. Control total. Tú construyes título, subtítulo y navegación.
#        Usada en los notebooks de la Fase AutoML (fautoml_m01 … fautoml_m06)
#        donde la navegación se genera manualmente con generar_html_navegacion_completa.
#        Devuelve el HTML como string — hay que guardarlo con .write_text().
#
#   2. render_pagina_desde_fichero(nombre_fichero, contenido, carpeta_notebook, ...)
#      → Nivel medio. Infiere título, fase y módulo del nombre del fichero
#        siguiendo la convención f5_m01_preparacion.ipynb → "Preparacion", fase5, m01.
#        Devuelve el HTML como string — hay que guardarlo con .write_text().
#
#   3. render_pagina(nombre_fichero, contenido, ruta_salida, carpeta_notebook, ...)  ← RECOMENDADA
#      → Nivel alto. Igual que (2) pero además guarda el fichero directamente.
#        Uso estándar desde Fase 5 en adelante. Una sola línea en el notebook:
#            render_pagina('f5_m01_preparacion.ipynb', secciones_html, RUTA_HTML_SALIDA)
#
# ============================================================================

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime

# --- Importar datos del proyecto ---
# Antes esto venía de src.utils.config (eliminado por duplicación).
# Ahora viene del ÚNICO sitio correcto: src.config_proyecto
try:
    from src.config_proyecto import AUTORA, EMAIL_UOC, EMAIL_UJI
    from src.config_proyecto import GITHUB_REPO, GITHUB_NOTEBOOKS
except ImportError:
    # Fallback por si se ejecuta fuera del proyecto
    AUTORA = "María José Morte"
    EMAIL_UOC = "mjmorteruiz@uoc.edu"
    EMAIL_UJI = "morte@uji.es"
    GITHUB_REPO = "https://github.com/mortemj/AU_UJI"
    GITHUB_NOTEBOOKS = f"{GITHUB_REPO}/blob/master/notebooks"

from .navegacion import (
    extraer_titulo_de_fichero,
    extraer_fase_de_fichero,
    extraer_modulo_de_fichero,
    obtener_subtitulo_fase,
    generar_html_navegacion_completa
)
from .components import get_header_html, get_footer_html


# ============================================================================
# CONFIGURACIÓN DE JINJA2
# ============================================================================
# La carpeta templates/ está al lado de este archivo: src/html/templates/

TEMPLATES_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True
)


# ============================================================================
# 1. FUNCIÓN DE NIVEL BAJO — control total
# ============================================================================
# Cuándo usarla: cuando necesitas título, subtítulo o navegación personalizados
# que no se pueden inferir del nombre del fichero. Actualmente en uso en:
#   · fautoml_m01_baselines.ipynb … fautoml_m06_comparativa.ipynb
# Devuelve str. Guarda con: ruta.write_text(html, encoding='utf-8')
# ============================================================================

def render_base_html(
    titulo: str,
    subtitulo: str,
    nav_fases: str,
    nav_modulos: str,
    contenido: str,
    icono: str = '',
    estilos_adicionales: str = '',
    scripts_adicionales: str = '',
    ruta_assets: str = '../../assets',
    notebook_nombre: str = None,
    notebook_carpeta: str = None
) -> str:
    """
    Renderiza una página HTML completa usando la plantilla base.html.

    Parameters
    ----------
    titulo : str
        Título del módulo (ej: "📊 Dashboard Fase 1")
    subtitulo : str
        Subtítulo con fase (ej: "Fase 1: Transformación | TFM")
    nav_fases : str
        HTML de la navegación principal de fases (generado por navegacion.py)
    nav_modulos : str
        HTML de la navegación de módulos (generado por navegacion.py)
    contenido : str
        HTML del contenido principal de la página
    icono : str, optional
        Emoji del módulo
    estilos_adicionales : str, optional
        CSS extra para esta página
    scripts_adicionales : str, optional
        JavaScript extra para esta página
    ruta_assets : str, optional
        Ruta relativa a la carpeta de assets (logos)
    notebook_nombre : str, optional
        Nombre del notebook (ej: 'f1_m05_dashboard.ipynb')
    notebook_carpeta : str, optional
        Carpeta del notebook (ej: 'fase1_transformacion')

    Returns
    -------
    str
        HTML completo listo para guardar en archivo
    """
    template = env.get_template("base.html")

    # Construir URLs del notebook
    notebook_github_url = None
    notebook_local_url = None
    if notebook_nombre and notebook_carpeta:
        notebook_github_url = f"{GITHUB_NOTEBOOKS}/{notebook_carpeta}/{notebook_nombre}"
        notebook_local_url = f"../../../notebooks/{notebook_carpeta}/{notebook_nombre}"

    html = template.render(
        titulo=titulo,
        icono=icono,
        subtitulo=subtitulo,
        nav_fases=nav_fases,
        nav_modulos=nav_modulos,
        contenido=contenido,
        estilos_adicionales=estilos_adicionales,
        scripts_adicionales=scripts_adicionales,
        ruta_assets=ruta_assets,
        autora=AUTORA,
        email_uoc=EMAIL_UOC,
        email_uji=EMAIL_UJI,
        notebook_github_url=notebook_github_url,
        notebook_local_url=notebook_local_url,
        github_repo=GITHUB_REPO,
        fecha_generacion=datetime.now().strftime("%d/%m/%Y")
    )

    return html


# ============================================================================
# 2. FUNCIÓN DE NIVEL MEDIO — infiere título y navegación del nombre del fichero
# ============================================================================
# Cuándo usarla: cuando el notebook sigue la convención de nombres del proyecto
# (f5_m01_preparacion.ipynb) pero quieres el HTML como string para procesarlo
# antes de guardarlo (ej: añadir metadatos, combinar con otro HTML, tests).
# Devuelve str. Guarda con: ruta.write_text(html, encoding='utf-8')
# ============================================================================

def render_pagina_desde_fichero(
    nombre_fichero: str,
    contenido: str,
    carpeta_notebook: str = None,
    ruta_assets: str = '../../assets',
    ruta_base_nav: str = '..'
) -> str:
    """
    Renderiza página HTML extrayendo título y fase del nombre del fichero.

    Útil cuando el notebook sigue la convención de nombres:
    f1_m03_reportes_clean.ipynb → título "Reportes Clean", fase1, módulo m03

    Parameters
    ----------
    nombre_fichero : str
        Nombre del fichero (ej: 'f1_m03_reportes_clean.ipynb')
    contenido : str
        HTML del contenido principal
    carpeta_notebook : str, optional
        Carpeta del notebook para enlace GitHub
    ruta_assets : str
        Ruta relativa a assets
    ruta_base_nav : str
        Ruta base para navegación

    Returns
    -------
    str
        HTML completo de la página
    """
    titulo    = extraer_titulo_de_fichero(nombre_fichero)
    fase_id   = extraer_fase_de_fichero(nombre_fichero)
    modulo_id = extraer_modulo_de_fichero(nombre_fichero)
    subtitulo = obtener_subtitulo_fase(fase_id)

    nav_fases, nav_modulos = generar_html_navegacion_completa(
        fase_activa=fase_id,
        modulo_activo=modulo_id,
        ruta_base=ruta_base_nav
    )

    return render_base_html(
        titulo=titulo,
        subtitulo=subtitulo,
        nav_fases=nav_fases,
        nav_modulos=nav_modulos,
        contenido=contenido,
        ruta_assets=ruta_assets,
        notebook_nombre=nombre_fichero,
        notebook_carpeta=carpeta_notebook
    )


# ============================================================================
# 3. FUNCIÓN DE NIVEL ALTO — infiere + guarda directamente  ← RECOMENDADA
# ============================================================================
# Cuándo usarla: uso estándar desde Fase 5 en adelante en todos los notebooks
# que siguen la convención de nombres. Una sola línea lo hace todo.
# Ejemplo en notebook:
#   render_pagina('f5_m01_preparacion.ipynb', secciones_html, RUTA_HTML_SALIDA)
# ============================================================================

def render_pagina(
    nombre_fichero: str,
    contenido: str,
    ruta_salida: Path,
    carpeta_notebook: str = None,
    ruta_assets: str = '../../assets',
    ruta_base_nav: str = '..'
) -> None:
    """
    Renderiza y guarda directamente la página HTML del módulo.

    Combina render_pagina_desde_fichero() + .write_text() en una sola llamada.
    Estándar recomendado para todos los notebooks de Fase 5 en adelante.

    Parameters
    ----------
    nombre_fichero : str
        Nombre del notebook siguiendo la convención del proyecto
        (ej: 'f5_m01_preparacion.ipynb')
    contenido : str
        HTML del contenido principal de la página
    ruta_salida : Path
        Ruta completa del fichero HTML de salida
        (ej: RUTA_HTML_FASE5 / 'm01_preparacion.html')
    carpeta_notebook : str, optional
        Carpeta del notebook para enlace GitHub (ej: 'fase5_modelado')
    ruta_assets : str, optional
        Ruta relativa a la carpeta de assets
    ruta_base_nav : str, optional
        Ruta base para la navegación entre módulos

    Returns
    -------
    None
        Guarda el fichero en ruta_salida. No devuelve nada.
    """
    html = render_pagina_desde_fichero(
        nombre_fichero   = nombre_fichero,
        contenido        = contenido,
        carpeta_notebook = carpeta_notebook,
        ruta_assets      = ruta_assets,
        ruta_base_nav    = ruta_base_nav
    )
    Path(ruta_salida).write_text(html, encoding='utf-8')
