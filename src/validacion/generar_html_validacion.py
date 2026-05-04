# ============================================================================
# GENERAR_HTML_VALIDACION.PY — Informe HTML de validación de Excel
# ============================================================================
# TFM: Predicción de Abandono Universitario UJI
#
# PROPÓSITO
# ---------
# Convierte el dict de resultados de `ejecutar_validacion_completa()` en un
# informe HTML autocontenido (CSS embebido, sin dependencias externas) que se
# guarda en `docs/html/fase0/validacion_excel.html`.
#
# El HTML está diseñado para:
#   • Tribunal del TFM: visión rápida del estado de los datos originales
#   • Futuros investigadores: cómo solicitar nuevos datos a OPP/UADTI
#   • Continuidad del proyecto: trazabilidad de validaciones
#
# DEPENDENCIAS
# ------------
# Solo Python estándar. NO requiere Jinja2 ni similares (mantenemos el peso
# del paquete bajo).
# ============================================================================

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from src.config_entorno import RUTA_HTML, EXCEL_PRINCIPAL, EXCEL_PREINSCRIPCION, BASE_PATH


# ============================================================================
# 1. PALETA DE COLORES (coherente con resto del proyecto)
# ============================================================================
# Reflejan los códigos del proyecto: ver src/config_proyecto.py
# Nota: NO importamos COLORES de config_proyecto para mantener este módulo
# desacoplado (puede ejecutarse aislado en otros entornos).

COLOR_OK         = "#38a169"   # verde — validación pasada
COLOR_WARNING    = "#d69e2e"   # ámbar — aviso (no bloquea)
COLOR_ERROR      = "#e53e3e"   # rojo  — fallo bloqueante
COLOR_NO_EJEC    = "#a0aec0"   # gris  — no ejecutado
COLOR_PRINCIPAL  = "#3182ce"   # azul  — color de marca del proyecto
COLOR_TEXTO      = "#2d3748"
COLOR_BG_SUAVE   = "#f7fafc"
COLOR_BORDE      = "#e2e8f0"


# ============================================================================
# 2. CSS EMBEBIDO
# ============================================================================
# Responsive + modo claro. Diseñado para imprimir bien también (PDF).

