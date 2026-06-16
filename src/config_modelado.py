# ============================================================================
# CONFIG_MODELADO.PY — Configuración central de la Fase 5: Modelado Clásico
# ============================================================================
# TFM: Predicción de Abandono Universitario
# Autora: María José Morte | UOC + UJI
#
# PROPÓSITO:
#   Este archivo es la ÚNICA fuente de verdad para todos los parámetros
#   de modelado. Ningún notebook de Fase 5 contiene valores hardcodeados:
#   todo —algoritmos, métricas, folds, semillas, colores— se lee aquí.
#
# ¿Por qué centralizar?
#   - Cambiar CV_FOLDS de 5 a 10 afecta a TODOS los módulos con un solo edit.
#   - El tribunal puede ver de un vistazo todas las decisiones metodológicas.
#   - Facilita la reproducibilidad: random_state siempre consistente.
#
# ¿Quién lo usa?
#   - f5_m00_indice.ipynb  → lee TODOS_LOS_ALGORITMOS y MODULOS_FASE5 para
#                            pintar el índice de Fase 5 (tarjetas + recuento 23/69).
#   - f5_m07_comparacion.ipynb → lee cargar_baseline_automl() para el baseline.
#
# NOTA IMPORTANTE: las listas de algoritmos de este archivo SOLO alimentan el
#   índice/tarjetas (display). El ENTRENAMIENTO real NO depende de ellas: cada
#   notebook de familia (f5_m01b/c, f5_m02, f5_m03, f5_m04, f5_m05, f5_m06)
#   instancia sus modelos directamente. La verdad congelada de los 69 modelos
#   está en resultados_maestro.json. Editar estas listas no afecta al modelo.
#
# NOTA: Este archivo se importa a través de src.config_modelado.
#   from src.config_modelado import CV_CONFIG, METRICAS_EVALUAR, ALGORITMOS_LINEALES
# ============================================================================

from typing import Dict, List, Any


# ============================================================================
# 1. CONFIGURACIÓN DE VALIDACIÓN CRUZADA
# ============================================================================
# Parámetros compartidos por TODOS los módulos de modelado.
#
# ¿Por qué estas decisiones?
#   - RANDOM_STATE=42: convención estándar para reproducibilidad.
#   - TEST_SIZE=0.2: split 80/20, equilibrio entre train suficiente y test fiable.
#   - CV_FOLDS=5: compromiso entre varianza del estimador y coste computacional.
#     Con 33.621 muestras, cada fold tiene ~5.400 muestras — estadísticamente robusto.
#   - ESTRATIFICADO=True: esencial con desbalance (29% abandono).

CV_CONFIG: Dict[str, Any] = {
    'random_state': 42,       # Semilla global — garantiza reproducibilidad total
    'test_size': 0.20,        # 20% test ≈ 6.724 muestras
    'cv_folds': 5,            # 5-Fold Stratified CV sobre train
    'estratificado': True,    # Mantiene proporción abandono/no-abandono en cada fold
    'n_jobs': -1,             # Usa todos los cores disponibles
    'verbose': 0,             # Sin output de scikit-learn (el notebook lo gestiona)
}


# ============================================================================
# 2. ESTRATEGIAS DE BALANCE DE CLASES
# ============================================================================
# El dataset tiene 29.2% abandono — desbalance moderado que puede sesgar
# modelos hacia la clase mayoritaria (no abandono).
#
# Se evalúan 3 estrategias para comparar su impacto en F1-macro:
#   A) Sin ajuste: línea base, ve el desbalance real
#   B) class_weight="balanced": penaliza errores en clase minoritaria
#   C) SMOTE: genera muestras sintéticas de la clase minoritaria
#
# La estrategia ganadora se documenta en f5_m05_comparativa.

ESTRATEGIAS_BALANCE: List[Dict[str, Any]] = [
    {
        'id': 'sin_ajuste',
        'nombre': 'Sin ajuste',
        'descripcion': 'Distribución original del dataset (29.2% abandono)',
        'class_weight': None,
        'usar_smote': False,
        'color': '#3182ce',
        'emoji': '⚖️',
    },
    {
        'id': 'balanced',
        'nombre': 'class_weight="balanced"',
        'descripcion': 'Peso inversamente proporcional a la frecuencia de clase',
        'class_weight': 'balanced',
        'usar_smote': False,
        'color': '#38a169',
        'emoji': '⚖️',
    },
    {
        'id': 'smote',
        'nombre': 'SMOTE',
        'descripcion': 'Synthetic Minority Over-sampling Technique sobre train',
        'class_weight': None,
        'usar_smote': True,
        'color': '#805ad5',
        'emoji': '🔄',
    },
]


