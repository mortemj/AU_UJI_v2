# ============================================================================
# CONTRATO_EXCEL.PY — Contrato esperado de los Excel originales
# ============================================================================
# TFM: Predicción de Abandono Universitario UJI
#
# PROPÓSITO
# ---------
# Fuente única de verdad sobre la estructura esperada de los 2 Excel originales
# proporcionados por la UJI (Oficina de Planificació i Prospectiva — OPP, y
# Unitat d'Anàlisi i Desenvolupament TI — UADTI). El validador de Fase 0
# (`f0_validar_excel.ipynb`) compara los Excel reales contra este contrato.
#
# Si la UJI envía nuevos datos (otros cursos, otras facultades) y la estructura
# cambia, SOLO hay que actualizar este fichero — el resto del proyecto se adapta.
#
# DISEÑO
# ------
# Cada hoja tiene 5 propiedades:
#   • tipo                 : "catalogo" o "alumno"
#                            - "catalogo": tabla maestra (Titulaciones), NO une
#                              por alumno, su clave es Exp_Tit_Id
#                            - "alumno"  : une por per_id_ficticio
#   • fichero              : "principal" o "preinscripcion"
#   • columnas_obligatorias: nombres exactos como aparecen en el Excel
#                            (la comparación REAL será case-insensitive en el
#                            validador, ver Paso 3 — esto se debe a que el
#                            contenido procede de exportaciones distintas y la
#                            consistencia de mayúsculas no está garantizada)
#   • tipos_esperados      : categoría semántica por columna:
#                              "numerico" → int / float
#                              "texto"    → object / string
#                              "fecha"    → datetime64
#                              "mixto"    → puede aceptar varios tipos (p.ej.
#                                           "Curso_Aca_Fin" tiene '-' o número)
#   • min_filas            : umbral mínimo razonable (~50% de las filas reales
#                            actuales, para tolerar variaciones sin ser laxo)
#
# CIFRAS DE REFERENCIA (al 04/05/2026 — informativo, NO usar en código)
# ---------------------------------------------------------------------
#   Titulaciones:           45 filas
#   Recibos:           114.454 filas
#   Domicilios:        210.911 filas
#   Expedientes:       109.568 filas
#   Nac-Sexo_Nacionalidad: 30.873 filas
#   Circunstancias:     70.524 filas
#   Trabajo:           195.524 filas
#   Notas:             107.908 filas
#   Hoja1 (preins.):   210.986 filas
#
# OBSERVACIONES SOBRE LOS DATOS ORIGINALES
# -----------------------------------------
#   • La hoja `Circunstancias` usa "Per_id_Ficticio" con F mayúscula, mientras
#     que las demás usan "Per_id_ficticio" con f minúscula. Es probable que
#     procedan de exportaciones distintas. El validador es tolerante a este
#     tipo de variaciones (case-insensitive).
#   • La hoja `Expedientes` tiene varias columnas con valores no-numéricos
#     (`-`, vacíos) en campos como `Nota`, `Curso_Aca_Fin`, `Nota_Acceso`. Por
#     eso esos campos se marcan como `mixto`.
#   • El campo `per_id_ficticio` es un identificador anonimizado: NO contiene
#     información personal real (nombres, DNI, etc.).
# ============================================================================

from typing import Dict, Any, List


# ============================================================================
# 1. CATEGORÍAS DE TIPOS ACEPTADAS
# ============================================================================
# Definidas como constantes para que el validador (Paso 3) las pueda importar
# y mapear a comprobaciones reales sobre los dtypes de pandas.

TIPO_NUMERICO = "numerico"   # int*, float* (incluye int64, float64, etc.)
TIPO_TEXTO    = "texto"      # object, string
TIPO_FECHA    = "fecha"      # datetime64[ns], datetime64
TIPO_MIXTO    = "mixto"      # tolera cualquier tipo (campos con '-' o NaN)


# ============================================================================
# 2. CONTRATO DE LAS 8 HOJAS DEL EXCEL PRINCIPAL
# ============================================================================
# `datos_proyecto_sin_preinscrip.xlsx` — fichero principal
# Cada hoja se mapea a un parquet en data/01_interim/ (ver MAPEO_HOJAS en
# config_entorno.py).