_CSS = f"""
<style>
  * {{
    box-sizing: border-box;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    margin: 0;
    padding: 32px 16px;
    background: {COLOR_BG_SUAVE};
    color: {COLOR_TEXTO};
    line-height: 1.55;
  }}
  .contenedor {{
    max-width: 1100px;
    margin: 0 auto;
    background: #ffffff;
    padding: 32px 40px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }}
  h1 {{
    color: {COLOR_PRINCIPAL};
    margin-top: 0;
    margin-bottom: 8px;
    font-size: 28px;
  }}
  h2 {{
    color: {COLOR_TEXTO};
    border-bottom: 2px solid {COLOR_BORDE};
    padding-bottom: 8px;
    margin-top: 40px;
    font-size: 22px;
  }}
  h3 {{
    color: {COLOR_TEXTO};
    margin-top: 24px;
    margin-bottom: 12px;
    font-size: 18px;
  }}
  .meta {{
    color: #718096;
    font-size: 14px;
    margin-bottom: 24px;
  }}
  .resumen-global {{
    padding: 16px 20px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    margin: 24px 0;
    border-left: 5px solid;
  }}
  .resumen-global.ok    {{ background: #f0fff4; border-left-color: {COLOR_OK};      color: #22543d; }}
  .resumen-global.aviso {{ background: #fffaf0; border-left-color: {COLOR_WARNING}; color: #744210; }}
  .resumen-global.error {{ background: #fff5f5; border-left-color: {COLOR_ERROR};   color: #742a2a; }}

  .grid-niveles {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin: 24px 0;
  }}
  .card-nivel {{
    padding: 16px;
    border-radius: 8px;
    text-align: center;
    border-left: 4px solid;
    background: #ffffff;
    border-top: 1px solid {COLOR_BORDE};
    border-right: 1px solid {COLOR_BORDE};
    border-bottom: 1px solid {COLOR_BORDE};
  }}
  .card-nivel.ok      {{ border-left-color: {COLOR_OK};      background: #f0fff4; }}
  .card-nivel.aviso   {{ border-left-color: {COLOR_WARNING}; background: #fffaf0; }}
  .card-nivel.error   {{ border-left-color: {COLOR_ERROR};   background: #fff5f5; }}
  .card-nivel.noejec  {{ border-left-color: {COLOR_NO_EJEC}; background: #f7fafc; }}

  .card-nivel .icono {{
    font-size: 32px;
    margin-bottom: 4px;
  }}
  .card-nivel .nivel-id {{
    font-weight: 700;
    font-size: 18px;
    margin-bottom: 2px;
  }}
  .card-nivel .titulo {{
    font-size: 13px;
    color: #4a5568;
    margin-bottom: 8px;
  }}
  .card-nivel .stats {{
    font-size: 13px;
    color: #4a5568;
  }}

  details {{
    background: #ffffff;
    border: 1px solid {COLOR_BORDE};
    border-radius: 8px;
    padding: 12px 16px;
    margin: 12px 0;
  }}
  details summary {{
    cursor: pointer;
    font-weight: 600;
    color: {COLOR_TEXTO};
    padding: 4px 0;
  }}
  details summary:hover {{
    color: {COLOR_PRINCIPAL};
  }}
  details[open] summary {{
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid {COLOR_BORDE};
  }}

  ul.mensajes {{
    list-style: none;
    padding-left: 0;
    margin: 8px 0;
  }}
  ul.mensajes li {{
    padding: 6px 10px;
    margin: 4px 0;
    border-radius: 4px;
    font-family: "Consolas", "Monaco", monospace;
    font-size: 13px;
    background: {COLOR_BG_SUAVE};
    border-left: 3px solid {COLOR_BORDE};
  }}
  ul.mensajes li.ok    {{ border-left-color: {COLOR_OK};      }}
  ul.mensajes li.warn  {{ border-left-color: {COLOR_WARNING}; }}
  ul.mensajes li.error {{ border-left-color: {COLOR_ERROR};   }}

  table.detalle {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }}
  table.detalle th, table.detalle td {{
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid {COLOR_BORDE};
  }}
  table.detalle th {{
    background: {COLOR_BG_SUAVE};
    font-weight: 600;
    color: #4a5568;
  }}
  table.detalle tr:hover td {{
    background: {COLOR_BG_SUAVE};
  }}

  .cartel-institucional {{
    background: #ebf8ff;
    border: 1px solid #90cdf4;
    border-left: 5px solid {COLOR_PRINCIPAL};
    padding: 20px 24px;
    border-radius: 8px;
    margin-top: 40px;
  }}
  .cartel-institucional h3 {{
    margin-top: 0;
    color: {COLOR_PRINCIPAL};
  }}
  .cartel-institucional p {{
    margin: 8px 0;
    font-size: 14px;
  }}
  .cartel-institucional .siglas {{
    font-weight: 600;
  }}

  footer {{
    text-align: center;
    color: #a0aec0;
    font-size: 12px;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid {COLOR_BORDE};
  }}
  footer a {{
    color: {COLOR_PRINCIPAL};
    text-decoration: none;
  }}
  footer a:hover {{
    text-decoration: underline;
  }}
</style>
"""


# ============================================================================
# 3. UTILIDADES DE FORMATO (estilo español, autocontenidas)
# ============================================================================
# Se definen aquí en lugar de importar de src.utils.formato para mantener
# este módulo desacoplado del resto del proyecto.

def _bytes_a_mb(num_bytes: int) -> str:
    """
    Convierte bytes a megabytes con 1 decimal y separador decimal español.
    Ejemplo: 29_197_213 → "29,2 MB"
    """
    mb = num_bytes / (1024 * 1024)
    return f"{mb:.1f} MB".replace(".", ",")


def _numero_es(num: int) -> str:
    """
    Formatea un entero con separador de miles estilo español ('.').
    Ejemplo: 109_568 → "109.568"
    """
    # f"{num:,}" da "109,568" → cambiamos coma por punto
    return f"{num:,}".replace(",", ".")


# ============================================================================
# 4. UTILIDADES PARA RENDERIZAR PARTES DEL HTML
# ============================================================================

def _clase_estado(resultado_nivel: Dict[str, Any]) -> str:
    """Devuelve la clase CSS según estado del nivel."""
    if resultado_nivel.get("pasa") is None:
        return "noejec"
    if resultado_nivel.get("pasa") is False:
        return "error"
    if resultado_nivel.get("mensajes_error"):
        return "aviso"
    return "ok"


def _icono_estado(resultado_nivel: Dict[str, Any]) -> str:
    """Icono según estado."""
    clase = _clase_estado(resultado_nivel)
    return {"ok": "✅", "aviso": "⚠️", "error": "❌", "noejec": "⏸️"}[clase]


def _renderizar_card_nivel(resultado: Dict[str, Any]) -> str:
    """Genera la card resumen de un nivel."""
    clase = _clase_estado(resultado)
    icono = _icono_estado(resultado)
    n_ok = len(resultado.get("mensajes_ok", []))
    n_err = len(resultado.get("mensajes_error", []))
    return f"""
    <div class="card-nivel {clase}">
      <div class="icono">{icono}</div>
      <div class="nivel-id">{resultado['nivel']}</div>
      <div class="titulo">{resultado['titulo']}</div>
      <div class="stats">{n_ok} OK · {n_err} avisos</div>
    </div>
    """


