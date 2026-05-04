import re
# =============================================================================
# p02_titulacion.py
# Pestaña 2 — Análisis por titulación
#
# QUÉ HACE:
#   Vista detallada del abandono en una titulación concreta.
#   El usuario elige la titulación → ve métricas, distribución de riesgo,
#   factores más influyentes (SHAP), y tabla de alumnos de riesgo alto.
#
# PERFIL DE USUARIO:
#   Profesores, coordinadores de titulación y tribunal evaluador del TFM.
#   El tribunal mirará esta pestaña en profundidad — explicativa y técnica.
#
# REQUISITOS:
#   - meta_test.parquet con prob_abandono (generado en f6_m00_preparacion)
#   - shap_global.pkl (valores SHAP del modelo CatBoost)
#   - pipeline_preprocesamiento.pkl y modelo CatBoost cargados vía loaders
#
# GENERA:
#   Visualización interactiva en Streamlit (sin ficheros de salida)
#
# FLUJO:
#   loaders.py → cargar_datos_app() → df con prob_abandono, titulacion, rama
#   Selector titulación → filtrar df → KPIs → gráficos → tabla
#
# SIGUIENTE: p03_prospecto.py
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ROOT robusto — igual que en todos los notebooks del proyecto
# ---------------------------------------------------------------------------
def _detectar_root() -> Path:
    """Sube niveles desde este fichero hasta encontrar src/."""
    ruta = Path(__file__).resolve()
    for padre in ruta.parents:
        if (padre / "src").exists():
            return padre
    raise FileNotFoundError(
        f"No se encontró src/ subiendo desde {ruta}. "
        "Asegúrate de que el proyecto tiene la carpeta src/ en la raíz."
    )

ROOT = _detectar_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_app import (
    APP_CONFIG, COLORES, COLORES_RAMAS, COLORES_RIESGO, RAMAS_NOMBRES,
    UMBRALES, UMBRALES_MUESTRA, NOMBRES_VARIABLES, nombre_legible,
)
from config_app import RUTAS as _RUTAS

# Refactor SRC↔APP (Chat 8): se borraron las siguientes definiciones locales
# porque ahora vienen de config_app:
#   - _NOMBRES_EXTRA: parche con 4 etiquetas (tasa_repeticion, cred_repetidos,
#     n_anios_trabajando, n_anios_sin_notas) que faltaban en NOMBRES_VARIABLES.
#     YA están en src/config_datos.py → ETIQUETAS_VARIABLES (paso 1 del refactor).
#   - _NOMBRES_VAR: dict combinado NOMBRES_VARIABLES + _NOMBRES_EXTRA.
#     Innecesario: NOMBRES_VARIABLES ya las contiene (paso 3 del refactor).
#   - _nombre_legible(): función local de fallback.
#     Sustituida por nombre_legible() de config_app (centralizada para todas
#     las páginas, importada arriba).

# Variables excluidas del gráfico de factores (técnicas o no interpretables)
_COLS_EXCLUIR_FACTORES = {
    "nota_1er_anio_missing",
    "nota_acceso_missing",
    "nota_selectividad_missing",
    "tasa_abandono_titulacion",
}
from utils.loaders import cargar_meta_test_app, cargar_modelo, cargar_pipeline
# Auditoría p03 (Chat p03): _tarjeta_kpi se mueve a utils/ui_helpers.py para
# que p02 y p03 usen la MISMA función (apariencia idéntica garantizada por
# construcción). Antes vivía duplicada en p02 y en pronostico_shared.py
# con estilos distintos (border-top vs border-left). Se importa desde aquí.
# REFACTOR p03 (27/04/2026): añadido _nombre_titulacion_corto al import.
from utils.ui_helpers import (
    _tarjeta_kpi, _nombre_titulacion_corto, _pie_pagina,
    _leer_metricas_modelo, _guardia_df_vacio,
)
# B10 (p02): eliminado `from config_app import RUTAS as _RUTAS` duplicado
# (ya importado en L61, no hace falta volver a importarlo).


# =============================================================================
# CONSTANTES LOCALES
# =============================================================================

# Columnas que son metadatos — NO son features del modelo
# Se usan para filtrar antes de pasar datos al pipeline
# B10 (p02): eliminado "rama" duplicado (era inocuo en set, pero confuso al leer).
_COLS_META = {
    "abandono", "titulacion", "rama", "anio_cohorte",
    "sexo", "nivel_riesgo", "prob_abandono", "per_id_ficticio",
    "cupo", "curso_aca_ini", "flag_cautela", "n_titulaciones",
    "vive_fuera", "pais_nombre", "provincia", "via_acceso"
}

# Colores para niveles de riesgo
# Colores para niveles de riesgo
# B9 (Chat p02): paleta unificada — aliases hacia COLORES_RIESGO oficial de
# config_app. Antes eran hex hardcodeados que diferían de la paleta global
# (#27AE60 vs #10b981, #F39C12 vs #f59e0b, #E53E3E vs #dc2626). Ahora la
# fuente de verdad es config_app.COLORES_RIESGO, que a su vez sale de
# COLORES['exito'/'advertencia'/'abandono']. Cum laude: una sola paleta.
_COLOR_BAJO   = COLORES_RIESGO["bajo"]    # #10b981 — verde éxito
_COLOR_MEDIO  = COLORES_RIESGO["medio"]   # #f59e0b — ámbar advertencia
_COLOR_ALTO   = COLORES_RIESGO["alto"]    # #dc2626 — rojo abandono

# Bug 6 (Chat p02): _COLOR_GRIS_CONTEXTO antes estaba duplicado en 2 funciones
# (L898 y L1539). Extraído a constante de módulo para una sola fuente de verdad.
# slate-300 (#cbd5e1) — gris suave legible que NO compite visualmente con
# los colores de rama. Se usa para "el resto de titulaciones que no son la
# protagonista" en gráficos de contexto. NO migrar a COLORES porque no es
# un color semántico de la paleta principal, sino un gris neutro auxiliar.
_COLOR_GRIS_CONTEXTO = "#cbd5e1"

# Número de alumnos a mostrar en la tabla de riesgo alto
_MAX_TABLA = 50



# =============================================================================
# Auditoría p03 (Chat p03, 27/04/2026): _nombre_titulacion_corto MOVIDA a
# utils/ui_helpers.py para que p01, p02, p03/p04 usen la MISMA función.
# Antes había 4 implementaciones distintas (3 en p02 fusionadas en una local
# + _nombre_corto_tit en pronostico_shared + _partir_label en p01).
# Importada al principio del fichero junto a _tarjeta_kpi.
# =============================================================================


# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _leer_metricas_modelo ELIMINADA.
# Sustituida por _leer_metricas_modelo de utils/ui_helpers.py.
# =============================================================================


# =============================================================================
# CARGA Y PREPARACIÓN
# =============================================================================

@st.cache_data(show_spinner=False)
def _cargar_y_preparar() -> pd.DataFrame:
    """
    Carga los datos de la app y añade prob_abandono y nivel_riesgo.
    Usa X_test_prep.parquet (ya preprocesado) para evitar errores de pipeline.
    """
    df = cargar_meta_test_app().copy()

    # Traducir abreviaturas de rama a nombres completos
    if "rama" in df.columns:
        df["rama"] = df["rama"].map(RAMAS_NOMBRES).fillna(df["rama"])

    # Calcular prob_abandono desde X_test_prep (ya preprocesado en Fase 5)
    if "prob_abandono" not in df.columns:
        try:
            ruta_xprep = _RUTAS.get("X_test_prep")
            if ruta_xprep and ruta_xprep.exists():
                X_prep = pd.read_parquet(ruta_xprep)
                modelo = cargar_modelo()
                prob = modelo.predict_proba(X_prep)[:, 1]
                df["prob_abandono"] = pd.Series(prob, index=X_prep.index)
            else:
                df["prob_abandono"] = np.nan
        except Exception as e:
            st.warning(f"⚠️ No se pudieron calcular las probabilidades: {e}")
            df["prob_abandono"] = np.nan

    # Añadir nivel de riesgo categórico si no existe
    # B11 (p02): renombrados los umbrales para que el rol semántico sea explícito.
    # Antes: `umbral_alto = UMBRALES["riesgo_medio"]` (confuso al leer).
    # Ahora: nombres directos a la frontera que representan.
    #
    # Lógica del np.select (orden importante — la primera condición que cumple gana):
    #   1. prob >= 0.60 → "Alto"
    #   2. prob >= 0.30 → "Medio" (ya no llega aquí si fuera ≥0.60)
    #   3. resto         → "Bajo"
    if "nivel_riesgo" not in df.columns and "prob_abandono" in df.columns:
        frontera_alto  = UMBRALES["riesgo_medio"]   # 0.60 — frontera Medio↔Alto
        frontera_medio = UMBRALES["riesgo_bajo"]    # 0.30 — frontera Bajo↔Medio

        condiciones = [
            df["prob_abandono"] >= frontera_alto,    # Alto si ≥ 0.60
            df["prob_abandono"] >= frontera_medio,   # Medio si ≥ 0.30 (y < 0.60)
        ]
        df["nivel_riesgo"] = np.select(
            condiciones,
            ["Alto", "Medio"],
            default="Bajo"                           # Bajo si < 0.30
        )

    # B7 (Chat p02): filtro implícito del universo de análisis.
    # El TFM está definido oficialmente sobre cursos 2010–2020. En el parquet
    # meta_test_app quedan ~129 alumnos con curso_aca_ini < 2010 que son
    # residuos del dataset original. Aplicamos el filtro al FINAL (tras
    # calcular prob_abandono y nivel_riesgo) para evitar problemas de
    # alineación de índices entre X_test_prep y df. Coherente con p01 (L183).
    if "curso_aca_ini" in df.columns:
        df = df[df["curso_aca_ini"] >= 2010].reset_index(drop=True)

    return df


def _lista_titulaciones(df: pd.DataFrame) -> list[str]:
    """
    Devuelve la lista de titulaciones ordenadas: primero por rama,
    luego alfabéticamente dentro de cada rama.
    """
    if "titulacion" not in df.columns:
        return []
    return (
        df[["titulacion", "rama"]]
        .drop_duplicates()
        .sort_values(["rama", "titulacion"])["titulacion"]
        .tolist()
    )


# =============================================================================
# BLOQUES DE CONTENIDO
# =============================================================================

# -----------------------------------------------------------------------------
# REFACTOR p03 (Chat p03, 27/04/2026): _guardia_df_vacio ELIMINADA.
# Sustituida por _guardia_df_vacio de utils/ui_helpers.py.
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Auditoría p03 (Chat p03): _tarjeta_kpi MOVIDA a utils/ui_helpers.py
# -----------------------------------------------------------------------------
# Antes vivía aquí (Bug 7 del chat p02 puso la barra lateral 4px estilo p01).
# Se mueve a utils/ui_helpers.py para que p03 (pronostico_shared.py) pueda
# usar la MISMA función y las tarjetas KPI tengan apariencia idéntica entre
# p02 y p03 por construcción (un único punto de cambio en el futuro).
#
# La función está importada al principio del fichero:
#   from utils.ui_helpers import _tarjeta_kpi
# -----------------------------------------------------------------------------