# ============================================================================
# 3. MÉTRICAS DE EVALUACIÓN
# ============================================================================
# Métricas calculadas para TODOS los modelos. Orden de prioridad:
#   1. F1 binario (clase abandono): métrica principal — F1 sobre la clase
#      positiva. Elegida porque la clase de interés es abandono (29% —
#      minoritaria). F1-macro promediaría ambas clases por igual y diluiría
#      el indicador. Estándar académico para clasificación binaria con
#      clase de interés clara (literatura: detección de abandono escolar).
#   2. AUC-ROC: capacidad discriminativa del modelo, independiente del umbral.
#   3. Precision/Recall (clase abandono): para analizar el trade-off en
#      contexto educativo. (Recall alto = detectar más abandonos;
#      Precision alta = menos falsos positivos)
#   4. Kappa de Cohen: acuerdo más allá del azar, útil con desbalance.
#   5. Tiempo: relevante para despliegue en producción institucional.

METRICAS_EVALUAR: List[Dict[str, Any]] = [
    {
        'id': 'f1',
        'nombre': 'F1 (clase abandono)',
        'descripcion': 'Media armónica de Precision y Recall sobre la clase positiva (abandono)',
        'sklearn_key': 'f1',          # Clave para cross_val_score o classification_report
        'principal': True,            # Métrica de ranking principal
        'formato': '.4f',
        'emoji': '🎯',
        'color': '#3182ce',
    },
    {
        'id': 'auc_roc',
        'nombre': 'AUC-ROC',
        'descripcion': 'Área bajo la curva ROC — capacidad discriminativa',
        'sklearn_key': 'roc_auc',
        'principal': False,
        'formato': '.4f',
        'emoji': '📈',
        'color': '#38a169',
    },
    {
        'id': 'precision',
        'nombre': 'Precision (clase abandono)',
        'descripcion': 'Proporción de predicciones de abandono que son correctas',
        'sklearn_key': 'precision',
        'principal': False,
        'formato': '.4f',
        'emoji': '🔍',
        'color': '#805ad5',
    },
    {
        'id': 'recall',
        'nombre': 'Recall (clase abandono)',
        'descripcion': 'Proporción de abandonos reales detectados por el modelo',
        'sklearn_key': 'recall',
        'principal': False,
        'formato': '.4f',
        'emoji': '🔔',
        'color': '#ed8936',
    },
    {
        'id': 'accuracy',
        'nombre': 'Accuracy',
        'descripcion': 'Proporción de predicciones correctas (informativa, no principal)',
        'sklearn_key': 'accuracy',
        'principal': False,
        'formato': '.4f',
        'emoji': '✅',
        'color': '#319795',
    },
    {
        'id': 'kappa',
        'nombre': 'Kappa de Cohen',
        'descripcion': 'Acuerdo inter-rater normalizado — robusto ante desbalance',
        'sklearn_key': 'cohen_kappa',  # Calcular manualmente con cohen_kappa_score
        'principal': False,
        'formato': '.4f',
        'emoji': '🤝',
        'color': '#e53e3e',
    },
    {
        'id': 'tiempo_s',
        'nombre': 'Tiempo (s)',
        'descripcion': 'Tiempo de entrenamiento en segundos — relevante para producción',
        'sklearn_key': None,           # Se mide con time.time()
        'principal': False,
        'formato': '.2f',
        'emoji': '⏱️',
        'color': '#718096',
    },
]

# Métrica principal (la usada para ranking y selección)
METRICA_PRINCIPAL = next(m for m in METRICAS_EVALUAR if m['principal'])


# ============================================================================
# 4. BASELINE AUTOML DE REFERENCIA — DINÁMICO (sin hardcodes)
# ============================================================================
# Lee del JSON real generado por la fase AutoML (`automl_comparativa_final.json`).
# Si la fase AutoML no se ha ejecutado, devuelve None y los notebooks que
# dependan de esto deben adaptarse.
#
# Decisiones metodológicas (sí van en código):
#   - Caso D_strict: elegido por estricta auditoría de leakage frente a D.
#   - Selección dentro del caso: mejor F1 binario (clase abandono).
#   - Color rojo y línea discontinua: estilo gráfico de referencia.

