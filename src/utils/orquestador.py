# ============================================================================
# ORQUESTADOR.PY - Orquestador de fases para notebooks de ejecución
# ============================================================================
# Ubicación: src/utils/orquestador.py
#
# Funciones disponibles:
#   orquestador_fase()   → crea y devuelve un ProgresoFase listo para usar
#
# Uso en f6_m00_ejecucion.ipynb:
#   from src.utils.orquestador import orquestador_fase
#
#   orch = orquestador_fase("Fase 6 — Evaluación")
#   orch.mostrar()
#
#   orch.iniciar('m01a')
#   ejecutar_notebook('f6_m01a_shap_global.ipynb')
#   orch.ok('m01a')
#
# Internamente delega en progress.progreso_fase para todo el rendering.
# Este módulo existe para poder importar el orquestador con un nombre
# semántico distinto de la barra de progreso de bucles.
# ============================================================================

from src.utils.progress import progreso_fase, _ProgresoFase
import subprocess
import sys
import time
from pathlib import Path


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def orquestador_fase(titulo: str, modulos: list = None) -> _ProgresoFase:
    """
    Crea un orquestador de progreso de fase.

    Devuelve un objeto _ProgresoFase con métodos:
        .mostrar()       → renderiza la tabla de progreso en el notebook
        .iniciar(id)     → marca módulo como ⏳ en ejecución
        .ok(id)          → marca módulo como ✅ completado + tiempo
        .error(id)       → marca módulo como ❌ fallido

    Parameters
    ----------
    titulo : str
        Título que aparece en la cabecera de la tabla.
        Ej: "Fase 1 — Transformación", "Fase 2 — EDA Datos Originales"
    modulos : list of dict, optional
        Lista de módulos con claves: 'id', 'nombre', 'emoji'
        Si se omite, se infiere del título automáticamente.
        Si el título no coincide con ninguna fase conocida, usa Fase 6.

    Returns
    -------
    _ProgresoFase
        Objeto de progreso listo para usar.

    Examples
    --------
    >>> from src.utils.orquestador import orquestador_fase
    >>> orch = orquestador_fase("Fase 1 — Transformación")
    >>> orch.mostrar()
    >>> orch.iniciar('m01')
    >>> # ... ejecutar notebook ...
    >>> orch.ok('m01')
    """
    if modulos is None:
        titulo_lower = titulo.lower()
        if 'fase 1' in titulo_lower or 'transformación' in titulo_lower or 'transformacion' in titulo_lower:
            modulos = MODULOS_FASE1
        elif 'fase 2' in titulo_lower or 'eda datos originales' in titulo_lower:
            modulos = MODULOS_FASE2
        elif 'fase 3' in titulo_lower or 'feature' in titulo_lower:
            modulos = MODULOS_FASE3
        elif 'fase 4' in titulo_lower or 'eda final' in titulo_lower:
            modulos = MODULOS_FASE4
        elif 'fase 5' in titulo_lower or 'modelado' in titulo_lower:
            modulos = MODULOS_FASE5
        elif 'fase 6' in titulo_lower or 'evaluación' in titulo_lower or 'evaluacion' in titulo_lower:
            modulos = MODULOS_FASE6
        elif 'automl' in titulo_lower:
            modulos = MODULOS_AUTOML
        else:
            modulos = MODULOS_FASE6  # fallback

    return progreso_fase(modulos, titulo)


# ============================================================================
# LISTAS DE MÓDULOS POR FASE
# ============================================================================

