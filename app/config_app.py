# =============================================================================
# config_app.py
# Fichero central de configuración de la app Streamlit
#
# ¿QUÉ HACE ESTE FICHERO?
#   Define en un único lugar todas las constantes, rutas y ajustes que
#   necesita la app. El resto de ficheros lo importan con:
#       from config_app import RUTAS, COLORES, APP_CONFIG
#   Así, si algo cambia (una ruta, un color), solo lo tocas aquí.
#
# ¿POR QUÉ ES LO PRIMERO QUE SE ESCRIBE?
#   Porque todos los demás ficheros dependen de él. Sin esta base,
#   cada fichero haría sus propias suposiciones y la app sería frágil.
#
# ORDEN DE SECCIONES:
#   1.  ROOT                — Localizar la carpeta raíz del proyecto
#   2.  APP_CONFIG          — Metadatos generales de la aplicación
#   3.  RUTAS               — Rutas a datos y modelos
#   4.  COLORES             — Paleta visual principal
#   5.  COLORES_RAMAS       — Paleta por rama de conocimiento
#   6.  COLORES_RIESGO      — Alias semántico para riesgo (no duplica hex)
#   7.  PESTAÑAS            — Definición de las páginas de la app
#   8.  UMBRALES            — Criterios para clasificar riesgo + muestra
#   9.  PARÁMETROS_ECONÓMICOS — Precio crédito UJI (editable en la app)
#   10. NOMBRES_VARIABLES   — Nombres legibles de features
#   11. VERIFICACIÓN        — Chequear ficheros críticos al arrancar
#   12. MAPAS_CODIFICACIÓN  — Texto legible ↔ código numérico del modelo
# =============================================================================

from pathlib import Path


# =============================================================================
# 1. ROOT — Localizar la carpeta raíz del proyecto
# =============================================================================
# Necesitamos saber dónde está instalado el proyecto en el ordenador de
# cualquier persona que lo ejecute. No podemos hardcodear
# "C:/Users/mjmor/..." porque en otro ordenador esa ruta no existe.
#
# La estrategia: este fichero (config_app.py) está en app/.
# Subimos un nivel con .parent y llegamos a la raíz del proyecto (AU_UJI/).
#
# Path(__file__)        → ruta completa a este fichero: .../app/config_app.py
# .resolve()            → convierte a ruta absoluta (sin ../.. relativos)
# .parent               → sube un nivel: de app/ a AU_UJI/
#
# Luego verificamos que la carpeta src/ exista ahí como comprobación
# de seguridad (igual que hacemos en los notebooks del TFM).

def _detectar_root() -> Path:
    """
    Sube niveles desde este fichero hasta encontrar la carpeta src/.
    Lanza un error claro si no la encuentra, en lugar de fallar misteriosamente.
    """
    candidato = Path(__file__).resolve().parent  # empieza en app/
    for _ in range(5):                           # sube hasta 5 niveles
        if (candidato / "src").exists():
            return candidato
        candidato = candidato.parent
    raise FileNotFoundError(
        "No se encontró la carpeta src/. "
        "Asegúrate de ejecutar la app desde dentro del proyecto."
    )

ROOT = _detectar_root()


# =============================================================================
# 1.bis — IMPORTAR DE src/ (refactor SRC↔APP)
# =============================================================================
# Hacemos que ROOT sea importable como paquete Python para poder hacer
# 'from src.config import ...' sin depender de la carpeta de trabajo.
#
# Alternativa rechazada: duplicar todos los mapas en este fichero (la versión
# vieja). Causaba bugs como SITUACION_LABORAL_MAP=11 que no existe en datos.
#
# A partir de aquí, los mapas de codificación, los nombres de ramas y las
# etiquetas legibles vienen de UNA SOLA FUENTE: src/config_datos.py y
# src/config_entorno.py (reexportados por src/config.py).

import sys
sys.path.insert(0, str(ROOT))

from src.config import (
    # Mapas de codificación — texto del formulario → código del modelo
    SITUACION_LABORAL_MAP,
    VIA_ACCESO_MAP,
    SEXO_MAP,
    PROVINCIA_MAP,
    PAIS_NOMBRE_MAP,
    UNIVERSIDAD_ORIGEN_MAP,
    RAMA_MAP,
    CUPO_MAP,
    # Diccionarios y nombres
    DICCIONARIO_RAMAS,             # {abreviatura: nombre completo}
    UNIVERSIDAD_ORIGEN_NOMBRES,    # {sigla: nombre completo} para etiquetas UI
    ETIQUETAS_VARIABLES,           # nombres legibles de variables (estilo abreviado)
    RAMAS_NOMBRES,                 # {abreviatura: nombre completo} (alias de DICCIONARIO_RAMAS)
    COLORES_RAMAS,                 # {nombre rama: color hex}
    COLORES_RAMAS_ABR,             # {abreviatura: color hex}
    COLORES_SEXO,                  # {Mujer/Hombre/Total: color hex}
    NOMBRES_LEGIBLES_FEATURES,     # {feature técnico: nombre legible largo}
)