# Decisiones metodológicas (estáticas)
BASELINE_CONFIG: Dict[str, Any] = {
    'caso_objetivo': 'D_strict',     # caso elegido por auditoría de leakage
    'criterio_seleccion': 'f1',      # F1 binario sobre clase abandono
    'color': '#e53e3e',              # rojo — línea referencia gráficos
    'linestyle': '--',               # línea discontinua — curvas comparativas
}


def cargar_baseline_automl(ruta_json=None) -> Dict[str, Any] | None:
    """
    Carga dinámicamente el baseline AutoML del JSON real.

    El JSON es la salida de la fase AutoML (m06_comparativa). Esta función
    selecciona el mejor modelo del caso `D_strict` por F1 binario, sin
    valores hardcodeados.

    Parameters
    ----------
    ruta_json : Path, optional
        Ruta al JSON. Si None, usa la ruta canónica del proyecto
        (`data/automl/automl_comparativa_final.json`).

    Returns
    -------
    dict | None
        Diccionario con las métricas del baseline o None si el JSON
        no existe o no contiene resultados del caso objetivo.

    Examples
    --------
    >>> baseline = cargar_baseline_automl()
    >>> if baseline:
    ...     print(f"Baseline: {baseline['modelo']} F1={baseline['f1']:.4f}")
    """
    import json as _json
    from pathlib import Path as _Path

    # Resolver ruta del JSON
    if ruta_json is None:
        try:
            from src.config import RUTA_AUTOML
            ruta_json = _Path(RUTA_AUTOML) / 'automl_comparativa_final.json'
        except ImportError:
            return None
    else:
        ruta_json = _Path(ruta_json)

    if not ruta_json.exists():
        return None

    # Cargar y filtrar
    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = _json.load(f)

    candidatos = [r for r in datos
                  if r.get('caso') == BASELINE_CONFIG['caso_objetivo']]
    if not candidatos:
        return None

    # Mejor por F1 (clave del JSON: 'f1' = binario clase positiva)
    mejor = max(candidatos, key=lambda r: r.get('f1', 0))

    return {
        'modelo':      mejor['model_name'],
        'framework':   mejor['framework'],
        'dataset':     mejor['caso'],
        'f1':          round(float(mejor['f1']), 4),
        'auc_roc':     round(float(mejor['auc_roc']), 4),
        'precision':   round(float(mejor['precision']), 4),
        'recall':      round(float(mejor['recall']), 4),
        'descripcion': (
            f'Mejor modelo del screening AutoML (168 modelos, 4 frameworks). '
            f'Caso {mejor["caso"]} — selección por F1 binario clase abandono. '
            f'Fase 5 parte de este baseline como referencia mínima.'
        ),
        'color':     BASELINE_CONFIG['color'],
        'linestyle': BASELINE_CONFIG['linestyle'],
    }


# ============================================================================
# 4-BIS. CRITERIOS DE SELECCIÓN DE MODELO GANADOR (sistema dinámico opción C)
# ============================================================================
# Decisiones metodológicas para elegir el modelo ganador en Fase 5 / Fase 6.
# El ganador NO se hardcodea — se elige leyendo `resultados_maestro.parquet`
# generado al final de Fase 5.
#
# Justificación de los criterios:
#   - F1 binario (clase abandono): métrica principal estándar para
#     clasificación binaria con clase de interés clara.
#   - Recall como primer desempate: en abandono escolar el coste de FN
#     (no detectar un abandono real) es mayor que el de FP (alarma falsa).
#     Ante empate en F1, preferimos el modelo que más abandonos detecta.
#   - AUC como segundo desempate: capacidad discriminativa global,
#     independiente del umbral de decisión.
#   - Tiempo como último desempate: ante empate métrico total, preferimos
#     el modelo más eficiente (mejor para producción institucional).
#
# UMBRAL_EMPATE = 0.001 → empate técnico si diferencia < 1 milésima.

CRITERIO_GANADOR:     str   = 'f1_test'        # columna de resultados_maestro.parquet
CRITERIO_DESEMPATE_1: str   = 'recall_test'    # primer desempate
CRITERIO_DESEMPATE_2: str   = 'auc_test'       # segundo desempate
CRITERIO_DESEMPATE_3: str   = 'tiempo_s'       # tercer desempate (menor = mejor)
UMBRAL_EMPATE:        float = 0.001            # diff < 0.001 → empate técnico


