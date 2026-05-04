# =============================================================================
# p01_institucional.py
# Pestaña 1 — Visión institucional
#
# ¿QUÉ HACE ESTE FICHERO?
#   Muestra una visión global del abandono universitario en la UJI.
#   Pensada para gestores y dirección académica que necesitan ver el
#   panorama completo de un vistazo, sin entrar en detalle de alumnos
#   concretos.
#
# ESTRUCTURA DE LA PÁGINA:
#   0. Filtros globales (sidebar) — afectan a TODOS los bloques
#   1. KPIs rápidos — métricas clave según filtros activos
#   2. Evolución temporal — tasa de abandono por año de cohorte
#   3. Abandono por rama — barras horizontales comparativas
#   4. Top titulaciones — tabla ordenable con más detalle
#   5. Distribución de riesgo predicho — donut bajo/medio/alto
#
# DATOS QUE USA:
#   - meta_test.parquet (vía loaders.cargar_meta_test)
#   - modelo + pipeline (vía loaders.cargar_modelo / cargar_pipeline)
#     para calcular probabilidades de abandono predichas
#
# REQUISITOS:
#   - config_app.py accesible (un nivel arriba)
#   - utils/loaders.py disponible
#   - Fase 5 ejecutada (modelo y pipeline en data/05_modelado/)
#   - Fase 6 ejecutada (meta_test en data/06_evaluacion/)
#
# GENERA:
#   Página HTML interactiva renderizada por Streamlit. No genera ficheros.
#
# SIGUIENTE:
#   pages/p02_titulacion.py — análisis por titulación individual
# =============================================================================

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Imports internos
# ---------------------------------------------------------------------------
# _path_setup añade app/ a sys.path de forma robusta en Windows/OneDrive
import _path_setup  # noqa: F401

from config_app import (
    APP_CONFIG,
    COLORES,
    COLORES_RAMAS,
    COLORES_RIESGO,
    COLORES_SEXO,
    NOMBRES_VARIABLES,
    RAMAS_NOMBRES,
    SEXO_INV,
    SITUACION_LABORAL_INV,
    UMBRALES,
    UMBRALES_MUESTRA,
    UNIVERSIDAD_ORIGEN_INV,
)
from config_app import RUTAS as _RUTAS
from utils.loaders import cargar_meta_test_app, cargar_modelo, cargar_pipeline
# REFACTOR p03 (Chat p03, 27/04/2026): _nombre_titulacion_corto y
# _clasificar_riesgo importados desde ui_helpers (antes había _partir_label
# local + regex inline + _color_tasa local).
from utils.ui_helpers import (
    _nombre_titulacion_corto, _clasificar_riesgo, _pie_pagina,
    _leer_metricas_modelo, _guardia_df_vacio, fmt,
)
import pandas as _pd


# =============================================================================
# CONSTANTES LOCALES — Colores del sparkline multi-línea (KPI Alumnos)
# =============================================================================
# Bug FASE C #14: el sparkline del KPI Alumnos mostraba una sola línea
# (N total por cohorte). María José pidió 3 líneas separadas por sexo:
#   - Total  (gris oscuro neutro)
#   - Hombre (azul institucional UJI)
#   - Mujer  (rosa reutilizado de la paleta de ramas)
#
# No hay una paleta "sexo" en COLORES (no había convención previa).
# Opción adoptada: reutilizar el rosa Dark24 de COLORES_RAMAS['Ciencias
# de la Salud'] para Mujer. Si mañana cambia ese color en SRC, el del
# sparkline cambiará también — es consciente, documentado, y se puede
# desacoplar aquí (basta editar la línea correspondiente).

