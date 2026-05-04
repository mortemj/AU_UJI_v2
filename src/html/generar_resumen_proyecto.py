# ============================================================================
# src/html/generar_resumen_proyecto.py
# ============================================================================
#
# Genera el HTML resumen del estado del proyecto y de la última ejecución
# del orquestador maestro.
#
# Uso desde el notebook orquestador_maestro.ipynb (al pulsar "Ver resumen"):
#
#     from src.html.generar_resumen_proyecto import generar_resumen_orquestador
#     generar_resumen_orquestador(resultados=ESTADO['resultados'],
#                                 t_inicio_global=ESTADO['t_inicio_global'],
#                                 parado=ESTADO['parado'])
#
# Uso desde notebook ligero f0_actualizar_resumen.ipynb (sin datos de ejecución):
#
#     from src.html.generar_resumen_proyecto import generar_resumen_orquestador
#     generar_resumen_orquestador()  # solo lee estado del proyecto, no ejecución
#
# La función SIEMPRE genera el HTML, aunque no haya datos. En ese caso muestra
# carteles "Pendiente" o "Sin datos disponibles" en lugar de inventar valores
# (regla absoluta del proyecto: cero hardcodes, nunca inventar).
#
# Patrón de robustez (if existe → datos reales / else → mensaje informativo):
#   - metricas_modelo.json     → modelo ganador, métricas, dataset, periodo
#   - app/main.py              → estado app V2
#   - resultados de ejecución  → tabla de fases (si se llamó tras orquestador)
#
# Esquema de campos reales de metricas_modelo.json (verificado 2026-05-04):
#   - modelo_nombre, modelo_estrategia, modelo_familia, modelo_descripcion
#   - auc, f1, precision, recall, accuracy
#   - n_registros, n_alumnos_unicos, n_titulaciones, n_features, n_test
#   - tasa_abandono, periodo_inicio, periodo_fin
#   - baseline_nombre, baseline_auc, baseline_f1
#   - robustez_calibracion_sostenibilidad: { robustez_temporal, calibracion,
#     sostenibilidad }
# ============================================================================

from datetime import datetime
from pathlib import Path
import json as _json
import time as _time


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def generar_resumen_orquestador(
    resultados: list = None,
    t_inicio_global: float = None,
    parado: bool = False,
    verbose: bool = True,
) -> Path:
    """
    Genera docs/html/orquestador_resumen.html con el resumen de la última
    ejecución del orquestador maestro y el estado actual del proyecto.

    Parameters
    ----------
    resultados : list of dict, optional
        Lista con los resultados de la ejecución del orquestador.
        Cada dict debe tener: id, nombre, ok, info, minutos.
        Si es None, se muestra un cartel "Sin ejecución registrada en
        esta sesión".
    t_inicio_global : float, optional
        Timestamp (time.time()) del inicio de la ejecución del orquestador.
        Si es None, no se muestra "tiempo total".
    parado : bool, optional
        True si la ejecución se detuvo manualmente con "Parar aquí".
        False si se completó hasta el final.
    verbose : bool, optional
        Si True, imprime mensajes de progreso por consola.

    Returns
    -------
    Path
        Ruta del HTML generado.
    """
    # --- Imports de config (centralizados, nunca hardcodeados) ---
    from src.config import (
        BASE_PATH,
        RUTA_HTML, RUTA_EVALUACION, RUTA_MODELADO,
        AUTORA, EMAIL_UOC, EMAIL_UJI, GITHUB_REPO,
        URL_APP_STREAMLIT,
    )

    if verbose:
        print('🔄 Generando orquestador_resumen.html...')

    # =====================================================================
    # PASO 1: Leer datos dinámicos (todo del JSON cuando sea posible)
    # =====================================================================
    # El JSON metricas_modelo.json es la fuente única de verdad. Trae
    # modelo, métricas, dataset, periodo, robustez, calibración y
    # sostenibilidad. NUNCA se hardcodean valores.

    metricas = _leer_json_seguro(RUTA_EVALUACION / 'metricas_modelo.json',
                                 'metricas_modelo.json', verbose)

    # Detección dinámica de fases — fuente única en src/html/estado_proyecto.py
    # Antes esta lógica estaba duplicada con index_generator.py (riesgo de
    # inconsistencias). Ahora se importa desde el módulo centralizado, que
    # contiene las 9 señales del proyecto (F0-F7 + AutoML). Aquí extraemos
    # los 3 booleanos legacy + la lista completa para el bloque visual.
    from src.html.estado_proyecto import detectar_estado_fases
    estados_fases = detectar_estado_fases()
    _estados_dict = {e['id']: e['hecha'] for e in estados_fases}
    fase5_done = _estados_dict['fase5']
    fase6_done = _estados_dict['fase6']
    fase7_done = _estados_dict['fase7']

    # =====================================================================
    # PASO 2: Construir bloques HTML por separado (composables)
    # =====================================================================
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')

    bloques = [
        _bloque_cabecera(metricas),
        _bloque_ejecucion(resultados, t_inicio_global, parado),
        _bloque_modelo(metricas),
        _bloque_dataset(metricas),
        _bloque_robustez(metricas),
        _bloque_estado_fases(estados_fases),
        _bloque_app(fase7_done, URL_APP_STREAMLIT),
        _bloque_acciones(),
    ]

    # =====================================================================
    # PASO 3: Ensamblar HTML completo
    # =====================================================================
    html = _html_completo(
        bloques=bloques,
        fecha_gen=fecha_gen,
        autora=AUTORA,
        email_uoc=EMAIL_UOC,
        email_uji=EMAIL_UJI,
        github_repo=GITHUB_REPO,
    )

    # =====================================================================
    # PASO 4: Guardar
    # =====================================================================
    ruta_salida = RUTA_HTML / 'orquestador_resumen.html'
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(html, encoding='utf-8')

    if verbose:
        print(f'✅ HTML generado: {ruta_salida}')

    return ruta_salida


