# =============================================================================
# loaders.py
# Módulo de carga de datos y modelos para la app Streamlit
#
# ¿QUÉ HACE ESTE FICHERO?
#   Contiene funciones que cargan desde disco los ficheros que necesita
#   la app: el modelo entrenado, el pipeline de preprocesamiento, los
#   valores SHAP, las métricas de fairness y los datos de test.
#
# ¿POR QUÉ ESTÁ SEPARADO DE main.py?
#   Por organización y reutilización. Cualquier página de la app puede
#   hacer "from utils.loaders import cargar_modelo" sin duplicar código.
#
# ¿QUÉ ES EL CACHÉ DE STREAMLIT? (concepto clave para novatas)
#   Recuerda que Streamlit re-ejecuta el script entero cada vez que
#   el usuario hace algo. Sin caché, cargaría el modelo desde disco
#   en cada clic — muy lento (el modelo pesa varios MB).
#
#   El decorador @st.cache_resource le dice a Streamlit:
#   "la primera vez que alguien llame a esta función, ejecuta el código
#   y guarda el resultado en memoria. Las siguientes veces, devuelve
#   directamente lo guardado sin volver a ejecutar nada."
#
#   Hay dos tipos de caché en Streamlit:
#   - @st.cache_resource → para objetos grandes que NO son datos:
#     modelos, pipelines, conexiones. Se comparte entre todos los usuarios.
#   - @st.cache_data     → para datos (DataFrames, listas, dicts).
#     Cada usuario tiene su propia copia en memoria.
#
# REQUISITOS:
#   - config_app.py debe estar en app/ (un nivel arriba)
#   - Los ficheros de modelo y datos deben existir en las rutas de RUTAS
#
# GENERA:
#   Funciones importables desde cualquier página de la app.
#
# SIGUIENTE:
#   utils/predictor.py — lógica de predicción usando modelo + pipeline
# =============================================================================

import sys
from pathlib import Path

import joblib        # para cargar ficheros .pkl (modelos y pipelines)
import pandas as pd  # para cargar ficheros .parquet (datos)
import streamlit as st  # necesario para los decoradores de caché

# ---------------------------------------------------------------------------
# Aseguramos que Python puede encontrar config_app.py
# ---------------------------------------------------------------------------
# config_app.py está en app/, y este fichero está en app/utils/.
# Python no sabe automáticamente que debe buscar un nivel arriba.
# Con esta línea le decimos: "busca también en la carpeta padre (app/)".
#
# Path(__file__)         → ruta a este fichero: .../app/utils/loaders.py
# .resolve().parent      → carpeta utils/
# .parent                → carpeta app/   ← aquí está config_app.py

_DIR_APP = Path(__file__).resolve().parent.parent
if str(_DIR_APP) not in sys.path:
    sys.path.insert(0, str(_DIR_APP))

from config_app import RUTAS  # importamos solo las rutas que necesitamos aquí

# =============================================================================
# MAPEO DE TITULACIONES — Planes curriculares antiguos → Titulación actual
# =============================================================================
# CONTEXTO: El dataset cubre cursos 2010–2020. Durante ese período, varias
# titulaciones cambiaron de plan curricular y aparecen con dos nombres:
# el antiguo (con año entre paréntesis) y el actual (sin paréntesis).
#
# DECISIÓN: En la app fusionamos los alumnos del plan antiguo con la
# titulación actual. Así la app muestra titulaciones vigentes y el
# análisis incluye TODOS los alumnos históricos de esa carrera.
#
# IMPORTANTE: El dataset original NO se modifica. cargar_meta_test()
# devuelve los datos tal cual. La fusión solo ocurre en cargar_meta_test_app(),
# que es la función que usan los gráficos y filtros de la app.
# Si en el futuro necesitas los planes antiguos por separado (para análisis
# de cambio de plan, comparativas históricas, etc.), usa cargar_meta_test().
#
# Titulaciones fusionadas (9 en total):
#   - Arquitectura Técnica (Plan 2020)                  →  8 alumnos
#   - Criminología y Seguridad (Plan 2020)              → 16 alumnos
#   - Historia y Patrimonio (Plan 2015)                 → 54 alumnos
#   - Ingeniería Agroalimentaria... (Plan 2018)         → 17 alumnos
#   - Maestro en Educación Infantil (Plan 2018)         → 94 alumnos
#   - Maestro en Educación Primaria (Plan 2018)         → 92 alumnos
#   - Medicina (Plan 2017)                              → 66 alumnos
#   - Ingeniería de la Edificación                      → 41 alumnos (cambio nombre)
#   - Doble Grado ADE y Derecho, (coma)                 → 22 alumnos (error datos)
# =============================================================================