# ============================================================================
# 4-TER. DESCRIPCIONES DE MODELOS (texto humano para informes y app)
# ============================================================================
# Diccionario de descripciones cortas en español para cada algoritmo del
# proyecto. Se usa en `f6_m00_preparacion.ipynb` para añadir el campo
# `modelo_descripcion` al JSON `metricas_modelo.json` que lee la app.
#
# Si gana un modelo desconocido (futuro algoritmo añadido a Fase 5 sin
# actualizar este dict), la función `descripcion_modelo()` devuelve un
# texto genérico para no romper el flujo. La regla absoluta del proyecto
# (cero hardcodes) sigue cumpliéndose: el NOMBRE del modelo ganador es
# dinámico; solo la descripción humana asociada está codificada aquí.

DESCRIPCIONES_MODELOS: Dict[str, str] = {
    # --- Lineales ---
    'LogReg':        'Regresión logística — modelo lineal probabilístico, baseline interpretable.',
    'Ridge':         'Regresión lineal con regularización L2 (Tikhonov).',
    'SGD':           'Clasificador lineal entrenado con descenso de gradiente estocástico.',
    'SGDElasticNet': 'Lineal SGD con regularización ElasticNet (L1+L2).',
    'Perceptron':    'Perceptrón clásico — algoritmo lineal de un solo nivel.',
    'LDA':           'Análisis discriminante lineal — proyecta en hiperplanos por clase.',
    'SVM_lineal':    'Máquina de vectores soporte con kernel lineal.',
    'SVM_RBF':       'Máquina de vectores soporte con kernel RBF (no lineal).',
    # --- Árboles ---
    'DecisionTree':  'Árbol de decisión simple — interpretable pero propenso a sobreajuste.',
    'RandomForest':  'Bosque aleatorio — ensemble de árboles con bagging.',
    'ExtraTrees':    'Extra Trees — bosque con splits aleatorios, menor varianza.',
    # --- Gradient Boosting ---
    'GradientBoosting': 'Gradient Boosting clásico de scikit-learn.',
    'XGBoost':       'Gradient boosting con regularización L1/L2 y manejo nativo de nulos.',
    'LightGBM':      'Gradient boosting basado en histogramas — rápido y eficiente.',
    'CatBoost':      'Gradient boosting con manejo nativo de variables categóricas.',
    # --- MLP + EBM ---
    'MLP':           'Red neuronal multicapa (perceptrón multicapa).',
    'EBM':           'Explainable Boosting Machine — modelo aditivo interpretable.',
    # --- Ensambles ---
    'Bagging':       'Bagging — ensemble de modelos entrenados con bootstrap.',
    'AdaBoost':      'AdaBoost — boosting adaptativo con clasificadores débiles.',
    'Voting':        'Voting Classifier — combinación de modelos por votación.',
    'Stacking':      'Stacking — combinación de modelos base con un meta-learner.',
    # --- Otros ---
    'KNN':           'K-Nearest Neighbors — clasificación por vecinos más cercanos.',
    'GaussianNB':    'Naive Bayes Gaussiano — asume features con distribución normal.',
    'BernoulliNB':   'Naive Bayes Bernoulli — para features binarias.',
}


def descripcion_modelo(nombre: str) -> str:
    """
    Devuelve la descripción humana de un algoritmo.

    Si el nombre no está en el diccionario, devuelve un texto genérico
    en lugar de fallar — esto permite añadir nuevos modelos en Fase 5
    sin romper la generación del JSON.

    Parameters
    ----------
    nombre : str
        Nombre del algoritmo (ej. 'XGBoost', 'Stacking', 'RandomForest').

    Returns
    -------
    str
        Descripción corta del modelo o texto genérico si no se conoce.

    Examples
    --------
    >>> descripcion_modelo('XGBoost')
    'Gradient boosting con regularización L1/L2 y manejo nativo de nulos.'
    >>> descripcion_modelo('AlgoritmoFuturo')
    'Modelo de clasificación supervisada.'
    """
    return DESCRIPCIONES_MODELOS.get(
        nombre,
        'Modelo de clasificación supervisada.'
    )


# ============================================================================
# 5. ALGORITMOS POR MÓDULO
# ============================================================================
# Cada módulo de Fase 5 tiene su lista de algoritmos.
# La estructura permite que f5_m05_comparativa ensamble la tabla maestra
# automáticamente sin conocer los detalles de cada módulo.
#
# ¿Por qué estos algoritmos?
#   - Cobertura de las principales familias del ML supervisado clásico.
#   - Coherente con literatura de predicción de abandono universitario.
#   - EBM (InterpretML) incluido en m04 como puente hacia Fase 6.

