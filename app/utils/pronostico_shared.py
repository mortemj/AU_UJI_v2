# =============================================================================
# pronostico_shared.py
# Módulo compartido de pronóstico personalizado
#
# ¿QUÉ HACE ESTE FICHERO?
#   Contiene toda la lógica y los gráficos del pronóstico individual.
#   Es usado tanto por p03_prospecto.py como por p04_en_curso.py.
#   La diferencia entre ambos modos es mínima:
#     - modo="prospecto" → sin nota_1er_anio ni créditos (aún no cursó nada)
#     - modo="en_curso"  → con nota_1er_anio y créditos superados
#
# ¿POR QUÉ EXISTE ESTE FICHERO?
#   Para no duplicar código entre p03 y p04. Toda la lógica vive aquí.
#   p03 y p04 son wrappers finos que solo llaman a show_pronostico().
#
# ESTRUCTURA:
#   1. Selector de contexto (titulación / rama / sin contexto)
#   2. Formulario de perfil:
#        - Features básicas obligatorias (siempre visibles)
#        - Features avanzadas opcionales (en expander)
#   3. Cálculo de probabilidad con el modelo
#   4. Gráfico 1 — Indicador de riesgo (velocímetro)
#   5. Gráfico 2 — Radar: tu perfil vs éxito Y vs abandono (2 líneas)
#   6. Gráfico 3 — Cascada de contribuciones con selector de método
#        - Método rápido: proxy de diferencia de medias
#        - Método preciso: SHAP TreeExplainer en tiempo real
#   7. Gráfico 4 — Percentil con selector de 3 grupos de referencia
#   8. Recomendaciones personalizadas
#
# FIXES APLICADOS:
#   - cargar_meta_test_app() en vez de cargar_meta_test() (titulaciones fusionadas)
#   - Selector de contexto usa rama_meta (nombre legible) no rama numérica
#   - Radar con 2 trazas: perfil éxito + perfil abandono
#   - Formulario con expander para features avanzadas
#   - Botón de selección de método para la cascada (rápido vs preciso)
#
# PARÁMETROS DE show_pronostico():
#   modo : str — "prospecto" o "en_curso"
#
# REQUISITOS:
#   - config_app.py accesible vía _path_setup
#   - utils/loaders.py disponible
#   - Modelo y pipeline de Fase 5 cargados
#   - shap instalado (para método preciso de cascada)
#
# GENERA:
#   Página Streamlit interactiva. No genera ficheros en disco.
# =============================================================================

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Imports internos — _path_setup añade app/ a sys.path en Windows/OneDrive
# ---------------------------------------------------------------------------
import _path_setup  # noqa: F401

from config_app import (
    COLORES, COLORES_RAMAS, COLORES_RIESGO, NOMBRES_VARIABLES,
    RAMAS_NOMBRES, UMBRALES,
    CATALOGO_TITULACIONES_UJI, ALIAS_TITULACIONES,
    # Auditoría p03 (Chat p03, 27/04/2026): añadido APP_CONFIG para pie
    # de página coherente con p00/p01/p02. Antes pronostico_shared no
    # tenía pie de página (bug grave) — afecta a p03 y p04.
    APP_CONFIG,
    # Refactor SRC↔APP: ya no importamos los 7 MAPS (con bugs en
    # SITUACION_LABORAL=11/8). En su lugar, usamos OPCIONES_*_UI:
    # subconjuntos limpios filtrados desde los mapas oficiales de SRC.
    OPCIONES_LABORAL_UI, OPCIONES_VIA_UI, OPCIONES_SEXO_UI,
    OPCIONES_UNIVERSIDAD_UI, RAMA_NOMBRE_A_CODIGO,
    # Mapas SRC: solo los necesarios para defaults defensivos en provincia/país
    # (formularios no muestran selectbox para estos, son código defensivo).
    PROVINCIA_MAP, PAIS_NOMBRE_MAP,
    # CUPO_MAP: necesario para convertir strings "General", "Mayor 25 Años"...
    # que vienen del dataset cuando se imputa por moda (meta_test_app guarda
    # cupo como string, el modelo espera int 1-7).
    CUPO_MAP, RAMA_MAP,
)
from utils.loaders import cargar_meta_test_app, cargar_modelo, cargar_pipeline
# Auditoría p03 (Chat p03): _tarjeta_kpi MOVIDA a utils/ui_helpers.py para
# que p02 y p03 usen la MISMA función (apariencia idéntica garantizada por
# construcción). Sustituye las cards inline con border-top:3px que tenía p03.
from utils.ui_helpers import _tarjeta_kpi, _nombre_titulacion_corto, _clasificar_riesgo, _pie_pagina, _hex_a_rgba, _leer_metricas_modelo, fmt


# =============================================================================
# CONSTANTES INTERNAS
# =============================================================================

# Columnas que NO son features del modelo (metadatos del test)
_COLS_META = {
    'abandono', 'titulacion', 'rama', 'rama_meta', 'anio_cohorte',
    'sexo', 'sexo_meta', 'nivel_riesgo', 'prob_abandono',
    'pais_nombre', 'pais_nombre_meta', 'provincia', 'provincia_meta',
    'via_acceso', 'via_acceso_meta', 'per_id_ficticio',
}

# Features básicas — siempre visibles en el formulario
# Ordenadas de mayor a menor importancia predictiva
_FEATURES_BASICAS = [
    'nota_acceso',        # numérica — muy predictiva
    'situacion_laboral',  # categórica — predictor más fuerte (código numérico)
    'n_anios_beca',       # numérica — factor protector clave
    'edad_entrada',       # numérica — nombre real en el modelo (no edad_acceso)
    'via_acceso',         # categórica — nombre real en el modelo (no tipo_acceso)
]

# Features avanzadas — en expander, opcionales
# Solo disponibles en prospecto las pre-matrícula
_FEATURES_AVANZADAS_PROSPECTO = [
    'nota_selectividad',    # numérica
    'orden_preferencia',    # numérica
    'anios_gap',            # numérica
    'universidad_origen',   # categórica
    'sexo',                 # categórica
]

# Features adicionales solo en modo en_curso
_FEATURES_EN_CURSO = [
    'nota_1er_anio',           # numérica — muy predictiva
    'cred_superados_anio_1er', # numérica
    'creditos_superados',      # numérica
    'tasa_rendimiento',        # numérica (calculada)
]

# Opciones para variables categóricas — filtradas para selectbox (sin
# variantes históricas duplicadas que tienen los mapas SRC).
# Refactor SRC↔APP: vienen de OPCIONES_*_UI (config_app), que son
# subconjuntos limpios de los mapas oficiales de SRC.
_OPCIONES_VIA_ACCESO = list(OPCIONES_VIA_UI.keys())
_OPCIONES_LABORAL    = list(OPCIONES_LABORAL_UI.keys())
_OPCIONES_SEXO       = list(OPCIONES_SEXO_UI.keys())
_OPCIONES_UNIVERSIDAD = list(OPCIONES_UNIVERSIDAD_UI.keys())


# =============================================================================
# FUNCIÓN PRINCIPAL — llamada desde p03 y p04
# =============================================================================


# =============================================================================
# HELPER: filtrar dataset por titulación considerando alias históricos
# =============================================================================
# El dataset puede tener nombres antiguos ("Ingeniería Mecanica") mientras que
# el usuario selecciona nombres oficiales actuales ("Ingeniería Mecánica") vía
# CATALOGO_TITULACIONES_UJI. Este helper resuelve la equivalencia usando
# ALIAS_TITULACIONES para que el filtro devuelva TODOS los registros que
# pertenecen al mismo grado, incluyendo los antiguos.
# =============================================================================
def _filtrar_por_titulacion(df: "pd.DataFrame", titulacion: str) -> "pd.DataFrame":
    if "titulacion" not in df.columns or not titulacion:
        return df.iloc[0:0]  # DataFrame vacío con mismas columnas
    # Incluimos el nombre actual + todos sus alias antiguos
    nombres_equivalentes = {titulacion} | {
        antiguo for antiguo, nuevo in ALIAS_TITULACIONES.items()
        if nuevo == titulacion
    }
    return df[df["titulacion"].isin(nombres_equivalentes)]



# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _nombre_corto_tit ELIMINADO.
# Se sustituye por _nombre_titulacion_corto de utils/ui_helpers.py.
# Antes había 4 implementaciones distintas:
#   - _nombre_titulacion_corto en p02 (la base)
#   - _nombre_corto_tit aquí (no manejaba 'Doble Grado en' al inicio)
#   - _partir_label en p01 (solo quitaba 'Grado en')
#   - regex inline en p01
# Ahora todas usan la misma función desde ui_helpers.
# =============================================================================



# =============================================================================
# CORRECCIÓN HEURÍSTICA EN ESPACIO LOGIT: logit(p) + log(tasa_tit / tasa_rama)
# =============================================================================
# El modelo predice a nivel de RAMA (5 categorías). Para titulaciones de la
# misma rama el modelo daría el mismo %, aunque su abandono histórico difiera.
# Esta función aplica un reescalado post-hoc basado en datos históricos.
#
# IMPLEMENTACIÓN (abril 2026): ajuste en espacio LOGIT, no multiplicativo.
#   logit_ajustado = logit(prob) + log(tasa_tit / tasa_rama)
#   prob_ajustada  = sigmoid(logit_ajustado)
#
# Por qué logit y no multiplicativo (prob × factor):
#   - Una probabilidad alta (p.ej. 0,96) multiplicada por un factor > 1 satura
#     en [0, 1] y obligaba a un cap duro en 0,99. Eso hacía que perfiles
#     extremos dieran 99,0% en varias titulaciones a la vez, ocultando
#     diferencias reales entre ellas.
#   - En espacio logit no hay saturación artificial: sumar log-odds es la
#     operación natural que usa cualquier regresión logística para combinar
#     evidencia. Los extremos se siguen diferenciando (0,96 y 0,98 son
#     logits 3,18 y 3,89 — muy distintos).
#   - Matemáticamente equivale a sumar un offset de log-odds al logit base,
#     que es exactamente el tipo de recalibración que haría un modelo con
#     variable binaria "es titulación X" si hubiera datos suficientes.
#
# El factor (tasa_tit / tasa_rama) se sigue limitando a [0,3 · 3,0] por
# seguridad frente a titulaciones con muy pocos registros.
#
# Limitación documentada: es univariante (solo tasa histórica), no aprende
# interacciones con otras variables del perfil.
# Referencia: README_titulacion_vs_rama.md · Fase 3 M08 (auditoría leakage)
# =============================================================================

def _ajustar_prob_por_titulacion(prob: float,
                                  contexto: dict,
                                  df_ref: "pd.DataFrame") -> tuple:
    """
    Aplica corrección heurística EN ESPACIO LOGIT cuando el contexto es una
    titulación concreta.

    logit_base     = log(prob / (1 - prob))
    logit_ajustado = logit_base + log(tasa_tit / tasa_rama)
    prob_ajustada  = 1 / (1 + exp(-logit_ajustado))

    El factor (tasa_tit / tasa_rama) se limita a [0,3 · 3,0] por seguridad,
    y el logit final se limita a ±10 (prob ≈ 0,99995 / 0,00005) para evitar
    overflow numérico con perfiles extremos.

    Ventaja sobre la versión multiplicativa anterior: no satura en 1,0, así
    perfiles de alto riesgo en titulaciones distintas siguen diferenciándose
    (p.ej. ADE 97,3% vs Derecho 98,1%) en lugar de aplastarse todos al cap.

    Returns
    -------
    prob_ajustada : float   (igual a prob si contexto no es titulación)
    ajustada      : bool    (True si se aplicó corrección)
    factor        : float   (el factor tasa_tit / tasa_rama aplicado)
    aviso         : str     (texto para mostrar al usuario, "" si no aplica)
    """
    if contexto.get("tipo") != "titulacion":
        return prob, False, 1.0, ""

    titulacion = contexto.get("valor", "")
    col_rama   = "rama_meta" if "rama_meta" in df_ref.columns else "rama"

    if "titulacion" not in df_ref.columns or "abandono" not in df_ref.columns:
        return prob, False, 1.0, ""

    df_tit  = _filtrar_por_titulacion(df_ref, titulacion)
    if len(df_tit) < 10:
        return prob, False, 1.0, ""

    tasa_tit  = float(df_tit["abandono"].mean())
    rama_val  = df_tit[col_rama].mode()[0] if col_rama in df_tit.columns else None

    if rama_val is not None:
        df_rama  = df_ref[df_ref[col_rama] == rama_val]
        tasa_rama = float(df_rama["abandono"].mean()) if len(df_rama) > 0 else tasa_tit
    else:
        tasa_rama = tasa_tit  # sin rama → no ajustamos

    if tasa_rama < 0.01:
        return prob, False, 1.0, ""

    # Factor multiplicativo en espacio probabilidad (solo se usa para el
    # aviso y para devolverlo a quien lo necesite con fines informativos).
    factor = tasa_tit / tasa_rama
    factor = max(0.3, min(3.0, factor))   # límites de seguridad

    # ---- Ajuste en espacio LOGIT (log-odds) ------------------------------
    # 1) Clamp numérico de prob para evitar logit(0) o logit(1).
    prob_clip = float(np.clip(prob, 1e-6, 1.0 - 1e-6))

    # 2) Pasar a logit, sumar el log-ratio de tasas, volver a probabilidad.
    logit_base     = np.log(prob_clip / (1.0 - prob_clip))
    logit_ajustado = logit_base + np.log(factor)

    # 3) Clamp en logit (±10) → equivale a prob ∈ [~0,00005, ~0,99995].
    #    Evita overflow de exp() y mantiene separación entre titulaciones
    #    en los extremos sin necesidad de un cap duro en probabilidad.
    logit_ajustado = float(np.clip(logit_ajustado, -10.0, 10.0))

    prob_ajustada = float(1.0 / (1.0 + np.exp(-logit_ajustado)))

    aviso = (
        f"⚠️ La probabilidad base del modelo ({prob*100:.1f}%) opera a nivel de "
        f"**rama de conocimiento**. Se ha aplicado un ajuste en espacio logit "
        f"por la tasa histórica de abandono de **{titulacion.replace('Grado en ', '')}** "
        f"({tasa_tit*100:.1f}%) respecto a la media de su rama ({tasa_rama*100:.1f}%). "
        f"Este ajuste no forma parte del modelo entrenado."
    )

    return prob_ajustada, True, factor, aviso


# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _pie_pagina ELIMINADA.
# Sustituida por _pie_pagina de utils/ui_helpers.py (importada al principio).
# =============================================================================


