# ============================================================================
# SRC/HTML/__INIT__.PY — Exports del módulo HTML
# ============================================================================
# TFM: Predicción de Abandono Universitario
#
# Este módulo genera las páginas HTML del proyecto:
#   - navegacion.py → Estructura de fases/módulos y navegación
#   - components.py → Componentes HTML reutilizables (KPIs, tarjetas, tablas)
#   - render.py → Renderizado final con Jinja2
#   - templates/ → Plantillas HTML (base.html, reporte.html)
#
# Uso típico desde un notebook:
#   from src.html import render_base_html, generar_kpis_html, guardar_html
# ============================================================================

from .navegacion import (
    FASES,
    extraer_titulo_de_fichero,
    extraer_fase_de_fichero,
    extraer_modulo_de_fichero,
    obtener_subtitulo_fase,
    obtener_fases_para_nav,
    obtener_modulos_para_nav,
    obtener_info_fase,
    obtener_info_modulo,
    generar_html_nav_fases,
    generar_html_nav_modulos,
    generar_html_navegacion_completa,
)

from .components import (
    get_header_html,
    get_footer_html,
    get_kpi_html,
    generar_kpis_html,
    generar_tarjeta_html,
    generar_tarjetas_html,
    generar_seccion_html,
    generar_tabla_html,
    generar_tabla_con_tooltip,
    generar_mensaje_html,
    guardar_html,
)

from .render import (
    render_base_html,
    render_pagina_desde_fichero,
    render_pagina,
)

__all__ = [
    # Navegación
    'FASES',
    'extraer_titulo_de_fichero',
    'extraer_fase_de_fichero',
    'extraer_modulo_de_fichero',
    'obtener_subtitulo_fase',
    'obtener_fases_para_nav',
    'obtener_modulos_para_nav',
    'obtener_info_fase',
    'obtener_info_modulo',
    'generar_html_nav_fases',
    'generar_html_nav_modulos',
    'generar_html_navegacion_completa',

    # Componentes
    'get_header_html',
    'get_footer_html',
    'get_kpi_html',
    'generar_kpis_html',
    'generar_tarjeta_html',
    'generar_tarjetas_html',
    'generar_seccion_html',
    'generar_tabla_html',
    'generar_tabla_con_tooltip',
    'generar_mensaje_html',
    'guardar_html',

    # Render
    'render_base_html',
    'render_pagina_desde_fichero',
    'render_pagina',
]