CONTRATO_EXCEL_PRINCIPAL: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------------
    # Titulaciones — TABLA CATÁLOGO (no une por alumno)
    # ------------------------------------------------------------------------
    # Es la tabla maestra de titulaciones del proyecto. NO contiene per_id.
    # Se relaciona con las demás hojas vía `Exp_Tit_Id`.
    "Titulaciones": {
        "tipo": "catalogo",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Exp_Tit_Id",
            "Titulacion",
            "Rama",
            "Cred_Titulacion",
            "Tipo",
            "Tipo_Estudio",
        ],
        "clave_principal": "Exp_Tit_Id",
        "tipos_esperados": {
            "Exp_Tit_Id":      TIPO_NUMERICO,
            "Titulacion":      TIPO_TEXTO,
            "Rama":            TIPO_TEXTO,
            "Cred_Titulacion": TIPO_NUMERICO,
            "Tipo":            TIPO_NUMERICO,
            "Tipo_Estudio":    TIPO_TEXTO,
        },
        "min_filas": 20,  # ~50% de 45
    },

    # ------------------------------------------------------------------------
    # Recibos — alumno
    # ------------------------------------------------------------------------
    # Histórico de recibos de matrícula del estudiantado.
    "Recibos": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Curso_Aca",
            "Nombre_recibos",
            "Forma_De_Pago",
            "Numero_Pagos",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio": TIPO_NUMERICO,
            "Curso_Aca":       TIPO_NUMERICO,
            "Nombre_recibos":  TIPO_TEXTO,
            "Forma_De_Pago":   TIPO_TEXTO,
            "Numero_Pagos":    TIPO_NUMERICO,
        },
        "min_filas": 50_000,  # ~50% de 114.454
    },

    # ------------------------------------------------------------------------
    # Domicilios — alumno
    # ------------------------------------------------------------------------
    # Domicilios declarados por el estudiantado (puede haber varios por curso).
    "Domicilios": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Poblacion",
            "Provincia",
            "Pais",
            "Curso_Aca",
            "Tipo_Domicilio",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio": TIPO_NUMERICO,
            "Poblacion":       TIPO_TEXTO,
            "Provincia":       TIPO_TEXTO,
            "Pais":            TIPO_TEXTO,
            "Curso_Aca":       TIPO_NUMERICO,
            "Tipo_Domicilio":  TIPO_TEXTO,
        },
        "min_filas": 100_000,  # ~50% de 210.911
    },

    # ------------------------------------------------------------------------
    # Expedientes — alumno (núcleo del proyecto)
    # ------------------------------------------------------------------------
    # Tabla principal: 1 fila por (alumno × titulación × curso académico).
    # Tiene varios campos `mixto` porque admite valores no-numéricos como '-'.
    "Expedientes": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Exp_Tit_Id",
            "Curso_Aca_Ini",
            "Curso_Aca",
            "Curso_Aca_Fin",
            "Nota",
            "Nombre",
            "Seguro",
            "Nota_selectividad",
            "Nota_Acceso",
            "Cred_Matriculados",
            "Cred_Superados",
            "Egresado",
            "Nuevo",
            "Media_Curso",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio":    TIPO_NUMERICO,
            "Exp_Tit_Id":         TIPO_NUMERICO,
            "Curso_Aca_Ini":      TIPO_NUMERICO,
            "Curso_Aca":          TIPO_NUMERICO,
            "Curso_Aca_Fin":      TIPO_MIXTO,    # admite '-'
            "Nota":               TIPO_MIXTO,    # admite '-'
            "Nombre":             TIPO_TEXTO,
            "Seguro":             TIPO_TEXTO,
            "Nota_selectividad":  TIPO_NUMERICO, # float con NaN
            "Nota_Acceso":        TIPO_MIXTO,    # admite '-'
            "Cred_Matriculados":  TIPO_NUMERICO,
            "Cred_Superados":     TIPO_NUMERICO,
            "Egresado":           TIPO_TEXTO,
            "Nuevo":              TIPO_TEXTO,
            "Media_Curso":        TIPO_MIXTO,    # admite '-' u otros valores no numéricos
        },
        "min_filas": 50_000,  # ~50% de 109.568
    },

    # ------------------------------------------------------------------------
    # Nac-Sexo_Nacionalidad — alumno (datos demográficos)
    # ------------------------------------------------------------------------
    # 1 fila por persona: sexo, fecha nacimiento, país. Tabla más pequeña que
    # las demás porque NO tiene multiplicidad por curso.
    "Nac-Sexo_Nacionalidad": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Sexo",
            "Fecha_nacimiento",
            "Id_Pais",
            "Pais_Nombre",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio":  TIPO_NUMERICO,
            "Sexo":             TIPO_NUMERICO,
            "Fecha_nacimiento": TIPO_FECHA,
            "Id_Pais":          TIPO_TEXTO,
            "Pais_Nombre":      TIPO_TEXTO,
        },
        "min_filas": 15_000,  # ~50% de 30.873
    },

    # ------------------------------------------------------------------------
    # Circunstancias — alumno (becas)
    # ------------------------------------------------------------------------
    # ⚠️ Esta hoja usa "Per_id_Ficticio" (F mayúscula), inconsistente con las
    # demás. La validación es case-insensitive (ver Paso 3) por lo que esto
    # NO genera error, pero queda documentado para el tribunal.
    "Circunstancias": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_Ficticio",   # F mayúscula intencional (así viene del origen)
            "Id_beca",
            "Nombre_beca",
            "Mat_Curso_Aca",
        ],
        "clave_principal": "Per_id_Ficticio",
        "tipos_esperados": {
            "Per_id_Ficticio": TIPO_NUMERICO,
            "Id_beca":         TIPO_NUMERICO,
            "Nombre_beca":     TIPO_TEXTO,
            "Mat_Curso_Aca":   TIPO_NUMERICO,
        },
        "min_filas": 30_000,  # ~50% de 70.524
    },

    # ------------------------------------------------------------------------
    # Trabajo — alumno (situación laboral)
    # ------------------------------------------------------------------------
    "Trabajo": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Exp_Tit_Id",
            "Nombre_trabajo",
            "Mat_Curso_Aca",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio": TIPO_NUMERICO,
            "Exp_Tit_Id":      TIPO_NUMERICO,
            "Nombre_trabajo":  TIPO_TEXTO,
            "Mat_Curso_Aca":   TIPO_NUMERICO,
        },
        "min_filas": 90_000,  # ~50% de 195.524
    },

    # ------------------------------------------------------------------------
    # Notas — alumno (medias académicas)
    # ------------------------------------------------------------------------
    "Notas": {
        "tipo": "alumno",
        "fichero": "principal",
        "columnas_obligatorias": [
            "Per_id_ficticio",
            "Curso_Aca",
            "Exp_Tit_Id",
            "Media_Titulacion_Curso",
            "Media_Titulacion_Alumno",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "Per_id_ficticio":         TIPO_NUMERICO,
            "Curso_Aca":               TIPO_NUMERICO,
            "Exp_Tit_Id":              TIPO_NUMERICO,
            "Media_Titulacion_Curso":  TIPO_NUMERICO,
            "Media_Titulacion_Alumno": TIPO_NUMERICO,
        },
        "min_filas": 50_000,  # ~50% de 107.908
    },
}