def show_pronostico(modo: str = "prospecto"):
    """
    Renderiza la página completa de pronóstico personalizado.

    Parameters
    ----------
    modo : str
        "prospecto" → alumno antes de matricularse (sin nota_1er_anio)
        "en_curso"  → alumno ya matriculado (con nota_1er_anio y créditos)
    """
    assert modo in ("prospecto", "en_curso"), \
        "modo debe ser 'prospecto' o 'en_curso'"

    # Textos que cambian según el modo
    # n_alumnos_unicos — leído de metricas_modelo.json (sin fallback numérico:
    # si JSON falla, mostramos "—" en vez de un valor obsoleto).
    try:
        _m_sp  = _leer_metricas_modelo()
        _n_alu = fmt(_m_sp.get("n_alumnos_unicos"), "miles")
    except Exception:
        _n_alu = "—"  # JSON no disponible

    textos = {
        "prospecto": {
            "titulo":      "🔍 Pronóstico para futuro estudiante",
            "subtitulo":   "Estima tu riesgo de abandono antes de matricularte",
            "descripcion": (
                "Rellena tu perfil de entrada y obtendrás una estimación "
                f"de tu riesgo de abandono basada en patrones de "
                f"{_n_alu} estudiantes de la UJI entre 2010 y 2020."
            ),
        },
        "en_curso": {
            "titulo":      "📊 Pronóstico para alumno en curso",
            "subtitulo":   "Estima tu riesgo de abandono con tus datos actuales",
            "descripcion": (
                "Rellena tu perfil actual. Cuantos más datos introduzcas, "
                "más precisa será la estimación. Los resultados son "
                "orientativos y no sustituyen la orientación académica."
            ),
        },
    }[modo]

    # Cabecera compacta: título + subtítulo en 1 bloque pequeño
    st.markdown(f"""
    <div style="margin-bottom:0.8rem;">
        <h4 style="color:{COLORES['primario']}; margin:0; font-weight:500; font-size:1.15rem;">
            {textos['titulo']}
        </h4>
        <p style="color:{COLORES['texto_suave']}; margin:0.1rem 0 0 0; font-size:0.78rem;">
            {textos['subtitulo']} · {textos['descripcion']}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Carga de datos y modelos — cacheados, solo se ejecuta la primera vez
    with st.spinner("Cargando modelo..."):
        try:
            df_ref   = cargar_meta_test_app()   # titulaciones fusionadas (para contexto/filtros)
            # Filtro canónico tribunal/memoria (28/04/2026): cohortes 2010-2020.
            # El n total del JSON ya viene filtrado por este rango.
            if 'curso_aca_ini' in df_ref.columns:
                df_ref = df_ref[df_ref['curso_aca_ini'].between(2010, 2020)].copy()
            modelo   = cargar_modelo()
            pipeline = cargar_pipeline()
            # X_test_prep: features numéricas reales — para imputar medias correctas
            try:
                import pandas as _pd
                from config_app import RUTAS as _RUTAS
                _ruta_xtest = _RUTAS.get('X_test_prep')
                df_features = _pd.read_parquet(_ruta_xtest) if _ruta_xtest and _ruta_xtest.exists() else None
            except Exception:
                df_features = None
        except FileNotFoundError as e:
            st.error(f"❌ {e}")
            st.stop()

    # --- Paso 1: selector de contexto ---
    contexto = _selector_contexto(df_ref, modo)

    st.markdown(f"<hr style='margin:0.5rem 0; border:none; border-top:1px solid {COLORES['borde']};'>",
                 unsafe_allow_html=True)

    # --- Bifurcación: comparativa vs pronóstico individual ---
    # Si el usuario eligió "Comparar varias titulaciones", mostramos
    # la comparativa directamente y salimos del flujo normal.
    if contexto["tipo"] == "comparativa":
        perfil, calcular = _formulario_perfil(modo, df_ref, contexto)
        if not calcular:
            _mostrar_instrucciones()
            _pie_pagina()
            return
        with st.spinner("Calculando comparativa..."):
            _mostrar_comparativa(perfil, contexto["titulaciones"],
                                 df_ref, modelo, pipeline,
                                 df_features=df_features if df_features is not None else df_ref)
        st.markdown(f"""
        <div style="font-size:0.75rem; color:{COLORES['texto_suave']};
                    border-top:1px solid {COLORES['borde']};
                    margin-top:1.5rem; padding-top:0.8rem;">
            ⚠️ <em>Este pronóstico es una estimación estadística basada en datos
            históricos. No determina ni condiciona ninguna decisión académica.</em>
        </div>
        """, unsafe_allow_html=True)
        _pie_pagina()
        return

    # --- Paso 2: formulario de perfil (básico + avanzado) ---
    perfil, calcular = _formulario_perfil(modo, df_ref, contexto)

    # Claves de session_state para este modo — evita colisiones entre p03 y p04
    _key_prob   = f"_prob_{modo}"
    _key_perfil = f"_perfil_{modo}"
    _key_ctx    = f"_contexto_{modo}"
    _key_df_ctx = f"_df_ctx_{modo}"
    _key_ajuste = f"_ajuste_{modo}"

    if calcular:
        # El usuario pulsó "Calcular" — recalculamos y guardamos en session_state
        df_ctx = contexto.get("df_contexto", df_ref)
        if df_ctx is None or len(df_ctx) == 0:
            df_ctx = df_ref

        with st.spinner("Calculando pronóstico..."):
            prob, error = _calcular_probabilidad(perfil, modelo, pipeline, df_ctx)

        if error:
            st.error(f"❌ Error al calcular: {error}")
            _pie_pagina()
            return

        prob, ajustada, factor, aviso_ajuste = _ajustar_prob_por_titulacion(
            prob, contexto, df_ref
        )

        # Guardar en session_state — los widgets de gráficos no perderán el resultado
        st.session_state[_key_prob]   = prob
        st.session_state[_key_perfil] = perfil
        st.session_state[_key_ctx]    = contexto
        st.session_state[_key_df_ctx] = df_ctx
        st.session_state[_key_ajuste] = (ajustada, aviso_ajuste)

    elif _key_prob in st.session_state:
        # Widget de gráfico cambió (radio percentil, etc.) — recuperar sin recalcular
        prob                   = st.session_state[_key_prob]
        perfil                 = st.session_state[_key_perfil]
        contexto               = st.session_state[_key_ctx]
        df_ctx                 = st.session_state[_key_df_ctx]
        ajustada, aviso_ajuste = st.session_state[_key_ajuste]

    else:
        # Nunca se ha calculado — mostrar instrucciones
        _mostrar_instrucciones()
        _pie_pagina()
        return

    st.markdown(f"<hr style='margin:0.3rem 0; border:none; border-top:1px solid {COLORES['borde']};'>",
                 unsafe_allow_html=True)

    # === FILA DE KPIs (4 chips resumen) ==============================
    _kpis_resumen(prob, perfil, contexto, df_ctx, df_ref)

    # Aviso de corrección heurística (solo si se aplicó)
    if ajustada and aviso_ajuste:
        # Auditoría p03 (Chat p03): hex hardcodeados → COLORES.
        # Auditoría p00 (28/04/2026): #fffbeb → rgba derivado de
        # advertencia con _hex_a_rgba (sin hardcoded).
        _bg_aviso = _hex_a_rgba(COLORES['advertencia'], 0.10)
        st.markdown(
            f"<div style='font-size:0.78rem; color:{COLORES['texto_suave']}; "
            f"border-left:3px solid {COLORES['advertencia']}; "
            f"padding:0.4rem 0.8rem; margin:0.3rem 0; border-radius:4px; "
            f"background:{_bg_aviso};'>"
            f"⚠️ {aviso_ajuste}</div>",
            unsafe_allow_html=True,
        )

    # === FILA 1: Velocímetro + Histórico (scatter) ===================
    col_veloci, col_scatter = st.columns([1, 1])
    with col_veloci:
        _grafico_indicador_riesgo(prob, modo=modo)
    with col_scatter:
        _grafico_historico_scatter(prob, contexto, df_ref, perfil=perfil)

    # === SELECTOR GLOBAL: Rapido vs Preciso (PASO 3 Bloque 4) =========
    # Conexión real activada en PASO 4. Se coloca ANTES del expander del
    # dot plot para que sea visible cuando el usuario abre el detalle técnico.
    #
    # FIX 29/04/2026 (Bloque 4): la key del st.radio interna debe ser
    # ÚNICA en toda la sesión Streamlit. Usar solo "single" provocaba
    # DuplicateElementKey en p03 cuando el contexto cambiaba entre rama,
    # titulación y todas las titulaciones (mismo widget renderizado más
    # de una vez en la misma sesión). Construimos la key combinando
    # modo (prospecto/en_curso) + tipo de contexto (todas/rama/
    # titulacion) + valor concreto, garantizando unicidad global.
    _ctx_tipo  = contexto.get("tipo",  "sin_tipo")
    _ctx_valor = str(contexto.get("valor", "all")).replace(" ", "_")[:30]
    _key_sel   = f"{modo}_{_ctx_tipo}_{_ctx_valor}"
    _metodo_dotplot = _selector_metodo_global(key_suffix=_key_sel)

    # === FILA 2: Detalle técnico (expander con radar + cascada) ======
    with st.expander("📊 Detalle técnico — radar del perfil y factores de riesgo", expanded=False):
        col_radar, col_cascada = st.columns([1, 1])
        with col_radar:
            _grafico_radar(perfil, df_ref, contexto, prob)
        with col_cascada:
            _grafico_cascada(perfil, df_ctx, prob, modelo, pipeline,
                             modo=modo, metodo=_metodo_dotplot)

    # === FILA 3: Percentil (expander) =================================
    with st.expander("📏 Tu posición en la distribución histórica", expanded=False):
        _grafico_percentil(prob, df_ref, contexto, modelo, pipeline)

    # === RECOMENDACIONES (compactas) ==================================
    st.markdown("")
    _recomendaciones(perfil, prob, modo, df_ctx=contexto.get('df_contexto'))

    # Aviso legal / limitaciones
    st.markdown(f"""
    <div style="
        font-size:0.75rem;
        color:{COLORES['texto_suave']};
        border-top:1px solid {COLORES['borde']};
        margin-top:1.5rem;
        padding-top:0.8rem;
    ">
        ⚠️ <em>Este pronóstico es una estimación estadística basada en datos
        históricos. No determina ni condiciona ninguna decisión académica.
        Si tienes dudas, visita el
        <a href="https://www.uji.es/perfils/estudiantat/v2/nou-estudiantat/"
        target="_blank">Portal Nuevo Estudiantado</a> de la UJI o consulta
        con la Unidad de Soporte Educativo (USE).</em>
    </div>
    """, unsafe_allow_html=True)

    # Pie de página (paridad p00/p01/p02)
    _pie_pagina()


# =============================================================================
# PASO 1: Selector de contexto
# =============================================================================

def _selector_contexto(df_ref: pd.DataFrame, modo: str) -> dict:
    """
    Permite al usuario elegir el contexto de comparación.

    En modo 'en_curso':  selector directo de titulación (obligatorio).
    En modo 'prospecto': radio buttons (todas / rama / titulación / comparar).

    Devuelve un dict con:
        tipo        : "titulacion" | "rama" | "todas"
        valor       : nombre de la titulación/rama, o None
        df_contexto : subconjunto de df_ref según el contexto elegido
    """
    col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'

    # =========================================================================
    # MODO EN CURSO — selector directo, sin radio buttons
    # =========================================================================
    if modo == "en_curso":
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin-bottom:0.5rem;">
            1️⃣ ¿Qué estás estudiando?
        </h4>
        <p style="font-size:0.85rem; color:{COLORES['texto_suave']};">
            Selecciona tu titulación. Las comparativas se calcularán respecto
            a alumnos históricos de ese mismo grado.
        </p>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            titulaciones_disp = sorted(
                df_ref['titulacion'].dropna().unique().tolist()
            ) if 'titulacion' in df_ref.columns else []
            valor_tit = st.selectbox(
                label="Tu titulación",
                options=titulaciones_disp,
                index=0,
                key=f"sel_tit_{modo}",
                help="Puedes escribir para buscar dentro de la lista.",
            ) if titulaciones_disp else None

        with col2:
            if valor_tit and 'titulacion' in df_ref.columns:
                df_ctx = df_ref[df_ref['titulacion'] == valor_tit]
                tasa   = (df_ctx['abandono'].sum() / len(df_ctx) * 100) \
                         if 'abandono' in df_ctx.columns and len(df_ctx) > 0 else 0
                st.markdown(f"""
                <div style="
                    background:{COLORES['fondo']};
                    border-left:3px solid {COLORES['primario']};
                    border-radius:4px;
                    padding:0.6rem 1rem;
                    font-size:0.83rem;
                    margin-top:1.6rem;
                ">
                    <strong>Alumnos en histórico:</strong> {f"{len(df_ctx):,}".replace(",", ".")}<br>
                    <strong>Tasa abandono histórica:</strong> {f"{tasa:.1f}".replace('.', ',')}%
                </div>
                """, unsafe_allow_html=True)
            else:
                df_ctx = df_ref.copy()

        st.divider()
        return {"tipo": "titulacion", "valor": valor_tit, "df_contexto": df_ctx}

    # =========================================================================
    # MODO PROSPECTO — flujo original con radio buttons
    # =========================================================================
    # Versión para el selector de contexto (independiente del formulario)
    # Se incrementa con el botón borrar para resetear los selects de rama/titulación.
    _ver_ctx_key = f"_ctx_v_{modo}"
    if _ver_ctx_key not in st.session_state:
        st.session_state[_ver_ctx_key] = 0
    _vc = st.session_state[_ver_ctx_key]
    _suf_ctx = f"{modo}_v{_vc}"

    # Cabecera con título y botón Borrar a la derecha
    col_titulo, col_borrar_top = st.columns([5, 1])
    with col_titulo:
        st.markdown(f"""
        <h5 style="color:{COLORES['texto']}; margin:0 0 0.2rem 0; font-weight:500;">
            1️⃣ ¿Tienes una titulación en mente?
            <span style="font-size:0.72rem; color:{COLORES['texto_suave']}; font-weight:400;">
            · opcional, sirve para contextualizar la comparativa
            </span>
        </h5>
        """, unsafe_allow_html=True)
    with col_borrar_top:
        # Espaciado vertical para alinear con el título
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "🗑️ Borrar todo",
            key=f"btn_borrar_top_{modo}",
            help="Borra todo: selector de titulación, perfil y resultado",
            width='stretch',
        ):
            # Limpiar resultado guardado
            for _k in (f"_prob_{modo}", f"_perfil_{modo}", f"_contexto_{modo}",
                       f"_df_ctx_{modo}", f"_ajuste_{modo}"):
                st.session_state.pop(_k, None)
            # Incrementar ambas versiones (formulario y contexto) para
            # forzar a Streamlit a recrear todos los widgets vacíos.
            st.session_state[_ver_ctx_key] += 1
            st.session_state[f"_form_v_{modo}"] = st.session_state.get(
                f"_form_v_{modo}", 0
            ) + 1
            st.rerun()

    col1, col2 = st.columns([1, 2])

    with col1:
        tipo_contexto = st.radio(
            label="Comparar contra:",
            options=[
                "Todas las titulaciones",
                "Una rama concreta",
                "Una titulación concreta",
                "🔀 Comparar varias titulaciones",
            ],
            index=0,
            key=f"tipo_contexto_{_suf_ctx}",
            help=(
                "Elige el grupo con el que quieres compararte. "
                "Con 'Comparar varias titulaciones' puedes ver tu riesgo "
                "en 2-5 carreras a la vez."
            ),
        )

    with col2:
        valor_contexto = None

        # Usamos rama_meta (nombre legible) si está disponible, si no rama
        col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'

        # Helper: traduce códigos (EX/HU/SA/SO/TE) a nombres completos legibles
        # usando RAMAS_NOMBRES. Si la columna ya es legible (rama_meta), no toca.
        def _ramas_legibles(df):
            if col_rama not in df.columns:
                return [], {}
            valores = sorted(df[col_rama].dropna().unique().tolist())
            if col_rama == 'rama_meta':
                return valores, {v: v for v in valores}
            legibles = [RAMAS_NOMBRES.get(v, v) for v in valores]
            return legibles, {RAMAS_NOMBRES.get(v, v): v for v in valores}

        # Helper: construye lista de titulaciones agrupada
        # - Arriba: titulaciones con datos en el dataset (orden alfabético)
        # - Separador visual
        # - Abajo: titulaciones del catálogo SIN datos, con emoji "⚠️ (sin datos)"
        # Devuelve (opciones_desplegable, set_con_datos, mapa_display→nombre_real)
        # sigla_rama opcional para filtrar catálogo por rama.
        # Aplica ALIAS_TITULACIONES para reconocer nombres antiguos del dataset.
        def _titulaciones_con_estado(df_base, sigla_rama=None):
            # Titulaciones presentes en el dataset (pueden ser nombres antiguos)
            tit_dataset = set(df_base['titulacion'].dropna().unique().tolist()) \
                if 'titulacion' in df_base.columns else set()
            # Normalizar: aplicar alias → nombres oficiales actuales
            # Así "Ingeniería Mecanica" cuenta como "Ingeniería Mecánica"
            con_datos = {
                ALIAS_TITULACIONES.get(t, t) for t in tit_dataset
            }
            # Catálogo oficial filtrado por rama si aplica
            if sigla_rama:
                catalogo_rama = {
                    t: r for t, r in CATALOGO_TITULACIONES_UJI.items()
                    if r == sigla_rama
                }
            else:
                catalogo_rama = dict(CATALOGO_TITULACIONES_UJI)
            # Separación: con datos vs sin datos (respecto al catálogo)
            todas_catalogo = set(catalogo_rama.keys())
            tit_con = sorted(con_datos & todas_catalogo)
            tit_sin = sorted(todas_catalogo - con_datos)
            # Construir opciones del selectbox (solo nombres del catálogo)
            opciones = list(tit_con)
            mapa_display = {t: t for t in opciones}
            if tit_sin:
                opciones.append("────────── Sin datos suficientes ──────────")
                for t in tit_sin:
                    display = f"{t} ⚠️ (sin datos)"
                    opciones.append(display)
                    mapa_display[display] = t
            return opciones, con_datos, mapa_display

        if tipo_contexto == "Una rama concreta" and col_rama in df_ref.columns:
            ramas_leg, mapa_leg_cod = _ramas_legibles(df_ref)
            rama_legible = st.selectbox(
                label="Selecciona la rama",
                options=ramas_leg,
                key=f"sel_rama_{_suf_ctx}",
            )
            # Guardamos el código internamente (para filtros) pero mostramos legible
            valor_contexto = mapa_leg_cod[rama_legible]

        elif tipo_contexto == "Una titulación concreta" and 'titulacion' in df_ref.columns:
            # Primero filtramos por rama si el usuario la eligió
            # Así la lista de titulaciones es manejable (~8-10 por rama)
            ramas_leg, mapa_leg_cod = _ramas_legibles(df_ref)

            sigla_rama_filtro = None
            if ramas_leg:
                rama_filtro = st.selectbox(
                    label="Filtrar por rama (opcional)",
                    options=["Todas las ramas"] + ramas_leg,
                    key=f"sel_rama_filtro_{_suf_ctx}",
                    help="Filtra la lista de titulaciones por rama para encontrarla más fácil",
                )
                if rama_filtro != "Todas las ramas":
                    df_filtrado = df_ref[df_ref[col_rama] == mapa_leg_cod[rama_filtro]]
                    # Convertir código interno a sigla (EX/HU/...) para filtrar catálogo
                    sigla_rama_filtro = mapa_leg_cod[rama_filtro]
                else:
                    df_filtrado = df_ref
            else:
                df_filtrado = df_ref

            # Lista mixta: con datos arriba + separador + sin datos abajo
            opciones, con_datos, mapa_display = _titulaciones_con_estado(
                df_filtrado, sigla_rama=sigla_rama_filtro
            )
            seleccion = st.selectbox(
                label="Selecciona la titulación",
                options=opciones,
                key=f"sel_tit_{_suf_ctx}",
                help="Las marcadas con ⚠️ están en la UJI pero no tienen suficientes datos en el histórico",
            )
            # Si es el separador, ignorar
            if seleccion and seleccion.startswith("──"):
                valor_contexto = None
                st.info("👆 Selecciona una titulación (no el separador).")
            else:
                valor_contexto = mapa_display.get(seleccion, seleccion)
                # Aviso transparente si no tiene datos suficientes
                if valor_contexto and valor_contexto not in con_datos:
                    st.warning(
                        f"⚠️ **{valor_contexto}** no tiene suficientes datos en el "
                        f"histórico del modelo. El pronóstico se calculará usando "
                        f"la **rama** como referencia en lugar de la titulación."
                    )

        # --- Opción comparativa: multiselect de titulaciones ---
        titulaciones_comparar = []
        if "Comparar" in tipo_contexto and 'titulacion' in df_ref.columns:
            # Filtro opcional por rama para acotar la lista (con nombres legibles)
            ramas_leg_c, mapa_leg_cod_c = _ramas_legibles(df_ref)
            sigla_rama_filtro_c = None
            if ramas_leg_c:
                rama_filtro_c = st.selectbox(
                    label="Filtrar por rama (opcional)",
                    options=["Todas las ramas"] + ramas_leg_c,
                    key=f"rama_comp_{_suf_ctx}",
                    help="Reduce la lista de titulaciones disponibles",
                )
                if rama_filtro_c != "Todas las ramas":
                    df_comp_filtrado = df_ref[df_ref[col_rama] == mapa_leg_cod_c[rama_filtro_c]]
                    sigla_rama_filtro_c = mapa_leg_cod_c[rama_filtro_c]
                else:
                    df_comp_filtrado = df_ref
            else:
                df_comp_filtrado = df_ref

            # Lista agrupada: con datos arriba + separador + sin datos abajo
            opciones_c, con_datos_c, mapa_display_c = _titulaciones_con_estado(
                df_comp_filtrado, sigla_rama=sigla_rama_filtro_c
            )
            # Quitamos el separador del multiselect (no tiene sentido ahí)
            opciones_c = [o for o in opciones_c if not o.startswith("──")]
            seleccion_raw = st.multiselect(
                label="Selecciona 2-5 titulaciones para comparar",
                options=opciones_c,
                default=[],
                max_selections=5,
                key=f"multisel_tit_{_suf_ctx}",
                help="Mínimo 2, máximo 5. Las marcadas con ⚠️ no tienen datos suficientes.",
            )
            # Convertir display → nombre real y avisar si hay sin datos
            titulaciones_comparar = [mapa_display_c.get(t, t) for t in seleccion_raw]
            sin_datos_elegidas = [
                t for t in titulaciones_comparar if t not in con_datos_c
            ]
            if sin_datos_elegidas:
                st.warning(
                    f"⚠️ {len(sin_datos_elegidas)} titulación(es) sin datos suficientes: "
                    f"{', '.join(sin_datos_elegidas)}. "
                    f"Se usará la rama como referencia para esas."
                )

            # Aviso si selección fuera de rango
            n = len(titulaciones_comparar)
            if n == 1:
                st.warning("⚠️ Selecciona al menos 2 titulaciones para comparar.")
            elif n >= 2:
                st.success(f"✅ {n} titulaciones seleccionadas. Rellena tu perfil y pulsa calcular.")

        # Tarjeta informativa del contexto elegido
        if valor_contexto and "Comparar" not in tipo_contexto:
            if tipo_contexto == "Una rama concreta":
                df_ctx = df_ref[df_ref[col_rama] == valor_contexto]
            else:
                # El helper aplica ALIAS_TITULACIONES automáticamente
                df_ctx = _filtrar_por_titulacion(df_ref, valor_contexto)

            tasa_ctx = (df_ctx['abandono'].sum() / len(df_ctx) * 100) \
                if 'abandono' in df_ctx.columns and len(df_ctx) > 0 else 0

            # Si estamos en rama, mostramos el nombre legible (no el código)
            contexto_display = (
                RAMAS_NOMBRES.get(valor_contexto, valor_contexto)
                if tipo_contexto == "Una rama concreta"
                else valor_contexto
            )
            st.markdown(f"""
            <div style="
                background:{COLORES['fondo']};
                border-left:3px solid {COLORES['primario']};
                border-radius:4px;
                padding:0.6rem 1rem;
                font-size:0.83rem;
                margin-top:0.3rem;
            ">
                <strong>Contexto:</strong> {contexto_display}<br>
                <strong>Alumnos en histórico:</strong> {f"{len(df_ctx):,}".replace(",", ".")}<br>
                <strong>Tasa abandono histórica:</strong> {f"{tasa_ctx:.1f}".replace('.', ',')}%
            </div>
            """, unsafe_allow_html=True)
        else:
            tasa_uji = (df_ref['abandono'].sum() / len(df_ref) * 100) \
                if 'abandono' in df_ref.columns else 0
            st.markdown(f"""
            <div style="
                background:{COLORES['fondo']};
                border-left:3px solid {COLORES['texto_suave']};
                border-radius:4px;
                padding:0.6rem 1rem;
                font-size:0.83rem;
                margin-top:0.3rem;
            ">
                <strong>Contexto:</strong> Toda la UJI<br>
                <strong>Alumnos en histórico:</strong> {f"{len(df_ref):,}".replace(",", ".")}<br>
                <strong>Tasa abandono histórica:</strong> {f"{tasa_uji:.1f}".replace('.', ',')}%
            </div>
            """, unsafe_allow_html=True)

    # Construimos el dict de contexto
    col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'
    if "Comparar" in tipo_contexto:
        # Modo comparativa — la lista de titulaciones ya está en titulaciones_comparar
        return {
            "tipo":         "comparativa",
            "valor":        None,
            "df_contexto":  df_ref.copy(),
            "titulaciones": titulaciones_comparar,
        }
    elif tipo_contexto == "Una rama concreta" and valor_contexto:
        tipo_key = "rama"
        df_ctx   = df_ref[df_ref[col_rama] == valor_contexto]
    elif tipo_contexto == "Una titulación concreta" and valor_contexto:
        tipo_key = "titulacion"
        df_ctx   = df_ref[df_ref['titulacion'] == valor_contexto]
    else:
        tipo_key = "todas"
        df_ctx   = df_ref.copy()

    return {"tipo": tipo_key, "valor": valor_contexto, "df_contexto": df_ctx}


# =============================================================================
# PASO 2: Formulario de perfil
# =============================================================================

def _formulario_perfil(modo: str, df_ref: pd.DataFrame,
                        contexto: dict) -> tuple[dict, bool]:
    """
    Formulario con los datos del alumno, dividido en dos bloques:
      - Básicas obligatorias: siempre visibles
      - Avanzadas opcionales: dentro de un expander

    Devuelve (perfil_dict, calcular_bool).
    calcular_bool es True cuando el usuario pulsa el botón.
    """
    # Versión de keys de los widgets — se incrementa al pulsar "Borrar"
    # para forzar a Streamlit a recrear los widgets con valores por defecto
    # (el patrón clásico de del session_state[k] no funciona con widgets).
    _ver_key = f"_form_v_{modo}"
    if _ver_key not in st.session_state:
        st.session_state[_ver_key] = 0
    _v = st.session_state[_ver_key]
    # Sufijo común para todas las keys de widgets de este formulario
    _suf = f"{modo}_v{_v}"

    st.markdown(f"""
    <h5 style="color:{COLORES['texto']}; margin:0.5rem 0 0.3rem 0; font-weight:500;">
        2️⃣ Rellena tu perfil
        <span style="font-size:0.72rem; color:{COLORES['texto_suave']}; font-weight:400;">
        · campos con <strong>*</strong> son los más influyentes
        </span>
    </h5>
    """, unsafe_allow_html=True)

    df_ctx = contexto['df_contexto']

    # Recordatorio de titulación/contexto seleccionado
    if contexto['tipo'] in ('titulacion', 'rama') and contexto.get('valor'):
        col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'
        n_alumnos = len(df_ctx)
        tasa = (df_ctx['abandono'].sum() / n_alumnos * 100)             if 'abandono' in df_ctx.columns and n_alumnos > 0 else None
        tasa_txt = (
            f" · Abandono histórico: {tasa:.1f}%".replace('.', ',')
            if tasa is not None else ""
        )
        st.markdown(f"""
        <div style="
            background:{COLORES['fondo']};
            border-left:3px solid {COLORES['primario']};
            border-radius:4px;
            padding:0.45rem 1rem;
            font-size:0.83rem;
            color:{COLORES['texto']};
            margin-bottom:0.6rem;
        ">
            📚 Calculando para: <strong>{RAMAS_NOMBRES.get(contexto['valor'], contexto['valor']) if contexto.get('tipo') == 'rama' else contexto['valor']}</strong>
            · {f"{n_alumnos:,}".replace(",", ".")} alumnos en histórico{tasa_txt}
        </div>
        """, unsafe_allow_html=True)

    # Helper: media del contexto como valor por defecto
    def _med(col, default):
        return float(df_ctx[col].mean()) \
            if col in df_ctx.columns and df_ctx[col].notna().any() else default

    perfil = {}

    # -------------------------------------------------------------------------
    # BLOQUE BÁSICO — siempre visible
    # -------------------------------------------------------------------------
    st.markdown(f"<p style='font-size:0.85rem; font-weight:600; color:{COLORES['texto']}; margin-bottom:0.3rem;'>📋 Datos principales</p>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # BLOQUE PRINCIPAL — distinto según modo
    # en_curso:  rendimiento académico primero (los más predictivos)
    # prospecto: datos de acceso primero (lo único disponible antes de entrar)
    # -------------------------------------------------------------------------

    if modo == "en_curso":
        # ---------------------------------------------------------------------
        # Layout en 3 cards temáticas:
        #   📘 Académico       (nota, créditos, repetidos, años matriculado)
        #   👤 Personal        (edad, sexo, provincia, interrupción)
        #   💼 Socioeconómico  (situación laboral, años trabajando, beca)
        # Cada card tiene un encabezado visual con icono y borde lateral azul.
        # Más profesional que el layout plano anterior y reduce el scroll.
        # ---------------------------------------------------------------------

        # HACK CSS para estrechar los inputs numéricos y selectores en p04.
        # Streamlit por defecto estira los widgets al 100% de la columna.
        # Aplicamos max-width SOLO a number_input y selectbox en modo en_curso.
        # Es un parche cosmético — si rompe algo, basta con quitar este bloque.
        # Los sliders se dejan anchos porque necesitan espacio para deslizar.
        st.markdown("""
        <style>
        /* Limitar ancho de number_input (edad, años, créditos...) */
        div[data-testid="stNumberInput"] {
            max-width: 200px;
        }
        /* Limitar ancho de selectbox (sexo, provincia, situación laboral) */
        div[data-testid="stSelectbox"] {
            max-width: 260px;
        }
        </style>
        """, unsafe_allow_html=True)

        col_aca, col_per, col_eco = st.columns(3)

        # === CARD 1 · ACADÉMICO ==============================================
        with col_aca:
            st.markdown(f"""
            <div style="
                background:{COLORES['fondo']};
                border:1.5px solid {COLORES['primario']};
                border-radius:10px;
                padding:0.6rem 0.9rem;
                margin-bottom:0.5rem;
            ">
                <div style="font-size:0.85rem; font-weight:600; color:{COLORES['primario']};">
                    📘 Académico
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Checkbox único para cubrir los dos casos de "no recuerdo"
            _no_datos_acad = st.checkbox(
                "No recuerdo mis datos académicos de 1º",
                value=False,
                key=f"no_datos_acad_{modo}",
            )
            perfil['nota_1er_anio'] = np.nan if _no_datos_acad else st.slider(
                label="Nota 1º *",
                min_value=0.0, max_value=10.0,
                value=round(_med('nota_1er_anio', 6.0), 1),
                step=0.1,
                help="Uno de los predictores más fuertes del modelo para alumnos en curso.",
                key=f"nota_1er_{modo}",
                disabled=_no_datos_acad,
            )
            # Cambio 30/04/2026 (Bug 127):
            # La columna fuente `cred_superados` del data warehouse UJI es ACUMULADA
            # (créditos del año + anteriores), no anual. Para alumnos con convalidación
            # masiva (Adaptación a Grado, Titulados Universitarios, Traslado, segunda
            # titulación, planes a extinguir) puede llegar a 240+ ECTS en su primer
            # registro. max_value=80 hacía saltar StreamlitValueAboveMaxError.
            # Ver: docs/diagnostico_bug127.md y memoria TFM Sec. 5 (Limitaciones).
            perfil['cred_superados_anio_1er'] = np.nan if _no_datos_acad else st.number_input(
                label="Créditos superados acumulados al iniciar *",
                min_value=0, max_value=300,
                value=int(_med('cred_superados_anio_1er', 40)),
                step=1,
                help=(
                    "Créditos totales superados que el alumno aporta al inicio del grado. "
                    "En alumnos sin trayectoria previa, suelen ser ≤ 60 ECTS (un curso completo). "
                    "Valores superiores indican convalidación por estudios previos, "
                    "traslado de expediente, segunda titulación o cambio de plan."
                ),
                key=f"cred_1er_{modo}",
                disabled=_no_datos_acad,
            )
            # cred_repetidos: preguntado como ASIGNATURAS (más natural) × 6 ECTS
            n_asignaturas_repetidas = st.number_input(
                label="Asignaturas repetidas",
                min_value=0, max_value=20,
                value=0,
                step=1,
                help="Número de asignaturas que has tenido que matricular más de una vez. 0 si no has repetido ninguna. Se calculan como 6 créditos cada una.",
                key=f"n_asig_rep_{_suf}",
            )
            perfil['cred_repetidos'] = n_asignaturas_repetidas * 6
            # Años matriculado va aquí (académico) — su valor se usa como
            # max del slider "años con beca" que está en la card económica.
            perfil['_anios_matriculado'] = st.number_input(
                label="Años matriculado *",
                min_value=1, max_value=10,
                value=1,
                step=1,
                help="Número de cursos académicos que llevas matriculado. Se usa para calcular los años sin beca.",
                key=f"anios_mat_bas_{_suf}",
            )

        # === CARD 2 · PERSONAL ===============================================
        with col_per:
            st.markdown(f"""
            <div style="
                background:{COLORES['fondo']};
                border:1.5px solid {COLORES['primario']};
                border-radius:10px;
                padding:0.6rem 0.9rem;
                margin-bottom:0.5rem;
            ">
                <div style="font-size:0.85rem; font-weight:600; color:{COLORES['primario']};">
                    👤 Personal
                </div>
            </div>
            """, unsafe_allow_html=True)

            perfil['edad_entrada'] = st.number_input(
                label="Edad al acceder",
                min_value=17, max_value=65,
                value=int(np.clip(_med('edad_entrada', 19), 17, 65)),
                step=1,
                key=f"edad_{_suf}",
            )
            perfil['sexo'] = st.selectbox(
                label="Sexo",
                options=_OPCIONES_SEXO,
                index=0,
                key=f"sexo_bas_{_suf}",
            )
            # provincia: 70% Castelló, 24% València, resto residual
            # PROVINCIA_MAP traduce el string a código al enviar al modelo
            perfil['provincia'] = st.selectbox(
                label="Provincia",
                options=['Castelló', 'València', 'Alacant', 'Tarragona', 'Terol', 'Otra / sin datos'],
                index=0,  # Castelló es mayoritario (UJI está en Castelló)
                help="Tu provincia de residencia actual.",
                key=f"prov_{_suf}",
            )
            perfil['indicador_interrupcion'] = int(st.checkbox(
                label="¿Has interrumpido algún curso?",
                value=False,
                help="Marca si hubo algún curso en que no te matriculaste estando todavía en la carrera.",
                key=f"interrupcion_{_suf}",
            ))

        # === CARD 3 · SOCIOECONÓMICO =========================================
        with col_eco:
            st.markdown(f"""
            <div style="
                background:{COLORES['fondo']};
                border:1.5px solid {COLORES['primario']};
                border-radius:10px;
                padding:0.6rem 0.9rem;
                margin-bottom:0.5rem;
            ">
                <div style="font-size:0.85rem; font-weight:600; color:{COLORES['primario']};">
                    💼 Socioeconómico
                </div>
            </div>
            """, unsafe_allow_html=True)

            perfil['situacion_laboral'] = st.selectbox(
                label="Situación laboral *",
                options=_OPCIONES_LABORAL,
                index=0,
                help="La situación laboral es el predictor categórico más fuerte del modelo (Cramér V=0.26).",
                key=f"laboral_{_suf}",
            )
            # n_anios_trabajando: complementa a situacion_laboral
            perfil['n_anios_trabajando'] = st.number_input(
                label="Años trabajando",
                min_value=0, max_value=10,
                value=int(_med('n_anios_trabajando', 0)),
                step=1,
                help="Número total de cursos en los que has trabajado mientras estudiabas.",
                key=f"anios_trab_{_suf}",
            )
            # Años con beca: máximo dinámico = años matriculado (validación
            # por construcción). Usamos number_input para coherencia visual.
            _max_beca    = int(perfil['_anios_matriculado'])
            _med_beca    = int(round(_med('n_anios_beca', 2)))
            _valor_beca  = min(_med_beca, _max_beca)
            perfil['n_anios_beca'] = st.number_input(
                label="Años con beca *",
                min_value=0, max_value=_max_beca,
                value=_valor_beca,
                step=1,
                help="Factor protector muy importante. Los becarios tienen tasas de abandono significativamente más bajas. No puede superar los años matriculados.",
                key=f"beca_{_suf}",
            )

    else:
        # Modo prospecto: orden original (acceso primero)
        col1, col2, col3 = st.columns(3)

        with col1:
            _val_nota = float(np.clip(round(_med('nota_acceso', 8.0), 1), 5.0, 14.0))
            perfil['nota_acceso'] = st.slider(
                label="Nota de acceso (PAU / FP) *",
                min_value=5.0, max_value=14.0,
                value=_val_nota,
                step=0.1,
                help="Nota de acceso a la universidad (escala 0–14). Es uno de los predictores más importantes.",
                key=f"nota_acceso_{_suf}",
            )
            perfil['via_acceso'] = st.selectbox(
                label="Vía de acceso *",
                options=_OPCIONES_VIA_ACCESO,
                index=0,
                key=f"tipo_acceso_{_suf}",
            )

        with col2:
            perfil['situacion_laboral'] = st.selectbox(
                label="Situación laboral *",
                options=_OPCIONES_LABORAL,
                index=0,
                help="La situación laboral es el predictor categórico más fuerte del modelo (Cramér V=0.26).",
                key=f"laboral_{_suf}",
            )
            _solicita_beca = st.checkbox(
                label="¿Piensas solicitar beca? *",
                value=False,
                help=(
                    "Los becarios tienen tasas de abandono significativamente más bajas. "
                    "Si marcas que sí, el modelo asume una media de 4 años con beca."
                ),
                key=f"beca_checkbox_{_suf}",
            )
            perfil['n_anios_beca'] = 4 if _solicita_beca else 0

        with col3:
            perfil['edad_entrada'] = st.number_input(
                label="Edad al acceder",
                min_value=17, max_value=65,
                value=int(np.clip(_med('edad_entrada', 19), 17, 65)),
                step=1,
                key=f"edad_{_suf}",
            )
            perfil['sexo'] = st.selectbox(
                label="Sexo",
                options=_OPCIONES_SEXO,
                index=0,
                key=f"sexo_bas_{_suf}",
            )
            # Prospecto: aviso compacto de que no se incluye rendimiento
            st.caption(
                "📌 Sin rendimiento académico (no matriculado/a). "
                "El modelo imputa con media histórica."
            )

    # -------------------------------------------------------------------------
    # BLOQUE AVANZADO — en expander
    # Los campos aquí se marcan como `_rellenado_<var>=True` SOLO si el
    # usuario activa el checkbox "He revisado mis datos avanzados".
    #
    # Histórico: antes se comparaba el valor del slider con el default
    # (heurística `abs(valor - default) > 0.05`). El problema era que el
    # default se recalculaba en cada re-render desde el contexto actual
    # (media histórica), y pequeñas variaciones de contexto entre clicks
    # disparaban falsos positivos: el flag se marcaba True aunque el usuario
    # no hubiera abierto siquiera el expander. Resultado: el dot plot
    # mostraba nota_selectividad como factor aunque el usuario no la había
    # rellenado (perfil D del testing).
    #
    # Ahora: checkbox explícito. El usuario decide si sus valores avanzados
    # deben entrar en la cascada, independientemente de si coinciden con el
    # default o no. Más transparente y defendible en tribunal.
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)

    # Cabecera con borde azul (mismo estilo que las 3 cards: Académico,
    # Personal, Socioeconómico). Se renderiza JUSTO ENCIMA del expander
    # para que visualmente formen un bloque coherente.
    st.markdown(f"""
    <div style="
        background:{COLORES['fondo']};
        border:1.5px solid {COLORES['primario']};
        border-radius:10px;
        padding:0.6rem 0.9rem;
        margin-bottom:0.3rem;
    ">
        <div style="font-size:0.85rem; font-weight:600; color:{COLORES['primario']};">
            ⚙️ Datos avanzados (opcionales — mejoran la precisión)
        </div>
    </div>
    """, unsafe_allow_html=True)

    label_exp = "Desplegar / ocultar"
    with st.expander(label_exp, expanded=False):
        st.markdown(f"""
        <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin-bottom:0.8rem;">
            Estos campos son opcionales. Si no los rellenas, el modelo
            utilizará la media histórica de tu contexto como aproximación.
        </p>
        """, unsafe_allow_html=True)

        # Checkbox global de confirmación: controla TODOS los flags
        # _rellenado_ de las variables del bloque avanzado.
        usar_avanzados = st.checkbox(
            label="✍️ He revisado mis datos avanzados · usar estos valores en el pronóstico",
            value=False,
            help=(
                "Si lo marcas, los valores que pongas abajo se usarán en tu "
                "pronóstico y aparecerán como factores en la cascada de "
                "influencias. Si no lo marcas, el modelo usará las medias "
                "históricas de tu contexto. Si no conoces algún campo concreto, "
                "déjalo en su valor por defecto."
            ),
            key=f"usar_avanzados_{_suf}",
        )

        adv1, adv2 = st.columns(2)

        with adv1:
            if modo != "en_curso":
                _default_sel = round(_med('nota_selectividad', 6.5), 1)
                perfil['nota_selectividad'] = st.slider(
                    label="Nota de selectividad",
                    # Rango 0-14: fase general (máx 10) + fase específica
                    # (hasta +4 pp por ponderaciones). Coherente con
                    # config_datos.py → 'nota_selectividad' rango (0, 14).
                    min_value=0.0, max_value=14.0,
                    value=_default_sel,
                    step=0.1,
                    key=f"selectividad_{_suf}",
                )
                # Flag controlado por el checkbox global (ver arriba)
                perfil['_rellenado_nota_selectividad'] = usar_avanzados

            _default_orden = max(1, int(_med('orden_preferencia', 1)))
            perfil['orden_preferencia'] = st.number_input(
                label="Orden de preferencia de la titulación",
                min_value=1, max_value=20,
                value=_default_orden,
                step=1,
                help="Posición en la que pediste esta titulación en la preinscripción (1 = primera opción).",
                key=f"orden_pref_{_suf}",
            )
            perfil['_rellenado_orden_preferencia'] = usar_avanzados

            if modo == "en_curso":
                _default_gap = int(_med('anios_gap', 0))
                perfil['anios_gap'] = st.number_input(
                    label="Años sin matricularse durante la carrera",
                    min_value=0, max_value=10,
                    value=_default_gap,
                    step=1,
                    help="Cursos en que no te matriculaste estando todavía en la carrera.",
                    key=f"gap_{_suf}",
                )
                perfil['_rellenado_anios_gap'] = usar_avanzados

            if modo == "en_curso":
                _val_nota_def = float(np.clip(round(_med('nota_acceso', 8.0), 1), 5.0, 14.0))
                perfil['nota_acceso'] = st.slider(
                    label="Nota de acceso (PAU / FP)",
                    min_value=5.0, max_value=14.0,
                    value=_val_nota_def,
                    step=0.1,
                    help="Nota de acceso a la universidad (escala 0–14).",
                    key=f"nota_acceso_{_suf}",
                )
                perfil['_rellenado_nota_acceso'] = usar_avanzados

        with adv2:
            perfil['universidad_origen'] = st.selectbox(
                label="Universidad de preinscripción",
                options=_OPCIONES_UNIVERSIDAD,
                index=0,
                help="Universidad a través de la cual realizaste la preinscripción. La mayoría de alumnos de bachillerato seleccionan UJI.",
                key=f"univ_origen_{_suf}",
            )
            perfil['_rellenado_universidad_origen'] = usar_avanzados

            if modo == "en_curso":
                # En prospecto, via_acceso ya está en el bloque básico
                # En en_curso no está en básico → la recogemos aquí
                perfil['via_acceso'] = st.selectbox(
                    label="Vía de acceso",
                    options=_OPCIONES_VIA_ACCESO,
                    index=0,
                    key=f"tipo_acceso_{_suf}",
                )
                perfil['_rellenado_via_acceso'] = usar_avanzados

    # -------------------------------------------------------------------------
    # Rellenar valores por defecto para features no mostradas
    # (el pipeline necesita todas las features, incluso las no introducidas)
    # -------------------------------------------------------------------------
    defaults_numericos = {
        # Variables NO disponibles para el prospecto — pasar NaN
        # para que el SimpleImputer del pipeline use su mediana del training set
        'nota_1er_anio':           np.nan,
        'cred_superados_anio_1er': np.nan,
        'creditos_superados':      np.nan,
        'tasa_rendimiento':        np.nan,
        'max_pagos':               np.nan,
        'creditos_matriculados':   np.nan,
        'indicador_interrupcion':  0,   # prospecto: asumimos que no ha interrumpido
        'anios_sin_beca':          np.nan,
        'anio_cohorte':            2020,
    }
    for col, val in defaults_numericos.items():
        if col not in perfil:
            perfil[col] = val

    # --- Derivaciones específicas de modo en_curso ---
    if modo == "en_curso":
        # anios_sin_beca: calculado a partir de años matriculado total - años con beca
        # _anios_matriculado se recoge en el bloque básico y es un campo auxiliar
        anios_mat = perfil.pop('_anios_matriculado', 1)
        n_beca    = perfil.get('n_anios_beca', 0)
        perfil['anios_sin_beca'] = max(0, int(anios_mat) - int(n_beca))

        # tasa_repeticion: derivada de cred_repetidos según la fórmula Fase 3
        # (f3_m02_agregacion.ipynb, celda 3):
        #     tasa_repeticion = (cred_repetidos / cred_titulacion) * 100
        # cred_titulacion depende de la titulación:
        #   - Medicina            → 360 ECTS
        #   - Doble Grado         → 384 ECTS
        #   - Resto (96% grados)  → 240 ECTS
        titulacion_sel = (contexto.get('valor') or '') if isinstance(contexto, dict) else ''
        if 'Medicina' in titulacion_sel:
            cred_titulacion = 360
        elif 'Doble Grado' in titulacion_sel:
            cred_titulacion = 384
        else:
            cred_titulacion = 240
        cred_rep = perfil.get('cred_repetidos', 0) or 0
        perfil['tasa_repeticion'] = (cred_rep / cred_titulacion) * 100

        # indicador_interrupcion ya viene del checkbox — no sobreescribir
        # (el default de arriba solo aplica si no estaba en perfil, lo cual
        # no ocurre en en_curso porque el checkbox siempre devuelve 0 o 1)

        # Limpiar auxiliares del formulario si existen (no son features del modelo).
        # Nota: tasa_repeticion SÍ es feature, se calcula arriba y no se limpia.
        for _aux in ('_creditos_por_curso', 'creditos_superados',
                     'creditos_matriculados', 'tasa_rendimiento'):
            perfil.pop(_aux, None)

    # Botón Calcular centrado (el botón Borrar está arriba en el bloque 1️⃣)
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([2, 1, 2])
    with col_btn:
        calcular = st.button(
            label="🔮 Calcular mi pronóstico",
            type="primary",
            width='stretch',
            key=f"btn_calcular_{modo}",
        )

    return perfil, calcular