# Familia Lineales (7): nombres reales sincronizados con resultados_maestro.json.
# Estas tarjetas SOLO pintan el índice de Fase 5; el entrenamiento real vive en
# los notebooks f5_m01b/f5_m01c (que definen los modelos directamente).
ALGORITMOS_LINEALES: List[Dict[str, Any]] = [
    {
        'id': 'lda',
        'nombre': 'LDA',
        'clase': 'LinearDiscriminantAnalysis',
        'descripcion': 'Análisis discriminante lineal — frontera lineal por covarianzas de clase',
        'emoji': '📐',
        'color': '#3182ce',
    },
    {
        'id': 'logreg',
        'nombre': 'LogReg',
        'clase': 'LogisticRegression',
        'descripcion': 'Regresión logística (saga) — baseline lineal interpretable',
        'emoji': '📈',
        'color': '#2b6cb0',
    },
    {
        'id': 'perceptron',
        'nombre': 'Perceptron',
        'clase': 'Perceptron',
        'descripcion': 'Perceptrón lineal — clasificador lineal online clásico',
        'emoji': '➗',
        'color': '#1a365d',
    },
    {
        'id': 'sgd',
        'nombre': 'SGD',
        'clase': 'SGDClassifier',
        'descripcion': 'Descenso de gradiente estocástico (modified_huber) — lineal escalable',
        'emoji': '📉',
        'color': '#4299e1',
    },
    {
        'id': 'sgd_elastic',
        'nombre': 'SGDElasticNet',
        'clase': 'SGDClassifier',
        'descripcion': 'SGD con penalización ElasticNet (L1+L2) — selección y shrinkage',
        'emoji': '🔗',
        'color': '#2c5282',
    },
    {
        'id': 'svm_rbf',
        'nombre': 'SVM_RBF',
        'clase': 'SVC',
        'descripcion': 'SVM con kernel RBF — frontera no lineal, probability=True',
        'emoji': '🌐',
        'color': '#2a4365',
    },
    {
        'id': 'svm_lineal',
        'nombre': 'SVM_lineal',
        'clase': 'SVC',
        'descripcion': 'SVM con kernel lineal — margen máximo en espacio original',
        'emoji': '📏',
        'color': '#1e3a5f',
    },
]

ALGORITMOS_ARBOLES: List[Dict[str, Any]] = [
    {
        'id': 'dt',
        'nombre': 'Decision Tree',
        'clase': 'DecisionTreeClassifier',
        'params': {'max_depth': None, 'random_state': 42},
        'descripcion': 'Árbol sin podar — referencia de árbol simple, interpretable',
        'emoji': '🌳',
        'color': '#38a169',
    },
    {
        'id': 'rf',
        'nombre': 'Random Forest',
        'clase': 'RandomForestClassifier',
        'params': {'n_estimators': 200, 'max_depth': None,
                   'n_jobs': -1, 'random_state': 42},
        'descripcion': 'Ensemble de árboles con bagging — robusto y con feature importance',
        'emoji': '🌲',
        'color': '#2f855a',
    },
    {
        'id': 'et',
        'nombre': 'Extra Trees',
        'clase': 'ExtraTreesClassifier',
        'params': {'n_estimators': 200, 'max_depth': None,
                   'n_jobs': -1, 'random_state': 42},
        'descripcion': 'Random Forest con splits completamente aleatorios — menor varianza',
        'emoji': '🌿',
        'color': '#276749',
    },
]

