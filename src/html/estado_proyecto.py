# ============================================================================
# src/html/estado_proyecto.py
# ============================================================================
#
# Detección dinámica del estado de cada fase del proyecto y generación del
# gráfico Plotly "Estado del Proyecto" usado en notebooks de conclusiones,
# en el índice principal (index.html) y en el resumen del orquestador.
#
# FUENTE ÚNICA DE VERDAD para "qué fichero indica que la fase X está hecha".
# Antes esta lógica estaba duplicada en 3 ficheros (index_generator.py,
# generar_resumen_proyecto.py y los notebooks de conclusiones), con riesgo
# de inconsistencias cada vez que cambiaba una ruta.
#
# ----------------------------------------------------------------------------
# Uso típico desde un notebook de conclusiones (ej. f2_m07_conclusiones.ipynb):
# ----------------------------------------------------------------------------
#
#     from src.html.estado_proyecto import generar_grafico_flujo
#     fig = generar_grafico_flujo(fase_actual='fase2')
#     fig.write_html(RUTA_GRAFICOS / 'm07_flujo_proyecto.html',
#                    include_plotlyjs='cdn')
#
# ----------------------------------------------------------------------------
# Uso desde código que solo necesita saber qué fases están hechas:
# ----------------------------------------------------------------------------
#
#     from src.html.estado_proyecto import detectar_estado_fases
#     estados = detectar_estado_fases()
#     fase5_done = next(e['hecha'] for e in estados if e['id'] == 'fase5')
#
# ----------------------------------------------------------------------------
# Patrón "if existe → Completada / else → Pendiente":
# ----------------------------------------------------------------------------
#
# Cada fase se considera completada si su fichero "señal" existe en disco.
# Las 9 señales están definidas en SEÑALES_FASES (constante de este módulo)
# y han sido verificadas en C:\FF\AU_UJI_v2 antes de fijarlas.
#
# ============================================================================

from pathlib import Path


# ============================================================================
# 1. CONSTANTE: SEÑALES DE LAS 9 FASES
# ============================================================================
# Cada tupla contiene:
#   - id:          identificador interno (str, sin espacios)
#   - etiqueta:    texto corto para el gráfico (ej. 'F0', 'AutoML')
#   - nombre:      nombre completo de la fase (mostrado en el gráfico)
#   - señal_rel:   ruta del fichero señal RELATIVA a BASE_PATH
#
# Si en el futuro cambia una ruta de fichero o se añade una fase, este es
# EL ÚNICO sitio donde hay que tocar — todo lo demás se actualiza solo.
#
# Orden importante: define cómo se dibujarán las barras en el gráfico
# (de arriba abajo en horizontal).

SEÑALES_FASES = [
    ('fase0',   'F0',     'Configuración',        'docs/html/orquestador_resumen.html'),
    ('fase1',   'F1',     'Transformación',       'data/02_processed/df_alumno.parquet'),
    ('fase2',   'F2',     'EDA Datos Originales', 'docs/html/fase2/m07_conclusiones.html'),
    ('fase3',   'F3',     'Features',             'data/03_features/dataset_final_tfm.parquet'),
    ('automl',  'AutoML', 'Pre-Modelado',         'docs/html/fase_automl/fase_automl_index.html'),
    ('fase4',   'F4',     'EDA Final',            'docs/html/fase4/m09_conclusiones_eda.html'),
    ('fase5',   'F5',     'Modelado',             'data/05_modelado/results/resultados_maestro.parquet'),
    ('fase6',   'F6',     'Evaluación',           'data/06_evaluacion/metricas_modelo.json'),
    ('fase7',   'F7',     'Aplicación',           'app/main.py'),
]


# ============================================================================
# 2. FUNCIÓN: DETECTAR ESTADO DE LAS FASES
# ============================================================================

