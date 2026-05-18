# ============================================================================
# NAVEGACION.PY - ESTRUCTURA DE FASES Y MÓDULOS DEL PROYECTO
# ============================================================================
# TFM: Predicción de Abandono Universitario
# Autora: María José Morte
# ============================================================================
# Cambios v2 (2026-03-11):
#   - Fase 6 actualizada: nueva estructura con principales + submodulos
#   - extraer_modulo_de_fichero() soporta submodulos con letra (m01a, m01b...)
#   - extraer_fase_de_fichero() soporta f6_m01a_, f6_m01b_...
# ============================================================================

from typing import Dict, List, Any
import re

# ============================================================================
# ESTRUCTURA DE FASES Y MÓDULOS
# ============================================================================

FASES: Dict[str, Dict[str, Any]] = {
    'inicio': {
        'nombre': 'Inicio',
        'emoji': '🏠',
        'archivo': '../index.html',
        'carpeta': '',
        'estado': 'activo'
    },
    'fase1': {
        'nombre': 'Transformación',
        'emoji': '📥',
        'archivo': 'fase1_index.html',
        'carpeta': 'fase1',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',          'archivo': 'fase1_index.html',        'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Reportes Datos Originales', 'archivo': 'm01_reportes_raw.html',   'emoji': '📋'},
            {'id': 'm02',    'nombre': 'Limpieza',         'archivo': 'm02_limpieza.html',       'emoji': '🧹'},
            {'id': 'm03',    'nombre': 'Reportes Clean',   'archivo': 'm03_reportes_clean.html', 'emoji': '✨'},
            {'id': 'm04',    'nombre': 'Dataset Final',    'archivo': 'm04_dataset_final.html',  'emoji': '🎯'},
            {'id': 'm05',    'nombre': 'Dashboard',        'archivo': 'm05_dashboard.html',      'emoji': '📊'},
            {'id': 'm06',    'nombre': 'Grafo',            'archivo': 'm06_grafo.html',          'emoji': '🕸️'},
        ]
    },
    'fase2': {
        'nombre': 'EDA Datos Originales',
        'emoji': '📊',
        'archivo': 'fase2_index.html',
        'carpeta': 'fase2',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',           'archivo': 'fase2_index.html',          'emoji': '📋'},
            {'id': 'm00_ejec', 'nombre': 'Ejecución',    'archivo': 'm00_ejecucion.html',        'emoji': '▶️'},
            {'id': 'm01',    'nombre': 'Inspección',       'archivo': 'm01_inspeccion.html',       'emoji': '🔍'},
            {'id': 'm02',    'nombre': 'Calidad',          'archivo': 'm02_calidad.html',          'emoji': '✅'},
            {'id': 'm03',    'nombre': 'Nulos',            'archivo': 'm03_nulos.html',            'emoji': '❓'},
            {'id': 'm04',    'nombre': 'Univariante Num',  'archivo': 'm04_univariante_num.html',  'emoji': '📈'},
            {'id': 'm05',    'nombre': 'Univariante Cat',  'archivo': 'm05_univariante_cat.html',  'emoji': '📊'},
            {'id': 'm06',    'nombre': 'Evolución',        'archivo': 'm06_evolucion.html',        'emoji': '📈'},
            {'id': 'm07',    'nombre': 'Conclusiones',     'archivo': 'm07_conclusiones.html',     'emoji': '📝'},
        ]
    },
    'fase3': {
        'nombre': 'Features',
        'emoji': '🔧',
        'archivo': 'fase3_index.html',
        'carpeta': 'fase3',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',           'archivo': 'fase3_index.html',           'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Validación',       'archivo': 'm01_validacion.html',        'emoji': '✅'},
            {'id': 'm02',    'nombre': 'Agregación',       'archivo': 'm02_agregacion.html',        'emoji': '🔗'},
            {'id': 'm03',    'nombre': 'Features',         'archivo': 'm03_features.html',          'emoji': '🧪'},
            {'id': 'm04',    'nombre': 'Encoding',         'archivo': 'm04_encoding.html',          'emoji': '🏷️'},
            {'id': 'm05',    'nombre': 'Target y Export',  'archivo': 'm05_target_export.html',     'emoji': '🎯'},
            {'id': 'm06',    'nombre': 'Alerta Temprana',  'archivo': 'm06_alerta_temprana.html',   'emoji': '⚠️'},
            {'id': 'm07',    'nombre': 'Validación',       'archivo': 'm07_validacion.html',        'emoji': '✅'},
            {'id': 'm08',    'nombre': 'Perfiles',         'archivo': 'm08_perfiles_riesgo.html',   'emoji': '👤'},
        ]
    },
    'fase4': {
        'nombre': 'EDA Final',
        'emoji': '🔬',
        'archivo': 'fase4_index.html',
        'carpeta': 'fase4',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',             'archivo': 'fase4_index.html',               'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Inspección',         'archivo': 'm01_inspeccion.html',            'emoji': '🔍'},
            {'id': 'm02',    'nombre': 'Target',             'archivo': 'm02_target.html',                'emoji': '🎯'},
            {'id': 'm03',    'nombre': 'Distrib. Num',       'archivo': 'm03_distribuciones_num.html',    'emoji': '📊'},
            {'id': 'm04',    'nombre': 'Distrib. Cat',       'archivo': 'm04_distribuciones_cat.html',    'emoji': '📈'},
            {'id': 'm05',    'nombre': 'Bivariante',         'archivo': 'm05_bivariante.html',            'emoji': '🔗'},
            {'id': 'm06',    'nombre': 'Correlaciones',      'archivo': 'm06_correlaciones.html',         'emoji': '🔥'},
            {'id': 'm07',    'nombre': 'Selección',          'archivo': 'm07_seleccion_features.html',    'emoji': '🎯'},
            {'id': 'm08',    'nombre': 'Comparativa Grupos', 'archivo': 'm08_perfiles_riesgo.html',       'emoji': '📊'},
            {'id': 'm09',    'nombre': 'Conclusiones',       'archivo': 'm09_conclusiones_eda.html',      'emoji': '📝'},
        ]
    },
    'fase5': {
        'nombre': 'Modelado',
        'emoji': '🤖',
        'archivo': 'fase5_index.html',
        'carpeta': 'fase5',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',            'archivo': 'fase5_index.html',    'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Modelos Lineales',  'archivo': 'm01_lineales.html',   'emoji': '📈'},
            {'id': 'm02',    'nombre': 'Árboles',           'archivo': 'm02_arboles.html',    'emoji': '🌲'},
            {'id': 'm03',    'nombre': 'Gradient Boosting', 'archivo': 'm03_boosting.html',   'emoji': '🚀'},
            {'id': 'm04',    'nombre': 'Otros Algoritmos',  'archivo': 'm04_otros.html',      'emoji': '🧪'},
            {'id': 'm05',    'nombre': 'MLP + EBM',         'archivo': 'm05_mlp_ebm.html',    'emoji': '🧠'},
            {'id': 'm06',    'nombre': 'Ensambles',         'archivo': 'm06_ensambles.html',  'emoji': '🔗'},
            {'id': 'm07',    'nombre': 'Comparativa Final', 'archivo': 'm07_comparacion.html','emoji': '🏆'},
        ]
    },
    # -----------------------------------------------------------------------
    # FASE 6: Interpretabilidad + Evaluación Final
    # Estructura: 3 gestión + 5 principales + 12 submodulos (con letra)
    # -----------------------------------------------------------------------
    'fase6': {
        'nombre': 'Evaluación',
        'emoji': '🔍',
        'archivo': 'fase6_index.html',
        'carpeta': 'fase6',
        'estado': 'activo',
        'modulos': [
            # --- Gestión ---
            {'id': 'indice',     'nombre': 'Índice',                    'archivo': 'fase6_index.html',                       'emoji': '📋'},
            {'id': 'm00_ejec',   'nombre': 'Ejecución',                 'archivo': 'm00_ejecucion.html',                     'emoji': '▶️'},
            # --- Principales ---
            {'id': 'm01',        'nombre': 'SHAP',                      'archivo': 'm01_interpretabilidad_shap.html', 'emoji': '🔍'},
            {'id': 'm02',        'nombre': 'Interp. Alternativa',       'archivo': 'm02_interpretabilidad_alternativa.html', 'emoji': '🧩'},
            {'id': 'm03',        'nombre': 'Fairness y Errores',        'archivo': 'm03_fairness_errores.html', 'emoji': '⚖️'},
            {'id': 'm04',        'nombre': 'Robustez y Sostenibilidad', 'archivo': 'm04_robustez.html',                       'emoji': '🛡️'},
            {'id': 'm06',        'nombre': 'Informe Final',             'archivo': 'm06_informe_final.html',                  'emoji': '📝'},
            # --- Submodulos SHAP ---
            {'id': 'm01a',       'nombre': 'SHAP Global',               'archivo': 'm01a_shap_global.html',                  'emoji': '🌍'},
            {'id': 'm01b',       'nombre': 'SHAP Local',                'archivo': 'm01b_shap_local.html',                   'emoji': '🔬'},
            {'id': 'm01c',       'nombre': 'SHAP Cohortes',             'archivo': 'm01c_shap_cohortes.html',                'emoji': '👥'},
            {'id': 'm01d',       'nombre': 'Shapash',                   'archivo': 'm01d_shapash.html',                      'emoji': '📊'},
            # --- Submodulos Interpretabilidad Alternativa ---
            {'id': 'm02a',       'nombre': 'LIME',                      'archivo': 'm02a_lime.html',                         'emoji': '🍋'},
            {'id': 'm02b',       'nombre': 'DiCE',                      'archivo': 'm02b_dice.html',                         'emoji': '🎲'},
            # --- Submodulos Fairness y Errores ---
            {'id': 'm03a',       'nombre': 'Fairness',                  'archivo': 'm03a_fairness.html',                     'emoji': '⚖️'},
            {'id': 'm03b',       'nombre': 'Errores FP/FN',             'archivo': 'm03b_errores_fpfn.html',                 'emoji': '❌'},
            # --- Submodulos Robustez y Sostenibilidad ---
            {'id': 'm04a',       'nombre': 'Stress Testing',            'archivo': 'm04a_stress.html',                       'emoji': '💪'},
            {'id': 'm04b',       'nombre': 'Calibración',               'archivo': 'm04b_calibracion.html',                  'emoji': '🎯'},
            {'id': 'm04c',       'nombre': 'Sostenibilidad',            'archivo': 'm04c_sostenibilidad.html',               'emoji': '🌱'},
            {'id': 'm04d',       'nombre': 'Robustez Temporal',         'archivo': 'm04d_robustez_temporal.html',            'emoji': '⏱️'},
        ]
    },
    'fase7': {
        'nombre': 'Aplicación',
        'emoji': '🚀',
        'archivo': 'fase7_index.html',
        'carpeta': 'fase7',
        'estado': 'pendiente',  # se actualiza dinámicamente al cargar el módulo (ver final del fichero)
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',           'archivo': 'fase7_index.html',        'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Dashboard Gestor', 'archivo': 'm01_dashboard_gestor.html','emoji': '📊'},
            {'id': 'm02',    'nombre': 'Vista Profesor',   'archivo': 'm02_vista_profesor.html',  'emoji': '👨‍🏫'},
            {'id': 'm03',    'nombre': 'Vista Alumno',     'archivo': 'm03_vista_alumno.html',    'emoji': '🎓'},
            {'id': 'm04',    'nombre': 'API',              'archivo': 'm04_api.html',             'emoji': '🔌'},
            {'id': 'm05',    'nombre': 'Documentación',    'archivo': 'm05_documentacion.html',   'emoji': '📖'},
        ]
    },
    # ------------------------------------------------------------------
    # ANEXO: Pre-Modelado AutoML (fuera del flujo principal)
    # ------------------------------------------------------------------
    'fase_automl': {
        'nombre': 'Pre-Modelado: AutoML',
        'emoji': '⚡',
        'archivo': 'fase_automl_index.html',
        'carpeta': 'fase_automl',
        'estado': 'activo',
        'modulos': [
            {'id': 'indice', 'nombre': 'Índice',      'archivo': 'fase_automl_index.html', 'emoji': '📋'},
            {'id': 'm01',    'nombre': 'Baselines',   'archivo': 'm01_baselines.html',     'emoji': '📊'},
            {'id': 'm02',    'nombre': 'LazyPredict', 'archivo': 'm02_lazypredict.html',   'emoji': '⚡'},
            {'id': 'm03',    'nombre': 'PyCaret',     'archivo': 'm03_pycaret.html',       'emoji': '🤖'},
            {'id': 'm04',    'nombre': 'H2O',         'archivo': 'm04_h2o.html',           'emoji': '💧'},
            {'id': 'm05',    'nombre': 'AutoGluon',   'archivo': 'm05_autogluon.html',     'emoji': '🚀'},
            {'id': 'm06',    'nombre': 'TabPFN',      'archivo': 'm06_tabpfn.html',        'emoji': '🧠'},
            {'id': 'm07',    'nombre': 'Comparativa', 'archivo': 'm07_comparativa.html',   'emoji': '🏆'},
        ]
    },
}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def obtener_fase_siguiente(fase_id: str) -> Dict:
    """Devuelve info de la fase siguiente."""
    fases_lista = list(FASES.keys())
    try:
        idx = fases_lista.index(fase_id)
        if idx + 1 < len(fases_lista):
            siguiente_id = fases_lista[idx + 1]
            return {
                'id': siguiente_id,
                **FASES[siguiente_id]
            }
    except (ValueError, IndexError):
        pass
    return {}