# =============================================================================
# 2. APP_CONFIG — Metadatos generales de la aplicación
# =============================================================================
# Información que aparece en el título del navegador, la barra lateral, etc.
# APP_CONFIG debe definirse ANTES que RUTAS porque algunas rutas usan
# nombre_modelo_pkl para construir la ruta del modelo.

APP_CONFIG = {
    "titulo":                 "Predicción de Abandono — UJI",
    "subtitulo":              "TFM · Universitat Oberta de Catalunya · María José Morte",
    "icono":                  "🎓",
    "layout":                 "wide",
    "sidebar_state":          "expanded",
    "universidad_datos":      "Universitat Jaume I",
    "universidad_master":     "UOC",
    "tipo_trabajo":           "Trabajo Final de Máster",
    "autora":                 "María José Morte Ruiz",
    "email_master":           "mjmorteruiz@uoc.edu",
    "email_datos":            "morte@uji.es",
    "ciudad":                 "Castellón de la Plana",
    "año":                    "2026",
    # nombre_modelo_pkl eliminado (29/04/2026): ahora se lee dinámicamente
    # del JSON metricas_modelo.json mediante _obtener_ruta_modelo_dinamico().
    # El sistema dinámico (Bloque 0, opción C) selecciona el ganador en
    # f6_m00_preparacion.ipynb por criterios F1>Recall>AUC>Tiempo.
    "logo_universidad_datos": "logo_uji.png",
    "logo_universidad_master":"logo_uoc.png",
    "tab_inicio":             "Inicio",
    "n_ramas":                5,
    # DEPRECADO (30/04/2026): preferir m.get("n_features") del JSON dinámico.
    # Se mantiene como fallback si el JSON no se puede leer.
    "n_variables":            24,
}


# =============================================================================
# 3. RUTAS — Dónde están los datos y modelos que necesita la app
# =============================================================================
# Usamos pathlib (Path) en lugar de strings de texto porque:
#   - Funciona igual en Windows, Mac y Linux (maneja / y \ automáticamente)
#   - Podemos concatenar carpetas con el operador /  (muy legible)
#   - Tiene métodos útiles: .exists(), .stem, .suffix, etc.


def _obtener_ruta_modelo_dinamico() -> Path:
    """
    Lee modelo_pkl del JSON metricas_modelo.json y devuelve la ruta
    completa al .pkl del modelo ganador.

    Sistema dinámico opción C (Bloque 0, abril 2026): el ganador se
    selecciona automáticamente en f6_m00_preparacion.ipynb por los
    criterios F1 > Recall > AUC > Tiempo, sin hardcodes.

    Esto permite que cambie el modelo ganador (por ejemplo si se reentrena
    Fase 5) sin tocar ni una línea de código de la app.

    Returns
    -------
    Path
        Ruta completa al fichero .pkl del modelo ganador.
        Si el JSON no existe (primera ejecución), devuelve una ruta a un
        fichero ficticio que activará el error claro de
        verificar_ficheros_criticos() al arrancar la app.
    """
    import json as _json
    ruta_json = ROOT / "data" / "06_evaluacion" / "metricas_modelo.json"
    if ruta_json.exists():
        try:
            with open(ruta_json, encoding="utf-8") as f:
                meta = _json.load(f)
            nombre_pkl = meta.get("modelo_pkl", "modelo_no_definido.pkl")
            return ROOT / "data" / "05_modelado" / "models" / nombre_pkl
        except Exception:
            pass
    # Fallback: ruta inexistente → activará error en verificar_ficheros_criticos()
    return ROOT / "data" / "05_modelado" / "models" / "modelo_no_definido.pkl"


RUTAS = {
    # --- Modelo y pipeline ---
    # El modelo ganador se lee dinámicamente del JSON metricas_modelo.json
    # generado por f6_m00_preparacion.ipynb (sistema dinámico opción C).
    # Si quieres cambiar el modelo ganador, regenera el JSON — la app
    # lo cargará automáticamente al arrancar, sin tocar este fichero.
    "modelo": _obtener_ruta_modelo_dinamico(),

    # El pipeline de preprocesamiento (imputer + encoder + scaler)
    # Se aplica ANTES de pasar datos al modelo
    "pipeline": ROOT / "data" / "05_modelado" / "pipeline_preprocesamiento.pkl",

    # --- Resultados de Fase 6 (interpretabilidad) ---
    # Valores SHAP globales calculados sobre el conjunto de test (estimador final del Stacking)
    "shap_global": ROOT / "results" / "fase6" / "shap_global_catboost.pkl",

    # Métricas de equidad (fairness) por subgrupos
    "fairness": ROOT / "results" / "fase6" / "fairness_metricas.parquet",

    # --- Datos de evaluación ---
    # Metadatos del test: titulacion, rama, sexo, per_id_ficticio, abandono...
    # Generado por f6_m00_preparacion.ipynb (NO contiene features del modelo)
    "meta_test": ROOT / "data" / "06_evaluacion" / "meta_test.parquet",

    # Features del test preprocesadas — las 19 variables que usa el pipeline
    # Generado en Fase 5. Se cruza con meta_test por índice en loaders.py
    "X_test_prep": ROOT / "data" / "05_modelado" / "X_test_prep.parquet",

    # Fichero puente: índice posicional + per_id_ficticio (Fase 6 celda 8b)
    #"X_test_ids": ROOT / "data" / "06_evaluacion" / "X_test_prep_ids.parquet", revissaar 
    "X_test_prep_ids": ROOT / "data" / "05_modelado" / "X_test_prep_ids.parquet",

    # Features del test sin preprocesar (valores originales legibles)
    "X_test": ROOT / "data" / "05_modelado" / "X_test.parquet",

    # Fichero unificado para la app — generado por f6_m00b_preparacion_app.ipynb
    # Contiene: metadatos + features originales + flags _missing (6.725 × 34 cols)
    "meta_test_app": ROOT / "data" / "06_evaluacion" / "meta_test_app.parquet",

    # Métricas del modelo — generado por f6_m00_preparacion.ipynb (celda 9b)
    # AUC, F1, n_alumnos, tasa_abandono... leídos dinámicamente por la app
    "metricas_modelo": ROOT / "data" / "06_evaluacion" / "metricas_modelo.json",

    # --- Dataset completo (para joins con titulación) ---
    # df_alumno.parquet se genera en Fase 2 (EDA) y se guarda en 02_processed.
    # 00_raw contiene los Excels originales; los parquets procesados van a 02_processed.
    "df_alumno": ROOT / "data" / "02_processed" / "df_alumno.parquet",
}


