# ============================================================================
# src/validacion/__init__.py
# ============================================================================
# TFM: Predicción de Abandono Universitario UJI
#
# Paquete de validación de Fase 0:
#   - contrato_excel.py     : contrato esperado de los 2 Excel originales
#   - validador_excel.py    : funciones N1-N5 (Paso 3, próximo)
#   - generar_html_validacion.py : informe HTML (Paso 4, próximo)
#
# Hace que `src/validacion/` sea un paquete formal de Python (en lugar de un
# namespace package implícito), lo que facilita imports, autocompletado en IDEs
# y empaquetado.
# ============================================================================

# Re-exportar las constantes y utilidades del contrato para imports más cortos:
#   from src.validacion import CONTRATO_EXCEL          (en lugar de
#   from src.validacion.contrato_excel import CONTRATO_EXCEL)
from src.validacion.contrato_excel import (
    CONTRATO_EXCEL,
    CONTRATO_EXCEL_PRINCIPAL,
    CONTRATO_EXCEL_PREINSCRIPCION,
    CRUCES_ESPERADOS,
    TIPO_NUMERICO,
    TIPO_TEXTO,
    TIPO_FECHA,
    TIPO_MIXTO,
    hojas_esperadas,
)

__all__ = [
    "CONTRATO_EXCEL",
    "CONTRATO_EXCEL_PRINCIPAL",
    "CONTRATO_EXCEL_PREINSCRIPCION",
    "CRUCES_ESPERADOS",
    "TIPO_NUMERICO",
    "TIPO_TEXTO",
    "TIPO_FECHA",
    "TIPO_MIXTO",
    "hojas_esperadas",
]