ALGORITMOS_BOOSTING: List[Dict[str, Any]] = [
    # Familia ganadora del AutoML. Se busca superar el baseline AutoML
    # (ver cargar_baseline_automl() en la sección 4).
    {
        'id': 'xgboost',
        'nombre': 'XGBoost',
        'clase': 'XGBClassifier',
        'modulo': 'xgboost',
        'params': {'n_estimators': 200, 'learning_rate': 0.1, 'max_depth': 6,
                   'use_label_encoder': False, 'eval_metric': 'logloss',
                   'n_jobs': -1, 'random_state': 42},
        'descripcion': 'Gradient Boosting con regularización L1/L2 y manejo nativo de nulos',
        'emoji': '🚀',
        'color': '#805ad5',
    },
    {
        'id': 'lightgbm',
        'nombre': 'LightGBM',
        'clase': 'LGBMClassifier',
        'modulo': 'lightgbm',
        'params': {'n_estimators': 200, 'learning_rate': 0.1,
                   'num_leaves': 31, 'n_jobs': -1,
                   'random_state': 42, 'verbose': -1},
        'descripcion': 'Leaf-wise boosting — más rápido que XGBoost en datasets grandes',
        'emoji': '💡',
        'color': '#553c9a',
    },
    {
        'id': 'catboost',
        'nombre': 'CatBoost',
        'clase': 'CatBoostClassifier',
        'modulo': 'catboost',
        'params': {'iterations': 200, 'learning_rate': 0.1, 'depth': 6,
                   'random_seed': 42, 'verbose': 0},
        'descripcion': 'Boosting simétrico con manejo nativo de categóricas — ganador AutoML',
        'emoji': '🐱',
        'color': '#44337a',
    },
    {
        'id': 'gradientboosting',
        'nombre': 'GradientBoosting',
        'clase': 'GradientBoostingClassifier',
        'modulo': 'sklearn.ensemble',
        'descripcion': 'Gradient Boosting clásico de sklearn — referencia sin librería externa',
        'emoji': '📊',
        'color': '#6b46c1',
    },
]

ALGORITMOS_OTROS: List[Dict[str, Any]] = [
    {
        'id': 'knn',
        'nombre': 'K-Nearest Neighbors',
        'clase': 'KNeighborsClassifier',
        'modulo': 'sklearn.neighbors',
        'params': {'n_neighbors': 5, 'weights': 'uniform', 'n_jobs': -1},
        'descripcion': 'Basado en instancias — sensible a escala, sin entrenamiento explícito',
        'emoji': '📍',
        'color': '#ed8936',
    },
    {
        'id': 'gnb',
        'nombre': 'Gaussian Naive Bayes',
        'clase': 'GaussianNB',
        'modulo': 'sklearn.naive_bayes',
        'params': {},
        'descripcion': 'Asume independencia y distribución normal — muy rápido',
        'emoji': '🎲',
        'color': '#c05621',
    },
    {
        'id': 'bnb',
        'nombre': 'Bernoulli Naive Bayes',
        'clase': 'BernoulliNB',
        'modulo': 'sklearn.naive_bayes',
        'params': {},
        'descripcion': 'Variante para features binarias — complementa GaussianNB',
        'emoji': '🎯',
        'color': '#dd6b20',
    },
]

# Mapa completo: módulo → lista de algoritmos
# Permite a f5_m05_comparativa iterar sobre todos sin conocer los detalles


# ============================================================================
# 5b. ALGORITMOS MLP + EBM (módulo m05)
# ============================================================================
ALGORITMOS_MLP_EBM: List[Dict[str, Any]] = [
    {
        'id': 'mlp',
        'nombre': 'MLP Classifier',
        'clase': 'MLPClassifier',
        'modulo': 'sklearn.neural_network',
        'params': {'hidden_layer_sizes': (100, 50), 'activation': 'relu',
                   'solver': 'adam', 'max_iter': 500, 'early_stopping': True,
                   'random_state': 42},
        'descripcion': 'Red neuronal multicapa — captura relaciones no lineales complejas',
        'emoji': '🧠',
        'color': '#3182ce',
    },
    {
        'id': 'ebm',
        'nombre': 'EBM (InterpretML)',
        'clase': 'ExplainableBoostingClassifier',
        'modulo': 'interpret.glassbox',
        'params': {'max_bins': 256, 'interactions': 10, 'learning_rate': 0.01,
                   'max_rounds': 5000, 'random_state': 42},
        'descripcion': 'Explainable Boosting Machine — precisión de boosting con interpretabilidad nativa',
        'emoji': '🔍',
        'color': '#805ad5',
    },
]

