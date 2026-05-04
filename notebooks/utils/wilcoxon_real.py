"""
Opción C — Wilcoxon pareado con folds reales.

Carga los modelos XGBoost y LightGBM de disco, ejecuta 5-Fold CV pareado
sobre el train, y aplica Wilcoxon signed-rank test.

Este script es INDEPENDIENTE — no toca ningún notebook.

Uso (en CMD):
    cd C:\\FF\\AU_UJI_v2
    conda activate tfm_abandono
    python wilcoxon_real.py
"""
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score
from scipy import stats

# ── ROOT ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

print('═' * 70)
print('WILCOXON SIGNED-RANK TEST: XGBoost vs LightGBM')
print('═' * 70)

# ── Cargar datos preprocesados (mismos que F5 usa) ───────────────────────────
RUTA = ROOT / 'data' / '05_modelado'
X_train = pd.read_parquet(RUTA / 'X_train_prep.parquet')
y_train = pd.read_parquet(RUTA / 'y_train.parquet').squeeze()

print(f'\nDatos cargados:')
print(f'  X_train_prep: {X_train.shape}')
print(f'  y_train:      {y_train.shape}  (abandono: {(y_train==1).mean()*100:.1f}%)')

# ── Cargar pipelines completos (con preprocesado interno) ────────────────────
# IMPORTANTE: los .pkl en data/05_modelado/models/ son Pipeline objects
# que YA incluyen el preprocesado. Los aplicamos directamente sobre X_train (raw).
RUTA_RAW = ROOT / 'data' / '05_modelado'
X_train_raw = pd.read_parquet(RUTA_RAW / 'X_train.parquet')

# Cargar modelos
modelo_xgb = joblib.load(RUTA / 'models' / 'XGBoost__none.pkl')
modelo_lgb = joblib.load(RUTA / 'models' / 'LightGBM__none.pkl')

print(f'\nModelos cargados desde disco:')
print(f'  ✅ XGBoost__none.pkl')
print(f'  ✅ LightGBM__none.pkl')

# ── 5-Fold CV pareado: mismos folds para ambos modelos ───────────────────────
print(f'\n5-Fold Stratified CV (mismos folds para ambos modelos)...\n')

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

aucs_xgb = []
aucs_lgb = []
f1s_xgb  = []
f1s_lgb  = []

for fold, (idx_tr, idx_va) in enumerate(cv.split(X_train_raw, y_train), 1):
    X_tr = X_train_raw.iloc[idx_tr]
    X_va = X_train_raw.iloc[idx_va]
    y_tr = y_train.iloc[idx_tr]
    y_va = y_train.iloc[idx_va]
    
    # Reentrenar cada modelo en este fold (los .pkl ya entrenados se usan
    # como referencia de configuración; clonamos y reentrenamos en el fold)
    from sklearn.base import clone
    
    m_xgb = clone(modelo_xgb)
    m_xgb.fit(X_tr, y_tr)
    p_xgb = m_xgb.predict_proba(X_va)[:, 1]
    pred_xgb = (p_xgb >= 0.5).astype(int)
    auc_xgb = roc_auc_score(y_va, p_xgb)
    f1_xgb_val = f1_score(y_va, pred_xgb)
    
    m_lgb = clone(modelo_lgb)
    m_lgb.fit(X_tr, y_tr)
    p_lgb = m_lgb.predict_proba(X_va)[:, 1]
    pred_lgb = (p_lgb >= 0.5).astype(int)
    auc_lgb = roc_auc_score(y_va, p_lgb)
    f1_lgb_val = f1_score(y_va, pred_lgb)
    
    aucs_xgb.append(auc_xgb); aucs_lgb.append(auc_lgb)
    f1s_xgb.append(f1_xgb_val); f1s_lgb.append(f1_lgb_val)
    
    diff = auc_xgb - auc_lgb
    print(f'  Fold {fold}: XGB AUC={auc_xgb:.4f}  LGB AUC={auc_lgb:.4f}  Δ={diff:+.4f}')