def detectar_estado_fases(fase_actual: str = None) -> list:
    """
    Detecta dinámicamente el estado de cada fase según señales en disco.

    Parameters
    ----------
    fase_actual : str, optional
        Identificador de la fase actual (ej. 'fase2', 'fase4', 'fase6').
        Si se proporciona, esa fase se marcará como '🔄 En curso' aunque
        su señal exista en disco. Útil cuando un notebook de conclusiones
        está re-generándose: visualmente queda más claro qué fase llamó.

    Returns
    -------
    list of dict
        Lista de 9 dicts (uno por fase) en el orden de SEÑALES_FASES.
        Cada dict tiene:
            - 'id':       identificador interno (ej. 'fase2')
            - 'fase':     etiqueta corta (ej. 'F2')
            - 'nombre':   nombre completo (ej. 'EDA Datos Originales')
            - 'estado':   '✅ Completada' / '🔄 En curso' / '⏳ Pendiente'
            - 'color':    hex de COLORES.OK / .PRINCIPAL / .PENDIENTE
            - 'hecha':    True si la señal existe en disco (bool)
            - 'actual':   True si es la fase indicada en fase_actual (bool)

    Notes
    -----
    Esta función NUNCA inventa rutas: usa BASE_PATH + las rutas relativas
    declaradas en SEÑALES_FASES, todas verificadas en disco antes de fijarlas.
    """
    # Imports locales — config se carga aquí para evitar dependencias circulares
    # cuando el módulo se importa desde sitios distintos (notebooks vs src/).
    from src.config import BASE_PATH, COLORES

    estados = []
    for id_fase, etiqueta, nombre, ruta_rel in SEÑALES_FASES:
        # Construir ruta absoluta desde la raíz del proyecto
        ruta_absoluta = BASE_PATH / ruta_rel
        hecha = ruta_absoluta.exists()
        actual = (id_fase == fase_actual)

        # Decidir estado y color según las 3 categorías:
        #   - actual (en curso) tiene prioridad sobre completada
        #   - completada solo si NO es la actual y la señal existe
        #   - pendiente si la señal no existe (independientemente de actual)
        if actual and hecha:
            estado_txt = '🔄 En curso'
            color = COLORES.PRINCIPAL
        elif hecha:
            estado_txt = '✅ Completada'
            color = COLORES.OK
        else:
            # Si es la actual pero la señal no existe, sigue siendo pendiente
            # (no se puede estar "en curso" de algo que no se ha tocado nunca).
            estado_txt = '⏳ Pendiente'
            color = COLORES.PENDIENTE

        estados.append({
            'id':     id_fase,
            'fase':   etiqueta,
            'nombre': nombre,
            'estado': estado_txt,
            'color':  color,
            'hecha':  hecha,
            'actual': actual,
        })

    return estados


# ============================================================================
# 3. FUNCIÓN: GENERAR GRÁFICO PLOTLY DE FLUJO
# ============================================================================

def generar_grafico_flujo(fase_actual: str = None,
                          titulo: str = '📍 Estado del Proyecto',
                          altura: int = 480):
    """
    Genera la figura Plotly del gráfico "Estado del Proyecto" (barras
    horizontales con las 9 fases coloreadas según su estado real).

    Parameters
    ----------
    fase_actual : str, optional
        Fase a marcar como '🔄 En curso'. Si es None, no se marca ninguna
        como actual (todas aparecen como Completada o Pendiente).
        Valores válidos: 'fase0', 'fase1', 'fase2', 'fase3', 'automl',
        'fase4', 'fase5', 'fase6', 'fase7'.
    titulo : str, optional
        Título del gráfico. Por defecto '📍 Estado del Proyecto'.
    altura : int, optional
        Altura del gráfico en píxeles. Por defecto 480 (suficiente para 9 barras).

    Returns
    -------
    plotly.graph_objects.Figure
        Figura Plotly lista para .write_html() o .show().

    Notes
    -----
    Las barras se dibujan en el orden inverso de SEÑALES_FASES porque Plotly
    coloca el primer elemento del eje Y abajo. Así F0 queda arriba y F7 abajo,
    que es el orden cronológico natural de lectura.
    """
    # Import local: plotly solo se carga si realmente se llama a esta función,
    # no en cada `from src.html.estado_proyecto import ...`
    import plotly.graph_objects as go

    # Obtener el estado real de las 9 fases
    estados = detectar_estado_fases(fase_actual=fase_actual)

    # Listas paralelas para Plotly (en orden inverso para que F0 quede arriba)
    etiquetas = [e['fase'] for e in estados][::-1]
    nombres = [e['nombre'] for e in estados][::-1]
    estados_txt = [e['estado'] for e in estados][::-1]
    colores = [e['color'] for e in estados][::-1]

    # Texto de cada barra: nombre de la fase + estado debajo en pequeño
    textos = [
        f'{nombre}<br><span style="font-size:0.8em">{est}</span>'
        for nombre, est in zip(nombres, estados_txt)
    ]

    # Crear figura — barras horizontales, todas con valor 1 (decorativas)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=etiquetas,
        x=[1] * len(etiquetas),
        orientation='h',
        marker_color=colores,
        text=textos,
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=13, color='white'),
        hovertemplate='%{y}: %{text}<extra></extra>',
    ))

    fig.update_layout(
        title=titulo,
        height=altura,
        xaxis=dict(visible=False),
        yaxis=dict(title=''),
        margin=dict(t=60, b=40, l=80, r=40),
        showlegend=False,
    )

    return fig