def _bloque_kpis_titulacion(df_tit: pd.DataFrame):
    """
    Fila de KPIs rápidos para la titulación seleccionada.
    5 métricas: total, tasa real, tasa predicha, riesgo alto, F1 del modelo.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    if _guardia_df_vacio(df_tit, "📌 Indicadores clave"):
        return

    # -------------------------------------------------------------------------
    # RD-A (Chat p02): KPIs custom HTML compactos — sustituye st.metric por
    # tarjetas con icono + cifra grande + delta inline. Inspirado en las
    # imágenes de dashboards profesionales aportadas por María José.
    # Ventajas:
    #   - Padding reducido (más compacto, cum laude visual)
    #   - Icono distintivo por KPI (identificación rápida)
    #   - Tooltips nativos HTML con <span title="...">
    # -------------------------------------------------------------------------
    n_total         = len(df_tit)
    n_abandono_real = df_tit["abandono"].sum() if "abandono" in df_tit.columns else None
    tasa_real       = (n_abandono_real / n_total * 100) if n_abandono_real is not None else None
    tasa_predicha   = df_tit["prob_abandono"].mean() * 100 if "prob_abandono" in df_tit.columns else None
    n_riesgo_alto   = (df_tit["nivel_riesgo"] == "Alto").sum()

    # F1 global del modelo — leído desde metricas_modelo.json
    _metricas = _leer_metricas_modelo()
    _f1       = _metricas.get("f1")
    f1_val    = f"{_f1:.3f}".replace(".", ",") if _f1 is not None else "N/D"

    # --- Construir las 5 tarjetas ---
    # Bug 7 (Chat p02): cada tarjeta lleva color_barra semántico para
    # coherencia visual con p01. Patrón: azul = neutro/informativo,
    # rojo = abandono/alerta, verde = éxito/calidad del modelo.

    # KPI 1: Alumnos en test (info neutra → azul)
    html_k1 = _tarjeta_kpi(
        icono="👥",
        etiqueta="Alumnos en test",
        valor=f"{n_total:,}".replace(",", "."),
        tooltip="Número total de alumnos de esta titulación en el conjunto de test.",
        color_barra=COLORES["primario"],
    )

    # KPI 2: Tasa abandono real (métrica crítica → rojo)
    html_k2 = _tarjeta_kpi(
        icono="📉",
        etiqueta="Abandono real",
        valor=f"{tasa_real:.1f}%".replace(".", ",") if tasa_real is not None else "N/D",
        tooltip="Porcentaje de alumnos que realmente abandonaron en el conjunto de test.",
        color_barra=COLORES["abandono"],
    )

    # KPI 3: Riesgo medio predicho (con delta vs tasa real → azul predicción)
    if tasa_predicha is not None and tasa_real is not None:
        delta_k3      = tasa_predicha - tasa_real
        delta_str_k3  = f"{delta_k3:+.1f}pp vs real".replace(".", ",")
        # Inverse: si predicción > real, es peor (rojo); si < real, mejor (verde)
        color_k3      = "red" if delta_k3 > 0 else ("green" if delta_k3 < 0 else "gray")
    else:
        delta_str_k3 = ""
        color_k3     = ""
    html_k3 = _tarjeta_kpi(
        icono="🔮",
        etiqueta="Riesgo predicho",
        valor=f"{tasa_predicha:.1f}%".replace(".", ",") if tasa_predicha is not None else "N/D",
        delta=delta_str_k3,
        delta_color=color_k3,
        tooltip=("Probabilidad media de abandono según el modelo. "
                 "El delta (pp = puntos porcentuales) compara el riesgo "
                 "predicho con la tasa real observada en el test."),
        color_barra=COLORES["primario"],
    )

    # KPI 4: Alumnos en riesgo alto (alerta → rojo)
    pct_alto = n_riesgo_alto / n_total * 100 if n_total > 0 else 0
    html_k4  = _tarjeta_kpi(
        icono="🚨",
        etiqueta="Riesgo alto",
        valor=f"{pct_alto:.1f}%".replace(".", ","),
        delta=f"{n_riesgo_alto:,} alumnos".replace(",", "."),
        delta_color="gray",
        tooltip=f"Alumnos con probabilidad de abandono ≥ {UMBRALES['riesgo_medio']:.0%}.",
        color_barra=COLORES["advertencia"],   # ámbar — paridad con p01 "En riesgo alto"
    )

    # KPI 5: F1 modelo (calidad del modelo → verde éxito)
    html_k5 = _tarjeta_kpi(
        icono="🎯",
        etiqueta="F1 modelo",
        valor=f1_val,
        tooltip=f"F1-score del modelo {_metricas.get('modelo_nombre', 'final')} sobre el conjunto de test completo.",
        color_barra=COLORES["exito"],
    )

    # --- Renderizar las 5 tarjetas en una fila ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(html_k1, unsafe_allow_html=True)
    col2.markdown(html_k2, unsafe_allow_html=True)
    col3.markdown(html_k3, unsafe_allow_html=True)
    col4.markdown(html_k4, unsafe_allow_html=True)
    col5.markdown(html_k5, unsafe_allow_html=True)


def _bloque_distribucion_riesgo_titulacion(df_tit: pd.DataFrame, nombre_tit: str):
    """
    Donut grande de distribución de riesgo (RD-B) +
    Gauge F1 modelo (RD-C) +
    Histograma de probabilidades.
    Tres elementos en columnas para visión densa estilo dashboard pro.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    if _guardia_df_vacio(df_tit, "🔮 Distribución del riesgo"):
        return

    # -------------------------------------------------------------------------
    # RD-B + RD-C (Chat p02): rediseño visual cum laude.
    # Layout 3 columnas: [Donut grande con %riesgo alto en centro] [Gauge F1] [Histograma]
    # Inspirado en imágenes 2, 3 y 4 de los dashboards profesionales aportados
    # por María José.
    # -------------------------------------------------------------------------
    col_donut, col_gauge, col_hist = st.columns([1.3, 0.9, 1.6])

    # Pre-cálculo del % riesgo alto para el centro del donut
    n_total      = len(df_tit)
    n_alto       = (df_tit["nivel_riesgo"] == "Alto").sum() if "nivel_riesgo" in df_tit.columns else 0
    pct_alto_str = f"{(n_alto / n_total * 100):.0f}%" if n_total > 0 else "—"

    # ------------------------------------------------------------- DONUT GRANDE
    with col_donut:
        st.subheader("Distribución del riesgo")

        conteo = df_tit["nivel_riesgo"].value_counts().reindex(
            ["Bajo", "Medio", "Alto"], fill_value=0
        ).reset_index()
        conteo.columns = ["nivel", "n"]

        fig_donut = go.Figure(go.Pie(
            labels=conteo["nivel"],
            values=conteo["n"],
            hole=0.65,  # RD-B: agujero más grande para que destaque la cifra central
            marker_colors=[_COLOR_BAJO, _COLOR_MEDIO, _COLOR_ALTO],
            textinfo="label+percent",
            textfont=dict(size=12),
            hovertemplate="%{label}: %{value} alumnos (%{percent})<extra></extra>",
            sort=False
        ))
        # RD-B: anotación central con % riesgo alto (la métrica clave)
        # Bug 6 (Chat p02): hex hardcodeados → COLORES[...]
        fig_donut.add_annotation(
            text=f"<b>{pct_alto_str}</b>",
            x=0.5, y=0.55,
            font=dict(size=34, color=COLORES["abandono"]),
            showarrow=False,
            xanchor="center"
        )
        fig_donut.add_annotation(
            text="riesgo alto",
            x=0.5, y=0.40,
            font=dict(size=11, color=COLORES["texto_suave"]),
            showarrow=False,
            xanchor="center"
        )
        fig_donut.update_layout(
            separators=",.",
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=320,  # RD-B: más alto que antes (era 280)
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_donut, width='stretch')

    # --------------------------------------------------------------- GAUGE F1
    with col_gauge:
        st.subheader("F1 modelo")
        # RD-C: gauge tipo velocímetro para visualizar F1 en escala 0-1
        # Zonas de color: rojo (mal) / amarillo (regular) / verde (bien)
        _metricas_g = _leer_metricas_modelo()
        _f1_g       = _metricas_g.get("f1") or 0.0

        # Bug 6 (Chat p02): hex hardcodeados → COLORES[...] excepto los
        # 3 pasteles del gauge (steps) que son intencionalmente Tailwind -100
        # y no existen en la paleta principal. Se extraen a constantes locales
        # con comentario para que sigan siendo identificables.
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=_f1_g,
            number={
                "valueformat": ".3f",
                "font": {"size": 32, "color": COLORES["texto"]}
            },
            gauge={
                "axis": {
                    "range": [0, 1],
                    "tickwidth": 1,
                    "tickcolor": COLORES["texto_muy_suave"],
                    "tickvals": [0, 0.5, 0.7, 1.0],
                    "ticktext": ["0", "0.5", "0.7", "1.0"],
                },
                "bar": {"color": COLORES["texto"], "thickness": 0.25},
                "bgcolor": COLORES["blanco"],
                "borderwidth": 1,
                "bordercolor": COLORES["borde"],
                # B9 (Chat p02): pasteles light alineados con COLORES_RIESGO
                # (Opción B). Cada uno es la versión "100" de la familia
                # Tailwind del color principal de la paleta oficial:
                #   #fee2e2 = red-100   (alineado con #dc2626 = red-600)
                #   #fef3c7 = amber-100 (alineado con #f59e0b = amber-500)
                #   #d1fae5 = emerald-100 (alineado con #10b981 = emerald-500)
                # Coherencia visual: las zonas del gauge usan la misma familia
                # que el donut/histograma sin saturar el ojo.
                # Bug 6: NO migrar a COLORES porque son tonos pastel que no
                # tienen entrada propia en la paleta principal de la app.
                "steps": [
                    {"range": [0,    0.5], "color": "#fee2e2"},   # red-100
                    {"range": [0.5,  0.7], "color": "#fef3c7"},   # amber-100
                    {"range": [0.7,  1.0], "color": "#d1fae5"},   # emerald-100
                ],
                "threshold": {
                    "line": {"color": _COLOR_ALTO, "width": 3},
                    "thickness": 0.75,
                    "value": _f1_g
                }
            },
            domain={"x": [0, 1], "y": [0, 1]}
        ))
        fig_gauge.update_layout(
            separators=",.",
            margin=dict(t=10, b=10, l=20, r=20),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_gauge, width='stretch')

    # ----------------------------------------------------------- HISTOGRAMA
    with col_hist:
        st.subheader("Probabilidad de abandono")

        if "prob_abandono" in df_tit.columns:
            fig_hist = px.histogram(
                df_tit,
                x="prob_abandono",
                nbins=30,
                color="nivel_riesgo",
                color_discrete_map={
                    "Bajo": _COLOR_BAJO,
                    "Medio": _COLOR_MEDIO,
                    "Alto": _COLOR_ALTO
                },
                category_orders={"nivel_riesgo": ["Bajo", "Medio", "Alto"]},
                labels={
                    "prob_abandono": "Probabilidad de abandono",
                    "nivel_riesgo": "Nivel de riesgo"
                }
            )
            # Líneas verticales de umbral
            for umbral, etiqueta, color in [
                (UMBRALES["riesgo_bajo"],  "Umbral bajo",  _COLOR_MEDIO),
                (UMBRALES["riesgo_medio"], "Umbral alto",  _COLOR_ALTO)
            ]:
                fig_hist.add_vline(
                    x=umbral,
                    line_dash="dash",
                    line_color=color,
                    annotation_text=etiqueta,
                    annotation_position="top right"
                )
            fig_hist.update_layout(
                separators=",.",
                margin=dict(t=10, b=30, l=0, r=0),
                height=320,  # mismo height que donut/gauge para alineación
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title_text="Riesgo"
            )
            st.plotly_chart(fig_hist, width='stretch')


