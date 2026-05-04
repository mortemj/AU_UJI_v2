# =============================================================================
# diagnostico_modelo.py
# 
# Script de diagnóstico — responde 3 preguntas a la vez:
#   P1: ¿qué tipo de objeto es el modelo cargado?
#   P2: ¿es un Stacking o un modelo directo?
#   P3: ¿qué otros modelos .pkl tengo entrenados en disco?
# 
# Cómo lanzarlo (desde cmd con conda tfm_abandono activado):
#   cd C:\proyectos\AU_UJI_v2
#   python diagnostico_modelo.py
# 
# Pega la salida COMPLETA en el chat.
# Este script NO modifica nada — solo lee.
# =============================================================================

import json
from pathlib import Path
import sys

# --- Localizar la raíz del proyecto -----------------------------------------
ROOT = Path(__file__).resolve().parent
print("=" * 70)
print(f"📁 ROOT detectado: {ROOT}")
print("=" * 70)

# --- 1. Leer metricas_modelo.json (fuente de verdad) -------------------------
print("\n🔵 [1/4] CONTENIDO DE metricas_modelo.json")
print("-" * 70)
ruta_json = ROOT / "data" / "06_evaluacion" / "metricas_modelo.json"
if ruta_json.exists():
    with open(ruta_json, encoding="utf-8") as f:
        meta = json.load(f)
    # Mostrar solo claves relevantes
    claves_modelo = [
        "modelo_nombre", "modelo_estrategia", "modelo_familia",
        "modelo_pkl", "modelo_descripcion",
        "auc", "f1", "precision", "recall", "accuracy",
    ]
    for clave in claves_modelo:
        if clave in meta:
            print(f"  {clave:25s} = {meta[clave]}")
    pkl_esperado = meta.get("modelo_pkl", "?")
else:
    print(f"  ❌ NO existe: {ruta_json}")
    pkl_esperado = "?"

# --- 2. Listar TODOS los .pkl del directorio de modelos ---------------------
print("\n🔵 [2/4] MODELOS .pkl EN data/05_modelado/models/")
print("-" * 70)
dir_models = ROOT / "data" / "05_modelado" / "models"
if dir_models.exists():
    pkls = sorted(dir_models.glob("*.pkl"))
    print(f"  Total: {len(pkls)} ficheros .pkl\n")
    for pkl in pkls:
        size_mb = pkl.stat().st_size / (1024 * 1024)
        marca = "  ⭐ <-- el ganador según JSON" if pkl.name == pkl_esperado else ""
        print(f"  {pkl.name:50s} ({size_mb:6.2f} MB){marca}")
else:
    print(f"  ❌ NO existe: {dir_models}")

# --- 3. Cargar el modelo ganador y ver su estructura ------------------------
print("\n🔵 [3/4] ESTRUCTURA DEL MODELO GANADOR (cargado desde .pkl)")
print("-" * 70)

# Añadir app/ al path para usar loaders.py de la app
sys.path.insert(0, str(ROOT / "app"))

try:
    from utils.loaders import cargar_modelo
    modelo = cargar_modelo()
    
    print(f"  Tipo de objeto cargado : {type(modelo).__name__}")
    print(f"  Módulo                 : {type(modelo).__module__}")
    
    # ¿Tiene named_steps? (es Pipeline de sklearn)
    if hasattr(modelo, "named_steps"):
        print(f"\n  ✅ Es un Pipeline de sklearn con named_steps:")
        for nombre, paso in modelo.named_steps.items():
            print(f"     - '{nombre}' → {type(paso).__name__} (módulo: {type(paso).__module__})")
        
        # Si tiene un step 'model', miramos qué hay dentro
        if "model" in modelo.named_steps:
            modelo_final = modelo.named_steps["model"]
            print(f"\n  📌 modelo.named_steps['model'] = {type(modelo_final).__name__}")
            
            # ¿Es Stacking?
            if "Stacking" in type(modelo_final).__name__:
                print(f"\n  ⚠️  ES UN STACKING. Estimadores base:")
                if hasattr(modelo_final, "estimators"):
                    for nombre, est in modelo_final.estimators:
                        print(f"     - '{nombre}' → {type(est).__name__}")
                if hasattr(modelo_final, "final_estimator_"):
                    print(f"     meta-learner: {type(modelo_final.final_estimator_).__name__}")
            else:
                print(f"\n  ✅ NO es Stacking — es un modelo directo: {type(modelo_final).__name__}")
    else:
        print(f"\n  ℹ️  NO tiene named_steps — no es Pipeline de sklearn.")
        print(f"     Es un modelo directo: {type(modelo).__name__}")
    
    # ¿Tiene predict_proba?
    if hasattr(modelo, "predict_proba"):
        print(f"\n  ✅ Tiene predict_proba (necesario para SHAP)")
    else:
        print(f"\n  ⚠️  NO tiene predict_proba")
        
except Exception as e:
    print(f"  ❌ Error al cargar modelo: {type(e).__name__}: {e}")

# --- 4. Cargar el pipeline de preprocesamiento ------------------------------
print("\n🔵 [4/4] ESTRUCTURA DEL PIPELINE DE PREPROCESAMIENTO")
print("-" * 70)
try:
    from utils.loaders import cargar_pipeline
    pipeline = cargar_pipeline()
    print(f"  Tipo : {type(pipeline).__name__}")
    if hasattr(pipeline, "named_steps"):
        print(f"  Steps:")
        for nombre, paso in pipeline.named_steps.items():
            print(f"     - '{nombre}' → {type(paso).__name__}")
    if hasattr(pipeline, "feature_names_in_"):
        feats = list(pipeline.feature_names_in_)
        print(f"  Features de entrada : {len(feats)}")
        print(f"  Primeras 5         : {feats[:5]}")
    if hasattr(pipeline, "get_feature_names_out"):
        try:
            feats_out = pipeline.get_feature_names_out()
            print(f"  Features de salida  : {len(feats_out)}")
            print(f"  Primeras 5          : {list(feats_out[:5])}")
        except Exception as e:
            print(f"  get_feature_names_out() falló: {e}")
except Exception as e:
    print(f"  ❌ Error al cargar pipeline: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("✅ DIAGNÓSTICO COMPLETO")
print("=" * 70)
print("\nCopia TODA esta salida y pégala en el chat.")