# =============================================================================
# 4. COLORES — Paleta visual de la app
# =============================================================================
# Centralizamos los colores para que toda la app tenga coherencia visual.
# Si mañana quieres cambiar el azul por otro tono, lo cambias aquí una vez.
#
# PALETA MEJORADA (abril 2026): manteniendo la identidad institucional UJI
# pero con más contraste para que los dashboards luzcan profesionales.
# Los nombres de clave se mantienen iguales que antes (primario, abandono,
# exito, advertencia, fondo, texto, texto_suave, borde, blanco) para no
# romper código existente — solo cambian algunos valores hex.

COLORES = {
    # --- Colores principales (cambios de hex para más contraste) ---
    "primario":         "#1e4d8c",   # azul institucional profundo (antes #3182ce)
    "primario_claro":   "#4a9fd8",   # azul claro accent (NUEVO - para hover/accents)
    "abandono":         "#dc2626",   # rojo más fuerte (antes #e53e3e)
    "exito":            "#10b981",   # verde más vivo (antes #38a169)
    "advertencia":      "#f59e0b",   # amarillo ámbar (antes #d69e2e)

    # --- Neutros (sin cambios — compatibles con p00) ---
    "fondo":            "#f7fafc",   # gris muy claro para fondos de tarjetas
    "fondo_pagina":     "#f8fafc",   # gris casi blanco para fondo de página (NUEVO)
    "texto":            "#2d3748",   # gris oscuro para texto principal
    "texto_suave":      "#718096",   # gris medio para texto secundario
    "texto_muy_suave":  "#94a3b8",   # gris claro para texto terciario (NUEVO)
    "borde":            "#e2e8f0",   # gris claro para bordes y separadores
    "blanco":           "#ffffff",   # blanco puro para fondos de tarjetas y tooltips
}


# =============================================================================
# 5. RAMAS_NOMBRES + COLORES_RAMAS — Importados desde src/config_entorno.py
# =============================================================================
# Antes este bloque definía RAMAS_NOMBRES y COLORES_RAMAS aquí (duplicados).
# Refactor SRC↔APP: ahora vienen de src.config (importados arriba en 1.bis).
# Se mantiene la sección como referencia. Para cambiar nombres o colores de
# rama, editar en src/config_entorno.py — afecta a notebooks Y app a la vez.


# =============================================================================
# 6. COLORES_RIESGO — Alias semántico por nivel de riesgo
# =============================================================================
# Antes duplicaba hex fijos (#38a169, #ECC94B, #e53e3e). Ahora es un ALIAS:
# apunta a las mismas claves de COLORES para evitar duplicación.
# Si mañana cambias COLORES["exito"], COLORES_RIESGO["bajo"] cambia solo.
#
# Uso habitual:
#   from config_app import COLORES_RIESGO
#   color = COLORES_RIESGO["bajo"]    # verde éxito
#   color = COLORES_RIESGO["medio"]   # amarillo advertencia
#   color = COLORES_RIESGO["alto"]    # rojo abandono

COLORES_RIESGO = {
    "bajo":  COLORES["exito"],         # verde → riesgo bajo
    "medio": COLORES["advertencia"],   # amarillo → riesgo medio
    "alto":  COLORES["abandono"],      # rojo → riesgo alto
}


# =============================================================================
# 7. PESTAÑAS — Definición de las páginas de la app
# =============================================================================
# Cada pestaña tiene un nombre, un icono y una descripción corta.
# Esta lista la usará main.py para construir la navegación horizontal.
# Añadir una pestaña nueva = añadir un diccionario a esta lista.

