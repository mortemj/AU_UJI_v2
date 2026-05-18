# ============================================================================
# DEPENDENCIAS.PY — VALIDACIÓN DE DEPENDENCIAS
# ============================================================================
# TFM: Predicción de Abandono Universitario
# Autora: María José Morte
# ============================================================================
# Sistema para verificar que existen los archivos necesarios antes de ejecutar.
# Evita errores en cascada y da mensajes claros.
#
# NOTA: Todas las rutas se construyen dinámicamente desde src.config_entorno.
# NO hay rutas hardcodeadas como strings.
# ============================================================================

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# ============================================================================
# IMPORTAR RUTAS DE src.config_entorno (FUENTE ÚNICA)
# ============================================================================

try:
    from .config_entorno import (
        RUTA_RAW, RUTA_INTERIM, RUTA_PROCESSED,
        EXCEL_PRINCIPAL, EXCEL_PREINSCRIPCION
    )
    _RUTAS_DISPONIBLES = True
except ImportError:
    _RUTAS_DISPONIBLES = False


# ============================================================================
# DEFINICIÓN DE DEPENDENCIAS POR NOTEBOOK
# ============================================================================

def _get_dependencias() -> Dict[str, Dict]:
    """
    Devuelve el diccionario de dependencias construido dinámicamente.

    Las rutas se calculan desde las constantes de config_entorno,
    garantizando que si cambian las carpetas, esto se actualiza solo.
    """
    if not _RUTAS_DISPONIBLES:
        return {}

    return {
        # === FASE 1 ===
        'f1_m01_reportes_raw': {
            'descripcion': 'Reportes Sweetviz de datos originales',
            'requiere': {
                'archivos': [EXCEL_PRINCIPAL],
                'notebooks': []
            },
            'genera': {
                'archivos': [],
                'metricas': []
            }
        },
        'f1_m02_limpieza': {
            'descripcion': 'Limpieza de datos originales',
            'requiere': {
                'archivos': [
                    EXCEL_PRINCIPAL,
                    EXCEL_PREINSCRIPCION,
                ],
                'notebooks': []
            },
            'genera': {
                'archivos': [
                    RUTA_INTERIM / 'expedientes.parquet',
                    RUTA_INTERIM / 'titulaciones.parquet',
                    RUTA_INTERIM / 'demograficos.parquet',
                    RUTA_INTERIM / 'domicilios.parquet',
                    RUTA_INTERIM / 'becas.parquet',
                    RUTA_INTERIM / 'trabajo.parquet',
                    RUTA_INTERIM / 'notas.parquet',
                    RUTA_INTERIM / 'recibos.parquet',
                    RUTA_INTERIM / 'preinscripcion.parquet',
                ],
                'metricas': ['fase1_limpieza']
            }
        },
        'f1_m03_reportes_clean': {
            'descripcion': 'Reportes Sweetviz de datos limpios',
            'requiere': {
                'archivos': [],  # se verifican dinámicamente con glob
                'notebooks': ['f1_m02_limpieza']
            },
            'genera': {
                'archivos': [],
                'metricas': []
            }
        },
        'f1_m04a_union_tablas': {
            'descripcion': 'Unión de tablas del Excel principal',
            'requiere': {
                'archivos': [
                    RUTA_INTERIM / 'expedientes.parquet',
                    RUTA_INTERIM / 'titulaciones.parquet',
                    RUTA_INTERIM / 'demograficos.parquet',
                ],
                'notebooks': ['f1_m02_limpieza']
            },
            'genera': {
                'archivos': [RUTA_PROCESSED / 'df_alumno_base.parquet'],
                'metricas': []
            }
        },
        'f1_m04b_union_preinscripcion': {
            'descripcion': 'Añadir preinscripción al dataset',
            'requiere': {
                'archivos': [
                    RUTA_PROCESSED / 'df_alumno_base.parquet',
                    RUTA_INTERIM / 'preinscripcion.parquet',
                ],
                'notebooks': ['f1_m04a_union_tablas']
            },
            'genera': {
                'archivos': [RUTA_PROCESSED / 'df_alumno.parquet'],
                'metricas': ['fase1_union']
            }
        },
        'f1_m05_dashboard': {
            'descripcion': 'Dashboard HTML de la Fase 1',
            'requiere': {
                'archivos': [RUTA_PROCESSED / 'df_alumno.parquet'],
                'notebooks': ['f1_m04b_union_preinscripcion']
            },
            'genera': {
                'archivos': [],
                'metricas': []
            }
        },

        # === FASE 2 - EDA ===
        'f2_m01_inspeccion': {
            'descripcion': 'Inspección inicial del dataset',
            'requiere': {
                'archivos': [RUTA_PROCESSED / 'df_alumno.parquet'],
                'notebooks': ['f1_m04b_union_preinscripcion']
            },
            'genera': {
                'archivos': [],
                'metricas': ['fase2_inspeccion']
            }
        },
        'f2_m02_calidad': {
            'descripcion': 'Análisis de calidad de datos',
            'requiere': {
                'archivos': [RUTA_PROCESSED / 'df_alumno.parquet'],
                'notebooks': ['f1_m04b_union_preinscripcion']
            },
            'genera': {
                'archivos': [],
                'metricas': ['fase2_calidad']
            }
        },
        'f2_m03_nulos': {
            'descripcion': 'Análisis de valores nulos',
            'requiere': {
                'archivos': [RUTA_PROCESSED / 'df_alumno.parquet'],
                'notebooks': ['f1_m04b_union_preinscripcion']
            },
            'genera': {
                'archivos': [],
                'metricas': ['fase2_nulos']
            }
        },
    }


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def verificar_dependencias(
    notebook: str,
    base_path: Optional[Path] = None,
    verbose: bool = True
) -> Tuple[bool, List[str]]:
    """
    Verifica que existen todas las dependencias de un notebook.

    Parameters
    ----------
    notebook : str
        Nombre del notebook (sin extensión): 'f1_m02_limpieza'
    base_path : Path, optional
        Ruta base del proyecto (no se usa si las rutas son absolutas)
    verbose : bool
        Si mostrar mensajes detallados

    Returns
    -------
    Tuple[bool, List[str]]
        (True si todo OK, lista de errores/warnings)
    """
    deps_dict = _get_dependencias()

    if notebook not in deps_dict:
        return True, [f"⚠️ Notebook '{notebook}' no tiene dependencias definidas"]

    deps = deps_dict[notebook]
    errores = []
    warnings_list = []

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🔍 VERIFICANDO DEPENDENCIAS: {notebook}")
        print(f"   {deps['descripcion']}")
        print(f"{'=' * 60}")

    # Verificar archivos requeridos
    archivos_req = deps.get('requiere', {}).get('archivos', [])
    for archivo in archivos_req:
        ruta = Path(archivo)
        if not ruta.exists():
            errores.append(f"❌ No existe: {ruta}")
        elif verbose:
            print(f"   ✅ Existe: {ruta.name}")

    # Verificar notebooks previos
    notebooks_req = deps.get('requiere', {}).get('notebooks', [])
    for nb in notebooks_req:
        if nb in deps_dict:
            archivos_gen = deps_dict[nb].get('genera', {}).get('archivos', [])
            for archivo in archivos_gen:
                if not Path(archivo).exists():
                    warnings_list.append(
                        f"⚠️ Notebook '{nb}' no ejecutado (falta {Path(archivo).name})"
                    )

    # Resumen
    if verbose:
        print(f"\n{'─' * 60}")
        if errores:
            print(f"❌ FALTAN {len(errores)} DEPENDENCIAS:")
            for e in errores:
                print(f"   {e}")
        if warnings_list:
            print(f"⚠️ AVISOS ({len(warnings_list)}):")
            for w in warnings_list:
                print(f"   {w}")
        if not errores and not warnings_list:
            print(f"✅ TODAS LAS DEPENDENCIAS OK")
        print(f"{'=' * 60}\n")

    return len(errores) == 0, errores + warnings_list