# ============================================================================
# FUNCIONES PARA TÍTULO DINÁMICO
# ============================================================================

def extraer_titulo_de_fichero(nombre_fichero: str) -> str:
    """
    Extrae título legible del nombre del fichero.

    Ejemplos:
        'f1_m03_reportes_clean.ipynb'    -> 'Reportes Clean'
        'f6_m01a_shap_global.ipynb'      -> 'Shap Global'
        'f6_m01_interpretabilidad_shap'  -> 'Interpretabilidad Shap'
        'f3_m00_indice.ipynb'            -> 'Índice'
        'fautoml_m03_pycaret.ipynb'      -> 'Pycaret'
    """
    nombre = nombre_fichero.replace('.ipynb', '').replace('.html', '')
    # Soportar fautoml_mXX_, fN_mXXa_, fN_mXX_ (submodulos con letra incluidos)
    patron = r'^(?:f\d+|fautoml)_m\d+[a-z]?_'
    nombre = re.sub(patron, '', nombre)

    if nombre.lower() in ['indice', 'resumen', 'index']:
        return 'Índice'

    titulo = nombre.replace('_', ' ').title()
    return titulo


def extraer_fase_de_fichero(nombre_fichero: str) -> str:
    """
    Extrae el ID de fase del nombre del fichero.

    Ejemplos:
        'f1_m03_reportes_clean.ipynb'  -> 'fase1'
        'f6_m01a_shap_global.ipynb'    -> 'fase6'
        'fautoml_m00_indice.ipynb'     -> 'fase_automl'
    """
    if nombre_fichero.startswith('fautoml_'):
        return 'fase_automl'
    match = re.match(r'^f(\d+)_', nombre_fichero)
    if match:
        return f'fase{match.group(1)}'
    return 'fase1'