PESTANAS = [
    {
        "id":          "institucional",
        "titulo":      "Visión institucional",
        "icono":       "🏛️",
        "descripcion": f"KPIs globales y tendencias de abandono en {APP_CONFIG['universidad_datos']}",
        "detalle":     "Evolución temporal · Por rama · Por titulación",
        "perfil":      "Gestores y dirección académica",
    },
    {
        "id":          "titulacion",
        "titulo":      "Por titulación",
        "icono":       "📚",
        "descripcion": "Análisis detallado por grado universitario",
        "detalle":     "SHAP · Factores de riesgo · Comparativa ramas",
        "perfil":      "Profesores y coordinadores de titulación",
    },
    {
        "id":          "prospecto",
        "titulo":      "Futuro estudiante",
        "icono":       "🔍",
        "descripcion": "Pronóstico para alumnos antes de matricularse",
        "detalle":     "Simulador · Perfil de riesgo · Recomendaciones",
        "perfil":      "Futuros estudiantes y orientadores",
    },
    {
        "id":          "en_curso",
        "titulo":      "Alumno en curso",
        "icono":       "📊",
        "descripcion": "Pronóstico para alumnos ya matriculados",
        "detalle":     "Predicción · SHAP individual · Evolución",
        "perfil":      "Estudiantes matriculados y tutores académicos",
    },
    {
        "id":          "equidad",
        "titulo":      "Equidad y diversidad",
        "icono":       "⚖️",
        "descripcion": "Análisis de fairness por género y rama de conocimiento",
        "detalle":     "Fairness · Por género · Por rama",
        "perfil":      "Todos los perfiles",
    },
    {
        "id":          "leyenda",
        "titulo":      "Guía semántica",
        "icono":       "📖",
        "descripcion": "Colores, métricas, glosario y marco ético",
        "detalle":     "Paleta · Transparencia · RGPD · AI Act · Glosario",
        "perfil":      "Tribunal · Gestores · Todos los perfiles",
    },
]


# =============================================================================
# 8. UMBRALES — Criterios para clasificar riesgo + tamaño de muestra
# =============================================================================
# UMBRALES: el modelo devuelve una probabilidad entre 0 y 1.
# Estos umbrales definen cuándo consideramos que el riesgo es bajo/medio/alto.
# Son ajustables: si el tribunal o los gestores prefieren otros valores,
# solo hay que cambiarlos aquí.

UMBRALES = {
    "riesgo_bajo":   0.30,   # prob < 0.30 → riesgo bajo (verde)
    "riesgo_medio":  0.60,   # 0.30 ≤ prob < 0.60 → riesgo medio (amarillo)
                             # prob ≥ 0.60 → riesgo alto (rojo)
}

# UMBRALES_MUESTRA: cuando el usuario aplica muchos filtros, la muestra puede
# quedarse demasiado pequeña para que los porcentajes sean fiables.
# Estos umbrales los usa p01 (y cualquier página que filtre datos) para
# mostrar avisos de interpretación al usuario.
#
# Criterio estadístico profesional (basado en teorema del límite central):
#   ≥ 100 → muestra sólida, sin aviso
#   30-99 → aviso amarillo: "muestra pequeña, interpretar con cautela"
#   10-29 → aviso naranja: "muestra muy pequeña, poco representativa"
#   <  10 → error rojo: "muestra insuficiente, no calcular porcentajes"

UMBRALES_MUESTRA = {
    "fiable":    100,   # ≥ este → sin aviso
    "aceptable":  30,   # ≥ este → aviso amarillo
    "minima":     10,   # ≥ este → aviso naranja; por debajo, error rojo
}


# =============================================================================
# 9. PARÁMETROS_ECONÓMICOS — Precio del crédito + créditos medios por abandono
# =============================================================================
# Valores por defecto usados en p01 ("Coste estimado del abandono").
# Ambos son EDITABLES por el usuario en la app mediante widgets numéricos,
# así que NO ES HARDCODE: son valores por defecto configurables.
#
# Referencias:
#   - PRECIO_CREDITO_UJI_DEFAULT = 18 €/crédito:
#     Grado primera matrícula (DOGV 2024-2025, pendiente confirmar con el Servicio de Planificación de la UJI).
#
#   - CREDITOS_MEDIOS_ABANDONO_DEFAULT = 60 créditos:
#     Supuesto basado en 1 año académico completo según EEES (60 ECTS = 1 curso).
#     Valor orientativo. En una futura mejora (ver pendiente F7-APP-B4-V2) se
#     sustituirá por la media real de `cred_superados` de los alumnos con
#     abandono=1 en df_alumno.parquet.

PRECIO_CREDITO_UJI_DEFAULT      = 18.0   # € por crédito — grado, primera matrícula
CREDITOS_MEDIOS_ABANDONO_DEFAULT = 60     # créditos cursados de media antes de abandonar