# ============================================================================
# LECTORES SEGUROS (cero excepciones hacia fuera)
# ============================================================================

def _leer_json_seguro(ruta: Path, etiqueta: str, verbose: bool) -> dict | None:
    """
    Lee un JSON con try/except. Devuelve dict o None.
    Si falla, imprime aviso pero no rompe la ejecución.
    """
    if not ruta.exists():
        if verbose:
            print(f'  ⚠ {etiqueta}: no encontrado en {ruta}')
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except (_json.JSONDecodeError, OSError) as e:
        if verbose:
            print(f'  ⚠ {etiqueta}: error al leer ({e.__class__.__name__})')
        return None


# ============================================================================
# FORMATEADORES NUMÉRICOS ESPAÑOLES
# ============================================================================

def _fmt_decimal(v, decimales: int = 4) -> str:
    """Formato decimal español: coma decimal."""
    if v is None:
        return '—'
    try:
        return f'{float(v):.{decimales}f}'.replace('.', ',')
    except (TypeError, ValueError):
        return str(v)


def _fmt_int(v) -> str:
    """Formato entero español: punto miles."""
    if v is None:
        return '—'
    try:
        return f'{int(v):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return str(v)


def _fmt_pct(v, decimales: int = 2) -> str:
    """Formato porcentaje español. Asume v ya está en escala 0-1."""
    if v is None:
        return '—'
    try:
        return f'{float(v) * 100:.{decimales}f}%'.replace('.', ',')
    except (TypeError, ValueError):
        return str(v)


def _fmt_periodo(metricas: dict | None) -> str:
    """Construye string de periodo con número de años."""
    if not metricas:
        return '—'
    p_ini = metricas.get('periodo_inicio')
    p_fin = metricas.get('periodo_fin')
    if p_ini is None or p_fin is None:
        return '—'
    n_anios = p_fin - p_ini + 1
    return f'{p_ini}–{p_fin} ({n_anios} años)'


# ============================================================================
# BLOQUES HTML — uno por sección lógica
# ============================================================================

def _bloque_cabecera(metricas: dict | None) -> str:
    """Cabecera con título, descripción y periodo dinámico."""
    periodo_txt = _fmt_periodo(metricas)
    periodo_html = (
        f'<p class="descripcion-pagina"><strong>Período cubierto:</strong> '
        f'{periodo_txt}</p>'
    ) if metricas else ''

    return (
        '<section class="bloque bloque-cabecera">'
        '<h1>🎓 Resumen del proyecto — AU_UJI Dinámico (V2)</h1>'
        '<p class="subtitulo-proyecto">'
        'Pronóstico del Éxito y del Abandono en los Títulos de Grado '
        'de la Universitat Jaume I'
        '</p>'
        '<p class="descripcion-pagina">'
        'Esta página muestra el estado actual del proyecto y los '
        'resultados de la última ejecución del orquestador maestro. '
        'Los datos se leen dinámicamente — si una fase aún no se '
        'ha ejecutado, el bloque correspondiente aparece como '
        '<em>«Pendiente»</em>.'
        '</p>'
        f'{periodo_html}'
        '</section>'
    )


