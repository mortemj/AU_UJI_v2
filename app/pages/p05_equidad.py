# =============================================================================
# p05_equidad.py
# Pestaña 5 — Equidad y diversidad
#
# ¿QUÉ HACE ESTE FICHERO?
#   Analiza si el modelo predice de forma justa entre distintos grupos
#   de estudiantes: sexo, rama de conocimiento, vía de acceso y situación
#   de beca. Pensada para todos los perfiles, especialmente para el tribunal
#   evaluador del TFM.
#
# FILOSOFÍA DE ESTA PESTAÑA:
#   Un modelo puede ser muy preciso globalmente pero injusto con ciertos
#   grupos. Esta pestaña lo analiza con honestidad, explica cada métrica
#   en lenguaje accesible, y concluye con una valoración directa.
#
# ESTRUCTURA:
#   1. ¿Qué es la equidad en ML? — explicación didáctica
#   2. Equidad por sexo — métricas y gráficos comparativos
#   3. Equidad por rama de conocimiento
#   4. Equidad por vía de acceso
#   5. Equidad por situación de beca
#   6. Disparate Impact — métrica estándar de fairness con gauge
#   7. Matriz de confusión por grupo — quién paga el precio del error
#   8. Simulador de política institucional — umbral ajustable ★ extra
#   9. Conclusión y limitaciones — valoración honesta y directa
#
# DATOS QUE USA:
#   - cargar_meta_test_app() → metadatos + features (6.725 filas, cursos >=2010
#     se filtra a 6.596)
#   - X_test_prep.parquet   → features ya preprocesadas, para predict_proba
#     directo SIN pipeline (patrón canónico igual que p02)
#   - metricas_modelo.json  → F1 y AUC globales dinámicos
#
# REQUISITOS:
#   - config_app.py accesible
#   - utils/loaders.py disponible
#
# GENERA:
#   Página HTML interactiva. No genera ficheros en disco.
# =============================================================================

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)

# ---------------------------------------------------------------------------
# Imports internos
# ---------------------------------------------------------------------------
import _path_setup  # noqa: F401

from config_app import COLORES, COLORES_RAMAS, COLORES_RIESGO, RAMAS_NOMBRES, RUTAS as _RUTAS
from utils.loaders import cargar_meta_test_app, cargar_modelo


# =============================================================================
# CONSTANTE DE CLASIFICACIÓN BINARIA
# =============================================================================
# Umbral fijo para convertir probabilidad en clase predicha.
# Regla del proyecto: métricas comparables siempre a 0.5.
# NO confundir con los umbrales del semáforo de riesgo (UMBRALES['riesgo_bajo']
# = 0.30 y UMBRALES['riesgo_medio'] = 0.60), que son fronteras de niveles de
# riesgo, no umbrales de decisión binaria.
# En el simulador de política (Bloque 8) el umbral sí es ajustable.
UMBRAL_CLASIFICACION = 0.5


# =============================================================================
# LECTURA DE MÉTRICAS DEL MODELO — patrón canónico p01/p02
# =============================================================================

@st.cache_data(show_spinner=False)
def _leer_metricas_modelo() -> dict:
    """
    Lee metricas_modelo.json generado por Fase 6.
    Devuelve {} si no existe o falla la lectura.
    """
    try:
        ruta_m = _RUTAS.get("metricas_modelo")
        if ruta_m and ruta_m.exists():
            with open(ruta_m, encoding="utf-8") as _f:
                return json.load(_f)
    except Exception:
        pass
    return {}


# =============================================================================
# CONFIGURACIÓN DE GRUPOS SENSIBLES
# =============================================================================
# Mapa: nombre legible → columna en el df (con fallback si no existe _meta)
# El orden define el orden de aparición en la pestaña.

GRUPOS_SENSIBLES = [
    {
        "col":         "sexo",
        "col_fallback": "sexo_meta",
        "nombre":      "sexo",
        "titulo":      "Sexo",
        "icono":       "👥",
        "nota":        "Variable sensible protegida (ODS 5 — Igualdad de género).",
    },
    {
        "col":         "rama",
        "col_fallback": "rama_meta",
        "nombre":      "rama",
        "titulo":      "Rama de conocimiento",
        "icono":       "📚",
        "nota":        (
            "No es una variable protegida en sentido estricto, pero permite "
            "detectar si el modelo rinde mejor en unas disciplinas que en otras."
        ),
    },
    {
        "col":         "via_acceso",
        "col_fallback": "via_acceso_meta",
        "nombre":      "via_acceso",
        "titulo":      "Vía de acceso",
        "icono":       "🎓",
        "nota":        (
            "Refleja el origen educativo del alumno (selectividad, FP, "
            "mayores de 25…). Diferencias aquí señalan posibles inequidades "
            "de oportunidad educativa."
        ),
    },
    {
        "col":         "_beca_bin",
        "col_fallback": "tuvo_beca",
        "nombre":      "beca",
        "titulo":      "Situación de beca",
        "icono":       "💰",
        "nota":        (
            "Tramos por intensidad del apoyo becario: Sin beca / 1-2 años "
            "(puntual) / 3+ años (sostenida). Más informativo que binario "
            "con/sin, porque permite detectar si el modelo trata distinto a "
            "becarios ocasionales frente a becarios crónicos. n_anios_beca "
            "es la variable más importante del modelo."
        ),
    },
    {
        "col":         "_orden_bin",
        "col_fallback": "_orden_bin",
        "nombre":      "orden_preferencia",
        "titulo":      "Orden de preferencia",
        "icono":       "🎯",
        "nota":        (
            "Posición en que el alumno eligió esta titulación en la preinscripción "
            "(1ª opción, 2ª, etc.). Agrupado en tramos para fiabilidad estadística. "
            "Variable no protegida, pero revela sesgos del sistema de asignación "
            "de plazas: los alumnos que no entran en su 1ª opción tienden a abandonar más."
        ),
    },
    {
        "col":         "_prov_bin",
        "col_fallback": "provincia",
        "nombre":      "provincia",
        "titulo":      "Provincia",
        "icono":       "📍",
        "nota":        (
            "Origen geográfico del alumno dentro de España. Agrupado en "
            "Castellón vs resto de provincias. Permite detectar si el arraigo "
            "territorial actúa como factor protector frente al abandono."
        ),
    },
    {
        "col":         "_pais_bin",
        "col_fallback": "pais_nombre",
        "nombre":      "pais_nombre",
        "titulo":      "País de origen",
        "icono":       "🌍",
        "nota":        (
            "Reagrupado en España / UE / Extracomunitario. Variable protegida "
            "(origen nacional). Los grupos extracomunitarios suelen tener "
            "dinámicas muy distintas (visados, idioma, adaptación cultural)."
        ),
    },
    {
        "col":         "_resid_bin",
        "col_fallback": "vive_fuera",
        "nombre":      "vive_fuera",
        "titulo":      "Residencia",
        "icono":       "🏠",
        "nota":        (
            "Indica si el alumno reside fuera de Castelló durante sus estudios. "
            "Vivir fuera implica mayor coste económico, menor arraigo familiar "
            "y más barreras logísticas, factores socioeconómicos relevantes "
            "para el abandono. Permite detectar si el modelo trata de forma "
            "equitativa a alumnos desplazados frente a locales."
        ),
    },
]


def _resolver_col(df: pd.DataFrame, grupo: dict) -> str | None:
    """Devuelve la columna real disponible para un grupo sensible."""
    if grupo["col"] in df.columns:
        return grupo["col"]
    if grupo["col_fallback"] in df.columns:
        return grupo["col_fallback"]
    return None


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def show():
    """Renderiza la pestaña de equidad y diversidad completa."""

    st.markdown(f"""
    <h2 style="color: {COLORES['primario']}; margin-bottom: 0.2rem;">
        ⚖️ Equidad y diversidad
    </h2>
    <p style="color: {COLORES['texto_suave']}; margin-top: 0; font-size: 0.95rem;">
        ¿Predice el modelo de forma justa entre distintos grupos de estudiantes?
    </p>
    """, unsafe_allow_html=True)

    # Carga de datos
    with st.spinner("Cargando datos..."):
        try:
            df_raw = cargar_meta_test_app()
            modelo = cargar_modelo()
        except FileNotFoundError as e:
            st.error(f"❌ {e}")
            st.stop()

    # Calcular probabilidades y predicciones
    df = _preparar_datos(df_raw, modelo)

    if df is None:
        st.error("❌ No se pudieron calcular las predicciones.")
        st.stop()

    # ------------------------------------------------------------------
    # Calcular tasas descriptivas (cacheadas — se ejecuta solo la primera
    # vez y se reutiliza en toda la sesión salvo cambio de dataset).
    # ------------------------------------------------------------------
    df_hash = str(pd.util.hash_pandas_object(
        df[['abandono']] if 'abandono' in df.columns else df.iloc[:, :1]
    ).sum())
    tasas = _calcular_tasas_descriptivas(df_hash, df)

    st.divider()

    # ------------------------------------------------------------------
    # BLOQUES NUEVOS AL PRINCIPIO: cabecera flechas + retrato descriptivo
    # ------------------------------------------------------------------
    _bloque_cabecera_flechas(tasas)
    st.divider()
    _bloque_retrato_descriptivo(tasas)
    st.divider()

    # Bloques existentes
    _bloque_explicacion_equidad()
    st.divider()

    # ------------------------------------------------------------------
    # Bloques de equidad por grupo, agrupados en parejas (2 por línea).
    # Cada bloque incluye su propia tabla en expander dentro de su columna.
    # ------------------------------------------------------------------
    grupos_disponibles = []
    grupos_para_render = []
    for g in GRUPOS_SENSIBLES:
        col_real = _resolver_col(df, g)
        if col_real is not None:
            grupos_disponibles.append({**g, "col_real": col_real})
            grupos_para_render.append({**g, "col_real": col_real})

    # Pintar de dos en dos. Si queda un grupo solo (impar) al final,
    # se renderiza a ancho completo para no dejar media pantalla en blanco.
    n_grupos = len(grupos_para_render)
    i = 0
    while i < n_grupos:
        # Último grupo impar → ancho completo
        if i == n_grupos - 1:
            g = grupos_para_render[i]
            _bloque_equidad_por_grupo(df, g["col_real"], g["titulo"],
                                       g["icono"], g["nota"])
            st.divider()
            i += 1
        # Pareja → 2 columnas
        else:
            col_izq, col_der = st.columns(2, vertical_alignment="top")
            with col_izq:
                g = grupos_para_render[i]
                _bloque_equidad_por_grupo(df, g["col_real"], g["titulo"],
                                           g["icono"], g["nota"])
            with col_der:
                g = grupos_para_render[i + 1]
                _bloque_equidad_por_grupo(df, g["col_real"], g["titulo"],
                                           g["icono"], g["nota"])
            st.divider()
            i += 2

    _bloque_disparate_impact(df, grupos_disponibles)
    st.divider()
    _bloque_confusion_por_grupo(df, grupos_disponibles)
    st.divider()
    _bloque_simulador_politica(df)
    st.divider()
    _bloque_conclusion(df, grupos_disponibles)