# Colores de sexo — vienen de COLORES_SEXO (src/config_entorno.py)
# Independientes de COLORES_RAMAS para evitar acoplamiento involuntario
_COLOR_SPARKLINE_MUJER  = COLORES_SEXO["Mujer"]   # #db2777 rosa ODS5
_COLOR_SPARKLINE_HOMBRE = COLORES_SEXO["Hombre"]  # #2563eb azul
_COLOR_SPARKLINE_TOTAL  = COLORES_SEXO["Total"]   # #475569 gris pizarra


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def show():
    """
    Renderiza la pestaña de visión institucional completa — LAYOUT DASHBOARD.

    Estructura:
      1. Cabecera (título · subtítulo · badge fecha)
      2. Filtros (5 visibles + 6 en expander · botón borrar · badge muestra)
      3. Aviso de muestra pequeña (si aplica)
      4. Fila KPIs (4 tarjetas full width)
      5. Fila evolución (60%) + abandono por rama (40%)
      6. Fila top titulaciones (65%) + distribución riesgo (35%)
      7. Nota metodológica (expander)
    """

    # -------------------------------------------------------------------
    # 1. CABECERA DE LA PÁGINA
    # -------------------------------------------------------------------
    col_tit, col_badge = st.columns([4, 1])
    with col_tit:
        st.markdown(f"""
        <h2 style="color: {COLORES['primario']}; margin-bottom: 0.2rem;">
            🏛️ Visión institucional
        </h2>
        <p style="color: {COLORES['texto_suave']}; margin-top: 0; font-size: 0.95rem;">
            Panorama global de abandono universitario ·
            {APP_CONFIG['universidad_datos']} · Datos de test ({_leer_metricas_modelo().get('periodo_inicio',2010)}–{_leer_metricas_modelo().get('periodo_fin',2020)})
        </p>
        """, unsafe_allow_html=True)
    with col_badge:
        import datetime as _dt
        fecha_hoy = _dt.date.today().strftime("%d/%m/%Y")
        st.markdown(f"""
        <div style="text-align:right; padding-top:0.8rem;">
            <span style="background:{COLORES['blanco']};
                border:1px solid {COLORES['borde']};
                padding:0.3rem 0.7rem; border-radius:6px;
                font-size:0.75rem; color:{COLORES['texto_suave']};">
                Actualizado · {fecha_hoy}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # 2. CARGA DE DATOS
    # -------------------------------------------------------------------
    with st.spinner("Cargando datos..."):
        try:
            df_raw   = cargar_meta_test_app()
            modelo   = cargar_modelo()
            pipeline = cargar_pipeline()
        except FileNotFoundError as e:
            st.error(f"❌ No se pudieron cargar los datos:\n\n{e}")
            st.stop()

    # -------------------------------------------------------------------
    # 3. PREPARACIÓN DEL DATAFRAME
    # -------------------------------------------------------------------
    # Calcular probabilidades y nivel de riesgo (bajo/medio/alto)
    df = _añadir_probabilidades(df_raw, modelo, pipeline)

    # Alias _meta para compatibilidad con filtros y gráficos (texto legible)
    for col in ['rama', 'sexo', 'via_acceso', 'pais_nombre', 'provincia']:
        if col in df.columns and f'{col}_meta' not in df.columns:
            df[f'{col}_meta'] = df[col]

    # Traducir abreviaturas de rama (SO, TE...) a nombres completos
    if 'rama_meta' in df.columns:
        df['rama_meta'] = df['rama_meta'].map(RAMAS_NOMBRES).fillna(df['rama_meta'])

    # Añadir nivel de riesgo a partir de la probabilidad predicha
    df = _añadir_nivel_riesgo(df)

    # -------------------------------------------------------------------
    # FILTRO IMPLÍCITO: universo de análisis = cursos 2010-2020
    # -------------------------------------------------------------------
    # FASE F Bloque 3: el TFM está definido sobre cursos 2010-2020. En el
    # parquet meta_test_app hay ~129 alumnos con curso_aca_ini < 2010 que
    # no forman parte del universo del TFM.
    #
    # Motivo del cambio: antes, el bloque amarillo mostraba "6.596 de 6.725
    # observaciones (98,1%)" incluso sin filtros, lo cual era incoherente.
    # Ahora df_completo YA excluye los cursos previos a 2010, así que el
    # universo de referencia coincide con el que realmente analizamos y
    # sin filtros aparece "6.596 de 6.596 (100%)".
    #
    # Los filtros posteriores de _aplicar_filtros_grid aplican el mismo
    # filtro curso >= 2010, así que este cambio NO altera df_filtrado —
    # solo alinea el total de referencia para que sea coherente.
    if 'curso_aca_ini' in df.columns:
        df = df[df['curso_aca_ini'] >= 2010].reset_index(drop=True)

    # -------------------------------------------------------------------
    # 4. BLOQUE DE FILTROS (nuevo: 5 visibles + 6 expander + borrar)
    # -------------------------------------------------------------------
    df_filtrado = _aplicar_filtros_grid(df)

    # -------------------------------------------------------------------
    # 5. AVISO DE MUESTRA PEQUEÑA (basado en UMBRALES_MUESTRA)
    # -------------------------------------------------------------------
    n_muestra = len(df_filtrado)
    if n_muestra < UMBRALES_MUESTRA['minima']:
        col_av, col_btn = st.columns([4, 1])
        with col_av:
            st.error(
                f"❌ Muestra insuficiente ({n_muestra} alumnos). "
                f"Los porcentajes no son fiables estadísticamente. "
                f"Te recomendamos ampliar o borrar los filtros para obtener resultados representativos."
            )
        with col_btn:
            if st.button("🗑️ Borrar filtros", key="btn_borrar_muestra_min"):
                for _k in [k for k in st.session_state if k.startswith("filtro_")]:
                    del st.session_state[_k]
                st.rerun()
    elif n_muestra < UMBRALES_MUESTRA['aceptable']:
        col_av, col_btn = st.columns([4, 1])
        with col_av:
            st.warning(
                f"⚠️ Muestra muy pequeña ({n_muestra} alumnos). "
                f"Los resultados son orientativos. "
                f"Amplía los filtros para mayor representatividad."
            )
        with col_btn:
            if st.button("🗑️ Borrar filtros", key="btn_borrar_muestra_peq"):
                for _k in [k for k in st.session_state if k.startswith("filtro_")]:
                    del st.session_state[_k]
                st.rerun()
    elif n_muestra < UMBRALES_MUESTRA['fiable']:
        st.info(
            f"ℹ️ Muestra pequeña ({n_muestra} alumnos). "
            f"Los porcentajes son indicativos."
        )

    # --------------------------------------------------------------
    # VALORES DE REFERENCIA — Tasas del test completo SIN filtros
    # --------------------------------------------------------------
    # Se usan en los KPIs como líneas "vs media UJI": permiten comparar
    # la selección actual (con filtros aplicados) contra la media global.
    #
    # - _tasa_ref   : % de alumnos que abandonan en todo el test
    # - _riesgo_ref : % de alumnos clasificados como 'Alto' en todo el test
    #
    # Bug FASE C #12: antes _riesgo_ref no existía y el delta vs UJI del
    # KPI Riesgo alto estaba hardcoded a 0.0. Ahora se calcula real.
    #
    # FASE F iter 8: si la columna 'abandono' no existe, leemos la tasa
    # desde metricas_modelo.json (dinámico). Si tampoco está el JSON, usamos
    # 29.25 como último recurso documentado.
    if 'abandono' in df.columns:
        _tasa_ref = df['abandono'].mean() * 100
    else:
        _metricas_mod = _leer_metricas_modelo()
        _tasa_json    = _metricas_mod.get('tasa_abandono')
        _tasa_ref     = float(_tasa_json) * 100 if _tasa_json is not None else 29.25

    _riesgo_ref = (
        (df['nivel_riesgo'] == 'Alto').mean() * 100
        if 'nivel_riesgo' in df.columns else 0.0
    )

    # -------------------------------------------------------------------
    # 6. FILA KPIs (4 tarjetas a full width)
    # -------------------------------------------------------------------
    _bloque_kpis_global(df_filtrado, tasa_ref=_tasa_ref, riesgo_ref=_riesgo_ref)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # 7. FILA 2: Evolución temporal (50%) + Abandono por rama (50%)
    # -------------------------------------------------------------------
    # FASE D #18: antes era [3, 2] (60/40). El gráfico de Rama quedaba
    # demasiado estrecho para ver las etiquetas de nombres completos.
    # 50/50 da más aire a ambos gráficos.
    col_evo, col_rama = st.columns([1, 1])
    with col_evo:
        _bloque_evolucion_temporal_global(df_filtrado)
    with col_rama:
        _bloque_abandono_por_rama(df_filtrado)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # 8. FILA 3: Gráficos de riesgo arriba + Tabla titulaciones abajo
    # -------------------------------------------------------------------
    # FASE D+E #8 (ITERACIÓN 2): mjmr prefiere el orden visual estándar de
    # dashboard — resumen general primero (gráficos), detalle después (tabla):
    #
    #   ┌──────────────────────┬──────────────────────┐
    #   │  Barras por rama     │  Donut distribución  │
    #   │  (50%)               │  (50%)               │
    #   └──────────────────────┴──────────────────────┘
    #   ┌─────────────────────────────────────────────┐
    #   │  Tabla titulaciones (ancho completo)        │
    #   └─────────────────────────────────────────────┘
    #
    # Ventaja: el usuario ve primero el panorama (donut + barras) y luego
    # baja al detalle por titulación. Orden natural de lectura.
    col_barras, col_donut = st.columns([1, 1])
    with col_barras:
        _bloque_barras_riesgo_por_rama(df_filtrado)
    with col_donut:
        _bloque_donut_riesgo(df_filtrado)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabla de titulaciones — no ocupa el ancho completo para que respire
    # FASE D+E iter 3 #4: mjmr pidió no tan ancha, con margen a ambos lados.
    # Proporción [1, 14, 1] → tabla ocupa ~87% del ancho, 6.5% margen cada lado.
    _col_margen_izq, col_tabla, _col_margen_der = st.columns([1, 14, 1])
    with col_tabla:
        _bloque_top_titulaciones(df_filtrado)

    st.divider()

    # -------------------------------------------------------------------
    # 9. NOTA METODOLÓGICA (general + selección actual)
    # -------------------------------------------------------------------
    # FASE D+E iter 6 #A: ahora son 2 expanders separados.
    #   - Primero: nota metodológica general (dataset, modelo, limitaciones)
    #   - Segundo: resumen de la selección actual con fondo amarillo claro,
    #     2 bloques (resultados vs UJI y demografía), comparativa vs global.
    with st.expander("📋 Nota metodológica — haz clic para ampliar", expanded=False):
        # Métricas leídas dinámicamente desde metricas_modelo.json.
        # SIN FALLBACKS NUMÉRICOS: si el JSON falla por cualquier razón,
        # fmt() devuelve "—" en lugar de números obsoletos del modelo
        # anterior. Esto preserva el carácter dinámico del proyecto:
        # el código no contiene métricas hardcodeadas que pudieran
        # quedar desincronizadas con el modelo activo.
        _m = _leer_metricas_modelo()
        _n_reg    = fmt(_m.get('n_registros'),      'miles')
        _n_alu    = fmt(_m.get('n_alumnos_unicos'), 'miles')
        _n_test   = fmt(_m.get('n_test'),           'miles')
        _tasa_pct = fmt(_m.get('tasa_abandono'),    'proporcion', decimales=1)
        _auc      = fmt(_m.get('auc'),              'decimal',    decimales=3)
        _f1       = fmt(_m.get('f1'),               'decimal',    decimales=3)
        st.markdown(f"""
        **Dataset:** {_n_reg} registros de modelado · {_n_alu} alumnos únicos · {APP_CONFIG['universidad_datos']} · Cursos {_m.get('periodo_inicio',2010)}–{_m.get('periodo_fin',2020)}.

        **Variable objetivo:** abandono definitivo del grado (definición estricta). Tasa de abandono en test: **{_tasa_pct}**.

        **Modelo final:** {_m.get('modelo_nombre', 'Modelo de clasificación')} ({_m.get('modelo_familia', '—')}) — {_m.get('modelo_descripcion', 'Modelo entrenado sobre el dataset D_strict.')} AUC = {_auc} · F1 = {_f1}.

        **Sobre los gráficos:** los porcentajes de riesgo son predicciones del modelo, no valores reales observados.
        La tasa de abandono real corresponde a los datos históricos del conjunto de test ({_n_test} observaciones).

        **Limitaciones:** el modelo está entrenado con datos hasta 2020. Las predicciones para cohortes
        posteriores deben interpretarse con cautela.
        """)

        # Bloque "Tu selección actual" — fondo amarillo claro con resultados + demografía
        _bloque_resumen_seleccion(df, df_filtrado, _tasa_ref)

    # Pie de página
    # REFACTOR p03 (Chat p03, 27/04/2026): pie de página inline sustituido
    # por _pie_pagina() de utils/ui_helpers.py (centralizado).
    _pie_pagina()


# =============================================================================
# HELPERS DE DATOS
# =============================================================================

def _añadir_probabilidades(df_raw: pd.DataFrame, modelo, pipeline) -> pd.DataFrame:
    """
    Calcula prob_abandono usando X_test_prep.parquet (ya preprocesado en Fase 5).
    Se une por índice con df_raw (meta_test_app). Así evitamos pasar columnas
    categóricas en texto crudo al pipeline, que espera valores numéricos.
    """
    df = df_raw.copy()

    try:
        # Cargar X_test_prep — features ya preprocesadas por el pipeline de Fase 5
        ruta_xprep = _RUTAS.get("X_test_prep")
        if ruta_xprep is None or not ruta_xprep.exists():
            raise FileNotFoundError(f"X_test_prep no encontrado en {ruta_xprep}")

        X_prep = _pd.read_parquet(ruta_xprep)

        # Calcular probabilidades directamente sobre X_test_prep
        prob = modelo.predict_proba(X_prep)[:, 1]

        # Unir por índice — ambos tienen el mismo índice posicional
        # Si meta_test_app ya trae prob_abandono guardada, la eliminamos antes
        # del join para evitar conflicto de columnas duplicadas
        if "prob_abandono" in df.columns:
            df = df.drop(columns=["prob_abandono"])
        prob_series = _pd.Series(prob, index=X_prep.index, name="prob_abandono")
        df = df.join(prob_series, how="left")

    except Exception as e:
        st.warning(f"⚠️ No se pudieron calcular las probabilidades: {e}")
        df['prob_abandono'] = np.nan

    return df


def _añadir_nivel_riesgo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica cada alumno en nivel de riesgo según su probabilidad predicha.
    Añade la columna 'nivel_riesgo' con valores: 'Bajo', 'Medio', 'Alto'.
    """
    df = df.copy()

    # NOTA REFACTOR p03 (Chat p03, 27/04/2026): esta lógica interna NO se
    # sustituye por _clasificar_riesgo de ui_helpers porque aquí se necesita
    # devolver SOLO el string del nivel + manejar NaN (devuelve 'Desconocido').
    # _clasificar_riesgo devuelve tupla (nivel, color, emoji, mensaje) y no
    # maneja NaN. Los umbrales sí se leen de UMBRALES centralizado.
    def _clasificar(prob):
        if pd.isna(prob):
            return 'Desconocido'
        if prob < UMBRALES['riesgo_bajo']:
            return 'Bajo'
        elif prob < UMBRALES['riesgo_medio']:
            return 'Medio'
        else:
            return 'Alto'

    df['nivel_riesgo'] = df['prob_abandono'].apply(_clasificar)
    return df


# =============================================================================
# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _leer_metricas_modelo ELIMINADA.
# Sustituida por _leer_metricas_modelo de utils/ui_helpers.py.
# Antes había 2 copias idénticas en p01 y p02.
# =============================================================================


def _aplicar_filtros_grid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bloque de filtros con layout en grid — 5 visibles + 6 en expander.

    Visibles (siempre):
      1. Sexo          (selectbox)
      2. Rama          (multiselect)
      3. Cohorte       (slider de rango)
      4. Situación     (selectbox con código → texto vía SITUACION_LABORAL_INV)
      5. Nota acceso   (slider de rango)

    Avanzados (expander, plegado por defecto):
      6. Nivel riesgo  (multiselect Bajo/Medio/Alto)
      7. Titulación    (multiselect)
      8. Vía acceso    (multiselect)
      9. Universidad   (multiselect con código → texto vía UNIVERSIDAD_ORIGEN_INV)
     10. Cupo          (multiselect — NaN se muestra como 'Sin dato')
     11. Años beca     (slider de rango)

    Adicionales:
      - Botón 🗑️ Borrar filtros → resetea session_state
      - Badge "📋 Mostrando X de Y · N filtros activos"
    """

    # Lista documental de todas las keys de widgets de filtros (NO se usa
    # directamente para borrar — cada tipo se limpia con su propia técnica).
    # Se mantiene como referencia para desarrolladores.
    _claves_filtros_p01 = [
        "filtro_sexo_p01", "filtro_rama_p01",
        "filtro_anios_p01 (slider, versionada)",
        "filtro_sit_lab_p01", "filtro_nota_acc_p01 (slider, versionada)",
        "filtro_riesgo_p01", "filtro_titulacion_p01", "filtro_via_p01",
        "filtro_universidad_p01", "filtro_cupo_p01",
        "filtro_beca_p01 (slider, versionada)",
    ]

    # PATRÓN ITER 5 (Streamlit 1.45+) — reseteo de filtros sin callback.
    #
    # Problema de iter 4: el patrón callback + flag + st.rerun() no reseteaba
    # los sliders en versión 1.45.1. Hipótesis: el callback `on_click` se
    # ejecuta DENTRO del script run actual, y el rerun que Streamlit provoca
    # automáticamente después NO vuelve a leer el bloque de borrado (lee el
    # valor cacheado de session_state[flag] antes del cambio).
    #
    # Solución iter 5: detectar el click del botón DIRECTAMENTE con la
    # expresión `if st.button(...)` (que devuelve True en el rerun inmediato
    # después del click), y ejecutar el borrado ANTES de instanciar los
    # widgets. Así nos saltamos toda la lógica de flags y callbacks.
    #
    # Sobre sliders: usamos keys versionadas (filtro_xxx_p01_v{N}) donde N
    # se incrementa al pulsar Borrar. Al cambiar la key, Streamlit crea un
    # widget nuevo y respeta el `value` por defecto.
    if "_p01_filtros_version" not in st.session_state:
        st.session_state["_p01_filtros_version"] = 0

    _valores_defecto_filtros = {
        "filtro_sexo_p01":        "Todos",
        "filtro_rama_p01":        [],
        "filtro_sit_lab_p01":     "Todas",
        "filtro_riesgo_p01":      [],
        "filtro_titulacion_p01":  [],
        "filtro_via_p01":         [],
        "filtro_universidad_p01": [],
        "filtro_cupo_p01":        [],
    }

    # Versión actual para las keys de los sliders (se usa abajo en st.slider)
    _v_filtros = st.session_state["_p01_filtros_version"]

    # -------------------------------------------------------------------
    # Cabecera del bloque de filtros
    # -------------------------------------------------------------------
    col_titulo, col_btn = st.columns([5, 1])
    with col_titulo:
        st.markdown(f"""
        <div style="font-weight:600; color:{COLORES['texto']};
            font-size:0.95rem; padding-top:0.3rem;">
            🔎 Filtros
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        # ITER 5: detección directa del click (sin on_click).
        # Si se pulsa, ejecutamos la lógica de borrado aquí mismo y llamamos
        # st.rerun() para regenerar todo el bloque desde cero.
        _click_borrar = st.button(
            "🗑️ Borrar filtros",
            key="btn_borrar_filtros_p01",
            width='stretch',
            help="Limpia todos los filtros y vuelve a ver el conjunto completo"
        )
        if _click_borrar:
            # 1. Resetear selectbox/multiselect → valor por defecto
            for k, v_default in _valores_defecto_filtros.items():
                st.session_state[k] = v_default
            # 2. Sliders → incrementar versión (fuerza key nueva, widget nuevo)
            st.session_state["_p01_filtros_version"] += 1
            # 3. Borrar filtros auxiliares
            for extra in ["rama_filtro_tabla"]:
                if extra in st.session_state:
                    try:
                        del st.session_state[extra]
                    except KeyError:
                        pass
            # 4. Rerun inmediato → todos los widgets se regeneran desde cero
            st.rerun()

    df_f = df.copy()

    # -------------------------------------------------------------------
    # FILA VISIBLE — 5 filtros principales
    # -------------------------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)

    # --- 1. Sexo ---
    with col1:
        col_sexo = 'sexo_meta' if 'sexo_meta' in df.columns else 'sexo'
        if col_sexo in df.columns:
            opciones_sexo = ["Todos"] + sorted(df[col_sexo].dropna().unique().tolist())
            sexo_sel = st.selectbox(
                "Sexo",
                options=opciones_sexo,
                key="filtro_sexo_p01",
                help="Filtra por sexo"
            )
            if sexo_sel != "Todos":
                df_f = df_f[df_f[col_sexo] == sexo_sel]

    # --- 2. Rama ---
    with col2:
        col_rama_s = 'rama_meta' if 'rama_meta' in df_f.columns else 'rama'
        if col_rama_s in df_f.columns:
            ramas_disp = sorted(df_f[col_rama_s].dropna().unique().tolist())
            ramas_sel = st.multiselect(
                "Rama",
                options=ramas_disp,
                placeholder="Todas",
                key="filtro_rama_p01",
                help="Deja vacío para ver todas. Selecciona una o varias para filtrar."
            )
            if ramas_sel:
                df_f = df_f[df_f[col_rama_s].isin(ramas_sel)]

    # --- 3. Cohorte (rango de años) ---
    with col3:
        if 'curso_aca_ini' in df_f.columns and df_f['curso_aca_ini'].notna().any():
            # Excluir 2009: alumnos pre-grado (curso idiomas/valenciano)
            df_f = df_f[df_f['curso_aca_ini'] >= 2010]
            if len(df_f) > 0:
                a_min = int(df_f['curso_aca_ini'].min())
                a_max = int(df_f['curso_aca_ini'].max())
                if a_min < a_max:
                    rango_anios = st.slider(
                        "Cohorte",
                        min_value=a_min,
                        max_value=a_max,
                        value=(a_min, a_max),
                        step=1,
                        key=f"filtro_anios_p01_v{_v_filtros}",
                        help="Rango de años de inicio de estudios"
                    )
                    df_f = df_f[
                        (df_f['curso_aca_ini'] >= rango_anios[0]) &
                        (df_f['curso_aca_ini'] <= rango_anios[1])
                    ]

    # --- 4. Situación laboral (código → texto) ---
    with col4:
        if 'situacion_laboral' in df.columns:
            # Códigos únicos presentes en los datos (antes de filtrar más)
            codigos_presentes = sorted(df['situacion_laboral'].dropna().unique().tolist())
            # Convertir código → etiqueta legible usando SITUACION_LABORAL_INV
            # Si un código no está en el diccionario, mostrar "Código N"
            opciones_sit = ["Todas"] + [
                SITUACION_LABORAL_INV.get(int(c), f"Código {int(c)}")
                for c in codigos_presentes
            ]
            sit_sel = st.selectbox(
                "Situación laboral",
                options=opciones_sit,
                key="filtro_sit_lab_p01",
                help="Filtra por situación laboral del alumno"
            )
            if sit_sel != "Todas":
                # Buscar el código que corresponde a la etiqueta elegida
                codigo_sel = None
                for c in codigos_presentes:
                    etiqueta = SITUACION_LABORAL_INV.get(int(c), f"Código {int(c)}")
                    if etiqueta == sit_sel:
                        codigo_sel = int(c)
                        break
                if codigo_sel is not None:
                    df_f = df_f[df_f['situacion_laboral'] == codigo_sel]

    # --- 5. Nota de acceso (rango numérico) ---
    with col5:
        if 'nota_acceso' in df_f.columns and df_f['nota_acceso'].notna().any():
            nota_min = float(df['nota_acceso'].min())
            nota_max = float(df['nota_acceso'].max())
            if nota_min < nota_max:
                rango_nota = st.slider(
                    "Nota acceso",
                    min_value=round(nota_min, 1),
                    max_value=round(nota_max, 1),
                    value=(round(nota_min, 1), round(nota_max, 1)),
                    step=0.1,
                    key=f"filtro_nota_acc_p01_v{_v_filtros}",
                    help="Rango de nota de acceso a la universidad"
                )
                df_f = df_f[
                    (df_f['nota_acceso'] >= rango_nota[0]) &
                    (df_f['nota_acceso'] <= rango_nota[1])
                ]

    # -------------------------------------------------------------------
    # EXPANDER — 6 filtros avanzados
    # -------------------------------------------------------------------
    with st.expander("🔧 Filtros avanzados (6) — riesgo · titulación · vía · universidad · cupo · beca", expanded=False):

        col_a, col_b, col_c = st.columns(3)

        # --- 6. Nivel de riesgo (CASCADA) ---
        # Cascada: solo se muestran niveles presentes en df_f (ya filtrado
        # por Sexo, Rama, Cohorte, Situación, Nota). Se limpian automáticamente
        # selecciones incompatibles de session_state.
        with col_a:
            if 'nivel_riesgo' in df_f.columns:
                niveles_posibles = ["Bajo", "Medio", "Alto"]
                # Niveles realmente presentes en df_f (cascada real)
                niveles_disp = [n for n in niveles_posibles if n in df_f['nivel_riesgo'].unique()]
                # Limpieza automática de selecciones incompatibles
                _sel_previa = st.session_state.get("filtro_riesgo_p01", [])
                _sel_valida = [r for r in _sel_previa if r in niveles_disp]
                if _sel_valida != _sel_previa:
                    st.session_state["filtro_riesgo_p01"] = _sel_valida
                riesgo_sel = st.multiselect(
                    "Nivel de riesgo",
                    options=niveles_disp,
                    placeholder="Todos",
                    key="filtro_riesgo_p01",
                    help=(
                        "Filtra por nivel de riesgo predicho por el modelo. "
                        "Nota: este filtro afecta a KPIs, tabla de titulaciones y "
                        "abandono por rama. No se aplica a Evolución temporal ni "
                        "Distribución del riesgo para preservar su interpretación."
                    )
                )
                if riesgo_sel:
                    df_f = df_f[df_f['nivel_riesgo'].isin(riesgo_sel)]

        # --- 7. Titulación (CASCADA) ---
        # Las opciones se construyen sobre df_f (ya filtrado por Sexo, Rama,
        # Cohorte, Situación, Nota). Si el usuario tenía seleccionadas
        # titulaciones que ya no están en df_f (por cambio de filtros previos),
        # se limpian automáticamente de session_state ANTES de instanciar el
        # widget, para evitar warnings de Streamlit y chips huérfanos.
        with col_b:
            if 'titulacion' in df_f.columns:
                # Opciones = solo titulaciones presentes en df_f (cascada real)
                titulaciones_disp = sorted(df_f['titulacion'].dropna().unique().tolist())
                # Limpieza automática de selecciones incompatibles
                _sel_previa = st.session_state.get("filtro_titulacion_p01", [])
                _sel_valida = [t for t in _sel_previa if t in titulaciones_disp]
                if _sel_valida != _sel_previa:
                    st.session_state["filtro_titulacion_p01"] = _sel_valida
                titul_sel = st.multiselect(
                    "Titulación",
                    options=titulaciones_disp,
                    placeholder="Todas",
                    key="filtro_titulacion_p01",
                    help="Filtra por uno o varios grados concretos"
                )
                if titul_sel:
                    df_f = df_f[df_f['titulacion'].isin(titul_sel)]

        # --- 8. Vía de acceso (CASCADA) ---
        # Cascada: solo se muestran vías presentes en df_f (ya filtrado por
        # Sexo, Rama, Cohorte, Situación, Nota, Riesgo, Titulación).
        with col_c:
            if 'via_acceso' in df_f.columns:
                # Vías presentes en df_f (cascada real)
                vias_disp = sorted(df_f['via_acceso'].dropna().unique().tolist())
                # Limpieza automática de selecciones incompatibles
                _sel_previa = st.session_state.get("filtro_via_p01", [])
                _sel_valida = [v for v in _sel_previa if v in vias_disp]
                if _sel_valida != _sel_previa:
                    st.session_state["filtro_via_p01"] = _sel_valida
                via_sel = st.multiselect(
                    "Vía de acceso",
                    options=vias_disp,
                    placeholder="Todas",
                    key="filtro_via_p01",
                    help="Filtra por vía de acceso a la universidad"
                )
                if via_sel:
                    df_f = df_f[df_f['via_acceso'].isin(via_sel)]

        col_d, col_e, col_f = st.columns(3)

        # --- 9. Universidad de origen (CASCADA) ---
        # Cascada: solo se muestran universidades presentes en df_f (ya filtrado
        # por Sexo, Rama, Cohorte, Situación, Nota, Titulación). Se limpian
        # automáticamente selecciones incompatibles de session_state.
        with col_d:
            if 'universidad_origen' in df_f.columns:
                # Códigos presentes en df_f (cascada real)
                codigos_uni = sorted(df_f['universidad_origen'].dropna().unique().tolist())
                opciones_uni = [
                    UNIVERSIDAD_ORIGEN_INV.get(int(c), f"Código {int(c)}")
                    for c in codigos_uni
                ]
                # Limpieza automática de selecciones incompatibles (sobre etiquetas,
                # que es lo que guarda session_state)
                _sel_previa = st.session_state.get("filtro_universidad_p01", [])
                _sel_valida = [u for u in _sel_previa if u in opciones_uni]
                if _sel_valida != _sel_previa:
                    st.session_state["filtro_universidad_p01"] = _sel_valida
                uni_sel = st.multiselect(
                    "Universidad de origen",
                    options=opciones_uni,
                    placeholder="Todas",
                    key="filtro_universidad_p01",
                    help="Universidad de la que procede el alumno"
                )
                if uni_sel:
                    # Traducir etiquetas seleccionadas a códigos
                    codigos_sel = []
                    for c in codigos_uni:
                        etiqueta = UNIVERSIDAD_ORIGEN_INV.get(int(c), f"Código {int(c)}")
                        if etiqueta in uni_sel:
                            codigos_sel.append(int(c))
                    if codigos_sel:
                        df_f = df_f[df_f['universidad_origen'].isin(codigos_sel)]

        # --- 10. Cupo (CASCADA, con opción "Sin dato" para NaN) ---
        # Cascada: solo se muestran cupos presentes en df_f (ya filtrado por
        # Sexo, Rama, Cohorte, Situación, Nota, Riesgo, Titulación, Vía,
        # Universidad). "Sin dato" solo aparece si df_f contiene NaN en cupo.
        with col_e:
            if 'cupo' in df_f.columns:
                # Valores no nulos presentes en df_f (cascada real)
                valores_cupo = sorted(df_f['cupo'].dropna().unique().tolist())
                hay_nan = df_f['cupo'].isna().any()
                opciones_cupo = valores_cupo + (["Sin dato"] if hay_nan else [])
                # Limpieza automática de selecciones incompatibles
                _sel_previa = st.session_state.get("filtro_cupo_p01", [])
                _sel_valida = [c for c in _sel_previa if c in opciones_cupo]
                if _sel_valida != _sel_previa:
                    st.session_state["filtro_cupo_p01"] = _sel_valida
                cupo_sel = st.multiselect(
                    "Cupo",
                    options=opciones_cupo,
                    placeholder="Todos",
                    key="filtro_cupo_p01",
                    help="Cupo de admisión (General, discapacidad, deportista...)"
                )
                if cupo_sel:
                    if "Sin dato" in cupo_sel:
                        # Incluir NaN + los valores seleccionados
                        valores_no_nan = [v for v in cupo_sel if v != "Sin dato"]
                        mask = df_f['cupo'].isna()
                        if valores_no_nan:
                            mask = mask | df_f['cupo'].isin(valores_no_nan)
                        df_f = df_f[mask]
                    else:
                        df_f = df_f[df_f['cupo'].isin(cupo_sel)]

        # --- 11. Años de beca ---
        with col_f:
            if 'n_anios_beca' in df_f.columns and df_f['n_anios_beca'].notna().any():
                beca_min = int(df['n_anios_beca'].min())
                beca_max = int(df['n_anios_beca'].max())
                if beca_min < beca_max:
                    rango_beca = st.slider(
                        "Años con beca",
                        min_value=beca_min,
                        max_value=beca_max,
                        value=(beca_min, beca_max),
                        step=1,
                        key=f"filtro_beca_p01_v{_v_filtros}",
                        help="Número de años con beca durante la carrera"
                    )
                    df_f = df_f[
                        (df_f['n_anios_beca'] >= rango_beca[0]) &
                        (df_f['n_anios_beca'] <= rango_beca[1])
                    ]

    # -------------------------------------------------------------------
    # BADGE DE MUESTRA (cuántos filtros están activos y cuántos alumnos)
    # -------------------------------------------------------------------
    # Contar filtros activos (cualquier clave con valor no neutro en session_state)
    # NOTA: los sliders usan key versionada (f"filtro_xxx_p01_v{_v_filtros}")
    # para permitir reset real desde el botón Borrar. Aquí leemos la versión
    # actual para saber qué clave buscar en session_state.
    n_activos = 0
    # Sexo
    if st.session_state.get("filtro_sexo_p01", "Todos") != "Todos":
        n_activos += 1
    # Rama
    if st.session_state.get("filtro_rama_p01", []):
        n_activos += 1
    # Cohorte — activo solo si el rango no cubre todos los años
    cohorte_val = st.session_state.get(f"filtro_anios_p01_v{_v_filtros}")
    if cohorte_val and 'curso_aca_ini' in df.columns:
        a_total_min = int(df.loc[df['curso_aca_ini'] >= 2010, 'curso_aca_ini'].min())
        a_total_max = int(df.loc[df['curso_aca_ini'] >= 2010, 'curso_aca_ini'].max())
        if cohorte_val != (a_total_min, a_total_max):
            n_activos += 1
    # Situación laboral
    if st.session_state.get("filtro_sit_lab_p01", "Todas") != "Todas":
        n_activos += 1
    # Nota acceso — activo si no cubre el rango total
    nota_val = st.session_state.get(f"filtro_nota_acc_p01_v{_v_filtros}")
    if nota_val and 'nota_acceso' in df.columns:
        nota_total_min = round(float(df['nota_acceso'].min()), 1)
        nota_total_max = round(float(df['nota_acceso'].max()), 1)
        if nota_val != (nota_total_min, nota_total_max):
            n_activos += 1
    # Avanzados: listas → activos si no están vacías
    for k in ("filtro_riesgo_p01", "filtro_titulacion_p01", "filtro_via_p01",
              "filtro_universidad_p01", "filtro_cupo_p01"):
        if st.session_state.get(k, []):
            n_activos += 1
    # Años beca — activo si no cubre el rango total
    beca_val = st.session_state.get(f"filtro_beca_p01_v{_v_filtros}")
    if beca_val and 'n_anios_beca' in df.columns:
        beca_total_min = int(df['n_anios_beca'].min())
        beca_total_max = int(df['n_anios_beca'].max())
        if beca_val != (beca_total_min, beca_total_max):
            n_activos += 1

    texto_activos = (
        "Sin filtros activos" if n_activos == 0
        else f"{n_activos} filtro{'s' if n_activos != 1 else ''} activo{'s' if n_activos != 1 else ''}"
    )

    # Color del badge según si hay filtros o no
    color_badge   = COLORES['primario'] if n_activos > 0 else COLORES['texto_suave']
    fondo_badge   = COLORES['fondo_pagina'] if n_activos > 0 else COLORES['fondo']

    st.markdown(f"""
    <div style="display:flex; justify-content:flex-end; margin-top:0.5rem;">
        <span style="background:{fondo_badge};
            color:{color_badge};
            padding:0.35rem 0.8rem;
            border-radius:6px;
            font-size:0.8rem;
            font-weight:500;">
            📋 Mostrando <strong>{len(df_f):,}</strong> de <strong>{len(df):,}</strong> · {texto_activos}
        </span>
    </div>
    """.replace(",", "."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    return df_f


# =============================================================================
# BLOQUE 1: KPIs rápidos
# =============================================================================

def _generar_sparkline_svg(
    valores: list,
    color: str,
    width: int = 200,
    height: int = 40,
) -> str:
    """
    Genera un sparkline SVG simple a partir de una lista de valores.

    Devuelve HTML <svg>...</svg> listo para insertar en markdown.
    Dibuja una polyline + un área suave bajo la línea con opacidad.

    - valores: lista de números (pueden ser NaN → se filtran)
    - color  : hex del color principal (ej. COLORES['primario'])
    - width  : ancho en px
    - height : alto en px
    """
    # Limpiar NaN o valores no numéricos
    serie = [v for v in valores if v is not None and not _pd.isna(v)]
    if len(serie) < 2:
        # No hay datos suficientes → devolver un SVG vacío con línea plana
        return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
                f'preserveAspectRatio="none"><line x1="0" y1="{height//2}" '
                f'x2="{width}" y2="{height//2}" stroke="{color}" '
                f'stroke-width="1" opacity="0.3"/></svg>')

    # Escalar valores al rango del SVG (invertido: más alto = menor Y)
    v_min, v_max = min(serie), max(serie)
    rango = v_max - v_min if v_max > v_min else 1  # evitar división por cero
    n = len(serie)
    margen = 4  # margen arriba/abajo
    alto_util = height - 2 * margen

    puntos = []
    for i, v in enumerate(serie):
        x = i / (n - 1) * width
        # Normalizar e invertir (eje Y del SVG crece hacia abajo)
        y = margen + alto_util - ((v - v_min) / rango) * alto_util
        puntos.append(f"{x:.1f},{y:.1f}")

    # Puntos para cerrar el área (añadir esquinas inferiores)
    puntos_area = puntos + [f"{width:.1f},{height}", f"0,{height}"]

    polyline_linea = " ".join(puntos)
    polygon_area   = " ".join(puntos_area)

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" style="display:block;">'
        # Área bajo la línea (opacidad baja)
        f'<polyline points="{polygon_area}" fill="{color}" opacity="0.15" stroke="none"/>'
        # Línea principal
        f'<polyline points="{polyline_linea}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def _generar_sparkline_multi_svg(
    series: dict,
    width: int = 200,
    height: int = 40,
) -> str:
    """
    Genera un sparkline SVG con MÚLTIPLES líneas superpuestas.

    A diferencia de _generar_sparkline_svg (que dibuja 1 serie con área),
    esta función dibuja N polilíneas sin área, cada una con su color.
    Todas comparten el mismo rango Y (normalización conjunta), para que
    la comparación visual sea honesta.

    Bug FASE C #14: sparkline de KPI Alumnos antes tenía 1 sola línea
    (N total por cohorte). Ahora muestra desglose Mujer/Hombre/Total.

    Parámetros
    ----------
    series : dict[str, tuple[list, str]]
        Diccionario con estructura:
          {"Etiqueta": (valores, color_hex), ...}
        Ejemplo:
          {
            "Total":  ([100, 150, 200], COLORES_SEXO["Total"]),
            "Hombre": ([45, 70, 95],    COLORES_SEXO["Hombre"]),
            "Mujer":  ([55, 80, 105],   COLORES_SEXO["Mujer"]),
          }
        Las etiquetas solo se usan internamente; no se dibujan en el SVG
        (eso va en la leyenda externa, en la tarjeta KPI).
    width : int
        Ancho en píxeles del SVG.
    height : int
        Alto en píxeles del SVG.

    Returns
    -------
    str
        HTML <svg>...</svg> listo para insertar en markdown.
        Si no hay datos suficientes, devuelve un SVG con línea plana.
    """
    # --- Validar y limpiar series ---
    # Filtramos NaN de cada serie y descartamos series vacías
    series_limpias = {}
    for etiqueta, (valores, color) in series.items():
        serie = [v for v in valores if v is not None and not _pd.isna(v)]
        if len(serie) >= 2:
            series_limpias[etiqueta] = (serie, color)

    # Si ninguna serie tiene suficientes puntos, línea plana de fallback
    if not series_limpias:
        return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
                f'preserveAspectRatio="none"><line x1="0" y1="{height//2}" '
                f'x2="{width}" y2="{height//2}" stroke="{COLORES["borde"]}" '
                f'stroke-width="1" opacity="0.3"/></svg>')

    # --- Escalado conjunto: todas las series en el mismo rango Y ---
    # Esto es esencial para comparar visualmente (si una serie se
    # normaliza por separado, las alturas no se pueden comparar entre ellas)
    todos_valores = [v for (serie, _c) in series_limpias.values() for v in serie]
    v_min, v_max = min(todos_valores), max(todos_valores)
    rango = v_max - v_min if v_max > v_min else 1
    margen = 4
    alto_util = height - 2 * margen

    # --- Construir polilíneas ---
    polilineas_svg = []
    for etiqueta, (serie, color) in series_limpias.items():
        n = len(serie)
        puntos = []
        for i, v in enumerate(serie):
            x = i / (n - 1) * width
            # Normalizar e invertir (eje Y del SVG crece hacia abajo)
            y = margen + alto_util - ((v - v_min) / rango) * alto_util
            puntos.append(f"{x:.1f},{y:.1f}")
        polilineas_svg.append(
            f'<polyline points="{" ".join(puntos)}" fill="none" '
            f'stroke="{color}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    # --- Construir SVG completo ---
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" style="display:block;">'
        + "".join(polilineas_svg)
        + '</svg>'
    )