def verificar_antes_de_ejecutar(
    notebook: str, base_path: Optional[Path] = None
) -> bool:
    """
    Verifica dependencias y detiene si faltan.

    Raises
    ------
    RuntimeError
        Si faltan dependencias críticas
    """
    ok, errores = verificar_dependencias(notebook, base_path, verbose=True)

    if not ok:
        errores_criticos = [e for e in errores if e.startswith('❌')]
        if errores_criticos:
            raise RuntimeError(
                f"\n\n🚨 NO SE PUEDE EJECUTAR '{notebook}'\n"
                f"   Faltan {len(errores_criticos)} dependencias críticas.\n"
                f"   Ejecuta primero los notebooks anteriores.\n"
            )

    return True


def listar_orden_ejecucion(fase: Optional[str] = None) -> List[str]:
    """
    Devuelve el orden correcto de ejecución de notebooks.

    Parameters
    ----------
    fase : str, optional
        Filtrar por fase: 'fase1', 'fase2', etc.
    """
    orden_fase1 = [
        'f1_m01_reportes_raw',
        'f1_m02_limpieza',
        'f1_m03_reportes_clean',
        'f1_m04a_union_tablas',
        'f1_m04b_union_preinscripcion',
        'f1_m05_dashboard',
    ]

    orden_fase2 = [
        'f2_m01_inspeccion',
        'f2_m02_calidad',
        'f2_m03_nulos',
    ]

    if fase == 'fase1':
        return orden_fase1
    elif fase == 'fase2':
        return orden_fase2

    return orden_fase1 + orden_fase2


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _detectar_base_path() -> Path:
    """Detecta la ruta base del proyecto buscando src/."""
    cwd = Path.cwd()

    # Buscar hacia arriba
    for parent in [cwd] + list(cwd.parents):
        if (parent / 'src').exists() and (parent / 'data').exists():
            return parent

    return cwd


def que_puedo_ejecutar(base_path: Optional[Path] = None) -> Dict[str, bool]:
    """Muestra qué notebooks se pueden ejecutar ahora."""
    print(f"\n{'=' * 60}")
    print(f"📋 ESTADO DE NOTEBOOKS")
    print(f"{'=' * 60}")

    resultado = {}
    for notebook in listar_orden_ejecucion():
        ok, _ = verificar_dependencias(notebook, base_path, verbose=False)
        resultado[notebook] = ok
        estado = "✅ Listo" if ok else "⏳ Pendiente"
        print(f"   {estado} — {notebook}")

    print(f"{'=' * 60}\n")
    return resultado
