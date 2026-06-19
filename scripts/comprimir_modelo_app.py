"""
=============================================================================
comprimir_modelo_app.py

Comprime con joblib (compress=3) el modelo GANADOR del proyecto, el unico
que necesita la app Streamlit, para reducir su tamano antes de subirlo a
GitHub.

El nombre del modelo ganador NO esta escrito a mano: se lee dinamicamente de
data/06_evaluacion/metricas_modelo.json (campo "modelo_pkl"), igual que hace
la app. Asi, si en el futuro el modelo ganador cambia (otro dataset, otro
algoritmo), este script comprime automaticamente el correcto sin tocar codigo.

Nota: si el modelo ganador ya pesa poco (p. ej. LightGBM__none.pkl, <1 MB),
el script avisa y no hace nada, porque no necesita compresion.

Llamado por comprimir_modelo_app.bat. Tambien puede ejecutarse directo:
    python comprimir_modelo_app.py
=============================================================================
"""

import json
import sys
from pathlib import Path

import joblib


# -----------------------------------------------------------------------------
# Localizar la raiz del proyecto (sube hasta encontrar carpeta src/)
# -----------------------------------------------------------------------------

def encontrar_root() -> Path:
    """Sube niveles hasta encontrar la carpeta src/, marca de la raiz."""
    actual = Path(__file__).resolve().parent
    for _ in range(6):
        if (actual / "src").is_dir():
            return actual
        actual = actual.parent
    raise FileNotFoundError(
        "No se encontro la raiz del proyecto (carpeta src/). "
        "Coloca este script en la raiz de AU_UJI/."
    )


# -----------------------------------------------------------------------------
# Leer el nombre del modelo ganador desde la fuente de verdad (el JSON)
# -----------------------------------------------------------------------------

def obtener_nombre_modelo_ganador(root: Path) -> str:
    """Lee modelo_pkl de data/06_evaluacion/metricas_modelo.json."""
    ruta_json = root / "data" / "06_evaluacion" / "metricas_modelo.json"
    if not ruta_json.exists():
        raise FileNotFoundError(
            f"No se encontro la fuente de verdad: {ruta_json}\n"
            "Ejecuta antes la Fase 6 para generar metricas_modelo.json."
        )
    with open(ruta_json, encoding="utf-8") as f:
        meta = json.load(f)
    nombre_pkl = meta.get("modelo_pkl")
    if not nombre_pkl:
        raise KeyError(
            "El JSON metricas_modelo.json no contiene el campo 'modelo_pkl'."
        )
    return nombre_pkl


# -----------------------------------------------------------------------------
# Funcion principal
# -----------------------------------------------------------------------------

def main() -> int:
    root = encontrar_root()
    nombre_modelo = obtener_nombre_modelo_ganador(root)
    ruta_pkl = root / "data" / "05_modelado" / "models" / nombre_modelo
    ruta_backup = ruta_pkl.with_suffix(".pkl.bak")

    print("=" * 70)
    print(f" Compresion del modelo ganador: {nombre_modelo}")
    print("=" * 70)

    # 1) Verificar que existe
    if not ruta_pkl.exists():
        print(f"[ERROR] No existe el fichero:")
        print(f"        {ruta_pkl}")
        return 1

    tam_original_mb = ruta_pkl.stat().st_size / 1024 / 1024
    print(f"\nFichero: {ruta_pkl}")
    print(f"Tamano actual: {tam_original_mb:.2f} MB")

    # 2) Si ya esta comprimido o es pequeno (< 30 MB), avisar y salir
    if tam_original_mb < 30:
        print(f"\n[AVISO] El fichero pesa menos de 30 MB.")
        print(f"        No necesita compresion (o ya esta comprimido). No se hace nada.")
        return 0

    # 3) Hacer backup
    print(f"\nCreando backup en: {ruta_backup.name}")
    if ruta_backup.exists():
        ruta_backup.unlink()
    ruta_pkl.rename(ruta_backup)

    # 4) Cargar y volver a guardar comprimido
    try:
        print("Cargando modelo (puede tardar unos segundos)...")
        modelo = joblib.load(ruta_backup)
        print(f"Modelo cargado: {type(modelo).__name__}")

        print("Comprimiendo y guardando (compress=3)...")
        joblib.dump(modelo, ruta_pkl, compress=3)

        tam_nuevo_mb = ruta_pkl.stat().st_size / 1024 / 1024
        reduccion = (1 - tam_nuevo_mb / tam_original_mb) * 100

        print(f"\nTamano nuevo: {tam_nuevo_mb:.2f} MB")
        print(f"Reduccion: {reduccion:.1f}%")

    except Exception as e:
        # Si algo falla, restaurar el original
        print(f"\n[ERROR] {e}")
        print("Restaurando fichero original...")
        if ruta_pkl.exists():
            ruta_pkl.unlink()
        ruta_backup.rename(ruta_pkl)
        return 1

    # 5) Verificar integridad cargando el comprimido
    try:
        print("\nVerificando integridad...")
        modelo_v = joblib.load(ruta_pkl)
        ok = (
            hasattr(modelo_v, "predict")
            and hasattr(modelo_v, "predict_proba")
        )
        if not ok:
            raise RuntimeError("El modelo cargado no tiene predict/predict_proba")
        print("Verificacion OK: predict y predict_proba presentes.")
    except Exception as e:
        print(f"\n[ERROR] La verificacion ha fallado: {e}")
        print("Restaurando original desde backup...")
        ruta_pkl.unlink()
        ruta_backup.rename(ruta_pkl)
        return 1

    # 6) Borrar backup (todo OK)
    print(f"\nBorrando backup {ruta_backup.name} (todo correcto)...")
    ruta_backup.unlink()

    print("\n" + "=" * 70)
    print(" Listo. El modelo ya esta comprimido y listo para subir a GitHub.")
    print("=" * 70)
    return 0


# -----------------------------------------------------------------------------
# Entrada
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