# ============================================================================
# 5c. ALGORITMOS ENSAMBLES (módulo m06)
# ============================================================================
ALGORITMOS_ENSAMBLES: List[Dict[str, Any]] = [
    {
        'id': 'voting',
        'nombre': 'VotingClassifier',
        'clase': 'VotingClassifier',
        'modulo': 'sklearn.ensemble',
        'params': {'voting': 'soft'},
        'descripcion': 'Votación suave de modelos base heterogéneos',
        'emoji': '🗳️',
        'color': '#3182ce',
    },
    {
        'id': 'stacking',
        'nombre': 'StackingClassifier',
        'clase': 'StackingClassifier',
        'modulo': 'sklearn.ensemble',
        'params': {},
        'descripcion': 'Meta-modelo LogReg que aprende a combinar predicciones base',
        'emoji': '🔗',
        'color': '#38a169',
    },
    {
        'id': 'bagging',
        'nombre': 'BaggingClassifier',
        'clase': 'BaggingClassifier',
        'modulo': 'sklearn.ensemble',
        'params': {'n_estimators': 100, 'random_state': 42},
        'descripcion': 'Bootstrap aggregating con base SVM — reduce varianza',
        'emoji': '🎒',
        'color': '#ed8936',
    },
    {
        'id': 'adaboost',
        'nombre': 'AdaBoost',
        'clase': 'AdaBoostClassifier',
        'modulo': 'sklearn.ensemble',
        'params': {'n_estimators': 200, 'learning_rate': 0.1, 'random_state': 42},
        'descripcion': 'Boosting adaptativo clásico con árboles de decisión',
        'emoji': '⚡',
        'color': '#d69e2e',
    },
]

ALGORITMOS_POR_MODULO: Dict[str, List[Dict]] = {
    'm01_lineales':  ALGORITMOS_LINEALES,
    'm02_arboles':   ALGORITMOS_ARBOLES,
    'm03_boosting':  ALGORITMOS_BOOSTING,
    'm04_otros':     ALGORITMOS_OTROS,
    'm05_mlp_ebm':   ALGORITMOS_MLP_EBM,
    'm06_ensambles': ALGORITMOS_ENSAMBLES,
}

# Lista plana de todos los algoritmos (para comparativa y conteos)
TODOS_LOS_ALGORITMOS: List[Dict] = (
    ALGORITMOS_LINEALES
    + ALGORITMOS_ARBOLES
    + ALGORITMOS_BOOSTING
    + ALGORITMOS_MLP_EBM
    + ALGORITMOS_ENSAMBLES
    + ALGORITMOS_OTROS
)


# ============================================================================
# 6. MÓDULOS DE FASE 5 (para generar tarjetas HTML en m00)
# ============================================================================
# Derivado automáticamente de las listas de algoritmos — sin hardcodes.

MODULOS_FASE5: List[Dict[str, Any]] = [
    {
        'id': 'f5_m01',
        'nombre': 'Modelos Lineales',
        'archivo_html': 'm01_lineales.html',
        'emoji': '📈',
        'color': '#3182ce',
        'algoritmos': ALGORITMOS_LINEALES,
        'n_algoritmos': len(ALGORITMOS_LINEALES),
        'descripcion': (
            f'{len(ALGORITMOS_LINEALES)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_LINEALES)
            + '. Baseline interpretable y referencia para modelos complejos.'
        ),
    },
    {
        'id': 'f5_m02',
        'nombre': 'Árboles',
        'archivo_html': 'm02_arboles.html',
        'emoji': '🌲',
        'color': '#38a169',
        'algoritmos': ALGORITMOS_ARBOLES,
        'n_algoritmos': len(ALGORITMOS_ARBOLES),
        'descripcion': (
            f'{len(ALGORITMOS_ARBOLES)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_ARBOLES)
            + '. Modelos basados en árboles con interpretabilidad nativa.'
        ),
    },
    {
        'id': 'f5_m03',
        'nombre': 'Gradient Boosting',
        'archivo_html': 'm03_boosting.html',
        'emoji': '🚀',
        'color': '#805ad5',
        'algoritmos': ALGORITMOS_BOOSTING,
        'n_algoritmos': len(ALGORITMOS_BOOSTING),
        'descripcion': (
            f'{len(ALGORITMOS_BOOSTING)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_BOOSTING)
            + '. Familia ganadora del AutoML. '
            'Baseline a superar: ver cargar_baseline_automl().'
        ),
    },
    {
        'id': 'f5_m04',
        'nombre': 'Otros Algoritmos',
        'archivo_html': 'm04_otros.html',
        'emoji': '🧪',
        'color': '#ed8936',
        'algoritmos': ALGORITMOS_OTROS,
        'n_algoritmos': len(ALGORITMOS_OTROS),
        'descripcion': (
            f'{len(ALGORITMOS_OTROS)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_OTROS)
            + '. Cobertura completa del espacio de algoritmos clásicos.'
        ),
    },
    {
        'id': 'f5_m05',
        'nombre': 'MLP + EBM',
        'archivo_html': 'm05_mlp_ebm.html',
        'emoji': '🧠',
        'color': '#3182ce',
        'algoritmos': ALGORITMOS_MLP_EBM,
        'n_algoritmos': len(ALGORITMOS_MLP_EBM),
        'descripcion': (
            f'{len(ALGORITMOS_MLP_EBM)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_MLP_EBM)
            + '. Redes neuronales y boosting interpretable.'
        ),
    },
    {
        'id': 'f5_m06',
        'nombre': 'Ensambles',
        'archivo_html': 'm06_ensambles.html',
        'emoji': '🔗',
        'color': '#38a169',
        'algoritmos': ALGORITMOS_ENSAMBLES,
        'n_algoritmos': len(ALGORITMOS_ENSAMBLES),
        'descripcion': (
            f'{len(ALGORITMOS_ENSAMBLES)} modelos: '
            + ', '.join(a['nombre'] for a in ALGORITMOS_ENSAMBLES)
            + '. Ensambles heterogéneos — Voting, Stacking, Bagging, AdaBoost.'
        ),
    },
    {
        'id': 'f5_m07',
        'nombre': 'Comparativa Final',
        'archivo_html': 'm07_comparacion.html',
        'emoji': '🏆',
        'color': '#e53e3e',
        'algoritmos': [],
        'n_algoritmos': len(TODOS_LOS_ALGORITMOS),
        'descripcion': (
            f'Tabla maestra de {len(TODOS_LOS_ALGORITMOS)} modelos. '
            'Curvas ROC comparativas. Ranking final. '
            'Selección del top-3 para Fase 6 (interpretabilidad + fairness).'
        ),
    },
]