# ============================================================================
# 3. CONTRATO DEL EXCEL DE PREINSCRIPCIÓN
# ============================================================================
# `preinscripcion_si.xlsx` — fichero secundario
# Solo tiene 1 hoja llamada "Hoja1" con 24 columnas. Contiene datos de
# preinscripción del estudiantado en el sistema universitario valenciano
# (no solo UJI: incluye UPV, etc.) y se cruza con el principal por
# `per_id_ficticio`.

CONTRATO_EXCEL_PREINSCRIPCION: Dict[str, Dict[str, Any]] = {

    "Hoja1": {
        "tipo": "alumno",
        "fichero": "preinscripcion",
        "columnas_obligatorias": [
            "ANO",
            "UNIVERSIDAD",
            "MUNICIPIO",
            "CP",
            "ORDEN_TITULACION",
            "CUPO",
            "NOM_CUPO",
            "ESTADO",
            "NOTA_TXT",
            "SOLICITUD_ID",
            "COD_ESTUDIOS",
            "VIA_ESTUDIOS",
            "CONVOCATORIA",
            "NOTA_1",
            "NOTA_2",
            "ANO_1",
            "CON_1",
            "TITULACION_CENTRO",
            "ESTADO_TITULACION",
            "UNI_ID",
            "NOMBRE_UNIVERSIDAD",
            "ESTUDIO",
            "Per_id_ficticio",
            "MATRICULADO",
        ],
        "clave_principal": "Per_id_ficticio",
        "tipos_esperados": {
            "ANO":                TIPO_NUMERICO,
            "UNIVERSIDAD":        TIPO_TEXTO,
            "MUNICIPIO":          TIPO_TEXTO,
            "CP":                 TIPO_NUMERICO,
            "ORDEN_TITULACION":   TIPO_NUMERICO,
            "CUPO":               TIPO_NUMERICO,
            "NOM_CUPO":           TIPO_TEXTO,
            "ESTADO":             TIPO_TEXTO,
            "NOTA_TXT":           TIPO_NUMERICO,
            "SOLICITUD_ID":       TIPO_NUMERICO,
            "COD_ESTUDIOS":       TIPO_NUMERICO,
            "VIA_ESTUDIOS":       TIPO_TEXTO,
            "CONVOCATORIA":       TIPO_NUMERICO,
            "NOTA_1":             TIPO_NUMERICO,
            "NOTA_2":             TIPO_NUMERICO,
            "ANO_1":              TIPO_NUMERICO,
            "CON_1":              TIPO_NUMERICO,
            "TITULACION_CENTRO":  TIPO_NUMERICO,
            "ESTADO_TITULACION":  TIPO_NUMERICO,
            "UNI_ID":             TIPO_NUMERICO,
            "NOMBRE_UNIVERSIDAD": TIPO_TEXTO,
            "ESTUDIO":            TIPO_TEXTO,
            "Per_id_ficticio":    TIPO_NUMERICO,
            "MATRICULADO":        TIPO_TEXTO,
        },
        "min_filas": 100_000,  # ~50% de 210.986
    },
}