# =============================================================================
# =============================================================================
# 10. NOMBRES_VARIABLES — ALIAS hacia ETIQUETAS_VARIABLES + extras UI
# =============================================================================
# Antes este bloque tenía un diccionario propio con nombres legibles.
# Refactor SRC↔APP: ahora ETIQUETAS_VARIABLES (SRC) es la fuente única
# para las 27 variables del modelo. Aquí solo añadimos extras que existen
# únicamente en la app (no son features del modelo, son etiquetas UI).
#
# Patrón: alias + extras = no duplicación + cobertura UI completa.
# Si necesitas cambiar etiqueta de feature: edita src/config_datos.py.
# Si necesitas añadir etiqueta UI no-feature: añádela aquí en _EXTRAS_UI.

_EXTRAS_UI = {
    "prob_abandono": "Probabilidad de abandono",
    # ---------------------------------------------------------------------
    # Comentario para futuras fases (Chat p02 - auditoría nombres técnicos):
    # "per_id_ficticio" es el ID anonimizado de alumno usado internamente
    # en el modelado. NO es una feature del modelo (no afecta a métricas
    # ni a SHAP). Solo se muestra en la app, en la tabla de "alumnos en
    # riesgo alto" de p02_titulacion como identificador para que la usuaria
    # pueda referirse a un alumno concreto.
    #
    # Por qué está aquí y no en src/config_datos.py (ETIQUETAS_VARIABLES):
    # ETIQUETAS_VARIABLES es la fuente de verdad para variables del modelo.
    # per_id_ficticio NO es variable de modelo, solo identificador UI. Por
    # tanto va en _EXTRAS_UI (etiquetas exclusivas de la app).
    #
    # Si añades esta etiqueta también en src/config_datos.py, asegúrate de
    # quitarla aquí para no tener doble fuente de verdad. Si modificas el
    # texto, recuerda que se usa en p02_titulacion (tabla riesgo alto).
    "per_id_ficticio": "ID alumno",
}

NOMBRES_VARIABLES = {**ETIQUETAS_VARIABLES, **_EXTRAS_UI}


# =============================================================================
# 10.bis — nombre_legible() — Función auxiliar segura
# =============================================================================
# Devuelve la etiqueta legible de una columna técnica.
# A diferencia de NOMBRES_VARIABLES["x"] (que da KeyError si "x" no existe),
# esta función NUNCA peta: si la clave no está en el diccionario, devuelve
# el nombre técnico tal cual, transformado para ser más leíble.
#
# Refactor SRC↔APP: centraliza la lógica que antes estaba duplicada en p02
# (función _nombre_legible). Ahora todas las páginas pueden importarla:
#   from config_app import nombre_legible
#   ax.set_ylabel(nombre_legible(col))

def nombre_legible(col: str) -> str:
    """
    Convierte un nombre técnico de columna a etiqueta legible.

    Si la columna está en NOMBRES_VARIABLES, devuelve su etiqueta oficial.
    Si no, devuelve el nombre técnico transformado (sin guiones bajos,
    capitalizado) para que al menos sea legible aunque no oficial.

    Nunca lanza KeyError, evitando crashes de la app por etiquetas faltantes.

    Parameters
    ----------
    col : str
        Nombre técnico de la columna (ej: 'tasa_abandono_titulacion').

    Returns
    -------
    str
        Etiqueta legible (ej: 'Tasa aband. titulación') o fallback
        (ej: 'tasa_abandono_titulacion' → 'Tasa abandono titulacion').

    Examples
    --------
    >>> nombre_legible('cred_repetidos')
    'Créd. repetidos'
    >>> nombre_legible('columna_inventada')   # no existe en NOMBRES_VARIABLES
    'Columna inventada'
    """
    if col in NOMBRES_VARIABLES:
        return NOMBRES_VARIABLES[col]
    # Fallback: quitar guiones bajos y capitalizar primera letra
    return col.replace("_", " ").capitalize()


# =============================================================================
# 11. VERIFICACIÓN — Comprobar que los ficheros clave existen al arrancar
# =============================================================================
# Esta función se llama desde main.py al iniciar la app.
# Si falta algún fichero crítico, avisa claramente en lugar de fallar
# con un error críptico de Python más adelante.

def verificar_ficheros_criticos() -> list[str]:
    """
    Comprueba que existen los ficheros imprescindibles para la app.
    Devuelve una lista de mensajes de error (vacía si todo está bien).
    """
    criticos = ["modelo", "pipeline", "meta_test"]
    errores = []
    for nombre in criticos:
        ruta = RUTAS[nombre]
        if not ruta.exists():
            if nombre == "modelo":
                errores.append(
                    f"❌ Modelo no encontrado: {ruta}\n"
                    f"   Posibles causas:\n"
                    f"   1) Falta ejecutar f6_m00_preparacion.ipynb (genera metricas_modelo.json).\n"
                    f"   2) El modelo ganador del JSON no está en data/05_modelado/models/.\n"
                    f"   3) Falta ejecutar Fase 5 completa para generar los .pkl."
                )
            else:
                errores.append(f"❌ No encontrado: {ruta}")
    return errores