MODULOS_FASE1 = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Reportes Raw',        'emoji': '📋'},
    {'id': 'm02',      'nombre': 'Limpieza',            'emoji': '🧹'},
    {'id': 'm03',      'nombre': 'Reportes Clean',      'emoji': '✨'},
    {'id': 'm04',      'nombre': 'Dataset Final',       'emoji': '🎯'},
    {'id': 'm04a',     'nombre': 'Unión Tablas',        'emoji': '🔗'},
    {'id': 'm04b',     'nombre': 'Unión Preinscripción','emoji': '📝'},
    {'id': 'm04c',     'nombre': 'Corrección Notas',    'emoji': '📊'},
    {'id': 'm04d',     'nombre': 'Corrección Vía Acceso','emoji': '🔧'},
    {'id': 'm05',      'nombre': 'Dashboard',           'emoji': '📊'},
    {'id': 'm06',      'nombre': 'Grafo',               'emoji': '🕸️'},
    {'id': 'm06b',     'nombre': 'Grafo Pyvis',         'emoji': '🌐'},
]

MODULOS_FASE2 = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Inspección',          'emoji': '🔍'},
    {'id': 'm02',      'nombre': 'Calidad',             'emoji': '✅'},
    {'id': 'm03',      'nombre': 'Nulos',               'emoji': '❓'},
    {'id': 'm04',      'nombre': 'Univariante Num',     'emoji': '📈'},
    {'id': 'm05',      'nombre': 'Univariante Cat',     'emoji': '📊'},
    {'id': 'm06',      'nombre': 'Evolución',           'emoji': '📈'},
    {'id': 'm06b',     'nombre': 'Temporal (Altair)',   'emoji': '📅'},
    {'id': 'm07',      'nombre': 'Conclusiones',        'emoji': '📝'},
]

MODULOS_FASE3 = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Validación',          'emoji': '✅'},
    {'id': 'm02',      'nombre': 'Agregación',          'emoji': '🔗'},
    {'id': 'm03',      'nombre': 'Features',            'emoji': '🧪'},
    {'id': 'm04',      'nombre': 'Encoding Índice',     'emoji': '🏷️'},
    {'id': 'm04a',     'nombre': 'Encoding AutoML',     'emoji': '🤖'},
    {'id': 'm04b',     'nombre': 'Encoding EDA',        'emoji': '📊'},
    {'id': 'm05',      'nombre': 'Target y Export',     'emoji': '🎯'},
    {'id': 'm06',      'nombre': 'Baselines',           'emoji': '📈'},
    {'id': 'm07',      'nombre': 'Validación',          'emoji': '🔍'},
    {'id': 'm08',      'nombre': 'Auditoría',           'emoji': '📋'},
    {'id': 'm09',      'nombre': 'Perfiles Riesgo',     'emoji': '👤'},
]

MODULOS_FASE4 = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Inspección',          'emoji': '🔍'},
    {'id': 'm02',      'nombre': 'Target',              'emoji': '🎯'},
    {'id': 'm03',      'nombre': 'Distrib. Num',        'emoji': '📊'},
    {'id': 'm04',      'nombre': 'Distrib. Cat',        'emoji': '📈'},
    {'id': 'm05',      'nombre': 'Bivariante',          'emoji': '🔗'},
    {'id': 'm06',      'nombre': 'Correlaciones',       'emoji': '🔥'},
    {'id': 'm07',      'nombre': 'Selección',           'emoji': '🎯'},
    {'id': 'm08',      'nombre': 'Comparativa Grupos',  'emoji': '📊'},
    {'id': 'm09',      'nombre': 'Conclusiones',        'emoji': '📝'},
]

MODULOS_FASE5 = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Modelos Lineales',    'emoji': '📈'},
    {'id': 'm02',      'nombre': 'Árboles',             'emoji': '🌲'},
    {'id': 'm03',      'nombre': 'Gradient Boosting',   'emoji': '🚀'},
    {'id': 'm04',      'nombre': 'Otros Algoritmos',    'emoji': '🧪'},
    {'id': 'm05',      'nombre': 'MLP + EBM',           'emoji': '🧠'},
    {'id': 'm06',      'nombre': 'Ensambles',           'emoji': '🔗'},
    {'id': 'm07',      'nombre': 'Comparativa Final',   'emoji': '🏆'},
]