# ============================================================================
# 4. CRUCES ESPERADOS ENTRE HOJAS (para validación N5)
# ============================================================================
# Lista de pares (hoja_origen, hoja_destino, columna_de_cruce).
# El validador N5 hará un sample de IDs en `hoja_origen` y verificará que
# un porcentaje razonable existe también en `hoja_destino`. Si NO se solapan
# casi nada, hay un problema de integridad referencial.
#
# Solo se incluyen cruces realmente esperables. Por ejemplo, NO toda persona
# en `Recibos` tiene fila en `Trabajo` (no todo el mundo trabaja), así que
# ese cruce no se valida.

CRUCES_ESPERADOS: List[Dict[str, str]] = [
    # Todo expediente debe tener su titulación en el catálogo
    {
        "origen": "Expedientes",
        "destino": "Titulaciones",
        "columna": "Exp_Tit_Id",
        "umbral_pct": 99.0,  # ≥99% de Exp_Tit_Id de Expedientes deben estar en Titulaciones
    },
    # Toda persona en Expedientes debería tener datos demográficos
    {
        "origen": "Expedientes",
        "destino": "Nac-Sexo_Nacionalidad",
        "columna": "Per_id_ficticio",
        "umbral_pct": 95.0,
    },
    # Toda persona en Expedientes debería tener al menos un domicilio
    {
        "origen": "Expedientes",
        "destino": "Domicilios",
        "columna": "Per_id_ficticio",
        "umbral_pct": 90.0,
    },
]


# ============================================================================
# 5. CONTRATO COMPLETO (consolidado para uso del validador)
# ============================================================================
# Diccionario único que el validador (Paso 3) importará. Combina los 2 ficheros.

CONTRATO_EXCEL: Dict[str, Dict[str, Any]] = {
    **CONTRATO_EXCEL_PRINCIPAL,
    **CONTRATO_EXCEL_PREINSCRIPCION,
}


# ============================================================================
# 6. UTILIDAD: hojas esperadas por fichero
# ============================================================================

def hojas_esperadas(fichero: str) -> List[str]:
    """
    Devuelve la lista de hojas esperadas en un fichero Excel.

    Parameters
    ----------
    fichero : str
        "principal" o "preinscripcion"

    Returns
    -------
    List[str]
        Nombres exactos de las hojas esperadas.

    Raises
    ------
    ValueError
        Si el fichero no es uno de los valores permitidos.
    """
    if fichero not in ("principal", "preinscripcion"):
        raise ValueError(
            f"fichero debe ser 'principal' o 'preinscripcion', no {fichero!r}"
        )

    return [
        nombre_hoja
        for nombre_hoja, contrato in CONTRATO_EXCEL.items()
        if contrato["fichero"] == fichero
    ]
