# =============================================================================
# utils/ui_helpers.py
# Helpers de UI compartidos entre páginas de la app
#
# ¿QUÉ HACE ESTE FICHERO?
#   Centraliza componentes visuales reutilizables (tarjetas KPI, formato de
#   nombres de titulación, etc.) para evitar que distintas páginas dupliquen
#   el mismo código y para que cualquier cambio se propague automáticamente.
#
# CONTENIDO:
#   - _pie_pagina(): pie de página con autoría
#   - _leer_metricas_modelo(): lee metricas_modelo.json (cacheado)
#   - _hex_a_rgba(hex, alpha): convierte hex a rgba con transparencia
#   - _guardia_df_vacio(df, titulo): aviso visual si df está vacío
#   - _clasificar_riesgo(prob): nivel + color + emoji + mensaje
#   - _nombre_titulacion_corto(nombre): acorta nombre quitando "Grado en"
#   - _tarjeta_kpi(...): tarjeta KPI compacta con barra lateral 4px +
#                       sparkline opcional (Chat p00, 28/04/2026)
#
# QUIÉN LA USA:
#   - p00_inicio.py
#   - p01_institucional.py
#   - p02_titulacion.py
#   - utils/pronostico_shared.py (p03, p04)
#
# REFACTOR (Chat p03, 27/04/2026): centralización de funciones que vivían
# duplicadas en distintos ficheros con implementaciones inconsistentes.
# =============================================================================

import _path_setup  # noqa: F401

from config_app import COLORES, COLORES_RIESGO, UMBRALES, APP_CONFIG


# =============================================================================
# HELPER — Pie de página (autoría)
# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): antes había 4 versiones:
#   - p00_inicio.py: función _pie_pagina()
#   - p02_titulacion.py: función _pie_pagina() (idéntica a p00)
#   - p01_institucional.py: bloque inline (no función)
#   - pronostico_shared.py: función _pie_pagina() (añadida ayer)
# Ahora todas usan ESTA, importada desde ui_helpers.