def _tarjeta_kpi_html(
    icono: str,
    label: str,
    valor: str,
    color_barra: str,
    sparkline_html: str = "",
    leyenda_html: str = "",
    delta_temporal: str = "",
    delta_ref: str = "",
    tooltip: str = "",
) -> str:
    """
    Genera HTML de una tarjeta KPI grande al estilo dashboard institucional.

    REFACTOR p03 (Chat p03, 27/04/2026): esta función NO se centraliza en
    utils/ui_helpers.py por ahora. Razones:
      1. Solo la usa p01_institucional (vista institucional con sparkline).
      2. Es bastante larga (~85 líneas) y muy específica del dashboard.
      3. Las otras páginas usan _tarjeta_kpi (compacta, en ui_helpers).
    Si en el futuro otra página la necesita, se mueve entonces a ui_helpers
    para que sea reutilizable. Coherente con _tarjeta_kpi (border-left 4px).

    Estructura:
      - Barra vertical de color a la izquierda (4px)
      - Header: icono + label arriba
      - Valor grande en el centro
      - Sparkline SVG (si se pasa)
      - Leyenda del sparkline (si se pasa) — solo para sparklines multi-línea
      - 2 deltas (temporal + referencia) en la parte inferior

    Los deltas ya deben venir como HTML con flecha + color aplicado desde
    la función que llama (_formato_delta_html).

    Bug FASE C #14: se añadió leyenda_html para poder distinguir las
    líneas del sparkline multi-línea del KPI Alumnos (Mujer/Hombre/Total).
    """
    # Sección de deltas: solo aparece si hay al menos uno
    deltas_html = ""
    if delta_temporal or delta_ref:
        lineas = []
        if delta_temporal:
            lineas.append(delta_temporal)
        if delta_ref:
            lineas.append(delta_ref)
        deltas_html = (
            f'<div style="border-top:1px solid {COLORES["borde"]}; '
            f'padding-top:0.4rem; margin-top:0.4rem; '
            f'display:flex; flex-direction:column; gap:0.15rem;">'
            + "".join(lineas)
            + '</div>'
        )

    # Sparkline: solo si se pasa
    sparkline_bloque = (
        f'<div style="margin:0.3rem 0 0.3rem 0;">{sparkline_html}</div>'
        if sparkline_html else ""
    )

    # Leyenda del sparkline: solo si se pasa (tarjetas con sparkline multi-línea)
    leyenda_bloque = (
        f'<div style="margin:0 0 0.3rem 0;">{leyenda_html}</div>'
        if leyenda_html else ""
    )

    # IMPORTANTE: la plantilla de la tarjeta se construye SIN saltos de línea
    # ni indentación entre bloques HTML dinámicos ({sparkline_bloque},
    # {leyenda_bloque}, {deltas_html}). Streamlit.markdown pasa el string
    # por un renderizador Markdown antes de tratar el HTML: cualquier línea
    # en blanco entre elementos se interpreta como fin de párrafo, corta el
    # HTML y escapa el resto como texto (se ve "<div style=..." literal).
    # Bug reportado por María José: los deltas y leyendas se mostraban como
    # código fuente. Arreglo: usar una sola línea para los bloques opcionales.
    return (
        f'<div style="position:relative;'
        f'background:{COLORES["blanco"]};'
        f'border:1px solid {COLORES["borde"]};'
        f'border-left:4px solid {color_barra};'
        f'border-radius:10px;'
        f'padding:0.9rem 1.1rem 0.8rem 1.1rem;'
        f'height:100%;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.04);" title="{tooltip}">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:0.25rem;">'
        f'<span style="font-size:0.82rem;color:{COLORES["texto_suave"]};'
        f'font-weight:500;">{label}</span>'
        f'<span style="font-size:1.1rem;">{icono}</span>'
        f'</div>'
        f'<div style="font-size:1.9rem;font-weight:700;'
        f'color:{COLORES["texto"]};line-height:1.1;margin-bottom:0.2rem;">'
        f'{valor}'
        f'</div>'
        f'{sparkline_bloque}{leyenda_bloque}{deltas_html}'
        f'</div>'
    )