# =============================================================================
# 12. MAPAS DE CODIFICACIÓN — OPCIONES UI Y DERIVADOS
# =============================================================================
# El modelo fue entrenado con variables categóricas codificadas como enteros
# (Fase 3, f3_m04a_automl_target.ipynb). Los mapas FUENTE están ahora en
# src/config_datos.py (importados en sección 1.bis arriba).
#
# Aquí solo definimos lo que es ESPECÍFICO de la app:
#   - OPCIONES_*_UI: subconjuntos limpios para selectbox (sin variantes
#     históricas duplicadas que tienen los mapas SRC).
#   - RAMA_NOMBRE_A_CODIGO: derivado nombre completo → código (la app usa
#     nombres completos en formulario, RAMA_MAP de SRC usa siglas).
#   - *_INV: diccionarios inversos para mostrar etiquetas en gráficos.
#
# texto legible (lo que ve el usuario) → código numérico (lo que ve el modelo)

SITUACION_LABORAL_MAP_DOCSTRING = """
NOTA — Refactor SRC↔APP:
Los 7 mapas que antes estaban definidos aquí (SITUACION_LABORAL_MAP,
VIA_ACCESO_MAP, UNIVERSIDAD_ORIGEN_MAP, SEXO_MAP, PROVINCIA_MAP,
PAIS_NOMBRE_MAP, RAMA_MAP) ahora vienen de src/config_datos.py
(importados arriba en sección 1.bis).

Los mapas de SRC contienen TODAS las variantes históricas de cada texto
(ej: "Pruebas acceso Bachiller Logse" + "Bachillerato / PAU" → ambos = 10).
La app no debe enseñar esa lista cruda al usuario en un selectbox.

Por eso aquí definimos los OPCIONES_*_UI: subconjuntos LIMPIOS de cada
mapa, con UNA sola etiqueta por categoría, listos para selectbox.

ANTES había bug crítico: SITUACION_LABORAL_MAP={..."No trabaja":11,
"parcial":2, "completo":8} con códigos 11/8 que NO EXISTEN en datos
(reales son 0/1/2/3). Ese bug ha quedado eliminado al borrar los mapas
duplicados.
"""


# --- OPCIONES_LABORAL_UI ---
# 3 etiquetas para selectbox (las 3 categorías reales del modelo + texto UI).
# Las 3 etiquetas existen en SITUACION_LABORAL_MAP de SRC con los códigos
# correctos (1, 2, 3). Antes la app usaba 11/8/2 (incorrectos).
OPCIONES_LABORAL_UI: dict = {
    "No trabaja (inactivo/desempleado)": SITUACION_LABORAL_MAP["No trabaja (inactivo/desempleado)"],
    "Trabaja a tiempo parcial":          SITUACION_LABORAL_MAP["Trabaja a tiempo parcial"],
    "Trabaja a tiempo completo":         SITUACION_LABORAL_MAP["Trabaja a tiempo completo"],
    "Prefiero no indicarlo / sin datos": 0,
}

# --- OPCIONES_VIA_UI ---
# 9 etiquetas modernas (sin variantes históricas tipo "Logse" o duplicados).
# Cubren todas las vías de acceso del dataset agrupadas por categoría.
OPCIONES_VIA_UI: dict = {
    "Bachillerato / PAU":      VIA_ACCESO_MAP["Bachillerato / PAU"],
    "FP Grado Superior":       VIA_ACCESO_MAP["FP Grado Superior"],
    "Titulados universitarios": VIA_ACCESO_MAP["Titulados universitarios"],
    "Mayores de 25 años":      VIA_ACCESO_MAP["Mayores de 25 años"],
    "Mayores de 40 años":      VIA_ACCESO_MAP["Mayores de 40 años"],
    "Mayores de 45 años":      VIA_ACCESO_MAP["Mayores de 45 años"],
    "Extranjeros (UE)":        VIA_ACCESO_MAP["Extranjeros (UE)"],
    "Extranjeros (fuera UE)":  VIA_ACCESO_MAP["Extranjeros (fuera UE)"],
    "Sin datos / otro":        VIA_ACCESO_MAP.get("Sin datos / otro", 0),
}

# --- OPCIONES_SEXO_UI ---
# 2 etiquetas (Mujer, Hombre) — coherente con el modelo binario.
# La opción "Otro / no indicar" antigua se eliminó: agrupaba a 0 (Mujer)
# de forma engañosa. Ahora si el usuario no quiere indicar, no rellena.
OPCIONES_SEXO_UI: dict = {
    "Mujer":  SEXO_MAP["Mujer"],
    "Hombre": SEXO_MAP["Hombre"],
}

# --- OPCIONES_UNIVERSIDAD_UI ---
# 6 etiquetas: las 5 universidades del SRC + "Otra / sin datos" (UI extra).
# La 6ª opción NO está en SRC pero el modelo asigna 0 a cualquier no-mapeado
# (decisión D9 del refactor — UX justifica mantenerla).
# Texto formato "SIGLA — Nombre completo" para claridad.
OPCIONES_UNIVERSIDAD_UI: dict = {
    f"UJI — {UNIVERSIDAD_ORIGEN_NOMBRES['UJI']}":  UNIVERSIDAD_ORIGEN_MAP["UJI"],
    f"UPV — {UNIVERSIDAD_ORIGEN_NOMBRES['UPV']}":  UNIVERSIDAD_ORIGEN_MAP["UPV"],
    f"UV — {UNIVERSIDAD_ORIGEN_NOMBRES['UV']}":    UNIVERSIDAD_ORIGEN_MAP["UV"],
    f"UA — {UNIVERSIDAD_ORIGEN_NOMBRES['UA']}":    UNIVERSIDAD_ORIGEN_MAP["UA"],
    f"UMH — {UNIVERSIDAD_ORIGEN_NOMBRES['UMH']}":  UNIVERSIDAD_ORIGEN_MAP["UMH"],
    "Otra universidad / sin datos":                 0,
}