def _formatear_mensaje_es(mensaje: str) -> str:
    """
    Reformatea un mensaje del validador a estilo español:
      • Números "29,197,213 bytes" → "29,2 MB"  (cuando hay 'bytes')
      • Números "109,568" (separador de miles inglés) → "109.568"
    
    Trabaja con regex sobre el string final para no tener que tocar el
    validador (separación de responsabilidades: validador genera datos,
    HTML los presenta).
    """
    import re

    # 1) Patrón "<número con comas> bytes" → MB
    def _reemplazar_bytes(match):
        num_str = match.group(1).replace(",", "")
        try:
            num = int(num_str)
            mb = num / (1024 * 1024)
            return f"{mb:.1f} MB".replace(".", ",")
        except ValueError:
            return match.group(0)

    mensaje = re.sub(r"(\d{1,3}(?:,\d{3})+)\s*bytes", _reemplazar_bytes, mensaje)

    # 2) Resto de números con separador de miles inglés "1,234,567" → "1.234.567"
    # Solo afecta a números con AL MENOS una coma (miles), no a decimales sueltos
    def _reemplazar_miles(match):
        return match.group(0).replace(",", ".")

    mensaje = re.sub(r"\d{1,3}(?:,\d{3})+(?!\d)", _reemplazar_miles, mensaje)

    return mensaje


def _renderizar_lista_mensajes(mensajes: List[str], clase: str) -> str:
    """Genera <ul> con los mensajes de OK o de error (formateados al ES)."""
    if not mensajes:
        return ""
    items = "\n".join(
        f'      <li class="{clase}">{_formatear_mensaje_es(m)}</li>'
        for m in mensajes
    )
    return f"    <ul class=\"mensajes\">\n{items}\n    </ul>"


def _renderizar_detalle_nivel(resultado: Dict[str, Any]) -> str:
    """Genera <details> desplegable con todos los mensajes del nivel."""
    icono = _icono_estado(resultado)
    n_ok = len(resultado.get("mensajes_ok", []))
    n_err = len(resultado.get("mensajes_error", []))

    bloque_ok = _renderizar_lista_mensajes(resultado.get("mensajes_ok", []), "ok")
    bloque_err = _renderizar_lista_mensajes(
        resultado.get("mensajes_error", []),
        "warn" if resultado.get("tipo") == "warning" else "error",
    )

    return f"""
    <details>
      <summary>{icono} {resultado['nivel']} — {resultado['titulo']}
      ({n_ok} mensajes OK · {n_err} avisos/errores)</summary>
{bloque_ok}
{bloque_err}
    </details>
    """


# ============================================================================
# 4. RENDERIZADO DEL CARTEL INSTITUCIONAL OPP / UADTI
# ============================================================================

def _renderizar_cartel_institucional() -> str:
    """
    Cartel para futuros investigadores que necesiten datos diferentes
    (otros periodos, otras facultades, otros campos).
    """
    return f"""
    <div class="cartel-institucional">
      <h3>📬 Solicitud de datos adicionales</h3>
      <p>
        Los datos validados en este informe corresponden al periodo del TFM y
        proceden de las siguientes unidades de la Universitat Jaume I:
      </p>
      <p>
        <span class="siglas">OPP</span> — <em>Oficina de Planificació i
        Prospectiva</em><br>
        <span class="siglas">UADTI</span> — <em>Unitat d'Anàlisi i
        Desenvolupament TI</em>
      </p>
      <p>
        Para solicitar datos de otros periodos, otras titulaciones o campos
        adicionales, las personas investigadoras pueden contactar con OPP y
        UADTI a través de los canales institucionales habituales (intranet UJI,
        Confluence/SGD).
      </p>
      <p style="margin-top: 12px; font-size: 13px; color: #4a5568;">
        Si la estructura de los nuevos Excel cambia respecto a la documentada
        aquí, debe actualizarse el contrato en
        <code>src/validacion/contrato_excel.py</code> antes de re-ejecutar
        el validador.
      </p>
    </div>
    """


# ============================================================================
# 5. RENDERIZADO DEL HTML COMPLETO
# ============================================================================