# =============================================================================
# PREPARACIÓN DE DATOS
# =============================================================================

def _preparar_datos(df_raw: pd.DataFrame, modelo) -> pd.DataFrame | None:
    """
    Añade probabilidades predichas y predicciones binarias al DataFrame.

    Patrón canónico (replica p02 líneas 165-173):
    - Carga X_test_prep.parquet (features ya preprocesadas en Fase 5)
    - Llama directamente modelo.predict_proba(X_prep) SIN pipeline
    - Une prob_abandono al df por índice
    - Aplica umbral FIJO 0.5 para pred_abandono (comparabilidad entre páginas)
    - Filtra curso_aca_ini >= 2010 al final (coherente con p01/p02, N=6.596)

    Devuelve None si hay un error en la carga o cálculo.
    """
    try:
        df = df_raw.copy()

        # ------------------------------------------------------------------
        # Traducir abreviaturas de rama a nombres completos (patrón p02 L162).
        # EX → Ciencias Experimentales, HU → Artes y Humanidades, etc.
        # ------------------------------------------------------------------
        if "rama" in df.columns:
            df["rama"] = df["rama"].map(RAMAS_NOMBRES).fillna(df["rama"])

        # ------------------------------------------------------------------
        # Probabilidades: leer X_test_prep directamente, sin pipeline.
        # ------------------------------------------------------------------
        ruta_xprep = _RUTAS.get("X_test_prep")
        if not (ruta_xprep and ruta_xprep.exists()):
            st.error(f"❌ No se encontró X_test_prep en: {ruta_xprep}")
            return None

        X_prep = pd.read_parquet(ruta_xprep)
        prob   = modelo.predict_proba(X_prep)[:, 1]
        df["prob_abandono"] = pd.Series(prob, index=X_prep.index)

        # Umbral FIJO 0.5 para clasificación binaria (regla del proyecto)
        df["pred_abandono"] = (df["prob_abandono"] >= UMBRAL_CLASIFICACION).astype(int)

        # ------------------------------------------------------------------
        # Situación de beca — 3 tramos sobre n_anios_beca.
        # 'tuvo_beca' no existe en meta_test_app, solo n_anios_beca. Creamos
        # una variable categórica de INTENSIDAD del apoyo becario, más
        # informativa que el binario con/sin (académicamente más defendible).
        #   0 años        → Sin beca
        #   1-2 años      → Beca puntual
        #   3+ años       → Beca sostenida (≥ mitad carrera)
        # ------------------------------------------------------------------
        if "n_anios_beca" in df.columns:
            def _bin_beca(x):
                if pd.isna(x):
                    return "Sin beca"
                x = int(x)
                if x == 0:
                    return "Sin beca"
                elif x <= 2:
                    return "Beca puntual (1-2 años)"
                else:
                    return "Beca sostenida (3+ años)"
            df["_beca_bin"] = df["n_anios_beca"].apply(_bin_beca)
            # Mantener tuvo_beca binario como fallback para otros consumos
            df["tuvo_beca"] = df["n_anios_beca"].apply(
                lambda x: "Con beca" if (pd.notna(x) and x > 0) else "Sin beca"
            )
        elif "tuvo_beca" in df.columns:
            col_beca = df["tuvo_beca"]
            if pd.api.types.is_numeric_dtype(col_beca):
                df["tuvo_beca"] = col_beca.apply(
                    lambda x: "Con beca" if (pd.notna(x) and x > 0) else "Sin beca"
                )

        # ------------------------------------------------------------------
        # Binning para variables con muchos valores (necesario antes del
        # filtro de cursos para que los bins se apliquen a todo el df).
        # ------------------------------------------------------------------
        # Orden de preferencia: 1ª / 2ª / 3ª-5ª / 6ª+
        # IMPORTANTE: orden_preferencia viene LOG-transformada en el dataset
        # procesado de Fase 3 (probable log(orden+1)). Decodificamos antes de
        # binear: n = round(exp(valor) - 1).
        if "orden_preferencia" in df.columns:
            def _decodificar_orden(x):
                """Invertir log(orden+1) → orden original."""
                if pd.isna(x):
                    return None
                try:
                    return int(round(np.exp(float(x)) - 1))
                except Exception:
                    return None

            def _bin_orden(x):
                orden = _decodificar_orden(x)
                if orden is None:
                    return "N/D"
                if orden <= 1:
                    return "1ª opción"
                elif orden == 2:
                    return "2ª opción"
                elif orden <= 5:
                    return "3ª-5ª"
                else:
                    return "6ª+"
            df["_orden_bin"] = df["orden_preferencia"].apply(_bin_orden)

        # Provincia: Castelló vs València vs Otras
        # Nombres en valenciano (Castelló, València, Alacant, Estrangers…)
        if "provincia" in df.columns:
            def _bin_prov(x):
                if pd.isna(x):
                    return "N/D"
                s = str(x).strip().lower()
                if s.startswith("castell"):
                    return "Castelló"
                elif s.startswith("val"):  # València / Valencia
                    return "València"
                else:
                    return "Otras provincias"
            df["_prov_bin"] = df["provincia"].apply(_bin_prov)

        # País: España / UE (no ES) / Extracomunitario
        if "pais_nombre" in df.columns:
            paises_ue = {
                "Alemania", "Austria", "Bélgica", "Bulgaria", "Chipre", "Croacia",
                "Dinamarca", "Eslovaquia", "Eslovenia", "Estonia", "Finlandia",
                "Francia", "Grecia", "Hungría", "Irlanda", "Italia", "Letonia",
                "Lituania", "Luxemburgo", "Malta", "Países Bajos", "Polonia",
                "Portugal", "Rumanía", "Suecia", "Chequia", "República Checa"
            }
            def _reagrupar_pais(x):
                if pd.isna(x):
                    return "N/D"
                s = str(x).strip()
                if s in ("España", "Espana", ""):
                    return "España"
                elif s in paises_ue:
                    return "UE (no ES)"
                else:
                    return "Extracomunitario"
            df["_pais_bin"] = df["pais_nombre"].apply(_reagrupar_pais)

        # Residencia: En Castelló vs Fuera de Castelló (variable socioeconómica)
        if "vive_fuera" in df.columns:
            def _bin_resid(x):
                if pd.isna(x):
                    return "N/D"
                # Acepta bool, int, str
                if isinstance(x, (bool, np.bool_)):
                    return "Fuera de Castelló" if bool(x) else "En Castelló"
                s = str(x).strip().lower()
                if s in ("true", "1", "sí", "si", "s"):
                    return "Fuera de Castelló"
                if s in ("false", "0", "no", "n"):
                    return "En Castelló"
                return "N/D"
            df["_resid_bin"] = df["vive_fuera"].apply(_bin_resid)

        # ------------------------------------------------------------------
        # Filtro universo TFM: cursos 2010-2020 (coherente con p01/p02).
        # Aplicado DESPUÉS de calcular prob_abandono para evitar problemas
        # de alineación de índices con X_test_prep.
        # ------------------------------------------------------------------
        if "curso_aca_ini" in df.columns:
            df = df[df["curso_aca_ini"] >= 2010].reset_index(drop=True)

        return df
    except Exception as e:
        st.warning(f"⚠️ Error preparando datos: {e}")
        return None


# Mínimo de alumnos por grupo para métricas fiables en gráficos
MIN_N_GRUPO = 30


def _metricas_grupo(df_g: pd.DataFrame) -> dict:
    """
    Calcula métricas de clasificación para un subgrupo.
    Grupos con n < MIN_N_GRUPO se calculan igualmente pero se marca
    'grupo_pequeno': True para filtrarlos del gráfico y avisar en tabla.
    """
    if len(df_g) < 5 or 'abandono' not in df_g.columns:
        return {}

    y_true = df_g['abandono'].values
    y_pred = df_g['pred_abandono'].values
    y_prob = df_g['prob_abandono'].values

    try:
        return {
            'n':             len(df_g),
            'grupo_pequeno': len(df_g) < MIN_N_GRUPO,
            'tasa_real':     y_true.mean() * 100,
            'tasa_pred':     y_pred.mean() * 100,
            'precision':     precision_score(y_true, y_pred, zero_division=0) * 100,
            'recall':        recall_score(y_true, y_pred, zero_division=0) * 100,
            'f1':            f1_score(y_true, y_pred, zero_division=0) * 100,
            'auc':           roc_auc_score(y_true, y_prob) * 100
                             if len(np.unique(y_true)) > 1 else np.nan,
        }
    except Exception:
        return {}


# =============================================================================
# CÁLCULO DE TASAS DESCRIPTIVAS (CACHEADO)
# =============================================================================
# Las tasas de abandono REALES por grupo (no las del modelo) son lo que
# alimenta el gráfico cabecera de flechas y el bloque de retrato descriptivo.
# Se cachean para no recalcular en cada interacción de la página.
#
# Invalidación automática: @st.cache_data hashea el df_hash que pasamos como
# argumento. Si el parquet fuente cambia → df_hash cambia → recalcula.