# =============================================================================
# PASO 3: Calcular probabilidad
# =============================================================================


def _traducir_perfil_a_codigos(perfil: dict) -> dict:
    """
    Convierte los valores de texto del formulario a los códigos numéricos
    que espera el pipeline del modelo.

    El modelo fue entrenado con enteros (via_acceso=10, sexo=0, etc.).
    El formulario recoge strings legibles ("Bachiller", "Mujer").
    Esta función hace la traducción usando los mapas de config_datos.py.

    Las variables numéricas (nota_acceso, n_anios_beca, etc.) se copian tal cual.
    """
    p = dict(perfil)  # copia para no mutar el original

    # Categóricas → código numérico
    # Refactor SRC↔APP: usamos OPCIONES_*_UI (etiquetas limpias filtradas
    # de los mapas SRC) en lugar de los MAPS antiguos con bugs.
    if 'situacion_laboral' in p and isinstance(p['situacion_laboral'], str):
        p['situacion_laboral'] = OPCIONES_LABORAL_UI.get(
            p['situacion_laboral'],
            1  # default: No trabaja (código 1 en SRC, antes era 11 incorrecto)
        )

    if 'via_acceso' in p and isinstance(p['via_acceso'], str):
        p['via_acceso'] = OPCIONES_VIA_UI.get(
            p['via_acceso'],
            10  # default: Bachillerato/PAU — código más frecuente
        )

    if 'sexo' in p and isinstance(p['sexo'], str):
        p['sexo'] = OPCIONES_SEXO_UI.get(p['sexo'], 0)

    if 'universidad_origen' in p and isinstance(p['universidad_origen'], str):
        p['universidad_origen'] = OPCIONES_UNIVERSIDAD_UI.get(
            p['universidad_origen'],
            0  # default: Otra / sin datos
        )

    if 'rama' in p and isinstance(p['rama'], str):
        # Defensivo: el formulario no expone rama directamente, pero por si
        # algún flujo la incluye, mapeamos nombre completo → código.
        p['rama'] = RAMA_NOMBRE_A_CODIGO.get(p['rama'], 3)  # default SO=3

    if 'provincia' in p and isinstance(p['provincia'], str):
        # Defensivo: formulario no expone provincia. PROVINCIA_MAP de SRC.
        p['provincia'] = PROVINCIA_MAP.get(
            p['provincia'],
            0  # default: Otra / sin datos
        )

    if 'pais_nombre' in p and isinstance(p['pais_nombre'], str):
        # Defensivo: formulario no expone país. PAIS_NOMBRE_MAP de SRC.
        p['pais_nombre'] = PAIS_NOMBRE_MAP.get(
            p['pais_nombre'],
            1  # default: España
        )

    # tuvo_beca: derivado de n_anios_beca
    if 'tuvo_beca' not in p:
        p['tuvo_beca'] = 1 if p.get('n_anios_beca', 0) > 0 else 0

    # anios_sin_beca: derivado si no está
    if 'anios_sin_beca' not in p:
        carrera_anios = 4
        p['anios_sin_beca'] = max(0, carrera_anios - int(p.get('n_anios_beca', 0)))

    return p


# =============================================================================
# HELPER: convertir valor string a código numérico para columnas categóricas
# =============================================================================
# Cuando imputamos desde df_ref (meta_test_app), las columnas categóricas
# vienen como strings ("General", "Mujer"...) pero el pipeline del modelo
# espera enteros. Este helper aplica el MAP correspondiente según el nombre
# de la columna. Si no hay MAP o el valor no está mapeado, devuelve 0 (default
# seguro alineado con la regla "fillna(0)" del preprocesado en SRC).
# =============================================================================
_MAPS_CATEGORICAS = {
    'cupo': CUPO_MAP,
    'rama': RAMA_MAP,
    'situacion_laboral': OPCIONES_LABORAL_UI,
    'via_acceso': OPCIONES_VIA_UI,
    'sexo': OPCIONES_SEXO_UI,
    'universidad_origen': OPCIONES_UNIVERSIDAD_UI,
    'provincia': PROVINCIA_MAP,
    'pais_nombre': PAIS_NOMBRE_MAP,
}

def _codificar_si_string(col: str, valor):
    """Si valor es string y existe MAP para esa columna, devuelve el código
    numérico. Si ya es numérico o no hay MAP, devuelve el valor tal cual."""
    if not isinstance(valor, str):
        return valor
    mapa = _MAPS_CATEGORICAS.get(col)
    if mapa is None:
        # Sin MAP conocido → último recurso: devolver 0 para evitar
        # que pipeline.transform() falle al convertir string a float
        return 0
    return mapa.get(valor, 0)


def _codificar_df_categoricas(df: "pd.DataFrame") -> "pd.DataFrame":
    """Versión vectorizada para DataFrames completos: convierte columnas
    string de categóricas conocidas (cupo, situacion_laboral, etc.) a su
    código numérico. Devuelve una COPIA del df con las columnas transformadas.
    Las columnas numéricas o no mapeadas se dejan intactas.
    """
    df_out = df.copy()
    for col, mapa in _MAPS_CATEGORICAS.items():
        if col in df_out.columns and df_out[col].dtype == object:
            # fillna(0) en los no mapeados — alineado con regla SRC
            df_out[col] = df_out[col].map(mapa).fillna(0).astype(int)
    return df_out


def _calcular_probabilidad(perfil: dict, modelo, pipeline,
                            df_ref: pd.DataFrame) -> tuple[float | None, str | None]:
    """
    Construye un DataFrame con el perfil del usuario en el formato
    que espera el pipeline, lo transforma y predice la probabilidad.

    Estrategia de imputación (por orden de prioridad):
      1. El usuario lo rellenó → usar directamente
      2. Está en df_ref → usar media/moda del contexto
      3. No está en df_ref pero el scaler tiene su media → usar media del training set
      4. Sin información → 0

    Devuelve (probabilidad, mensaje_error).
    """
    try:
        # Traducir strings del formulario a códigos numéricos del modelo
        perfil = _traducir_perfil_a_codigos(perfil)

        # Columnas que el pipeline espera — fuente de verdad
        if hasattr(pipeline, 'feature_names_in_'):
            cols_pipeline = list(pipeline.feature_names_in_)
        else:
            cols_pipeline = [c for c in df_ref.columns if c not in _COLS_META]

        # Extraer medias del scaler para imputación correcta
        # El scaler fue entrenado con el training set — sus medias son los valores
        # más representativos para imputar cuando no tenemos otra información
        medias_scaler = {}
        try:
            num_pipeline = pipeline.named_transformers_.get('num')
            if num_pipeline and hasattr(num_pipeline, 'steps'):
                scaler = dict(num_pipeline.steps).get('scaler')
                if scaler and hasattr(scaler, 'mean_'):
                    # Las columnas del scaler son las mismas que feature_names_in_
                    for col, mean in zip(cols_pipeline, scaler.mean_):
                        medias_scaler[col] = float(mean)
        except Exception:
            pass  # Si falla, seguimos sin medias del scaler

        # Construimos la fila con EXACTAMENTE las columnas del pipeline
        fila = {}
        for col in cols_pipeline:
            if col in perfil:
                # Prioridad 1: el usuario lo rellenó
                fila[col] = perfil[col]
            elif col in df_ref.columns and df_ref[col].notna().any():
                # Prioridad 2: media/moda del contexto (df_ref)
                if df_ref[col].dtype.kind in ('f', 'i'):
                    fila[col] = float(df_ref[col].mean())
                else:
                    # Moda puede venir como string ("General", "Mujer"...)
                    # Convertimos a código numérico antes de pasar al pipeline.
                    valor_moda = df_ref[col].mode()[0]
                    fila[col] = _codificar_si_string(col, valor_moda)
            elif col in medias_scaler:
                # Prioridad 3: media del training set (del scaler)
                # Mejor que 0 — evita predicciones absurdas
                fila[col] = medias_scaler[col]
            else:
                # Prioridad 4: sin información — valor neutro
                fila[col] = 0

        X_usuario = pd.DataFrame([fila], columns=cols_pipeline)
        # Defensivo: si alguna celda quedó como NaN (p.ej. el formulario
        # devolvió None para un campo opcional no rellenado), el pipeline
        # o el modelo final (LogisticRegression del meta-learner) revientan.
        # Rellenamos NaN con 0 como último recurso (alineado con regla SRC).
        X_usuario = X_usuario.fillna(0)
        X_prep    = pipeline.transform(X_usuario)

        # El modelo fue entrenado con los nombres ORIGINALES de features
        # (cupo, anios_gap...), no con los del preprocesador (minmax__*).
        # Pasamos X_prep como numpy array directamente para evitar que el
        # modelo se queje de "feature names mismatch". El warning cosmético
        # de sklearn "X does not have valid feature names" es inofensivo.
        import numpy as _np
        if hasattr(X_prep, 'values'):
            X_prep = X_prep.values
        elif not isinstance(X_prep, _np.ndarray):
            X_prep = _np.asarray(X_prep)

        # Defensa final: si quedó algún NaN tras el pipeline, rellenar con 0.
        # El meta-learner LogisticRegression no acepta NaN.
        if _np.isnan(X_prep).any():
            X_prep = _np.nan_to_num(X_prep, nan=0.0)

        prob      = modelo.predict_proba(X_prep)[0, 1]

        return float(prob), None

    except Exception as e:
        return None, str(e)