def _formato_delta_html(
    delta_valor: float,
    etiqueta: str,
    subir_es_bueno: bool,
    sufijo_unidad: str = "pp",
) -> str:
    """
    Devuelve HTML de una línea de delta con flecha + color coherente.

    REGLA (confirmada con mjmr — FASE C):
      - Si algo MEJORA  → flecha ▲ verde (exito)
      - Si algo EMPEORA → flecha ▼ rojo  (abandono)
      - Si no cambia     → flecha · gris (texto_muy_suave)

    La dirección de la flecha NO depende del signo del número, sino de si
    el cambio representa una mejora o empeoramiento según el KPI.

    Parámetros:
      - delta_valor:  número (positivo o negativo)
      - etiqueta:     texto descriptivo ("vs cohorte anterior", "vs media UJI")
      - subir_es_bueno: True si que el valor suba es algo bueno (ej. AUC),
                        False si subir es malo (ej. tasa abandono)
      - sufijo_unidad: "pp" (puntos porcentuales) o "%" o lo que sea
    """
    # Tolerancia para considerar "sin cambio"
    if abs(delta_valor) < 0.05:
        flecha      = "·"
        color_delta = COLORES['texto_muy_suave']
    else:
        sube = delta_valor > 0
        # "Mejora" = sube y subir es bueno · O · baja y subir es malo
        mejora = (sube and subir_es_bueno) or (not sube and not subir_es_bueno)
        if mejora:
            flecha      = "▲"
            color_delta = COLORES['exito']
        else:
            flecha      = "▼"
            color_delta = COLORES['abandono']

    # Signo explícito (+ o -) y coma decimal española
    signo = "+" if delta_valor > 0 else ("-" if delta_valor < 0 else "")
    valor_str = f"{abs(delta_valor):.1f}".replace(".", ",")

    # FASE F Bloque 2 — Tooltip "pp" (puntos porcentuales)
    # Cuando el sufijo es "pp", lo envolvemos en un <span title="..."> con borde
    # inferior punteado para señalar visualmente que hay información adicional
    # al pasar el ratón. Para otros sufijos (ej. "%") no se añade tooltip.
    if sufijo_unidad == "pp":
        sufijo_html = (
            f'<span title="pp = puntos porcentuales. '
            f'Diferencia absoluta entre dos tasas expresadas en porcentaje." '
            f'style="cursor:help; border-bottom:1px dotted currentColor;">'
            f'{sufijo_unidad}'
            f'</span>'
        )
    else:
        sufijo_html = sufijo_unidad

    return (
        f'<div style="display:flex; justify-content:space-between; '
        f'align-items:center; font-size:0.75rem;">'
        f'<span style="color:{COLORES["texto_muy_suave"]};">{etiqueta}</span>'
        f'<span style="color:{color_delta}; font-weight:600;">'
        f'{flecha} {signo}{valor_str} {sufijo_html}'
        f'</span>'
        f'</div>'
    )


# =============================================================================
# GUARDIA ANTI-DF-VACÍO — Helper común para todos los _bloque_*
# =============================================================================
# FASE F B3: se detectó que varios bloques gráficos (_bloque_evolucion_temporal,
# _bloque_abandono_por_rama, etc.) petaban con TypeError cuando el usuario
# aplicaba filtros tan restrictivos que df_filtrado quedaba con 0 filas.
#
# Ejemplo del error original:
#     File ..., line 1649, in _bloque_evolucion_temporal
#         anio_max = int(evolucion['anio_cohorte'].max())
#     TypeError: int() argument must be a string, a bytes-like object or a
#     real number, not 'NAType'
#
# Causa: .max() / .min() sobre una Serie vacía devuelve pd.NA (NAType), y
# int(pd.NA) explota. Lo mismo pasa con conteos, groupbys, etc.
#
# Solución: cada bloque gráfico llama a _guardia_df_vacio() al principio.
# Si devuelve True, el bloque muestra un aviso visual amigable y retorna
# sin intentar calcular nada. Así la app degrada con elegancia cuando el
# usuario provoca una muestra vacía (filtros muy restrictivos).

# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _guardia_df_vacio ELIMINADA.
# Sustituida por _guardia_df_vacio de utils/ui_helpers.py.
# =============================================================================


# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): bloques de p01 RENOMBRADOS con sufijo
# "_global" para diferenciarlos de los bloques de p02 que tenían el mismo
# nombre pero firma y contenido distintos:
#   - _bloque_kpis        → _bloque_kpis_global       (p01: df global UJI)
#                           _bloque_kpis_titulacion   (p02: df de UNA titulación)
#   - _bloque_evolucion_temporal → _bloque_evolucion_temporal_global
#                                  _bloque_evolucion_temporal_titulacion
#   - _bloque_distribucion_riesgo → _bloque_distribucion_riesgo_global
#                                   _bloque_distribucion_riesgo_titulacion
# NO se centralizan en ui_helpers porque la lógica es radicalmente distinta
# (cobertura global vs cobertura por una titulación, KPIs distintos).
# =============================================================================


def _bloque_kpis_global(df: pd.DataFrame, tasa_ref: float = 29.25,
                 riesgo_ref: float = 0.0):
    """
    Fila de 4 tarjetas KPI grandes estilo dashboard.

    Nota FASE F (iter 8) sobre defaults:
    - `tasa_ref = 29.25` es el valor histórico del conjunto de test
      (F1 2025-11). Se usa SOLO si se llama a esta función sin pasar
      `tasa_ref` explícitamente. En show() siempre se pasa el valor
      real calculado en tiempo de ejecución. Se mantiene como default
      documentado por seguridad, no como fuente de verdad.

    Métricas:
      1. 👥 Alumnos          — sin deltas (valor absoluto) + sparkline multi-línea
                                (Mujer / Hombre / Total) por cohorte
      2. 📉 Tasa abandono    — 2 deltas (vs cohorte anterior + vs UJI) + sparkline
      3. 🔴 Riesgo alto (%)  — 2 deltas + sparkline
      4. 🎓 Titulaciones     — sin deltas (valor absoluto) · sin sparkline

    Parámetros
    ----------
    df : DataFrame con los datos YA filtrados (lo que el usuario ha seleccionado).
    tasa_ref : float
        Tasa de abandono (%) del test completo SIN filtros. Se usa para el
        delta "vs UJI" del KPI Tasa abandono.
    riesgo_ref : float
        % de alumnos con nivel_riesgo='Alto' en el test completo SIN filtros.
        Se usa para el delta "vs UJI" del KPI Riesgo alto.
        Bug FASE C #12: antes este valor no existía y el delta estaba
        hardcoded a 0.0. Ahora se recibe real desde show().

    Debajo: expander "💰 Coste estimado del abandono" con number_input editable.

    REGLA DE FLECHAS (acordada FASE C):
      - Mejora → ▲ verde     · Empeora → ▼ rojo     · Sin cambio → · gris
    """

    # --------------------------------------------------------------
    # Cabecera: título grande + toggle-switch a la derecha (Opción 4)
    # --------------------------------------------------------------
    # FASE D+E iter 7: el expander nativo de Streamlit se parecía demasiado
    # a un filtro avanzado. Ahora usamos un encabezado más institucional:
    # título <h4> a la izquierda y un st.toggle "Visibles" a la derecha,
    # con borde inferior gris. Streamlit 1.31+ soporta st.toggle.
    if "_p01_kpis_visible" not in st.session_state:
        st.session_state["_p01_kpis_visible"] = True

    _col_titulo_k, _col_toggle_k = st.columns([4, 1])
    with _col_titulo_k:
        st.markdown(f"""
        <h4 style="color:{COLORES['texto']}; margin:0; padding:6px 0;
                   border-bottom:2px solid {COLORES['borde']};">
            📌 Indicadores clave
        </h4>
        """, unsafe_allow_html=True)
    with _col_toggle_k:
        kpis_visibles = st.toggle(
            "Visibles",
            value=st.session_state["_p01_kpis_visible"],
            key="_toggle_kpis_p01",
            help="Desactiva para ocultar los indicadores y ver mejor los gráficos",
        )
        st.session_state["_p01_kpis_visible"] = kpis_visibles

    # Solo dibujamos los KPIs si el toggle está activado
    if kpis_visibles:

        # FASE F B3-guardia: si el df está vacío (filtros muy restrictivos),
        # no intentamos calcular ni sparklines ni tarjetas — solo mostramos
        # un aviso amigable y salimos.
        if _guardia_df_vacio(df, "📌 Indicadores clave"):
            return

        # --------------------------------------------------------------
        # Métricas agregadas sobre el df filtrado
        # --------------------------------------------------------------
        n_total         = len(df)
        n_abandono      = df['abandono'].sum()              if 'abandono' in df.columns else 0
        tasa_abandono   = (n_abandono / n_total * 100)      if n_total > 0 else 0
        n_riesgo_alto   = (df['nivel_riesgo'] == 'Alto').sum() if 'nivel_riesgo' in df.columns else 0
        pct_riesgo_alto = (n_riesgo_alto / n_total * 100)   if n_total > 0 else 0
        n_titulaciones  = df['titulacion'].nunique()        if 'titulacion' in df.columns else 0

        # --------------------------------------------------------------
        # Tasa de riesgo alto de referencia (sobre todo el df SIN filtros)
        # — se usa para el delta "vs media UJI" del KPI riesgo alto
        # --------------------------------------------------------------
        # NOTA: tasa_ref ya viene como % calculado sobre df completo sin filtros.
        # Para riesgo alto no tenemos el df sin filtros aquí, así que el delta
        # vs UJI se calcula sobre prob_abandono medio. Lo calculamos por simplicidad:
        # si no hay columna nivel_riesgo en df completo, usamos el propio df.
        # (Para v1 dejamos esta aproximación y en FASE F la afinamos.)

        # --------------------------------------------------------------
        # Preparar sparklines por cohorte (si hay columna curso_aca_ini)
        # --------------------------------------------------------------
        # Bug FASE C #14: el sparkline de Alumnos antes mostraba 1 sola línea
        # (N total por cohorte). Ahora muestra 3 líneas: Mujer / Hombre / Total.
        # Si sexo_meta no está disponible, cae al comportamiento viejo (1 línea).
        sparkline_alumnos = ""
        sparkline_tasa    = ""
        sparkline_riesgo  = ""
        leyenda_alumnos   = ""    # leyenda HTML de colores del sparkline multi-línea
        delta_tasa_tempo  = ""
        delta_riesgo_tempo = ""

        if 'curso_aca_ini' in df.columns and df['curso_aca_ini'].notna().any():
            # Agrupar por cohorte para construir las series temporales base
            # (tasa abandono, riesgo alto) — usadas por los otros 2 sparklines.
            df_valid = df[df['curso_aca_ini'] >= 2010].copy()
            if len(df_valid) > 0:
                por_cohorte = df_valid.groupby('curso_aca_ini').agg(
                    n=('abandono', 'count'),
                    abandonos=('abandono', 'sum'),
                    riesgo_altos=('nivel_riesgo', lambda s: (s == 'Alto').sum()),
                ).reset_index().sort_values('curso_aca_ini')
                por_cohorte['tasa_pct']  = por_cohorte['abandonos'] / por_cohorte['n'] * 100
                por_cohorte['riesgo_pct'] = por_cohorte['riesgo_altos'] / por_cohorte['n'] * 100

                # --------------------------------------------------------------
                # Sparkline Alumnos (MULTI-LÍNEA) — Mujer / Hombre / Total
                # --------------------------------------------------------------
                # Elegimos la columna de sexo legible:
                #   - sexo_meta si existe (texto "Mujer"/"Hombre" del meta_test)
                #   - sexo      como fallback (puede ser código numérico 0/1)
                col_sexo_spark = None
                if 'sexo_meta' in df_valid.columns and df_valid['sexo_meta'].notna().any():
                    col_sexo_spark = 'sexo_meta'
                elif 'sexo' in df_valid.columns and df_valid['sexo'].notna().any():
                    col_sexo_spark = 'sexo'

                if col_sexo_spark is not None:
                    # Si la columna tiene códigos numéricos, traducir a texto
                    # usando SEXO_INV (0→Mujer, 1→Hombre). Si ya es texto
                    # ("Mujer"/"Hombre"), .map devuelve NaN y .fillna lo recupera.
                    serie_sexo = df_valid[col_sexo_spark]
                    if _pd.api.types.is_numeric_dtype(serie_sexo):
                        df_valid['_sexo_texto'] = serie_sexo.map(SEXO_INV).fillna(serie_sexo.astype(str))
                    else:
                        df_valid['_sexo_texto'] = serie_sexo.astype(str)

                    # Agrupar por (cohorte, sexo) y pivotar: columnas = sexo
                    por_cohorte_sexo = (
                        df_valid
                        .groupby(['curso_aca_ini', '_sexo_texto'])
                        .size()
                        .unstack(fill_value=0)
                        .reset_index()
                        .sort_values('curso_aca_ini')
                    )

                    # Construir las 3 series. Si alguna no existe, se omite
                    # (la función _generar_sparkline_multi_svg lo maneja).
                    series_sexo = {}
                    if 'Mujer' in por_cohorte_sexo.columns:
                        series_sexo['Mujer'] = (
                            por_cohorte_sexo['Mujer'].tolist(),
                            _COLOR_SPARKLINE_MUJER,
                        )
                    if 'Hombre' in por_cohorte_sexo.columns:
                        series_sexo['Hombre'] = (
                            por_cohorte_sexo['Hombre'].tolist(),
                            _COLOR_SPARKLINE_HOMBRE,
                        )
                    # Total = N por cohorte (ya lo tenemos en por_cohorte['n'])
                    series_sexo['Total'] = (
                        por_cohorte['n'].tolist(),
                        _COLOR_SPARKLINE_TOTAL,
                    )

                    sparkline_alumnos = _generar_sparkline_multi_svg(series_sexo)

                    # Construir leyenda HTML — una etiqueta por serie dibujada.
                    # Se muestra debajo del sparkline en la tarjeta KPI.
                    items_leyenda = []
                    for etiqueta, (_serie, color) in series_sexo.items():
                        items_leyenda.append(
                            f'<span style="display:inline-flex; align-items:center; '
                            f'gap:4px; font-size:0.7rem; color:{COLORES["texto_suave"]};">'
                            f'<span style="width:10px; height:2px; background:{color}; '
                            f'border-radius:1px; display:inline-block;"></span>'
                            f'{etiqueta}</span>'
                        )
                    leyenda_alumnos = (
                        f'<div style="display:flex; gap:10px; flex-wrap:wrap; '
                        f'margin-top:0.15rem;">'
                        + "".join(items_leyenda)
                        + '</div>'
                    )
                else:
                    # Fallback: no hay columna de sexo → sparkline clásico 1 línea
                    sparkline_alumnos = _generar_sparkline_svg(
                        por_cohorte['n'].tolist(), COLORES['primario']
                    )
                    # Sin leyenda: una línea sola no la necesita

                # --------------------------------------------------------------
                # Sparklines de tasa abandono y riesgo (línea única, sin cambio)
                # --------------------------------------------------------------
                sparkline_tasa = _generar_sparkline_svg(
                    por_cohorte['tasa_pct'].tolist(), COLORES['abandono']
                )
                sparkline_riesgo = _generar_sparkline_svg(
                    por_cohorte['riesgo_pct'].tolist(), COLORES['advertencia']
                )

                # Delta temporal: última cohorte vs penúltima
                if len(por_cohorte) >= 2:
                    ult = int(por_cohorte['curso_aca_ini'].iloc[-1])
                    pen = int(por_cohorte['curso_aca_ini'].iloc[-2])
                    # Delta tasa abandono
                    d_tasa = por_cohorte['tasa_pct'].iloc[-1] - por_cohorte['tasa_pct'].iloc[-2]
                    delta_tasa_tempo = _formato_delta_html(
                        d_tasa,
                        f"{ult} vs {pen}",
                        subir_es_bueno=False,   # abandono sube = empeora
                    )
                    # Delta riesgo alto
                    d_riesgo = por_cohorte['riesgo_pct'].iloc[-1] - por_cohorte['riesgo_pct'].iloc[-2]
                    delta_riesgo_tempo = _formato_delta_html(
                        d_riesgo,
                        f"{ult} vs {pen}",
                        subir_es_bueno=False,   # riesgo alto sube = empeora
                    )

        # --------------------------------------------------------------
        # Delta "vs media UJI" (tasa de referencia sin filtros)
        # --------------------------------------------------------------
        # Ambos deltas comparan la SELECCIÓN ACTUAL (con filtros) contra
        # el TEST COMPLETO (sin filtros). Positivo = peor que la media UJI.
        delta_tasa_uji = _formato_delta_html(
            tasa_abandono - tasa_ref,
            "vs media UJI",
            subir_es_bueno=False,
        )
        # Bug FASE C #12 ARREGLADO: antes era 0.0 hardcoded. Ahora usa
        # riesgo_ref recibido como parámetro, calculado en show() sobre df
        # sin filtros. subir_es_bueno=False porque más riesgo = peor.
        delta_riesgo_uji = _formato_delta_html(
            pct_riesgo_alto - riesgo_ref,
            "vs media UJI",
            subir_es_bueno=False,
        )

        # --------------------------------------------------------------
        # Formatear valores para mostrar
        # --------------------------------------------------------------
        v_alumnos       = f"{n_total:,}".replace(",", ".")
        v_tasa          = f"{tasa_abandono:.1f} %".replace(".", ",")
        v_riesgo        = f"{pct_riesgo_alto:.1f} %".replace(".", ",")
        v_titulaciones  = f"{n_titulaciones}"

        # --------------------------------------------------------------
        # Renderizar 4 tarjetas en columnas iguales
        # --------------------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(
                _tarjeta_kpi_html(
                    icono="👥",
                    label="Alumnos (test)",
                    valor=v_alumnos,
                    color_barra=COLORES['primario'],
                    sparkline_html=sparkline_alumnos,
                    leyenda_html=leyenda_alumnos,
                    tooltip="Número de registros en el conjunto de test con los filtros activos",
                ),
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                _tarjeta_kpi_html(
                    icono="📉",
                    label="Tasa abandono real",
                    valor=v_tasa,
                    color_barra=COLORES['abandono'],
                    sparkline_html=sparkline_tasa,
                    delta_temporal=delta_tasa_tempo,
                    delta_ref=delta_tasa_uji,
                    tooltip=(f"Porcentaje de abandono observado. "
                             f"Sin filtros: {tasa_ref:.1f}%".replace(".", ",")),
                ),
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                _tarjeta_kpi_html(
                    icono="🔴",
                    label="En riesgo alto",
                    valor=v_riesgo,
                    color_barra=COLORES['advertencia'],
                    sparkline_html=sparkline_riesgo,
                    delta_temporal=delta_riesgo_tempo,
                    delta_ref=delta_riesgo_uji,
                    tooltip=(f"Alumnos con probabilidad predicha ≥ "
                             f"{UMBRALES['riesgo_medio']:.0%}"),
                ),
                unsafe_allow_html=True,
            )

        with c4:
            st.markdown(
                _tarjeta_kpi_html(
                    icono="🎓",
                    label="Titulaciones activas",
                    valor=v_titulaciones,
                    color_barra=COLORES['exito'],
                    sparkline_html="",   # sin sparkline — no tiene sentido temporalmente
                    tooltip="Número de titulaciones distintas con los filtros activos",
                ),
                unsafe_allow_html=True,
            )

        # --------------------------------------------------------------
        # Expander: Coste estimado del abandono
        # --------------------------------------------------------------
        _expander_coste_abandono(df)