def extraer_modulo_de_fichero(nombre_fichero: str) -> str:
    """
    Extrae el ID de módulo del nombre del fichero.
    Soporta submodulos con letra: m01a, m01b, m02a...

    Ejemplos:
        'f1_m03_reportes_clean.ipynb'         -> 'm03'
        'f6_m01_interpretabilidad_shap.ipynb' -> 'm01'
        'f6_m01a_shap_global.ipynb'           -> 'm01a'
        'f6_m01b_shap_local.ipynb'            -> 'm01b'
        'f6_m04c_sostenibilidad.ipynb'        -> 'm04c'
        'f3_m00_indice.ipynb'                 -> 'indice'
        'fautoml_m01_baselines.ipynb'         -> 'm01'
    """
    # Soportar fautoml_mXX_ y fN_mXXa_ (con letra opcional)
    match = re.match(r'^(?:f\d+|fautoml)_m(\d+)([a-z]?)_', nombre_fichero)
    if match:
        num  = match.group(1)
        letra = match.group(2)   # '' si no hay letra
        if num == '00' and not letra:
            # m00_indice -> 'indice', m00_preparacion -> 'm00_prep', m00_ejecucion -> 'm00_ejec'
            nombre_lower = nombre_fichero.lower()
            if 'preparacion' in nombre_lower:
                return 'm00_prep'
            if 'ejecucion' in nombre_lower:
                return 'm00_ejec'
            return 'indice'
        return f'm{num}{letra}'
    return 'indice'