@st.cache_data(show_spinner=False)
def _calcular_tasas_descriptivas(df_hash: str, df: pd.DataFrame) -> dict:
    """
    Para cada variable sensible, devuelve:
        { 'sexo': [ {grupo, n, tasa_pct}, ... ], ... }
    Solo grupos con N >= MIN_N_GRUPO entran en el resultado (para fiabilidad).
    La tasa global también se devuelve en la clave especial '_global'.
    """
    if "abandono" not in df.columns:
        return {}

    resultado = {"_global": {
        "n": len(df),
        "tasa_pct": df["abandono"].mean() * 100,
    }}

    # Columnas a recorrer (todas las que existan)
    variables = {
        "sexo":       "sexo",
        "rama":       "rama",
        "via_acceso": "via_acceso",
        "beca":       "_beca_bin",
        "orden":      "_orden_bin",
        "provincia":  "_prov_bin",
        "pais":       "_pais_bin",
        "residencia": "_resid_bin",
    }

    for clave, col in variables.items():
        if col not in df.columns:
            continue

        resumen = (
            df.groupby(col, dropna=False)
              .agg(n=("abandono", "size"), tasa=("abandono", "mean"))
              .reset_index()
        )
        # Solo grupos fiables
        resumen = resumen[resumen["n"] >= MIN_N_GRUPO]
        # Y con al menos 2 grupos distintos para que tenga sentido comparar
        if len(resumen) < 2:
            continue

        resumen["tasa_pct"] = (resumen["tasa"] * 100).round(1)
        resumen = resumen.sort_values("tasa_pct")

        resultado[clave] = [
            {
                "grupo":    str(fila[col]),
                "n":        int(fila["n"]),
                "tasa_pct": float(fila["tasa_pct"]),
            }
            for _, fila in resumen.iterrows()
        ]

    return resultado


# =============================================================================
# BLOQUE CABECERA: Flechas divergentes (estilo The Economist)
# =============================================================================
#
# Resume de un vistazo qué variable desplaza más el riesgo de abandono.
# Cada fila es una variable; la flecha azul apunta al grupo con MENOR tasa
# y la roja al de MAYOR tasa, partiendo de la media UJI.
#
# Solo se incluyen variables con diferencia >= 3 pp (las que apenas varían,
# como posiblemente país reagrupado, no aportan y se excluirían).