def _pie_pagina():
    """Información de autoría y créditos (usar al final de cada página)."""
    import streamlit as st  # import local: ui_helpers no debería forzar st global
    st.markdown("<br>", unsafe_allow_html=True)  # espaciado
    st.markdown(f"""
    <div style="
        text-align: center;
        font-size: 0.78rem;
        color: {COLORES["texto_suave"]};
        padding: 1rem;
        border-top: 1px solid {COLORES["borde"]};
    ">
        {APP_CONFIG['autora']} &nbsp;·&nbsp;
        {APP_CONFIG['tipo_trabajo']} &nbsp;·&nbsp;
        {APP_CONFIG['universidad_master']} + {APP_CONFIG['universidad_datos']} &nbsp;·&nbsp; {APP_CONFIG['año']}<br>
        <span style="font-size: 0.72rem;">
            {APP_CONFIG['email_master']} &nbsp;·&nbsp; {APP_CONFIG['email_datos']}
        </span>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# HELPER — Leer métricas del modelo desde metricas_modelo.json
# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): antes había 2 copias idénticas en
# p01 y p02. Centralizada aquí. Cacheada con st.cache_data para no releer
# el fichero en cada rerun. NUNCA lanza excepción: devuelve {} si falla.


def _leer_metricas_modelo() -> dict:
    """
    Lee el fichero metricas_modelo.json generado por la Fase 6 (evaluación).

    Returns
    -------
    dict
        Diccionario con las métricas del modelo. Claves típicas:
          - 'tasa_abandono' (float entre 0 y 1)
          - 'f1', 'auc', 'accuracy', 'precision', 'recall' (floats)
          - 'fecha_entrenamiento' (str, opcional)
          - 'modelo' (str, opcional — p.ej. "LightGBM__none", "Stacking__balanced")
          - 'n_alumnos_unicos', 'n_registros', 'n_test' (int, opcional)
        Si el fichero no existe o falla la lectura, devuelve {} (dict vacío).

    Notas
    -----
    - NUNCA lanza excepción: si algo falla, devuelve {} silenciosamente.
      Esto permite que las funciones que lo usen traten la ausencia de
      datos con su propia lógica (ej. mostrar "N/D" o usar fallback).
    """
    try:
        import json as _json
        from config_app import RUTAS as _RUTAS
        ruta_m = _RUTAS.get("metricas_modelo")
        if ruta_m and ruta_m.exists():
            with open(ruta_m, encoding="utf-8") as _f:
                return _json.load(_f)
    except Exception:
        pass
    return {}


# =============================================================================
# HELPER — Formato numérico al estilo español (fmt)
# =============================================================================
# Centralizado en ui_helpers (Chat 30/04/2026) para sustituir los ~145
# `.replace(",", ".")` y `.replace(".", ",")` ad-hoc dispersos por la app.
#
# Convenciones del proyecto:
#     - Separador de miles:    .  (punto)        → 6.725
#     - Separador decimal:     ,  (coma)         → 0,9564
#     - Porcentajes:           29,2% (sin espacio antes del %)
#     - Nulos / NaN / None:    "—"  (em-dash)
#
# La función trabaja con TIPOS EXPLÍCITOS para evitar la ambigüedad sobre
# si un valor está ya en escala porcentual (29.2) o en proporción (0.292).
# Esto era una de las fuentes de error más frecuentes en el proyecto.
#
# RAZÓN DE EXISTIR (Orden 0 del plan de coherencia):
# Antes de quitar los fallbacks hardcoded del tipo `m.get("auc", 0.954)`,
# necesitamos un helper que sepa formatear None/NaN sin romper. El patrón
# correcto es:
#     auc = metricas.get("auc")
#     auc_str = fmt(auc, "decimal", 3)  # devuelve "—" si auc es None
# En lugar de:
#     auc = metricas.get("auc", 0.954)  # hardcode obsoleto
#     auc_str = f"{auc:.3f}".replace(".", ",")


def fmt(valor, tipo: str = "auto", decimales=None, sufijo: str = "") -> str:
    """
    Formatea un número al estilo español (miles con `.`, decimales con `,`).

    Parameters
    ----------
    valor : int | float | None | str-numérico
        Número a formatear. None, NaN o "" devuelven "—".
    tipo : str
        - "auto"        → entero si int, 2 decimales si float
        - "entero"      → 6.725 (sin decimales)
        - "decimal"     → 0,954 (decimales con coma)
        - "porcentaje"  → 29,2% (valor YA en escala 0-100, no multiplica)
        - "proporcion"  → 29,2% (valor en escala 0-1, multiplica por 100)
        - "miles"       → 30.872 (alias de "entero", más legible en código)
    decimales : int, optional
        Nº de decimales. Si None: 0 para entero/miles, 2 para auto/decimal,
        1 para porcentaje/proporcion.
    sufijo : str
        Texto a añadir al final (" alumnos", " €", etc.). El % de los
        porcentajes se añade automáticamente, no hace falta pasarlo aquí.

    Returns
    -------
    str
        Número formateado o "—" si valor no es numérico.

    Examples
    --------
    >>> fmt(6725, "entero")
    '6.725'
    >>> fmt(0.9564, "decimal", 4)
    '0,9564'
    >>> fmt(29.25, "porcentaje", 1)
    '29,3%'
    >>> fmt(0.2925, "proporcion", 1)
    '29,3%'
    >>> fmt(30872, "miles", sufijo=" alumnos")
    '30.872 alumnos'
    >>> fmt(None)
    '—'
    >>> fmt(float('nan'))
    '—'
    """
    # Guarda contra None, NaN o cadena vacía
    if valor is None or valor == "":
        return "—"
    try:
        v = float(valor)
        if v != v:  # NaN check (NaN != NaN)
            return "—"
    except (TypeError, ValueError):
        return "—"

    # Decimales por defecto según tipo
    if decimales is None:
        if tipo in ("entero", "miles"):
            decimales = 0
        elif tipo in ("porcentaje", "proporcion"):
            decimales = 1
        elif tipo == "decimal":
            decimales = 2
        else:  # auto
            decimales = 0 if float(valor).is_integer() else 2

    # Si es proporción, escalar a 0-100
    if tipo == "proporcion":
        v = v * 100

    # Formateo: usamos el formato inglés con coma de miles + punto decimal,
    # y luego intercambiamos los separadores con un placeholder intermedio
    # para no pisar uno con otro:
    #   "6,725.00" → "6§725.00" → "6§725,00" → "6.725,00"
    base = f"{v:,.{decimales}f}"
    base = base.replace(",", "§").replace(".", ",").replace("§", ".")

    # Sufijo según tipo
    if tipo in ("porcentaje", "proporcion"):
        return f"{base}%{sufijo}"
    return f"{base}{sufijo}"


# =============================================================================
# HELPER — Validación de recursos críticos al arrancar (degradación elegante)
# =============================================================================
# Concepto aplicado: GRACEFUL DEGRADATION (degradación elegante)
#
# En ingeniería de software se llama "degradación elegante" al patrón por el
# cual una aplicación que detecta un problema NO se rompe con un error técnico
# crudo, sino que informa al usuario de forma comprensible:
#   1. QUÉ está pasando (sin jerga técnica)
#   2. POR QUÉ es importante (qué función no podrá hacer la app)
#   3. CÓMO solucionarlo (pasos concretos accionables)
#
# Antes (sin degradación elegante):
#   → La app peta con un Traceback de Python y el usuario no entiende nada
#
# Después (con degradación elegante):
#   → La app muestra un cartel amable en azul/naranja explicando la situación
#     y los pasos exactos para que el usuario lo arregle por sí mismo.
#
# Referencia académica: Nielsen, J. (1994). "Heuristic Evaluation of User
# Interfaces" — heurística #9: "Help users recognize, diagnose, and recover
# from errors". Norman, D. (1988). "The Design of Everyday Things" — capítulo
# sobre error messages.


def validar_recursos_app() -> tuple[bool, list[dict]]:
    """
    Valida que los recursos críticos de la app estén disponibles y tengan
    el formato esperado. Devuelve si todo está OK + lista de problemas.

    Aplica el patrón de degradación elegante: si algo falla, no levanta
    excepciones, sino que devuelve información estructurada para mostrar
    un mensaje amable al usuario.

    Returns
    -------
    (ok, problemas) : tuple[bool, list[dict]]
        - ok: True si todo está bien, False si hay problemas críticos
        - problemas: lista de diccionarios con la información de cada
          problema detectado. Cada diccionario tiene:
            - "que":     descripción del problema (sin jerga técnica)
            - "por_que": consecuencia para el usuario
            - "como":    pasos concretos para solucionarlo
            - "tecnico": detalle técnico (oculto en expander)
    """
    problemas = []

    # 1. metricas_modelo.json existe
    try:
        from config_app import RUTAS as _RUTAS
        ruta_json = _RUTAS.get("metricas_modelo")
        if not ruta_json or not ruta_json.exists():
            problemas.append({
                "que":     "No se encuentra el fichero de métricas del modelo",
                "por_que": ("La app necesita conocer las métricas del modelo "
                            "(AUC, F1, tasa de abandono, etc.) para mostrar "
                            "los indicadores y la guía semántica."),
                "como":    ("1. Abre Jupyter\n"
                            "2. Ejecuta el notebook "
                            "`notebooks/fase6_evaluacion/f6_m00_preparacion.ipynb`\n"
                            "3. Verifica que se haya generado "
                            "`data/06_evaluacion/metricas_modelo.json`\n"
                            "4. Recarga esta página"),
                "tecnico": f"Ruta esperada: {ruta_json}",
            })
            # Si no existe el JSON, no podemos validar las claves; salimos aquí
            return (False, problemas)
    except Exception as e:
        problemas.append({
            "que":     "No se puede acceder a la configuración de la app",
            "por_que": ("Hay un problema técnico al cargar las rutas de los "
                        "ficheros de la app."),
            "como":    ("1. Comprueba que `app/config_app.py` no esté corrupto\n"
                        "2. Reinicia Streamlit"),
            "tecnico": f"{type(e).__name__}: {e}",
        })
        return (False, problemas)

    # 2. El JSON tiene las claves obligatorias y son del tipo correcto
    metricas = _leer_metricas_modelo()
    claves_obligatorias = {
        "tasa_abandono":      (float, "Tasa de abandono del dataset (proporción 0-1)"),
        "auc":                (float, "AUC del modelo"),
        "f1":                 (float, "F1-Score del modelo"),
        "n_test":             (int,   "Número de alumnos del conjunto de test"),
        "n_alumnos_unicos":   (int,   "Número de alumnos únicos del dataset"),
        "n_registros":        (int,   "Número de registros del dataset"),
        "modelo_pkl":         (str,   "Nombre del fichero del modelo activo"),
        "modelo_familia":     (str,   "Familia del modelo (Gradient Boosting, etc.)"),
    }

    claves_faltantes = []
    claves_tipo_malo = []
    for clave, (tipo_esperado, _descripcion) in claves_obligatorias.items():
        valor = metricas.get(clave)
        if valor is None:
            claves_faltantes.append(clave)
            continue
        # Validación de tipo (int también acepta float si es entero, etc.)
        try:
            if tipo_esperado is int:
                int(valor)
            elif tipo_esperado is float:
                float(valor)
            elif tipo_esperado is str:
                str(valor)
        except (TypeError, ValueError):
            claves_tipo_malo.append(clave)

    if claves_faltantes:
        problemas.append({
            "que":     (f"Faltan datos en el fichero de métricas: "
                        f"{', '.join(claves_faltantes)}"),
            "por_que": ("Algunas páginas (Inicio, Visión institucional, "
                        "Equidad, Guía semántica) no podrán mostrar todos "
                        "los indicadores correctamente."),
            "como":    ("1. Abre Jupyter\n"
                        "2. Ejecuta el notebook "
                        "`notebooks/fase6_evaluacion/f6_m00_preparacion.ipynb`\n"
                        "3. Asegúrate de que el notebook se ejecute sin "
                        "errores hasta el final\n"
                        "4. Recarga esta página"),
            "tecnico": (f"Claves faltantes en metricas_modelo.json: "
                        f"{claves_faltantes}"),
        })

    if claves_tipo_malo:
        problemas.append({
            "que":     (f"Algunas métricas tienen un formato inesperado: "
                        f"{', '.join(claves_tipo_malo)}"),
            "por_que": "La app no puede interpretar correctamente esos valores.",
            "como":    ("1. Comprueba que `metricas_modelo.json` no se haya "
                        "editado a mano\n"
                        "2. Re-genera el fichero ejecutando "
                        "`f6_m00_preparacion.ipynb`\n"
                        "3. Recarga esta página"),
            "tecnico": (f"Claves con tipo incorrecto: {claves_tipo_malo}"),
        })

    # 3. Verificar coherencia con el modelo activo
    modelo_pkl = metricas.get("modelo_pkl")
    if modelo_pkl:
        try:
            ruta_modelo = _RUTAS.get("modelo")
            if ruta_modelo and not ruta_modelo.exists():
                problemas.append({
                    "que":     f"No se encuentra el fichero del modelo: {modelo_pkl}",
                    "por_que": ("La app no podrá calcular predicciones para "
                                "los pronósticos individuales (Futuro estudiante "
                                "y Alumno en curso)."),
                    "como":    ("1. Verifica que el fichero existe en "
                                "`data/05_modelado/models/`\n"
                                "2. Si has cambiado de modelo, re-ejecuta "
                                "`f6_m00_preparacion.ipynb` para actualizar "
                                "el JSON\n"
                                "3. Recarga esta página"),
                    "tecnico": f"Ruta esperada: {ruta_modelo}",
                })
        except Exception:
            pass  # Si falla aquí no bloqueamos: el config ya validó modelo

    ok = len(problemas) == 0
    return (ok, problemas)


def mostrar_cartel_problemas(problemas: list[dict]) -> None:
    """
    Renderiza el cartel de degradación elegante cuando hay problemas críticos.

    Usa Streamlit para mostrar una pantalla amigable que explica qué falla
    y cómo arreglarlo, sin tracebacks técnicos.

    Tras renderizar el cartel, llama a st.stop() para que la app no continúe
    cargando con datos rotos.
    """
    import streamlit as _st
    from config_app import COLORES as _COLORES

    # Cabecera amable (no asustadora)
    _st.markdown(f"""
    <div style="
        background: {_COLORES.get('fondo', '#f7fafc')};
        border-left: 5px solid {_COLORES.get('primario', '#3182ce')};
        border-radius: 8px;
        padding: 1.5rem 1.8rem;
        margin: 2rem 0 1.5rem 0;
        font-family: Arial, sans-serif;
    ">
        <div style="font-size:1.4rem; font-weight:700;
                    color:{_COLORES.get('primario', '#3182ce')};
                    margin-bottom:0.5rem;">
            💡 La app necesita un poco de ayuda para arrancar
        </div>
        <div style="font-size:0.95rem; color:{_COLORES.get('texto', '#2d3748')};
                    line-height:1.5;">
            Hemos detectado que faltan algunos datos para que la aplicación
            funcione correctamente. No te preocupes — abajo te explicamos
            qué pasa y cómo solucionarlo en pocos pasos.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cada problema en su tarjeta
    for i, p in enumerate(problemas, 1):
        _st.markdown(f"""
        <div style="
            background: white;
            border: 1px solid {_COLORES.get('borde', '#e2e8f0')};
            border-radius: 8px;
            padding: 1.2rem 1.4rem;
            margin: 0.8rem 0;
            font-family: Arial, sans-serif;
        ">
            <div style="font-size:1.05rem; font-weight:700;
                        color:{_COLORES.get('primario', '#3182ce')};
                        margin-bottom:0.6rem;">
                Problema {i}: {p['que']}
            </div>
            <div style="font-size:0.92rem; color:{_COLORES.get('texto_suave', '#4a5568')};
                        margin:0.4rem 0 0.8rem 0; line-height:1.5;">
                <strong>¿Por qué importa?</strong> {p['por_que']}
            </div>
            <div style="font-size:0.92rem; color:{_COLORES.get('texto', '#2d3748')};
                        background:{_COLORES.get('fondo', '#f7fafc')};
                        border-radius:6px; padding:0.7rem 1rem; line-height:1.6;">
                <strong>Cómo solucionarlo:</strong><br>
                {p['como'].replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detalle técnico oculto en expander
        with _st.expander(f"🔧 Detalle técnico del problema {i} (para developers)",
                          expanded=False):
            _st.code(p.get("tecnico", "(sin detalles)"), language="text")

    # Nota final + botón de reintento
    _st.markdown(f"""
    <div style="
        background:{_COLORES.get('fondo', '#f7fafc')};
        border-radius:8px; padding:1rem 1.4rem; margin:1.2rem 0 0.5rem 0;
        font-family: Arial, sans-serif;
        font-size:0.85rem; color:{_COLORES.get('texto_suave', '#4a5568')};
        line-height:1.5;
    ">
        ℹ️ <strong>Nota técnica:</strong> esta pantalla aplica el patrón de
        <em>degradación elegante</em> (graceful degradation), una buena
        práctica de ingeniería de software por la cual una aplicación que
        detecta un problema informa al usuario de forma comprensible en lugar
        de fallar con errores técnicos crudos.
    </div>
    """, unsafe_allow_html=True)

    if _st.button("🔄 Volver a comprobar", type="primary"):
        _st.rerun()

    _st.stop()



# =============================================================================
# HELPER — Convertir color hex a rgba con transparencia
# =============================================================================
# Centralizado en ui_helpers (Chat p00, 28/04/2026) para que cualquier
# página pueda derivar fondos suaves a partir de COLORES sin hardcodear.
# Antes se repetía en pronostico_shared (línea 1665) y p00 usaba hex de
# 8 caracteres tipo "{COLORES['primario']}15" que no son universales.


def _hex_a_rgba(hex_color: str, alpha: float) -> str:
    """
    Convierte un color hex (#rrggbb) a rgba(r,g,b,alpha).

    Útil para crear fondos suaves derivados de la paleta COLORES sin
    hardcodear hex auxiliares en config_app. Si el color de base cambia,
    el fondo derivado se actualiza automáticamente.

    Parameters
    ----------
    hex_color : str
        Color hex de 7 caracteres (#rrggbb). Si ya viene en rgba u otro
        formato, se devuelve tal cual.
    alpha : float
        Opacidad entre 0 y 1.

    Returns
    -------
    str
        rgba(r,g,b,alpha) si el hex es válido. El input original si no.

    Examples
    --------
    >>> _hex_a_rgba(COLORES['exito'], 0.10)
    'rgba(16,185,129,0.1)'
    >>> _hex_a_rgba(COLORES['primario'], 0.08)
    'rgba(30,77,140,0.08)'
    """
    if isinstance(hex_color, str) and hex_color.startswith("#") and len(hex_color) == 7:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"rgba({r},{g},{b},{alpha})"
        except ValueError:
            pass
    return hex_color


# =============================================================================
# HELPER — Guardia para DataFrame vacío
# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): antes había 2 copias idénticas en
# p01 y p02. Centralizada aquí. Devuelve True si el DataFrame está vacío
# (para que el bloque llamante haga return) y muestra un aviso visual
# coherente con el estilo de la app.


def _guardia_df_vacio(df, titulo_bloque: str) -> bool:
    """
    Comprueba si un DataFrame está vacío y, si lo está, renderiza un aviso
    visual coherente con el estilo de la app.

    Devuelve:
      - True  → df está vacío, el bloque que lo llame debe hacer `return`
      - False → df tiene datos, el bloque puede continuar normalmente

    Parámetros:
      df            → DataFrame a comprobar (típicamente df_filtrado)
      titulo_bloque → Nombre del bloque para el aviso (ej: "Evolución temporal")
    """
    import streamlit as st  # import local: ui_helpers no fuerza streamlit global
    if df is None or len(df) == 0:
        st.markdown(f"""
        <div style="background:{COLORES['fondo']};
            border:1px dashed {COLORES['texto_muy_suave']};
            border-radius:8px;
            padding:1.5rem 1rem;
            text-align:center;
            color:{COLORES['texto_suave']};
            font-size:0.85rem;
            margin:0.5rem 0;">
            <div style="font-weight:600; margin-bottom:0.3rem;
                color:{COLORES['texto']};">
                {titulo_bloque}
            </div>
            📭 No hay datos para mostrar con los filtros actuales.
            <br>
            <span style="font-size:0.78rem;">
                Prueba a relajar los filtros para ver este bloque.
            </span>
        </div>
        """, unsafe_allow_html=True)
        return True
    return False


# =============================================================================
# HELPER — Clasificar nivel de riesgo
# =============================================================================
# REFACTOR p03 (Chat p03, 27/04/2026): antes había 4 implementaciones:
#   - _clasificar_riesgo en pronostico_shared (la base, completa)
#   - _color_tasa en p01 (devolvía solo color+emoji)
#   - lógica inline en p01 L408 (if/elif/else)
#   - lógica inline en p02
# Ahora todas usan ESTA. Si _color_tasa solo necesita color+emoji, hace:
#   _, color, emoji, _ = _clasificar_riesgo(prob)


def _clasificar_riesgo(prob: float) -> tuple[str, str, str, str]:
    """
    Clasifica una probabilidad de abandono en nivel + color + emoji + mensaje.

    Usa UMBRALES y COLORES_RIESGO de config_app para coherencia global con
    los gauges, las tablas y los velocímetros del modelo.

    Parameters
    ----------
    prob : float
        Probabilidad en escala 0-1 (no porcentaje).

    Returns
    -------
    tuple[str, str, str, str]
        (nivel, color_hex, emoji, mensaje_descriptivo).
        nivel ∈ {'Bajo', 'Medio', 'Alto'}.

    Examples
    --------
    >>> nivel, color, emoji, msg = _clasificar_riesgo(0.85)
    >>> nivel
    'Alto'
    """
    if prob < UMBRALES['riesgo_bajo']:
        return (
            'Bajo', COLORES_RIESGO['bajo'], '✅',
            'Tu perfil muestra factores protectores importantes. '
            'El riesgo de abandono es reducido según el modelo.',
        )
    elif prob < UMBRALES['riesgo_medio']:
        return (
            'Medio', COLORES_RIESGO['medio'], '⚠️',
            'Hay algunos factores de riesgo en tu perfil. '
            'Con el apoyo adecuado y buena planificación, es muy manejable.',
        )
    else:
        return (
            'Alto', COLORES_RIESGO['alto'], '🔴',
            'Tu perfil presenta varios factores de riesgo. '
            'Te recomendamos consultar con la Unidad de Soporte Educativo '
            '(USE) de la UJI.',
        )


# =============================================================================
# HELPER — Acortar nombre de titulación
# =============================================================================
# REGLA: "acortar" = quitar el prefijo redundante "Grado en" porque todas
# son grados. NO es resumir ni inventar abreviaturas.
#
# Caso especial Doble Grado: el prefijo "Doble Grado en" se sustituye por
# "Doble: " para mantener la pista de que es un doble grado sin la
# redundancia. Sin esto, "Doble Grado en ADE y Derecho" se confunde con
# "Grado en ADE" si solo se muestra el resto.
#
# REFACTOR p03 (Chat p03, 27/04/2026): antes había 4 implementaciones:
#   - _nombre_titulacion_corto en p02 (la más completa, base de esta)
#   - _nombre_corto_tit en pronostico_shared (no manejaba Doble Grado)
#   - _partir_label en p01 (solo quitaba "Grado en", sin Doble)
#   - regex inline en p01 L2122
# Ahora todas usan ESTA, que es la versión completa.
_PREFIJOS_TITULACION = (
    "Grado en Ingeniería en ",
    "Grado en Ingeniería ",
    "Grado en Maestro en ",
    "Grado en Maestro o Maestra en ",
    "Grado en ",
    "Grado de ",
    "Grado ",
)


def _nombre_titulacion_corto(nombre: str, partir_lineas: bool = False,
                              max_chars: int = 22) -> str:
    """
    Acorta el nombre de una titulación quitando redundancia.

    Caso especial Doble Grado: el prefijo "Doble Grado en" se sustituye por
    "Doble: " para que el lector siga sabiendo que es un doble grado pero
    sin redundancia.

    Parameters
    ----------
    nombre : str
        Nombre completo de la titulación (ej: "Grado en Medicina").
    partir_lineas : bool
        Si True, parte el resultado en 2 líneas con <br> usando el espacio
        más cercano al centro. Default False.
    max_chars : int
        Si partir_lineas=True, solo parte si supera este umbral. Default 22.

    Returns
    -------
    str
        Nombre acortado (y opcionalmente partido en 2 líneas).

    Examples
    --------
    >>> _nombre_titulacion_corto("Grado en Medicina")
    'Medicina'
    >>> _nombre_titulacion_corto("Grado en Ingeniería en Tecnologías Industriales")
    'Tecnologías Industriales'
    >>> _nombre_titulacion_corto("Doble Grado en Administración y Dirección de Empresas y Derecho")
    'Doble: Administración y Dirección de Empresas y Derecho'
    """
    if not nombre:
        return ""

    # Caso especial: Doble Grado — sustituir "Doble Grado en" por "Doble: "
    nombre_limpio = nombre.strip().rstrip(",").strip()
    if nombre_limpio.startswith("Doble Grado en "):
        nombre = "Doble: " + nombre_limpio[len("Doble Grado en "):]
    elif nombre_limpio.startswith("Doble Grado de "):
        nombre = "Doble: " + nombre_limpio[len("Doble Grado de "):]
    else:
        # Caso general: quitar prefijo (el primero que coincida gana)
        for prefijo in _PREFIJOS_TITULACION:
            if nombre.startswith(prefijo):
                nombre = nombre[len(prefijo):]
                break

    # Paso 2: opcional, partir en 2 líneas
    if not partir_lineas or len(nombre) <= max_chars:
        return nombre

    mid = len(nombre) // 2
    izq = nombre.rfind(" ", 0, mid)
    der = nombre.find(" ", mid)
    if izq == -1 and der == -1:
        return nombre
    if izq == -1:
        corte = der
    elif der == -1:
        corte = izq
    else:
        corte = izq if (mid - izq) <= (der - mid) else der
    return nombre[:corte] + "<br>" + nombre[corte+1:]


# =============================================================================
# HELPER — Tarjeta KPI compacta (border-left 4px)
# =============================================================================
# Réplica del patrón de _tarjeta_kpi_html de p01, en versión compacta sin
# sparkline. Para vista operativa (p02 modo detalle/comparativa, p03 KPIs).
#
# REGLAS DE COLORES SEMÁNTICOS (alineadas con p01):
#   👥 alumnos          → COLORES["primario"]    azul
#   📉 abandono real    → COLORES["abandono"]    rojo
#   🔮 predicción       → COLORES["primario"]    azul
#   🚨 riesgo alto      → COLORES["advertencia"] ámbar  (NO rojo)
#   🎯 calidad modelo   → COLORES["exito"]       verde


def _tarjeta_kpi(icono: str, etiqueta: str, valor: str,
                 delta: str = "", delta_color: str = "",
                 tooltip: str = "", color_barra: str = None,
                 sparkline: tuple = None,
                 sparkline_labels: tuple = None) -> str:
    """
    Genera el HTML de una tarjeta KPI compacta con barra lateral de color.

    Función UNIFICADA (Chat p00, 28/04/2026): única card de KPI usada en
    p00, p02, p03, p04, p05. Sustituye a _kpi_card local de p00 y al
    _tarjeta_kpi_html de p01 (excepto cuando p01 necesita evolución
    temporal — para eso se usa _tarjeta_kpi_evolucion).

    Argumentos:
        icono: emoji del KPI (👥, 📉, 🔮, 🚨, 🎯…)
        etiqueta: nombre del indicador (en MAYÚSCULAS, va arriba)
        valor: valor principal del KPI (cifra grande)
        delta: texto secundario en cajita (vs cohorte anterior, vs media…).
               Si delta_color es 'red'/'green', se renderiza en cajita
               coloreada (estilo unificado p00). Si '' o 'gray', va en
               texto suelto sin cajita.
        delta_color: '' (gris), 'red' (peor), 'green' (mejor), 'gray' (info)
        tooltip: texto de tooltip nativo HTML
        color_barra: hex o COLORES[clave]. Si None, usa COLORES["primario"].
        sparkline: tupla (val_base, val_modelo) en escala 0-1 para mostrar
                   mini-barra comparativa. Si None, no se muestra.
                   Ejemplo: (0.927, 0.954) para AUC baseline→modelo final.
        sparkline_labels: tupla (label_base, label_modelo) — leyenda bajo
                   la barra. Ejemplo: ("CatBoost", "LightGBM").
                   Si None, no se muestra leyenda.

    Devuelve:
        str con el HTML de la tarjeta. Para renderizar:
            st.markdown(_tarjeta_kpi(...), unsafe_allow_html=True)
    """
    # Mapeo semántico de colores del delta
    _color_delta = {
        "red":   COLORES["abandono"],
        "green": COLORES["exito"],
        "gray":  COLORES["texto_muy_suave"],
        "":      COLORES["texto_muy_suave"],
    }.get(delta_color, COLORES["texto_muy_suave"])

    # Color de la barra lateral (default = primario azul, igual que p01)
    _color_barra = color_barra if color_barra else COLORES["primario"]

    # BUG FIX (Chat p03, 27/04/2026): antes generábamos DOS atributos style=
    # en el mismo div cuando había tooltip:
    #     <div title="..." style="cursor:help;" style="background:..."> ❌
    # El navegador solo respeta el PRIMER style= e ignora el segundo, así
    # que la barra lateral, fondo, padding y bordes desaparecían cuando
    # se pasaba un tooltip. Solución: tooltip y cursor van como atributos
    # separados (title="..." + cursor en el style único de la tarjeta).
    title_attr  = f' title="{tooltip}"' if tooltip else ""
    cursor_css  = "cursor:help;" if tooltip else ""

    # --- DELTA: cajita coloreada (estilo p00 unificado, 28/04/2026) ---
    # Si delta_color es 'red' o 'green', se renderiza en cajita coloreada
    # con fondo suave + flecha. Si '' o 'gray', texto suelto sin cajita.
    if delta:
        if delta_color in ("red", "green"):
            _bg_delta = ("rgba(16,185,129,0.10)" if delta_color == "green"
                         else "rgba(220,38,38,0.10)")
            _arrow = "▲ " if delta.lstrip().startswith("+") else (
                     "▼ " if delta.lstrip().startswith("-") else "")
            delta_html = (
                f'<div style="display:inline-block; font-size:0.78rem; '
                f'color:{_color_delta}; background:{_bg_delta}; '
                f'padding:0.15rem 0.5rem; border-radius:4px; '
                f'margin-top:0.35rem; font-weight:500; white-space:nowrap;">'
                f'{_arrow}{delta}</div>'
            )
        else:
            delta_html = (
                f'<div style="font-size:0.78rem; color:{_color_delta}; '
                f'margin-top:0.15rem; font-weight:500;">{delta}</div>'
            )
    else:
        delta_html = '<div style="font-size:0.78rem; margin-top:0.15rem;">&nbsp;</div>'

    # --- SPARKLINE OPCIONAL (Chat p00, 28/04/2026) ---
    # Mini-barra comparativa "antes → después". Solo aparece si se pasa
    # el parámetro sparkline=(val_base, val_modelo) en escala 0-1.
    sparkline_html = ""
    if sparkline is not None and len(sparkline) == 2:
        _vb, _vm = float(sparkline[0]), float(sparkline[1])
        _pct_b = round(_vb * 100, 1)
        _pct_m = round(_vm * 100, 1)
        _diff  = round((_vm - _vb) * 100, 1)
        _color_mejora = (COLORES["exito"] if _vm >= _vb
                         else COLORES["abandono"])
        sparkline_html = (
            f'<div style="margin-top:0.5rem; display:flex; align-items:center; gap:3px;">'
            f'<div style="width:{_pct_b}%; height:5px; '
            f'background:{COLORES["borde"]}; border-radius:3px 0 0 3px;"></div>'
            f'<div style="width:{abs(_diff)}%; height:5px; '
            f'background:{_color_mejora}; border-radius:0 3px 3px 0;"></div>'
            f'</div>'
        )
        if sparkline_labels and len(sparkline_labels) == 2:
            _lb, _lm = sparkline_labels
            sparkline_html += (
                f'<div style="font-size:0.68rem; color:{COLORES["texto_muy_suave"]}; '
                f'margin-top:0.2rem;">'
                f'{_lb}: {str(_pct_b).replace(".", ",")}% → '
                f'<span style="color:{_color_mejora}; font-weight:600;">'
                f'{_lm}: {str(_pct_m).replace(".", ",")}%</span>'
                f'</div>'
            )

    return (
        f'<div{title_attr} style="{cursor_css}'
        f'background:{COLORES["blanco"]};'
        f'border:1px solid {COLORES["borde"]};'
        f'border-left:4px solid {_color_barra};'
        f'border-radius:10px;'
        f'padding:0.85rem 1rem;box-shadow:0 1px 2px rgba(0,0,0,0.04);'
        f'height:100%;min-height:6.2rem;display:flex;'
        f'flex-direction:column;justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;">'
        f'<div style="font-size:1.4rem;line-height:1;flex-shrink:0;">{icono}</div>'
        f'<div style="font-size:0.72rem;color:{COLORES["texto_suave"]};font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.03em;line-height:1.2;">'
        f'{etiqueta}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:1.7rem;font-weight:700;color:{COLORES["texto"]};'
        f'line-height:1.1;margin-top:0.3rem;">{valor}</div>'
        f'{delta_html}'
        f'{sparkline_html}'
        f'</div>'
        f'</div>'
    )