# =============================================================================
# RESULTADO PRINCIPAL
# =============================================================================

def _mostrar_resultado_principal(prob: float, modo: str):
    """Banner con el resultado principal antes de los gráficos."""
    pct = prob * 100
    nivel, color, emoji, mensaje = _clasificar_riesgo(prob)
    _pct_txt = f"{pct:.1f}".replace('.', ',')

    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg, {color}18, {color}08);
        border:2px solid {color}60;
        border-radius:12px;
        padding:1.5rem 2rem;
        text-align:center;
        margin:0.5rem 0;
    ">
        <div style="font-size:2.5rem;">{emoji}</div>
        <div style="font-size:2rem; font-weight:bold; color:{color};">
            {_pct_txt}%
        </div>
        <div style="font-size:1.1rem; font-weight:bold; color:{COLORES['texto']};">
            Riesgo de abandono: <span style="color:{color};">{nivel}</span>
        </div>
        <div style="font-size:0.88rem; color:{COLORES['texto_suave']}; margin-top:0.4rem;">
            {mensaje}
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# GRÁFICO 1: Indicador de riesgo (velocímetro)
# =============================================================================


# _hex_to_rgba ELIMINADA (Chat p00, 28/04/2026) — sustituida por
# _hex_a_rgba de utils/ui_helpers.py para no duplicar lógica.
# Las llamadas internas de este fichero ahora usan _hex_a_rgba.



def _grafico_velocimetro_comparativa(resultados: list):
    """
    Velocímetro híbrido para comparativa de carreras:
      - 2-3 carreras → 1 velocímetro grande con N agujas (Opción D)
      - 4-5 carreras → N mini-velocímetros en grid (Opción C)
    Cada carrera mantiene su color distintivo de la paleta comparativa.
    """
    n = len(resultados)
    # Modo grid SIEMPRE: mini-velocímetros lado a lado (mejor lectura
    # que agujas solapadas en un único velocímetro, incluso con 2-3 carreras).
    cols = st.columns(n)
    for col_st, r in zip(cols, resultados):
        with col_st:
            _mini_gauge_individual(r)
    return

    # Modo agujas (2-3 carreras): un velocímetro con varias agujas
    fig = go.Figure()

    # Zonas de fondo del velocímetro (verde / amarillo / rojo)
    fig.add_trace(go.Indicator(
        mode="gauge",
        value=0,  # valor dummy — no mostramos número central
        gauge={
            'axis': {
                'range': [0, 100],
                'tickvals': [0, 30, 60, 100],
                'ticktext': ['0%', '30%', '60%', '100%'],
                'tickwidth': 1,
                'tickcolor': COLORES['texto_suave'],
            },
            'bar': {'color': 'rgba(0,0,0,0)', 'thickness': 0},  # barra invisible
            'bgcolor': 'white',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  UMBRALES['riesgo_bajo']  * 100],
                 'color': 'rgba(56,161,105,0.15)'},
                {'range': [UMBRALES['riesgo_bajo']  * 100,
                           UMBRALES['riesgo_medio'] * 100],
                 'color': 'rgba(236,201,75,0.15)'},
                {'range': [UMBRALES['riesgo_medio'] * 100, 100],
                 'color': 'rgba(229,62,62,0.15)'},
            ],
        },
        domain={'x': [0, 1], 'y': [0, 1]},
    ))

    # Una aguja desde el centro hacia el % de cada carrera
    import math
    cx, cy = 0.5, 0.27       # centro del gauge en coord paper
    longitud = 0.34          # longitud de la aguja
    for r in resultados:
        pct   = r["pct"]
        color = r["color_comp"]
        angulo_deg = 180 - (pct / 100 * 180)
        angulo_rad = math.radians(angulo_deg)
        x1 = cx + longitud * math.cos(angulo_rad)
        y1 = cy + longitud * math.sin(angulo_rad)
        # Aguja
        fig.add_shape(
            type="line",
            x0=cx, y0=cy, x1=x1, y1=y1,
            line=dict(color=color, width=3),
            xref="paper", yref="paper",
        )
    # Pivot central oscuro encima de las agujas
    fig.add_shape(
        type="circle",
        xref="paper", yref="paper",
        x0=cx - 0.018, y0=cy - 0.018,
        x1=cx + 0.018, y1=cy + 0.018,
        fillcolor=COLORES['texto'],
        line=dict(color=COLORES['texto'], width=0),
    )

    # Leyenda textual debajo (■ color · nombre · pct)
    partes_leyenda = []
    for r in resultados:
        col  = r["color_comp"]
        nom  = r["titulacion"]
        for pref in ["Grado en ", "Doble Grado en ", "Grado Universitario en "]:
            if nom.startswith(pref):
                nom = nom[len(pref):]
                break
        nom = nom[:32] + "…" if len(nom) > 32 else nom
        pct  = r["pct"]
        _pct_leyenda_txt = f"{pct:.1f}".replace('.', ',')
        partes_leyenda.append(
            f"<span style='color:{col};font-weight:bold;'>■</span> {nom} "
            f"({_pct_leyenda_txt}%)"
        )
    leyenda_html = " &nbsp;·&nbsp; ".join(partes_leyenda)

    fig.update_layout(
        separators=",.",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=10),
        height=260,
        showlegend=False,
    )

    st.plotly_chart(fig, width='stretch', key="velocimetro_comparativa")
    st.markdown(
        f"<p style='font-size:0.78rem; color:{COLORES['texto_suave']}; "
        f"text-align:center; margin-top:-0.5rem;'>{leyenda_html}</p>",
        unsafe_allow_html=True
    )


def _mini_gauge_individual(r: dict):
    """Mini-velocímetro individual para grid de 4-5 carreras (modo C).
    r contiene: titulacion (nombre), pct (0-100), color_comp (hex)."""
    pct   = r["pct"]
    color = r["color_comp"]
    # Auditoría p03 (Chat p03, 27/04/2026): se usa el helper centralizado
    # _nombre_titulacion_corto en vez de la lógica local que truncaba
    # con "…" a 18 caracteres. Ahora el nombre se parte en 2 líneas con <br>
    # para que entre completo (24 chars + 24 chars). Helper consistente con
    # el resto de la app y maneja correctamente "Doble Grado en ...".
    nom = _nombre_titulacion_corto(r["titulacion"], partir_lineas=True, max_chars=24)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={'suffix': '%', 'font': {'size': 22, 'color': color}},
        gauge={
            'axis': {'range': [0, 100], 'tickvals': [0, 50, 100],
                     'tickfont': {'size': 8, 'color': COLORES['texto_suave']}},
            'bar': {'color': color, 'thickness': 0.25},
            'bgcolor': 'white',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  UMBRALES['riesgo_bajo']  * 100],
                 'color': 'rgba(56,161,105,0.15)'},
                {'range': [UMBRALES['riesgo_bajo']  * 100,
                           UMBRALES['riesgo_medio'] * 100],
                 'color': 'rgba(236,201,75,0.15)'},
                {'range': [UMBRALES['riesgo_medio'] * 100, 100],
                 'color': 'rgba(229,62,62,0.15)'},
            ],
        },
        domain={'x': [0, 1], 'y': [0, 1]},
    ))
    fig.update_layout(
        separators=",.",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        height=170,
        showlegend=False,
    )
    # Key con titulación completa (no el 'nom' truncado) para evitar colisiones
    # si 2 titulaciones comparten los primeros 18 chars + mismo pct.
    _key = f"mini_gauge_{r['titulacion']}_{pct:.2f}"
    st.plotly_chart(fig, width='stretch', key=_key)
    st.markdown(
        f"<p style='font-size:0.78rem; color:{color}; font-weight:500; "
        f"text-align:center; margin-top:-0.6rem;'>{nom}</p>",
        unsafe_allow_html=True
    )


def _kpis_resumen(prob: float, perfil: dict, contexto: dict,
                   df_ctx: pd.DataFrame, df_ref: pd.DataFrame):
    """Fila de 4 KPIs compactos con lectura rápida del resultado.

    KPIs:
      1. Riesgo personal (%) con delta vs media UJI
      2. Media del contexto (%)
      3. Percentil del alumno en su contexto
      4. Factor clave (variable con mayor peso del perfil)
    """
    # Tasa media UJI — leída de metricas_modelo.json (sin fallback numérico
    # obsoleto: si JSON falla, fallback con valor real del JSON actual
    # — main.py ya valida la existencia de tasa_abandono al arrancar).
    try:
        _m_ps     = _leer_metricas_modelo()
        _tasa_val = _m_ps.get("tasa_abandono")
        media_uji = float(_tasa_val) * 100 if _tasa_val is not None else 29.25
    except Exception:
        media_uji = 29.25  # red de seguridad — main.py ya hace validación previa

    # KPI 2: media del contexto (titulación/rama/todas)
    if df_ctx is not None and 'abandono' in df_ctx.columns and len(df_ctx) > 0:
        media_ctx_pct = float(df_ctx['abandono'].mean()) * 100
        nombre_ctx = contexto.get('valor') or 'UJI completo'
    else:
        media_ctx_pct = media_uji
        nombre_ctx = 'UJI completo'

    # KPI 3: ranking del alumno por NOTA de acceso dentro del contexto.
    # Mide el % de alumnos del contexto con nota INFERIOR a la del usuario.
    # Rápido (sin predicción), intuitivo y aporta info nueva al resto de KPIs.
    ranking_nota = None
    nota_alumno = perfil.get('nota_acceso')
    if (df_ctx is not None and len(df_ctx) > 0
            and 'nota_acceso' in df_ctx.columns
            and nota_alumno is not None):
        try:
            nota_alumno_f = float(nota_alumno)
            notas = df_ctx['nota_acceso'].dropna()
            if len(notas) > 0:
                ranking_nota = int((notas < nota_alumno_f).mean() * 100)
        except Exception:
            ranking_nota = None

    # KPI 4: factor clave — variable con mayor peso según diferencia
    # de medias del perfil vs la media del contexto (proxy simple).
    factores_top = [
        ('nota_acceso', 'Nota de acceso'),
        ('n_anios_beca', 'Años con beca'),
        ('n_anios_trabajando', 'Años trabajando'),
        ('edad_entrada', 'Edad de entrada'),
    ]
    factor_clave = 'Nota de acceso'
    if df_ctx is not None and len(df_ctx) > 0:
        max_z = -1.0
        for col, nombre in factores_top:
            if col in df_ctx.columns and col in perfil:
                try:
                    val_usuario = float(perfil[col])
                    media_col = float(df_ctx[col].mean())
                    std_col = float(df_ctx[col].std()) or 1.0
                    z = abs((val_usuario - media_col) / std_col)
                    if z > max_z:
                        max_z = z
                        factor_clave = nombre
                except Exception:
                    pass

    nivel, color, _, _ = _clasificar_riesgo(prob)
    delta_pp = prob * 100 - media_uji
    # Formato español: coma decimal (variables intermedias para evitar
    # f-strings anidadas con comillas, no soportadas en todas las versiones).
    delta_txt = (
        f"{'+' if delta_pp >= 0 else ''}{delta_pp:.1f}pp vs media UJI"
    ).replace(".", ",")
    _prob_kpi_txt       = f"{prob*100:.1f}".replace('.', ',')
    _media_ctx_kpi_txt  = f"{media_ctx_pct:.1f}".replace('.', ',')

    # -------------------------------------------------------------------------
    # Auditoría p03 (Chat p03): renderizado migrado a _tarjeta_kpi de
    # utils/ui_helpers.py para apariencia IDÉNTICA a p02 (border-left:4px,
    # etiqueta MAYÚSCULA con CSS text-transform:uppercase, valor 1.7rem,
    # padding y altura uniforme). Antes vivía con cards inline border-top:3px
    # que rompían la coherencia visual con el resto de la app.
    #
    # Mapeo de colores semánticos (alineado con p02):
    #   🎯 RIESGO PERSONAL → color del nivel (verde/ámbar/rojo) — el dato
    #                         más importante: la barra refleja el nivel.
    #   📚 MEDIA CONTEXTO  → primario (azul) — informativo neutro
    #   📏 RANKING DE NOTA → texto_muy_suave (gris) — métrica auxiliar
    #   🔑 FACTOR CLAVE    → primario (azul) — informativo neutro
    # -------------------------------------------------------------------------

    # KPI 1: riesgo personal — barra del color del nivel
    # delta_color: el delta indica si estás POR ENCIMA (peor=red) o
    # POR DEBAJO (mejor=green) de la media UJI.
    _delta_color_k1 = "red" if delta_pp > 0 else ("green" if delta_pp < 0 else "gray")
    html_k1 = _tarjeta_kpi(
        icono="🎯",
        etiqueta="Riesgo personal",
        valor=f"{_prob_kpi_txt}%",
        delta=f"{nivel} · {delta_txt}",
        delta_color=_delta_color_k1,
        tooltip="Probabilidad estimada de abandono según tu perfil. "
                "El delta (pp = puntos porcentuales) compara con la media UJI "
                f"({media_uji:.1f}%).".replace(".", ","),
        color_barra=color,   # verde / ámbar / rojo según el nivel
    )

    # KPI 2: media contexto — barra azul primario
    nombre_corto = nombre_ctx[:24] + "…" if len(nombre_ctx) > 24 else nombre_ctx
    html_k2 = _tarjeta_kpi(
        icono="📚",
        etiqueta="Media contexto",
        valor=f"{_media_ctx_kpi_txt}%",
        delta=nombre_corto,
        delta_color="gray",
        tooltip="Tasa real de abandono observada en el contexto seleccionado "
                "(titulación, rama o UJI completo).",
        color_barra=COLORES["primario"],
    )

    # KPI 3: ranking de nota — barra gris (métrica auxiliar)
    if ranking_nota is not None:
        valor_k3 = f"{ranking_nota}%"
        nota_txt = f"{float(nota_alumno):.1f}".replace(".", ",") if nota_alumno else "—"
        delta_k3 = f"alumnos con nota peor · tu nota: {nota_txt}"
    else:
        valor_k3 = "—"
        delta_k3 = "sin datos de nota"
    html_k3 = _tarjeta_kpi(
        icono="📏",
        etiqueta="Ranking de nota",
        valor=valor_k3,
        delta=delta_k3,
        delta_color="gray",
        tooltip="Porcentaje de alumnos del contexto con nota de acceso "
                "INFERIOR a la tuya. Cuanto mayor, mejor posicionada está "
                "tu nota dentro del contexto.",
        color_barra=COLORES["texto_muy_suave"],
    )

    # KPI 4: factor clave — barra azul primario
    html_k4 = _tarjeta_kpi(
        icono="🔑",
        etiqueta="Factor clave",
        valor=factor_clave,
        delta="Mayor desviación en tu perfil",
        delta_color="gray",
        tooltip="Variable de tu perfil con mayor desviación respecto a la "
                "media del contexto (z-score absoluto). Es el factor que más "
                "te diferencia del alumnado típico de tu contexto.",
        color_barra=COLORES["primario"],
    )

    # Renderizar las 4 tarjetas en una fila
    cols = st.columns(4)
    cols[0].markdown(html_k1, unsafe_allow_html=True)
    cols[1].markdown(html_k2, unsafe_allow_html=True)
    cols[2].markdown(html_k3, unsafe_allow_html=True)
    cols[3].markdown(html_k4, unsafe_allow_html=True)


def _grafico_historico_scatter(prob: float, contexto: dict,
                                 df_ref: pd.DataFrame,
                                 perfil: dict = None):
    """Histograma compacto de la distribución de notas de acceso del
    contexto, con una línea vertical marcando la nota del usuario.
    Sirve para visualizar de un vistazo dónde se sitúa el alumno
    respecto al resto de alumnos del contexto elegido (titulación,
    rama o toda UJI)."""
    df_ctx_plot = contexto.get('df_contexto')
    if df_ctx_plot is None or len(df_ctx_plot) == 0 \
       or 'nota_acceso' not in df_ctx_plot.columns:
        st.info("Sin datos suficientes para el histórico del contexto.")
        return

    notas = df_ctx_plot['nota_acceso'].dropna()
    if len(notas) == 0:
        st.info("Sin notas de acceso disponibles en el contexto.")
        return

    nota_usuario = None
    if perfil is not None and perfil.get('nota_acceso') is not None:
        try:
            nota_usuario = float(perfil['nota_acceso'])
        except Exception:
            nota_usuario = None
    media_notas = float(notas.mean())

    nombre_ctx = contexto.get('valor') or 'UJI completo'

    st.markdown(f"""
    <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0.3rem 0 0.2rem 0;">
        📊 Distribución de notas · <strong>{nombre_ctx}</strong>
    </p>
    """, unsafe_allow_html=True)
    import plotly.graph_objects as _go
    fig = _go.Figure()

    # Histograma de notas del contexto
    fig.add_trace(_go.Histogram(
        x=notas,
        nbinsx=30,
        marker=dict(color=COLORES['primario'], opacity=0.45),
        name='Contexto',
        hovertemplate='Nota %{x:,.1f}<br>%{y} alumnos<extra></extra>',
    ))

    # Línea vertical: media del contexto (gris oscuro, anclada abajo)
    fig.add_vline(
        x=media_notas,
        line=dict(color=COLORES['texto'], width=1.5, dash='dash'),
        annotation_text=f"Media: {media_notas:.1f}".replace(".", ","),
        annotation_position="bottom left",
        annotation_font=dict(size=11, color=COLORES['texto']),
        annotation_bgcolor="rgba(255,255,255,0.85)",
    )

    # Línea vertical: nota del usuario (verde si por encima de media, rojo si debajo)
    # Auditoría p03 (Chat p03): hex #1D9E75/#C53030 → COLORES['exito']/COLORES['abandono'].
    if nota_usuario is not None:
        col_user = (COLORES['exito']
                    if nota_usuario >= media_notas
                    else COLORES['abandono'])
        fig.add_vline(
            x=nota_usuario,
            line=dict(color=col_user, width=3),
            annotation_text=f"Tu nota: {nota_usuario:.1f}".replace(".", ","),
            annotation_position="top right",
            annotation_font=dict(size=11, color=col_user),
            annotation_bgcolor="rgba(255,255,255,0.85)",
        )

    fig.update_layout(
        separators=",.",
        xaxis_title=None,
        yaxis_title="Nº alumnos",
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=200,
        margin=dict(l=40, r=10, t=5, b=5),
        showlegend=False,
        xaxis=dict(range=[max(0, float(notas.min()) - 0.5),
                           min(14, float(notas.max()) + 0.5)],
                   showgrid=True,
                   gridcolor=COLORES['borde']),
        yaxis=dict(showgrid=True, gridcolor=COLORES['borde']),
    )
    # Key única: prob + contexto (tipo+valor) para evitar colisiones si 2
    # llamadas distintas tienen la misma prob.
    _ctx_key = f"{contexto.get('tipo','x')}_{str(contexto.get('valor','x'))[:20]}"
    st.plotly_chart(fig, width='stretch',
                     key=f'historico_nota_{prob:.4f}_{_ctx_key}')


def _grafico_indicador_riesgo(prob: float, modo: str = "prospecto"):
    """
    Velocímetro semicircular con la probabilidad de abandono.
    La aguja apunta al valor predicho. Verde → amarillo → rojo.
    Delta muestra la diferencia respecto a la media UJI.
    """
    # media_uji — leída de metricas_modelo.json (sin fallback numérico
    # obsoleto: si JSON falla, fallback con valor real del JSON actual
    # — main.py ya valida la existencia de tasa_abandono al arrancar).
    try:
        _m_ig     = _leer_metricas_modelo()
        _tasa_val = _m_ig.get("tasa_abandono")
        media_uji = float(_tasa_val) * 100 if _tasa_val is not None else 29.25
    except Exception:
        media_uji = 29.25  # red de seguridad — main.py ya hace validación previa
    st.markdown(f"""
    <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0.3rem 0 0.2rem 0;">
        🎯 Tu riesgo personal
    </p>
    """, unsafe_allow_html=True)

    pct = prob * 100
    _, color, _, _ = _clasificar_riesgo(prob)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct,
        number={'suffix': '%', 'font': {'size': 36, 'color': color}},
        delta={
            'reference': media_uji,
            'increasing': {'color': COLORES['abandono']},
            'decreasing': {'color': COLORES['exito']},
            'suffix': ' pp vs media UJI',
        },
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': COLORES['texto_suave'],
                'tickvals': [0, 30, 60, 100],
                'ticktext': ['0%', '30%', '60%', '100%'],
            },
            'bar': {'color': color, 'thickness': 0.25},
            'bgcolor': 'white',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  UMBRALES['riesgo_bajo']  * 100],
                 'color': 'rgba(56,161,105,0.15)'},   # verde suave
                {'range': [UMBRALES['riesgo_bajo']  * 100,
                           UMBRALES['riesgo_medio'] * 100],
                 'color': 'rgba(236,201,75,0.15)'},   # amarillo suave
                {'range': [UMBRALES['riesgo_medio'] * 100, 100],
                 'color': 'rgba(229,62,62,0.15)'},    # rojo suave
            ],
            'threshold': {
                'line': {'color': COLORES['texto'], 'width': 3},
                'thickness': 0.75,
                'value': pct,
            },
        },
        title={
            'text': (
                # Auditoría p03 (Chat p03, 27/04/2026): antes "media UJI = 29.2%"
                # estaba HARDCODEADO. Ahora se lee de metricas_modelo.json
                # vía media_uji (línea ~2198) y se formatea con coma decimal.
                "Probabilidad de abandono predicha<br>"
                "<span style='font-size:0.8em;color:gray'>"
                f"Referencia: media UJI = {media_uji:.1f}%".replace(".", ",") +
                "</span>"
            ),
            'font': {'size': 14},
        },
        domain={'x': [0, 1], 'y': [0, 1]},
    ))

    fig.update_layout(
        separators=",.",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=5),
        height=200,
    )

    st.plotly_chart(fig, width='stretch', key=f"indicador_riesgo_{modo}")


# =============================================================================
# GRÁFICO 2: Radar — tu perfil vs éxito Y vs abandono (2 líneas de referencia)
# =============================================================================

