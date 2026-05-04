"""
==============================================================================
limpiar_antes_push.py — Limpieza local de ficheros scratch antes de push
==============================================================================

Autora: María José Morte
Proyecto: TFM AU_UJI v2
Fecha: 04/05/2026

Qué hace:
    1. Recorre el proyecto buscando elementos scratch (cachés y notebooks scratch).
    2. Muestra una tabla agrupada con todo lo encontrado (ruta + tamaño).
    3. Pide confirmación explícita antes de borrar.
    4. Borra solo si dices 's'. Resumen final con total liberado.

Salvaguardas:
    - Solo opera dentro de C:\\FF\\AU_UJI_v2 (verifica ROOT antes de empezar).
    - Carpetas protegidas (no se entra a borrarlas como bloque): data/, app/,
      docs/, notebooks/, src/, results/, tests/, scripts/, tribunal/,
      trazabilidad/, contexto/, .git/.
    - Solo borra elementos cuyo NOMBRE EXACTO coincida con la lista cerrada
      de patrones (no acepta wildcards libres tipo *scratch*).

Uso:
    python scripts/limpiar_antes_push.py              # interactivo
    python scripts/limpiar_antes_push.py --dry-run    # solo muestra
==============================================================================
"""

# ----------------------------------------------------------------------------
# Imports estándar (sin dependencias externas)
# ----------------------------------------------------------------------------
import sys
import shutil
from pathlib import Path

# ----------------------------------------------------------------------------
# CONFIGURACIÓN — listas cerradas, modificar con cuidado
# ----------------------------------------------------------------------------

# Raíz del proyecto: el script debe estar en scripts/ dentro de la raíz.
# Si se mueve, hay que ajustar este cálculo.
ROOT = Path(__file__).resolve().parent.parent

# Salvaguarda absoluta: no se opera fuera de esta ruta esperada.
# Si la ruta no coincide, el script se aborta para evitar daños.
RUTA_ESPERADA = Path(r"C:\FF\AU_UJI_v2")

# Nombres EXACTOS de carpetas-caché que se buscan recursivamente y se borran
# allá donde aparezcan (incluyendo dentro de carpetas protegidas).
CACHES_CARPETAS = {
    "__pycache__",          # caché de bytecode Python
    ".pytest_cache",        # caché de pytest
    ".ipynb_checkpoints",   # checkpoints automáticos de Jupyter
}

# Lista CERRADA de ficheros/carpetas scratch que se borran si existen.
# Rutas relativas a ROOT. Añadir nuevos casos solo aquí, nunca con patrones libres.
SCRATCH_ESPECIFICOS = [
    "scripts/COMPROBA_STATIC_NO USO.ipynb",
]

# Carpetas raíz que NO se exploran como bloque (sus cachés internas SÍ).
# Esto es solo informativo: el script igualmente las recorre buscando
# CACHES_CARPETAS dentro, pero nunca borra la carpeta entera.
CARPETAS_PROTEGIDAS = {
    ".git", "data", "app", "docs", "notebooks", "src", "results",
    "tests", "scripts", "tribunal", "trazabilidad", "contexto",
}


# ----------------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------------

def calcular_tamano(ruta: Path) -> int:
    """
    Calcula el tamaño en bytes de un fichero o carpeta (recursivo para carpetas).
    Devuelve 0 si la ruta no existe o no es accesible.
    """
    if not ruta.exists():
        return 0
    if ruta.is_file():
        try:
            return ruta.stat().st_size
        except OSError:
            return 0
    # Si es carpeta, sumar todos los ficheros interiores
    total = 0
    for f in ruta.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def formato_tamano(bytes_: int) -> str:
    """
    Convierte bytes a formato humano legible (KB, MB).
    Ej: 1536 -> '1.5 KB'
    """
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f} KB"
    return f"{bytes_ / (1024 * 1024):.2f} MB"


def buscar_caches() -> list[Path]:
    """
    Recorre todo el proyecto buscando carpetas cuyo nombre coincida
    EXACTAMENTE con CACHES_CARPETAS. Devuelve lista de Path.
    """
    encontradas = []
    # rglob('*') recorre todo, pero filtramos por nombre exacto
    for p in ROOT.rglob("*"):
        if p.is_dir() and p.name in CACHES_CARPETAS:
            encontradas.append(p)
    return encontradas