def obtener_subtitulo_fase(fase_id: str) -> str:
    """
    Devuelve el subtítulo de la fase.

    Ejemplo:
        'fase3'        -> 'Fase 3: Features | TFM Abandono Universitario'
        'fase_automl'  -> 'Pre-Modelado: AutoML | TFM Abandono Universitario'
    """
    if fase_id not in FASES:
        return 'TFM Abandono Universitario'

    fase = FASES[fase_id]
    nombre = fase['nombre']

    if fase_id == 'fase_automl':
        return f'{nombre} | TFM Abandono Universitario'

    num = fase_id.replace('fase', '')
    return f'Fase {num}: {nombre} | TFM Abandono Universitario'


# ============================================================================
# FUNCIONES DE NAVEGACIÓN
# ============================================================================

def obtener_fases_para_nav(fase_activa: str = None) -> List[Dict]:
    """Devuelve lista de fases para la navegación principal."""
    nav = []
    for fase_id, info in FASES.items():
        nav.append({
            'id': fase_id,
            'nombre': info['nombre'],
            'emoji': info['emoji'],
            'archivo': info['archivo'],
            'carpeta': info.get('carpeta', ''),
            'activo': fase_id == fase_activa,
            'estado': info.get('estado', 'activo')
        })
    return nav


def obtener_modulos_para_nav(fase_id: str, modulo_activo: str = None) -> List[Dict]:
    """Devuelve lista de módulos para la navegación secundaria."""
    if fase_id not in FASES or 'modulos' not in FASES[fase_id]:
        return []

    nav = []
    for mod in FASES[fase_id]['modulos']:
        nav.append({
            'id': mod['id'],
            'nombre': mod['nombre'],
            'emoji': mod.get('emoji', '📄'),
            'archivo': mod['archivo'],
            'activo': mod['id'] == modulo_activo
        })
    return nav