# ── Resultados ───────────────────────────────────────────────────────────────
print(f'\n{"═" * 70}')
print(f'RESULTADOS')
print(f'{"═" * 70}')
print(f'\nXGBoost  AUC: {np.mean(aucs_xgb):.4f} ± {np.std(aucs_xgb):.4f}')
print(f'LightGBM AUC: {np.mean(aucs_lgb):.4f} ± {np.std(aucs_lgb):.4f}')
print(f'Diferencia media: {np.mean(aucs_xgb) - np.mean(aucs_lgb):+.4f}')

# ── Wilcoxon signed-rank test (pareado) ──────────────────────────────────────
stat_auc, p_auc = stats.wilcoxon(aucs_xgb, aucs_lgb, alternative='two-sided')
stat_f1,  p_f1  = stats.wilcoxon(f1s_xgb,  f1s_lgb,  alternative='two-sided')

print(f'\n┌─────────────────────────────────────────────┐')
print(f'│   WILCOXON SIGNED-RANK TEST (5 folds)       │')
print(f'├─────────────────────────────────────────────┤')
print(f'│ AUC: stat={stat_auc:.4f}  p-value={p_auc:.4f}  │')
print(f'│ F1 : stat={stat_f1:.4f}  p-value={p_f1:.4f}  │')
print(f'└─────────────────────────────────────────────┘')

# ── Veredicto ────────────────────────────────────────────────────────────────
print(f'\n📊 VEREDICTO (α = 0.05):')
for nombre, p in [('AUC', p_auc), ('F1', p_f1)]:
    if p < 0.05:
        print(f'  ❌ {nombre}: p={p:.4f} < 0.05 → DIFERENCIA SIGNIFICATIVA')
    else:
        print(f'  ✅ {nombre}: p={p:.4f} ≥ 0.05 → EMPATE TÉCNICO')

if p_auc >= 0.05 and p_f1 >= 0.05:
    print(f'\n🎯 CONCLUSIÓN: Los modelos son estadísticamente equivalentes en AUC y F1.')
    print(f'   La elección XGBoost vs LightGBM debe basarse en OTROS criterios:')
    print(f'   - Estabilidad (auc_std)')
    print(f'   - Interpretabilidad / fairness')
    print(f'   - Eficiencia / coherencia con app')
elif p_auc < 0.05 or p_f1 < 0.05:
    print(f'\n🎯 CONCLUSIÓN: XGBoost ES significativamente mejor en alguna métrica.')
    print(f'   Es preferible aceptarlo como ganador.')

# ── Guardar resultado para citar en memoria ──────────────────────────────────
import json
resultado = {
    'fecha':            pd.Timestamp.now().isoformat(),
    'modelos':          ['XGBoost__none', 'LightGBM__none'],
    'cv_folds':         5,
    'aucs_xgb':         [round(x, 6) for x in aucs_xgb],
    'aucs_lgb':         [round(x, 6) for x in aucs_lgb],
    'f1s_xgb':          [round(x, 6) for x in f1s_xgb],
    'f1s_lgb':          [round(x, 6) for x in f1s_lgb],
    'wilcoxon_auc':     {'statistic': float(stat_auc), 'p_value': float(p_auc)},
    'wilcoxon_f1':      {'statistic': float(stat_f1),  'p_value': float(p_f1)},
    'conclusion':       'empate' if p_auc >= 0.05 and p_f1 >= 0.05 else 'xgboost_significativo',
}

ruta_json = ROOT / 'data' / '05_modelado' / 'results' / 'wilcoxon_xgb_vs_lgb.json'
ruta_json.parent.mkdir(parents=True, exist_ok=True)
with open(ruta_json, 'w', encoding='utf-8') as f:
    json.dump(resultado, f, indent=2, ensure_ascii=False)

print(f'\n💾 Resultado guardado en:')
print(f'   {ruta_json}')