def _bloque_ejecucion(resultados: list | None,
                      t_inicio_global: float | None,
                      parado: bool) -> str:
    """Bloque con la tabla de fases ejecutadas (si las hay)."""
    if not resultados:
        return (
            '<section class="bloque">'
            '<h2>▶️ Última ejecución del orquestador</h2>'
            '<div class="aviso-pendiente">'
            'Sin datos de ejecución en esta sesión. '
            'Para registrar una ejecución, abrir '
            '<code>notebooks/fase0_configuracion/orquestador_maestro.ipynb</code> '
            'y pulsar el botón <strong>▶️ Comenzar Fase 1</strong>.'
            '</div>'
            '</section>'
        )

    # Tabla de fases
    n_total = len(resultados)
    n_ok = sum(1 for r in resultados if r.get('ok'))
    n_err = n_total - n_ok

    if t_inicio_global:
        t_total_min = (_time.time() - t_inicio_global) / 60
        tiempo_str = f'{t_total_min:.1f} min'
    else:
        tiempo_str = '—'

    estado_titulo = (
        '⏸️ Ejecución detenida por el usuario' if parado
        else ('🎉 Ejecución completada' if n_err == 0
              else '⚠️ Ejecución completada con errores')
    )
    color_estado = ('#f59e0b' if parado else
                    ('#10b981' if n_err == 0 else '#dc2626'))

    filas_html = []
    for r in resultados:
        icono = '✅' if r.get('ok') else '❌'
        color = '#10b981' if r.get('ok') else '#dc2626'
        filas_html.append(
            f'<tr>'
            f'<td>{icono}</td>'
            f'<td>{r.get("nombre", "—")}</td>'
            f'<td style="color:{color};">{r.get("info", "—")}</td>'
            f'</tr>'
        )

    tabla = (
        '<table class="tabla-ejecucion">'
        '<thead><tr><th>Estado</th><th>Fase</th><th>Resultado</th></tr></thead>'
        '<tbody>' + ''.join(filas_html) + '</tbody>'
        '</table>'
    )

    return (
        '<section class="bloque">'
        f'<h2 style="color:{color_estado};">{estado_titulo}</h2>'
        f'<p class="resumen-numerico">'
        f'<strong>{n_ok}/{n_total}</strong> fases completadas correctamente · '
        f'<strong>{n_err}</strong> con error · '
        f'Tiempo total: <strong>{tiempo_str}</strong></p>'
        f'{tabla}'
        '</section>'
    )


def _bloque_modelo(metricas: dict | None) -> str:
    """Bloque con métricas del modelo ganador. Lee campos reales del JSON."""
    if not metricas:
        return (
            '<section class="bloque">'
            '<h2>🏆 Modelo ganador</h2>'
            '<div class="aviso-pendiente">'
            'Métricas pendientes — ejecuta la <strong>Fase 6</strong> '
            'para generar <code>metricas_modelo.json</code>.'
            '</div>'
            '</section>'
        )

    # --- Lectura defensiva de campos reales del JSON ---
    nombre        = metricas.get('modelo_nombre', '—')
    estrategia    = metricas.get('modelo_estrategia', '')
    familia       = metricas.get('modelo_familia', '')
    descripcion   = metricas.get('modelo_descripcion', '')
    pkl_filename  = metricas.get('modelo_pkl', '')

    auc           = metricas.get('auc')
    f1            = metricas.get('f1')
    precision     = metricas.get('precision')
    recall        = metricas.get('recall')
    accuracy      = metricas.get('accuracy')

    n_test        = metricas.get('n_test')
    n_features    = metricas.get('n_features')
    n_features_t  = metricas.get('n_features_tecnicas')

    # Construcción del nombre con estrategia: "LightGBM (none)"
    nombre_completo = nombre
    if estrategia and estrategia != 'none':
        nombre_completo = f'{nombre} ({estrategia})'

    familia_html = (f' · Familia: <strong>{familia}</strong>'
                    if familia else '')
    pkl_html = (f' · Fichero: <code>{pkl_filename}</code>'
                if pkl_filename else '')
    descripcion_html = (f'<p class="modelo-descripcion">{descripcion}</p>'
                        if descripcion else '')

    # Suffix de features: "24 (27 técnicas)"
    if n_features and n_features_t and n_features != n_features_t:
        features_str = f'{_fmt_int(n_features)} ({_fmt_int(n_features_t)} técnicas)'
    else:
        features_str = _fmt_int(n_features)

    kpis = [
        ('AUC-ROC',   _fmt_decimal(auc),       '#3182ce'),
        ('F1-score',  _fmt_decimal(f1),        '#10b981'),
        ('Precisión', _fmt_decimal(precision), '#805ad5'),
        ('Recall',    _fmt_decimal(recall),    '#ed8936'),
        ('Accuracy',  _fmt_decimal(accuracy),  '#319795'),
    ]

    kpis_html = ''.join(
        f'<div class="kpi"><div class="value" style="color:{c};">{v}</div>'
        f'<div class="label">{l}</div></div>'
        for l, v, c in kpis
    )

    return (
        '<section class="bloque">'
        '<h2>🏆 Modelo ganador</h2>'
        f'<p class="modelo-nombre">'
        f'<strong>{nombre_completo}</strong>'
        f'{familia_html}'
        f'{pkl_html}'
        f'</p>'
        f'<p class="modelo-detalle">'
        f'Entrenado sobre <strong>{_fmt_int(n_test)}</strong> casos de test '
        f'con <strong>{features_str}</strong> features.'
        f'</p>'
        f'{descripcion_html}'
        f'<div class="kpis">{kpis_html}</div>'
        '</section>'
    )


