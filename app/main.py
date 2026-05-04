# =============================================================================
# main.py — navegación por pestañas horizontales, sin sidebar
# =============================================================================

import sys
from pathlib import Path
import streamlit as st

_DIR_APP = Path(__file__).resolve().parent
if str(_DIR_APP) not in sys.path:
    sys.path.insert(0, str(_DIR_APP))

from config_app import APP_CONFIG, COLORES, PESTANAS, verificar_ficheros_criticos

st.set_page_config(
    page_title=APP_CONFIG["titulo"],
    page_icon=APP_CONFIG["icono"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state="collapsed",
)

st.markdown(f"""
<style>
    section[data-testid="stSidebar"] {{display: none !important;}}
    [data-testid="collapsedControl"] {{display: none !important;}}
    .main {{background-color: {COLORES["fondo"]};}}
</style>
""", unsafe_allow_html=True)

errores = verificar_ficheros_criticos()
if errores:
    # Cartel bonito + degradación elegante para ficheros críticos
    # (modelo, pipeline, parquet del test). Antes salía un st.error técnico.
    from utils.ui_helpers import mostrar_cartel_problemas
    problemas_criticos = [
        {
            "que":     "Faltan ficheros esenciales para que la app funcione",
            "por_que": ("La app necesita el modelo entrenado, el pipeline de "
                        "preprocesamiento y el parquet de test para mostrar "
                        "cualquier predicción o métrica."),
            "como":    ("1. Verifica que la Fase 5 se haya ejecutado completamente\n"
                        "2. Re-ejecuta `f6_m00_preparacion.ipynb` y "
                        "`f6_m00b_preparacion_app.ipynb` para regenerar los "
                        "ficheros derivados\n"
                        "3. Comprueba que las rutas de `app/config_app.py` "
                        "apuntan al sitio correcto\n"
                        "4. Recarga esta página"),
            "tecnico": "\n".join(errores),
        }
    ]
    mostrar_cartel_problemas(problemas_criticos)  # incluye st.stop()

# Validación adicional del JSON metricas_modelo.json y sus claves obligatorias.
# Aplica el patrón de degradación elegante: si algo falta, el usuario ve un
# cartel amable con instrucciones, no un traceback técnico.
from utils.ui_helpers import validar_recursos_app, mostrar_cartel_problemas
_ok_recursos, _problemas_recursos = validar_recursos_app()
if not _ok_recursos:
    mostrar_cartel_problemas(_problemas_recursos)  # incluye st.stop()

# Banner superior con logos — visible en todas las páginas
_ROOT = Path(__file__).resolve().parent.parent
_logo_uji = _ROOT / "docs" / "assets" / APP_CONFIG["logo_universidad_datos"]
_logo_uoc = _ROOT / "docs" / "assets" / APP_CONFIG["logo_universidad_master"]

col_uji, col_titulo, col_uoc = st.columns([1, 4, 1])
with col_uji:
    if _logo_uji.exists():
        st.image(str(_logo_uji), use_container_width=True)
with col_titulo:
    st.markdown(f"""
    <div style="text-align:center; padding:0.3rem 0;">
        <span style="font-size:1.6rem; font-weight:bold; color:{COLORES['primario']};">
            {APP_CONFIG['icono']} {APP_CONFIG['titulo']}
        </span><br>
        <span style="font-size:0.8rem; color:{COLORES['texto_suave']};">
            {APP_CONFIG['subtitulo']}
        </span>
    </div>
    """, unsafe_allow_html=True)
with col_uoc:
    if _logo_uoc.exists():
        st.image(str(_logo_uoc), use_container_width=True)

st.divider()

# Pestañas horizontales — Streamlit gestiona cuál se ve
tab0, *tabs_resto = st.tabs(
    [f"{APP_CONFIG['icono']} {APP_CONFIG['tab_inicio']}"] + [f"{p['icono']} {p['titulo']}" for p in PESTANAS]
)

with tab0:
    from pages import p00_inicio as _p00; _p00.show()
for tab, p in zip(tabs_resto, PESTANAS):
    with tab:
        if p["id"] == "institucional":
            from pages import p01_institucional as _p01; _p01.show()
        elif p["id"] == "titulacion":
            from pages import p02_titulacion as _p02; _p02.show()
        elif p["id"] == "prospecto":
            from pages import p03_prospecto as _p03; _p03.show()
        elif p["id"] == "en_curso":
            from pages import p04_en_curso as _p04; _p04.show()
        elif p["id"] == "equidad":
            from pages import p05_equidad as _p05; _p05.show()
        elif p["id"] == "leyenda":
            from pages import p06_leyenda as _p06; _p06.show()