def _bloque_cabecera_flechas(tasas: dict):
    """Cabecera visual: flechas divergentes desde la media UJI."""
    if "_global" not in tasas:
        return

    media = tasas["_global"]["tasa_pct"]

    # Construir filas ordenadas por mayor diferencia primero
    variables_mostrar = [
        ("Rama",                "rama"),
        ("Orden de preferencia","orden"),
        ("Vía de acceso",       "via_acceso"),
        ("Sexo",                "sexo"),
        ("Beca",                "beca"),
        ("Provincia",           "provincia"),
        ("Residencia",          "residencia"),
        ("País origen",         "pais"),
    ]

    filas = []
    for etiqueta, clave in variables_mostrar:
        if clave not in tasas or len(tasas[clave]) < 2:
            continue
        grupos = tasas[clave]
        g_min = grupos[0]    # menor tasa (ya vienen ordenados)
        g_max = grupos[-1]   # mayor tasa
        diff = g_max["tasa_pct"] - g_min["tasa_pct"]
        # Filtro: solo variables con diferencia >= 3 pp
        if diff < 3:
            continue
        filas.append({
            "etiqueta":   etiqueta,
            "grupo_bajo": g_min["grupo"],
            "tasa_baja":  g_min["tasa_pct"],
            "grupo_alto": g_max["grupo"],
            "tasa_alta":  g_max["tasa_pct"],
            "diff":       diff,
        })

    if not filas:
        return

    # Ordenar por diferencia descendente
    filas.sort(key=lambda r: r["diff"], reverse=True)

    # Texto descriptivo (con coma decimal española)
    media_txt = f"{media:.1f}".replace('.', ',')
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin: 0 0 0.4rem 0;
               border-bottom: 2px solid {COLORES['borde']}; padding-bottom: 0.5rem;">
        🎯 ¿Qué desplaza más el riesgo de abandono?
    </h4>
    <p style="color: {COLORES['texto_suave']}; font-size: 0.88rem;
              margin: 0 0 1rem 0;">
        Tasa real de abandono por categoría. La línea punteada es la media UJI
        (<strong>{media_txt}%</strong>). Cada flecha muestra cuánto desvía ese
        grupo el riesgo respecto a la media.
    </p>
    """, unsafe_allow_html=True)

    # --- Construir figura Plotly con flechas (annotations con arrows) ---
    # Rango X dinámico: desde min - margen hasta max + margen
    tasa_min_global = min(f["tasa_baja"] for f in filas)
    tasa_max_global = max(f["tasa_alta"] for f in filas)
    x_min = max(0, tasa_min_global - 5)
    x_max = tasa_max_global + 5

    fig = go.Figure()

    # Una fila por variable (invertimos para que la mayor diff quede arriba)
    y_labels = [f["etiqueta"] for f in filas]

    # Línea vertical media UJI (con coma decimal española)
    media_str = f"{media:.1f}".replace('.', ',')
    fig.add_shape(
        type="line",
        x0=media, x1=media,
        y0=-0.5, y1=len(filas) - 0.5,
        line=dict(color=COLORES['texto_suave'], width=1, dash="dot"),
    )
    fig.add_annotation(
        x=media, y=len(filas) - 0.5,
        text=f"<b>media UJI {media_str}%</b>",
        showarrow=False,
        font=dict(size=10, color=COLORES['texto_suave']),
        yshift=10,
    )

    # Helper local para truncar nombres largos sin romper layout
    def _truncar(nombre: str, max_len: int = 25) -> str:
        s = str(nombre)
        return s if len(s) <= max_len else s[:max_len - 1] + "…"

    # Para cada fila: dos flechas (azul hacia baja, roja hacia alta) + labels
    for i, f in enumerate(filas):
        y = len(filas) - 1 - i  # invertir orden

        # Flecha azul (menor tasa) — desde la media hasta la tasa baja
        # Color oficial proyecto: azul UJI #1e4d8c
        fig.add_annotation(
            x=f["tasa_baja"], y=y,
            ax=media, ay=y,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=2, arrowsize=1.3, arrowwidth=2.5,
            arrowcolor="#1e4d8c",
        )
        # Label azul (a la izquierda del extremo, ARRIBA de la flecha)
        fig.add_annotation(
            x=f["tasa_baja"], y=y,
            text=f"<b>{_truncar(f['grupo_bajo'])}</b> · {f['tasa_baja']:.0f}%",
            showarrow=False,
            font=dict(size=10, color="#1e4d8c"),
            xanchor="right", xshift=-16, yshift=12,
        )

        # Flecha roja (mayor tasa) — desde la media hasta la tasa alta
        # Color oficial proyecto: rojo dropout #e53e3e
        fig.add_annotation(
            x=f["tasa_alta"], y=y,
            ax=media, ay=y,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=2, arrowsize=1.3, arrowwidth=2.5,
            arrowcolor="#e53e3e",
        )
        # Label rojo (a la derecha del extremo, ARRIBA de la flecha)
        fig.add_annotation(
            x=f["tasa_alta"], y=y,
            text=f"<b>{_truncar(f['grupo_alto'])}</b> · {f['tasa_alta']:.0f}%",
            showarrow=False,
            font=dict(size=10, color="#e53e3e"),
            xanchor="left", xshift=8, yshift=12,
        )

    # Traza invisible para que los ejes se dibujen
    fig.add_trace(go.Scatter(
        x=[x_min, x_max], y=[-0.5, len(filas) - 0.5],
        mode="markers",
        marker=dict(size=0.1, opacity=0),
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_xaxes(
        range=[x_min, x_max],
        title="Tasa de abandono real (%)",
        title_font=dict(size=10, color=COLORES['texto_suave']),
        tickfont=dict(size=10, color=COLORES['texto_suave']),
        ticksuffix="%",
        showgrid=True, gridcolor=COLORES['borde'],
        zeroline=False,
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(filas))),
        ticktext=y_labels[::-1],
        tickfont=dict(size=11, color=COLORES['texto']),
        showgrid=False, zeroline=False,
    )
    fig.update_layout(
        height=max(220, 38 * len(filas) + 60),
        margin=dict(l=100, r=20, t=20, b=35),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
    )
    st.plotly_chart(fig, width='stretch')

    st.markdown(f"""
    <p style="font-size: 0.78rem; color: {COLORES['texto_suave']};
              font-style: italic; margin-top: -0.5rem;">
        Variables con diferencia &lt; 3 pp entre grupos se excluyen del gráfico
        (no aportan narrativa visual). N total analizado:
        <strong>{tasas['_global']['n']:,}</strong> alumnos.
    </p>
    """, unsafe_allow_html=True)


# =============================================================================
# BLOQUE RETRATO DESCRIPTIVO
# =============================================================================
#
# Cards con tasas de abandono reales por variable sensible. Es la "foto
# real" del dataset: cuánto abandona CADA tipo de estudiante, antes de
# hablar de modelo y predicciones.

def _bloque_retrato_descriptivo(tasas: dict):
    """Cards de 2x2 con las tasas reales por grupo."""
    if "_global" not in tasas:
        return

    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin: 0 0 0.4rem 0;
               border-bottom: 2px solid {COLORES['borde']}; padding-bottom: 0.5rem;">
        📊 Retrato del abandono
    </h4>
    <p style="color: {COLORES['texto_suave']}; font-size: 0.88rem;
              margin: 0 0 1rem 0;">
        Tasas de abandono reales en el dataset, no predicciones del modelo.
        La barra muestra dónde está cada grupo en la escala 0-100%.
    </p>
    """, unsafe_allow_html=True)

    # Tarjetas a mostrar: (titulo, clave_en_tasas)
    cards = [
        ("💰 Beca",       "beca"),
        ("🎯 Orden",      "orden"),
        ("👥 Sexo",       "sexo"),
        ("📍 Provincia",  "provincia"),
    ]

    # Colores oficiales del proyecto (p02/p03/p04 los usan igual)
    color_bajo  = COLORES_RIESGO["bajo"]    # #10b981 verde — grupo protector
    color_alto  = COLORES_RIESGO["alto"]    # #dc2626 rojo — grupo vulnerable
    color_medio = COLORES_RIESGO["medio"]   # #f59e0b ámbar — para Δ grandes
    color_neutro = COLORES["texto_suave"]   # gris para Δ pequeñas

    cols = st.columns(4, vertical_alignment="top")
    for i, (titulo, clave) in enumerate(cards):
        with cols[i]:
            if clave not in tasas or len(tasas[clave]) < 2:
                st.markdown(f"""
                <div style="background: white;
                            border: 1px solid {COLORES['borde']};
                            border-left: 4px solid {COLORES['borde']};
                            border-radius: 8px; padding: 0.6rem 0.75rem;
                            margin-bottom: 0.4rem; min-height: 88px;">
                    <div style="font-size: 0.78rem; font-weight: 500;
                                color: {COLORES['texto']}; margin-bottom: 0.4rem;">
                        {titulo}
                    </div>
                    <div style="color: {COLORES['texto_suave']}; font-size: 0.7rem;">
                        Datos insuficientes.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                continue

            grupos = tasas[clave]
            g_bajo = grupos[0]
            g_alto = grupos[-1]
            diff   = g_alto["tasa_pct"] - g_bajo["tasa_pct"]

            # Color del Δ según severidad: ámbar si grande (≥10), gris si no.
            color_delta = color_medio if diff >= 10 else color_neutro

            # Truncar nombres largos para que quepan en card estrecha
            nombre_bajo = (g_bajo['grupo'][:15] + '…') if len(g_bajo['grupo']) > 16 else g_bajo['grupo']
            nombre_alto = (g_alto['grupo'][:15] + '…') if len(g_alto['grupo']) > 16 else g_alto['grupo']

            # Posiciones x del SVG (escala 0-100% = 0-100 viewBox)
            x_bajo = g_bajo["tasa_pct"]
            x_alto = g_alto["tasa_pct"]

            st.markdown(f"""
            <div style="background: white;
                        border: 1px solid {COLORES['borde']};
                        border-left: 4px solid {color_delta};
                        border-radius: 8px; padding: 0.6rem 0.75rem;
                        margin-bottom: 0.4rem; min-height: 88px;">
                <div style="display: flex; justify-content: space-between;
                            align-items: center; margin-bottom: 0.45rem;">
                    <span style="font-size: 0.78rem; font-weight: 500;
                                 color: {COLORES['texto']};">{titulo}</span>
                    <span style="font-size: 0.95rem; font-weight: 600;
                                 color: {color_delta};">{diff:.0f} pp</span>
                </div>
                <svg viewBox="0 0 100 12" preserveAspectRatio="none"
                     style="width: 100%; height: 12px; display: block;">
                    <line x1="0" y1="6" x2="100" y2="6"
                          stroke="{COLORES['borde']}" stroke-width="1.5"/>
                    <circle cx="{x_bajo}" cy="6" r="3.2" fill="{color_bajo}"/>
                    <circle cx="{x_alto}" cy="6" r="3.2" fill="{color_alto}"/>
                </svg>
                <div style="display: flex; justify-content: space-between;
                            font-size: 0.65rem; color: {COLORES['texto_suave']};
                            margin-top: 0.25rem;">
                    <span><span style="color: {color_bajo}; font-weight: 500;">{g_bajo['tasa_pct']:.0f}%</span> {nombre_bajo}</span>
                    <span><span style="color: {color_alto}; font-weight: 500;">{g_alto['tasa_pct']:.0f}%</span> {nombre_alto}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# BLOQUE 1: Explicación de equidad en ML
# =============================================================================

def _bloque_explicacion_equidad():
    """
    Explicación didáctica de qué es la equidad en machine learning.
    En lenguaje accesible para perfiles no técnicos (tribunal incluido).
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        🎓 ¿Qué es la equidad en un modelo de machine learning?
    </h4>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, vertical_alignment="top")

    tarjetas = [
        {
            'icono': '🎯',
            'titulo': 'El problema',
            'texto': (
                'Un modelo puede tener buena precisión global pero '
                'equivocarse sistemáticamente más con ciertos grupos. '
                'Por ejemplo, detectar peor el abandono en mujeres '
                'que en hombres, o en alumnos sin beca que con beca.'
            )
        },
        {
            'icono': '⚖️',
            'titulo': 'Qué medimos',
            'texto': (
                'Comparamos si el modelo tiene el mismo rendimiento '
                '(F1, recall, precisión) en todos los grupos. '
                'También medimos el Disparate Impact: el ratio entre '
                'las tasas de predicción positiva de cada grupo.'
            )
        },
        {
            'icono': '📏',
            'titulo': 'La regla del 80%',
            'texto': (
                'Estándar internacional de fairness: si el grupo menos '
                'favorecido recibe predicciones positivas a menos del '
                '80% de la tasa del grupo más favorecido, el modelo '
                'muestra señales de discriminación estadística.'
            )
        },
    ]

    for col, t in zip([col1, col2, col3], tarjetas):
        with col:
            st.markdown(f"""
            <div style="
                background: white;
                border: 1px solid {COLORES['borde']};
                border-top: 3px solid {COLORES['primario']};
                border-radius: 8px;
                padding: 1.2rem;
                min-height: 220px;
                height: 100%;
            ">
                <div style="font-size: 1.8rem;">{t['icono']}</div>
                <div style="font-weight: bold; color: {COLORES['primario']};
                            margin: 0.4rem 0; font-size: 0.92rem;">
                    {t['titulo']}
                </div>
                <div style="font-size: 0.8rem; color: {COLORES['texto']};
                            line-height: 1.5;">
                    {t['texto']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Variables sensibles analizadas — banner informativo
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="
        background: {COLORES['primario']}08;
        border: 1px solid {COLORES['primario']}30;
        border-radius: 8px;
        padding: 0.9rem 1.2rem;
        font-size: 0.85rem;
        color: {COLORES['texto']};
    ">
        <strong>Variables analizadas en este TFM:</strong>
        👥 <strong>Sexo</strong> (variable protegida, ODS 5) ·
        📚 <strong>Rama de conocimiento</strong> (5 áreas) ·
        🎓 <strong>Vía de acceso</strong> (origen educativo) ·
        💰 <strong>Situación de beca</strong> (proxy socioeconómico, variable más
        importante del modelo)<br>
        <span style="color: {COLORES['texto_suave']}; font-size: 0.8rem;">
        El análisis de equidad es un requisito ético del TFM (CEISH/UJI) y uno de
        los aspectos más valorados por los tribunales de Data Science.
        </span>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# BLOQUE 2–5: Equidad por grupo (genérico)
# =============================================================================

def _bloque_equidad_por_grupo(
    df: pd.DataFrame,
    col_real: str,
    titulo: str,
    icono: str,
    nota: str,
):
    """
    Analiza la equidad del modelo para cualquier variable sensible.
    Muestra tabla de métricas + gráfico comparativo de barras agrupadas
    + nota contextual + interpretación automática.
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.3rem;">
        {icono} Equidad por {titulo.lower()}
    </h4>
    <p style="font-size: 0.82rem; color: {COLORES['texto_suave']};
              margin-bottom: 0.8rem; font-style: italic;
              min-height: 4.5em;">
        {nota}
    </p>
    """, unsafe_allow_html=True)

    if col_real not in df.columns:
        st.info(f"La columna '{col_real}' no está disponible en los datos.")
        return

    grupos   = df[col_real].dropna().unique()
    filas    = []
    for g in sorted(grupos, key=lambda x: str(x)):
        df_g     = df[df[col_real] == g]
        metricas = _metricas_grupo(df_g)
        if metricas:
            metricas[titulo] = g
            filas.append(metricas)

    if not filas:
        st.info("No hay suficientes datos para calcular métricas por grupo.")
        return

    df_met    = pd.DataFrame(filas)
    col_grupo = titulo

    # --- Tabla de métricas ---
    tabla = df_met[[col_grupo, 'n', 'tasa_real', 'tasa_pred',
                    'precision', 'recall', 'f1', 'auc']].copy()
    tabla.columns = [col_grupo, 'N alumnos', 'Abandono real (%)',
                     'Predicho (%)', 'Precisión (%)', 'Recall (%)',
                     'F1 (%)', 'AUC (%)']

    for col in ['Abandono real (%)', 'Predicho (%)', 'Precisión (%)',
                'Recall (%)', 'F1 (%)', 'AUC (%)']:
        tabla[col] = tabla[col].round(1)

    # AUC puede ser NaN si un grupo tiene solo una clase (raro en este dataset
    # pero posible en grupos muy pequeños de vía de acceso). ProgressColumn no
    # renderiza bien NaN y corta la fila: reemplazar por 0 para que se vea.
    tabla['AUC (%)'] = tabla['AUC (%)'].fillna(0)
    tabla['F1 (%)']  = tabla['F1 (%)'].fillna(0)

    # Altura fija: 35px por fila + ~40px de header. Evita recortes en tablas
    # con muchas filas (p.ej. vía de acceso con 10-12 categorías).
    altura_tabla = 40 + 35 * len(tabla)

    # NOTA: el expander "📋 Ver tabla detallada" se renderiza AL FINAL del
    # bloque (después del gráfico y del veredicto) para no pisar el gráfico
    # cuando se abre. Ver bloque al final de esta función.

    # --- Gráfico de barras agrupadas: métricas clave por grupo ---
    # Solo grupos fiables en el gráfico (evita barras de 100% artificiales)
    tabla_fiable = tabla[tabla['N alumnos'] >= MIN_N_GRUPO].copy()
    tabla_graf   = tabla_fiable if len(tabla_fiable) >= 2 else tabla

    metricas_plot = ['Precisión (%)', 'Recall (%)', 'F1 (%)']
    fig = go.Figure()

    # -------------------------------------------------------------------
    # PALETA POR TIPO DE VARIABLE
    # Plan unificado (Chat p05 · abril 2026):
    #   · Rama      → COLORES_RAMAS oficiales (ya alineado con config_app)
    #   · Sexo      → Azul UJI #1e4d8c (H) + Rosa #E15F99 (M) — coherente p01
    #   · Beca      → semáforo verde/ámbar/rojo por intensidad de apoyo
    #   · País      → semáforo verde/ámbar/rojo por riesgo cultural/administrativo
    #   · Orden     → gradiente azul→rojo (preferencia → forzado)
    #   · Provincia → 3 tonos neutros (no hay orden natural)
    #   · Vía acceso→ paleta categórica amplia (10+ colores, no hay orden)
    # Los mapeos se hacen por NOMBRE DE GRUPO, no por índice, para que
    # cambios en el orden alfabético no rompan la semántica.
    # -------------------------------------------------------------------
    def _color_para_grupo(nombre_grupo: str, idx_fallback: int) -> str:
        g = str(nombre_grupo).strip()
        g_low = g.lower()

        if titulo == "Rama de conocimiento":
            # Mapeo bidireccional: probamos ambos lados (por si el df tiene
            # código o nombre legible).
            # 1) Intento directo por código: EX, HU, SA, SO, TE
            if g in COLORES_RAMAS:
                return COLORES_RAMAS[g]
            # 2) Intento por nombre legible → código → color
            nombre_a_codigo = {v.lower(): k for k, v in RAMAS_NOMBRES.items()}
            codigo = nombre_a_codigo.get(g_low)
            if codigo and codigo in COLORES_RAMAS:
                return COLORES_RAMAS[codigo]
            # 3) Coincidencia parcial (por si cambia la cadena "y" vs "i")
            for nombre_legible, cod in nombre_a_codigo.items():
                if nombre_legible.split()[0] in g_low:
                    return COLORES_RAMAS.get(cod, COLORES['primario'])
            return COLORES['primario']

        if titulo == "Sexo":
            # Plan unificado: Azul UJI #1e4d8c = Hombre, Rosa #E15F99 = Mujer
            # Coherente con p01 (retrato descriptivo).
            # Acepta nombre completo ("Hombre"/"Mujer") o código ("H"/"M").
            if g_low.startswith('mujer') or g_low == 'm':
                return '#E15F99'
            if g_low.startswith('hombre') or g_low == 'h':
                return '#1e4d8c'
            return '#1e4d8c'  # fallback neutro UJI

        if titulo == "Situación de beca":
            if 'sostenida' in g_low:
                return COLORES_RIESGO['bajo']
            if 'puntual' in g_low:
                return COLORES_RIESGO['medio']
            return COLORES_RIESGO['alto']

        if titulo == "País de origen":
            if g_low.startswith('españa') or g_low.startswith('espa'):
                return COLORES_RIESGO['bajo']
            if 'ue' in g_low and 'no' in g_low:
                return COLORES_RIESGO['medio']
            return COLORES_RIESGO['alto']

        if titulo == "Provincia":
            # Gradiente azul UJI oficial (sin grises):
            # Castelló (arraigo local) → València (cercana) → Otras (lejana)
            if 'castell' in g_low:
                return '#1e4d8c'   # azul UJI oficial
            if 'val' in g_low:
                return '#3182ce'   # azul principal proyecto
            return '#7FB3E0'       # azul claro derivado

        if titulo == "Residencia":
            # Gradiente azul UJI oficial:
            # En Castelló (arraigo protector) → Fuera (desplazado)
            if 'en castell' in g_low or g_low == 'en castelló':
                return '#1e4d8c'   # azul UJI oficial
            if 'fuera' in g_low:
                return '#3182ce'   # azul principal proyecto
            return '#7FB3E0'       # fallback azul claro

        if titulo == "Orden de preferencia":
            # Azul UJI oscuro (1ª opción) → azul principal (2ª) → ámbar (3ª-5ª) → rojo (6ª+)
            # Gradiente "preferencia → forzado" coherente con paleta oficial proyecto.
            if '1' in g:
                return '#1e4d8c'   # azul UJI oficial
            if '2' in g:
                return '#3182ce'   # azul principal proyecto
            if '3' in g or '5' in g:
                return '#F59E0B'   # ámbar
            if '6' in g:
                return '#DC2626'   # rojo
            return '#94A3B8'

        # Default: paleta categórica
        paleta_cat = ['#2563EB', '#DC2626', '#059669', '#D97706',
                      '#7C3AED', '#0891B2', '#DB2777', '#65A30D',
                      '#EA580C', '#475569', '#1e4d8c']
        return paleta_cat[idx_fallback % len(paleta_cat)]

    # Calcular número de grupos PRIMERO para ajustar tamaño de texto y leyenda.
    # Con muchos grupos las barras son más estrechas y los % se solapan.
    n_grupos_leg = len(tabla_graf)
    if n_grupos_leg >= 8:
        text_size = 8
        legend_y = -0.36
        margin_b = 135
        height_graf = 300
    elif n_grupos_leg >= 6:
        text_size = 9
        legend_y = -0.32
        margin_b = 125
        height_graf = 290
    elif n_grupos_leg >= 4:
        text_size = 10
        legend_y = -0.24
        margin_b = 100
        height_graf = 275
    else:
        text_size = 11
        legend_y = -0.18
        margin_b = 70
        height_graf = 260

    max_val = 0.0
    for i, fila in tabla_graf.reset_index(drop=True).iterrows():
        vals = [fila[m] for m in metricas_plot]
        max_val = max(max_val, max(v for v in vals if pd.notna(v)))
        color_bar = _color_para_grupo(fila[col_grupo], i)
        fig.add_trace(go.Bar(
            name=str(fila[col_grupo]),
            x=metricas_plot,
            y=vals,
            marker_color=color_bar,
            text=[f"<b>{v:.1f}%</b>" for v in vals],
            textposition='outside',
            textfont=dict(size=text_size, color='#1a1a1a'),
            cliponaxis=False,
            constraintext='none',
            hovertemplate=f"<b>{fila[col_grupo]}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    # Línea de referencia F1 global del modelo — leída de metricas_modelo.json
    _met = _leer_metricas_modelo()
    f1_global_pct = float(_met.get("f1", 0.0)) * 100 if _met.get("f1") else 79.9

    f1_global_str = f"{f1_global_pct:.1f}".replace('.', ',')
    fig.add_hline(
        y=f1_global_pct,
        line_dash="dot",
        line_color=COLORES['texto_suave'],
        line_width=1.5,
        annotation_text=f"F1 global ({f1_global_str}%)",
        annotation_position="right",
        annotation_font_size=10,
    )

    # Eje Y dinámico — nunca hay overflow aunque algún grupo llegue a 100%
    y_max = max(105.0, min(max_val * 1.10, 108.0))

    fig.update_layout(
        barmode='group',
        yaxis=dict(range=[0, y_max], ticksuffix='%'),
        yaxis_title="Valor (%)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=legend_y,
                    xanchor="center", x=0.5, font=dict(size=9)),
        margin=dict(l=35, r=15, t=15, b=margin_b),
        height=height_graf,
        font=dict(size=10),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORES['borde'])

    # Calcular grupos pequeños para caption y para la nota dentro de tabla
    grupos_pequenos = df_met[df_met.get('grupo_pequeno', False) == True][col_grupo].tolist() \
        if 'grupo_pequeno' in df_met.columns else []

    if len(tabla_graf) < len(tabla):
        st.caption(
            f"Gráfico con grupos de N ≥ {MIN_N_GRUPO}. "
            f"Excluidos por tamaño insuficiente: {', '.join(str(g) for g in grupos_pequenos)}."
        )

    st.plotly_chart(fig, width='stretch')

    # Interpretación automática — basada solo en grupos fiables
    df_interp = tabla_fiable if len(tabla_fiable) >= 2 else tabla
    if 'F1 (%)' in df_interp.columns and len(df_interp) >= 2:
        f1_vals     = df_interp['F1 (%)'].values
        dif_f1      = f1_vals.max() - f1_vals.min()
        grupo_mejor = str(df_interp.loc[df_interp['F1 (%)'].idxmax(), col_grupo])
        grupo_peor  = str(df_interp.loc[df_interp['F1 (%)'].idxmin(), col_grupo])

        if dif_f1 < 5:
            msg   = f"✅ El modelo muestra un rendimiento <strong>homogéneo</strong> entre grupos de {titulo.lower()} (diferencia F1: {dif_f1:.1f}".replace('.', ',') + " pp)."
            color = COLORES['exito']
        elif dif_f1 < 10:
            dif_str = f"{dif_f1:.1f}".replace('.', ',')
            msg   = (
                f"⚠️ Hay una diferencia <strong>moderada</strong> de rendimiento entre grupos de {titulo.lower()} "
                f"(diferencia F1: {dif_str} pp). "
                f"El modelo funciona mejor en <strong>{grupo_mejor}</strong> que en <strong>{grupo_peor}</strong>."
            )
            color = COLORES['advertencia']
        else:
            dif_str = f"{dif_f1:.1f}".replace('.', ',')
            msg   = (
                f"🔴 Hay una diferencia <strong>notable</strong> de rendimiento entre grupos de {titulo.lower()} "
                f"(diferencia F1: {dif_str} pp). "
                f"El grupo <strong>{grupo_peor}</strong> está significativamente menos protegido. Requiere atención."
            )
            color = COLORES['abandono']

        # Nota contextual para beca: diferencia estructural, no sesgo del modelo
        nota_extra = ""
        if titulo == "Situación de beca" and dif_f1 > 5:
            nota_extra = (
                f"<br><em style='font-size:0.75rem; color:{COLORES['texto_suave']}'>"
                "Nota: los becarios tienen una tasa de abandono real mucho más baja, "
                "por eso el modelo los detecta menos como positivos. "
                "No indica sesgo discriminatorio.</em>"
            )

        st.markdown(f"""
        <div style="
            background: {color}12;
            border-left: 4px solid {color};
            border-radius: 6px;
            padding: 0.55rem 0.8rem;
            font-size: 0.8rem;
            margin-top: 0.3rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            min-height: 3.5em;
        ">{msg}{nota_extra}</div>
        """, unsafe_allow_html=True)

    # --- Tabla detallada DESPUÉS del gráfico y veredicto ---
    # Se coloca al final del bloque para que al expandirla no pise el gráfico,
    # respetando la estructura natural "gráfico → veredicto → datos de apoyo".
    with st.expander("📋 Ver tabla detallada", expanded=False):
        st.dataframe(
            tabla,
            width='stretch',
            height=altura_tabla,
            hide_index=True,
            column_config={
                'F1 (%)': st.column_config.ProgressColumn(
                    'F1 (%)', min_value=0, max_value=100, format='%.1f%%'
                ),
                'AUC (%)': st.column_config.ProgressColumn(
                    'AUC (%)', min_value=0, max_value=100, format='%.1f%%'
                ),
            }
        )

        # Aviso grupos pequeños — dentro del expander (es info de la tabla)
        if grupos_pequenos:
            nombres_gp = ', '.join(str(g) for g in grupos_pequenos)
            st.markdown(f"""
            <div style="font-size:0.78rem; color:{COLORES['texto_suave']};
                        margin-top:0.3rem;">
                ⚠️ <em>Grupos con N &lt; {MIN_N_GRUPO} (resultados poco estables):
                {nombres_gp}</em>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# BLOQUE 6: Disparate Impact
# =============================================================================

def _bloque_disparate_impact(df: pd.DataFrame, grupos_disponibles: list):
    """
    Calcula el Disparate Impact para todos los grupos sensibles disponibles.
    Métrica estándar: ratio entre tasa de predicción positiva del grupo
    menos favorecido vs el más favorecido.
    Regla del 80%: DI < 0.8 indica posible discriminación estadística.
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.3rem;">
        📐 Brecha de predicción entre grupos
        <span style="font-size: 0.7rem; font-weight: normal;
                     color: {COLORES['texto_suave']};">
            (Disparate Impact)
        </span>
    </h4>
    <p style="font-size: 0.85rem; color: {COLORES['texto_suave']}; margin-bottom: 1rem;">
        Ratio entre la tasa de predicción positiva (riesgo alto) del grupo
        menos favorecido respecto al más favorecido.
        <strong>Valor ideal: cercano a 1.0. Señal de alerta: por debajo de 0.8</strong>
        (regla del 80%, estándar internacional de fairness).
    </p>
    """, unsafe_allow_html=True)

    # Filtrar grupos que tienen columna disponible en df
    grupos_validos = [g for g in grupos_disponibles
                      if g["col_real"] in df.columns and 'pred_abandono' in df.columns]

    if not grupos_validos:
        st.info("No hay datos suficientes para calcular el Disparate Impact.")
        return

    # Distribuir en columnas (máx 4)
    n_cols = min(len(grupos_validos), 4)
    cols   = st.columns(n_cols, vertical_alignment="top")

    for col_ui, g in zip(cols, grupos_validos):
        col_real = g["col_real"]
        titulo   = g["titulo"]

        with col_ui:
            # Contar N por grupo para poder filtrar los pequeños
            n_por_grupo = df.groupby(col_real).size()

            # Calcular tasa de predicción positiva solo en grupos fiables
            grupos_fiables = n_por_grupo[n_por_grupo >= MIN_N_GRUPO].index.tolist()
            df_fiable = df[df[col_real].isin(grupos_fiables)]

            tasas = (
                df_fiable.groupby(col_real)['pred_abandono']
                .mean()
                .sort_values()
                .dropna()
            )

            if len(tasas) < 2:
                st.markdown(f"""
                <div style="
                    background: {COLORES['fondo']};
                    border: 1px solid {COLORES['borde']};
                    border-radius: 8px;
                    padding: 0.9rem 1rem;
                    font-size: 0.82rem;
                    color: {COLORES['texto_suave']};
                    text-align: center;
                ">
                    <strong>{titulo}</strong><br>
                    Menos de 2 grupos con N ≥ {MIN_N_GRUPO}.<br>
                    No se puede calcular un DI fiable.
                </div>
                """, unsafe_allow_html=True)
                continue

            # Si la tasa máxima es 0, DI no está definido (raro tras filtrar)
            if tasas.iloc[-1] == 0:
                st.markdown(f"""
                <div style="
                    background: {COLORES['fondo']};
                    border: 1px solid {COLORES['borde']};
                    border-radius: 8px;
                    padding: 0.9rem 1rem;
                    font-size: 0.82rem;
                    color: {COLORES['texto_suave']};
                    text-align: center;
                ">
                    <strong>{titulo}</strong><br>
                    Ningún grupo tiene predicciones positivas.<br>
                    DI no está definido.
                </div>
                """, unsafe_allow_html=True)
                continue

            di        = tasas.iloc[0] / tasas.iloc[-1]
            grupo_min = str(tasas.index[0])
            grupo_max = str(tasas.index[-1])

            if di >= 0.8:
                color_di  = COLORES['exito']
                texto_di  = "✅ Dentro del umbral"
            elif di >= 0.6:
                color_di  = COLORES['advertencia']
                texto_di  = "⚠️ Brecha moderada"
            else:
                color_di  = COLORES['abandono']
                texto_di  = "🔴 Brecha significativa"

            di_str = f"{di:.3f}".replace('.', ',')

            fig = go.Figure(go.Indicator(
                mode="gauge",
                value=round(di, 3),
                gauge={
                    'axis': {
                        'range': [0, 1],
                        'tickvals': [0, 0.6, 0.8, 1.0],
                        'ticktext': ['0', '0,6', '0,8', '1,0'],
                    },
                    'bar': {'color': color_di, 'thickness': 0.3},
                    'steps': [
                        {'range': [0.0, 0.6], 'color': 'rgba(229,62,62,0.12)'},
                        {'range': [0.6, 0.8], 'color': 'rgba(214,158,46,0.12)'},
                        {'range': [0.8, 1.0], 'color': 'rgba(56,161,105,0.12)'},
                    ],
                    'threshold': {
                        'line': {'color': COLORES['texto'], 'width': 2},
                        'thickness': 0.75,
                        'value': 0.8,
                    },
                },
                title={
                    'text': f"DI por {titulo}",
                    'font': {'size': 13}
                },
            ))
            # Añadir el valor numérico como anotación (con coma decimal española)
            fig.add_annotation(
                x=0.5, y=0.2,
                xref="paper", yref="paper",
                text=f"<b>{di_str}</b>",
                showarrow=False,
                font=dict(size=28, color=color_di),
            )
            fig.update_layout(
                paper_bgcolor="white",
                margin=dict(l=20, r=20, t=40, b=10),
                height=200,
            )
            st.plotly_chart(fig, width='stretch')

            # Info min/max + veredicto, en HTML para poder mostrar nombres largos
            st.markdown(f"""
            <div style="text-align: center; margin-top: -0.4rem;">
                <div style="font-size: 0.78rem; color: {COLORES['texto_suave']};
                            line-height: 1.4; margin-bottom: 0.3rem;">
                    Menor tasa pred.: <strong>{grupo_min}</strong><br>
                    Mayor tasa pred.: <strong>{grupo_max}</strong>
                </div>
                <div style="font-size: 0.82rem; color: {color_di}; font-weight: bold;">
                    {texto_di}
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# BLOQUE 7: Matriz de confusión por grupo
# =============================================================================

def _bloque_confusion_por_grupo(df: pd.DataFrame, grupos_disponibles: list):
    """
    Muestra los falsos positivos y falsos negativos por grupo.
    Pregunta clave: ¿a quién perjudica más el modelo cuando se equivoca?

    Falso positivo (FP): alumno que NO abandona pero el modelo predice que sí
    → intervención innecesaria, puede estigmatizar al alumno

    Falso negativo (FN): alumno que SÍ abandona pero el modelo no lo detecta
    → alumno en riesgo sin apoyo
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.5rem;">
        🔍 ¿A quién perjudica el modelo cuando se equivoca?
    </h4>
    <p style="font-size: 0.85rem; color: {COLORES['texto_suave']}; margin-bottom: 1rem;">
        <strong>Falso positivo (FP):</strong> el modelo predice abandono pero el alumno completa el grado
        → intervención innecesaria.<br>
        <strong>Falso negativo (FN):</strong> el alumno abandona pero el modelo no lo detecta
        → alumno sin apoyo.
    </p>
    """, unsafe_allow_html=True)

    # Opciones de grupo disponibles
    opciones = {g["titulo"]: g["col_real"] for g in grupos_disponibles
                if g["col_real"] in df.columns}

    if not opciones:
        st.info("No hay variables de grupo disponibles para este análisis.")
        return

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        grupo_sel = st.selectbox(
            label="Analizar errores por:",
            options=list(opciones.keys()),
            key="grupo_confusion",
        )

    col_real = opciones[grupo_sel]

    if col_real not in df.columns or 'abandono' not in df.columns:
        st.info("Datos no disponibles para este análisis.")
        return

    grupos      = sorted(df[col_real].dropna().unique(), key=lambda x: str(x))
    datos_fp_fn = []

    for g in grupos:
        df_g = df[df[col_real] == g]
        if len(df_g) < 5:
            continue
        y_true = df_g['abandono'].values
        y_pred = df_g['pred_abandono'].values
        tn, fp, fn, tp = (
            confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            if len(np.unique(y_true)) > 1 else (0, 0, 0, 0)
        )
        n = len(df_g)
        datos_fp_fn.append({
            'grupo':  g,
            'FP (%)': round(fp / n * 100, 1),
            'FN (%)': round(fn / n * 100, 1),
            'TP (%)': round(tp / n * 100, 1),
            'TN (%)': round(tn / n * 100, 1),
            'N':      n,
        })

    if not datos_fp_fn:
        st.info("No hay suficientes datos para este análisis.")
        return

    df_conf = pd.DataFrame(datos_fp_fn)

    fig = go.Figure()
    for tipo, color, descripcion in [
        ('FP (%)', COLORES['advertencia'], 'Falsos positivos'),
        ('FN (%)', COLORES['abandono'],    'Falsos negativos'),
        ('TP (%)', COLORES['exito'],       'Verdaderos positivos'),
    ]:
        fig.add_trace(go.Bar(
            name=descripcion,
            x=df_conf['grupo'],
            y=df_conf[tipo],
            marker_color=color,
            text=df_conf[tipo].apply(lambda x: f"{x:.1f}%"),
            textposition='auto',
            hovertemplate=f"<b>%{{x}}</b><br>{descripcion}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        barmode='group',
        yaxis_title="% sobre total del grupo",
        yaxis=dict(ticksuffix='%'),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5, font=dict(size=11)),
        margin=dict(l=40, r=20, t=50, b=80),
        height=320,
    )
    fig.update_xaxes(showgrid=False, tickangle=-25)
    fig.update_yaxes(showgrid=True, gridcolor=COLORES['borde'])

    st.plotly_chart(fig, width='stretch')
    st.caption(
        "💡 Un porcentaje de FN alto significa que el modelo deja sin detectar "
        "a muchos alumnos en riesgo de ese grupo. Un FP alto implica más "
        "intervenciones innecesarias."
    )


# =============================================================================
# BLOQUE 8: Simulador de política institucional ★
# =============================================================================

def _bloque_simulador_politica(df: pd.DataFrame):
    """
    Permite al gestor o al tribunal ajustar el umbral de decisión del modelo
    y ver en tiempo real cómo cambia el impacto institucional:
    - Cuántos alumnos se detectan como en riesgo
    - Cuántos son falsos positivos (intervención innecesaria)
    - Cuántos son falsos negativos (alumnos sin apoyo)
    - Coste estimado de intervención

    Este bloque transforma el análisis técnico en una herramienta de
    apoyo a la toma de decisiones institucionales reales.
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.3rem;">
        🎛️ Simulador de política institucional
        <span style="
            font-size: 0.7rem;
            background: {COLORES['primario']};
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 10px;
            margin-left: 0.5rem;
            vertical-align: middle;
        ">★ Extra</span>
    </h4>
    <p style="font-size: 0.85rem; color: {COLORES['texto_suave']}; margin-bottom: 1rem;">
        ¿Qué pasa si la UJI decide intervenir con todos los alumnos que superen
        un umbral de riesgo determinado? Ajusta el umbral y ve el impacto en
        tiempo real. Esto permite encontrar el equilibrio entre detectar más
        casos (recall alto) y no saturar los servicios de orientación (pocos FP).
    </p>
    """, unsafe_allow_html=True)

    if 'abandono' not in df.columns or 'prob_abandono' not in df.columns:
        st.info("Datos no disponibles para el simulador.")
        return

    col_ctrl, col_coste = st.columns([2, 1])

    with col_ctrl:
        umbral_sim = st.slider(
            label="Umbral de intervención (probabilidad de riesgo)",
            min_value=0.10,
            max_value=0.90,
            value=UMBRAL_CLASIFICACION,
            step=0.05,
            format="%.2f",
            help=(
                "Si el modelo predice una probabilidad de abandono mayor que "
                "este valor, el alumno recibirá una intervención de apoyo. "
                f"Umbral de decisión del modelo: {UMBRAL_CLASIFICACION:.2f} "
                "(regla estándar de clasificación binaria)."
            ),
            key="umbral_simulador"
        )

    with col_coste:
        coste_intervencion = st.number_input(
            label="Coste estimado por intervención (€)",
            min_value=0,
            max_value=5000,
            value=150,
            step=50,
            help=(
                "Coste aproximado de una sesión de tutoría o intervención "
                "de orientación académica por alumno. Valor orientativo."
            ),
            key="coste_intervencion"
        )

    y_true      = df['abandono'].values
    y_prob      = df['prob_abandono'].values
    y_pred_sim  = (y_prob >= umbral_sim).astype(int)

    n_total          = len(df)
    n_intervencion   = y_pred_sim.sum()
    n_fp             = ((y_pred_sim == 1) & (y_true == 0)).sum()
    n_fn             = ((y_pred_sim == 0) & (y_true == 1)).sum()
    n_tp             = ((y_pred_sim == 1) & (y_true == 1)).sum()
    coste_total      = n_intervencion * coste_intervencion
    recall_sim       = n_tp / max(y_true.sum(), 1) * 100
    precision_sim    = n_tp / max(n_intervencion, 1) * 100
    pct_intervencion = n_intervencion / n_total * 100

    c1, c2, c3, c4, c5 = st.columns(5, vertical_alignment="top")

    pct_int_str  = f"{pct_intervencion:.1f}".replace('.', ',')
    recall_str   = f"{recall_sim:.1f}".replace('.', ',')
    fp_pct_str   = f"{n_fp/n_total*100:.1f}".replace('.', ',')
    fn_pct_str   = f"{n_fn/y_true.sum()*100:.1f}".replace('.', ',')

    # Helper para renderizar KPI cards con borde lateral de color
    def _kpi_card(titulo: str, valor: str, delta: str, color: str) -> str:
        return f"""
        <div style="background: white;
                    border: 1px solid {COLORES['borde']};
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 0.7rem 0.9rem;
                    min-height: 110px;">
            <div style="font-size: 0.78rem; color: {COLORES['texto_suave']};
                        margin-bottom: 0.3rem; font-weight: 500;">
                {titulo}
            </div>
            <div style="font-size: 1.55rem; font-weight: 700;
                        color: {COLORES['texto']}; line-height: 1.1;
                        margin-bottom: 0.3rem;">
                {valor}
            </div>
            <div style="font-size: 0.72rem; color: {color};
                        font-weight: 500;">
                {delta}
            </div>
        </div>
        """

    with c1:
        st.markdown(_kpi_card(
            "🔔 Alumnos a intervenir",
            f"{n_intervencion:,}".replace(',', '.'),
            f"{pct_int_str}% del total",
            COLORES['advertencia'],
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi_card(
            "✅ Detectados correctamente",
            f"{n_tp:,}".replace(',', '.'),
            f"Recall: {recall_str}%",
            COLORES['exito'],
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi_card(
            "⚠️ Falsas alarmas (FP)",
            f"{n_fp:,}".replace(',', '.'),
            f"{fp_pct_str}% del total",
            COLORES['advertencia'],
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi_card(
            "❌ Abandonos no detectados",
            f"{n_fn:,}".replace(',', '.'),
            f"{fn_pct_str}% de los que abandonan",
            COLORES['abandono'],
        ), unsafe_allow_html=True)
    with c5:
        st.markdown(_kpi_card(
            "💶 Coste estimado",
            f"{coste_total:,.0f}".replace(',', '.') + " €",
            f"{coste_intervencion} €/alumno",
            COLORES['primario'],
        ), unsafe_allow_html=True)

    # Curva recall/precisión en función del umbral
    umbrales_rango = np.arange(0.05, 0.96, 0.02)
    recalls, precisiones, n_interv = [], [], []

    for u in umbrales_rango:
        y_p = (y_prob >= u).astype(int)
        tp  = ((y_p == 1) & (y_true == 1)).sum()
        recalls.append(tp / max(y_true.sum(), 1) * 100)
        precisiones.append(tp / max(y_p.sum(), 1) * 100)
        n_interv.append(y_p.sum())

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=umbrales_rango,
        y=recalls,
        name='Recall (% abandonos detectados)',
        line=dict(color=COLORES['exito'], width=2.5),
        hovertemplate="Umbral: %{x:.2f}<br>Recall: %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=umbrales_rango,
        y=precisiones,
        name='Precisión (% intervenciones acertadas)',
        line=dict(color=COLORES['primario'], width=2.5),
        hovertemplate="Umbral: %{x:.2f}<br>Precisión: %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=umbrales_rango,
        y=[n / n_total * 100 for n in n_interv],
        name='% alumnos a intervenir',
        line=dict(color=COLORES['advertencia'], width=1.5, dash='dash'),
        hovertemplate="Umbral: %{x:.2f}<br>Intervenciones: %{y:.1f}%<extra></extra>",
        yaxis='y2',
    ))

    fig.add_vline(
        x=umbral_sim,
        line_color=COLORES['abandono'],
        line_width=2,
        line_dash="solid",
        annotation_text=f"  Umbral actual ({umbral_sim:.2f})",
        annotation_font_color=COLORES['abandono'],
        annotation_font_size=11,
    )

    fig.update_layout(
        xaxis_title="Umbral de decisión",
        yaxis_title="Porcentaje (%)",
        yaxis=dict(range=[0, 105], ticksuffix='%'),
        yaxis2=dict(
            title="% alumnos a intervenir",
            overlaying='y',
            side='right',
            range=[0, 105],
            ticksuffix='%',
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=60, t=40, b=40),
        height=360,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORES['borde'])
    fig.update_yaxes(showgrid=True, gridcolor=COLORES['borde'])

    st.plotly_chart(fig, width='stretch')
    st.caption(
        "💡 Mueve el slider para encontrar el equilibrio óptimo entre detectar "
        "el máximo de abandonos (recall alto) y no saturar los servicios de "
        "orientación (precisión alta, pocas falsas alarmas)."
    )


# =============================================================================
# BLOQUE 9: Conclusión y limitaciones
# =============================================================================

def _bloque_conclusion(df: pd.DataFrame, grupos_disponibles: list):
    """
    Conclusión directa y honesta sobre la equidad del modelo.
    Los datos citados se calculan DINÁMICAMENTE sobre el mismo df que el
    resto de la página. No hay texto hardcoded con cifras: si el modelo
    cambia o se re-entrena, la conclusión se actualiza automáticamente.
    """
    st.markdown(f"""
    <h4 style="color: {COLORES['texto']}; margin-bottom: 0.8rem;">
        📝 Conclusión: ¿Es justo el modelo?
    </h4>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Calcular resultados reales para la conclusión
    # ------------------------------------------------------------------
    nombres_grupos = [g["titulo"] for g in grupos_disponibles
                      if g["col_real"] in df.columns]

    # Recorre cada grupo sensible y computa DI + diferencia F1
    resumen_por_grupo = []
    for g in grupos_disponibles:
        col_real = g["col_real"]
        if col_real not in df.columns or 'pred_abandono' not in df.columns:
            continue

        # Disparate Impact: ratio tasa_pred_min / tasa_pred_max
        tasas = (df.groupby(col_real)['pred_abandono']
                   .mean().sort_values().dropna())
        di = (tasas.iloc[0] / tasas.iloc[-1]) if (len(tasas) >= 2 and tasas.iloc[-1] > 0) else np.nan

        # Diferencia F1 entre grupos fiables (N >= MIN_N_GRUPO)
        f1_vals = []
        for v in df[col_real].dropna().unique():
            df_g = df[df[col_real] == v]
            if len(df_g) < MIN_N_GRUPO or 'abandono' not in df_g.columns:
                continue
            if len(np.unique(df_g['abandono'])) < 2:
                continue
            f1_vals.append(f1_score(df_g['abandono'], df_g['pred_abandono'],
                                    zero_division=0))
        dif_f1 = (max(f1_vals) - min(f1_vals)) * 100 if len(f1_vals) >= 2 else np.nan

        resumen_por_grupo.append({
            'titulo': g['titulo'],
            'di':     di,
            'dif_f1': dif_f1,
        })

    # Clasificar severidad
    dis_pasan = [r for r in resumen_por_grupo if pd.notna(r['di']) and r['di'] >= 0.8]
    dis_alerta = [r for r in resumen_por_grupo if pd.notna(r['di']) and r['di'] < 0.8]
    peor_di = min((r for r in resumen_por_grupo if pd.notna(r['di'])),
                  key=lambda r: r['di'], default=None)
    peor_f1 = max((r for r in resumen_por_grupo if pd.notna(r['dif_f1'])),
                  key=lambda r: r['dif_f1'], default=None)

    # Veredicto global: tono y mensaje en función de los resultados
    # Métricas leídas del JSON (modelo final dinámico) — se reutiliza más abajo
    _met = _leer_metricas_modelo()
    _modelo_nom = _met.get("modelo_nombre", "final")
    if not dis_alerta and (peor_f1 is None or peor_f1['dif_f1'] < 10):
        color_vered = COLORES['exito']
        icono_vered = "✅"
        titulo_vered = "Valoración general"
        msg_vered = (
            f"El modelo {_modelo_nom} muestra un comportamiento "
            f"<strong>razonablemente equitativo</strong> en los grupos analizados "
            f"({', '.join(nombres_grupos)}). "
            f"El Disparate Impact supera el umbral del 80% en todas las variables "
            f"sensibles analizadas, lo que indica que el modelo no presenta "
            f"señales sistemáticas de discriminación estadística."
        )
    elif dis_alerta and len(dis_alerta) < len(resumen_por_grupo):
        color_vered = COLORES['advertencia']
        icono_vered = "⚠️"
        titulo_vered = "Valoración matizada"
        variables_alerta = ", ".join(r['titulo'].lower() for r in dis_alerta)
        msg_vered = (
            f"El modelo se comporta de forma <strong>mayoritariamente equitativa</strong>, "
            f"pero muestra señales de posible discriminación estadística en "
            f"<strong>{variables_alerta}</strong> (Disparate Impact &lt; 0.8). "
            f"Este hallazgo no invalida el modelo pero exige supervisión explícita "
            f"en la toma de decisiones institucionales que lo empleen."
        )
    else:
        color_vered = COLORES['abandono']
        icono_vered = "🔴"
        titulo_vered = "Valoración con reservas"
        msg_vered = (
            f"El modelo presenta <strong>señales de inequidad</strong> en la mayoría "
            f"de variables sensibles analizadas. No se recomienda su uso institucional "
            f"sin aplicar antes técnicas de mitigación (re-muestreo, reponderación "
            f"o restricciones de equidad en el entrenamiento)."
        )

    # Datos concretos a citar (con coma decimal española)
    datos_citables = []
    if peor_di is not None:
        di_str = f"{peor_di['di']:.2f}".replace('.', ',')
        datos_citables.append(
            f"DI mínimo: <strong>{di_str}</strong> (en {peor_di['titulo'].lower()})"
        )
    if peor_f1 is not None and pd.notna(peor_f1['dif_f1']):
        diff_str = f"{peor_f1['dif_f1']:.1f}".replace('.', ',')
        datos_citables.append(
            f"diferencia F1 máxima: <strong>{diff_str} pp</strong> "
            f"(en {peor_f1['titulo'].lower()})"
        )
    # Métricas globales desde JSON (_met ya leído arriba)
    if _met.get("f1") and _met.get("auc"):
        f1_str  = f"{float(_met['f1'])*100:.1f}".replace('.', ',')
        auc_str = f"{float(_met['auc'])*100:.1f}".replace('.', ',')
        datos_citables.append(
            f"F1 global: <strong>{f1_str}%</strong>, "
            f"AUC: <strong>{auc_str}%</strong>"
        )
    datos_str = " · ".join(datos_citables) if datos_citables else ""

    # ------------------------------------------------------------------
    # CSS scoped: solo los expanders dentro de .expander-amarillo-conclusion
    # llevan el tono amarillo. El resto (p.ej. "Marco normativo") queda intacto.
    # ------------------------------------------------------------------
    st.markdown(f"""
    <style>
    /* Header del expander amarillo */
    div[data-testid="stExpander"]:has(.marca-exp-amarillo-concl) summary,
    .expander-amarillo-concl div[data-testid="stExpander"] summary {{
        background: {COLORES['advertencia']}10 !important;
        border: 1px solid {COLORES['advertencia']}40 !important;
        border-radius: 8px !important;
    }}
    /* Texto del label del expander amarillo */
    div[data-testid="stExpander"]:has(.marca-exp-amarillo-concl) summary p,
    .expander-amarillo-concl div[data-testid="stExpander"] summary p {{
        color: {COLORES['advertencia']} !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }}
    /* Caja interior del expander amarillo (al abrir) */
    div[data-testid="stExpander"]:has(.marca-exp-amarillo-concl) > details > div,
    .expander-amarillo-concl div[data-testid="stExpander"] > details > div {{
        background: {COLORES['advertencia']}10 !important;
        border: 1px solid {COLORES['advertencia']}40 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    col_concl, col_limit = st.columns([1, 1], vertical_alignment="top")

    with col_concl:
        st.markdown('<div class="expander-amarillo-concl">',
                    unsafe_allow_html=True)
        with st.expander(f"{icono_vered} {titulo_vered}", expanded=False):
            st.markdown(
                '<span class="marca-exp-amarillo-concl"></span>',
                unsafe_allow_html=True
            )
            st.markdown(f"""
            <div style="font-size: 0.85rem; color: {COLORES['texto']};
                        line-height: 1.7;">
                {msg_vered}<br><br>
                <span style="font-size: 0.8rem; color: {COLORES['texto_suave']};">
                    <strong>Datos clave del test (N = {f"{len(df):,}".replace(",", ".")} alumnos):</strong><br>{datos_str}
                </span><br><br>
                <em>Cualquier uso institucional debe ir acompañado de supervisión
                humana y revisión periódica.</em>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_limit:
        st.markdown('<div class="expander-amarillo-concl">',
                    unsafe_allow_html=True)
        with st.expander("⚠️ Limitaciones del análisis", expanded=False):
            st.markdown(
                '<span class="marca-exp-amarillo-concl"></span>',
                unsafe_allow_html=True
            )
            st.markdown(f"""
            <div style="font-size: 0.85rem; color: {COLORES['texto']};
                        line-height: 1.7;">
                <strong>1. Datos históricos:</strong> el modelo refleja los patrones
                de 2010–2020. Los cambios estructurales recientes (pandemia, nuevos
                grados) pueden no estar representados.<br><br>
                <strong>2. Censura temporal cohorte 2020:</strong> los 584 alumnos
                que iniciaron en 2020 tienen una ventana de observación inferior
                a 4 años (cierre del dataset en 2023), por lo que su tasa de
                abandono observada (0%) <strong>infraestima el valor real</strong>.
                La solución metodológica correcta (análisis de supervivencia
                Kaplan-Meier) se presenta de forma exploratoria al final de esta
                página y queda como línea de ampliación del TFM.<br><br>
                <strong>3. Equidad ≠ causalidad:</strong> que el modelo sea equitativo
                no significa que el sistema académico lo sea. El modelo aprende
                de desigualdades preexistentes en los datos.<br><br>
                <strong>4. Grupos pequeños:</strong> las estimaciones para grupos
                con N &lt; {MIN_N_GRUPO} tienen mayor varianza estadística y se
                excluyen de los gráficos comparativos, pero se listan en las tablas
                con un aviso.<br><br>
                <strong>5. Sin constraints de fairness en entrenamiento:</strong>
                el modelo no incorpora restricciones de equidad durante la
                optimización. Métodos como reweighting, exponentiated gradient o
                threshold optimization podrían mejorar la paridad entre grupos
                a costa de rendimiento global.<br><br>
                <strong>6. Uso ético obligatorio:</strong> esta herramienta es
                de apoyo a la decisión, nunca sustituto del juicio humano.
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Referencia al marco normativo
    with st.expander("📖 Marco normativo y referencias de fairness — clic para ampliar",
                     expanded=False):
        st.markdown(f"""
        <div style="font-size: 0.83rem; color: {COLORES['texto']}; line-height: 1.8;">

        <strong>Marco normativo aplicable:</strong><br>
        · Reglamento UE 2016/679 (RGPD) — protección de datos personales<br>
        · Reglamento UE 2024/1689 (AI Act) —
          sistemas de IA en educación clasificados como alto riesgo<br>
        · UNESCO Recommendation on the Ethics of AI (2021)<br><br>

        <strong>Métricas de fairness utilizadas:</strong><br>
        · Disparate Impact Ratio (Feldman et al., 2015)<br>
        · Equal Opportunity / Equalized Odds (Hardt et al., 2016)<br>
        · Análisis de FP/FN diferencial por subgrupos<br><br>

        <strong>Librería de referencia:</strong> fairlearn (Microsoft, 2020)<br>
        <strong>Umbral estándar:</strong> Disparate Impact ≥ 0.8
        (EEOC Four-Fifths Rule, adaptado a ML)

        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# FIN DE p05_equidad.py
# =============================================================================