def _expander_coste_abandono(df: pd.DataFrame):
    """
    Expander opcional con el cálculo del coste económico del abandono.

    FASE F Bloque 4: el valor de 60 créditos medios ya NO está hardcoded.
    Ahora es editable mediante un segundo st.number_input, usando como
    valor por defecto la constante CREDITOS_MEDIOS_ABANDONO_DEFAULT de
    config_app.py (actualmente 60 = 1 año académico EEES).

    Fórmula del cálculo:
        coste = n_abandonos × créditos_medios × precio_por_crédito

    Ambos parámetros (créditos medios y precio) son editables por el
    usuario. Así el cálculo se adapta a los valores exactos de cada
    momento y el tribunal puede ver tanto el supuesto como el resultado.

    Limitación conocida (ver pendiente F7-APP-B4-V2):
        Asumimos que TODOS los alumnos con abandono=1 cursaron la misma
        cantidad media de créditos. En realidad, cada alumno abandona en
        un momento distinto de su trayectoria. Una mejora futura usará
        la media real de `cred_superados` desde df_alumno.parquet.
    """
    # Import local — solo se cargan si el expander se usa.
    # Importamos también CREDITOS_MEDIOS_ABANDONO_DEFAULT (añadido en B4).
    from config_app import (
        PRECIO_CREDITO_UJI_DEFAULT,
        CREDITOS_MEDIOS_ABANDONO_DEFAULT,
    )

    # Guardia anti df vacío (FASE F B3-guardia, 7º bloque — uniformidad).
    # Aunque este bloque no petaría con df vacío (sum() devuelve 0 limpiamente),
    # mostrar "0 abandonos × 60 × 18 = 0 €" no tiene sentido y confunde al
    # usuario. Con la guardia mostramos el mismo aviso amigable que en el
    # resto de bloques y no renderizamos el expander.
    if _guardia_df_vacio(df, "💰 Coste estimado del abandono"):
        return

    with st.expander("💰 Coste estimado del abandono — haz clic para ampliar", expanded=False):

        # Texto introductorio — explica qué se estima y qué se puede ajustar.
        # Mejora FASE F Bloque 4: ahora se mencionan AMBOS parámetros
        # ajustables (antes solo el precio).
        st.markdown(f"""
        <p style="color:{COLORES['texto_suave']}; font-size:0.88rem;
                  margin-bottom:0.8rem;">
            Estimación del impacto económico del abandono en el subgrupo actual.
            Puedes ajustar tanto el precio del crédito como el número de
            créditos medios cursados antes del abandono para ver el impacto
            en tiempo real.
        </p>
        """, unsafe_allow_html=True)

        # Layout: 3 columnas — 2 parámetros editables + resultado grande.
        # FASE F Bloque 4: antes era [1, 2] con 1 sólo input. Ahora [1, 1, 2]
        # para acomodar el segundo input sin que el resultado pierda tamaño.
        col_precio, col_creditos, col_result = st.columns([1, 1, 2])

        with col_precio:
            precio_credito = st.number_input(
                "Precio por crédito (€)",
                min_value=0.0,
                max_value=500.0,
                value=float(PRECIO_CREDITO_UJI_DEFAULT),
                step=0.5,
                key="precio_credito_p01",
                help=(f"Valor por defecto: {PRECIO_CREDITO_UJI_DEFAULT} €/crédito. "
                      f"Grado primera matrícula (orientativo)."),
            )

        with col_creditos:
            # FASE F Bloque 4: NUEVO — créditos medios editable.
            # Default desde config_app. El usuario puede bajarlo si sabe que
            # en su titulación los alumnos abandonan antes del primer año,
            # o subirlo si abandonan más tarde (ej: 120 = 2 años).
            creditos_medios = st.number_input(
                "Créditos medios cursados",
                min_value=0,
                max_value=240,
                value=int(CREDITOS_MEDIOS_ABANDONO_DEFAULT),
                step=5,
                key="creditos_medios_p01",
                help=(f"Valor por defecto: {CREDITOS_MEDIOS_ABANDONO_DEFAULT} créditos "
                      f"(= 1 año académico completo según EEES). Ajusta si conoces "
                      f"la media real de tu colectivo."),
            )

        # Cálculo del coste estimado — fórmula transparente al usuario.
        n_abandonos  = int(df['abandono'].sum()) if 'abandono' in df.columns else 0
        coste_total  = n_abandonos * creditos_medios * precio_credito

        # Formato en euros con separadores de miles españoles (punto, no coma).
        coste_fmt = f"{coste_total:,.0f} €".replace(",", ".")

        with col_result:
            # Tarjeta con el resultado y la fórmula desplegada.
            st.markdown(f"""
            <div style="background:{COLORES['fondo']};
                border:1px solid {COLORES['borde']};
                border-left:4px solid {COLORES['abandono']};
                border-radius:8px;
                padding:0.8rem 1rem;
                margin-top:1.5rem;">
                <div style="font-size:0.82rem; color:{COLORES['texto_suave']};">
                    Coste estimado con los filtros actuales
                </div>
                <div style="font-size:1.6rem; font-weight:700;
                    color:{COLORES['abandono']}; line-height:1.2;">
                    {coste_fmt}
                </div>
                <div style="font-size:0.78rem; color:{COLORES['texto_suave']};
                    margin-top:0.3rem;">
                    Fórmula: <strong>{n_abandonos:,}</strong> abandonos ×
                    <strong>{creditos_medios}</strong> créditos medios ×
                    <strong>{precio_credito:.2f} €</strong>
                </div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)

        # Caption explicativo — ya NO dice "afinaremos en Fase F".
        # Ahora documenta el supuesto y explica que es editable.
        st.caption(
            f"⚠️ Estimación orientativa. La fórmula asume que los "
            f"{n_abandonos:,} alumnos con abandono cursaron de media "
            f"{creditos_medios} créditos antes de dejar los estudios. "
            f"Ambos parámetros son editables arriba para reflejar el "
            f"contexto real del subgrupo analizado."
            .replace(",", ".")
        )


# =============================================================================
# BLOQUE 2: Evolución temporal
# =============================================================================

def _bloque_evolucion_temporal_global(df: pd.DataFrame):
    """Gráfico de línea: tasa de abandono real por año de cohorte."""

    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        📈 Evolución temporal del abandono
    </h4>
    """, unsafe_allow_html=True)

    # FASE F B3-guardia: si df vacío, mostrar aviso y salir (evita TypeError
    # al hacer int(pd.NA) cuando no hay filas para calcular min/max de cohorte).
    if _guardia_df_vacio(df, "📈 Evolución temporal del abandono"):
        return

    if 'curso_aca_ini' not in df.columns or 'abandono' not in df.columns:
        st.info("No hay datos de cohorte disponibles con los filtros actuales.")
        return

    # Agrupamos por año y calculamos tasa de abandono
    evolucion = (
        df.groupby('curso_aca_ini')
        .agg(
            n_total=('abandono', 'count'),
            n_abandono=('abandono', 'sum'),
            prob_media=('prob_abandono', 'mean')
        )
        .reset_index()
    )
    evolucion = evolucion.rename(columns={'curso_aca_ini': 'anio_cohorte'})
    evolucion['tasa_abandono_pct'] = (
        evolucion['n_abandono'] / evolucion['n_total'] * 100
    ).round(1)
    evolucion['prob_media_pct'] = (evolucion['prob_media'] * 100).round(1)

    # Gráfico con dos líneas: abandono real y probabilidad media predicha
    fig = go.Figure()

    # Línea 1: abandono real observado
    fig.add_trace(go.Scatter(
        x=evolucion['anio_cohorte'],
        y=evolucion['tasa_abandono_pct'],
        mode='lines+markers',
        name='Abandono real (%)',
        line=dict(color=COLORES['abandono'], width=2.5),
        marker=dict(size=8),
        hovertemplate=(
            "<b>Cohorte %{x}</b><br>"
            "Abandono real: %{y:,.1f}%<br>"
            "N alumnos: %{customdata}<extra></extra>"
        ),
        customdata=evolucion['n_total']
    ))

    # Línea 2: probabilidad media predicha por el modelo
    fig.add_trace(go.Scatter(
        x=evolucion['anio_cohorte'],
        y=evolucion['prob_media_pct'],
        mode='lines+markers',
        name='Riesgo predicho medio (%)',
        line=dict(color=COLORES['primario'], width=2, dash='dash'),
        marker=dict(size=6),
        hovertemplate=(
            "<b>Cohorte %{x}</b><br>"
            "Riesgo predicho medio: %{y:,.1f}%<extra></extra>"
        )
    ))

    # Anotación de cautela para la cohorte más reciente (truncamiento temporal)
    # Las cohortes recientes tienen tasa baja no porque abandonen menos
    # sino porque aún no han tenido tiempo suficiente para abandonar
    anio_max = int(evolucion['anio_cohorte'].max())
    tasa_max = evolucion[evolucion['anio_cohorte'] == anio_max]['tasa_abandono_pct'].values[0]
    fig.add_annotation(
        x=anio_max, y=tasa_max,
        text="⚠️ Truncamiento<br>temporal",
        showarrow=True, arrowhead=2,
        arrowcolor=COLORES['advertencia'],
        font=dict(size=11, color=COLORES['advertencia']),
        bgcolor=COLORES['blanco'],   # FASE D #23a: era "white" hardcoded
        bordercolor=COLORES['advertencia'],
        borderwidth=1,
        ax=-70, ay=-40,
    )

    fig.update_layout(
        separators=",.",   # Auditoría formato ES (Chat p02)
        xaxis_title="Año de cohorte",
        yaxis_title="Porcentaje (%)",
        yaxis=dict(range=[0, 100]),
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.18,
            xanchor="center", x=0.5,
            font=dict(size=13),
            bgcolor="rgba(255,255,255,0.0)",   # transparente — ok
            borderwidth=0,
        ),
        plot_bgcolor=COLORES['blanco'],    # FASE D #23a: era "white"
        paper_bgcolor=COLORES['blanco'],   # FASE D #23a: era "white"
        margin=dict(l=40, r=20, t=30, b=80),
        height=400,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORES['borde'])
    fig.update_yaxes(showgrid=True, gridcolor=COLORES['borde'])

    st.plotly_chart(fig, width='stretch')   # FASE D #28: use_container_width deprecado

    st.caption(
        "💡 La caída en cohortes recientes (2018-2020) refleja truncamiento temporal: "
        "los alumnos más recientes aún no han tenido tiempo suficiente para abandonar. "
        "La línea azul (riesgo predicho) es más estable porque el modelo no depende del tiempo observado."
    )