def _renderizar_resumen_global(resultado_completo: Dict[str, Any]) -> str:
    """
    Genera el bloque grande de resumen global (verde/ámbar/rojo) según el
    estado de las 5 validaciones.
    """
    if resultado_completo["bloqueante_fallido"]:
        return f"""
        <div class="resumen-global error">
          ❌ Validación FALLIDA — uno o más niveles bloqueantes (N1-N3) no
          se han superado. <strong>Las fases siguientes NO deberían
          ejecutarse</strong> hasta que se corrijan los problemas.
        </div>
        """

    if resultado_completo["todos_ok"]:
        return f"""
        <div class="resumen-global ok">
          ✅ Validación COMPLETADA con éxito — los 5 niveles han pasado sin
          incidencias. Los Excel originales cumplen el contrato esperado y
          el proyecto puede continuar con Fase 1.
        </div>
        """

    # Pasa los bloqueantes pero hay warnings en N4/N5
    return f"""
    <div class="resumen-global aviso">
      ⚠️ Validación COMPLETADA con avisos — los niveles bloqueantes (N1-N3)
      se han superado, pero hay incidencias menores en N4 y/o N5. El
      proyecto puede continuar, aunque conviene revisar los avisos.
    </div>
    """


def generar_html_validacion(
    resultado_completo: Dict[str, Any],
    ruta_salida: Path = None,
) -> Path:
    """
    Genera el HTML del informe de validación a partir del dict devuelto por
    `ejecutar_validacion_completa()`.

    Parameters
    ----------
    resultado_completo : dict
        Dict con claves: `resultados`, `bloqueante_fallido`, `todos_ok`,
        `resumen_corto`.
    ruta_salida : Path, opcional
        Ruta donde guardar el HTML. Por defecto:
        `docs/html/fase0/validacion_excel.html`

    Returns
    -------
    Path
        Ruta del HTML generado.
    """
    if ruta_salida is None:
        ruta_salida = RUTA_HTML / "fase0" / "validacion_excel.html"

    # Asegurar que la carpeta existe
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # --- Construir bloques HTML ---
    fecha = datetime.now().strftime("%d/%m/%Y a las %H:%M")

    cards_html = "\n".join(
        _renderizar_card_nivel(r) for r in resultado_completo["resultados"]
    )

    detalles_html = "\n".join(
        _renderizar_detalle_nivel(r) for r in resultado_completo["resultados"]
    )

    resumen_global = _renderizar_resumen_global(resultado_completo)
    cartel = _renderizar_cartel_institucional()

    # Info de los ficheros validados (rutas RELATIVAS al proyecto, sin
    # exponer la ubicación absoluta del usuario en disco)
    ruta_principal_rel = EXCEL_PRINCIPAL.relative_to(BASE_PATH).as_posix()
    ruta_preins_rel = EXCEL_PREINSCRIPCION.relative_to(BASE_PATH).as_posix()

    info_ficheros = f"""
    <table class="detalle">
      <thead>
        <tr><th>Fichero</th><th>Ruta (relativa al proyecto)</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Excel principal</strong></td>
          <td><code>{ruta_principal_rel}</code></td>
        </tr>
        <tr>
          <td><strong>Excel preinscripción</strong></td>
          <td><code>{ruta_preins_rel}</code></td>
        </tr>
      </tbody>
    </table>
    """

    # --- HTML completo ---
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Validación de Excel — Fase 0 — TFM Predicción de Abandono UJI</title>
  {_CSS}
</head>
<body>
  <div class="contenedor">

    <h1>📋 Validación de Excel originales — Fase 0</h1>
    <div class="meta">
      TFM: <em>Pronóstico del Éxito y del Abandono en los Títulos de Grado de
      la UJI</em><br>
      Autora: María José Morte<br>
      Fecha de validación: <strong>{fecha}</strong>
    </div>

    {resumen_global}

    <h2>Resumen por niveles</h2>
    <p>
      El validador comprueba 5 niveles. Los niveles 🔴 N1-N3 son
      <strong>bloqueantes</strong> (un fallo aquí impide continuar con
      las fases siguientes). 🟡 N4 y N5 son <strong>avisos</strong> que
      conviene revisar pero no bloquean.
    </p>
    <div class="grid-niveles">
      {cards_html}
    </div>

    <h2>Detalle por nivel</h2>
    <p>
      Despliega cada bloque para ver los mensajes individuales generados
      durante la validación.
    </p>
    {detalles_html}

    <h2>Ficheros validados</h2>
    {info_ficheros}

    {cartel}

    <footer>
      Generado automáticamente por
      <code>src/validacion/generar_html_validacion.py</code><br>
      <a href="https://github.com/mortemj/AU_UJI_v2"
         target="_blank">github.com/mortemj/AU_UJI_v2</a>
    </footer>

  </div>
</body>
</html>
"""

    # --- Escribir fichero ---
    ruta_salida.write_text(html, encoding="utf-8")
    return ruta_salida