# --- RAMA_NOMBRE_A_CODIGO ---
# El RAMA_MAP de SRC usa siglas como claves ('TE': 1, 'HU': 2, ...).
# La app necesita mapear NOMBRE COMPLETO → código (porque el formulario
# muestra el nombre completo, no la sigla).
# Construido derivando: nombre_completo = DICCIONARIO_RAMAS[sigla]
RAMA_NOMBRE_A_CODIGO: dict = {
    nombre: RAMA_MAP[sigla]
    for sigla, nombre in DICCIONARIO_RAMAS.items()
}

# --- CATALOGO_TITULACIONES_UJI ---
# Catálogo OFICIAL completo de titulaciones de grado ofertadas por la UJI
# (37 grados, incluye dobles grados y titulaciones recientes que pueden
# no tener datos suficientes en el dataset de modelado).
#
# Uso en la app: permite mostrar al usuario TODAS las opciones reales de la
# UJI en los selectores de p03 (prospecto). Si una titulación no aparece en
# el dataset o tiene muy pocos alumnos, se marca visualmente como
# "sin datos" y se avisa al usuario al seleccionarla (transparencia).
#
# Formato: {nombre_oficial: codigo_rama_sigla}
#   sigla → usa DICCIONARIO_RAMAS para nombre completo de la rama
#   codigo_numerico → via RAMA_MAP[sigla]
CATALOGO_TITULACIONES_UJI: dict = {
    # Ciencias Sociales y Jurídicas (SO) — 18
    "Doble Grado en Administración y Dirección de Empresas y Derecho": "SO",
    "Grado en Administración y Dirección de Empresas": "SO",
    "Grado en Ciencias de la Actividad Física y del Deporte": "SO",
    "Grado en Criminología y Seguridad": "SO",
    "Grado en Comunicación Audiovisual": "SO",
    "Grado en Derecho": "SO",
    "Grado en Economía": "SO",
    "Grado en Finanzas y Contabilidad": "SO",
    "Grado en Gestión y Administración Pública": "SO",
    "Grado en International Business Economics": "SO",
    "Grado en Maestro o Maestra en Educación Infantil": "SO",
    "Grado en Maestro o Maestra en Educación Primaria": "SO",
    "Doble Grado en Maestro o Maestra en Educación Infantil y Primaria": "SO",
    "Grado en Marketing": "SO",
    "Grado en Periodismo": "SO",
    "Grado en Publicidad y Comunicación Corporativa": "SO",
    "Grado en Relaciones Laborales y Recursos Humanos": "SO",
    "Grado en Turismo": "SO",
    # Artes y Humanidades (HU) — 4
    "Grado en Estudios Ingleses": "HU",
    "Grado en Historia y Patrimonio": "HU",
    "Grado en Humanidades": "HU",
    "Grado en Traducción e Interpretación": "HU",
    # Ingeniería y Arquitectura (TE) — 10
    "Grado en Diseño y Desarrollo de Videojuegos": "TE",
    "Grado en Ingeniería en Diseño Industrial y Desarrollo de Productos": "TE",
    "Grado en Ingeniería Eléctrica": "TE",
    "Grado en Arquitectura Técnica": "TE",
    "Grado en Ingeniería en Tecnologías Industriales": "TE",
    "Grado en Ingeniería Informática": "TE",
    "Grado en Ingeniería Mecánica": "TE",
    "Grado en Ingeniería Química": "TE",
    "Grado en Inteligencia Robótica": "TE",
    "Grado en Matemática Computacional": "TE",
    # Ciencias Experimentales (EX) — 2
    "Grado en Química": "EX",
    "Grado en Bioquímica i Biología Molecular": "EX",
    # Ciencias de la Salud (SA) — 3
    "Grado en Psicología": "SA",
    "Grado en Enfermería": "SA",
    "Grado en Medicina": "SA",
}