# =============================================================================
# BLOQUE 3: Abandono por rama
# =============================================================================

def _bloque_abandono_por_rama(df: pd.DataFrame):
    """Barras horizontales: tasa de abandono real por rama de conocimiento.
    Si hay filtro de rama o titulación activo, desglosa por titulación
    y muestra nombre completo de rama en el título.
    """

    # Detectar filtros activos
    _ramas_sel    = st.session_state.get("filtro_rama_p01", [])
    _tits_sel     = st.session_state.get("filtro_titulacion_p01", [])
    # Desglose por titulación SOLO cuando hay titulaciones específicas elegidas
    # Si solo hay filtro de rama → sigue mostrando una barra por rama
    _hay_filtro_tit = bool(_tits_sel)
    _hay_filtro     = bool(_ramas_sel or _tits_sel)

    # Título dinámico
    if _hay_filtro_tit and _ramas_sel and len(_ramas_sel) == 1:
        _nombre_rama = _ramas_sel[0]
        _titulo_grafico = f"📚 Abandono por titulación — {_nombre_rama}"
    elif _hay_filtro_tit:
        _titulo_grafico = "📚 Abandono por titulación seleccionada"
    elif _hay_filtro and _ramas_sel and len(_ramas_sel) == 1:
        _titulo_grafico = f"📚 Abandono por rama — {_ramas_sel[0]}"
    else:
        _titulo_grafico = "📚 Abandono por rama de conocimiento"

    st.markdown(
        f'<h4 style="color:{COLORES["texto"]};margin-bottom:0.8rem;">'
        f'{_titulo_grafico}</h4>',
        unsafe_allow_html=True
    )

    # FASE F B3-guardia: salir temprano si no hay datos.
    if _guardia_df_vacio(df, "📚 Abandono por rama"):
        return

    col_rama = 'rama_meta' if 'rama_meta' in df.columns else 'rama'
    if col_rama not in df.columns or 'abandono' not in df.columns:
        st.info("No hay datos de rama disponibles con los filtros actuales.")
        return

    # Si hay titulaciones específicas elegidas → desglosar por titulación
    # Solo filtro de rama → sigue mostrando una barra por rama
    if _hay_filtro_tit and 'titulacion' in df.columns:
        _grp_cols = ['titulacion', col_rama]
        por_rama = (
            df.groupby(_grp_cols)
            .agg(
                n_total=('abandono', 'count'),
                n_abandono=('abandono', 'sum'),
                prob_media=('prob_abandono', 'mean')
            )
            .reset_index()
        )
        # Etiqueta del eje Y: titulación en 2 líneas si es larga.
        # REFACTOR p03 (Chat p03, 27/04/2026): _partir_label ELIMINADA.
        # Sustituida por _nombre_titulacion_corto(partir_lineas=True) del
        # helper centralizado en utils/ui_helpers.py.
        por_rama['eje_y'] = por_rama['titulacion'].apply(
            lambda n: _nombre_titulacion_corto(n, partir_lineas=True, max_chars=28)
        )
        # Color por rama
        por_rama['rama'] = por_rama[col_rama]
        _col_color = 'rama'
    else:
        por_rama = (
            df.groupby(col_rama)
            .agg(
                n_total=('abandono', 'count'),
                n_abandono=('abandono', 'sum'),
                prob_media=('prob_abandono', 'mean')
            )
            .reset_index()
        )
        por_rama = por_rama.rename(columns={col_rama: 'rama'})
        por_rama['eje_y'] = por_rama['rama']
        _col_color = 'rama'

    por_rama['tasa_pct'] = (
        por_rama['n_abandono'] / por_rama['n_total'] * 100
    ).round(1)
    por_rama = por_rama.sort_values('tasa_pct', ascending=True)

    # Tasa global UJI desde metricas_modelo.json — lectura centralizada
    # FASE F iter 8: antes había lectura duplicada con fallback 29.25.
    # Ahora usamos _leer_metricas_modelo() (cacheado) y fallback explícito.
    _metricas = _leer_metricas_modelo()
    _tasa_json = _metricas.get("tasa_abandono")
    if _tasa_json is not None:
        tasa_global_pct = float(_tasa_json) * 100
    else:
        # Fallback documentado: valor del test original (F1 2025-11) —
        # se mantiene solo como último recurso si el JSON no está disponible.
        tasa_global_pct = 29.25

    import math

    # Tasa filtrada actual
    tasa_filtrada_pct = (df['abandono'].sum() / len(df) * 100)         if 'abandono' in df.columns and len(df) > 0 else 0.0

    # Tasa rama (solo si hay 1 rama visible)
    tasa_rama_pct = float(por_rama['tasa_pct'].iloc[0]) if len(por_rama) == 1 else None

    # Eje X: máximo real * 1.35, mínimo 40%, redondeado al 10 superior
    max_val = max(por_rama['tasa_pct'].max(), tasa_global_pct, tasa_filtrada_pct)
    eje_max = math.ceil((max_val + 5) / 5) * 5  # +5 puntos, redondeado al múltiplo de 5 superior
    tasa_linea = math.ceil(tasa_global_pct / 10) * 10

    fig = px.bar(
        por_rama,
        x='tasa_pct',
        y='eje_y',
        orientation='h',
        color='rama',
        color_discrete_map=COLORES_RAMAS,
        text='tasa_pct',
        custom_data=['n_total', 'n_abandono'],
        labels={'tasa_pct': 'Tasa abandono (%)', 'eje_y': ''},
    )
    fig.update_traces(
        texttemplate='%{text:,.1f}%',
        textposition='outside',
        showlegend=False,   # FASE D #20: leyenda redundante — rama ya está en eje Y
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Tasa abandono: %{x:,.1f}%<br>"
            "Alumnos totales: %{customdata[0]}<br>"
            "Abandonos: %{customdata[1]}<extra></extra>"
        )
    )

    # Banda sombreada: zona por debajo de la media UJI
    # FASE D #23a: antes era "rgba(56,161,105,0.07)" (verde hex hardcoded).
    # Ahora usamos rgba a partir del verde oficial de la paleta (COLORES['exito']).
    # Valor: #10b981 → rgb(16,185,129) — mantenemos alpha 0.07.
    fig.add_vrect(
        x0=0, x1=tasa_global_pct,
        fillcolor="rgba(16,185,129,0.07)",
        layer="below", line_width=0,
    )

    # FASE D+E iter 7 #3: mjmr pidió quitar las anotaciones "Media UJI" y
    # "Selección" porque solapaban con los valores del final de las barras
    # y esa info ya está en la caption inferior. Mantenemos las líneas
    # verticales (MÁS GRUESAS Y VISIBLES), pero sin texto encima.

    # Línea naranja discontinua — media UJI (referencia fija)
    fig.add_vline(
        x=tasa_global_pct,
        line_dash="dash",
        line_color=COLORES["advertencia"],
        line_width=3,
    )

    # Línea azul sólida — selección actual (solo si hay filtros)
    if tasa_filtrada_pct > 0:
        fig.add_vline(
            x=tasa_filtrada_pct,
            line_dash="solid",
            line_color=COLORES["primario"],
            line_width=3,
        )

    # Línea azul gruesa — tasa de la rama (solo si hay 1 sola rama filtrada)
    if tasa_rama_pct is not None:
        fig.add_vline(
            x=tasa_rama_pct,
            line_dash="solid",
            line_color=COLORES["primario"],
            line_width=3.5,
        )

    fig.update_layout(
        separators=",.",   # Auditoría formato ES (Chat p02)
        coloraxis_showscale=False,
        plot_bgcolor=COLORES['blanco'],    # FASE D #23a
        paper_bgcolor=COLORES['blanco'],   # FASE D #23a
        # FASE D+E iter 7: sin anotaciones arriba/abajo, reducimos margen t/b
        margin=dict(l=160, r=100, t=20, b=40),
        height=max(300, len(por_rama) * 65),
        xaxis=dict(
            range=[0, eje_max],
            showgrid=True,
            gridcolor=COLORES['borde'],
            dtick=10,
            ticksuffix="%",
        ),
        yaxis=dict(showgrid=False),
    )

    st.plotly_chart(fig, width='stretch')   # FASE D #28: deprecación
    # Auditoría formato ES (Chat p02): replace para coma decimal en caption.
    st.caption(
        f"🔵 Selección: {tasa_filtrada_pct:.1f}% · ".replace(".", ",")
        + f"🟠 Media UJI: {tasa_global_pct:.1f}%. ".replace(".", ",")
        + "Zona sombreada = por debajo de la media UJI."
    )


# =============================================================================
# BLOQUE 4: Top titulaciones
# =============================================================================

