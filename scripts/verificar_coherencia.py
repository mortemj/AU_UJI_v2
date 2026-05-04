"""
=============================================================================
verificar_coherencia.py
=============================================================================
Script de verificación MANUAL para complementar la auditoría automática.

EJECUCIÓN:
    cd "C:\\Users\\mjmor\\OneDrive - Universitat Jaume I\\2.- AU_UJI"
    python verificar_coherencia.py

QUÉ HACE:
    Verifica las cosas que el análisis estático del código NO puede detectar:

      1. Fechas de modificación de los ficheros clave (parquets, .pkl, .json)
      2. Coherencia entre el modelo activo del JSON y las fechas
      3. Si meta_test_app.parquet tiene la columna prob_abandono
      4. Si la huella probs_modelo_pkl coincide con modelo_pkl
      5. Detección de ficheros desincronizados (modelo más nuevo que parquet)

QUÉ NO HACE:
    No modifica nada. Solo lee y diagnostica.

SALIDA:
    Imprime un informe de verificación y guarda un .json con el resultado.
=============================================================================
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# CONFIGURACIÓN — ajustar ROOT si se ejecuta desde otra carpeta
# -----------------------------------------------------------------------------
ROOT = Path.cwd()
# Subir niveles hasta encontrar src/
for _ in range(6):
    if (ROOT / "src").exists() or (ROOT / "data").exists():
        break
    ROOT = ROOT.parent

print(f"📂 ROOT detectado: {ROOT}\n")

DATA = ROOT / "data"
RESULTS = ROOT / "results"

# Ficheros a verificar
FICHEROS = {
    "metricas_modelo.json":       DATA / "06_evaluacion" / "metricas_modelo.json",
    "meta_test.parquet":          DATA / "06_evaluacion" / "meta_test.parquet",
    "meta_test_app.parquet":      DATA / "06_evaluacion" / "meta_test_app.parquet",
    "pipeline_preprocesamiento.pkl": DATA / "05_modelado" / "pipeline_preprocesamiento.pkl",
    "X_test_prep.parquet":        DATA / "05_modelado" / "X_test_prep.parquet",
    "X_test.parquet":             DATA / "05_modelado" / "X_test.parquet",
    "fairness_metricas.parquet":  RESULTS / "fase6" / "fairness_metricas.parquet",
}

# -----------------------------------------------------------------------------
# UTILIDADES
# -----------------------------------------------------------------------------
def fmt_fecha(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def fmt_size(bytes_):
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    return f"{bytes_/1024**2:.1f} MB"

def banner(texto, char="="):
    print(char * 78)
    print(f"  {texto}")
    print(char * 78)

# -----------------------------------------------------------------------------
# CHECK 1 — Existencia y fechas de ficheros clave
# -----------------------------------------------------------------------------
banner("CHECK 1 — Existencia y fechas de ficheros clave")

resultado = {"checks": [], "modelo_activo": None, "errores": [], "warnings": []}

fechas = {}
for nombre, ruta in FICHEROS.items():
    if not ruta.exists():
        print(f"  ❌ NO EXISTE: {nombre}  →  {ruta}")
        resultado["errores"].append(f"Falta: {nombre}")
        continue
    stat = ruta.stat()
    fechas[nombre] = stat.st_mtime
    print(f"  ✅ {nombre:<40} {fmt_fecha(stat.st_mtime)}  ({fmt_size(stat.st_size)})")
    resultado["checks"].append({
        "fichero": nombre,
        "ruta": str(ruta),
        "existe": True,
        "fecha_modificacion": fmt_fecha(stat.st_mtime),
        "tamano_bytes": stat.st_size,
    })

# -----------------------------------------------------------------------------
# CHECK 2 — Modelo activo y fechas relativas
# -----------------------------------------------------------------------------
print()
banner("CHECK 2 — Modelo activo (lectura del JSON)")

ruta_json = FICHEROS["metricas_modelo.json"]
if ruta_json.exists():
    with open(ruta_json, encoding="utf-8") as f:
        meta = json.load(f)
    modelo_pkl = meta.get("modelo_pkl", "?")
    print(f"  📌 Modelo activo: {modelo_pkl}")
    print(f"     Familia: {meta.get('modelo_familia', '?')}")
    print(f"     AUC:     {meta.get('auc', '?')}")
    print(f"     F1:      {meta.get('f1', '?')}")
    print(f"     n_test:  {meta.get('n_test', '?')}")
    resultado["modelo_activo"] = modelo_pkl

    # Verificar que el .pkl del modelo activo existe
    ruta_modelo = DATA / "05_modelado" / "models" / modelo_pkl
    if ruta_modelo.exists():
        stat = ruta_modelo.stat()
        fechas[modelo_pkl] = stat.st_mtime
        print(f"\n  ✅ {modelo_pkl} existe  ({fmt_fecha(stat.st_mtime)}, {fmt_size(stat.st_size)})")
    else:
        print(f"\n  🔴 ERROR: {modelo_pkl} no existe en {ruta_modelo}")
        resultado["errores"].append(f"Modelo {modelo_pkl} declarado en JSON pero no existe")

    # Verificar huella probs_modelo_pkl
    probs_modelo = meta.get("probs_modelo_pkl")
    probs_fecha = meta.get("probs_fecha_calculo")
    if probs_modelo:
        coherente = probs_modelo == modelo_pkl
        icono = "✅" if coherente else "🔴"
        print(f"\n  {icono} Huella probs_modelo_pkl: {probs_modelo}")
        print(f"     Calculadas el: {probs_fecha}")
        if not coherente:
            print(f"     🔴 INCOHERENCIA: el parquet tiene probs de {probs_modelo} "
                  f"pero el modelo activo es {modelo_pkl}")
            print(f"     ➜  Solución: ejecutar f6_m00c_export_probs.ipynb")
            resultado["errores"].append(
                f"meta_test_app.parquet desincronizado: probs={probs_modelo}, modelo={modelo_pkl}"
            )
    else:
        print(f"\n  ⚠️ El JSON no tiene huella probs_modelo_pkl. "
              f"Ejecuta f6_m00c_export_probs.ipynb para añadirla.")
        resultado["warnings"].append("Falta huella probs_modelo_pkl en JSON")

# -----------------------------------------------------------------------------
# CHECK 3 — Coherencia de fechas (orden esperado)
# -----------------------------------------------------------------------------
print()
banner("CHECK 3 — Orden esperado de fechas de modificación")

# El orden esperado de generación (cronológico):
#   1. .pkl del modelo (Fase 5)
#   2. metricas_modelo.json (Fase 6 m00, después del modelo)
#   3. meta_test.parquet (Fase 6 m00)
#   4. meta_test_app.parquet (Fase 6 m00b + m00c)
#
# Si meta_test_app es ANTERIOR al modelo, hay desincronización

orden_esperado = [
    ("pipeline_preprocesamiento.pkl", "1. Pipeline (Fase 5)"),
    ("metricas_modelo.json",          "2. JSON métricas (Fase 6 m00)"),
    ("meta_test.parquet",             "3. meta_test (Fase 6 m00)"),
    ("meta_test_app.parquet",         "4. meta_test_app (Fase 6 m00c)"),
    ("fairness_metricas.parquet",     "5. fairness (Fase 6 m03)"),
]

for nombre, descripcion in orden_esperado:
    if nombre in fechas:
        print(f"  {descripcion:<40}  {fmt_fecha(fechas[nombre])}")

# Verificación clave: meta_test_app debe ser POSTERIOR al modelo
modelo_nombre = resultado.get("modelo_activo")
if modelo_nombre and modelo_nombre in fechas and "meta_test_app.parquet" in fechas:
    fecha_modelo = fechas[modelo_nombre]
    fecha_parquet = fechas["meta_test_app.parquet"]
    if fecha_parquet < fecha_modelo:
        print(f"\n  🔴 ALERTA: meta_test_app.parquet ({fmt_fecha(fecha_parquet)}) es ANTERIOR "
              f"al modelo {modelo_nombre} ({fmt_fecha(fecha_modelo)})")
        print(f"     ➜  El parquet contiene probs de un modelo viejo. Ejecuta f6_m00c.")
        resultado["errores"].append("meta_test_app.parquet anterior al modelo activo")
    else:
        delta_min = (fecha_parquet - fecha_modelo) / 60
        print(f"\n  ✅ meta_test_app.parquet es {delta_min:.0f} min posterior al modelo activo  ✓")

# -----------------------------------------------------------------------------
# CHECK 4 — Contenido de meta_test_app.parquet
# -----------------------------------------------------------------------------
print()
banner("CHECK 4 — Contenido de meta_test_app.parquet")

try:
    import pandas as pd
    ruta = FICHEROS["meta_test_app.parquet"]
    if ruta.exists():
        df = pd.read_parquet(ruta)
        print(f"  Shape: {df.shape}")
        print(f"  Columnas: {len(df.columns)}")
        cols = list(df.columns)
        if "prob_abandono" in cols:
            print(f"  ✅ Columna 'prob_abandono' presente")
            print(f"     Rango: [{df['prob_abandono'].min():.4f}, {df['prob_abandono'].max():.4f}]")
            print(f"     Media: {df['prob_abandono'].mean():.4f}")
            tasa_real = df['abandono'].mean() if 'abandono' in cols else None
            if tasa_real is not None:
                diff = abs(df['prob_abandono'].mean() - tasa_real)
                print(f"     Tasa real abandono: {tasa_real:.4f}")
                print(f"     Diferencia (|media_pred - tasa_real|): {diff:.4f}")
                if diff > 0.05:
                    print(f"     ⚠️ Diferencia > 5% — modelo posiblemente mal calibrado")
                    resultado["warnings"].append(f"Calibración: diff = {diff:.4f}")
                else:
                    print(f"     ✅ Modelo bien calibrado (diff ≤ 5%)")
        else:
            print(f"  🔴 Falta columna 'prob_abandono' — ejecuta f6_m00c_export_probs.ipynb")
            resultado["errores"].append("meta_test_app.parquet sin prob_abandono")
except ImportError:
    print(f"  ⚠️ pandas no disponible. Saltando este check.")
except Exception as e:
    print(f"  🔴 Error leyendo parquet: {e}")
    resultado["errores"].append(f"Error meta_test_app: {e}")

# -----------------------------------------------------------------------------
# RESUMEN FINAL
# -----------------------------------------------------------------------------
print()
banner("RESUMEN FINAL", "=")

n_err = len(resultado["errores"])
n_warn = len(resultado["warnings"])

if n_err == 0 and n_warn == 0:
    print("\n  🎉 TODO CORRECTO — No se han detectado errores ni warnings")
elif n_err == 0:
    print(f"\n  ✅ Sin errores graves  ({n_warn} warnings)")
    for w in resultado["warnings"]:
        print(f"     ⚠️ {w}")
else:
    print(f"\n  🔴 {n_err} ERRORES detectados:")
    for e in resultado["errores"]:
        print(f"     • {e}")
    if n_warn > 0:
        print(f"\n  ⚠️ {n_warn} warnings:")
        for w in resultado["warnings"]:
            print(f"     • {w}")

# Guardar resultado en JSON
out_json = ROOT / "verificacion_coherencia.json"
resultado["fecha_verificacion"] = datetime.now().isoformat(timespec="seconds")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"\n  📁 Resultado guardado: {out_json}")
print()

# Código de salida: 0 si todo OK, 1 si hay errores
sys.exit(1 if n_err > 0 else 0)