# ============================================================================
# 7. RUTAS DE RESULTADOS
# ============================================================================
# Nombres de ficheros donde cada módulo guarda sus resultados.
# f5_m05_comparativa los carga todos para construir la tabla maestra.

RUTAS_RESULTADOS: Dict[str, str] = {
    'm01_lineales':  'resultados/f5_m01_lineales.parquet',
    'm02_arboles':   'resultados/f5_m02_arboles.parquet',
    'm03_boosting':  'resultados/f5_m03_boosting.parquet',
    'm04_otros':     'resultados/f5_m04_otros.parquet',
}

# Nombre del archivo de métricas JSON (sistema src.metricas)
METRICAS_JSON_KEY = 'fase5_resultados'


# ============================================================================
# 8. FUNCIONES DE UTILIDAD (sin dependencias externas)
# ============================================================================

def get_algoritmo_por_id(alg_id: str) -> Dict[str, Any]:
    """
    Busca un algoritmo por su id en todas las listas.

    Parameters
    ----------
    alg_id : str
        Identificador del algoritmo (ej: 'xgboost', 'logreg')

    Returns
    -------
    Dict con la configuración del algoritmo, o {} si no se encuentra.
    """
    for alg in TODOS_LOS_ALGORITMOS:
        if alg['id'] == alg_id:
            return alg
    return {}


def get_metrica_principal() -> Dict[str, Any]:
    """Devuelve la métrica marcada como principal."""
    return METRICA_PRINCIPAL


def resumen_config() -> None:
    """Imprime un resumen de la configuración para verificación en notebooks."""
    total = len(TODOS_LOS_ALGORITMOS)
    print('=' * 65)
    print('CONFIG_MODELADO — Fase 5: Modelado Clásico')
    print('=' * 65)
    print(f'  CV:              {CV_CONFIG["cv_folds"]}-Fold Stratified | '
          f'random_state={CV_CONFIG["random_state"]} | '
          f'test_size={CV_CONFIG["test_size"]}')
    print(f'  Estrategias:     {len(ESTRATEGIAS_BALANCE)} '
          f'({", ".join(e["id"] for e in ESTRATEGIAS_BALANCE)})')
    print(f'  Métricas:        {len(METRICAS_EVALUAR)} '
          f'| Principal: {METRICA_PRINCIPAL["nombre"]}')
    print(f'  Baseline AutoML: ', end='')
    _baseline = cargar_baseline_automl()
    if _baseline:
        print(f'{_baseline["modelo"]} '
              f'F1={_baseline["f1"]:.4f} | AUC={_baseline["auc_roc"]:.4f}')
    else:
        print('⚠️ JSON no encontrado — ejecuta la fase AutoML primero')
    print(f'  Algoritmos:      {total} en total')
    for modulo in MODULOS_FASE5[:-1]:  # Excluye comparativa
        print(f'    {modulo["emoji"]} {modulo["nombre"]}: '
              f'{modulo["n_algoritmos"]} modelos')
    print('=' * 65)
