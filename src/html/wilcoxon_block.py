"""
Módulo: src/html/wilcoxon_block.py
==================================
Genera el bloque HTML de justificación estadística (test de Wilcoxon)
para incluir en los informes HTML del grupo M01 SHAP.

Lectura DINÁMICA desde data/05_modelado/results/wilcoxon_top3.json
(generado por f5_wilcoxon_top3.ipynb).

Uso:
    from src.html.wilcoxon_block import bloque_wilcoxon_html

    bloque = bloque_wilcoxon_html(ROOT, nombre_ganador)
    contenido = (
        f'<h2>...</h2>'
        + bloque
        + '<p>...</p>'
        + ...
    )

Si el JSON no existe o está corrupto → devuelve string vacío
(el bloque simplemente no se muestra, sin romper el HTML).
"""

import json
from pathlib import Path


def bloque_wilcoxon_html(root: Path, nombre_ganador: str) -> str:
    """
    Genera el bloque HTML de justificación estadística del modelo ganador
    a partir del fichero wilcoxon_top3.json.

    Args:
        root: ruta raíz del proyecto (ROOT detectado en cada notebook).
        nombre_ganador: nombre del modelo ganador (ej: 'LightGBM'),
                        leído típicamente de metricas_modelo.json.

    Returns:
        str con el bloque HTML completo, o '' si el JSON no existe.
    """
    ruta_w = root / 'data' / '05_modelado' / 'results' / 'wilcoxon_top3.json'

    if not ruta_w.exists():
        return ''

    try:
        with open(ruta_w, encoding='utf-8') as fh:
            w = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return ''

    # Filas de la tabla — una por comparación pareada
    filas_w = ''
    for c in w.get('comparaciones', []):
        veredicto = c.get('veredicto', '—')
        color_vrd = '#718096' if veredicto == 'EMPATE TÉCNICO' else '#2c5282'
        filas_w += (
            '<tr>'
            f'<td style="padding:6px 12px">{c["modelo_1"]} vs {c["modelo_2"]}</td>'
            f'<td style="padding:6px 12px;text-align:right;font-variant-numeric:tabular-nums">'
            f'{c["wilcoxon_auc"]["p_value"]:.4f}</td>'
            f'<td style="padding:6px 12px;text-align:right;font-variant-numeric:tabular-nums">'
            f'{c["wilcoxon_f1"]["p_value"]:.4f}</td>'
            f'<td style="padding:6px 12px;color:{color_vrd};font-size:12px">{veredicto}</td>'
            '</tr>'
        )

    # Datos del ganador para la nota de estabilidad
    ms = w.get('mean_std', {})
    auc_std_lgb = ms.get('LightGBM', {}).get('auc_std')
    auc_std_xgb = ms.get('XGBoost', {}).get('auc_std')
    nota_estab = ''
    if auc_std_lgb is not None and auc_std_xgb is not None and auc_std_xgb > 0:
        reduccion = (auc_std_xgb - auc_std_lgb) / auc_std_xgb * 100
        nota_estab = (
            f' AUC std LightGBM = {auc_std_lgb:.4f} vs XGBoost = {auc_std_xgb:.4f} '
            f'(variabilidad {reduccion:.0f}% menor en LightGBM).'
        )

    return (
        '<div style="margin:20px 0 28px;padding:16px 20px;background:#f7fafc;'
        'border:1px solid #e2e8f0;border-left:3px solid #4a5568;border-radius:6px;'
        'font-size:13px;color:#2d3748">'
        f'<div style="font-weight:600;margin-bottom:8px;color:#2d3748">'
        f'🏆 Selección del modelo: justificación estadística</div>'
        f'<p style="margin:0 0 10px;color:#4a5568;line-height:1.5">'
        f'El modelo elegido es <strong>{nombre_ganador}</strong>, '
        f'ganador del proceso de selección dinámica documentado en '
        f'<code>f6_m00_preparacion</code>. La comparación con los otros modelos '
        f'del top mediante test de Wilcoxon pareado '
        f'({w.get("cv_folds", "?")}-fold CV, n_train={w.get("n_train", "?"):,}, '
        f'α={w.get("alpha", 0.05)}) confirma que <em>no existen diferencias '
        f'estadísticamente significativas</em> entre ellos:'
        f'</p>'
        '<table style="width:100%;border-collapse:collapse;font-size:12px;'
        'background:white;border-radius:4px;overflow:hidden">'
        '<thead><tr style="background:#edf2f7;color:#4a5568">'
        '<th style="padding:7px 12px;text-align:left;font-weight:600">Comparación</th>'
        '<th style="padding:7px 12px;text-align:right;font-weight:600">p (AUC)</th>'
        '<th style="padding:7px 12px;text-align:right;font-weight:600">p (F1)</th>'
        '<th style="padding:7px 12px;text-align:left;font-weight:600">Veredicto</th>'
        '</tr></thead>'
        f'<tbody>{filas_w}</tbody></table>'
        f'<p style="margin:10px 0 0;color:#4a5568;line-height:1.5;font-size:12px">'
        f'Al no existir diferencia significativa, se aplica criterio de '
        f'<strong>estabilidad</strong> en validación cruzada.{nota_estab}'
        f'</p>'
        '</div>'
    )