# --- ALIAS_TITULACIONES ---
# Mapa de equivalencias: nombre ANTIGUO (como aparece en el dataset histórico)
# → nombre NUEVO OFICIAL (como se llama actualmente en la UJI y figura en
# CATALOGO_TITULACIONES_UJI). Se usa para cruzar datos: al filtrar el dataset
# por una titulación del catálogo, hay que buscar también por sus alias
# antiguos para recuperar todos los registros históricos.
#
# Ejemplo: "Arquitectura Técnica" (actual) incluye alumnos del antiguo
# "Ingeniería de la Edificación" → ambas apuntan al mismo grado.
#
# Titulaciones desaparecidas y no renombradas (p.ej. Ingeniería Agroalimentaria,
# suprimida en 2023) NO están en el catálogo ni en este mapa: sus datos
# siguen en el dataset pero no se ofrecen al usuario para pronóstico.
ALIAS_TITULACIONES: dict = {
    "Grado en Administración de Empresas":
        "Grado en Administración y Dirección de Empresas",
    "Grado en Criminologia y Seguridad":
        "Grado en Criminología y Seguridad",
    "Grado en Humanidades: Estudios Interculturales":
        "Grado en Humanidades",
    "Grado en Ingeniería Mecanica":
        "Grado en Ingeniería Mecánica",
    "Grado en Maestro en Educación Infantil":
        "Grado en Maestro o Maestra en Educación Infantil",
    "Grado en Maestro en Educación Primaria":
        "Grado en Maestro o Maestra en Educación Primaria",
    "Grado en Matematica Computacional":
        "Grado en Matemática Computacional",
    "Grado en Publicidad y Relaciones Públicas":
        "Grado en Publicidad y Comunicación Corporativa",
    "Grado en Ingeniería de la Edificación":
        "Grado en Arquitectura Técnica",
    # --- Pares viejo+nuevo con "(Plan XXXX)" --------------------------------
    # Cada titulación tiene dos registros en el dataset: el plan antiguo y
    # el plan nuevo. Unificamos al nombre base (sin paréntesis) porque para
    # el alumno y el tribunal es la misma titulación, y así la app ofrece
    # una sola opción por grado en los selectores.
    "Grado en Arquitectura Técnica (Plan 2020)":
        "Grado en Arquitectura Técnica",
    "Grado en Criminologia y Seguridad  (Plan 2020)":  # doble espacio real en dataset
        "Grado en Criminología y Seguridad",
    "Grado en Criminología y Seguridad (Plan 2020)":
        "Grado en Criminología y Seguridad",
    "Grado en Historia y Patrimonio (Plan 2015)":
        "Grado en Historia y Patrimonio",
    "Grado en Maestro en Educación Infantil (Plan 2018)":
        "Grado en Maestro o Maestra en Educación Infantil",
    "Grado en Maestro en Educación Primaria (Plan 2018)":
        "Grado en Maestro o Maestra en Educación Primaria",
    "Grado en Medicina (Plan 2017)":
        "Grado en Medicina",
    # Ingeniería Agroalimentaria: titulación suprimida. Unificamos las dos
    # variantes entre sí (Plan 2018 → sin plan) para que los registros
    # históricos se agrupen, aunque no figure en CATALOGO_TITULACIONES_UJI
    # (no se ofrece a prospectos, pero sí aparece en análisis históricos).
    "Grado en Ingeniería Agroalimentaria y del Medio Rural (Plan 2018)":
        "Grado en Ingeniería Agroalimentaria y del Medio Rural",
}

# Diccionarios inversos — código → etiqueta (para mostrar en gráficos)
# Generados a partir de los mapas importados de SRC (no duplicados).
# Como los mapas SRC tienen múltiples textos por código (variantes
# históricas), el "último gana": queda la etiqueta UI (la más limpia).
SITUACION_LABORAL_INV: dict = {v: k for k, v in SITUACION_LABORAL_MAP.items()}
VIA_ACCESO_INV:        dict = {v: k for k, v in VIA_ACCESO_MAP.items()}
UNIVERSIDAD_ORIGEN_INV:dict = {v: k for k, v in UNIVERSIDAD_ORIGEN_MAP.items()}
SEXO_INV:              dict = {v: k for k, v in SEXO_MAP.items()}
PROVINCIA_INV:         dict = {v: k for k, v in PROVINCIA_MAP.items()}
PAIS_NOMBRE_INV:       dict = {v: k for k, v in PAIS_NOMBRE_MAP.items()}
# RAMA_MAP_INV eliminado en refactor SRC↔APP — código muerto, nadie lo usaba

# --- PARCHES UI para códigos "fillna(0)" ---
# Los mapas SRC no definen el código 0 porque nacen de la regla de limpieza:
#   "Si el valor no está mapeado → fillna(0)"
# El 0 representa "sin datos / ausente". En la app lo mostramos al usuario
# como "Sin datos" para que los filtros sean legibles. Añadimos aquí el
# fallback SIN tocar SRC (es UX, no datos).
# Bug FASE C #13: filtro situacion_laboral mostraba "Código 0" sin etiqueta.
SITUACION_LABORAL_INV[0]  = "Sin datos"
VIA_ACCESO_INV[0]         = "Sin datos"
UNIVERSIDAD_ORIGEN_INV[0] = "Otra / sin datos"
PROVINCIA_INV[0]          = "Otra / sin datos"
PAIS_NOMBRE_INV[0]        = "Sin datos"


# =============================================================================
# FIN DE config_app.py
# Para importar en otro fichero:
#   from config_app import RUTAS, COLORES, APP_CONFIG, PESTANAS, UMBRALES
#   from config_app import UMBRALES_MUESTRA, PRECIO_CREDITO_UJI_DEFAULT
# =============================================================================