def _grafico_radar(perfil: dict, df_ref: pd.DataFrame,
                   contexto: dict, prob: float, key_suffix: str = ""):
    """
    Gráfico de araña con 3 trazas:
      - Perfil de éxito  (azul) — media de los que NO abandonaron
      - Perfil de abandono (rojo) — media de los que SÍ abandonaron
      - Tu perfil         (verde/amarillo/rojo según riesgo)

    Cada eje es una variable numérica normalizada a 0-1 usando los
    rangos del dataset completo (para comparabilidad).

    Bug fix (Chat p03, 27/04/2026): añadido key_suffix para evitar
    StreamlitDuplicateElementKey cuando el radar se renderiza varias veces
    en la misma sesión (ej: contexto principal + dentro de expander de
    comparativa con la misma titulación).
    """
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin-bottom:0.3rem;">
        🕸️ Tu perfil vs perfiles de referencia
    </h4>
    """, unsafe_allow_html=True)

    df_ctx = contexto['df_contexto']

    # Variables a mostrar — ajustadas según modo (prospecto sin nota_1er_anio)
    # Refactor SRC↔APP: corregido bug histórico — antes se usaba 'edad_acceso'
    # que no existe como columna del modelo. El nombre correcto es 'edad_entrada'
    # (ver FEATURES_NUM_MODELO en src/config_entorno.py). Eran el mismo concepto
    # con dos nombres; se ha unificado a 'edad_entrada'.
    vars_radar = ['nota_acceso', 'n_anios_beca', 'edad_entrada',
                  'nota_selectividad', 'tasa_rendimiento']
    if 'nota_1er_anio' in perfil and perfil.get('nota_1er_anio', None) is not None:
        vars_radar = ['nota_acceso', 'nota_1er_anio', 'n_anios_beca',
                      'tasa_rendimiento', 'edad_entrada']

    vars_ok = [v for v in vars_radar if v in df_ctx.columns]

    if len(vars_ok) < 3:
        st.info("No hay suficientes variables para el gráfico de radar.")
        return

    # Perfiles de referencia en el contexto elegido
    if 'abandono' in df_ctx.columns:
        df_exito    = df_ctx[df_ctx['abandono'] == 0]
        df_abandona = df_ctx[df_ctx['abandono'] == 1]
        exito_vals    = df_exito[vars_ok].mean()
        abandono_vals = df_abandona[vars_ok].mean()
    else:
        exito_vals    = df_ctx[vars_ok].mean()
        abandono_vals = df_ctx[vars_ok].mean()

    usuario_vals = pd.Series({v: float(perfil.get(v, df_ref[v].mean()
                                                   if v in df_ref.columns else 0))
                               for v in vars_ok})

    # Normalización a 0-1 usando los rangos del dataset completo
    for v in vars_ok:
        vmin  = df_ref[v].min() if v in df_ref.columns else 0
        vmax  = df_ref[v].max() if v in df_ref.columns else 1
        rango = vmax - vmin if vmax != vmin else 1
        exito_vals[v]    = (exito_vals[v]    - vmin) / rango
        abandono_vals[v] = (abandono_vals[v] - vmin) / rango
        usuario_vals[v]  = (usuario_vals[v]  - vmin) / rango

    nombres_ejes = [NOMBRES_VARIABLES.get(v, v.replace('_', ' ').title())
                    for v in vars_ok]
    # Cerramos el polígono repitiendo el primer valor
    nombres_c    = nombres_ejes + [nombres_ejes[0]]
    exito_c      = list(exito_vals.values)    + [exito_vals.values[0]]
    abandono_c   = list(abandono_vals.values) + [abandono_vals.values[0]]
    usuario_c    = list(usuario_vals.values)  + [usuario_vals.values[0]]

    _, color_usuario, _, _ = _clasificar_riesgo(prob)

    fig = go.Figure()

    # Traza 1: Perfil de éxito (azul)
    fig.add_trace(go.Scatterpolar(
        r=exito_c, theta=nombres_c,
        fill='toself',
        fillcolor='rgba(49,130,206,0.12)',
        line=dict(color=COLORES['primario'], width=2),
        name='No abandona (éxito)',
    ))

    # Traza 2: Perfil de abandono (rojo)
    fig.add_trace(go.Scatterpolar(
        r=abandono_c, theta=nombres_c,
        fill='toself',
        fillcolor='rgba(229,62,62,0.08)',
        line=dict(color=COLORES['abandono'], width=2, dash='dot'),
        name='Abandona',
    ))

    # Traza 3: Tu perfil (color según riesgo)
    fig.add_trace(go.Scatterpolar(
        r=usuario_c, theta=nombres_c,
        fill='toself',
        fillcolor=_hex_a_rgba(color_usuario, 0.18),
        line=dict(color=color_usuario, width=2.5, dash='dash'),
        name='Tu perfil',
    ))

    nombre_ctx = contexto['valor'] or "toda la UJI"
    fig.update_layout(
        separators=",.",
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                ticktext=['0%', '25%', '50%', '75%', '100%'],
                tickfont=dict(size=9),
            ),
            bgcolor="white",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.20,
                    font=dict(size=10)),
        paper_bgcolor="white",
        margin=dict(l=40, r=40, t=30, b=70),
        height=360,
    )

    # Key único derivado del contexto + sufijo opcional para evitar
    # DuplicateElementId cuando se renderiza varias veces (ej: expanders
    # de comparativa con la misma titulación que el contexto principal).
    _sfx = f"_{key_suffix}" if key_suffix else ""
    _key = f"radar_{contexto.get('tipo','x')}_{contexto.get('valor','x')}{_sfx}"
    st.plotly_chart(fig, width='stretch', key=_key)
    st.caption(
        f"💡 Comparativa sobre alumnos de {nombre_ctx}. "
        "Cuanto más cerca del borde exterior, mejor en esa variable."
    )


# =============================================================================
# SELECTOR GLOBAL: metodo de calculo del dot plot (Rapido vs Preciso)
# Anadido en Bloque 4 PASO 3 (29/04/2026)
# =============================================================================

def _selector_metodo_global(key_suffix: str = "") -> str:
    """
    Renderiza un selector st.radio horizontal con dos opciones:
      - Rapido (proxy heuristico, instantaneo, default)
      - Preciso (SHAP exacto agnostico al modelo, opt-in)

    Devuelve "rapido" o "preciso" segun la eleccion del usuario.

    Tooltip explicativo (icono ?) con la justificacion de UX. El selector
    se renderiza una sola vez por pagina y su valor se aplica a TODOS los
    dot plots que se pinten despues (Opcion 2 - selector global).

    PASO 3 (Bloque 4): selector decorativo — su valor se pasa a
    _grafico_cascada pero AUN NO se usa para alternar el metodo. La
    conexion real con _contribuciones_shap se hace en el PASO 4.

    Parameters
    ----------
    key_suffix : str
        Sufijo unico para la key del st.radio. Necesario porque el
        selector puede aparecer mas de una vez en la misma sesion
        (p03 simple vs p03 comparativa) y Streamlit exige keys unicas.

    Returns
    -------
    str
        "rapido" o "preciso"
    """
    # Tooltip con la justificacion de UX (decision Bloque 4 - opcion D)
    tooltip = (
        "Decisión de diseño UX para una app de despliegue público dirigida "
        "a estudiantes y orientadores. El método rápido (heurístico) es "
        "interpretable sin conocimientos técnicos previos y garantiza tiempo "
        "de respuesta inmediato. El método preciso (SHAP) es matemáticamente "
        "exacto sobre el modelo entrenado, opt-in para usuarios técnicos. "
        "Coherente con patrón estándar de UX (rápido por defecto, "
        "avanzado bajo demanda)."
    )

    eleccion = st.radio(
        label="Cómo calcular los factores",
        options=["⚡ Rápido", "🔬 Preciso"],
        index=0,                      # default = Rapido
        horizontal=True,
        key=f"metodo_dotplot_{key_suffix}",
        help=tooltip,
    )

    # Aviso UX honesto: Streamlit dispara rerun al cambiar el radio, lo
    # que obliga a recalcular el pronóstico. Decisión consciente para
    # garantizar que el usuario vea siempre valores coherentes con el
    # método activo, sin caché latente que pudiera mostrar resultados
    # antiguos. La mejora con cacheo selectivo queda apuntada como
    # mejora UX para post-defensa.
    st.caption(
        "💡 Si cambias el método o cualquier dato del perfil, "
        "deberás pulsar de nuevo **Calcular mi pronóstico**."
    )

    # Normalizar a "rapido" / "preciso" (sin emojis ni acentos)
    return "preciso" if "Preciso" in eleccion else "rapido"


# =============================================================================
# GRÁFICO 3: Cascada de contribuciones
#            Con selector de método: rápido (proxy) vs preciso (SHAP)
# =============================================================================

def _grafico_cascada(perfil: dict, df_ref: pd.DataFrame,
                     prob: float, modelo, pipeline,
                     key_suffix: str = "",
                     modo: str = "prospecto",
                     metodo: str = "rapido"):
    """
    Dot plot de impacto de factores (antes era cascada/waterfall).

    key_suffix: identificador único (p.ej. titulación) para evitar keys
    duplicadas cuando se renderizan varios dot plots con la misma prob.

    modo: "prospecto" (excluye variables académicas del 1er año) o
    "en_curso" (las incluye).

    metodo: "rapido" (proxy heurístico, instantáneo, default) o "preciso"
    (SHAP exacto sobre el modelo entrenado, agnóstico al modelo). El
    selector se controla globalmente desde la función llamadora — aquí
    solo se recibe el parámetro.

    PASO 4 (Bloque 4): el parámetro 'metodo' está activo. Bifurca entre
    _contribuciones_proxy (rápido) y _contribuciones_shap (preciso, agnóstico
    al modelo). Si SHAP falla, las 3 capas de defensa internas caen
    automáticamente al método rápido sin cortar la experiencia del usuario.
    """
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin-bottom:0.3rem;">
        📊 ¿Qué factores influyen en tu riesgo?
    </h4>
    """, unsafe_allow_html=True)

    # PASO 4 (Bloque 4): bifurcación según el método elegido por el usuario.
    # - "rapido"  → proxy heurístico (instantáneo, descripción empírica)
    # - "preciso" → SHAP exacto sobre el modelo entrenado (TreeExplainer/
    #   LinearExplainer/EBM nativo según familia detectada)
    #
    # Si SHAP falla por cualquier motivo (incompatibilidad de versiones,
    # NaN/inf, valores anómalos, modelo desconocido…), las 3 capas de
    # defensa de _contribuciones_shap caen automáticamente a
    # _contribuciones_proxy. La app NUNCA queda sin contribuciones.
    if metodo == "preciso":
        contribuciones = _contribuciones_shap(perfil, df_ref, modelo, pipeline)
    else:
        contribuciones = _contribuciones_proxy(perfil, df_ref, modo=modo)

    if not contribuciones:
        st.info(
            "No hay suficientes datos rellenados para mostrar los factores. "
            "Completa más campos del perfil para ver el análisis."
        )
        return

    _renderizar_waterfall(contribuciones, prob, df_ref, key_suffix=key_suffix)


def _contribuciones_proxy(perfil: dict, df_ref: pd.DataFrame,
                            modo: str = "prospecto") -> list[dict]:
    """
    Método rápido: para cada variable, calcula cuánto difiere la tasa
    de abandono media del grupo del usuario respecto a la media general.
    Es una aproximación marginal (no considera interacciones).

    Filtrado de variables:
      - En modo 'prospecto' se EXCLUYEN variables académicas (nota_1er_anio,
        cred_superados_anio_1er) porque un futuro estudiante aún no las tiene.
      - Variables que el usuario NO haya rellenado explícitamente (flag
        `_rellenado_` en el perfil) se excluyen para no falsear la cascada
        con valores imputados.
      - Se descartan contribuciones con magnitud < 0.5 pp (ruido).
    """
    prob_base = df_ref['abandono'].mean() \
        if 'abandono' in df_ref.columns else _leer_metricas_modelo().get("tasa_abandono", 0.2925)

    # Variables candidatas según modo
    vars_cascada_base = ['nota_acceso', 'situacion_laboral', 'n_anios_beca',
                          'edad_entrada', 'via_acceso', 'nota_selectividad']
    vars_cascada_curso = ['nota_1er_anio', 'tasa_rendimiento']

    if modo == "en_curso":
        vars_cascada = vars_cascada_base + vars_cascada_curso
    else:
        # Prospecto: excluimos variables académicas (aún no existen)
        vars_cascada = vars_cascada_base

    # Solo variables que el usuario haya indicado (rellenado) y existan en df_ref.
    # Si el perfil tiene marcador explícito `_rellenado_<var>`=False, excluir.
    def _rellenada(v: str) -> bool:
        marcador = f"_rellenado_{v}"
        if marcador in perfil:
            return bool(perfil[marcador])
        # Fallback defensivo: considerar rellenada si el valor no es None ni NaN
        val = perfil.get(v)
        if val is None:
            return False
        try:
            if isinstance(val, float) and np.isnan(val):
                return False
        except Exception:
            pass
        return True

    vars_ok = [v for v in vars_cascada
               if v in perfil and v in df_ref.columns and _rellenada(v)]

    contribuciones = []
    for v in vars_ok:
        val_usuario = perfil[v]
        # Forzar tipo numérico para comparación segura
        try:
            val_usuario = float(val_usuario)
        except (TypeError, ValueError):
            val_usuario = 0.0

        if df_ref[v].dtype.kind in ('f', 'i'):
            q33 = float(df_ref[v].quantile(0.33))
            q66 = float(df_ref[v].quantile(0.66))
            if val_usuario <= q33:
                grupo = df_ref[df_ref[v] <= q33]
                etiqueta = f"bajo ({val_usuario:.1f})"
            elif val_usuario <= q66:
                grupo = df_ref[(df_ref[v] > q33) & (df_ref[v] <= q66)]
                etiqueta = f"medio ({val_usuario:.1f})"
            else:
                grupo = df_ref[df_ref[v] > q66]
                etiqueta = f"alto ({val_usuario:.1f})"
        else:
            grupo    = df_ref[df_ref[v] == val_usuario]
            etiqueta = str(val_usuario)

        contribucion = (grupo['abandono'].mean() - prob_base) \
            if len(grupo) > 0 and 'abandono' in grupo.columns else 0.0

        nombre = NOMBRES_VARIABLES.get(v, v.replace('_', ' ').title())
        contribuciones.append({
            'variable':     nombre,
            'valor':        etiqueta,
            'contribucion': float(contribucion),
        })

    # Filtrar contribuciones <0.5 pp (ruido) — no aportan al dot plot
    contribuciones = [c for c in contribuciones
                      if abs(c['contribucion']) >= 0.005]

    # Ordenar por valor absoluto, top 6
    contribuciones.sort(key=lambda x: abs(x['contribucion']), reverse=True)
    return contribuciones[:6]


def _contribuciones_shap(perfil: dict, df_ref: pd.DataFrame,
                          modelo, pipeline) -> list[dict]:
    """
    Metodo PRECISO: SHAP agnostico al modelo (refactor Bloque 4 - opcion D).

    COBERTURA DE SHAP - JUSTIFICACION METODOLOGICA
    ===============================================
    Familias con SHAP/explainer EXACTO (~72% de los 69 modelos Fase 5):
      - Gradient boosting: LightGBM, CatBoost, XGBoost, GradientBoosting
        (sklearn) -> TreeExplainer
      - Bosques: RandomForest, ExtraTrees, AdaBoost, DecisionTree, Bagging
        (con base de arbol) -> TreeExplainer
      - Lineales: LogisticRegression, SGD, Perceptron, LDA, SVM_lineal,
        RidgeClassifier, PassiveAggressive -> LinearExplainer
      - EBM (Explainable Boosting Machine, Nori et al. 2019, Microsoft
        Research) -> explainer nativo InterpretML

    Familias con HEURISTICA TRANSPARENTE (aviso + metodo rapido):
      - Stacking, Voting -> SHAP por cadena requiere promediado de
        estimadores base ponderado por meta-learner; aproximacion no exacta
        (Lundberg et al., 2020). Ademas Voting quedo en Fase 5 m06 con
        AUC=0,9254 (por debajo de gradient boosting individuales).
      - Naive Bayes, KNN, SVM RBF, MLP -> KernelExplainer requerido, lento
        y no exacto. Modelos descartados en AutoML (M01-M05) y Fase 5 m02-m04
        por rendimiento por debajo de gradient boosting.

    Decision metodologica: cubrir SHAP exacto solo para familias tecnicamente
    directas Y competitivas en la fase de seleccion. El resto recibe metodo
    heuristico con aviso al usuario, preservando la trazabilidad
    AutoML -> Fase 5 -> Fase 7 (app).

    3 capas de defensa:
      1. Deteccion de tipo de modelo (whitelist por familia)
      2. Validacion de salida (NaN, inf, valores anomalos)
      3. try/except global con fallback a _contribuciones_proxy
    """
    # -- Capa 0: importacion lazy de SHAP --------------------------------------
    try:
        import shap  # solo se carga si el usuario elige metodo preciso
    except ImportError:
        st.error("❌ La librería SHAP no está instalada. Usando método rápido.")
        return _contribuciones_proxy(perfil, df_ref)

    # Variable referenciada en el except global (evita NameError si peta antes)
    modelo_final = modelo

    with st.spinner("🔬 Calculando contribuciones SHAP..."):
        try:
            # -- Preparar datos del usuario (igual que _calcular_probabilidad) --
            perfil = _traducir_perfil_a_codigos(perfil)
            cols_features = (
                list(pipeline.feature_names_in_)
                if hasattr(pipeline, 'feature_names_in_')
                else [c for c in df_ref.columns if c not in _COLS_META]
            )
            fila = {}
            for col in cols_features:
                if col in perfil:
                    fila[col] = perfil[col]
                elif col in df_ref.columns:
                    if df_ref[col].dtype.kind in ('f', 'i'):
                        fila[col] = df_ref[col].mean()
                    else:
                        if df_ref[col].notna().any():
                            valor_moda = df_ref[col].mode()[0]
                            fila[col] = _codificar_si_string(col, valor_moda)
                        else:
                            fila[col] = 0
                else:
                    fila[col] = 0
            X_usuario = pd.DataFrame([fila])
            X_prep    = pipeline.transform(X_usuario)

            # -- Capa 1: detectar tipo de modelo (whitelist por familia) -------
            modelo_final = modelo
            if hasattr(modelo, 'named_steps'):
                modelo_final = modelo.named_steps.get('model', modelo)
            nombre_clase = type(modelo_final).__name__

            # Whitelists por familia (basadas en clase del estimador)
            FAMILIAS_TREE = {
                'LGBMClassifier', 'CatBoostClassifier', 'XGBClassifier',
                'RandomForestClassifier', 'ExtraTreesClassifier',
                'GradientBoostingClassifier', 'AdaBoostClassifier',
                'DecisionTreeClassifier',
            }
            FAMILIAS_LINEAR = {
                'LogisticRegression', 'SGDClassifier', 'Perceptron',
                'LinearDiscriminantAnalysis', 'LinearSVC',
                'RidgeClassifier', 'PassiveAggressiveClassifier',
            }
            FAMILIAS_EBM = {'ExplainableBoostingClassifier'}
            FAMILIAS_AVISO = {  # ensembles complejos + descartados Fase 5
                'StackingClassifier', 'VotingClassifier',
                'BernoulliNB', 'GaussianNB', 'KNeighborsClassifier',
                'SVC', 'MLPClassifier',
            }

            # -- Capa 2: ramificar segun familia -------------------------------
            vals = None  # SHAP values (clase 1, primera fila)
            prob_pred = 0.5  # fallback razonable; se sobreescribe en cada rama

            # --- Caso A: arboles (gradient boosting + bosques) ----------------
            if nombre_clase in FAMILIAS_TREE:
                explainer = shap.TreeExplainer(modelo_final)
                shap_vals = explainer.shap_values(X_prep)
                # Normalizar formato (puede ser array o lista segun version)
                if isinstance(shap_vals, list):
                    vals = np.asarray(shap_vals[1][0])  # clase 1
                elif shap_vals.ndim == 3:
                    vals = np.asarray(shap_vals[0, :, 1])
                elif shap_vals.ndim == 2:
                    vals = np.asarray(shap_vals[0])
                else:
                    vals = np.asarray(shap_vals)
                prob_pred = float(modelo.predict_proba(X_usuario)[0, 1])

            # --- Caso B: Bagging (solo si su base es arbol) -------------------
            elif nombre_clase == 'BaggingClassifier':
                base_est = getattr(modelo_final, 'estimator_',
                          getattr(modelo_final, 'base_estimator_', None))
                base_clase = type(base_est).__name__ if base_est else ''
                if base_clase in FAMILIAS_TREE or 'Tree' in base_clase:
                    explainer = shap.TreeExplainer(modelo_final)
                    shap_vals = explainer.shap_values(X_prep)
                    if isinstance(shap_vals, list):
                        vals = np.asarray(shap_vals[1][0])
                    elif shap_vals.ndim == 3:
                        vals = np.asarray(shap_vals[0, :, 1])
                    elif shap_vals.ndim == 2:
                        vals = np.asarray(shap_vals[0])
                    else:
                        vals = np.asarray(shap_vals)
                    prob_pred = float(modelo.predict_proba(X_usuario)[0, 1])
                else:
                    st.info(
                        f"ℹ️ Bagging con base no arbórea ({base_clase}) — "
                        f"SHAP exacto no aplicable. Usando método rápido."
                    )
                    return _contribuciones_proxy(perfil, df_ref)

            # --- Caso C: lineales --------------------------------------------
            elif nombre_clase in FAMILIAS_LINEAR:
                # Background sample del df_ref (max 100 filas para velocidad)
                X_bg_raw = df_ref[cols_features].head(100).fillna(0)
                X_bg     = pipeline.transform(X_bg_raw)
                explainer = shap.LinearExplainer(modelo_final, X_bg)
                shap_vals = explainer.shap_values(X_prep)
                if isinstance(shap_vals, list):
                    vals = np.asarray(shap_vals[1][0])
                elif shap_vals.ndim == 2:
                    vals = np.asarray(shap_vals[0])
                else:
                    vals = np.asarray(shap_vals)
                if hasattr(modelo, 'predict_proba'):
                    prob_pred = float(modelo.predict_proba(X_usuario)[0, 1])

            # --- Caso D: EBM (explainer nativo InterpretML) -------------------
            elif nombre_clase in FAMILIAS_EBM:
                # EBM tiene su propio metodo de explicacion local exacto
                explanation = modelo_final.explain_local(X_prep)
                data        = explanation.data(0)
                # 'names' = features, 'scores' = contribuciones en log-odds
                names_ebm  = list(data['names'])
                scores_ebm = np.asarray(data['scores'], dtype=float)
                # Filtrar la fila "Intercept" si existe (no es feature)
                mask = np.array([n != 'Intercept' for n in names_ebm])
                vals = scores_ebm[mask]
                feature_names_override = [n for n in names_ebm if n != 'Intercept']
                prob_pred = float(modelo.predict_proba(X_usuario)[0, 1])
                # EBM usa sus propios feature_names (no los del pipeline)
                return _construir_contribuciones_shap(
                    vals, feature_names_override, prob_pred
                )

            # --- Caso E: aviso explicito (ensembles + descartados) ------------
            elif nombre_clase in FAMILIAS_AVISO:
                st.info(
                    f"ℹ️ El modelo actual es **{nombre_clase}**. "
                    f"SHAP exacto requeriría análisis específico no implementado "
                    f"(decisión metodológica documentada). Usando método rápido."
                )
                return _contribuciones_proxy(perfil, df_ref)

            # --- Caso F: desconocido (generico) -------------------------------
            else:
                st.info(
                    f"ℹ️ SHAP no implementado para **{nombre_clase}**. "
                    f"Usando método rápido."
                )
                return _contribuciones_proxy(perfil, df_ref)

            # -- Capa 3: validacion de salida (NaN, inf, anomalos) -------------
            if vals is None or len(vals) == 0:
                st.warning("⚠️ SHAP devolvió valores vacíos. Usando método rápido.")
                return _contribuciones_proxy(perfil, df_ref)
            if np.isnan(vals).any() or np.isinf(vals).any():
                st.warning(
                    "⚠️ SHAP produjo valores anómalos (NaN/inf). "
                    "Usando método rápido como respaldo."
                )
                return _contribuciones_proxy(perfil, df_ref)

            # -- Construir resultado en formato compatible con _proxy ----------
            # Nombres de features tras el pipeline
            try:
                feature_names = list(pipeline.get_feature_names_out())
            except (AttributeError, ValueError):
                feature_names = [f"feat_{i}" for i in range(len(vals))]

            return _construir_contribuciones_shap(vals, feature_names, prob_pred)

        # -- Capa 4: try/except global (fallback de seguridad) -----------------
        except Exception as e:
            st.warning(
                f"⚠️ El método SHAP no pudo calcularse para "
                f"{type(modelo_final).__name__}. "
                f"Detalle técnico: {type(e).__name__}: {e}. "
                f"Usando método rápido como respaldo."
            )
            return _contribuciones_proxy(perfil, df_ref)