def _bloque_dataset(metricas: dict | None) -> str:
    """Bloque con info del dataset modelado. Lee del JSON, no del parquet."""
    if not metricas:
        return (
            '<section class="bloque">'
            '<h2>📊 Dataset modelado</h2>'
            '<div class="aviso-pendiente">'
            'Dataset pendiente — ejecuta la <strong>Fase 6</strong> '
            'para generar <code>metricas_modelo.json</code> con la información '
            'del dataset.'
            '</div>'
            '</section>'
        )

    n_registros      = metricas.get('n_registros')
    n_alumnos_unicos = metricas.get('n_alumnos_unicos')
    n_titulaciones   = metricas.get('n_titulaciones')
    tasa_abandono    = metricas.get('tasa_abandono')

    return (
        '<section class="bloque">'
        '<h2>📊 Dataset modelado</h2>'
        '<div class="kpis">'
        f'<div class="kpi"><div class="value" style="color:#3182ce;">'
        f'{_fmt_int(n_registros)}</div><div class="label">Registros</div></div>'
        f'<div class="kpi"><div class="value" style="color:#805ad5;">'
        f'{_fmt_int(n_alumnos_unicos)}</div><div class="label">Alumnos únicos</div></div>'
        f'<div class="kpi"><div class="value" style="color:#319795;">'
        f'{_fmt_int(n_titulaciones)}</div><div class="label">Titulaciones</div></div>'
        f'<div class="kpi"><div class="value" style="color:#dc2626;">'
        f'{_fmt_pct(tasa_abandono, 2)}</div><div class="label">Tasa abandono</div></div>'
        '</div></section>'
    )