def obtener_info_fase(fase_id: str) -> Dict:
    """Devuelve info completa de una fase."""
    return FASES.get(fase_id, {})


def obtener_info_modulo(fase_id: str, modulo_id: str) -> Dict:
    """Devuelve info de un módulo específico."""
    fase = FASES.get(fase_id, {})
    modulos = fase.get('modulos', [])
    for mod in modulos:
        if mod['id'] == modulo_id:
            return mod
    return {}


# ============================================================================
# GENERACIÓN DE HTML DE NAVEGACIÓN
# ============================================================================

def generar_html_nav_fases(fase_activa: str = None, ruta_base: str = '..') -> str:
    """Genera HTML de navegación de fases."""
    fases = obtener_fases_para_nav(fase_activa)

    html = '<nav class="nav-fases">\n'
    for fase in fases:
        clase = 'active' if fase['activo'] else ''
        if fase['estado'] == 'pendiente':
            clase += ' disabled'

        if fase['id'] == 'inicio':
            href = f'{ruta_base}/index.html'
        else:
            href = f'{ruta_base}/{fase["carpeta"]}/{fase["archivo"]}'

        html += f'  <a href="{href}" class="{clase}">{fase["emoji"]} {fase["nombre"]}</a>\n'

    html += '</nav>'
    return html