def _bloque_evolucion_temporal_titulacion(df_tit: pd.DataFrame):
    """
    Línea temporal: tasa de abandono real vs riesgo predicho por año de cohorte.
    Permite ver si el problema ha mejorado o empeorado en esta titulación.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    if _guardia_df_vacio(df_tit, "📈 Evolución temporal del abandono"):
        return

    st.subheader("Evolución temporal")

    col_anio = None
    for candidato in ["anio_cohorte", "curso_aca_ini"]:
        if candidato in df_tit.columns:
            col_anio = candidato
            break

    if col_anio is None or "prob_abandono" not in df_tit.columns:
        st.info("No hay datos temporales disponibles para esta titulación.")
        return

    # Agregar por año
    evol = (
        df_tit
        .groupby(col_anio)
        .agg(
            tasa_real    = ("abandono",     "mean"),
            riesgo_medio = ("prob_abandono", "mean"),
            n_alumnos    = ("prob_abandono", "count")
        )
        .reset_index()
        .rename(columns={col_anio: "anio"})
        .sort_values("anio")
    )

    fig = go.Figure()

    # Línea tasa real
    if "tasa_real" in evol.columns and evol["tasa_real"].notna().any():
        fig.add_trace(go.Scatter(
            x=evol["anio"],
            y=evol["tasa_real"] * 100,
            mode="lines+markers",
            name="Abandono real (%)",
            line=dict(color=COLORES["abandono"], width=2.5),
            marker=dict(size=7),
            hovertemplate="Año %{x}<br>Abandono real: %{y:,.1f}%<extra></extra>"
        ))

    # Línea riesgo predicho
    fig.add_trace(go.Scatter(
        x=evol["anio"],
        y=evol["riesgo_medio"] * 100,
        mode="lines+markers",
        name="Riesgo predicho medio (%)",
        line=dict(color=COLORES["primario"], width=2.5, dash="dot"),
        marker=dict(size=7),
        hovertemplate="Año %{x}<br>Riesgo predicho: %{y:,.1f}%<extra></extra>"
    ))

    fig.update_layout(
        separators=",.",
        xaxis_title="Año de cohorte",
        yaxis_title="Porcentaje (%)",
        yaxis=dict(range=[0, 100]),
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=30, b=30, l=0, r=0),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, width='stretch')


def _bloque_factores_shap(df_tit: pd.DataFrame, titulacion: str):
    """
    Variables más influyentes en esta titulación.
    Usa los valores SHAP medios del subconjunto de la titulación.
    Si SHAP no está disponible, muestra diferencia de medias como proxy.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    if _guardia_df_vacio(df_tit, "🔑 Factores que influyen"):
        return

    st.subheader("Factores más influyentes en esta titulación")
    st.caption(
        "Importancia media de cada variable (SHAP) para los alumnos "
        f"de {titulacion}. Barras positivas → aumentan el riesgo de abandono."
    )

    # Intentar cargar SHAP desde sesión (precargado en loaders)
    datos_shap = st.session_state.get("shap_values_catboost", None)

    if datos_shap is not None and "indices_tit" in st.session_state:
        # Usar SHAP real para los alumnos de esta titulación
        indices = st.session_state["indices_tit"].get(titulacion, None)
        if indices is not None and len(indices) > 0:
            shap_tit = datos_shap[indices]
            importancia_media = np.abs(shap_tit).mean(axis=0)
            shap_medio        = shap_tit.mean(axis=0)

            # Nombres legibles de las features
            feature_names = [
                NOMBRES_VARIABLES.get(f, f)
                for f in st.session_state.get("feature_names", range(len(importancia_media)))
            ]

            df_shap = pd.DataFrame({
                "variable":    feature_names,
                "importancia": importancia_media,
                "shap_medio":  shap_medio
            }).sort_values("importancia", ascending=True).tail(12)

            fig = go.Figure(go.Bar(
                x=df_shap["shap_medio"],
                y=df_shap["variable"],
                orientation="h",
                marker_color=[
                    _COLOR_ALTO if v > 0 else _COLOR_BAJO
                    for v in df_shap["shap_medio"]
                ],
                hovertemplate="%{y}: SHAP medio = %{x:,.3f}<extra></extra>"
            ))
            fig.add_vline(x=0, line_color="gray", line_width=1)
            fig.update_layout(
                separators=",.",
                xaxis_title="Impacto SHAP medio",
                margin=dict(t=10, b=10, l=0, r=0),
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, width='stretch')
            return

    # --- Fallback: diferencia de medias estandarizada (Cohen's d) ---
    # Bug 3 (Chat p02): refactor del gráfico de factores en 5 problemas:
    #
    # 1) ESCALAS INCOMPARABLES: antes se mostraba la diferencia ABSOLUTA, lo
    #    que aplastaba variables de escala pequeña (notas 0-10) frente a las
    #    grandes (créditos 0-60). Ahora se muestra el effect size de Cohen
    #    (diferencia / desviación estándar pooled) que normaliza todas las
    #    variables a la misma escala (típicamente -3 a +3).
    #
    # 2) FORMATO DECIMAL ESPAÑOL: tickformat con coma decimal y separator
    #    de miles (",.2f" en Plotly = 1,234.56 → con separators={"decimal":",",
    #    "thousands":"."} → 1.234,56).
    #
    # 3) TOOLTIP RICO: muestra valor original (media abandona, media no
    #    abandona, diferencia real con unidades) además del effect size.
    #
    # 4) CAPTION EXPLICATIVO: en lenguaje plano qué se está viendo.
    #
    # 5) Si una titulación no tiene 2 clases en abandono (todos abandonan o
    #    ninguno), aviso visual.

    cols_num = [
        c for c in df_tit.select_dtypes(include=[np.number]).columns
        if c not in _COLS_META and "prob" not in c
        and c not in _COLS_EXCLUIR_FACTORES
    ]

    if not cols_num:
        st.info("No hay variables numéricas disponibles para este análisis.")
        return

    if "abandono" not in df_tit.columns:
        st.info("La columna 'abandono' no está disponible en este subconjunto.")
        return

    # Bug 3 (problema 5): aviso si solo hay una clase
    if df_tit["abandono"].nunique() < 2:
        st.warning(
            "⚠️ No es posible mostrar los factores influyentes en esta "
            "titulación: en el conjunto de test todos los alumnos pertenecen "
            "al mismo grupo (todos abandonan o ninguno abandona). Esto es "
            "habitual en titulaciones con muestra muy pequeña."
        )
        return

    # Calcular medias por grupo y desviación estándar pooled por variable
    grupo_aband = df_tit[df_tit["abandono"] == 1][cols_num]
    grupo_cont  = df_tit[df_tit["abandono"] == 0][cols_num]

    media_aband = grupo_aband.mean()
    media_cont  = grupo_cont.mean()
    diferencia  = media_aband - media_cont

    # Cohen's d: diferencia / desviación estándar pooled
    # Pooled std = sqrt((var1 + var2) / 2) — versión simple, robusta a tamaños
    var_aband = grupo_aband.var()
    var_cont  = grupo_cont.var()
    std_pooled = np.sqrt((var_aband + var_cont) / 2)
    # Evitar división por cero: si std=0 (variable constante) → d=0
    cohens_d = diferencia / std_pooled.replace(0, np.nan)
    cohens_d = cohens_d.fillna(0)

    # Cambio relativo en % respecto a la media del grupo no-abandono
    pct_cambio = (diferencia / media_cont.replace(0, np.nan) * 100).fillna(0)

    df_proxy = pd.DataFrame({
        "var_tecnica": cols_num,
        "variable":    [nombre_legible(c) for c in cols_num],
        "diferencia":  diferencia.values,
        "cohens_d":    cohens_d.values,
        "media_aband": media_aband.values,
        "media_cont":  media_cont.values,
        "pct_cambio":  pct_cambio.values,
    }).sort_values("cohens_d")

    # Quedarse con top 12 por |effect size|
    df_proxy["abs_d"] = df_proxy["cohens_d"].abs()
    df_proxy = df_proxy.nlargest(12, "abs_d").sort_values("cohens_d")

    # Tooltip rico (Bug 3 problema 3): formato español con coma decimal
    customdata = np.column_stack([
        df_proxy["media_aband"].round(2),
        df_proxy["media_cont"].round(2),
        df_proxy["diferencia"].round(2),
        df_proxy["pct_cambio"].round(1),
    ])
    hovertemplate = (
        "<b>%{y}</b><br>"
        "Los que abandonan: %{customdata[0]:,.2f}<br>"
        "Los que NO abandonan: %{customdata[1]:,.2f}<br>"
        "Diferencia: %{customdata[2]:+.2f} (%{customdata[3]:+.1f}%%)<br>"
        "Tamaño de efecto (d): %{x:,.2f}"
        "<extra></extra>"
    )

    fig = go.Figure(go.Bar(
        x=df_proxy["cohens_d"],
        y=df_proxy["variable"],
        orientation="h",
        marker_color=[
            _COLOR_ALTO if v > 0 else _COLOR_BAJO
            for v in df_proxy["cohens_d"]
        ],
        customdata=customdata,
        hovertemplate=hovertemplate,
    ))
    fig.add_vline(x=0, line_color="gray", line_width=1)
    fig.update_layout(
        xaxis_title="Tamaño de efecto (Cohen's d)",
        # Bug 3 (problema 2): formato español con coma decimal
        xaxis=dict(tickformat=".1f"),
        separators=",.",   # Plotly: decimal "," miles "."
        margin=dict(t=10, b=10, l=0, r=0),
        height=max(380, len(df_proxy) * 28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, width='stretch')

    # Bug 3 (problema 4): caption explicativo en lenguaje plano
    st.caption(
        "ℹ️ **Cómo leer este gráfico:** las barras muestran cuánto se "
        "diferencian los alumnos que abandonan de los que no, en cada "
        "variable. La escala está normalizada (Cohen's d) para poder "
        "comparar variables con escalas distintas (notas, créditos, años). "
        "**Pasa el ratón por encima** para ver los valores reales. "
        "Barras hacia la derecha (rojo) → los que abandonan tienen MÁS de "
        "esa variable. Barras hacia la izquierda (verde) → tienen MENOS. "
        "Los valores SHAP no están cargados; se usa este proxy como "
        "alternativa robusta."
    )


def _bloque_tabla_riesgo_alto(df_tit: pd.DataFrame):
    """
    Tabla de alumnos con riesgo alto, ordenada de mayor a menor probabilidad.
    Columnas seleccionadas para ser útiles al profesor coordinador.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    if _guardia_df_vacio(df_tit, "⚠️ Alumnos en riesgo alto"):
        return

    st.subheader(f"Alumnos en riesgo alto (≥ {UMBRALES['riesgo_medio']:.0%})")

    df_alto = df_tit[df_tit["nivel_riesgo"] == "Alto"].copy()

    if df_alto.empty:
        st.success("✅ No hay alumnos en riesgo alto en esta titulación.")
        return

    # Columnas a mostrar — las que existan en el dataframe
    cols_mostrar_candidatas = [
        "per_id_ficticio", "prob_abandono", "nota_acceso", "nota_1er_anio",
        "n_anios_beca", "tasa_rendimiento", "situacion_laboral",
        "anio_cohorte", "sexo_meta"
    ]
    cols_mostrar = [c for c in cols_mostrar_candidatas if c in df_alto.columns]

    df_tabla = (
        df_alto[cols_mostrar]
        .sort_values("prob_abandono", ascending=False)
        .head(_MAX_TABLA)
        .rename(columns={
            # Auditoría nombres técnicos (Chat p02): "per_id_ficticio" se
            # añadió a config_app.py → _EXTRAS_UI con etiqueta "ID alumno"
            # para que el rename automático con NOMBRES_VARIABLES lo cubra.
            # Antes había un rename local explícito aquí; ahora ya no hace
            # falta porque viene del diccionario global.
            c: NOMBRES_VARIABLES.get(c, c) for c in cols_mostrar
        })
    )

    # Formatear columna de probabilidad
    col_prob = NOMBRES_VARIABLES.get("prob_abandono", "prob_abandono")
    # Bug C (Chat p02): formato español en %. f-string con :.1% usa punto.
    if col_prob not in df_tabla.columns:
        # Buscar por nombre original formateado
        col_prob_display = "Probabilidad de abandono"
        if col_prob_display in df_tabla.columns:
            df_tabla[col_prob_display] = df_tabla[col_prob_display].map(
                lambda x: f"{x:.1%}".replace(".", ",") if pd.notna(x) else "—"
            )
    else:
        df_tabla[col_prob] = df_tabla[col_prob].map(
            lambda x: f"{x:.1%}".replace(".", ",") if pd.notna(x) else "—"
        )

    st.dataframe(
        df_tabla,
        width='stretch',
        height=min(400, 40 + len(df_tabla) * 35)
    )

    if len(df_alto) > _MAX_TABLA:
        st.caption(f"Mostrando los {_MAX_TABLA} alumnos de mayor riesgo de {len(df_alto)} totales.")


def _bloque_contexto_titulacion(df: pd.DataFrame, titulacion_sel: str, rama_tit: str):
    """
    Comparativa de la titulación seleccionada con las de su misma rama.
    Colores por rama — seleccionada más intensa, resto más suave.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    # Nota: aquí df es el dataset GLOBAL (no filtrado por titulación), por lo
    # que en la práctica rara vez estará vacío, pero aplicamos la guardia
    # igualmente por paridad estructural con los otros 6 bloques.
    if _guardia_df_vacio(df, "🧭 Contexto de la titulación"):
        return

    st.subheader("Comparativa con el resto de titulaciones")

    if "titulacion" not in df.columns or "prob_abandono" not in df.columns:
        return

    # Mostrar todas las titulaciones de la misma rama
    col_rama = "rama"
    df_rama = df[df[col_rama] == rama_tit] if rama_tit and col_rama in df.columns else df

    por_tit = (
        df_rama.groupby("titulacion")["prob_abandono"]
        .mean()
        .reset_index()
        .rename(columns={"prob_abandono": "riesgo_medio"})
        .sort_values("riesgo_medio", ascending=True)
    )

    if por_tit.empty:
        return

    # Color base de la rama
    color_rama = COLORES_RAMAS.get(rama_tit, COLORES["primario"])

    # Fix 2 (Chat p02, Opción C): coherente con modo comparativo.
    # Seleccionada → color de rama intenso (protagonista).
    # Resto → gris slate-300 suave (contexto). Antes era rgba transparente
    # del mismo color de rama, lo que saturaba visualmente cuando todas
    # las titulaciones eran de la misma rama.
    # Bug 6: usa _COLOR_GRIS_CONTEXTO (constante de módulo, antes duplicada).
    colores = [
        color_rama if t == titulacion_sel else _COLOR_GRIS_CONTEXTO
        for t in por_tit["titulacion"]
    ]

    # Bug 8 (Chat p02): antes usaba re.sub("Grado en|Doble Grado en") con
    # solo 2 prefijos, dejando títulos largos como "Grado en Ingeniería en X"
    # como "Ingeniería en X". Ahora usa el helper unificado del módulo que
    # cubre todos los prefijos y trata el caso especial de Doble Grado.
    tit_cortas = [_nombre_titulacion_corto(t) for t in por_tit["titulacion"]]

    fig = go.Figure(go.Bar(
        x=por_tit["riesgo_medio"] * 100,
        y=tit_cortas,
        orientation="h",
        marker_color=colores,
        text=[f"{v*100:.1f}%".replace(".", ",") for v in por_tit["riesgo_medio"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:,.1f}%<extra></extra>"
    ))
    max_x = max(por_tit["riesgo_medio"].max() * 100 * 1.25, 15)
    fig.update_layout(
        separators=",.",
        xaxis_title="Riesgo medio predicho (%)",
        xaxis=dict(range=[0, max_x]),
        margin=dict(t=10, b=30, l=0, r=60),
        height=max(200, 40 + len(por_tit) * 38),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.caption(
        f"Titulaciones de la rama '{rama_tit}' ordenadas por riesgo predicho. "
        "La seleccionada aparece en color sólido."
    )
    st.plotly_chart(fig, width='stretch')


def _comparativa_construir_tabla(df: pd.DataFrame, titulaciones_sel: list[str], col_rama: str) -> pd.DataFrame:
    """Construye el DataFrame resumen para el modo comparativo."""
    filas = []
    for tit in titulaciones_sel:
        df_t = df[df["titulacion"] == tit]
        if df_t.empty:
            continue
        n         = len(df_t)
        tasa_real = df_t["abandono"].mean() * 100 if "abandono" in df_t.columns else None
        riesgo    = df_t["prob_abandono"].mean() * 100 if "prob_abandono" in df_t.columns else None
        n_alto    = (df_t["nivel_riesgo"] == "Alto").sum()
        pct_alto  = n_alto / n * 100 if n > 0 else 0
        rama      = df_t[col_rama].mode()[0] if col_rama in df_t.columns and not df_t.empty else "—"
        # Regla: usar helper unificado (incluye trato especial Doble Grado).
        tit_corto = _nombre_titulacion_corto(tit)
        filas.append({
            "Titulación":          tit_corto,
            "Rama":                rama,
            "Alumnos":             n,
            "Abandono real (%)":   round(tasa_real, 1) if tasa_real is not None else None,
            "Riesgo predicho (%)": round(riesgo, 1) if riesgo is not None else None,
            "En riesgo alto":      n_alto,
            "% riesgo alto":       round(pct_alto, 1),
        })
    return pd.DataFrame(filas)


# Fix 3 (Chat p02): paleta profesional Tailwind para distinguir titulaciones
# en gráficos del modo comparativo (líneas evolución, barras factores).
# Antes eran hex aleatorios (verde #38A169, naranja #D69E2E, magenta #E91E8C)
# que no combinaban entre sí ni con COLORES_RIESGO/COLORES_RAMAS.
# Ahora: 10 colores Tailwind en intensidad -500/-600, escogidos para
# máxima distinción visual entre sí y paleta moderna coherente.
_PALETA_COMP = [
    "#4f46e5",  # indigo-600
    "#e11d48",  # rose-600
    "#059669",  # emerald-600
    "#d97706",  # amber-600
    "#7c3aed",  # violet-600
    "#0891b2",  # cyan-600
    "#db2777",  # pink-600
    "#65a30d",  # lime-600
    "#2563eb",  # blue-600
    "#ea580c",  # orange-600
]


# -----------------------------------------------------------------------------
# B3-D (Chat p02): HELPER PARA ETIQUETAS CON N VISIBLE
# -----------------------------------------------------------------------------
# Para nivel cum laude, en los gráficos del modo comparativo mostramos el
# número de alumnos junto al nombre de la titulación. Esto evita que el
# tribunal/lector interprete "60% riesgo alto en X" sin saber si X tiene
# 300 alumnos (sólido) o 5 alumnos (ruido estadístico).
#
# Si N < UMBRALES_MUESTRA['aceptable'] (30 alumnos), añadimos ⚠️ delante
# como aviso visual de muestra pequeña.
#
# Formato: "Medicina (300 alumnos)" o "⚠️ Doble Grado (8 alumnos)"

def _etiqueta_titulacion_con_n(nombre: str, n: int, segunda_linea: bool = False) -> str:
    """
    Construye la etiqueta de una titulación con su N de alumnos.

    Parámetros:
      nombre         → nombre de la titulación (puede llevar saltos <br>)
      n              → número de alumnos en el conjunto de test
      segunda_linea  → si True, coloca el "(N alumnos)" en una segunda línea
                       con etiqueta más pequeña en gris (Bug E1+E4 Chat p02).
                       Recomendado para etiquetas de eje Y/X de gráficos donde
                       el espacio horizontal es limitado.

    Devuelve:
      str con formato "Nombre (N alumnos)" o si segunda_linea=True:
      "Nombre<br><span ...>(N alumnos)</span>".
      Si N < UMBRALES_MUESTRA['aceptable'], se prefija ⚠️.
    """
    n_str = f"{n:,}".replace(",", ".")
    aviso = "⚠️ " if n < UMBRALES_MUESTRA['aceptable'] else ""

    if segunda_linea:
        # Bug E1+E4 (Chat p02): "(N alumnos)" en segunda línea más pequeña y
        # gris. Plotly admite HTML básico en etiquetas de eje (<br>, <span>).
        # tickfont del eje no se modifica, solo se añade el span pequeño.
        return (
            f"{aviso}{nombre}<br>"
            f'<span style="font-size:0.78em; color:{COLORES["texto_suave"]};">'
            f"({n_str} alumnos)</span>"
        )

    return f"{aviso}{nombre} ({n_str} alumnos)"


# -----------------------------------------------------------------------------
# Bug 4 parte B (Chat p02): LEYENDA HTML COMPARTIDA
# -----------------------------------------------------------------------------
# Para que un PAR de gráficos comparativos comparta una sola leyenda visual
# debajo (en lugar de duplicarla arriba de cada uno, ocupando 2 espacios),
# generamos un bloque HTML con chips coloreados que se pinta una vez.
#
# Ventajas frente a la leyenda nativa de Plotly:
#   - Una sola leyenda para 2 gráficos (no 2 leyendas duplicadas)
#   - Posición fija debajo del par, no arriba
#   - 2 líneas en horizontal (ahorra espacio vertical)
#   - Mismo color exacto que las trazas (color_tit del diccionario)
#
# Uso:
#   1. En cada gráfico del par: showlegend=False
#   2. Al final del par (después de los 2 st.plotly_chart): llamar a
#      _renderizar_leyenda_titulaciones_html(titulaciones_sel, color_tit)

def _renderizar_leyenda_titulaciones_html(titulaciones: list, color_map: dict):
    """
    Renderiza una leyenda HTML compartida con chips coloreados de titulación.
    Diseñada para ir DEBAJO de un par de gráficos comparativos.

    Layout: flex-wrap, max 2 líneas en pantallas habituales, cada chip lleva
    cuadrado de color + nombre acortado (helper unificado del módulo).

    Parameters
    ----------
    titulaciones : list[str]
        Lista de nombres de titulación a mostrar.
    color_map : dict[str, str]
        Mapa nombre titulación → color hex (color_tit del bloque comparativo).
    """
    chips = []
    for tit in titulaciones:
        color = color_map.get(tit, COLORES["primario"])
        nombre_corto = _nombre_titulacion_corto(tit)
        chips.append(
            f'<span style="display:inline-flex;align-items:center;'
            f'gap:0.4rem;padding:0.2rem 0.6rem;margin:0.15rem 0.25rem;'
            f'background:{COLORES["fondo"]};border-radius:6px;'
            f'font-size:0.82rem;color:{COLORES["texto"]};">'
            f'<span style="display:inline-block;width:0.8rem;height:0.8rem;'
            f'background:{color};border-radius:2px;flex-shrink:0;"></span>'
            f'{nombre_corto}'
            f'</span>'
        )

    html = (
        f'<div style="display:flex;flex-wrap:wrap;justify-content:center;'
        f'align-items:center;margin:0.4rem 0 0.8rem 0;'
        f'padding:0.4rem;border-top:1px solid {COLORES["borde"]};">'
        + "".join(chips) +
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _bloque_comparativa_titulaciones(df: pd.DataFrame, titulaciones_sel: list[str]):
    """
    Vista comparativa cuando el usuario selecciona varias titulaciones.
    Mismos 4 bloques que el modo detalle, adaptados para comparar N titulaciones.
    """
    # B3-C (Chat p02): guardia de df vacío al inicio del bloque (paridad p01).
    # df es el dataset GLOBAL aquí — rara vez vacío, pero aplicamos por paridad.
    if _guardia_df_vacio(df, "📊 Comparativa entre titulaciones"):
        return

    col_rama = "rama"  # B10 (p02): antes había condición tautológica que siempre devolvía "rama"
    df_comp  = _comparativa_construir_tabla(df, titulaciones_sel, col_rama)

    # B3-C (Chat p02): reemplazada la mini-guardia `if df_comp.empty: st.warning`
    # por _guardia_df_vacio para coherencia visual con el resto de bloques.
    # Antes era un st.warning simple; ahora es la caja gris elegante unificada.
    if _guardia_df_vacio(df_comp, "📊 Comparativa entre titulaciones"):
        return

    # Asignar un color fijo a cada titulación para coherencia entre gráficos
    color_tit = {
        tit: _PALETA_COMP[i % len(_PALETA_COMP)]
        for i, tit in enumerate(titulaciones_sel)
    }

    # -------------------------------------------------------------------------
    # CABECERA + TABLA RESUMEN
    # -------------------------------------------------------------------------
    st.subheader(f"Comparativa de {len(titulaciones_sel)} titulaciones")

    # -------------------------------------------------------------------------
    # RD-A-comp (Chat p02): KPIs agregados del modo comparativo.
    # 5 indicadores con MISMO ORDEN E ICONOS que el modo detalle (Opción C
    # decidida con María José, sesión 22-abr-26) para 100% coherencia UX:
    #   1. 👥 Alumnos totales (suma)
    #   2. 📉 Abandono real medio (ponderado por N)
    #   3. 🔮 Riesgo predicho medio (ponderado por N)
    #   4. 🚨 Riesgo alto (% del total + suma)
    #   5. 🎯 F1 modelo (mismo dato que en detalle, modelo único)
    # El nº de titulaciones queda en el subtítulo "Comparativa de N titulaciones",
    # no necesita repetirse como KPI.
    # -------------------------------------------------------------------------
    # Construir df solo con las titulaciones seleccionadas para los cálculos
    df_sel = df[df["titulacion"].isin(titulaciones_sel)]

    n_alumnos_total     = len(df_sel)
    abandono_real_medio = (
        df_sel["abandono"].mean() * 100
        if "abandono" in df_sel.columns and n_alumnos_total > 0
        else None
    )
    riesgo_pred_medio   = (
        df_sel["prob_abandono"].mean() * 100
        if "prob_abandono" in df_sel.columns and n_alumnos_total > 0
        else None
    )
    n_riesgo_alto_total = (
        (df_sel["nivel_riesgo"] == "Alto").sum()
        if "nivel_riesgo" in df_sel.columns
        else 0
    )

    # F1 global del modelo — mismo dato que en modo detalle (modelo único)
    _metricas_comp = _leer_metricas_modelo()
    _f1_comp       = _metricas_comp.get("f1")
    f1_val_comp    = f"{_f1_comp:.3f}".replace(".", ",") if _f1_comp is not None else "N/D"

    # Bug 7 (Chat p02): mismos colores semánticos que en modo detalle
    # para coherencia visual entre las dos vistas.

    # KPI 1: Alumnos totales (info neutra → azul)
    html_c1 = _tarjeta_kpi(
        icono="👥",
        etiqueta="Alumnos totales",
        valor=f"{n_alumnos_total:,}".replace(",", "."),
        tooltip="Suma de alumnos de todas las titulaciones seleccionadas en el test.",
        color_barra=COLORES["primario"],
    )

    # KPI 2: Abandono real medio (métrica crítica → rojo)
    html_c2 = _tarjeta_kpi(
        icono="📉",
        etiqueta="Abandono real medio",
        valor=f"{abandono_real_medio:.1f}%".replace(".", ",") if abandono_real_medio is not None else "N/D",
        tooltip="Tasa media de abandono real (ponderada por número de alumnos de cada titulación).",
        color_barra=COLORES["abandono"],
    )

    # KPI 3: Riesgo predicho medio con delta vs real (azul predicción)
    if riesgo_pred_medio is not None and abandono_real_medio is not None:
        delta_c3     = riesgo_pred_medio - abandono_real_medio
        delta_str_c3 = f"{delta_c3:+.1f}pp vs real".replace(".", ",")
        color_c3     = "red" if delta_c3 > 0 else ("green" if delta_c3 < 0 else "gray")
    else:
        delta_str_c3 = ""
        color_c3     = ""
    html_c3 = _tarjeta_kpi(
        icono="🔮",
        etiqueta="Riesgo predicho medio",
        valor=f"{riesgo_pred_medio:.1f}%".replace(".", ",") if riesgo_pred_medio is not None else "N/D",
        delta=delta_str_c3,
        delta_color=color_c3,
        tooltip=("Probabilidad media de abandono según el modelo (ponderada). "
                 "El delta (pp = puntos porcentuales) compara con la tasa real."),
        color_barra=COLORES["primario"],
    )

    # KPI 4: Riesgo alto (alerta → rojo)
    pct_alto_total = (n_riesgo_alto_total / n_alumnos_total * 100
                      if n_alumnos_total > 0 else 0)
    html_c4 = _tarjeta_kpi(
        icono="🚨",
        etiqueta="Riesgo alto",
        valor=f"{pct_alto_total:.1f}%".replace(".", ","),
        delta=f"{n_riesgo_alto_total:,} alumnos".replace(",", "."),
        delta_color="gray",
        tooltip=f"Alumnos con probabilidad de abandono ≥ {UMBRALES['riesgo_medio']:.0%}.",
        color_barra=COLORES["advertencia"],   # ámbar — paridad con p01
    )

    # KPI 5: F1 modelo (calidad del modelo → verde)
    html_c5 = _tarjeta_kpi(
        icono="🎯",
        etiqueta="F1 modelo",
        valor=f1_val_comp,
        tooltip=f"F1-score del modelo {_metricas_comp.get('modelo_nombre', 'final')} sobre el conjunto de test completo.",
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

    st.caption("Haz clic en el encabezado de cualquier columna para ordenar.")
    # Bug C (Chat p02): formato español en la tabla. Streamlit no respeta
    # locale por defecto, hay que pasar column_config con format manual.
    # Truco: %.1f genera "37.1" → reemplazamos a string formateado en el df
    # antes de mostrarlo (column_config solo da puntos como separador).
    df_comp_show = df_comp.copy()
    for col in ["Abandono real (%)", "Riesgo predicho (%)", "% riesgo alto"]:
        if col in df_comp_show.columns:
            df_comp_show[col] = df_comp_show[col].apply(
                lambda v: f"{v:.1f}".replace(".", ",") if pd.notna(v) else "—"
            )
    # "Alumnos" y "En riesgo alto" son enteros — añadir separador de miles ES.
    for col in ["Alumnos", "En riesgo alto"]:
        if col in df_comp_show.columns:
            df_comp_show[col] = df_comp_show[col].apply(
                lambda v: f"{int(v):,}".replace(",", ".") if pd.notna(v) else "—"
            )
    st.dataframe(df_comp_show, width='stretch', hide_index=True,
                 height=min(450, 50 + len(df_comp_show) * 38))

    st.divider()

    # =========================================================================
    # BLOQUE 1 — Distribución del riesgo (barras apiladas horizontales)
    # =========================================================================
    filas_riesgo = []
    for tit in titulaciones_sel:
        df_t = df[df["titulacion"] == tit].copy()
        n    = len(df_t)
        if n == 0 or "nivel_riesgo" not in df_t.columns:
            continue
        conteo = df_t["nivel_riesgo"].value_counts().reindex(
            ["Bajo", "Medio", "Alto"], fill_value=0
        )
        for nivel, cnt in conteo.items():
            filas_riesgo.append({
                "Titulación": tit,
                "Nivel":      nivel,
                "Porcentaje": cnt / n * 100,
                "N":          int(cnt),
                # B3-D (Chat p02): N_total = alumnos totales de la titulación.
                # Se usa para construir la etiqueta del eje Y "Tit (N alumnos)".
                # No confundir con "N" arriba, que es el conteo de ese nivel.
                "N_total":    n,
            })

    # RD-D-comp (Chat p02): Estrategia B — 2 columnas SIEMPRE para
    # Distribución por riesgo + Probabilidad de abandono, no solo cuando ≤2
    # titulaciones. Más denso visualmente, menos scroll. Si resulta apretado
    # con muchas titulaciones, revertir a `usar_columnas = len(titulaciones_sel) <= 2`.
    usar_columnas = True
    col_dist, col_hist = st.columns(2)
    if filas_riesgo:
        df_r = pd.DataFrame(filas_riesgo)
        fig_dist = go.Figure()
        # Bug 8 (Chat p02): antes había una función local _partir_nombre que
        # SOLO partía en 2 líneas, NO quitaba prefijo "Grado en". Resultado:
        # las etiquetas mostraban "Grado en Estudios<br>Ingleses". Ahora se
        # usa el helper unificado del módulo que sí quita prefijos comunes.

        for nivel, color in [("Bajo", _COLOR_BAJO), ("Medio", _COLOR_MEDIO), ("Alto", _COLOR_ALTO)]:
            df_n = df_r[df_r["Nivel"] == nivel].copy()
            # B3-D (Chat p02): la etiqueta del eje Y muestra el N total de
            # alumnos: "Medicina (300 alumnos)" o "⚠️ Doble Grado (8 alumnos)"
            # si N < 30. El helper se aplica solo al nombre; el "(N alumnos)"
            # se concatena después para no romper el truncado.
            # E1+E4 Opción B (Chat p02): el N se anota al final de cada
            # barra (n=NNN), NO en el eje Y. El eje Y muestra solo el nombre
            # corto. Resuelve la lectura difícil de las etiquetas largas.
            df_n["Titulación"] = df_n.apply(
                lambda fila: (
                    "⚠️ " if int(fila["N_total"]) < UMBRALES_MUESTRA["aceptable"] else ""
                ) + _nombre_titulacion_corto(
                    fila["Titulación"], partir_lineas=True, max_chars=22
                ),
                axis=1
            )
            fig_dist.add_trace(go.Bar(
                y=df_n["Titulación"],
                x=df_n["Porcentaje"],
                name=nivel,
                orientation="h",
                marker_color=color,
                text=[f"{v:.1f}%".replace(".", ",") for v in df_n["Porcentaje"]],
                textposition="inside",
                hovertemplate="%{y} — " + nivel + ": %{x:,.1f}% (%{customdata} alumnos)<extra></extra>",
                customdata=df_n["N"],
            ))

        # E1+E4 Opción B (Chat p02): anotación "n=NNN" pegada al final de
        # cada barra (a la derecha del 100%). Usa annotations en lugar de
        # texto en el trace para que no se solape con los % de Bajo/Medio/Alto.
        # Recorremos las titulaciones únicas (df_r["Titulación"] tiene 3
        # filas por titulación, una por nivel).
        df_n_unico = df_r.drop_duplicates("Titulación")[["Titulación", "N_total"]]
        df_n_unico["etiq_y"] = df_n_unico.apply(
            lambda fila: (
                "⚠️ " if int(fila["N_total"]) < UMBRALES_MUESTRA["aceptable"] else ""
            ) + _nombre_titulacion_corto(
                fila["Titulación"], partir_lineas=True, max_chars=22
            ),
            axis=1
        )
        for _, fila in df_n_unico.iterrows():
            fig_dist.add_annotation(
                x=102,                       # un poco fuera del 100% para no pisar
                y=fila["etiq_y"],
                text=f"n={int(fila['N_total'])}",
                showarrow=False,
                xanchor="left",
                font=dict(size=11, color=COLORES["texto_suave"]),
            )

        fig_dist.update_layout(
            separators=",.",
            barmode="stack",
            xaxis_title="Porcentaje (%)",
            xaxis=dict(range=[0, 115]),    # ampliar un poco para que entre la anotación
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        traceorder="normal"),
            margin=dict(t=30, b=20, l=0, r=10),
            height=min(280, 60 + len(titulaciones_sel) * 45),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        contenedor_dist = col_dist if usar_columnas else st.container()
        with contenedor_dist:
            st.subheader("Distribución por riesgo")
            st.caption("Proporción de alumnos en cada nivel de riesgo por titulación.")
            st.plotly_chart(fig_dist, width='stretch')

    # --- Histograma (<=2 titulaciones) o Boxplot (>2 titulaciones) ---
    if "prob_abandono" in df.columns:
        contenedor_hist = col_hist if usar_columnas else st.container()
        with contenedor_hist:
            st.subheader("Probabilidad de abandono")
            stats_list = []  # se rellena en el bloque violin (>2 tit)
            if len(titulaciones_sel) <= 2:
                # Histograma superpuesto
                fig_prob = go.Figure()
                for tit in titulaciones_sel:
                    df_t = df[df["titulacion"] == tit]
                    if df_t.empty:
                        continue
                    tit_corto = _nombre_titulacion_corto(tit)
                    fig_prob.add_trace(go.Histogram(
                        x=df_t["prob_abandono"],
                        name=tit_corto,
                        nbinsx=25,
                        marker_color=color_tit[tit],
                        opacity=0.6,
                        hovertemplate=f"{tit_corto}<br>Probabilidad: %{{x:,.2f}}<br>Alumnos: %{{y}}<extra></extra>"
                    ))
                for umbral, etiqueta, color in [
                    (UMBRALES["riesgo_bajo"],  "Umbral bajo",  _COLOR_MEDIO),
                    (UMBRALES["riesgo_medio"], "Umbral alto",  _COLOR_ALTO)
                ]:
                    fig_prob.add_vline(
                        x=umbral, line_dash="dash", line_color=color,
                        annotation_text=etiqueta, annotation_position="top right"
                    )
                fig_prob.update_layout(
                    separators=",.",
                    barmode="overlay",
                    xaxis_title="Probabilidad de abandono",
                    yaxis_title="Nº alumnos",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(t=50, b=20, l=0, r=0),
                    height=max(220, 50 + len(titulaciones_sel) * 45),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
            else:
                # Violin plot — muestra distribución completa de probabilidades por titulación
                # Bug 8 (Chat p02): antes había una función local _nombre_corto
                # que duplicaba la lógica. Ahora usa el helper unificado del módulo.

                # Calcular estadísticas por titulación para tooltip y tabla
                stats_list = []
                fig_prob = go.Figure()
                for tit in titulaciones_sel:
                    df_t = df[df["titulacion"] == tit]["prob_abandono"].dropna()
                    if df_t.empty:
                        continue
                    # B3-D (Chat p02): N = nº de alumnos de esta titulación con
                    # probabilidad calculada. Se usa para etiqueta "Tit (N alumnos)".
                    n_tit = len(df_t)
                    q1, med, q3 = df_t.quantile([0.25, 0.5, 0.75]).values
                    media = df_t.mean()
                    mini  = df_t.min()
                    maxi  = df_t.max()
                    stats_list.append({
                        # Regla: nunca "Grado en" en tablas/gráficos.
                        "Titulación": _nombre_titulacion_corto(tit),
                        "Media":    round(media, 3),
                        "Mediana":  round(med,   3),
                        "Q1":       round(q1,    3),
                        "Q3":       round(q3,    3),
                        "Mín":      round(mini,  3),
                        "Máx":      round(maxi,  3),
                    })
                    # Tooltip sin nombre — solo estadísticas
                    hover = (
                        f"Media: {media:.3f}<br>"
                        f"Mediana: {med:.3f}<br>"
                        f"Q1: {q1:.3f} · Q3: {q3:.3f}<br>"
                        f"Mín: {mini:.3f} · Máx: {maxi:.3f}"
                        "<extra></extra>"
                    )
                    fig_prob.add_trace(go.Violin(
                        y=df_t,
                        # E1+E4 Opción B (Chat p02): el nombre del violin va
                        # SIN "(N alumnos)". El N se muestra como anotación
                        # encima del violin (más limpio, no se mezcla con la
                        # cola del violin gracias a yref="paper").
                        # Bug 8: usa helper unificado (max_chars 18 para violin).
                        name=(
                            "⚠️ " if n_tit < UMBRALES_MUESTRA["aceptable"] else ""
                        ) + _nombre_titulacion_corto(
                            tit, partir_lineas=True, max_chars=18
                        ),
                        marker_color=color_tit[tit],
                        fillcolor=color_tit[tit],
                        opacity=0.7,
                        box_visible=True,
                        meanline_visible=True,
                        points=False,
                        hovertemplate=hover
                    ))

                # E1+E4 Opción B (Chat p02) — Bug B fix: anotaciones n=NNN
                # encima de cada violin. Cambios respecto al intento anterior:
                #   - y subido a 1.08 (yref="paper") para quedar bien fuera
                #     del área del gráfico, sin pisar las colas que llegan a 1.
                #   - bgcolor blanco + borde gris claro: garantiza legibilidad
                #     incluso si Plotly recorta el área de margen.
                #   - x usa índice de la traza (i), NO el nombre con <br>,
                #     para evitar que Plotly no encuentre la categoría exacta.
                for i, tit in enumerate(titulaciones_sel):
                    df_t = df[df["titulacion"] == tit]["prob_abandono"].dropna()
                    if df_t.empty:
                        continue
                    fig_prob.add_annotation(
                        x=i,
                        y=1.08,
                        yref="paper",
                        text=f"<b>n={len(df_t)}</b>",
                        showarrow=False,
                        font=dict(size=11, color=COLORES["texto"]),
                        bgcolor=COLORES["blanco"],
                        bordercolor=COLORES["borde"],
                        borderwidth=1,
                        borderpad=2,
                    )

                for umbral, etiqueta, color_ann in [
                    (UMBRALES["riesgo_bajo"],  "Umbral bajo",  _COLOR_MEDIO),
                    (UMBRALES["riesgo_medio"], "Umbral alto",  _COLOR_ALTO)
                ]:
                    fig_prob.add_hline(
                        y=umbral, line_dash="dash", line_color=color_ann,
                        annotation_text=etiqueta,
                        annotation_position="right",
                        annotation_font_color=color_ann
                    )
                fig_prob.update_layout(
                    separators=",.",
                    yaxis_title="Probabilidad<br>de abandono",
                    yaxis=dict(range=[0, 1]),
                    xaxis=dict(tickangle=-30),
                    showlegend=False,
                    margin=dict(t=60, b=20, l=0, r=80),   # +40 arriba para anotaciones n=
                    height=max(360, 100 + len(titulaciones_sel) * 50),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
            st.plotly_chart(fig_prob, width='stretch')

            # Expander con tabla de estadísticas detalladas
            if stats_list:
                with st.expander("📊 Estadísticas detalladas de probabilidad de abandono", expanded=False):
                    import pandas as _pd_stats
                    df_stats = _pd_stats.DataFrame(stats_list).set_index("Titulación")
                    # Formatear con coma decimal
                    for col in df_stats.columns:
                        df_stats[col] = df_stats[col].apply(lambda x: f"{x:.3f}".replace(".", ","))
                    st.dataframe(df_stats, width='stretch')
                    st.caption(
                        "Media = promedio de probabilidad predicha · "
                        "Mediana = valor central · Q1/Q3 = percentiles 25 y 75 · "
                        "Mín/Máx = valores extremos"
                    )

    st.divider()

    # =========================================================================
    # RD-D-comp (Chat p02): BLOQUES 2+3 en 2 columnas (Evolución + Factores)
    # Misma proporción 40/60 que en modo detalle, para coherencia visual.
    # =========================================================================
    col_evo_c, col_fact_c = st.columns([1, 1.5])

    # =========================================================================
    # BLOQUE 2 — Evolución temporal (una línea por titulación, abandono real)
    # =========================================================================
    with col_evo_c:
        st.subheader("Evolución temporal")
        st.caption("Tasa de abandono real por año de cohorte. Una línea por titulación.")

        col_anio = next((c for c in ["anio_cohorte", "curso_aca_ini"] if c in df.columns), None)

        if col_anio and "abandono" in df.columns:
            fig_evol = go.Figure()
            for tit in titulaciones_sel:
                df_t = df[df["titulacion"] == tit]
                evol = (
                    df_t.groupby(col_anio)["abandono"]
                    .mean()
                    .reset_index()
                    .rename(columns={col_anio: "anio", "abandono": "tasa_real"})
                    .sort_values("anio")
                )
                if evol.empty:
                    continue
                tit_corto = _nombre_titulacion_corto(tit)
                fig_evol.add_trace(go.Scatter(
                    x=evol["anio"],
                    y=evol["tasa_real"] * 100,
                    mode="lines+markers",
                    name=tit_corto,
                    line=dict(color=color_tit[tit], width=2.5),
                    marker=dict(size=6),
                    hovertemplate=f"{tit_corto}<br>Año %{{x}}: %{{y:,.1f}}%<extra></extra>"
                ))
            fig_evol.update_layout(
                separators=",.",
                xaxis_title="Año de cohorte",
                yaxis_title="Tasa de abandono real (%)",
                yaxis=dict(range=[0, 100]),
                showlegend=False,  # Bug 4B: leyenda compartida HTML abajo
                margin=dict(t=30, b=30, l=0, r=0),
                height=340,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_evol, width='stretch')
        else:
            st.info("No hay datos temporales disponibles.")

    # =========================================================================
    # BLOQUE 3 — Factores influyentes (Cohen's d, barras agrupadas)
    # =========================================================================
    with col_fact_c:
        st.subheader("Factores más influyentes")
        st.caption(
            "Variables que más diferencian a los alumnos que abandonan de los "
            "que no, en cada titulación."
        )

        # Bug A (Chat p02): aplicar también la exclusión de variables técnicas
        # (_missing flags, tasa_abandono_titulacion). Sin esto se colaba
        # "nota_1er_anio_missing" sin formatear en el gráfico de factores.
        cols_num = [
            c for c in df.select_dtypes(include=[np.number]).columns
            if c not in _COLS_META and "prob" not in c
            and c not in _COLS_EXCLUIR_FACTORES
        ]

        if cols_num and "abandono" in df.columns:
            # Bug 3 (Chat p02): refactor cum laude — Cohen's d normalizado
            # + tooltip rico + aviso de titulaciones excluidas.
            cohens_d_dict = {}     # {tit: Series con cohens_d por variable}
            customdata_dict = {}   # {tit: dict{var: (m_aband, m_cont, dif, pct)}}
            tits_excluidas = []

            for tit in titulaciones_sel:
                df_t    = df[df["titulacion"] == tit]
                cols_ok = [c for c in cols_num if c in df_t.columns]

                # Bug 3 (problema 5): titulaciones sin 2 clases se excluyen
                # con aviso explícito al usuario.
                if df_t["abandono"].nunique() < 2:
                    tits_excluidas.append(tit)
                    continue

                grupo_a = df_t[df_t["abandono"] == 1][cols_ok]
                grupo_n = df_t[df_t["abandono"] == 0][cols_ok]
                m_a = grupo_a.mean()
                m_n = grupo_n.mean()
                dif = m_a - m_n

                # Cohen's d con std pooled
                std_pool = np.sqrt((grupo_a.var() + grupo_n.var()) / 2)
                d = (dif / std_pool.replace(0, np.nan)).fillna(0)

                # % cambio
                pct = (dif / m_n.replace(0, np.nan) * 100).fillna(0)

                cohens_d_dict[tit] = d
                customdata_dict[tit] = {
                    var: (m_a[var], m_n[var], dif[var], pct[var])
                    for var in cols_ok
                }

            # Aviso de titulaciones excluidas (Bug 3 problema 5)
            if tits_excluidas:
                _nombres_excluidas = ", ".join(
                    _nombre_titulacion_corto(t) for t in tits_excluidas
                )
                st.info(
                    f"ℹ️ {len(tits_excluidas)} titulación(es) no aparece(n) "
                    f"en el gráfico porque en el test no tienen alumnos de "
                    f"ambas clases (todos abandonan o ninguno): "
                    f"**{_nombres_excluidas}**. Suele pasar en titulaciones "
                    f"con muestra muy pequeña."
                )

            if cohens_d_dict:
                # Top 10 variables por |Cohen's d| medio entre titulaciones
                df_d = pd.DataFrame(cohens_d_dict)
                top_vars = df_d.abs().mean(axis=1).nlargest(10).index.tolist()
                df_top   = df_d.loc[top_vars].copy()

                fig_fact = go.Figure()
                for tit in titulaciones_sel:
                    if tit not in df_top.columns:
                        continue
                    # Construir customdata por variable para esta titulación
                    cd_tit = customdata_dict[tit]
                    customdata = np.array([
                        [cd_tit[v][0], cd_tit[v][1], cd_tit[v][2], cd_tit[v][3]]
                        for v in top_vars
                    ])
                    tit_corto = _nombre_titulacion_corto(tit)
                    fig_fact.add_trace(go.Bar(
                        y=[NOMBRES_VARIABLES.get(v, v) for v in top_vars],
                        x=df_top[tit].values,
                        name=tit_corto,
                        orientation="h",
                        marker_color=color_tit[tit],
                        opacity=0.85,
                        customdata=customdata,
                        hovertemplate=(
                            f"<b>{tit_corto}</b><br>"
                            "%{y}<br>"
                            "Los que abandonan: %{customdata[0]:,.2f}<br>"
                            "Los que NO abandonan: %{customdata[1]:,.2f}<br>"
                            "Diferencia: %{customdata[2]:+.2f} (%{customdata[3]:+.1f}%%)<br>"
                            "Tamaño de efecto (d): %{x:,.2f}"
                            "<extra></extra>"
                        ),
                    ))
                fig_fact.add_vline(x=0, line_color="gray", line_width=1)
                fig_fact.update_layout(
                    barmode="group",
                    xaxis_title="Tamaño de efecto (Cohen's d)",
                    xaxis=dict(tickformat=".1f"),
                    separators=",.",
                    showlegend=False,  # Bug 4B: leyenda compartida HTML abajo
                    margin=dict(t=30, b=20, l=0, r=10),
                    height=max(400, 50 + len(top_vars) * 42),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_fact, width='stretch')
                st.caption(
                    "ℹ️ **Cómo leer:** escala normalizada (Cohen's d) que "
                    "permite comparar variables de escalas distintas (notas, "
                    "créditos, años). Pasa el ratón por encima para ver los "
                    "valores reales de cada titulación. SHAP no cargado; se "
                    "usa este proxy robusto."
                )
        else:
            st.info("No hay variables numéricas disponibles para este análisis.")

    # Bug 4B (Chat p02): leyenda compartida HTML para el par
    # Evolución temporal + Factores influyentes. Las dos figuras tienen
    # showlegend=False — esta leyenda actúa para ambas.
    _renderizar_leyenda_titulaciones_html(titulaciones_sel, color_tit)

    st.divider()

    # =========================================================================
    # BLOQUE 4 — Contexto ramas (resaltando las ramas de las titulaciones sel.)
    # =========================================================================
    st.subheader("Comparativa con el resto de titulaciones")
    st.caption(
        "Las ramas de las titulaciones seleccionadas aparecen resaltadas. "
        "Sirve para contextualizar si el abandono es alto o bajo respecto al resto."
    )

    if "titulacion" in df.columns and "prob_abandono" in df.columns:
        tits_sel_set = set(titulaciones_sel)
        por_tit_ctx = (
            df.groupby("titulacion")["prob_abandono"]
            .mean()
            .reset_index()
            .rename(columns={"prob_abandono": "riesgo_medio"})
            .sort_values("riesgo_medio", ascending=True)
        )
        # B10 (p02): formato de la línea simplificado (antes tenía espacios extra
        # que dificultaban la lectura). Misma lógica.
        rama_por_tit = (
            df.drop_duplicates("titulacion").set_index("titulacion")["rama"].to_dict()
            if "rama" in df.columns else {}
        )
        # Fix 2 (Chat p02, Opción C): "Comparativa con resto" — gris suave
        # para las NO seleccionadas (contexto) + color de rama intenso para
        # las seleccionadas (protagonistas). Inspirado en dashboards pro
        # (Tableau, PowerBI). Resuelve el problema de paletas desordenadas
        # (magenta/verde/azul mezclados sin lógica) que se veía antes.
        # Bug 6: usa _COLOR_GRIS_CONTEXTO (constante de módulo).
        colores_ctx = [
            COLORES_RAMAS.get(rama_por_tit.get(t, ""), COLORES["primario"])
            if t in tits_sel_set
            else _COLOR_GRIS_CONTEXTO
            for t in por_tit_ctx["titulacion"]
        ]
        borde_ancho = [2 if t in tits_sel_set else 0 for t in por_tit_ctx["titulacion"]]
        borde_color = [COLORES["texto"] if t in tits_sel_set else "rgba(0,0,0,0)"
                       for t in por_tit_ctx["titulacion"]]
        # Regla: nunca mostrar "Grado en"/"Doble Grado en" en etiquetas. Helper.
        tit_cortas_ctx = [_nombre_titulacion_corto(t) for t in por_tit_ctx["titulacion"]]
        # hovertemplate también debe mostrar el nombre corto — guardamos el
        # original en customdata para el tooltip si hace falta acceder a él
        # más adelante (de momento solo lo usamos si quisiéramos verlo).
        fig_ctx = go.Figure(go.Bar(
            x=por_tit_ctx["riesgo_medio"] * 100,
            y=tit_cortas_ctx,
            orientation="h",
            marker=dict(color=colores_ctx, line=dict(color=borde_color, width=borde_ancho)),
            text=[
                (f"{v*100:.1f}% ◀" if t in tits_sel_set else f"{v*100:.1f}%").replace(".", ",")
                for v, t in zip(por_tit_ctx["riesgo_medio"], por_tit_ctx["titulacion"])
            ],
            textposition="outside",
            hovertemplate="%{y}: %{x:,.1f}%<extra></extra>"
        ))
        fig_ctx.update_layout(
            separators=",.",
            xaxis_title="Riesgo medio predicho (%)",
            xaxis=dict(range=[0, max(por_tit_ctx["riesgo_medio"].max() * 115, 10)]),
            margin=dict(t=10, b=30, l=0, r=60),
            height=max(300, 40 + len(por_tit_ctx) * 22),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_ctx, width='stretch')


def _nota_metodologica_p02(n_alumnos_test: int = None):
    """
    Bloque plegable con explicación metodológica orientada al tribunal.
    Responde a preguntas que un evaluador podría hacer al ver esta pestaña.

    B12 (Chat p02): refactor completo —
      - Base learners corregidos: CatBoost + RandomForest (antes: XGBoost/LightGBM erróneo)
      - AUC y F1 leídos dinámicamente de metricas_modelo.json
      - Umbrales leídos de UMBRALES (config_app) — antes hardcodeados a 30/60
      - N del test pasado como parámetro (antes hardcodeado a 6.725)

    Parameters
    ----------
    n_alumnos_test : int, optional
        Número total de alumnos en el conjunto de test. Si es None, no se
        incluye el dato en el texto. Se recomienda pasar len(df) desde mostrar().
    """
    # --- Leer métricas del modelo (fallbacks documentados si el JSON falla) ---
    _metricas = _leer_metricas_modelo()
    _auc = _metricas.get("auc")
    _f1  = _metricas.get("f1")
    auc_str = f"{_auc:.3f}".replace(".", ",") if _auc is not None else "0,931"
    f1_str  = f"{_f1:.3f}".replace(".", ",")  if _f1  is not None else "0,799"

    # --- Umbrales dinámicos desde UMBRALES (config_app) ---
    _u_bajo  = UMBRALES.get("riesgo_bajo",  0.30)
    _u_medio = UMBRALES.get("riesgo_medio", 0.60)
    bajo_pct  = f"{_u_bajo:.0%}"
    medio_pct = f"{_u_medio:.0%}"

    # --- N del test (con separador de miles al estilo español) ---
    n_str = f"{n_alumnos_test:,}".replace(",", ".") if n_alumnos_test else "—"

    with st.expander("📋 Cómo entender estos datos", expanded=False):
        st.markdown(f"""
        **¿Qué hace el modelo?**

        Mira las características de un alumno (notas, beca, situación laboral,
        etc.) y estima la probabilidad de que abandone. Aprende de los
        históricos de **30.872 alumnos** que entraron en la UJI entre 2010 y 2020.

        **¿Funciona bien?**

        Acierta en el **95 %** de los casos al ordenar a los alumnos por riesgo
        (AUC = {auc_str}). Mantiene buen equilibrio entre detectar a los que
        sí abandonan sin marcar por error a los que terminan (F1 = {f1_str}).

        **¿Por qué el riesgo predicho no coincide con el abandono real?**

        El modelo da una probabilidad ("30 % de riesgo"), no un sí/no rotundo.
        El "abandono real" es lo que pasó de verdad. Una diferencia pequeña
        entre los dos indica que el modelo es realista.

        **Niveles de riesgo:** bajo (< {bajo_pct}), medio ({bajo_pct}–{medio_pct}),
        alto (≥ {medio_pct}).

        **Lo que no puede hacer**

        - Decir con certeza si UN alumno concreto abandonará. Da probabilidades.
        - Predecir bien para cohortes de 2020 en adelante (aún no sabemos
          si abandonarán o no).
        - Las titulaciones con pocos alumnos en test ({n_str} en total)
          muestran tasas más inestables.

        Los datos están anonimizados; ningún alumno aparece identificado.
        """)


# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): _pie_pagina ELIMINADA.
# Sustituida por _pie_pagina de utils/ui_helpers.py.
# =============================================================================


# =============================================================================
# FUNCIÓN PRINCIPAL DE LA PESTAÑA
# =============================================================================

# -----------------------------------------------------------------------------
# B4 (Chat p02): NOTA SOBRE EL PATRÓN DE BORRAR FILTROS
# -----------------------------------------------------------------------------
# El botón 🗑️ Borrar filtros sigue el patrón establecido en p01 (líneas
# 494-518) — NO usa on_click=callback ni session_state.pop(), porque ambos
# fallan con multiselects que tienen key= (los chips visuales no se borran).
#
# Patrón correcto (replicado de p01):
#   1. Detectar click directo: if st.button(...): ...
#   2. Asignar el valor por defecto: st.session_state[k] = []  (no pop)
#   3. Forzar re-render completo con st.rerun()
#
# La lógica está inline en el botón (líneas ~1450-1465), no en helper externo,
# por coherencia con p01.
#
# TODO: si en el futuro se añaden sliders u otros widgets persistentes a los
# filtros de p02, ampliar con el patrón ITER 5 de p01:
#   - Crear una clave de versión: st.session_state["_p02_filtros_version"] = N
#   - Al borrar: st.session_state["_p02_filtros_version"] += 1
#   - Usar la versión en la key del slider: key=f"slider_X_v{version}"
# Esto fuerza a Streamlit a recrear el widget desde cero (limpieza visual real).


def mostrar():
    """
    Punto de entrada principal. Llamada desde main.py cuando se selecciona
    la pestaña 'Análisis por titulación'.
    """
    st.title("📚 Análisis por titulación")
    st.markdown(
        "Selecciona una titulación para ver el perfil de abandono, "
        "los factores de riesgo y los alumnos que requieren más atención."
    )

    # --- Carga de datos ---
    with st.spinner("Cargando datos..."):
        try:
            df = _cargar_y_preparar()
        except Exception as e:
            st.error(f"Error cargando los datos: {e}")
            st.stop()

    if df.empty:
        st.warning("El conjunto de datos está vacío.")
        st.stop()

    if "titulacion" not in df.columns:
        st.error(
            "La columna 'titulacion' no está disponible. "
            "Comprueba que `meta_test.parquet` incluye la titulación "
            "y que `loaders.py` hace el join correctamente."
        )
        st.stop()

    # --- Selectores en la página ---
    col_rama = "rama"  # B10 (p02): antes había condición tautológica que siempre devolvía "rama"
    ramas_disponibles = sorted(df[col_rama].dropna().unique().tolist())

    # Zona de filtros — línea azul arriba y abajo
    # B4 (Chat p02): cabecera reorganizada como p01 (líneas 486-518).
    # Layout: [título "🔍 Filtros" | botón "🗑️ Borrar filtros"]
    # CRÍTICO: el botón se renderiza ANTES de los multiselects para que la
    # lógica de borrado pueda asignar session_state[k]=[] sin error
    # (Streamlit prohíbe modificar session_state de un widget ya instanciado).
    col_titulo, col_btn = st.columns([5, 1])
    with col_titulo:
        # Bug 6 (Chat p02): #3182ce (azul claro viejo) → COLORES["primario"]
        # (azul institucional profundo, valor actual #1e4d8c). Coherencia con
        # el resto de la app que ya usa el primario.
        st.markdown(f"""
        <div style="border-top: 2px solid {COLORES['primario']}; margin-bottom: 0.5rem;">
            <span style="font-size:0.72rem; font-weight:600; color:{COLORES['primario']};
                         text-transform:uppercase; letter-spacing:0.05em;">
                🔍 Filtros
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        # B4 (Chat p02): patrón ITER 5 de p01 — detección directa del click
        # con `if st.button(...)`, asignación al valor por defecto, st.rerun().
        # NO usar on_click=callback (no funciona aquí) ni session_state.pop()
        # (los chips visuales se quedan). Ver p01 líneas 494-518.
        _click_borrar = st.button(
            "🗑️ Borrar filtros",
            key="btn_borrar_filtros_p02",
            width='stretch',
            help="Limpia las selecciones de Rama y Titulación."
        )
        if _click_borrar:
            # Resetear multiselects a su valor por defecto (lista vacía).
            # Como el botón se renderiza ANTES de los multiselects, esta
            # asignación es válida (los widgets aún no están instanciados).
            st.session_state["filtro_rama_p02"] = []
            st.session_state["filtro_tit_p02"]  = []
            # Re-render inmediato → todos los widgets se regeneran desde cero.
            st.rerun()

    col_sel1, col_sel2 = st.columns([1, 2])

    # Selector 1: filtro por rama (acota la lista de titulaciones)
    # B2 (p02): eliminado `default=[]` para evitar warning de Streamlit
    # cuando se combina con `key=`. Con solo `key=`, Streamlit inicializa a
    # lista vacía automáticamente (mismo comportamiento, sin warning).
    with col_sel1:
        ramas_sel = st.multiselect(
            "Rama",
            options=ramas_disponibles,
            placeholder="Acotar por rama (opcional)",
            key="filtro_rama_p02",
            help="Deja vacío para ver todas. Selecciona para acotar las titulaciones."
        )
    df_filtrado = df[df[col_rama].isin(ramas_sel)] if ramas_sel else df

    titulaciones = _lista_titulaciones(df_filtrado)
    if not titulaciones:
        st.warning("No hay titulaciones disponibles.")
        st.stop()

    # Selector 2: multiselect de titulaciones (como p01 con ramas)
    # B2 (p02): eliminado `default=[]` para evitar warning de Streamlit.
    # B1 (p02): CASCADA — limpieza automática de selecciones incompatibles.
    # Si el usuario tenía una titulación seleccionada (p.ej. "Grado en Medicina")
    # y cambia la rama a una que no la incluye (p.ej. "Sociales"), el chip se
    # queda pegado en session_state. Patrón ITER 5 de p01: limpiamos las
    # selecciones inválidas ANTES de instanciar el widget para que el estado
    # visible sea siempre coherente con las opciones disponibles.
    _sel_previa_tit = st.session_state.get("filtro_tit_p02", [])
    _sel_valida_tit = [t for t in _sel_previa_tit if t in titulaciones]
    if _sel_valida_tit != _sel_previa_tit:
        st.session_state["filtro_tit_p02"] = _sel_valida_tit

    # Bug 4 (Chat p02): límite de 8 titulaciones máximo en el multiselect.
    # Razón: con más de 8 titulaciones los gráficos comparativos se vuelven
    # ilegibles (leyenda demasiado larga, barras apiladas se aplastan, etc.).
    # max_selections=8 es bloqueante: Streamlit no deja añadir la 9ª.
    # Mostramos aviso informativo cuando se alcanza el tope.
    _MAX_TITULACIONES_COMPARATIVA = 8

    with col_sel2:
        tits_sel = st.multiselect(
            "Titulación",
            options=titulaciones,
            placeholder="Selecciona una o varias titulaciones (máx. 8)",
            key="filtro_tit_p02",
            max_selections=_MAX_TITULACIONES_COMPARATIVA,
            help=(
                f"Una titulación → análisis detallado. Varias → comparativa. "
                f"Límite: {_MAX_TITULACIONES_COMPARATIVA} titulaciones para "
                f"que los gráficos sigan siendo legibles."
            )
        )

    # Aviso amarillo cuando se alcanza el tope (paridad con el patrón p01)
    if len(tits_sel) >= _MAX_TITULACIONES_COMPARATIVA:
        st.warning(
            f"⚠️ Has alcanzado el límite de {_MAX_TITULACIONES_COMPARATIVA} "
            f"titulaciones. Si quieres comparar otra, deselecciona alguna primero."
        )

    # Bug 6 (Chat p02): banda inferior #3182ce → COLORES["primario"]
    st.markdown(f"""
    <div style="border-bottom: 2px solid {COLORES['primario']}; margin-top: 0.5rem; margin-bottom: 1rem;"></div>
    """, unsafe_allow_html=True)

    # Pantalla neutra si no ha seleccionado titulación.
    # Bug 1 (Chat p02): si hay Rama elegida pero NO Titulación, mostrar
    # automáticamente la comparativa de TODAS las titulaciones de esa rama
    # (capada a _MAX_TITULACIONES_COMPARATIVA si la rama tiene más).
    # Antes: solo se mostraba un mensaje "elige una titulación" (vacío).
    # Ahora: se aprovecha la rama como acotador de comparativa rápida.
    if not tits_sel:
        if ramas_sel:
            # Hay rama → comparativa automática de las titulaciones de la rama
            tits_de_rama = titulaciones  # ya filtradas por rama en L1874
            n_total_rama = len(tits_de_rama)

            if n_total_rama == 0:
                # Caso teórico — no debería ocurrir porque ya hay st.stop arriba
                st.warning("No hay titulaciones disponibles en esta rama.")
                _pie_pagina()
                return

            if n_total_rama == 1:
                # Solo 1 titulación en la rama → mostrar modo detalle directamente
                tits_sel = tits_de_rama[:]
            else:
                # Varias titulaciones → comparativa.
                # Si pasa de 8, capar a las 8 con más alumnos en test (más
                # representativas) y avisar.
                if n_total_rama > _MAX_TITULACIONES_COMPARATIVA:
                    # Ordenar por nº de alumnos descendente y coger las top 8
                    conteo_alumnos = (
                        df_filtrado.groupby("titulacion").size()
                        .sort_values(ascending=False)
                    )
                    tits_top = [t for t in conteo_alumnos.index if t in tits_de_rama]
                    tits_sel = tits_top[:_MAX_TITULACIONES_COMPARATIVA]

                    st.info(
                        f"ℹ️ La rama **{', '.join(ramas_sel)}** tiene "
                        f"{n_total_rama} titulaciones. Se muestran las "
                        f"{_MAX_TITULACIONES_COMPARATIVA} con más alumnos "
                        f"en el test. Para comparar otras, selecciónalas "
                        f"manualmente arriba."
                    )
                else:
                    tits_sel = tits_de_rama[:]

                # Pasar al modo comparativo directamente
                _bloque_comparativa_titulaciones(df, tits_sel)
                st.divider()
                _nota_metodologica_p02(n_alumnos_test=len(df))
                _pie_pagina()
                return
        else:
            # Estado "Sin nada elegido": invitación corta y directa
            _msg_html = (
                '<div style="font-size:1.05rem; margin-top:0.5rem;">'
                'Elige una titulación para empezar<br>'
                f'<span style="font-size:0.85rem; color:{COLORES["texto_muy_suave"]};">'
                'o filtra por rama para ver la comparativa de esa rama'
                '</span>'
                '</div>'
            )
            # Bug 6: #718096 → COLORES["texto_suave"]
            st.markdown(f"""
            <div style="text-align:center; padding:3rem 1rem; color:{COLORES['texto_suave']};">
                <div style="font-size:3rem;">🎓</div>
                {_msg_html}
            </div>
            """, unsafe_allow_html=True)
            _pie_pagina()
            return

    # =========================================================================
    # MODO COMPARATIVO — varias titulaciones seleccionadas
    # =========================================================================
    if len(tits_sel) > 1:
        _bloque_comparativa_titulaciones(df, tits_sel)
        st.divider()
        _nota_metodologica_p02(n_alumnos_test=len(df))
        _pie_pagina()
        return

    # =========================================================================
    # MODO DETALLE — una sola titulación seleccionada
    # =========================================================================
    titulacion_sel = tits_sel[0]

    # Filtrar al subconjunto de la titulación seleccionada
    df_tit = df[df["titulacion"] == titulacion_sel].copy()
    rama_tit = df_tit[col_rama].mode()[0] if col_rama in df_tit.columns and not df_tit.empty else ""

    # -------------------------------------------------------------------------
    # CONTENIDO PRINCIPAL
    # -------------------------------------------------------------------------
    st.caption(f"Rama: {rama_tit} · {len(df_tit):,} alumnos en el conjunto de test".replace(",", "."))
    st.divider()

    # -------------------------------------------------------------------------
    # B3-B (Chat p02): AVISO DE TAMAÑO DE MUESTRA
    # -------------------------------------------------------------------------
    # Copiado de p01 (líneas 191-209) para paridad total.
    # Si la titulación seleccionada tiene muy pocos alumnos en el test, los
    # porcentajes y tasas no son fiables estadísticamente. Mostramos un aviso
    # proporcional a la gravedad usando UMBRALES_MUESTRA de config_app:
    #   - minima (10):    error rojo  → muestra insuficiente
    #   - aceptable (30): warning     → muy pequeña
    #   - fiable (100):   info        → pequeña
    # Frase final "Interpreta los resultados con cautela" unificada con p01
    # para coherencia textual entre páginas (Estrategia B, sesión 22-abr-26).
    n_muestra_tit = len(df_tit)
    if n_muestra_tit < UMBRALES_MUESTRA['minima']:
        st.error(
            f"❌ Muestra insuficiente ({n_muestra_tit} alumnos). "
            f"Los porcentajes no son fiables estadísticamente. "
            f"Interpreta los resultados con cautela."
        )
    elif n_muestra_tit < UMBRALES_MUESTRA['aceptable']:
        st.warning(
            f"⚠️ Muestra muy pequeña ({n_muestra_tit} alumnos). "
            f"Los resultados son orientativos — poco representativos."
        )
    elif n_muestra_tit < UMBRALES_MUESTRA['fiable']:
        st.info(
            f"ℹ️ Muestra pequeña ({n_muestra_tit} alumnos). "
            f"Los porcentajes son indicativos."
        )

    # Bloque 1 — KPIs
    _bloque_kpis_titulacion(df_tit)

    st.divider()

    # Bloque 2 — Distribución de riesgo
    _bloque_distribucion_riesgo_titulacion(df_tit, titulacion_sel)

    st.divider()

    # -------------------------------------------------------------------------
    # RD-D (Chat p02): layout 2 columnas para Evolución + Factores.
    # Decisión cum laude: reduce scroll vertical y aprovecha ancho horizontal.
    # Proporción 40/60 — Factores recibe más espacio porque suele tener
    # nombres largos en el eje Y (más legible con anchura).
    # Comparativa con resto de titulaciones se queda full-width abajo
    # porque suele tener muchas titulaciones y necesita el ancho completo.
    # -------------------------------------------------------------------------
    col_evo, col_fact = st.columns([1, 1.5])  # 40% / 60%

    with col_evo:
        # Bloque 3 — Evolución temporal
        _bloque_evolucion_temporal_titulacion(df_tit)

    with col_fact:
        # Bloque 4 — Factores más influyentes (SHAP o proxy)
        _bloque_factores_shap(df_tit, titulacion_sel)

    st.divider()

    # Bloque 5 — Tabla quitada (datos anonimizados + escalados, sin utilidad)

    # Bloque 6 — Contexto: titulaciones de la misma rama (full-width)
    _bloque_contexto_titulacion(df, titulacion_sel, rama_tit)

    st.divider()

    # Nota metodológica para el tribunal
    _nota_metodologica_p02(n_alumnos_test=len(df))

    # Pie de página — paridad con p00/p01
    _pie_pagina()
# Alias para compatibilidad con main.py
show = mostrar