def _bloque_top_titulaciones(df: pd.DataFrame):
    """Tabla ordenable con las titulaciones y sus métricas de abandono."""

    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        🎓 Abandono por titulación
    </h4>
    """, unsafe_allow_html=True)

    # FASE F B3-guardia: salir temprano si no hay datos.
    if _guardia_df_vacio(df, "🎓 Abandono por titulación"):
        return

    if 'titulacion' not in df.columns or 'abandono' not in df.columns:
        st.info("No hay datos de titulación disponibles con los filtros actuales.")
        return

    # Controles: filtro rama + nº titulaciones (sin "Ordenar por" — se ordena pulsando cabecera)
    col_f, col_n = st.columns([2, 1])

    with col_f:
        col_rama_disp = 'rama_meta' if 'rama_meta' in df.columns else 'rama'
        ramas_tabla   = ["Todas"] + sorted(df[col_rama_disp].dropna().unique().tolist())
        rama_sel_t    = st.selectbox(
            "Filtrar por rama",
            options=ramas_tabla, index=0,
            key="rama_filtro_tabla",
            help="Filtra las titulaciones por rama de conocimiento"
        )

    with col_n:
        n_mostrar = st.slider(
            "Titulaciones",
            min_value=5,
            max_value=min(40, df['titulacion'].nunique()),
            value=10, step=5,
            help="Cuántas titulaciones ver"
        )

    df_t = df.copy()
    if rama_sel_t != "Todas":
        df_t = df_t[df_t[col_rama_disp] == rama_sel_t]

    col_rama_t2 = 'rama_meta' if 'rama_meta' in df_t.columns else 'rama'
    por_titulacion = (
        df_t.groupby(['titulacion', col_rama_t2] if col_rama_t2 in df_t.columns else ['titulacion'])
        .agg(
            Alumnos=('abandono', 'count'),
            Abandonos=('abandono', 'sum'),
            Riesgo_medio=('prob_abandono', 'mean')
        )
        .reset_index()
    )
    por_titulacion['tasa_pct'] = (por_titulacion['Abandonos'] / por_titulacion['Alumnos'] * 100).round(1)
    por_titulacion['riesgo_pct'] = (por_titulacion['Riesgo_medio'] * 100).round(1)
    por_titulacion = por_titulacion.sort_values('tasa_pct', ascending=False).head(n_mostrar)

    # Acortar nombres de titulación
    # REFACTOR p03 (Chat p03, 27/04/2026): regex inline sustituida por
    # _nombre_titulacion_corto de utils/ui_helpers (helper centralizado que
    # maneja correctamente "Grado en Ingeniería en X", "Doble Grado en X",
    # "Doble Grado de X", etc.).
    por_titulacion['titulacion_corta'] = (
        por_titulacion['titulacion'].apply(_nombre_titulacion_corto)
    )

    # REFACTOR p03 (Chat p03, 27/04/2026): _color_tasa ELIMINADA.
    # Sustituida por _clasificar_riesgo de utils/ui_helpers.py.
    # NOTA 1: _color_tasa recibía PORCENTAJE (0-100) y _clasificar_riesgo
    # recibe PROBABILIDAD (0-1) — al usarlo dividimos /100.
    # NOTA 2: la tabla original mostraba círculos 🟢🟡🔴, _clasificar_riesgo
    # devuelve ✅⚠️🔴. Mantenemos los círculos con un mapeo nivel→emoji
    # local para no alterar la estética de esta tabla específica.
    _CIRCULOS_RIESGO = {'Bajo': '🟢', 'Medio': '🟡', 'Alto': '🔴'}

    # Construir tabla HTML propia
    filas_html = ""
    for _, row in por_titulacion.iterrows():
        nivel, color, _, _ = _clasificar_riesgo(row['tasa_pct'] / 100)
        emoji = _CIRCULOS_RIESGO[nivel]
        rama_txt = str(row.get(col_rama_t2, ""))
        tit = str(row['titulacion_corta'])

        # Barra de abandono
        # FASE E #23b: fondo barra #eee → COLORES['borde']
        barra_ab = f"""
        <div style="display:flex; align-items:center; gap:6px;">
            <span>{emoji}</span>
            <div style="flex:1; background:{COLORES['borde']}; border-radius:4px; height:8px;">
                <div style="width:{min(row['tasa_pct'],100)}%; background:{color};
                            border-radius:4px; height:8px;"></div>
            </div>
            <span style="font-size:0.8rem; min-width:38px;">{row['tasa_pct']:.1f}%</span>
        </div>"""

        # Barra de riesgo predicho
        barra_riesgo = f"""
        <div style="display:flex; align-items:center; gap:6px;">
            <div style="flex:1; background:{COLORES['borde']}; border-radius:4px; height:8px;">
                <div style="width:{min(row['riesgo_pct'],100)}%; background:{COLORES['primario']};
                            border-radius:4px; height:8px;"></div>
            </div>
            <span style="font-size:0.8rem; min-width:38px;">{row['riesgo_pct']:.1f}%</span>
        </div>"""

        filas_html += f"""
        <tr style="border-bottom: 1px solid {COLORES['borde']};">
            <td style="padding:8px 10px; font-size:0.82rem; line-height:1.3;
                       min-width:180px; max-width:260px; word-wrap:break-word;
                       white-space:normal;">{tit}</td>
            <td style="padding:8px 10px; font-size:0.82rem; text-align:right;">{int(row['Alumnos'])}</td>
            <td style="padding:8px 10px; font-size:0.82rem; text-align:right;">{int(row['Abandonos'])}</td>
            <td style="padding:8px 10px; min-width:160px;">{barra_ab}</td>
            <td style="padding:8px 10px; min-width:160px;">{barra_riesgo}</td>
        </tr>"""

    # FASE E #23b: todos los colores hardcoded de la tabla sustituidos por COLORES
    # FASE D+E #6: quitada la columna "Rama" — redundante porque el filtro
    # "Filtrar por rama" arriba de la tabla ya da esa información. Libera
    # ~140px de ancho para que "Abandono %" y "Riesgo %" respiren.
    tabla_html = f"""
    <div style="overflow-x:auto; border:1px solid {COLORES['borde']}; border-radius:8px;">
    <table style="width:100%; border-collapse:collapse; background:{COLORES['blanco']};">
        <thead>
            <tr style="background:{COLORES['fondo']}; border-bottom:2px solid {COLORES['borde']};">
                <th style="padding:10px; text-align:left; font-size:0.82rem;
                           color:{COLORES['texto']}; font-weight:600;">Titulación</th>
                <th style="padding:10px; text-align:right; font-size:0.82rem;
                           color:{COLORES['texto']}; font-weight:600;">Alumnos</th>
                <th style="padding:10px; text-align:right; font-size:0.82rem;
                           color:{COLORES['texto']}; font-weight:600;">Abandonos</th>
                <th style="padding:10px; text-align:left; font-size:0.82rem;
                           color:{COLORES['texto']}; font-weight:600;">Abandono (%)</th>
                <th style="padding:10px; text-align:left; font-size:0.82rem;
                           color:{COLORES['texto']}; font-weight:600;">Riesgo predicho (%)</th>
            </tr>
        </thead>
        <tbody>{filas_html}</tbody>
    </table>
    </div>
    """
    st.markdown(tabla_html, unsafe_allow_html=True)
    st.caption("💡 Haz clic en el filtro de rama para ver titulaciones por área de conocimiento.")


# =============================================================================
# BLOQUE 5: Distribución del riesgo predicho
# =============================================================================

def _bloque_barras_riesgo_por_rama(df: pd.DataFrame):
    """
    Barras apiladas 100% por nivel de riesgo, agrupadas por rama.
    Muestra para cada rama qué % de alumnos está en riesgo bajo/medio/alto.

    FASE E: antes formaba parte de _bloque_distribucion_riesgo (que mostraba
    donut + barras lado a lado). Ahora se separa para permitir el layout
    pedido (tabla izquierda | barras arriba + donut abajo a la derecha).

    Bug FASE E #22 ARREGLADO: antes usaba 'rama' (códigos numéricos 1-5)
    que se veían feos en el eje X. Ahora usa 'rama_meta' (nombres legibles)
    con fallback a 'rama' si no existe. Patrón consistente con
    _bloque_abandono_por_rama (línea 1472) y _bloque_top_titulaciones
    (líneas 1636, 1658).
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        📊 Riesgo por rama
    </h4>
    """, unsafe_allow_html=True)

    # FASE F B3-guardia: salir temprano si no hay datos.
    if _guardia_df_vacio(df, "📊 Riesgo por rama"):
        return

    if 'nivel_riesgo' not in df.columns or df['nivel_riesgo'].isna().all():
        st.info("No hay datos de nivel de riesgo disponibles.")
        return

    # FASE E #22: fallback defensivo (misma estrategia que otras funciones)
    # Prefiere columna legible (rama_meta con nombres completos). Si no
    # existe, cae a la numérica (rama con códigos 1-5). Si ninguna, None.
    if 'rama_meta' in df.columns:
        col_rama_hist = 'rama_meta'
    elif 'rama' in df.columns:
        col_rama_hist = 'rama'
    else:
        col_rama_hist = None

    if col_rama_hist is None:
        st.info("No hay datos de rama disponibles.")
        return

    # Calcular % por nivel de riesgo agrupado por rama
    grupos = df.groupby([col_rama_hist, 'nivel_riesgo']).size().reset_index(name='n')
    totales = grupos.groupby(col_rama_hist)['n'].transform('sum')
    grupos['pct'] = grupos['n'] / totales * 100

    # FASE D+E #7: abreviar nombres largos en eje X para que no se solapen.
    # Creamos mapa inverso {nombre_completo → abreviatura} desde RAMAS_NOMBRES
    # (que viene como {abrev → nombre_completo}). Guardamos el nombre completo
    # en columna separada para usarlo en el tooltip (hovertemplate).
    nombre_a_abrev = {v: k for k, v in RAMAS_NOMBRES.items()}
    # Si el valor ya es abreviatura (no existe en el mapa inverso), se queda igual
    grupos['rama_abrev'] = grupos[col_rama_hist].map(nombre_a_abrev).fillna(
        grupos[col_rama_hist]
    )
    # Copiamos el nombre completo para usarlo en el tooltip
    grupos['rama_nombre'] = grupos[col_rama_hist]

    # Etiquetas eje X: nombre completo abreviado en 2 palabras para legibilidad
    # Usamos rama_nombre (nombre completo) directamente — más claro que abreviaturas
    orden_riesgo = ['Bajo', 'Medio', 'Alto']
    fig_hist = go.Figure()
    for nivel in orden_riesgo:
        g = grupos[grupos['nivel_riesgo'] == nivel]
        # Acortar nombres largos para eje X: primeras 2 palabras
        _etiquetas_x = g['rama_nombre'].apply(
            lambda n: '<br>'.join(n.split()[:3]) if len(n.split()) > 2 else n
        )
        fig_hist.add_trace(go.Bar(
            name=nivel,
            x=_etiquetas_x,
            y=g['pct'],
            marker_color=COLORES_RIESGO[nivel.lower()],
            customdata=g['rama_nombre'],
            hovertemplate=(
                f"<b>%{{customdata}}</b><br>"
                f"{nivel}: %{{y:,.1f}}%<extra></extra>"
            ),
            text=g['pct'].apply(lambda v: f"{v:.0f}%" if v >= 5 else ""),
            # Nota: aquí v:.0f no genera punto decimal porque es entero.
            # Plotly aplicará separators=",." para miles si los hubiera.
            textposition="inside",
        ))

    # Sin leyenda de abreviaturas — ahora usamos nombre completo directamente
    leyenda_abrev_str = ""

    fig_hist.update_layout(
        separators=",.",   # Auditoría formato ES (Chat p02)
        barmode="stack",
        yaxis=dict(range=[0, 100], title="% alumnos", ticksuffix="%"),
        # Auditoría layout (Chat p02): etiquetas X en 2 líneas (con <br>) NO
        # giradas + leyenda ARRIBA del gráfico (no abajo) para evitar el
        # solapamiento que se veía cuando la leyenda iba a y=-0.20 y las
        # etiquetas con <br> ocupaban más espacio vertical.
        xaxis=dict(title="", tickangle=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,            # encima del área del gráfico
            x=0.5,
            xanchor="center",
            title_text="",
        ),
        plot_bgcolor=COLORES['blanco'],
        paper_bgcolor=COLORES['blanco'],
        margin=dict(l=10, r=10, t=40, b=80),  # +b para etiquetas en 2 líneas
        height=290,                           # +50 para que entre todo
    )
    fig_hist.update_xaxes(showgrid=False)
    fig_hist.update_yaxes(showgrid=True, gridcolor=COLORES['borde'])

    st.plotly_chart(fig_hist, width='stretch')

    # Leyenda de abreviaturas — pequeña, gris, debajo del gráfico
    st.caption(f"Ramas: {leyenda_abrev_str}")


def _bloque_donut_riesgo(df: pd.DataFrame):
    """
    Gráfico donut: proporción de alumnos por nivel de riesgo (bajo/medio/alto).
    Muestra el total de alumnos en el centro del donut.

    FASE E: antes formaba parte de _bloque_distribucion_riesgo (que mostraba
    donut + barras lado a lado). Ahora se separa para permitir el layout
    pedido (tabla izquierda | barras arriba + donut abajo a la derecha).
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        🔮 Distribución del riesgo
    </h4>
    """, unsafe_allow_html=True)

    # FASE F B3-guardia: salir temprano si no hay datos.
    if _guardia_df_vacio(df, "🔮 Distribución del riesgo"):
        return

    if 'prob_abandono' not in df.columns or df['prob_abandono'].isna().all():
        st.info("No hay probabilidades predichas disponibles.")
        return

    # Gráfico donut: proporción bajo / medio / alto
    conteo_riesgo = df['nivel_riesgo'].value_counts() if 'nivel_riesgo' in df.columns else {}
    orden = ['Bajo', 'Medio', 'Alto']
    valores = [conteo_riesgo.get(nivel, 0) for nivel in orden]
    colores_donut = [COLORES_RIESGO['bajo'], COLORES_RIESGO['medio'], COLORES_RIESGO['alto']]

    fig_donut = go.Figure(go.Pie(
        labels=orden,
        values=valores,
        hole=0.55,
        marker_colors=colores_donut,
        # Auditoría formato ES (Chat p02): textinfo='percent' usa punto.
        # texttemplate explícito con :,.1f y replace forzaría coma decimal,
        # pero Plotly Pie permite text con replace previo. Solución: pasar
        # 'text' precalculado en español y usar textinfo='text'.
        text=[
            f"{v / sum(valores) * 100:.1f}%".replace(".", ",") if sum(valores) > 0 else ""
            for v in valores
        ],
        textinfo='text',
        hovertemplate="<b>%{label}</b><br>%{value} alumnos (%{percent})<extra></extra>",
    ))
    fig_donut.update_layout(
        separators=",.",   # Auditoría formato ES (Chat p02)
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05),
        margin=dict(l=10, r=10, t=10, b=10),
        height=240,
        annotations=[dict(
            # Auditoría formato ES (Chat p02): replace para separador miles ES.
            text=f"<b>{len(df):,}</b><br>alumnos".replace(",", "."),
            x=0.5, y=0.5,
            font_size=13,
            showarrow=False
        )]
    )
    st.plotly_chart(fig_donut, width='stretch')

    st.caption(
        # Auditoría formato ES (Chat p02): :.0% genera enteros, no hay
        # decimal. Pero si en el futuro UMBRALES no fuera redondo añadir
        # replace(".", ",").
        f"Umbrales: bajo < {UMBRALES['riesgo_bajo']:.0%} · "
        f"medio < {UMBRALES['riesgo_medio']:.0%} · "
        f"alto ≥ {UMBRALES['riesgo_medio']:.0%}"
    )


# --- Wrapper de compatibilidad (por si algo externo llama al nombre viejo) ---
# Mantiene la función antigua _bloque_distribucion_riesgo como alias que
# ejecuta las 2 funciones nuevas en el layout original (2 columnas lado a lado).
# FASE E: ya no se usa desde show(), pero lo dejamos por si se referencia.
def _bloque_distribucion_riesgo_global(df: pd.DataFrame):
    """DEPRECATED (FASE E): usar _bloque_barras_riesgo_por_rama y
    _bloque_donut_riesgo por separado. Se mantiene como wrapper."""
    col_donut, col_hist = st.columns([1, 2])
    with col_donut:
        _bloque_donut_riesgo(df)
    with col_hist:
        _bloque_barras_riesgo_por_rama(df)


# =============================================================================
# BLOQUE: Resumen de la selección actual (nota metodológica)
# =============================================================================

def _bloque_resumen_seleccion(df_completo: pd.DataFrame,
                               df_filtrado: pd.DataFrame,
                               tasa_ref: float) -> None:
    """
    Bloque "Tu selección actual" — fondo amarillo claro con comparativa vs UJI.

    FASE D+E iter 6 #A: añadido a petición de mjmr. Muestra un resumen de
    los KPIs del df filtrado junto con la comparativa vs el conjunto UJI sin
    filtros. Dos columnas visuales:
      - RESULTADOS: tasa abandono, riesgo alto/medio/bajo, diferencias vs UJI
      - DEMOGRAFÍA: edad media, nota acceso, % mujeres, % becados

    Además lista los filtros activos detectados en session_state.
    """
    # ----- CÁLCULOS -----
    n_filtrado      = len(df_filtrado)
    n_completo      = len(df_completo)
    pct_del_total   = (n_filtrado / n_completo * 100) if n_completo > 0 else 0

    # Resultados (df filtrado)
    n_abandono      = df_filtrado['abandono'].sum() if 'abandono' in df_filtrado.columns else 0
    tasa_abandono   = (n_abandono / n_filtrado * 100) if n_filtrado > 0 else 0

    # Niveles de riesgo — % de cada categoría en la selección
    if 'nivel_riesgo' in df_filtrado.columns and n_filtrado > 0:
        conteo_riesgo = df_filtrado['nivel_riesgo'].value_counts(normalize=True) * 100
        pct_alto  = conteo_riesgo.get('Alto', 0)
        pct_medio = conteo_riesgo.get('Medio', 0)
        pct_bajo  = conteo_riesgo.get('Bajo', 0)
    else:
        pct_alto = pct_medio = pct_bajo = 0

    # % riesgo alto en el df completo (para la diferencia)
    if 'nivel_riesgo' in df_completo.columns and n_completo > 0:
        pct_alto_uji = (df_completo['nivel_riesgo'] == 'Alto').mean() * 100
    else:
        pct_alto_uji = 0

    # Número de alumnos en riesgo alto (para el subtítulo)
    n_riesgo_alto_sel = int((df_filtrado['nivel_riesgo'] == 'Alto').sum()) if 'nivel_riesgo' in df_filtrado.columns else 0

    # Diferencias vs UJI
    diff_abandono    = tasa_abandono - tasa_ref
    diff_riesgo_alto = pct_alto      - pct_alto_uji

    # ----- DEMOGRAFÍA (FASE F Bloque 3) -----
    # Cálculo de las 4 métricas demográficas del df_filtrado.
    #
    # HALLAZGO IMPORTANTE (ver pendiente F3-AUDIT-CRITICAL y F3-MEM):
    # La columna 'edad_entrada' de meta_test_app.parquet está almacenada
    # como log(edad) — no como años reales. Esto se descubrió al investigar
    # que la media "3.05" que salía no cuadraba con años. Verificación:
    #     exp(2.9957) = 20.0  → la mediana del train cuadra con 20 años
    #     exp(3.0537) = 21.2  → la media del test cuadra con ~21 años
    #
    # Aplicamos np.exp() SOLO PARA VISUALIZAR. El modelo sigue usando los
    # valores log-transformados tal como fueron entrenados — no tocamos los
    # datos, solo la presentación al usuario.
    #
    # n_anios_beca, nota_acceso: ya están en escala original, se usan tal cual.
    # sexo_meta: puede ser texto ("Mujer"/"Hombre") o código numérico (0/1).

    # Cálculos seguros con guardas para NaN y dataframes vacíos.
    # Si una columna no existe o está toda NaN, devolvemos None y el
    # formateador muestra "—".

    # 1. Edad media — aplicar exp() para pasar de log(edad) a años
    if 'edad_entrada' in df_filtrado.columns and df_filtrado['edad_entrada'].notna().any():
        edad_log_series = df_filtrado['edad_entrada'].dropna()
        edad_media = float(np.exp(edad_log_series).mean())
    else:
        edad_media = None

    # 2. Nota acceso media — valores originales, sin transformación
    if 'nota_acceso' in df_filtrado.columns and df_filtrado['nota_acceso'].notna().any():
        nota_media = float(df_filtrado['nota_acceso'].dropna().mean())
    else:
        nota_media = None

    # 3. Becas — mostramos DOS valores combinados (maqueta FULL, acordada):
    #    (a) % de alumnos con beca alguna vez (n_anios_beca > 0)
    #    (b) media de años con beca calculada SOLO sobre los becados
    #
    # Motivación: el % solo (72%) parece alto sin contexto; la media global
    # (1,7) diluye a los que nunca tuvieron beca. Mostrando ambos el tribunal
    # ve la foto completa: "72% tuvo beca en algún momento, y de media fueron
    # 2,7 años de carrera con beca".
    #
    # Nota: qué cuenta exactamente n_anios_beca (becas MEC vs cualquier ayuda
    # económica UJI) está PENDIENTE de verificación (ver F3-AUDIT-BECAS).
    pct_becados       = None
    media_anios_beca  = None   # media calculada solo entre los becados
    if 'n_anios_beca' in df_filtrado.columns and df_filtrado['n_anios_beca'].notna().any():
        serie_beca = df_filtrado['n_anios_beca'].dropna()
        if len(serie_beca) > 0:
            mascara_con_beca = serie_beca > 0
            pct_becados = float(mascara_con_beca.mean() * 100)
            # Media solo entre los que tuvieron beca — None si no hay becados
            if mascara_con_beca.any():
                media_anios_beca = float(serie_beca[mascara_con_beca].mean())

    # 4. % mujeres — sexo_meta puede ser texto o código. Lo tratamos según el caso.
    pct_mujeres = None
    col_sexo_demo = None
    if 'sexo_meta' in df_filtrado.columns and df_filtrado['sexo_meta'].notna().any():
        col_sexo_demo = 'sexo_meta'
    elif 'sexo' in df_filtrado.columns and df_filtrado['sexo'].notna().any():
        col_sexo_demo = 'sexo'

    if col_sexo_demo is not None:
        serie_sexo_demo = df_filtrado[col_sexo_demo].dropna()
        if len(serie_sexo_demo) > 0:
            if _pd.api.types.is_numeric_dtype(serie_sexo_demo):
                # Código numérico: traducir con SEXO_INV (0→Mujer, 1→Hombre)
                serie_texto = serie_sexo_demo.map(SEXO_INV).fillna(serie_sexo_demo.astype(str))
            else:
                serie_texto = serie_sexo_demo.astype(str)
            pct_mujeres = float((serie_texto == 'Mujer').mean() * 100)

    # ----- FILTROS ACTIVOS -----
    # FASE F Bloque 2-bis: detección COMPLETA de los 11 filtros de p01.
    # Antes: solo se detectaban 9 filtros (faltaban los sliders nota_acceso y
    # años beca), y los multiselect se mostraban como "Vía (13)" sin detalle.
    # Ahora: los 11 filtros se detectan; los multiselect muestran los valores
    # (con truncado "..." si hay muchos); los sliders muestran el rango sólo
    # cuando el usuario ha modificado los valores por defecto.

    # Helper interno para formatear multiselect: lista los valores, recorta
    # si hay más de MAX_VALORES_VISIBLES para no saturar el bloque amarillo.
    MAX_VALORES_VISIBLES = 3
    def _fmt_multi(valores, etiqueta):
        """
        Formatea una lista de valores seleccionados para mostrarla en el
        bloque amarillo. Si la lista es muy larga, muestra los primeros
        MAX_VALORES_VISIBLES y añade '...+N más' al final.
        """
        valores_str = [str(v) for v in valores]
        n = len(valores_str)
        if n <= MAX_VALORES_VISIBLES:
            return f"{etiqueta} = {', '.join(valores_str)}"
        visibles = ", ".join(valores_str[:MAX_VALORES_VISIBLES])
        return f"{etiqueta} = {visibles} (+{n - MAX_VALORES_VISIBLES} más)"

    filtros_activos = []
    v = st.session_state.get("_p01_filtros_version", 0)

    # --- 1. Sexo (selectbox, default "Todos") ---
    if st.session_state.get("filtro_sexo_p01", "Todos") != "Todos":
        filtros_activos.append(f"Sexo = {st.session_state['filtro_sexo_p01']}")

    # --- 2. Rama (multiselect) ---
    rama_sel = st.session_state.get("filtro_rama_p01", [])
    if rama_sel:
        filtros_activos.append(_fmt_multi(rama_sel, "Rama"))

    # --- 3. Cohorte (slider versionado) — activo si no cubre el rango completo ---
    anios_val = st.session_state.get(f"filtro_anios_p01_v{v}")
    if anios_val and 'curso_aca_ini' in df_completo.columns:
        a_total_min = int(df_completo.loc[df_completo['curso_aca_ini'] >= 2010, 'curso_aca_ini'].min())
        a_total_max = int(df_completo.loc[df_completo['curso_aca_ini'] >= 2010, 'curso_aca_ini'].max())
        if tuple(anios_val) != (a_total_min, a_total_max):
            filtros_activos.append(f"Cohorte = {anios_val[0]}–{anios_val[1]}")

    # --- 4. Situación laboral (selectbox, default "Todas") ---
    if st.session_state.get("filtro_sit_lab_p01", "Todas") != "Todas":
        filtros_activos.append(f"Sit. laboral = {st.session_state['filtro_sit_lab_p01']}")

    # --- 5. Nota acceso (slider versionado) — activo si el rango no cubre todo ---
    nota_val = st.session_state.get(f"filtro_nota_acc_p01_v{v}")
    if nota_val and 'nota_acceso' in df_completo.columns and df_completo['nota_acceso'].notna().any():
        nota_total_min = round(float(df_completo['nota_acceso'].min()), 1)
        nota_total_max = round(float(df_completo['nota_acceso'].max()), 1)
        nota_sel_min = round(float(nota_val[0]), 1)
        nota_sel_max = round(float(nota_val[1]), 1)
        if (nota_sel_min, nota_sel_max) != (nota_total_min, nota_total_max):
            # Formato español con coma decimal
            n_min_str = f"{nota_sel_min:.1f}".replace(".", ",")
            n_max_str = f"{nota_sel_max:.1f}".replace(".", ",")
            filtros_activos.append(f"Nota acceso = {n_min_str}–{n_max_str}")

    # --- 6-10. Multiselect de filtros avanzados ---
    # Iteramos con (clave, etiqueta UI) y mostramos los valores reales,
    # no solo el conteo como hacía la versión anterior.
    for k, etiq in [
        ("filtro_riesgo_p01",      "Riesgo"),
        ("filtro_titulacion_p01",  "Titulación"),
        ("filtro_via_p01",         "Vía"),
        ("filtro_universidad_p01", "Universidad"),
        ("filtro_cupo_p01",        "Cupo"),
    ]:
        v_sel = st.session_state.get(k, [])
        if v_sel:
            filtros_activos.append(_fmt_multi(v_sel, etiq))

    # --- 11. Años beca (slider versionado) — activo si el rango no cubre todo ---
    beca_val = st.session_state.get(f"filtro_beca_p01_v{v}")
    if beca_val and 'n_anios_beca' in df_completo.columns and df_completo['n_anios_beca'].notna().any():
        beca_total_min = int(df_completo['n_anios_beca'].min())
        beca_total_max = int(df_completo['n_anios_beca'].max())
        if tuple(beca_val) != (beca_total_min, beca_total_max):
            filtros_activos.append(f"Años beca = {int(beca_val[0])}–{int(beca_val[1])}")

    n_filtros = len(filtros_activos)
    texto_filtros = " · ".join(filtros_activos) if filtros_activos else "— Sin filtros activos —"

    # ----- FORMATEADORES -----
    def _fmt(v, sufijo="", decimales=1):
        """Formatea valor con coma decimal española. Devuelve '—' si es None."""
        if v is None:
            return "—"
        fmt = f"{{:.{decimales}f}}".format(v).replace(".", ",")
        return f"{fmt}{sufijo}"

    def _fmt_diff(d, sufijo=" pp"):
        """Formatea diferencia con signo y color rojo/verde.

        FASE F Bloque 2: si el sufijo contiene "pp", añade tooltip explicativo
        sobre la unidad "puntos porcentuales" con subrayado punteado.
        """
        if d > 0.1:
            color = COLORES["abandono"]  # rojo — peor rendimiento
            flecha = "▲"
        elif d < -0.1:
            color = COLORES["exito"]  # verde — mejor rendimiento
            flecha = "▼"
        else:
            # Auditoría p03 (Chat p03, 27/04/2026): hex #78350F → COLORES['texto_suave'].
            color = COLORES["texto_suave"]
            flecha = "≈"
        signo = "+" if d > 0 else ""
        valor_str = f"{d:.1f}".replace(".", ",")

        # Envolver "pp" (si está en el sufijo) en span con tooltip
        if "pp" in sufijo:
            # Separamos la parte sin "pp" (espacios al inicio) del literal "pp"
            # para poder decorar solo la unidad. sufijo por defecto = " pp".
            prefijo_sufijo = sufijo.replace("pp", "").rstrip()
            sufijo_html = (
                f'{prefijo_sufijo} '
                f'<span title="pp = puntos porcentuales. '
                f'Diferencia absoluta entre dos tasas expresadas en porcentaje." '
                f'style="cursor:help; border-bottom:1px dotted currentColor;">'
                f'pp'
                f'</span>'
            )
        else:
            sufijo_html = sufijo

        return (f'<span style="color:{color};">'
                f'{flecha} {signo}{valor_str}{sufijo_html}'
                f'</span>')

    # ----- HTML -----
    # Fondo amarillo claro (#FEF3C7) + borde izquierdo naranja (#F59E0B).
    # Texto en tono cálido (#78350F) para legibilidad sobre amarillo.
    n_filtrado_str      = f"{n_filtrado:,}".replace(",", ".")
    n_completo_str      = f"{n_completo:,}".replace(",", ".")
    n_abandono_str      = f"{int(n_abandono):,}".replace(",", ".")
    n_riesgo_alto_str   = f"{n_riesgo_alto_sel:,}".replace(",", ".")
    pct_del_total_str   = f"{pct_del_total:.1f}".replace(".", ",")

    # ----- HTML (una sola línea, sin saltos — Streamlit los escapa) -----
    # FASE D+E iter 7: el HTML anterior salía literal en pantalla porque
    # Streamlit interpreta líneas en blanco dentro de st.markdown como fin
    # de párrafo y escapa el resto. Solución: todo en una sola línea.
    #
    # FASE F Bloque 3: RESTAURADA la sección 👥 DEMOGRAFÍA con datos reales.
    # La edad se reconstruye con np.exp() porque edad_entrada está en log(edad)
    # en meta_test_app.parquet — ver cálculos arriba para la explicación completa.
    #
    # Auditoría p03 (Chat p03, 27/04/2026): los 5 hex de este callout
    # (#FEF3C7 bg, #F59E0B borde, #78350F texto principal, #92400E sub-
    # títulos, #FCD34D separador) son una paleta amber Tailwind cohesiva
    # para el callout "Tu selección actual". NO se migran a COLORES porque:
    #   - No son colores semánticos de la paleta principal de la app
    #   - Son una familia visual intencionada (50/500/700/900 + 300)
    #   - Crear 5 entradas en COLORES solo para este callout sería
    #     sobreingeniería. Documentado y aislado en un único bloque.
    html = (
        f'<div style="background:#FEF3C7;border-left:4px solid #F59E0B;'
        f'border-radius:8px;padding:16px;margin-top:16px;'
        f'color:#78350F;font-size:13px;">'
        f'<div style="font-weight:600;font-size:15px;margin-bottom:12px;">'
        f'🟡 Tu selección actual'
        f'</div>'
        f'<div style="margin-bottom:12px;">'
        f'<b>Muestra:</b> {n_filtrado_str} alumnos '
        f'({pct_del_total_str}% del test de {n_completo_str} observaciones) · '
        f'{n_abandono_str} abandonos reales · '
        f'{n_riesgo_alto_str} en riesgo alto predicho'
        f'</div>'
        # --- Columna RESULTADOS (izquierda) + DEMOGRAFÍA (derecha) ---
        # Usamos CSS grid con 2 columnas iguales para que queden alineadas.
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'
        # Sub-bloque RESULTADOS
        f'<div>'
        f'<div style="font-weight:500;color:#92400E;margin-bottom:4px;'
        f'font-size:12px;">⚠️ RESULTADOS</div>'
        f'<div style="line-height:1.7;font-size:12px;">'
        f'· Abandono: <b>{_fmt(tasa_abandono, "%")}</b> '
        f'{_fmt_diff(diff_abandono)}<br>'
        f'· Riesgo alto: <b>{_fmt(pct_alto, "%")}</b> '
        f'{_fmt_diff(diff_riesgo_alto)}<br>'
        f'· Riesgo medio: <b>{_fmt(pct_medio, "%")}</b><br>'
        f'· Riesgo bajo: <b>{_fmt(pct_bajo, "%")}</b>'
        f'</div>'
        f'</div>'
        # Sub-bloque DEMOGRAFÍA (FASE F Bloque 3)
        # La edad media tiene un tooltip que documenta la transformación.
        # Los becados muestran DOS datos: % con beca alguna vez + media de años
        # entre los becados. Ver cálculos arriba para la justificación.
        f'<div>'
        f'<div style="font-weight:500;color:#92400E;margin-bottom:4px;'
        f'font-size:12px;">👥 DEMOGRAFÍA</div>'
        f'<div style="line-height:1.7;font-size:12px;">'
        f'· <span title="Edad media reconstruida desde log(edad) con exp(). '
        f'La columna edad_entrada se almacena en escala logarítmica en el '
        f'dataset." style="cursor:help; border-bottom:1px dotted currentColor;">'
        f'Edad media</span>: <b>{_fmt(edad_media, " años")}</b><br>'
        f'· Nota acceso: <b>{_fmt(nota_media, "")}</b><br>'
        f'· % Mujeres: <b>{_fmt(pct_mujeres, "%")}</b><br>'
        f'· <span title="El % indica cuántos alumnos recibieron beca al menos '
        f'un año durante su carrera. La media en paréntesis se calcula SOLO '
        f'sobre los alumnos becados, para que el dato no se diluya con los '
        f'que nunca tuvieron beca." '
        f'style="cursor:help; border-bottom:1px dotted currentColor;">'
        f'Becados</span>: '
        f'<b>{_fmt(pct_becados, "%")}</b>'
        f'{" (media " + _fmt(media_anios_beca, " años") + ")" if media_anios_beca is not None else ""}'
        f'</div>'
        f'</div>'
        f'</div>'  # cierre del grid
        f'<div style="margin-top:12px;padding-top:10px;'
        f'border-top:1px solid #FCD34D;font-size:12px;">'
        f'<b>Filtros ({n_filtros}):</b> {texto_filtros}'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


# =============================================================================
# FIN DE p01_institucional.py
# =============================================================================