def _bloque_robustez(metricas: dict | None) -> str:
    """Bloque con métricas de robustez, calibración y sostenibilidad."""
    if not metricas:
        return ''  # No mostrar bloque si no hay datos

    rcs = metricas.get('robustez_calibracion_sostenibilidad')
    if not rcs:
        return ''  # No mostrar bloque si el sub-objeto no está

    rob = rcs.get('robustez_temporal', {})
    cal = rcs.get('calibracion', {})
    sost = rcs.get('sostenibilidad', {})

    # --- Subgrupo: Robustez temporal ---
    auc_media = rob.get('auc_media')
    auc_std   = rob.get('auc_std')
    auc_min   = rob.get('auc_min')
    auc_max   = rob.get('auc_max')
    n_cohortes = rob.get('n_cohortes_evaluadas')

    # --- Subgrupo: Calibración ---
    brier = cal.get('brier_score')
    ece   = cal.get('ece_10_bins')

    # --- Subgrupo: Sostenibilidad ---
    tiempo_alumno = sost.get('tiempo_por_alumno_ms')
    throughput    = sost.get('throughput_alumnos_segundo')
    tamano_kb     = sost.get('tamano_pkl_kb')

    return (
        '<section class="bloque">'
        '<h2>📐 Robustez, calibración y sostenibilidad</h2>'
        '<div class="subbloque">'
        '<h3>🕒 Robustez temporal</h3>'
        '<div class="kpis">'
        f'<div class="kpi"><div class="value" style="color:#3182ce;">'
        f'{_fmt_decimal(auc_media)}</div><div class="label">AUC media</div></div>'
        f'<div class="kpi"><div class="value" style="color:#805ad5;">'
        f'±{_fmt_decimal(auc_std)}</div><div class="label">AUC std</div></div>'
        f'<div class="kpi"><div class="value" style="color:#10b981;">'
        f'[{_fmt_decimal(auc_min, 3)}; {_fmt_decimal(auc_max, 3)}]</div><div class="label">AUC rango</div></div>'
        f'<div class="kpi"><div class="value" style="color:#319795;">'
        f'{_fmt_int(n_cohortes)}</div><div class="label">Cohortes</div></div>'
        '</div></div>'
        '<div class="subbloque">'
        '<h3>🎯 Calibración</h3>'
        '<div class="kpis">'
        f'<div class="kpi"><div class="value" style="color:#3182ce;">'
        f'{_fmt_decimal(brier)}</div><div class="label">Brier score</div></div>'
        f'<div class="kpi"><div class="value" style="color:#805ad5;">'
        f'{_fmt_decimal(ece)}</div><div class="label">ECE (10 bins)</div></div>'
        '</div></div>'
        '<div class="subbloque">'
        '<h3>🌱 Sostenibilidad</h3>'
        '<div class="kpis">'
        f'<div class="kpi"><div class="value" style="color:#3182ce;">'
        f'{_fmt_decimal(tiempo_alumno, 4)}<span class="unidad"> ms</span></div>'
        f'<div class="label">Tiempo por alumno</div></div>'
        f'<div class="kpi"><div class="value" style="color:#10b981;">'
        f'{_fmt_int(throughput)}<span class="unidad"> al/s</span></div>'
        f'<div class="label">Throughput</div></div>'
        f'<div class="kpi"><div class="value" style="color:#805ad5;">'
        f'{_fmt_decimal(tamano_kb, 1)}<span class="unidad"> KB</span></div>'
        f'<div class="label">Tamaño .pkl</div></div>'
        '</div></div>'
        '</section>'
    )


def _bloque_estado_fases(estados_fases: list) -> str:
    """
    Bloque visual con check de cada fase del proyecto (las 9 fases).

    Parameters
    ----------
    estados_fases : list of dict
        Salida de `detectar_estado_fases()` del módulo `src.html.estado_proyecto`.
        Cada dict tiene: id, fase, nombre, estado, color, hecha, actual.

    Returns
    -------
    str
        HTML del bloque <section> con un semáforo por cada fase del proyecto.

    Notes
    -----
    Antes esta función recibía 3 booleanos (fase5_done, fase6_done, fase7_done)
    y mostraba solo esos 3 semáforos. Ahora se alimenta del listado completo
    de las 9 fases detectadas dinámicamente, mostrando un semáforo por cada
    una. La descripción de cada semáforo cita el fichero "señal" que se ha
    detectado en disco (basename) — así el lector sabe qué evidencia se usa
    para considerar la fase completada.
    """
    # Mapa: id_fase → texto descriptivo del semáforo (qué fichero se ha detectado).
    # Se construye a partir de SEÑALES_FASES para no duplicar rutas.
    from src.html.estado_proyecto import SEÑALES_FASES
    descripciones = {
        id_fase: f'Detectado <code>{Path(ruta_rel).name}</code>'
        for id_fase, _, _, ruta_rel in SEÑALES_FASES
    }
    descripciones_pendiente = {
        id_fase: f'Pendiente — falta <code>{Path(ruta_rel).name}</code>'
        for id_fase, _, _, ruta_rel in SEÑALES_FASES
    }

    def _semaforo(estado: dict) -> str:
        """Genera el HTML de un semáforo a partir de un dict de estado."""
        # Icono y color según si la fase está hecha (color OK) o no (gris).
        if estado['hecha']:
            icono = '✅'
            color = '#10b981'  # verde — coincide con COLORES.OK
            descripcion = descripciones.get(estado['id'], '')
        else:
            icono = '⚪'
            color = '#a0aec0'  # gris — coincide con COLORES.PENDIENTE
            descripcion = descripciones_pendiente.get(estado['id'], '')

        # Etiqueta combinando código corto y nombre completo
        # (ej. "F5 — Modelado", "AutoML — Pre-Modelado")
        etiqueta = f'{estado["fase"]} — {estado["nombre"]}'

        return (
            f'<div class="semaforo">'
            f'<div class="semaforo-icono" style="color:{color};">{icono}</div>'
            f'<div><strong>{etiqueta}</strong><br>'
            f'<span class="semaforo-desc">{descripcion}</span></div>'
            f'</div>'
        )

    # Concatenar el HTML de todos los semáforos en orden cronológico
    semaforos_html = ''.join(_semaforo(e) for e in estados_fases)

    return (
        '<section class="bloque">'
        '<h2>🚦 Estado de fases (señales en disco)</h2>'
        '<div class="semaforos">'
        + semaforos_html
        + '</div>'
        + '</section>'
    )