def buscar_scratch() -> list[Path]:
    """
    Comprueba uno a uno los ficheros/carpetas de SCRATCH_ESPECIFICOS.
    Devuelve solo los que existen.
    """
    encontrados = []
    for rel in SCRATCH_ESPECIFICOS:
        ruta = ROOT / rel
        if ruta.exists():
            encontrados.append(ruta)
    return encontrados


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    # Detectar flag --dry-run
    dry_run = "--dry-run" in sys.argv

    print("=" * 78)
    print("  LIMPIEZA LOCAL ANTES DE GIT PUSH — TFM AU_UJI v2")
    print("=" * 78)
    print()

    # --- Salvaguarda 1: verificar que estamos en la ruta esperada ---
    print(f"📁 Raíz detectada: {ROOT}")
    if ROOT != RUTA_ESPERADA:
        print(f"⚠️  Ruta esperada: {RUTA_ESPERADA}")
        print("❌ ABORTADO: el script no se ejecuta fuera de la raíz esperada.")
        print("   Si has movido el proyecto, edita RUTA_ESPERADA en el script.")
        sys.exit(1)
    print("✅ Salvaguarda OK: dentro de la raíz esperada.")
    print()

    # --- Fase 1: inspección ---
    print("🔍 Buscando elementos a limpiar...")
    print()

    caches = buscar_caches()
    scratch = buscar_scratch()

    if not caches and not scratch:
        print("✅ Nada que limpiar. Disco ya está limpio.")
        return

    # Mostrar tabla agrupada
    total_bytes = 0
    print("-" * 78)
    print("  📂 CACHÉS PYTHON / JUPYTER / PYTEST")
    print("-" * 78)
    if caches:
        for c in sorted(caches):
            tam = calcular_tamano(c)
            total_bytes += tam
            rel = c.relative_to(ROOT)
            print(f"  [{formato_tamano(tam):>10}]  {rel}")
    else:
        print("  (ninguna encontrada)")
    print()

    print("-" * 78)
    print("  📝 SCRATCH ESPECÍFICOS (lista cerrada)")
    print("-" * 78)
    if scratch:
        for s in scratch:
            tam = calcular_tamano(s)
            total_bytes += tam
            rel = s.relative_to(ROOT)
            print(f"  [{formato_tamano(tam):>10}]  {rel}")
    else:
        print("  (ninguno encontrado)")
    print()

    print("=" * 78)
    print(f"  💾 TOTAL A LIBERAR: {formato_tamano(total_bytes)}")
    print(f"  📊 Elementos: {len(caches)} cachés + {len(scratch)} scratch")
    print("=" * 78)
    print()

    # --- Modo dry-run: terminar aquí ---
    if dry_run:
        print("🛑 Modo --dry-run: nada se ha borrado. Salida.")
        return

    # --- Fase 2: confirmación ---
    print("⚠️  ¿Borrar todos los elementos listados?")
    print("   Esto NO afecta a Git ni al repositorio remoto.")
    print("   Solo limpia tu disco local.")
    print()
    respuesta = input("   Escribe 's' para confirmar, cualquier otra cosa para cancelar: ").strip().lower()

    if respuesta != "s":
        print()
        print("🛑 Cancelado. Nada se ha borrado.")
        return

    # --- Fase 3: borrado ---
    print()
    print("🗑️  Borrando...")
    print()

    borrados_ok = 0
    borrados_error = 0

    for elemento in caches + scratch:
        rel = elemento.relative_to(ROOT)
        try:
            if elemento.is_dir():
                shutil.rmtree(elemento)
            else:
                elemento.unlink()
            print(f"   ✅ Borrado: {rel}")
            borrados_ok += 1
        except Exception as e:
            print(f"   ❌ Error borrando {rel}: {e}")
            borrados_error += 1

    print()
    print("=" * 78)
    print(f"  ✅ Borrados OK: {borrados_ok}")
    if borrados_error:
        print(f"  ❌ Errores: {borrados_error}")
    print(f"  💾 Espacio liberado: {formato_tamano(total_bytes)}")
    print("=" * 78)


if __name__ == "__main__":
    main()