def _construir_contribuciones_shap(vals: np.ndarray,
                                     feature_names: list,
                                     prob_pred: float) -> list[dict]:
    """
    Construye la lista de contribuciones a partir de valores SHAP.

    Devuelve formato compatible con _contribuciones_proxy:
      {'variable': str, 'valor': str, 'contribucion': float}
    Donde 'contribucion' esta en escala 0-1 (NO 0-100), igual que _proxy.
    _renderizar_waterfall multiplica x100 al pintar.

    Conversion log-odds -> escala probabilidad:
      delta_prob ~= shap_log_odds * p * (1 - p)   (derivada local de sigmoid)
    Aproximacion local de primer orden - estandar en literatura SHAP.
    """
    # Factor de escala log-odds -> probabilidad (aproximacion local)
    escala = prob_pred * (1.0 - prob_pred)

    contribuciones = []
    for fname, shap_val in zip(feature_names, vals):
        # Limpiar prefijos del ColumnTransformer (ej: "robust__nota_acceso")
        fname_clean = fname.split('__')[-1] if '__' in fname else fname
        nombre = NOMBRES_VARIABLES.get(
            fname_clean,
            fname_clean.replace('_', ' ').title()
        )
        contribuciones.append({
            'variable':     nombre,
            'valor':        fname_clean,
            'contribucion': float(shap_val) * escala,  # escala 0-1 (NO x100)
        })

    # Filtrar ruido (<0.5pp) - mismo umbral que _contribuciones_proxy
    contribuciones = [c for c in contribuciones
                      if abs(c['contribucion']) >= 0.005]

    # Ordenar por magnitud, top 6 (consistente con _proxy)
    contribuciones.sort(key=lambda x: abs(x['contribucion']), reverse=True)
    return contribuciones[:6]


def _renderizar_waterfall(contribuciones: list[dict], prob: float,
                           df_ref: pd.DataFrame,
                           key_suffix: str = ""):
    """Renderiza un dot plot de impacto de factores (reemplaza al waterfall).

    Cada factor es un punto sobre una línea desde 0, con tamaño proporcional
    a la magnitud del impacto. Verde a la izquierda = reduce riesgo, rojo a
    la derecha = lo aumenta. Los valores NO son aditivos: son impactos
    marginales estimados por factor, no componentes que sumen al riesgo final.
    Por eso mostramos el riesgo final como KPI grande aparte, no como suma.

    key_suffix: string opcional para evitar keys duplicadas cuando se
    renderizan varios dot plots con la misma prob.
    """

    prob_base = df_ref['abandono'].mean() \
        if 'abandono' in df_ref.columns else _leer_metricas_modelo().get("tasa_abandono", 0.2925)

    # --- KPI grande con el riesgo final y comparativa con la media ---
    _, color_user, _, _ = _clasificar_riesgo(prob)
    diff_pp = (prob - prob_base) * 100
    sig     = "+" if diff_pp >= 0 else ""
    # Valores formateados con coma decimal española (solo los datos, no el CSS)
    _prob_txt      = f"{prob*100:.1f}%".replace('.', ',')
    _prob_base_txt = f"{prob_base*100:.1f}%".replace('.', ',')
    _diff_txt      = f"{sig}{diff_pp:.1f} pp".replace('.', ',')
    st.markdown(f"""
    <div style="background:{COLORES['fondo']}; border-radius:8px;
                padding:0.8rem 1rem; margin-bottom:0.8rem;
                text-align:center;">
        <div style="font-size:0.72rem; color:{COLORES['texto_suave']};
                    letter-spacing:0.5px;">TU RIESGO ESTIMADO</div>
        <div style="font-size:1.8rem; font-weight:500; color:{color_user};
                    margin:0.2rem 0; line-height:1;">
            {_prob_txt}
        </div>
        <div style="font-size:0.72rem; color:{COLORES['texto_suave']};">
            media del contexto: {_prob_base_txt} · {_diff_txt}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not contribuciones:
        st.info("No hay suficientes datos para mostrar los factores.")
        return

    # --- Preparar datos: ordenados por magnitud absoluta (los más
    # influyentes arriba), convertidos a puntos porcentuales. ---
    factores_raw = [
        {
            'nombre': c['variable'],
            'valor_pp': float(c['contribucion']) * 100,  # a puntos porcentuales
        }
        for c in contribuciones
    ]
    factores_raw.sort(key=lambda f: abs(f['valor_pp']), reverse=True)

    nombres = [f['nombre'] for f in factores_raw]
    valores = [f['valor_pp'] for f in factores_raw]
    colores = [COLORES['exito'] if v < 0 else COLORES['abandono']
               for v in valores]

    # Tamaños proporcionales a |valor|, con mínimo y máximo razonables
    max_abs = max((abs(v) for v in valores), default=1)
    tamanos = [max(12, 12 + (abs(v) / max_abs) * 22) for v in valores]

    # Textos con signo explícito y coma decimal española
    textos      = [f"{'+' if v >= 0 else ''}{v:.1f} pp".replace('.', ',')
                   for v in valores]
    posiciones  = ['middle left' if v < 0 else 'middle right' for v in valores]

    fig = go.Figure()

    # Línea conectora de cada factor desde el cero — misma y que el punto.
    # Ancho mayor para que no se vea pobre en columnas estrechas.
    for nom, v, col in zip(nombres, valores, colores):
        fig.add_trace(go.Scatter(
            x=[0, v], y=[nom, nom],
            mode='lines',
            line=dict(color=col, width=3),
            hoverinfo='skip', showlegend=False,
        ))

    # Puntos con tamaño variable y etiqueta a un lado.
    # textposition: siempre 'outside' del punto respecto al cero; así
    # la etiqueta nunca tapa la línea conectora.
    fig.add_trace(go.Scatter(
        x=valores, y=nombres,
        mode='markers+text',
        marker=dict(size=tamanos, color=colores,
                    line=dict(color='white', width=2)),
        text=textos,
        textposition=posiciones,
        textfont=dict(size=11, color=COLORES['texto']),
        hovertemplate='%{y}: %{x:,.1f} pp<extra></extra>',
        showlegend=False,
        cliponaxis=False,  # No recortar etiquetas cerca del borde del eje
    ))

    # Rango simétrico para que el eje 0 quede visualmente centrado.
    # Factor 1.5 + 8 pp para dejar aire a las etiquetas (±N,N pp).
    rango = max(abs(min(valores, default=-1)),
                abs(max(valores, default=1))) * 1.5 + 8

    fig.update_layout(
        separators=",.",
        xaxis=dict(
            title="Impacto (puntos porcentuales)",
            zeroline=True,
            zerolinecolor=COLORES['texto_suave'],
            zerolinewidth=2,
            ticksuffix=' pp',
            range=[-rango, rango],
            gridcolor=COLORES['borde'],
        ),
        yaxis=dict(
            autorange='reversed',
            gridcolor='rgba(0,0,0,0)',
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=max(260, 50 + 42 * len(factores_raw)),
        margin=dict(l=120, r=50, t=10, b=50),
        showlegend=False,
    )

    # Clave única incluyendo sufijo (p.ej. titulación)
    _key_base = f'factores_{prob:.4f}'
    _key      = f'{_key_base}_{key_suffix}' if key_suffix else _key_base
    st.plotly_chart(fig, width='stretch', key=_key)
    st.caption(
        "🟢 Verde = ese factor reduce tu riesgo.  🔴 Rojo = lo aumenta.  "
        "Los valores son impactos marginales por factor, no componentes que "
        "sumen al riesgo final."
    )


# =============================================================================
# GRÁFICO 4: Percentil
# =============================================================================

def _grafico_percentil(prob: float, df_ref: pd.DataFrame,
                        contexto: dict, modelo, pipeline):
    """
    Histograma del grupo de referencia con la posición del usuario marcada.
    El usuario puede cambiar el grupo con un selector de 3 opciones.
    """
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin-bottom:0.3rem;">
        📍 ¿Dónde estás respecto a otros alumnos?
    </h4>
    """, unsafe_allow_html=True)

    col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'

    # --- Caso especial: modo comparativa (2b) con varias titulaciones ---
    # No mostramos selector, solo usamos el df_contexto agregado que nos llega.
    if contexto['tipo'] == 'titulaciones_multiples':
        df_grupo     = contexto.get('df_contexto', df_ref.copy())
        nombre_grupo = contexto.get('valor', 'titulaciones elegidas')
        # Número real de titulaciones elegidas: lo pasa _seccion_donde_estas_multi
        # en contexto['n_titulaciones']. Fallback al unique del df si no está.
        n_tit_reales = contexto.get('n_titulaciones')
        if n_tit_reales is None:
            n_tit_reales = (len(df_grupo['titulacion'].unique())
                            if 'titulacion' in df_grupo.columns else '—')
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            st.markdown(
                f"<p style='font-size:0.78rem; color:{COLORES['texto_suave']}; "
                f"margin:0.5rem 0 0 0;'>Agregado sobre las <strong>{n_tit_reales}"
                f"</strong> titulaciones seleccionadas.</p>",
                unsafe_allow_html=True,
            )
        grupo_sel = nombre_grupo  # placeholder; la lógica siguiente se salta

    else:
        # Opciones de grupo de referencia — siempre las 3 si el contexto lo permite
        opciones_grupo = ["Toda la UJI"]
        if contexto['tipo'] in ('rama', 'titulacion') and col_rama in df_ref.columns:
            opciones_grupo.append("Solo mi rama")
        if contexto['tipo'] == 'titulacion' and 'titulacion' in df_ref.columns:
            opciones_grupo.append("Solo mi titulación")

        col_sel, col_info = st.columns([1, 2])

        with col_sel:
            grupo_sel = st.radio(
                label="Comparar con:",
                options=opciones_grupo,
                index=0,
                key=f"grupo_percentil_{contexto['tipo']}_{contexto['valor']}",
                help="Elige el grupo con el que quieres comparar tu posición.",
            )

        # DataFrame del grupo seleccionado
        if grupo_sel == "Toda la UJI":
            df_grupo     = df_ref.copy()
            nombre_grupo = "toda la UJI"
        elif "titulación" in grupo_sel and contexto['valor']:
            df_grupo     = df_ref[df_ref['titulacion'] == contexto['valor']]
            nombre_grupo = contexto['valor']
        else:
            # "Solo mi rama" — obtener la rama del contexto correctamente
            # Si el contexto es titulación, la rama está en df_contexto, no en valor
            if contexto['tipo'] == 'titulacion' and contexto.get('df_contexto') is not None:
                df_tit = contexto['df_contexto']
                val_rama = df_tit[col_rama].mode()[0] if col_rama in df_tit.columns and len(df_tit) > 0 else None
            else:
                val_rama = contexto['valor']
            df_grupo     = df_ref[df_ref[col_rama] == val_rama] \
                if val_rama else df_ref.copy()
            nombre_grupo = val_rama or "toda la UJI"

    # Probabilidades del grupo (usamos col precalculada si existe)
    if 'prob_abandono' in df_grupo.columns:
        probs_grupo = df_grupo['prob_abandono'].dropna().values
    else:
        try:
            cols_pipeline = list(pipeline.feature_names_in_)                 if hasattr(pipeline, 'feature_names_in_') else                 [c for c in df_grupo.columns if c not in _COLS_META]
            # Si a df_grupo le faltan columnas que el pipeline necesita,
            # no podemos calcular probs reales — usamos fallback: tasa
            # histórica de abandono del grupo como aproximación simple.
            cols_faltantes = [c for c in cols_pipeline if c not in df_grupo.columns]
            if cols_faltantes:
                # Fallback: aproximamos prob con la tasa histórica del grupo
                # (cada alumno con abandono=1 → prob≈1, abandono=0 → prob≈0)
                if 'abandono' in df_grupo.columns:
                    probs_grupo = df_grupo['abandono'].dropna().astype(float).values
                else:
                    probs_grupo = np.array([])
            else:
                cols_ok = [c for c in cols_pipeline if c in df_grupo.columns]
                # Convertir columnas categóricas string a código antes del pipeline
                df_grupo_cod = _codificar_df_categoricas(df_grupo[cols_ok])
                # Defensivo: rellenar NaN con 0 antes del transform
                df_grupo_cod = df_grupo_cod.fillna(0)
                X_prep  = pipeline.transform(df_grupo_cod)
                # Pasamos array numpy directamente al modelo para evitar
                # "feature names mismatch" (el modelo se entrenó con nombres
                # originales, no con los prefijos del preprocesador).
                if hasattr(X_prep, 'values'):
                    X_prep = X_prep.values
                elif not isinstance(X_prep, np.ndarray):
                    X_prep = np.asarray(X_prep)
                # Defensa NaN para el meta-learner LogisticRegression
                if np.isnan(X_prep).any():
                    X_prep = np.nan_to_num(X_prep, nan=0.0)
                probs_grupo   = modelo.predict_proba(X_prep)[:, 1]
        except Exception:
            # Red de seguridad: si el modelo falla aquí, leer la tasa actual
            # del JSON. Si también falla, fallback con valor real LightGBM.
            probs_grupo = np.array([
                _leer_metricas_modelo().get("tasa_abandono", 0.2925)
            ])

    # Percentil del usuario
    percentil = float((probs_grupo < prob).mean() * 100)

    # Banner compacto (1 sola línea) con los datos clave
    with col_info:
        _, color, _, _ = _clasificar_riesgo(prob)
        # Variable intermedia para coma decimal
        _prob_pct_txt = f"{prob*100:.1f}".replace('.', ',')
        st.markdown(f"""
        <div style="
            background:{color}12;
            border-left:3px solid {color};
            border-radius:4px;
            padding:0.5rem 0.9rem;
            font-size:0.82rem;
            line-height:1.4;
        ">
            Tu riesgo es <strong style="color:{color};">{_prob_pct_txt}%</strong>.
            Estás mejor que el <strong>{100-percentil:.0f}%</strong> de
            alumnos de <em>{nombre_grupo}</em>.
        </div>
        """, unsafe_allow_html=True)

    # --- Umbral mínimo: no tiene sentido un histograma con <10 alumnos ---
    MIN_ALUMNOS = 10
    if len(probs_grupo) < MIN_ALUMNOS:
        st.info(
            f"ℹ️ El grupo **{nombre_grupo}** tiene solo {len(probs_grupo)} alumno(s) "
            f"en el conjunto de test — insuficiente para mostrar una distribución. "
            f"Prueba con 'Toda la UJI' o 'Solo mi rama' para una comparativa más representativa."
        )
        return

    # === FILA: 3 MINI-KPIs arriba del violín ============================
    media_grupo = float(probs_grupo.mean() * 100)
    mediana_grupo = float(np.median(probs_grupo) * 100)
    diff_pp = prob * 100 - media_grupo

    _, color_user, _, _ = _clasificar_riesgo(prob)
    # Variables intermedias para coma decimal en los 3 KPIs
    _media_grp_txt   = f"{media_grupo:.1f}".replace('.', ',')
    _mediana_grp_txt = f"{mediana_grupo:.1f}".replace('.', ',')
    _diff_grp_txt    = f"{diff_pp:.1f}".replace('.', ',')

    # Auditoría p03 (Chat p03, 27/04/2026): 3 KPIs migradas a _tarjeta_kpi
    # de ui_helpers.py para coherencia visual con resto de p03 y con p02.
    # Antes: cards inline border-top:2px (estilo distinto). Ahora: barra
    # lateral 4px estándar de la app. Iconos:
    #   📏 PERCENTIL EN GRUPO → barra del color del nivel del usuario
    #   📊 MEDIA DEL GRUPO    → primario (azul)
    #   ⚖️  TÚ VS MEDIA       → rojo si peor, verde si mejor
    sig = "+" if diff_pp >= 0 else ""
    col_diff = COLORES['abandono'] if diff_pp > 0 else COLORES['exito']

    nombre_grupo_corto = nombre_grupo[:22] + "…" if len(nombre_grupo) > 22 else nombre_grupo

    html_p1 = _tarjeta_kpi(
        icono="📏",
        etiqueta="Percentil en grupo",
        valor=f"{percentil:.0f}",
        delta=f"de 100 · {nombre_grupo_corto}",
        delta_color="gray",
        tooltip=("Posición del usuario dentro de la distribución de probabilidad "
                 "del grupo de referencia. 0 = mejor que nadie, 100 = peor que nadie."),
        color_barra=color_user,
    )
    html_p2 = _tarjeta_kpi(
        icono="📊",
        etiqueta="Media del grupo",
        valor=f"{_media_grp_txt}%",
        delta=f"mediana: {_mediana_grp_txt}%",
        delta_color="gray",
        tooltip="Probabilidad media de abandono del grupo de referencia "
                "según el modelo.",
        color_barra=COLORES["primario"],
    )
    html_p3 = _tarjeta_kpi(
        icono="⚖️",
        etiqueta="Tú vs media",
        valor=f"{sig}{_diff_grp_txt} pp",
        delta=("peor que la media" if diff_pp > 0 else "mejor que la media"),
        delta_color=("red" if diff_pp > 0 else "green"),
        tooltip="Diferencia entre tu riesgo personal y la media del grupo, "
                "en puntos porcentuales (pp). Positivo = peor que la media.",
        color_barra=col_diff,
    )

    kpi_cols = st.columns(3)
    kpi_cols[0].markdown(html_p1, unsafe_allow_html=True)
    kpi_cols[1].markdown(html_p2, unsafe_allow_html=True)
    kpi_cols[2].markdown(html_p3, unsafe_allow_html=True)

    # === 2 GRÁFICOS LADO A LADO =======================================
    col_dot, col_spark = st.columns([1, 1])

    # --------- GRÁFICO 1: DOT PLOT (1 punto = 1 alumno) ----------------
    with col_dot:
        st.markdown(f"""
        <p style="font-size:0.78rem; color:{COLORES['texto_suave']};
                  margin:0 0 0.2rem 0;">
            🎯 Cada punto = 1 alumno · color por nivel de riesgo
        </p>
        """, unsafe_allow_html=True)

        # Reducimos a máx 500 puntos si hay muchos (muestreo determinista)
        MAX_PUNTOS = 500
        if len(probs_grupo) > MAX_PUNTOS:
            np.random.seed(42)
            idx = np.random.choice(len(probs_grupo), MAX_PUNTOS, replace=False)
            probs_plot = probs_grupo[idx]
        else:
            probs_plot = probs_grupo.copy()

        # Distribuir puntos en grid: x = prob, y = jitter vertical
        n = len(probs_plot)
        y_jitter = np.random.uniform(0, 1, size=n)

        # Color por umbral de riesgo
        colors = []
        for p in probs_plot:
            if p < UMBRALES['riesgo_bajo']:
                colors.append(COLORES_RIESGO['bajo'])
            elif p < UMBRALES['riesgo_medio']:
                colors.append(COLORES_RIESGO['medio'])
            else:
                colors.append(COLORES_RIESGO['alto'])

        fig_dot = go.Figure()
        fig_dot.add_trace(go.Scatter(
            x=probs_plot * 100,
            y=y_jitter,
            mode='markers',
            marker=dict(size=6, color=colors, opacity=0.55,
                         line=dict(width=0)),
            hovertemplate='%{x:,.1f}%<extra></extra>',
            showlegend=False,
        ))

        # Tu punto: anillo negro grande destacado
        fig_dot.add_trace(go.Scatter(
            x=[prob * 100], y=[0.5],
            mode='markers',
            marker=dict(
                size=20, color=color,
                line=dict(color=COLORES['texto'], width=2.5),
                symbol='circle',
            ),
            hovertemplate=f'Tu riesgo: {prob*100:.1f}%<extra></extra>',
            showlegend=False,
        ))

        fig_dot.update_layout(
            separators=",.",
            xaxis=dict(title='Probabilidad de abandono (%)',
                        range=[0, 100], ticksuffix='%',
                        showgrid=True, gridcolor=COLORES['borde']),
            yaxis=dict(showgrid=False, showticklabels=False,
                        range=[-0.1, 1.1]),
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=20, r=10, t=10, b=40),
            height=230,
            showlegend=False,
        )
        st.plotly_chart(fig_dot, width='stretch',
                         key=f'dotplot_{nombre_grupo[:15]}_{prob:.4f}_{contexto.get("tipo","x")}')

    # --------- GRÁFICO 2: SPARKLINES ESTILO ECONOMIST ------------------
    with col_spark:
        st.markdown(f"""
        <p style="font-size:0.78rem; color:{COLORES['texto_suave']};
                  margin:0 0 0.2rem 0;">
            📈 Distribución por niveles de riesgo
        </p>
        """, unsafe_allow_html=True)

        # Contamos alumnos por nivel de riesgo
        n_bajo  = int((probs_grupo < UMBRALES['riesgo_bajo']).sum())
        n_medio = int(((probs_grupo >= UMBRALES['riesgo_bajo'])
                        & (probs_grupo < UMBRALES['riesgo_medio'])).sum())
        n_alto  = int((probs_grupo >= UMBRALES['riesgo_medio']).sum())
        total = max(1, n_bajo + n_medio + n_alto)

        # Determinar en qué nivel estás
        if prob < UMBRALES['riesgo_bajo']:
            nivel_usr = 'Bajo'
        elif prob < UMBRALES['riesgo_medio']:
            nivel_usr = 'Medio'
        else:
            nivel_usr = 'Alto'

        niveles = [
            ('Bajo',  n_bajo,  COLORES_RIESGO['bajo']),
            ('Medio', n_medio, COLORES_RIESGO['medio']),
            ('Alto',  n_alto,  COLORES_RIESGO['alto']),
        ]

        fig_spark = go.Figure()
        for nom, cnt, col in niveles:
            pct = cnt / total * 100
            # Barra con opacidad alta en "tu nivel"
            opacity = 0.95 if nom == nivel_usr else 0.45
            fig_spark.add_trace(go.Bar(
                x=[cnt], y=[nom], orientation='h',
                marker=dict(color=col, opacity=opacity),
                text=[f'{pct:.1f}% · {cnt:,} alumnos'.replace(',', '.')],
                textposition='outside',
                textfont=dict(size=11,
                               color=col if nom == nivel_usr else COLORES['texto_suave']),
                hoverinfo='skip',
                showlegend=False,
            ))

        # Añadir emoji "tú" en tu nivel
        fig_spark.add_annotation(
            x=0, y=nivel_usr,
            text=" ← TÚ",
            showarrow=False,
            xanchor='left',
            xref='paper',
            font=dict(size=11, color=color, family='Arial Black'),
        )

        fig_spark.update_layout(
            separators=",.",
            xaxis=dict(showgrid=True, gridcolor=COLORES['borde'],
                        showticklabels=False, zeroline=False,
                        range=[0, max(n_bajo, n_medio, n_alto) * 1.35]),
            yaxis=dict(showgrid=False,
                        tickfont=dict(size=12),
                        categoryorder='array',
                        categoryarray=['Alto', 'Medio', 'Bajo']),
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=55, r=20, t=10, b=40),
            height=230,
            showlegend=False,
            bargap=0.35,
        )
        st.plotly_chart(fig_spark, width='stretch',
                         key=f'spark_{nombre_grupo[:15]}_{prob:.4f}_{contexto.get("tipo","x")}')

    st.caption(
        f"📊 {len(probs_grupo):,} alumnos · {nombre_grupo}".replace(",", ".")
    )



# =============================================================================
# SECCIÓN PERCENTIL AGREGADO (modo 2b - sobre titulaciones elegidas)
# =============================================================================

def _seccion_donde_estas_multi(prob: float, titulaciones: list,
                                 df_ref: "pd.DataFrame", modelo, pipeline):
    """Variante de la sección '¿Dónde estás respecto a otros alumnos?'
    agregada sobre las titulaciones elegidas en modo comparativa.
    Reutiliza _grafico_percentil con un contexto sintético que une los
    registros de todas las titulaciones seleccionadas."""
    if "titulacion" not in df_ref.columns or not titulaciones:
        return

    df_multi = df_ref[df_ref['titulacion'].isin(titulaciones)].copy()
    if len(df_multi) == 0:
        st.info("Sin datos suficientes para el agregado de titulaciones elegidas.")
        return

    # Etiqueta legible del agregado — usamos el número real de titulaciones
    # pedidas (el df_multi puede tener menos si alguna no tiene test disponible)
    etiqueta = f"titulaciones elegidas ({len(titulaciones)})"
    contexto_multi = {
        "tipo":            "titulaciones_multiples",
        "valor":           etiqueta,
        "df_contexto":     df_multi,
        "n_titulaciones":  len(titulaciones),
    }
    _grafico_percentil(prob, df_ref, contexto_multi, modelo, pipeline)