def _bloque_app(fase7_done: bool, url_app: str) -> str:
    """Bloque con enlaces a la app desplegada."""
    estado = '🟢 Activa' if fase7_done else '⚪ Pendiente'
    return (
        '<section class="bloque">'
        '<h2>🌐 Aplicación web</h2>'
        f'<p>Estado del código: <strong>{estado}</strong></p>'
        '<ul class="lista-enlaces">'
        f'<li>👉 <strong>App V2 (esta versión):</strong> '
        f'<a href="{url_app}" target="_blank">{url_app}</a></li>'
        '<li>📦 <strong>Repositorio V2:</strong> '
        '<a href="https://github.com/mortemj/AU_UJI_v2" target="_blank">'
        'https://github.com/mortemj/AU_UJI_v2</a></li>'
        '<li>📖 <strong>Documentación V2:</strong> '
        '<a href="https://mortemj.github.io/AU_UJI_v2/" target="_blank">'
        'https://mortemj.github.io/AU_UJI_v2/</a></li>'
        '<li>🔁 <strong>Versión anterior estable (V1):</strong> '
        '<a href="https://tfm-abandono.streamlit.app" target="_blank">'
        'https://tfm-abandono.streamlit.app</a></li>'
        '</ul>'
        '</section>'
    )


def _bloque_acciones() -> str:
    """Bloque final con instrucciones de cómo refrescar este HTML."""
    return (
        '<section class="bloque bloque-acciones">'
        '<h2>🔄 ¿Cómo actualizar esta página?</h2>'
        '<p>Los datos de esta página se leen dinámicamente cada vez '
        'que se regenera. Para actualizar:</p>'
        '<ol>'
        '<li>Abrir <code>notebooks/fase0_configuracion/'
        'f0_actualizar_resumen.ipynb</code> y ejecutarlo, <strong>o</strong></li>'
        '<li>Re-ejecutar el <code>orquestador_maestro.ipynb</code> '
        'completo, <strong>o</strong></li>'
        '<li>Pulsar el botón <strong>🔄 Refrescar resumen</strong> '
        'al final del orquestador maestro tras una ejecución.</li>'
        '</ol>'
        '</section>'
    )


# ============================================================================
# HTML COMPLETO (página standalone, no usa base.html porque no tiene
# navegación entre fases — es una página de raíz, no una de fase)
# ============================================================================

def _html_completo(bloques: list[str],
                   fecha_gen: str,
                   autora: str,
                   email_uoc: str,
                   email_uji: str,
                   github_repo: str) -> str:
    """Ensambla el HTML completo, autocontenido, sin dependencia de base.html."""
    contenido = '\n'.join(bloques)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resumen del proyecto · AU_UJI Dinámico</title>