MODULOS_AUTOML = [
    {'id': 'indice',   'nombre': 'Índice',              'emoji': '📋'},
    {'id': 'm01',      'nombre': 'Baselines',           'emoji': '📊'},
    {'id': 'm02',      'nombre': 'LazyPredict',         'emoji': '⚡'},
    {'id': 'm03',      'nombre': 'PyCaret',             'emoji': '🤖'},
    {'id': 'm04',      'nombre': 'H2O',                 'emoji': '💧'},
    {'id': 'm05',      'nombre': 'AutoGluon',           'emoji': '🚀'},
    {'id': 'm06',      'nombre': 'Comparativa',         'emoji': '🏆'},
]

# ============================================================================
# LISTA ESTÁNDAR DE MÓDULOS FASE 6
# ============================================================================

MODULOS_FASE6 = [
    # --- Gestión ---
    {'id': 'm00_prep',  'nombre': 'Preparación',            'emoji': '⚙️'},
    {'id': 'm00_ejec',  'nombre': 'Ejecución',              'emoji': '▶️'},
    # --- SHAP ---
    {'id': 'm01a',      'nombre': 'SHAP Global',            'emoji': '🌍'},
    {'id': 'm01b',      'nombre': 'SHAP Local',             'emoji': '🔬'},
    {'id': 'm01c',      'nombre': 'SHAP Cohortes',          'emoji': '👥'},
    {'id': 'm01d',      'nombre': 'Shapash',                'emoji': '📊'},
    # --- Interpretabilidad Alternativa ---
    {'id': 'm02a',      'nombre': 'LIME',                   'emoji': '🍋'},
    {'id': 'm02b',      'nombre': 'DiCE',                   'emoji': '🎲'},
    # --- Fairness y Errores ---
    {'id': 'm03a',      'nombre': 'Fairness',               'emoji': '⚖️'},
    {'id': 'm03b',      'nombre': 'Errores FP/FN',          'emoji': '❌'},
    # --- Robustez y Calibración ---
    {'id': 'm04a',      'nombre': 'Stress Testing',         'emoji': '💪'},
    {'id': 'm04b',      'nombre': 'Calibración',            'emoji': '🎯'},
    {'id': 'm04c',      'nombre': 'Sostenibilidad',         'emoji': '🌱'},
    # --- Informe Final ---
    {'id': 'm05',       'nombre': 'Informe Final',          'emoji': '🏆'},
]


# ============================================================================
# EJECUCIÓN DE NOTEBOOKS (helper opcional)
# ============================================================================

def ejecutar_notebook(ruta_notebook: str | Path, timeout: int = -1) -> bool:
    """
    Ejecuta un notebook con nbconvert y devuelve True si tuvo éxito.

    Pensado para uso desde f6_m00_ejecucion.ipynb junto al orquestador:
        orch.iniciar('m01a')
        ok = ejecutar_notebook('f6_m01a_shap_global.ipynb')
        orch.ok('m01a') if ok else orch.error('m01a')

    Parameters
    ----------
    ruta_notebook : str | Path
        Ruta al fichero .ipynb (absoluta o relativa al CWD).
    timeout : int
        Tiempo máximo en segundos por celda (por defecto -1 = sin límite).

    Returns
    -------
    bool
        True si nbconvert terminó sin errores, False en caso contrario.
    """
    ruta = Path(ruta_notebook)
    cmd = [
        sys.executable, '-m', 'nbconvert',
        '--to', 'notebook',
        '--execute',
        f'--ExecutePreprocessor.timeout={timeout}',
        '--inplace',
        str(ruta)
    ]
    try:
        # NOTA: capture_output desactivado para ver progreso en tiempo real
        # en el orquestador. Si quieres silenciar la salida, vuelve a poner
        # capture_output=True.
        result = subprocess.run(cmd, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error ejecutando {ruta.name}: {e}")
        return False
