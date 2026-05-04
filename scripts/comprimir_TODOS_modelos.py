"""
=============================================================================
comprimir_TODOS_modelos.py

Comprime TODOS los .pkl de data/05_modelado/models/ usando joblib con
compress=3 para reducir su tamaño (típicamente 50-70% de reducción).

Esto permite subirlos a GitHub bajo el límite de 100 MB/fichero, y mantener
la reproducibilidad total del proyecto (sistema dinámico opción C).

USO:
    python comprimir_TODOS_modelos.py

CARACTERÍSTICAS:
- Solo comprime ficheros que pesan más de 5 MB (los pequeños no compensa)
- Hace backup .bak antes de cada compresión
- Verifica que el modelo se carga correctamente después
- Si algo falla en uno, conserva el original y sigue con los demás
- Resumen final con totales antes/después

NOTA: joblib carga ficheros comprimidos automáticamente. La app NO necesita
cambios para usar los modelos comprimidos.
=============================================================================
"""

import sys
import time
from pathlib import Path

import joblib


# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

# Solo comprimir ficheros que superen este umbral en MB.
# Ficheros más pequeños no compensa (poco ahorro, joblib ya tiene formato eficiente)
UMBRAL_MB = 5.0

# Nivel de compresión joblib (1-9). 3 es el sweet spot velocidad/tamaño.
NIVEL_COMPRESION = 3


# -----------------------------------------------------------------------------
# Localizar la raíz del proyecto
# -----------------------------------------------------------------------------

def encontrar_root() -> Path:
    """Sube niveles hasta encontrar la carpeta src/, marca de la raiz."""
    actual = Path(__file__).resolve().parent
    for _ in range(6):
        if (actual / "src").is_dir():
            return actual
        actual = actual.parent
    raise FileNotFoundError(
        "No se encontró la raíz del proyecto (carpeta src/). "
        "Coloca este script en la raíz de AU_UJI_v2/."
    )


# -----------------------------------------------------------------------------
# Comprimir un modelo individual
# -----------------------------------------------------------------------------

def comprimir_modelo(ruta_pkl: Path) -> dict:
    """
    Comprime un .pkl in-place (con backup .bak temporal).

    Returns
    -------
    dict con keys:
        'estado'    : 'comprimido' | 'omitido' | 'error'
        'mb_antes'  : tamaño original en MB
        'mb_despues': tamaño comprimido en MB (None si omitido/error)
        'mensaje'   : mensaje informativo
    """
    nombre = ruta_pkl.name
    mb_antes = ruta_pkl.stat().st_size / 1024 / 1024

    # Si está debajo del umbral, omitir
    if mb_antes < UMBRAL_MB:
        return {
            'estado':     'omitido',
            'mb_antes':   mb_antes,
            'mb_despues': mb_antes,
            'mensaje':    f'Omitido (< {UMBRAL_MB} MB)',
        }

    # Crear backup
    ruta_backup = ruta_pkl.with_suffix('.pkl.bak')
    if ruta_backup.exists():
        ruta_backup.unlink()

    try:
        ruta_pkl.rename(ruta_backup)

        # Cargar y guardar comprimido
        modelo = joblib.load(ruta_backup)
        joblib.dump(modelo, ruta_pkl, compress=NIVEL_COMPRESION)
        mb_despues = ruta_pkl.stat().st_size / 1024 / 1024

        # Verificar que el comprimido se carga
        modelo_v = joblib.load(ruta_pkl)
        if not (hasattr(modelo_v, 'predict') and hasattr(modelo_v, 'predict_proba')):
            raise RuntimeError('El modelo comprimido no tiene predict/predict_proba')

        # Todo OK, borrar backup
        ruta_backup.unlink()

        reduccion = (1 - mb_despues / mb_antes) * 100
        return {
            'estado':     'comprimido',
            'mb_antes':   mb_antes,
            'mb_despues': mb_despues,
            'mensaje':    f'{mb_antes:.1f} MB -> {mb_despues:.1f} MB (-{reduccion:.0f}%)',
        }

    except Exception as e:
        # Restaurar el original desde backup
        if ruta_pkl.exists():
            ruta_pkl.unlink()
        if ruta_backup.exists():
            ruta_backup.rename(ruta_pkl)

        return {
            'estado':     'error',
            'mb_antes':   mb_antes,
            'mb_despues': None,
            'mensaje':    f'Error: {e}',
        }


# -----------------------------------------------------------------------------
# Función principal
# -----------------------------------------------------------------------------

def main() -> int:
    root = encontrar_root()
    dir_models = root / 'data' / '05_modelado' / 'models'

    if not dir_models.is_dir():
        print(f'[ERROR] No existe la carpeta: {dir_models}')
        return 1

    pkls = sorted(dir_models.glob('*.pkl'))
    if not pkls:
        print(f'[AVISO] No hay .pkl en {dir_models}')
        return 0

    print('=' * 70)
    print(f' Compresión de {len(pkls)} modelos en {dir_models}')
    print(f' Umbral: solo comprimir >= {UMBRAL_MB} MB | Nivel joblib compress={NIVEL_COMPRESION}')
    print('=' * 70)

    inicio = time.time()
    resultados = []

    # Recorrer todos los .pkl
    for i, ruta in enumerate(pkls, 1):
        print(f'\n[{i}/{len(pkls)}] {ruta.name}')
        resultado = comprimir_modelo(ruta)
        resultado['nombre'] = ruta.name
        resultados.append(resultado)
        print(f'    {resultado["mensaje"]}')

    duracion = time.time() - inicio

    # -------------------------------------------------------------------------
    # Resumen
    # -------------------------------------------------------------------------
    print('\n' + '=' * 70)
    print(' RESUMEN')
    print('=' * 70)

    n_comprimidos = sum(1 for r in resultados if r['estado'] == 'comprimido')
    n_omitidos    = sum(1 for r in resultados if r['estado'] == 'omitido')
    n_errores     = sum(1 for r in resultados if r['estado'] == 'error')

    mb_antes_total   = sum(r['mb_antes']   for r in resultados)
    mb_despues_total = sum(r['mb_despues'] for r in resultados if r['mb_despues'])

    print(f'  Comprimidos: {n_comprimidos}')
    print(f'  Omitidos (< {UMBRAL_MB} MB): {n_omitidos}')
    print(f'  Errores: {n_errores}')
    print()
    print(f'  Tamaño total ANTES:   {mb_antes_total:.1f} MB')
    print(f'  Tamaño total DESPUÉS: {mb_despues_total:.1f} MB')
    if mb_antes_total > 0:
        reduccion_total = (1 - mb_despues_total / mb_antes_total) * 100
        print(f'  Reducción total:      -{reduccion_total:.0f}%')
    print()
    print(f'  Tiempo total: {duracion:.1f} segundos')

    # Mostrar errores si los hay
    if n_errores > 0:
        print('\n[ATENCIÓN] Hubo errores en estos ficheros:')
        for r in resultados:
            if r['estado'] == 'error':
                print(f'  - {r["nombre"]}: {r["mensaje"]}')
        print('\nLos originales se han restaurado, no se ha perdido nada.')

    print('\n' + '=' * 70)
    if n_errores == 0:
        print(' ¡LISTO! Todos los modelos están comprimidos y listos para GitHub.')
    else:
        print(' Compresión terminada con algunos errores. Revisa arriba.')
    print('=' * 70)

    return 1 if n_errores > 0 else 0


# -----------------------------------------------------------------------------
# Entrada
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    sys.exit(main())