# =============================================================================
# COMPARATIVA DE TITULACIONES
# =============================================================================

def _mostrar_comparativa(perfil: dict, titulaciones: list,
                          df_ref: "pd.DataFrame", modelo, pipeline,
                          df_features: "pd.DataFrame | None" = None):
    """
    Comparativa entre titulaciones seleccionadas.

    DISEÑO:
      Dato central  → tasa histórica de abandono por titulación (varía realmente)
      Dato secundario → tu riesgo personal (calculado UNA sola vez con tu perfil)

    POR QUÉ:
      El modelo no tiene 'titulacion' como feature — solo 'rama'.
      Tu riesgo personal es el mismo para titulaciones de la misma rama.
      La tasa histórica sí varía entre titulaciones y es muy útil para
      un prospecto que quiere saber qué carrera tiene más abandonos reales.
    """
    if len(titulaciones) < 2:
        st.warning("Selecciona al menos 2 titulaciones para ver la comparativa.")
        return

    st.markdown(f"""
    <h3 style="color:{COLORES['primario']}; margin-bottom:0.3rem;">
        Comparativa de titulaciones
    </h3>
    <p style="font-size:0.88rem; color:{COLORES['texto_suave']}; margin-top:0;">
        Abandono histórico real de cada titulación + tu riesgo personal estimado.
    </p>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 1. Recopilar datos históricos + calcular prob por titulación
    #    Cada titulación usa su propio df filtrado → pronósticos distintos.
    # ------------------------------------------------------------------
    col_rama = 'rama_meta' if 'rama_meta' in df_ref.columns else 'rama'
    _PALETA_COMP = ["#3182ce", "#805ad5", "#319795", "#d69e2e", "#e53e3e"]

    datos = []
    for i, tit in enumerate(titulaciones):
        df_tit = _filtrar_por_titulacion(df_ref, tit) \
            if "titulacion" in df_ref.columns else df_ref.copy()
        # Fallback: si la titulación no tiene datos, usamos df_ref global
        if len(df_tit) == 0:
            df_tit = df_ref.copy()

        tasa_hist = float(df_tit["abandono"].mean() * 100) \
            if "abandono" in df_tit.columns and len(df_tit) > 0 else 0.0
        n_alumnos = len(df_tit)
        rama = df_tit[col_rama].mode()[0] \
            if col_rama in df_tit.columns and len(df_tit) > 0 else "–"

        # Calcular prob con las medias de ESTA titulación
        prob_tit, err_tit = _calcular_probabilidad(perfil, modelo, pipeline, df_tit)
        if err_tit or prob_tit is None:
            prob_tit = 0.0

        # Corrección heurística: ajusta por tasa histórica tit vs rama
        ctx_tit_tmp = {"tipo": "titulacion", "valor": tit}
        prob_tit, _, _, _ = _ajustar_prob_por_titulacion(prob_tit, ctx_tit_tmp, df_ref)
        nivel_tit, color_tit, _, _ = _clasificar_riesgo(prob_tit)

        # Nombre corto (sin prefijo "Grado en ...") — versión plana
        nc = tit
        for pref in ["Grado en ", "Doble Grado en ", "Grado Universitario en "]:
            if nc.startswith(pref):
                nc = nc[len(pref):]
                break

        datos.append({
            "titulacion":   tit,
            "nombre":       nc,
            # nombre_40: versión sencilla truncada con "…" para contextos que
            # NO admiten <br> (ej. títulos de expanders, captions).
            # Ampliado a 50 chars para que entre "Ingeniería en Diseño
            # Industrial y Desarrollo de Productos" casi completo.
            "nombre_40":    nc[:50] + "…" if len(nc) > 50 else nc,
            # nombre_corto: versión en 2 líneas con <br> (usa el helper
            # _nombre_titulacion_corto). Para gráficos Plotly y HTML markdown.
            "nombre_corto": _nombre_titulacion_corto(tit, partir_lineas=True, max_chars=24),
            "tasa_hist":    tasa_hist,
            "n_alumnos":    n_alumnos,
            "rama":         rama,
            "color":        _PALETA_COMP[i % len(_PALETA_COMP)],
            "prob":         prob_tit,
            "nivel":        nivel_tit,
            "color_riesgo": color_tit,
        })

    # Ordenar por tasa histórica de mayor a menor
    datos.sort(key=lambda x: x["tasa_hist"], reverse=True)

    # ------------------------------------------------------------------
    # Auditoría p03 (Chat p03, 27/04/2026): bloque de 5 KPIs agregados
    # ANTES de la tabla. Réplica EXACTA del patrón de p02 modo comparativa
    # (líneas 1331+ de p02_titulacion.py) con _tarjeta_kpi de ui_helpers.
    #
    # 5 indicadores con MISMO ORDEN E ICONOS que p02 para coherencia UX:
    #   1. 👥 Alumnos totales (suma) — primario azul
    #   2. 📉 Abandono real medio (ponderado por N) — abandono rojo
    #   3. 🔮 Riesgo predicho medio (medio del perfil del usuario) — primario azul
    #   4. 🚨 Riesgo alto (% de titulaciones con riesgo del usuario alto) — advertencia ámbar
    #   5. 🎯 F1 modelo (mismo dato que en detalle, modelo único) — exito verde
    # ------------------------------------------------------------------
    n_alumnos_total      = sum(d["n_alumnos"] for d in datos)
    # Abandono real medio ponderado por N de cada titulación
    if n_alumnos_total > 0:
        abandono_real_medio = sum(d["tasa_hist"] * d["n_alumnos"] for d in datos) / n_alumnos_total
    else:
        abandono_real_medio = 0.0
    # Riesgo predicho medio = media del riesgo del usuario en cada titulación
    riesgo_pred_medio = (sum(d["prob"] for d in datos) / len(datos) * 100) if datos else 0.0
    # Riesgo alto: cuántas titulaciones devuelven riesgo "Alto" para el usuario
    n_riesgo_alto_titulaciones = sum(1 for d in datos if d["nivel"] == "Alto")
    pct_alto = (n_riesgo_alto_titulaciones / len(datos) * 100) if datos else 0.0

    # F1 global del modelo + nombre del modelo — leídos desde metricas_modelo.json
    # (patrón de p02). FIX 29/04/2026: _nombre_modelo_comp se asigna también en
    # el except para evitar UnboundLocalError si _RUTAS no tiene la clave o el
    # JSON no se puede leer (caso reproducible en p03 → comparativa múltiple).
    try:
        import json as _json_comp
        _ruta_m_comp = _RUTAS.get("metricas_modelo")
        _m_comp      = (_json_comp.loads(_ruta_m_comp.read_text(encoding="utf-8"))
                        if _ruta_m_comp and _ruta_m_comp.exists() else {})
        _f1_comp     = _m_comp.get("f1")
        f1_val_comp  = f"{_f1_comp:.3f}".replace(".", ",") if _f1_comp is not None else "N/D"
        _nombre_modelo_comp = _m_comp.get("modelo_nombre", "actual")
    except Exception:
        f1_val_comp         = "0,827"  # fallback documentado
        _nombre_modelo_comp = "actual"  # fallback gramaticalmente correcto

    # KPI 1: alumnos totales (info neutra → azul)
    html_c1 = _tarjeta_kpi(
        icono="👥",
        etiqueta="Alumnos totales",
        valor=f"{n_alumnos_total:,}".replace(",", "."),
        tooltip="Suma de alumnos de las titulaciones seleccionadas en el conjunto de test.",
        color_barra=COLORES["primario"],
    )

    # KPI 2: abandono real medio (métrica crítica → rojo)
    _abandono_txt = f"{abandono_real_medio:.1f}%".replace(".", ",")
    html_c2 = _tarjeta_kpi(
        icono="📉",
        etiqueta="Abandono real medio",
        valor=_abandono_txt,
        tooltip="Tasa media de abandono real, ponderada por número de alumnos de cada titulación.",
        color_barra=COLORES["abandono"],
    )

    # KPI 3: riesgo predicho medio del usuario (con delta vs real)
    _delta_c3   = riesgo_pred_medio - abandono_real_medio
    _delta_str  = f"{_delta_c3:+.1f}pp vs real".replace(".", ",")
    _color_d_c3 = "red" if _delta_c3 > 0 else ("green" if _delta_c3 < 0 else "gray")
    _riesgo_txt = f"{riesgo_pred_medio:.1f}%".replace(".", ",")
    html_c3 = _tarjeta_kpi(
        icono="🔮",
        etiqueta="Riesgo predicho medio",
        valor=_riesgo_txt,
        delta=_delta_str,
        delta_color=_color_d_c3,
        tooltip=("Probabilidad media de abandono según el modelo, calculada con tu "
                 "perfil sobre cada titulación seleccionada. El delta (pp = puntos "
                 "porcentuales) compara con la tasa real."),
        color_barra=COLORES["primario"],
    )

    # KPI 4: riesgo alto (alerta → ámbar, NO rojo, paridad p01/p02)
    _pct_alto_txt = f"{pct_alto:.1f}%".replace(".", ",")
    _delta_c4     = (f"{n_riesgo_alto_titulaciones} de {len(datos)} titulaciones"
                     if datos else "")
    html_c4 = _tarjeta_kpi(
        icono="🚨",
        etiqueta="Riesgo alto",
        valor=_pct_alto_txt,
        delta=_delta_c4,
        delta_color="gray",
        tooltip=(f"Porcentaje de titulaciones seleccionadas en las que tu riesgo "
                 f"estimado supera el umbral de riesgo medio "
                 f"({UMBRALES['riesgo_medio']:.0%})."),
        color_barra=COLORES["advertencia"],
    )

    # KPI 5: F1 modelo (calidad del modelo → verde)
    # Tooltip dinámico — _nombre_modelo_comp ya está definido arriba en el
    # try/except (con fallback "actual" si falla la lectura del JSON).
    html_c5 = _tarjeta_kpi(
        icono="🎯",
        etiqueta="F1 modelo",
        valor=f1_val_comp,
        tooltip=f"F1-score del modelo {_nombre_modelo_comp} sobre el conjunto de test completo.",
        color_barra=COLORES["exito"],
    )

    # Renderizar las 5 tarjetas en una fila
    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    cc1.markdown(html_c1, unsafe_allow_html=True)
    cc2.markdown(html_c2, unsafe_allow_html=True)
    cc3.markdown(html_c3, unsafe_allow_html=True)
    cc4.markdown(html_c4, unsafe_allow_html=True)
    cc5.markdown(html_c5, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.divider()

    # ------------------------------------------------------------------
    # 4. Tabla resumen — dato central: abandono histórico
    # ------------------------------------------------------------------
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin:0.5rem 0 0.4rem 0;">
        📋 Abandono histórico por titulación
    </h4>
    <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0 0 0.6rem 0;">
        Porcentaje real de estudiantes que abandonaron cada titulación
        en el período 2010–2020. Dato independiente de tu perfil.
    </p>
    """, unsafe_allow_html=True)

    # Cabecera
    cols_h = st.columns([3, 1.5, 1.2, 1.8, 1.2])
    for col, h in zip(cols_h, ["Titulación", "Abandono histórico", "Alumnos", "Rama", "Tu riesgo"]):
        col.markdown(
            f"<p style='font-size:0.77rem; font-weight:600; "
            f"color:{COLORES['texto_suave']}; margin:0;'>{h}</p>",
            unsafe_allow_html=True,
        )
    st.markdown(f"<hr style='margin:0.2rem 0; border-color:{COLORES['borde']}'>",
                unsafe_allow_html=True)

    for d in datos:
        # Color de la barra de tasa histórica según nivel
        if d["tasa_hist"] >= 40:
            col_hist = COLORES["abandono"]
        elif d["tasa_hist"] >= 25:
            col_hist = COLORES["advertencia"]
        else:
            col_hist = COLORES["exito"]

        # Formatos en coma española (variables intermedias para evitar
        # f-strings anidadas con comillas, que Python no admite).
        _tasa_hist_txt = f"{d['tasa_hist']:.1f}".replace('.', ',')
        _prob_txt      = f"{d['prob']*100:.1f}".replace('.', ',')

        cs = st.columns([3, 1.5, 1.2, 1.8, 1.2])
        cs[0].markdown(
            f"<p style='font-size:0.83rem; color:{COLORES['texto']}; "
            f"margin:0.15rem 0; line-height:1.3;'>"
            f"<span style='color:{d['color']};'>■</span> {d['nombre_corto']}</p>",
            unsafe_allow_html=True,
        )
        cs[1].markdown(
            f"<p style='font-size:0.92rem; font-weight:bold; "
            f"color:{col_hist}; margin:0.15rem 0;'>{_tasa_hist_txt}%</p>",
            unsafe_allow_html=True,
        )
        cs[2].markdown(
            f"<p style='font-size:0.83rem; color:{COLORES['texto_suave']}; "
            f"margin:0.15rem 0;'>{d['n_alumnos']:,}</p>",
            unsafe_allow_html=True,
        )
        cs[3].markdown(
            f"<p style='font-size:0.83rem; color:{COLORES['texto_suave']}; "
            f"margin:0.15rem 0;'>{d['rama']}</p>",
            unsafe_allow_html=True,
        )
        cs[4].markdown(
            f"<p style='font-size:0.83rem; font-weight:bold; "
            f"color:{d['color_riesgo']}; margin:0.15rem 0;'>{_prob_txt}%</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<hr style='margin:0.1rem 0; border-color:{COLORES['borde']}'>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # 5. Comparativa visual (barras) + Histograma agregado (notas)
    #    lado a lado en columnas.
    # ------------------------------------------------------------------
    col_cv, col_hist = st.columns([1.4, 1])

    with col_cv:
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin:1.5rem 0 0.4rem 0;">
            📊 Comparativa visual
        </h4>""", unsafe_allow_html=True)

        fig = go.Figure()
        for d in datos:
            fig.add_trace(go.Bar(
                x=[d["tasa_hist"]],
                y=[d["nombre_corto"]],
                orientation="h",
                marker_color=d["color"],
                text=f"{d['tasa_hist']:.1f}%",
                textposition="outside",
                name=d["nombre_corto"],
                hovertemplate=(
                    f"<b>{d['nombre']}</b><br>"
                    f"Abandono histórico: {d['tasa_hist']:.1f}%<br>"
                    f"Alumnos: {d['n_alumnos']:,}<br>"
                    f"Tu riesgo personal: {d['prob']*100:.1f}%"
                    "<extra></extra>"
                ),
                showlegend=False,
            ))

        # Línea vertical: media UJI histórica
        media_uji_hist = float(df_ref["abandono"].mean() * 100)         if "abandono" in df_ref.columns else 29.2
        # Auditoría p03 (Chat p03, 27/04/2026): añadido replace para coma decimal.
        _media_uji_txt = f"{media_uji_hist:.1f}".replace(".", ",")
        fig.add_vline(
            x=media_uji_hist,
            line_color=COLORES["texto_suave"], line_dash="dash", line_width=1.5,
            annotation_text=f"Media UJI ({_media_uji_txt}%)",
            annotation_font_size=10,
            annotation_font_color=COLORES["texto_suave"],
        )
        # (línea de riesgo personal eliminada: cada titulación tiene su prob)
        # En su lugar: marcadores de riesgo como scatter sobre las barras
        fig.add_trace(go.Scatter(
            x=[d["prob"] * 100 for d in datos],
            y=[d["nombre_corto"] for d in datos],
            mode="markers+text",
            marker=dict(
                symbol="diamond",
                size=12,
                color=[d["color_riesgo"] for d in datos],
                line=dict(color="white", width=1.5),
            ),
            text=[f'{d["prob"]*100:.1f}%'.replace('.', ',') for d in datos],
            # Texto arriba del diamante para evitar cortes por margen derecho
            textposition="top center",
            textfont=dict(size=10),
            name="Tu riesgo estimado",
            hovertemplate=(
                "<b>Tu riesgo en %{y}</b><br>"
                "Probabilidad estimada: %{x:,.1f}%"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

        # --- Rango dinámico del eje X: ajustado al máximo real + margen ---
        # Incluye tasas históricas, probs personales y media UJI. Redondeo
        # al múltiplo de 10 superior para escalar limpio (32 → 40, 44 → 50).
        # Si hay probs altas (≥80) escalamos hasta 100 para dar aire al diamante.
        _vals_eje = [d["tasa_hist"] for d in datos] \
                    + [d["prob"] * 100 for d in datos] \
                    + [media_uji_hist]
        _max_real = max(_vals_eje) if _vals_eje else 30
        _max_eje = int(np.ceil((_max_real + 10) / 10.0) * 10)
        _max_eje = min(_max_eje, 100)  # cap absoluto

        fig.update_layout(
            separators=",.",
            xaxis=dict(range=[0, _max_eje], ticksuffix="%",
                       title="Tasa de abandono histórica (%)"),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=30, t=20, b=40),
            height=max(220, len(datos) * 65),
            bargap=0.3,
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor=COLORES["borde"])
        st.plotly_chart(fig, width='stretch', key='comparativa_visual')
        st.caption(
            "📊 Barras = tasa de abandono histórica real (2010–2020). "
            "╌╌╌ Línea gris discontinua = media UJI. "
            "◆ Diamante de color = tu riesgo estimado para este perfil (por titulación)."
        )

    # ------------------------------------------------------------------
    # 5.bis — Histograma agregado de notas (col_hist)
    # Histograma agregado: todas las notas de las titulaciones elegidas
    # + línea vertical por titulación (color de la paleta de comparativa)
    # + línea verde/rojo con la nota del usuario (si disponible).
    # ------------------------------------------------------------------
    with col_hist:
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin:1.5rem 0 0.4rem 0;">
            📊 Distribución de notas de acceso
        </h4>
        <p style="font-size:0.78rem; color:{COLORES['texto_suave']}; margin:0 0 0.3rem 0;">
            Histograma agregado de las titulaciones seleccionadas. Cada línea
            vertical marca la media de una titulación.
        </p>
        """, unsafe_allow_html=True)

        # Recopilamos notas de todas las titulaciones elegidas
        notas_all = []
        medias_por_tit = []  # [(nombre_40, media, color), ...]
        for d in datos:
            df_tit_h = _filtrar_por_titulacion(df_ref, d["titulacion"]) \
                if "titulacion" in df_ref.columns else df_ref.copy()
            if "nota_acceso" in df_tit_h.columns:
                notas_tit = df_tit_h["nota_acceso"].dropna()
                if len(notas_tit) > 0:
                    notas_all.extend(notas_tit.tolist())
                    medias_por_tit.append((
                        d["nombre_40"], float(notas_tit.mean()), d["color"],
                    ))

        if len(notas_all) < 3:
            st.info("Sin notas de acceso suficientes en las titulaciones elegidas.")
        else:
            import plotly.graph_objects as _go
            fig_h = _go.Figure()
            fig_h.add_trace(_go.Histogram(
                x=notas_all,
                nbinsx=25,
                marker=dict(color=COLORES['primario'], opacity=0.35),
                hovertemplate='Nota %{x:,.1f}<br>%{y} alumnos<extra></extra>',
                showlegend=False,
            ))

            # Líneas verticales: una por titulación con su color.
            # Escalonado adaptativo de las etiquetas para evitar solape
            # cuando las medias están próximas (caso típico: 4-5 titulaciones
            # de notas similares agrupadas entre 6,5 y 8,5):
            #   1) ordenamos por media para detectar vecinas próximas
            #   2) cada etiqueta se pone por encima del gráfico, con un
            #      yshift escalonado en 4 niveles (0, -16, -32, -48 px)
            #   3) si dos medias están separadas >0,6 reseteamos el nivel
            #   4) con ≥4 titulaciones reducimos fuente y truncamos nombre
            # Separamos vline (sin texto) y annotation (con yshift) porque
            # add_vline no acepta yshift en su annotation embebida.
            n_tits = len(medias_por_tit)
            font_sz = 8 if n_tits >= 4 else 9
            trunc   = 14 if n_tits >= 4 else 16

            # Ordenamos por media para escalonado coherente
            medias_ord = sorted(enumerate(medias_por_tit), key=lambda t: t[1][1])

            y_shift_px = [0, -16, -32, -48]   # 4 niveles escalonados
            nivel = 0
            media_prev = None
            for _, (nombre_tit, media_tit, col_tit) in medias_ord:
                # Si esta media está lejos de la anterior (>0,6 puntos),
                # reiniciamos el escalón; si está cerca, subimos un nivel.
                if media_prev is None or abs(media_tit - media_prev) > 0.6:
                    nivel = 0
                else:
                    nivel = (nivel + 1) % len(y_shift_px)

                # Línea vertical sin texto
                fig_h.add_vline(
                    x=media_tit,
                    line=dict(color=col_tit, width=2, dash='dot'),
                )
                # Anotación independiente con yshift (en píxeles, yref paper)
                etiqueta = f"{nombre_tit[:trunc]}: {media_tit:.1f}".replace(".", ",")
                fig_h.add_annotation(
                    x=media_tit, y=1.0, xref='x', yref='paper',
                    text=etiqueta, showarrow=False,
                    font=dict(size=font_sz, color=col_tit),
                    bgcolor="rgba(255,255,255,0.9)",
                    yshift=y_shift_px[nivel],
                    yanchor='bottom',
                )
                media_prev = media_tit

            # Línea vertical: nota del usuario
            nota_user = None
            if perfil.get('nota_acceso') is not None:
                try:
                    nota_user = float(perfil['nota_acceso'])
                except Exception:
                    nota_user = None
            if nota_user is not None:
                media_global = float(np.mean(notas_all))
                # Auditoría p03 (Chat p03): hex → COLORES.
                col_user = (COLORES['exito']
                            if nota_user >= media_global
                            else COLORES['abandono'])
                fig_h.add_vline(
                    x=nota_user,
                    line=dict(color=col_user, width=3),
                    annotation_text=f"Tu nota: {nota_user:.1f}".replace(".", ","),
                    annotation_position="bottom",
                    annotation_font=dict(size=10, color=col_user),
                    annotation_bgcolor="rgba(255,255,255,0.9)",
                )

            x_min = max(0, float(min(notas_all)) - 0.5)
            x_max = min(14, float(max(notas_all)) + 0.5)
            # Margen superior generoso para que las etiquetas escalonadas
            # (hasta 4 niveles, ~50 px) no se corten por encima.
            fig_h.update_layout(
                separators=",.",
                xaxis_title=None,
                yaxis_title="Nº alumnos",
                paper_bgcolor='white',
                plot_bgcolor='white',
                height=max(260, len(datos) * 70),
                margin=dict(l=40, r=20, t=80, b=40),
                showlegend=False,
                xaxis=dict(range=[x_min, x_max],
                           showgrid=True, gridcolor=COLORES['borde']),
                yaxis=dict(showgrid=True, gridcolor=COLORES['borde']),
                bargap=0.1,
            )
            st.plotly_chart(fig_h, width='stretch',
                             key='hist_notas_multi')

    # ------------------------------------------------------------------
    # 5b. Velocímetro unificado con aguja por titulación
    # ------------------------------------------------------------------
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin:1.2rem 0 0.3rem 0;">
        🎯 Tu riesgo en cada titulación (velocímetro)
    </h4>
    <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0 0 0.4rem 0;">
        Una aguja por titulación, con su color distintivo. Zona verde-amarilla-roja
        según umbrales de riesgo del modelo.
    </p>
    """, unsafe_allow_html=True)
    resultados_vel = [
        {"titulacion": d["titulacion"], "pct": d["prob"]*100, "color_comp": d["color"]}
        for d in datos
    ]
    _grafico_velocimetro_comparativa(resultados_vel)

    # ------------------------------------------------------------------
    # 5c. Scatter (hist vs tu riesgo) + Box plot con rug plot
    #     lado a lado en columnas.
    # ------------------------------------------------------------------
    col_sc, col_box = st.columns([1, 1])

    with col_sc:
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin:1.2rem 0 0.3rem 0;">
            📈 Histórico vs tu riesgo personal
        </h4>
        <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0 0 0.4rem 0;">
            Eje horizontal: abandono histórico de cada titulación.
            Eje vertical: tu riesgo predicho. La diagonal marca la igualdad:
            <strong>por encima</strong>, peor que la media; <strong>por debajo</strong>, mejor.
        </p>
        """, unsafe_allow_html=True)
        import plotly.graph_objects as _go
        fig_sc = _go.Figure()
        # Diagonal de referencia (igualdad)
        _max = max([max(d["tasa_hist"], d["prob"]*100) for d in datos] + [50]) + 15
        fig_sc.add_trace(_go.Scatter(
            x=[0, _max], y=[0, _max], mode='lines',
            line=dict(color=COLORES['texto_suave'], dash='dash', width=1),
            name='Igualdad (histórico = tu riesgo)',
            hoverinfo='skip',
            showlegend=False,  # explicación en la caption debajo del gráfico
        ))
        # Un marcador por titulación, SIN texto sobre el punto.
        # La identificación pasa a la leyenda horizontal inferior. Esto evita
        # el solape cuando las etiquetas de los puntos están próximas entre sí
        # (p.ej. 5 titulaciones con riesgos similares en el rango 65-75%).
        for d in datos:
            fig_sc.add_trace(_go.Scatter(
                x=[d["tasa_hist"]], y=[d["prob"]*100],
                mode='markers',
                marker=dict(size=18, color=d["color"],
                            line=dict(color='white', width=2)),
                # Nombre sin prefijo "Grado en " → entra en la leyenda de forma
                # compacta pero legible al completo.
                name=d["nombre"],
                # Auditoría p03 (Chat p03, 27/04/2026): hover usaba
                # d['titulacion'] (con "Grado en "), ahora usa d['nombre']
                # para coherencia con el name/leyenda. También :,.1f para
                # coma decimal española (con separators=",.", del layout).
                hovertemplate=(
                    f"<b>{d['nombre']}</b><br>"
                    f"Histórico: %{{x:,.1f}}%<br>"
                    f"Tu riesgo: %{{y:,.1f}}%<extra></extra>"
                ),
                showlegend=True,
            ))
        fig_sc.update_layout(
            separators=",.",
            xaxis_title="Abandono histórico (%)",
            yaxis_title="Tu riesgo personal (%)",
            xaxis=dict(range=[0, _max], showgrid=True, gridcolor=COLORES['borde']),
            yaxis=dict(range=[0, _max], showgrid=True, gridcolor=COLORES['borde']),
            paper_bgcolor="white",
            plot_bgcolor="white",
            height=420,
            # Margen inferior amplio para la leyenda horizontal; márgenes
            # laterales normales ya que los nombres no viven sobre el plot.
            margin=dict(l=60, r=30, t=30, b=110),
            showlegend=True,
            # Leyenda horizontal debajo del gráfico. x=0.5 + xanchor='center'
            # la centra; y negativo la coloca fuera del área del plot.
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
                bgcolor="rgba(255,255,255,0.8)",
            ),
        )
        st.plotly_chart(fig_sc, width='stretch', key='scatter_hist_vs_tu_riesgo')
        st.caption(
            "💡 Si un punto está por encima de la diagonal, tu perfil es más "
            "vulnerable que la media de esa titulación. Si está por debajo, estás mejor."
        )

    # ------------------------------------------------------------------
    # 5d. Box plot + rug plot: distribución real por titulación
    # ------------------------------------------------------------------
    with col_box:
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin:1.2rem 0 0.3rem 0;">
            📦 Tu posición vs distribución por titulación
        </h4>
        <p style="font-size:0.82rem; color:{COLORES['texto_suave']}; margin:0 0 0.4rem 0;">
            Caja con cuartiles + rug plot con puntos individuales del
            conjunto de test. Si el diamante cae <strong>dentro</strong> de
            la caja, tu perfil es típico; si cae <strong>fuera</strong>, eres atípico.
        </p>
        """, unsafe_allow_html=True)

        fig_bx = _go.Figure()

        # Para cada titulación: recopilamos las probs reales del test
        hay_datos_box = False
        for d in datos:
            df_tit_box = _filtrar_por_titulacion(df_ref, d["titulacion"]) \
                if "titulacion" in df_ref.columns else df_ref.copy()

            # Probs del test de esa titulación
            if 'prob_abandono' in df_tit_box.columns:
                probs_tit = df_tit_box['prob_abandono'].dropna().values * 100
            else:
                # Fallback: usamos tasa histórica como aproximación binaria
                if 'abandono' in df_tit_box.columns:
                    probs_tit = df_tit_box['abandono'].dropna().astype(float).values * 100
                else:
                    probs_tit = np.array([])

            if len(probs_tit) < 5:
                continue
            hay_datos_box = True

            fig_bx.add_trace(_go.Box(
                y=probs_tit,
                x=[d["nombre_corto"]] * len(probs_tit),
                name=d["nombre_corto"],
                marker=dict(color=d["color"], opacity=0.55, size=3),
                fillcolor=_hex_a_rgba(d["color"], 0.18),
                line=dict(color=d["color"], width=1.5),
                boxpoints='all',
                pointpos=1.8,
                jitter=0.4,
                hovertemplate='%{y:,.1f}%<extra></extra>',
                showlegend=False,
            ))

        if not hay_datos_box:
            st.info("Sin probabilidades de test suficientes por titulación para el box plot.")
        else:
            # Diamante con tu riesgo personal por titulación.
            # Sin etiqueta de texto para evitar que se salga del eje cuando
            # el riesgo es muy alto (>85%). El valor está en hover y en la tabla.
            fig_bx.add_trace(_go.Scatter(
                x=[d["nombre_corto"] for d in datos],
                y=[d["prob"]*100 for d in datos],
                mode='markers',
                marker=dict(
                    symbol='diamond',
                    size=18,
                    color=[d["color"] for d in datos],
                    line=dict(color=COLORES['texto'], width=2),
                ),
                # cliponaxis=False: garantía de que el diamante nunca se
                # convertirá en triángulo rojo "fuera de rango" aunque la
                # prob del usuario coincida con un extremo del eje Y.
                cliponaxis=False,
                showlegend=False,
                hovertemplate='Tu riesgo: %{y:,.1f}%<extra></extra>',
            ))

            # Rango Y dinámico: calculamos el extremo entre (a) las probs
            # reales del test que ya están en los boxes (implícito en datos
            # de las trazas) y (b) los diamantes del usuario. Como no
            # tenemos acceso directo a probs_tit fuera del bucle, usamos
            # el max de los diamantes + un colchón. El box siempre está en
            # [0, 100] porque son probabilidades, así que [0, 100] cubre
            # los puntos del test. Los diamantes pueden estar hasta 99,99%
            # con el fix logit → añadimos +3 de colchón superior.
            _probs_user = [d["prob"] * 100 for d in datos]
            _y_max = min(105, max(100, max(_probs_user) + 3))
            _y_min = max(-5, min(0, min(_probs_user) - 3))

            fig_bx.update_layout(
                separators=",.",
                yaxis=dict(title="Probabilidad de abandono (%)",
                           range=[_y_min, _y_max], ticksuffix="%",
                           showgrid=True, gridcolor=COLORES['borde']),
                xaxis=dict(showgrid=False,
                           # tickangle=0: nombres horizontales. Con
                           # nombre_corto en 2 líneas caben sin diagonal.
                           tickangle=0),
                paper_bgcolor='white',
                plot_bgcolor='white',
                height=420,
                # Márgenes: derecha generosa para que la 5ª caja no se
                # corte; inferior amplia para los nombres en 2 líneas.
                margin=dict(l=60, r=60, t=20, b=80),
                showlegend=False,
                # boxgap: separación entre cajas (0 = pegadas, 1 = muy
                # separadas). Con 5 titulaciones + rug al lado, 0.45
                # deja aire suficiente.
                boxgap=0.45,
            )
            st.plotly_chart(fig_bx, width='stretch', key='boxplot_rug_titulaciones')
            st.caption(
                "◆ Diamante = tu riesgo · Caja = Q1-Q3 · Línea = mediana · "
                "Puntos al lado = cada alumno del test."
            )


    # ------------------------------------------------------------------
    # 6. Detalle expandible por titulación — radar + cascada
    # ------------------------------------------------------------------
    st.divider()
    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin:0.5rem 0 0.3rem 0;">
        🔎 Detalle por titulación
    </h4>
    <p style="font-size:0.83rem; color:{COLORES['texto_suave']}; margin:0 0 0.8rem 0;">
        Despliega para ver el perfil de abandono histórico y los factores de riesgo.
    </p>""", unsafe_allow_html=True)

    # === SELECTOR GLOBAL: Rapido vs Preciso (PASO 3 Bloque 4) =========
    # Conexión real activada en PASO 4. Se coloca ANTES del bucle para
    # que un solo selector controle TODOS los dot plots de las
    # titulaciones comparadas.
    #
    # FIX 29/04/2026: key única basada en cuántas titulaciones se
    # comparan (evita colisiones si el usuario cambia el conjunto sin
    # recargar página).
    _n_tits = len(titulaciones) if titulaciones else 0
    _metodo_dotplot_comp = _selector_metodo_global(
        key_suffix=f"comparativa_n{_n_tits}"
    )

    for idx_d, d in enumerate(datos):
        col_hist_nivel = COLORES["abandono"] if d["tasa_hist"] >= 40 \
            else COLORES["advertencia"] if d["tasa_hist"] >= 25 else COLORES["exito"]
        # Variables intermedias para coma española en el label y título del
        # expander (f-strings anidadas con comillas dobles no válidas en Py).
        _hist_lbl = f"{d['tasa_hist']:.1f}".replace('.', ',')
        _prob_lbl = f"{d['prob']*100:.1f}".replace('.', ',')
        label = (
            f"<span style='color:{d['color']};'>■</span> "
            f"{d['nombre_40']} — "
            f"Histórico: {_hist_lbl}% · "
            f"Tu riesgo: {_prob_lbl}% · "
            f"{d['n_alumnos']:,} alumnos"
        )
        with st.expander(
            f"{d['nombre_40']} — Histórico: {_hist_lbl}% · Tu riesgo: {_prob_lbl}%",
            expanded=False,
        ):
            ctx_tit = {
                "tipo":        "titulacion",
                "valor":       d["titulacion"],
                "df_contexto": _filtrar_por_titulacion(df_ref, d["titulacion"])
                               if "titulacion" in df_ref.columns else df_ref.copy(),
            }
            c1, c2 = st.columns([1, 1])
            with c1:
                # Bug fix (Chat p03, 27/04/2026): key_suffix con idx_d para
                # diferenciar este radar (dentro de expander de comparativa)
                # del radar principal cuando el contexto tiene la misma
                # titulación. Antes daba StreamlitDuplicateElementKey.
                _sfx_radar = f"exp{idx_d}"
                _grafico_radar(perfil, df_ref, ctx_tit, d['prob'],
                               key_suffix=_sfx_radar)
            with c2:
                df_tit_exp = _filtrar_por_titulacion(df_ref, d['titulacion']).copy() if 'titulacion' in df_ref.columns else df_ref
                # key_suffix único por titulación para evitar colisión con
                # otras cascadas que tengan la misma prob (p.ej. 0.99 en 2 titulaciones).
                _suf_key = f"{idx_d}_{d['titulacion'][:20].replace(' ', '_')}"
                # La comparativa siempre se invoca desde modo prospecto (p03).
                _grafico_cascada(perfil, df_tit_exp, d['prob'], modelo, pipeline,
                                 key_suffix=_suf_key, modo="prospecto",
                                 metodo=_metodo_dotplot_comp)

    # ------------------------------------------------------------------
    # 6bis. ¿Dónde estás respecto a otros alumnos? — agregado sobre
    #       las titulaciones elegidas (sin selector, un solo contexto)
    # ------------------------------------------------------------------
    st.divider()
    # prob representativa = media de las probs por titulación elegida
    prob_agregada = float(np.mean([d['prob'] for d in datos])) if datos else 0.0
    _seccion_donde_estas_multi(
        prob_agregada,
        [d['titulacion'] for d in datos],
        df_ref, modelo, pipeline,
    )

    # ------------------------------------------------------------------
    # 7. Recomendaciones personalizadas basadas en el perfil
    # ------------------------------------------------------------------
    st.divider()
    _recomendaciones(perfil, datos[0]['prob'] if datos else 0.0, 'prospecto')