<link rel="stylesheet" href="style.css">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 14px; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f7fafc;
  color: #2d3748;
  line-height: 1.6;
}}
.page-wrapper {{
  max-width: 1080px;
  margin: 0 auto;
  padding: 24px;
}}
header.principal {{
  background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
  color: white;
  padding: 24px 0;
  margin-bottom: 24px;
}}
header.principal .interior {{
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 24px;
}}
header.principal h1 {{ font-size: 22px; margin-bottom: 4px; }}
header.principal p {{ font-size: 13px; opacity: 0.9; }}
.bloque {{
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 18px;
}}
.bloque h2 {{
  font-size: 18px;
  color: #1a365d;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid #edf2f7;
}}
.bloque h3 {{
  font-size: 14px;
  color: #2d3748;
  margin-bottom: 10px;
  margin-top: 8px;
}}
.subbloque {{
  margin-bottom: 14px;
}}
.subbloque:last-child {{ margin-bottom: 0; }}
.bloque-cabecera {{
  background: #ebf4ff;
  border-color: #bee3f8;
}}
.bloque-cabecera h1 {{ color: #1a365d; font-size: 24px; margin-bottom: 8px; }}
.bloque-cabecera .subtitulo-proyecto {{
  font-size: 14px; color: #2c5282; margin-bottom: 12px; font-style: italic;
}}
.bloque-cabecera .descripcion-pagina {{
  font-size: 13px; color: #4a5568; margin-bottom: 6px;
}}
.aviso-pendiente {{
  background: #fffaf0;
  border-left: 4px solid #ed8936;
  padding: 12px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #7b341e;
}}
.aviso-pendiente code {{
  background: #fed7aa; padding: 1px 5px; border-radius: 3px;
}}
.kpis {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}}
.kpi {{
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}}
.kpi .value {{ font-size: 20px; font-weight: 700; }}
.kpi .value .unidad {{
  font-size: 11px; color: #718096; font-weight: 500; margin-left: 2px;
}}
.kpi .label {{
  font-size: 11px; color: #718096; margin-top: 4px;
  text-transform: uppercase; letter-spacing: 0.5px;
}}
.modelo-nombre {{ font-size: 14px; margin-bottom: 6px; color: #2d3748; }}
.modelo-detalle {{ font-size: 13px; margin-bottom: 8px; color: #4a5568; }}
.modelo-descripcion {{
  font-size: 12px; color: #718096;
  margin-bottom: 14px; font-style: italic;
}}
.tabla-ejecucion {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
.tabla-ejecucion th {{
  background: #edf2f7;
  text-align: left;
  padding: 8px 10px;
  font-weight: 600;
  color: #2d3748;
  border-bottom: 2px solid #cbd5e0;
}}
.tabla-ejecucion td {{
  padding: 8px 10px;
  border-bottom: 1px solid #edf2f7;
}}
.resumen-numerico {{ font-size: 13px; color: #4a5568; margin-bottom: 12px; }}
.semaforos {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}}
.semaforo {{
  display: flex; gap: 12px;
  background: #f7fafc;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}}
.semaforo-icono {{ font-size: 24px; line-height: 1; }}
.semaforo-desc {{ font-size: 11px; color: #718096; }}
.semaforo code {{
  background: #edf2f7; padding: 1px 4px;
  border-radius: 3px; font-size: 11px;
}}
.lista-enlaces {{ list-style: none; padding-left: 0; }}
.lista-enlaces li {{ padding: 6px 0; font-size: 13px; }}
.lista-enlaces a {{ color: #3182ce; text-decoration: none; }}
.lista-enlaces a:hover {{ text-decoration: underline; }}
.bloque-acciones {{ background: #f0fff4; border-color: #c6f6d5; }}
.bloque-acciones ol {{ padding-left: 24px; font-size: 13px; }}
.bloque-acciones li {{ padding: 4px 0; }}
footer {{
  margin-top: 32px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  font-size: 12px;
  color: #718096;
  text-align: center;
}}
footer a {{ color: #3182ce; text-decoration: none; }}
footer a:hover {{ text-decoration: underline; }}
.boton-volver {{
  display: inline-block;
  margin-bottom: 16px;
  padding: 8px 14px;
  background: white;
  color: #2b6cb0;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  text-decoration: none;
  font-size: 13px;
}}
.boton-volver:hover {{ background: #ebf4ff; }}
</style>
</head>
<body>

<header class="principal">
  <div class="interior">
    <h1>🎓 Resumen del proyecto · AU_UJI Dinámico</h1>
    <p>Estado actual del proyecto y última ejecución del orquestador maestro</p>
  </div>
</header>

<div class="page-wrapper">
  <a href="index.html" class="boton-volver">← Volver al índice principal</a>
  {contenido}

  <footer>
    <strong>{autora}</strong> ·
    <a href="mailto:{email_uoc}">{email_uoc}</a> (UOC) ·
    <a href="mailto:{email_uji}">{email_uji}</a> (UJI) ·
    <a href="{github_repo}" target="_blank">🐙 GitHub</a><br>
    Generado: {fecha_gen}
  </footer>
</div>

</body>
</html>
"""