import re as _re

_MAPEO_TITULACIONES = {
    # Cambios de plan curricular — plan antiguo → nombre actual
    "Grado en Arquitectura Técnica (Plan 2020)":                          "Grado en Arquitectura Técnica",
    "Grado en Criminologia y Seguridad  (Plan 2020)":                     "Grado en Criminologia y Seguridad",
    "Grado en Historia y Patrimonio (Plan 2015)":                         "Grado en Historia y Patrimonio",
    "Grado en Ingeniería Agroalimentaria y del Medio Rural (Plan 2018)":  "Grado en Ingeniería Agroalimentaria y del Medio Rural",
    "Grado en Maestro en Educación Infantil (Plan 2018)":                 "Grado en Maestro en Educación Infantil",
    "Grado en Maestro en Educación Primaria (Plan 2018)":                 "Grado en Maestro en Educación Primaria",
    "Grado en Medicina (Plan 2017)":                                      "Grado en Medicina",
    # Cambio de nombre — titulación renombrada
    "Grado en Ingeniería de la Edificación":                              "Grado en Arquitectura Técnica",
    # Error de datos — coma al final del nombre
    "Doble Grado en Administración y Dirección de Empresas y Derecho,":   "Doble Grado en Administración y Dirección de Empresas y Derecho",
}