def generar_html_nav_modulos(fase_id: str, modulo_activo: str = None) -> str:
    """
    Genera HTML de navegación de módulos de una fase.
    Para fase6: muestra solo los módulos principales (sin submodulos con letra).
    Los submodulos aparecen en la navegación interna de cada principal.
    """
    modulos = obtener_modulos_para_nav(fase_id, modulo_activo)

    if not modulos:
        return ''

    html = '<nav class="nav-modulos">\n'
    for mod in modulos:
        # En fase6 ocultar submodulos (ids con letra al final: m01a, m01b...)
        if fase_id == 'fase6' and re.match(r'^m\d+[a-z]$', mod['id']):
            continue
        clase = 'active' if mod['activo'] else ''
        html += f'  <a href="{mod["archivo"]}" class="{clase}">{mod["emoji"]} {mod["nombre"]}</a>\n'

    html += '</nav>'
    return html


def generar_html_nav_submodulos(fase_id: str, modulo_padre: str, modulo_activo: str = None) -> str:
    """
    Genera HTML de navegación de submodulos dentro de un módulo principal.
    Solo relevante para fase6.

    Ejemplo: modulo_padre='m01' devuelve navegación de m01a, m01b, m01c, m01d

    Parameters
    ----------
    fase_id : str
        ID de la fase (ej. 'fase6')
    modulo_padre : str
        ID del módulo principal (ej. 'm01')
    modulo_activo : str, optional
        ID del submodulo activo (ej. 'm01b')
    """
    if fase_id not in FASES or 'modulos' not in FASES[fase_id]:
        return ''

    # Extraer número del padre para filtrar sus submodulos
    match = re.match(r'^m(\d+)$', modulo_padre)
    if not match:
        return ''
    num_padre = match.group(1)

    html = '<nav class="nav-submodulos">\n'
    encontrado = False
    for mod in FASES[fase_id]['modulos']:
        # Submodulo del padre: mXXa, mXXb, mXXc...
        if re.match(rf'^m{num_padre}[a-z]$', mod['id']):
            clase = 'active' if mod['id'] == modulo_activo else ''
            html += f'  <a href="{mod["archivo"]}" class="{clase}">{mod["emoji"]} {mod["nombre"]}</a>\n'
            encontrado = True

    html += '</nav>'
    return html if encontrado else ''


def generar_html_navegacion_completa(fase_activa: str, modulo_activo: str = None,
                                      ruta_base: str = '..') -> tuple:
    """
    Genera HTML completo de navegación (fases + módulos).

    Returns
    -------
    tuple : (nav_fases_html, nav_modulos_html)
    """
    nav_fases   = generar_html_nav_fases(fase_activa, ruta_base)
    nav_modulos = generar_html_nav_modulos(fase_activa, modulo_activo)

    return nav_fases, nav_modulos


# ============================================================================
# DETECCIÓN DINÁMICA DEL ESTADO DE FASE 7
# ============================================================================
# Fase 7 = app Streamlit. Se detecta su existencia comprobando si hay un
# main.py en la carpeta app/ del proyecto. Si existe → 'activo'; si no → 'pendiente'.
# Esto sustituye al estado hardcoded para que el código funcione en cualquier
# checkout del repositorio (regla absoluta del proyecto: cero hardcodes).

def _detectar_estado_fase7() -> str:
    """
    Detecta dinámicamente el estado de la Fase 7 (app Streamlit).

    Sube niveles desde la ubicación de este fichero hasta encontrar la
    raíz del proyecto (la carpeta que contiene `src/`) y comprueba si
    existe `app/main.py`.

    Returns
    -------
    str
        'activo' si existe `app/main.py` en la raíz del proyecto.
        'pendiente' en caso contrario.
    """
    from pathlib import Path

    aqui = Path(__file__).resolve()
    for parent in aqui.parents:
        # Buscamos la raíz del proyecto (la que tiene src/)
        if (parent / 'src').exists():
            # Desde la raíz, comprobamos la app
            if (parent / 'app' / 'main.py').exists():
                return 'activo'
            return 'pendiente'
    return 'pendiente'


# Aplicar detección dinámica al cargar el módulo
FASES['fase7']['estado'] = _detectar_estado_fase7()