# =============================================================================
# RECOMENDACIONES PERSONALIZADAS
# =============================================================================

def _recomendaciones(perfil: dict, prob: float, modo: str,
                      df_ctx: pd.DataFrame = None):
    """
    Genera recomendaciones concretas basadas en el perfil y el nivel de riesgo.
    Las recomendaciones son distintas para prospecto (antes de entrar) y
    en_curso (ya matriculado): el alumno en curso necesita orientación
    inmediata y acciones concretas, no consejos de acceso.
    """
    # Nota metodológica — transparencia sobre cómo se generan las recomendaciones
    # Estilo coherente con otras notas metodológicas de la app (p02, etc.)
    # Auditoría p00 (28/04/2026): #f0f9ff → rgba derivado de primario.
    _bg_nota = _hex_a_rgba(COLORES['primario'], 0.06)
    st.markdown(f"""
    <div style="
        background:{_bg_nota};
        border-left:3px solid {COLORES['primario']};
        border-radius:4px;
        padding:0.6rem 1rem;
        font-size:0.78rem;
        color:{COLORES['texto_suave']};
        margin:0.5rem 0 1rem 0;
    ">
        <strong>ℹ️ Nota metodológica:</strong> las recomendaciones se generan
        a partir de <strong>reglas heurísticas</strong> basadas en los factores
        del perfil (nota de acceso, situación laboral, beca, etc.), no del modelo
        de machine learning. Sirven como orientación, no como diagnóstico.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <h4 style="color:{COLORES['texto']}; margin-bottom:0.5rem;">
        💡 Recomendaciones personalizadas
    </h4>
    """, unsafe_allow_html=True)

    nivel, color, _, _ = _clasificar_riesgo(prob)
    recomendaciones = []

    # ------------------------------------------------------------------
    # MODO EN CURSO — alumno ya matriculado
    # Recomendaciones orientadas a la acción inmediata dentro de la UJI
    # ------------------------------------------------------------------
    if modo == "en_curso":

        nota_1er = perfil.get('nota_1er_anio', 10)
        cred_1er = perfil.get('cred_superados_anio_1er', 40)
        # Traducir string → código si hace falta (viene del formulario crudo)
        _sl = perfil.get('situacion_laboral', 1)
        if isinstance(_sl, str):
            _sl = OPCIONES_LABORAL_UI.get(_sl, 1)
        trabaja  = _sl in (2, 3)
        beca     = perfil.get('n_anios_beca', 0)

        if nota_1er < 5:
            recomendaciones.append({
                'icono': '🆘',
                'titulo': 'Contacta con tu tutor ahora',
                'texto': (
                    'Una nota media del primer año por debajo de 5 es una '
                    'señal de alerta importante. La Unidad de Soporte Educativo '
                    '(USE) de la UJI ofrece orientación durante los estudios. '
                    'Habla también con tu tutor/a de titulación.'
                ),
            })
        elif nota_1er < 7:
            recomendaciones.append({
                'icono': '📋',
                'titulo': 'Revisión de tu plan de estudios',
                'texto': (
                    'Tu rendimiento tiene margen de mejora. Considera revisar '
                    'con tu tutor si la carga de asignaturas es adecuada a '
                    'tu situación personal. Reducir créditos un año puede '
                    'ser más eficaz que repetir asignaturas.'
                ),
            })

        if cred_1er < 30:
            recomendaciones.append({
                'icono': '📉',
                'titulo': 'Pocos créditos superados',
                'texto': (
                    'Haber superado menos de 30 créditos al iniciar es un factor '
                    'de riesgo relevante. Habla con tu facultad sobre la posibilidad '
                    'de adaptar tu matrícula o acceder a grupos de refuerzo.'
                ),
            })

        if trabaja:
            recomendaciones.append({
                'icono': '⏰',
                'titulo': 'Compatibiliza trabajo y estudio',
                'texto': (
                    'Combinar trabajo y estudios aumenta el riesgo de abandono. '
                    'Consulta con tu facultad las opciones disponibles para '
                    'organizar tu carga lectiva (matrícula parcial, horarios, '
                    'etc.).'
                ),
            })

        if beca == 0 and nivel in ('Medio', 'Alto'):
            recomendaciones.append({
                'icono': '🎓',
                'titulo': 'Solicita una beca',
                'texto': (
                    'Los estudiantes becados tienen tasas de abandono '
                    'significativamente más bajas. Si cumples los requisitos '
                    'económicos, solicita la beca del Ministerio o las '
                    'propias de la UJI en la próxima convocatoria.'
                ),
            })

        if nivel == 'Bajo' or not recomendaciones:
            recomendaciones.append({
                'icono': '✅',
                'titulo': 'Vas por buen camino',
                'texto': (
                    'Tu perfil actual muestra factores protectores importantes. '
                    'Mantén el ritmo de estudio y no descuides los primeros '
                    'cuatrimestres — son los más decisivos para consolidar '
                    'el hábito académico.'
                ),
            })

    # ------------------------------------------------------------------
    # MODO PROSPECTO — alumno que todavía no está matriculado
    # Recomendaciones orientadas a la decisión de entrada
    # ------------------------------------------------------------------
    else:

        # El perfil viene del formulario como STRING ("Trabaja a tiempo parcial").
        # Usamos OPCIONES_LABORAL_UI para obtener el código numérico y luego
        # aplicar la lógica por códigos (1=no trabaja, 2=parcial, 3=completo).
        sit_lab_raw = perfil.get('situacion_laboral', 1)
        if isinstance(sit_lab_raw, str):
            cod_lab = OPCIONES_LABORAL_UI.get(sit_lab_raw, 1)
        else:
            cod_lab = sit_lab_raw
        beca    = perfil.get('n_anios_beca', 0)
        nota    = perfil.get('nota_acceso', 10)
        edad    = perfil.get('edad_entrada', 19)

        if beca == 0:
            recomendaciones.append({
                'icono': '🎓',
                'titulo': 'Infórmate sobre becas',
                'texto': (
                    'Los años con beca son uno de los factores protectores más '
                    'importantes. Consulta las convocatorias del Ministerio y '
                    'las becas propias de la UJI antes de matricularte.'
                ),
            })

        # Texto dinámico según el tipo de trabajo declarado
        # Solo aplica si el usuario marcó tiempo parcial (2) o completo (3).
        # No aplica para "No trabaja" (1) ni "Prefiero no indicarlo" (0).
        if cod_lab in (2, 3):
            tipo_jornada = "tiempo parcial" if cod_lab == 2 else "tiempo completo"
            # Lectura dinámica de la tasa media del JSON
            _t_lab = _leer_metricas_modelo().get("tasa_abandono")
            tasa_uji_pct = float(_t_lab) * 100 if _t_lab is not None else 29.25
            recomendaciones.append({
                'icono': '⏰',
                'titulo': f'Trabajas a {tipo_jornada} — planifica',
                'texto': (
                    f'Has indicado que trabajas a {tipo_jornada}. Combinar '
                    f'trabajo y estudios aumenta el riesgo de abandono. '
                    f'Consulta con tu facultad las opciones disponibles para '
                    f'organizar tu carga lectiva.'
                ),
            })

        # Recomendación de refuerzo académico: comparamos nota del usuario
        # vs media histórica del contexto (titulación o rama si la hay,
        # o toda UJI si el usuario eligió "Todas las titulaciones").
        media_ctx = None
        if df_ctx is not None and 'nota_acceso' in df_ctx.columns and len(df_ctx) > 0:
            media_ctx = float(df_ctx['nota_acceso'].mean())

        if media_ctx is not None and nota < media_ctx:
            recomendaciones.append({
                'icono': '📚',
                'titulo': 'Refuerzo académico desde el inicio',
                'texto': (
                    f'Tu nota de acceso ({nota:.2f}) está por debajo de la media '
                    f'histórica de tu contexto ({media_ctx:.2f}). '
                    f'Esto se puede compensar con buena organización desde el primer '
                    f'cuatrimestre. Los servicios de tutoría de la UJI están a tu '
                    f'disposición desde el primer día.'
                ),
            })
        elif media_ctx is None and nota < 7:
            # Fallback al criterio fijo si no hay contexto
            recomendaciones.append({
                'icono': '📚',
                'titulo': 'Refuerzo académico desde el inicio',
                'texto': (
                    'Una nota de acceso más baja se puede compensar con una '
                    'buena organización desde el primer cuatrimestre. Los '
                    'servicios de tutoría de la UJI están a tu disposición '
                    'desde el primer día.'
                ),
            })

        if edad > 25:
            recomendaciones.append({
                'icono': '🤝',
                'titulo': 'Aprovecha tu experiencia',
                'texto': (
                    'Los estudiantes maduros tienen más responsabilidades pero '
                    'también más motivación y experiencia vital. Visita el '
                    '<a href="https://www.uji.es/perfils/estudiantat/v2/nou-estudiantat/" '
                    'target="_blank">Portal Nuevo Estudiantado</a> para '
                    'información sobre acogida y orientación inicial.'
                ),
            })

        # "Buen perfil de entrada" SOLO si no hay otras recomendaciones
        # (antes salía siempre con nivel=Bajo, contradiciendo otras alertas)
        if not recomendaciones:
            recomendaciones.append({
                'icono': '✅',
                'titulo': 'Buen perfil de entrada',
                'texto': (
                    'Tu perfil muestra factores protectores importantes. '
                    'Mantén el mismo nivel de dedicación durante el primer año — '
                    'es el período más crítico para consolidar el hábito de estudio.'
                ),
            })

    # ------------------------------------------------------------------
    # Renderizado de tarjetas (igual para ambos modos)
    # ------------------------------------------------------------------
    cols = st.columns(min(len(recomendaciones), 3))
    for i, rec in enumerate(recomendaciones[:3]):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="
                background:white;
                border:1px solid {COLORES['borde']};
                border-top:3px solid {color};
                border-radius:8px;
                padding:0.7rem 0.9rem;
                min-height:auto;
            ">
                <div style="font-size:1.1rem; margin-bottom:0.1rem;">{rec['icono']}</div>
                <div style="font-weight:500; font-size:0.85rem;
                            color:{COLORES['texto']}; margin:0.1rem 0;">
                    {rec['titulo']}
                </div>
                <div style="font-size:0.74rem; color:{COLORES['texto_suave']};
                            line-height:1.35;">
                    {rec['texto']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# PANTALLA DE INSTRUCCIONES (antes de calcular)
# =============================================================================

def _mostrar_instrucciones():
    """Mensaje orientativo que se muestra antes de que el usuario calcule."""
    st.markdown(f"""
    <div style="text-align:center; padding:3rem 2rem; color:{COLORES['texto_suave']};">
        <div style="font-size:3rem; margin-bottom:1rem;">🔮</div>
        <div style="font-size:1.1rem; font-weight:bold; color:{COLORES['texto']};">
            Rellena tu perfil y pulsa "Calcular mi pronóstico"
        </div>
        <div style="font-size:0.88rem; margin-top:0.5rem;">
            El modelo analizará tu perfil y te mostrará una estimación
            personalizada de tu riesgo de abandono.
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _clasificar_riesgo ELIMINADA.
# Sustituida por _clasificar_riesgo de utils/ui_helpers.py.
# Importada al principio del fichero. Antes había 4 implementaciones
# (esta + _color_tasa en p01 + lógica inline en p01:408 + lógica inline en p02).
# =============================================================================


# =============================================================================
# FIN DE pronostico_shared.py
# =============================================================================