def _fusionar_titulaciones(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Sustituye nombres de planes antiguos por el nombre actual.
    Solo afecta a la columna 'titulacion'. El resto del dataframe no cambia.
    """
    df = df.copy()
    if "titulacion" in df.columns:
        df["titulacion"] = df["titulacion"].replace(_MAPEO_TITULACIONES)
        # Limpiar comas sobrantes al final del nombre (error P09 del audit de calidad)
        df["titulacion"] = df["titulacion"].str.strip().str.rstrip(",").str.strip()
    return df



# =============================================================================
# FUNCIÓN 1: Cargar el modelo entrenado
# =============================================================================
# El modelo es un objeto CatBoostClassifier guardado con joblib en Fase 5.
# Pesa varios MB. Con @st.cache_resource solo se carga UNA vez por sesión.

@st.cache_resource(show_spinner="Cargando modelo de predicción...")
def cargar_modelo():
    """
    Carga el modelo CatBoost entrenado desde disco.

    Returns
    -------
    modelo : objeto CatBoostClassifier (o similar)
        El modelo listo para hacer predicciones con .predict() y
        .predict_proba().

    Raises
    ------
    FileNotFoundError
        Si el fichero .pkl no existe en la ruta esperada.
    """
    ruta = RUTAS["modelo"]

    # Comprobación amigable: si el fichero no existe, error claro
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en:\n{ruta}\n\n"
            "Posibles causas:\n"
            "  1) Falta ejecutar f6_m00_preparacion.ipynb (genera metricas_modelo.json\n"
            "     con el nombre del modelo ganador del sistema dinámico).\n"
            "  2) El .pkl del modelo ganador no está en data/05_modelado/models/.\n"
            "  3) Falta ejecutar Fase 5 completa para generar los .pkl."
        )

    # joblib.load() deserializa el objeto Python guardado en el .pkl
    modelo = joblib.load(ruta)
    return modelo


# =============================================================================
# FUNCIÓN 2: Cargar el pipeline de preprocesamiento
# =============================================================================
# El pipeline transforma los datos originales del usuario (con missing values,
# variables categóricas, escalas distintas) al formato que espera el modelo.
# SIEMPRE hay que aplicar el pipeline ANTES de llamar al modelo.

@st.cache_resource(show_spinner="Cargando pipeline de preprocesamiento...")
def cargar_pipeline():
    """
    Carga el pipeline de preprocesamiento entrenado desde disco.

    El pipeline incluye: imputación de valores perdidos, codificación
    de variables categóricas y escalado numérico.

    Returns
    -------
    pipeline : objeto sklearn Pipeline
        Listo para transformar datos con .transform().
    """
    ruta = RUTAS["pipeline"]

    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el pipeline en:\n{ruta}\n\n"
            "Verifica que el fichero pipeline_preprocesamiento.pkl "
            "está en data/05_modelado/"
        )

    pipeline = joblib.load(ruta)
    return pipeline


# =============================================================================
# FUNCIÓN 3: Cargar los datos de test con metadatos
# =============================================================================
# meta_test.parquet es el conjunto de test generado en f6_m00_preparacion.
# Contiene las features + metadatos (titulación, cohorte, rama, abandono real).
# Lo usamos para mostrar estadísticas reales en la app.

@st.cache_data(show_spinner="Cargando datos de evaluación...")
def cargar_meta_test() -> pd.DataFrame:
    """
    Carga el conjunto de test completo: features + metadatos.

    Combina dos ficheros generados en fases anteriores:
    - X_test_prep.parquet → 19 features preprocesadas (Fase 5)
    - meta_test.parquet   → metadatos: titulacion, rama, sexo, abandono (Fase 6)

    Ambos tienen 6.725 filas con el mismo índice, por lo que el join
    es directo por índice sin riesgo de mezclar filas.

    Returns
    -------
    df : pd.DataFrame
        DataFrame con features + metadatos listo para predicción y análisis.
    """
    ruta_meta  = RUTAS["meta_test"]
    ruta_xtest = RUTAS["X_test_prep"]

    for ruta, nombre in [(ruta_meta, "meta_test"), (ruta_xtest, "X_test_prep")]:
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró {nombre} en:\n{ruta}\n\n"
                "Verifica que las Fases 5 y 6 se han ejecutado correctamente."
            )

    # Cargamos los dos ficheros
    meta  = pd.read_parquet(ruta_meta)   # metadatos: titulacion, rama, abandono...
    xtest = pd.read_parquet(ruta_xtest)  # features: nota_acceso, n_anios_beca...

    # VERIFICACION DE SEGURIDAD: indices deben coincidir
    # Si Fase 5 se re-ejecuto sin re-ejecutar f6_m00_preparacion,
    # los indices no coincidiran y el join seria incorrecto.
    indices_xtest = set(xtest.index)
    indices_meta  = set(meta.index)
    if indices_xtest != indices_meta:
        raise ValueError(
            "ERROR CRITICO: Los indices de X_test_prep y meta_test no coinciden.\n"
            "Esto ocurre cuando se re-ejecuta Fase 5 sin re-ejecutar despues\n"
            "f6_m00_preparacion.ipynb.\n"
            "Solucion: ejecuta f6_m00_preparacion.ipynb y reinicia la app."
        )

    # -----------------------------------------------------------------------
    # JOIN POR INDICE POSICIONAL
    # -----------------------------------------------------------------------
    # Ambos ficheros tienen exactamente 6725 filas con el mismo indice.
    # El join es directo y seguro.
    #
    # PROBLEMA CONOCIDO: rama y sexo existen en los DOS ficheros.
    #   - En X_test_prep: rama está codificada numéricamente por OrdinalEncoder
    #   - En meta_test:   rama es texto legible ("Ingeniería", "Ciencias Sociales")
    # El join mantiene la de X_test_prep (numérica) y descarta la de meta_test.
    #
    # SOLUCIÓN: renombramos rama y sexo de meta_test antes del join
    # para que ambas versiones queden disponibles:
    #   rama      → versión numérica del pipeline (para predict_proba)
    #   rama_meta → versión legible para gráficos y filtros
    # -----------------------------------------------------------------------
    meta_join = meta.copy()
    # Renombramos columnas que existen en ambos para no perder la versión legible
    cols_renombrar = [c for c in ['rama', 'sexo', 'pais_nombre', 'provincia', 'via_acceso']
                      if c in meta_join.columns and c in xtest.columns]
    meta_join = meta_join.rename(columns={c: c + '_meta' for c in cols_renombrar})

    # Traducir abreviaturas de rama a nombres completos
    # EX→Ciencias Experimentales, HU→Artes y Humanidades, etc.
    # El mapeo viene de config_app.RAMAS_NOMBRES (igual que en Fase 4)
    if 'rama_meta' in meta_join.columns:
        from config_app import RAMAS_NOMBRES
        meta_join['rama_meta'] = meta_join['rama_meta'].map(RAMAS_NOMBRES).fillna(meta_join['rama_meta'])

    cols_solo_meta = [c for c in meta_join.columns if c not in xtest.columns]
    df = xtest.join(meta_join[cols_solo_meta])

    return df


# =============================================================================
# FUNCIÓN 4: Cargar los valores SHAP globales
# =============================================================================
# Los valores SHAP explican qué variables influyen más en las predicciones.
# Se calcularon en Fase 6 (f6_m01) sobre el modelo CatBoost.
# Son opcionales: si no existen, la app funciona igualmente sin ellos.

@st.cache_data(show_spinner="Cargando valores SHAP...")
def cargar_shap_global():
    """
    Carga los valores SHAP globales calculados en Fase 6.

    Returns
    -------
    shap_values : objeto shap.Explanation o None
        Los valores SHAP listos para visualizar.
        Devuelve None si el fichero no existe (en lugar de lanzar error),
        para que la app pueda funcionar aunque Fase 6 no esté completa.
    """
    ruta = RUTAS["shap_global"]

    if not ruta.exists():
        # Advertencia visible en la app, pero no error fatal
        st.warning(
            "⚠️ No se encontraron los valores SHAP. "
            "El análisis de importancia de variables no estará disponible. "
            f"Ruta esperada: {ruta}"
        )
        return None

    shap_values = joblib.load(ruta)
    return shap_values


# =============================================================================
# FUNCIÓN 5: Cargar las métricas de fairness (equidad)
# =============================================================================
# fairness_metricas.parquet contiene métricas de equidad por subgrupos
# (género, rama) calculadas en Fase 6 (f6_m05).
# También opcional: la pestaña de equidad la necesita, el resto no.

@st.cache_data(show_spinner="Cargando métricas de equidad...")
def cargar_fairness() -> pd.DataFrame | None:
    """
    Carga las métricas de fairness calculadas en Fase 6.

    Returns
    -------
    df : pd.DataFrame o None
        DataFrame con métricas de equidad por subgrupo.
        Devuelve None si el fichero no existe.
    """
    ruta = RUTAS["fairness"]

    if not ruta.exists():
        st.warning(
            "⚠️ No se encontraron las métricas de equidad. "
            "La pestaña de equidad no estará disponible. "
            f"Ruta esperada: {ruta}"
        )
        return None

    df = pd.read_parquet(ruta)
    return df


# =============================================================================
# FUNCIÓN 6: Cargar todo de una vez (función de conveniencia)
# =============================================================================
# En vez de llamar a las 5 funciones por separado, main.py puede llamar
# a esta única función al arrancar y obtenerlo todo.
# Como cada función individual ya tiene caché, no hay penalización
# por llamarla varias veces.

def cargar_todo() -> dict:
    """
    Carga todos los recursos necesarios para la app de una sola vez.

    Útil para el arranque inicial en main.py. Maneja errores de forma
    centralizada y devuelve un diccionario con todo disponible.

    Returns
    -------
    recursos : dict con claves:
        - "modelo"    : modelo CatBoost
        - "pipeline"  : pipeline sklearn
        - "meta_test" : DataFrame con datos de test
        - "shap"      : valores SHAP (o None)
        - "fairness"  : DataFrame fairness (o None)
        - "ok"        : True si los recursos críticos cargaron bien
        - "errores"   : lista de mensajes de error (vacía si todo ok)
    """
    recursos = {
        "modelo":    None,
        "pipeline":  None,
        "meta_test": None,
        "shap":      None,
        "fairness":  None,
        "ok":        False,
        "errores":   [],
    }

    # Recursos críticos: si fallan, la app no puede funcionar
    try:
        recursos["modelo"] = cargar_modelo()
    except FileNotFoundError as e:
        recursos["errores"].append(str(e))

    try:
        recursos["pipeline"] = cargar_pipeline()
    except FileNotFoundError as e:
        recursos["errores"].append(str(e))

    try:
        recursos["meta_test"] = cargar_meta_test()
    except FileNotFoundError as e:
        recursos["errores"].append(str(e))

    # Recursos opcionales: si fallan, la app funciona en modo reducido
    # (las funciones individuales ya muestran st.warning por su cuenta)
    recursos["shap"]     = cargar_shap_global()
    recursos["fairness"] = cargar_fairness()

    # La app está "ok" solo si los tres recursos críticos cargaron bien
    recursos["ok"] = len(recursos["errores"]) == 0

    return recursos



# =============================================================================
# FUNCIÓN 3b: Versión para la app — parquet unificado (sin joins en tiempo real)
# =============================================================================
# Carga meta_test_app.parquet generado por f6_m00b_preparacion_app.ipynb.
# Contiene: metadatos + features originales + flags _missing (6.725 × 34 cols).
# Es más rápido que cargar_meta_test() porque no requiere cruzar ficheros.
#
# USAR ESTA FUNCIÓN en todos los gráficos, filtros y ejemplos de la app.
# cargar_meta_test() se mantiene para compatibilidad y análisis históricos.

@st.cache_data(show_spinner="Cargando datos de evaluación...")
def cargar_meta_test_app() -> "pd.DataFrame":
    """
    Carga el fichero unificado meta_test_app.parquet para la app.

    Contiene metadatos + features originales + flags _missing en un único
    fichero. No requiere joins. Generado por f6_m00b_preparacion_app.ipynb.

    Si el fichero no existe (p.ej. en despliegue nuevo), recae en
    cargar_meta_test() con fusión de titulaciones como fallback.

    Returns
    -------
    df : pd.DataFrame  6.725 × 34 cols con titulaciones fusionadas
    """
    ruta = RUTAS.get("meta_test_app")

    # Ruta disponible y fichero existe → carga directa (camino rápido)
    if ruta is not None and ruta.exists():
        df = pd.read_parquet(ruta)
        return _fusionar_titulaciones(df)

    # Fallback: construir desde los ficheros base (más lento pero siempre funciona)
    st.warning(
        "⚠️ meta_test_app.parquet no encontrado. "
        "Ejecuta f6_m00b_preparacion_app.ipynb para generarlo. "
        "Usando fallback con join en tiempo real."
    )
    df = cargar_meta_test()
    return _fusionar_titulaciones(df)


# =============================================================================
# FIN DE loaders.py
#
# Para usar estas funciones desde una página de la app:
#   from utils.loaders import cargar_modelo, cargar_meta_test
#   modelo    = cargar_modelo()
#   meta_test = cargar_meta_test()
# =============================================================================
