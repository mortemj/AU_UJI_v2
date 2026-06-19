# Detalle de arquitectura — Flujo de predicción de la app (p03 / p04)

Documento de apoyo para la defensa. Complementa la vista global
([`arquitectura_tfm.md`](arquitectura_tfm.md)) haciendo *zoom* en cómo la
aplicación produce, en tiempo real, la probabilidad de abandono de un perfil
concreto. El diagrama acompañante está en
[`arquitectura_detalle.mmd`](arquitectura_detalle.mmd).

> **Exportar a imagen:** en este entorno no había herramienta de renderizado
> (`mmdc`/`npx` no disponibles). Para obtener el `.png`/`.svg`: pegar el `.mmd`
> en <https://mermaid.live> o usar `mmdc -i arquitectura_detalle.mmd -o
> arquitectura_detalle.png`.

> **Fuentes leídas (solo lectura):** `app/pages/p03_prospecto.py`,
> `app/pages/p04_en_curso.py`, `app/utils/pronostico_shared.py`
> (`show_pronostico`, `_calcular_probabilidad`, `_ajustar_prob_por_titulacion`)
> y `app/utils/loaders.py`.

---

## Entrada · páginas wrapper

`p03_prospecto.py` y `p04_en_curso.py` son *wrappers* finos: toda la lógica vive
en `pronostico_shared.show_pronostico(modo)`. La única diferencia es el `modo`:
`"prospecto"` (alumnado antes de matricularse, sin nota de 1.º ni créditos) y
`"en_curso"` (ya matriculado, con rendimiento académico). Así no se duplica
código entre ambas páginas.

## Paso 0 · Carga de recursos (cacheada)

`show_pronostico` pide a `utils/loaders.py` cuatro recursos, todos con caché de
Streamlit (se cargan una sola vez): el **modelo** (cuya ruta se resuelve
dinámicamente leyendo `modelo_pkl` de `metricas_modelo.json` → hoy
`LightGBM__none.pkl`), el **pipeline** de preprocesamiento
(`pipeline_preprocesamiento.pkl`: imputación + codificación + escalado), el
DataFrame de referencia `df_ref` (`meta_test_app.parquet`, con titulaciones
fusionadas) y `X_test_prep.parquet` (`df_features`, para imputar con medias
reales).

## Paso 1 · Selector de contexto

`_selector_contexto()` deja elegir contra qué comparar: todas las titulaciones,
una rama, una titulación concreta o varias (comparativa). Devuelve `df_ctx`, el
subconjunto histórico que se usará como referencia para imputar valores y para
los gráficos.

## Paso 2 · Formulario de perfil

`_formulario_perfil()` recoge los datos del alumno en un `dict` (`perfil`): unas
**features básicas** siempre visibles (nota de acceso, situación laboral, años
de beca, edad, vía de acceso) y unas **avanzadas** opcionales que cambian según
el modo. Los campos vacíos se imputarán después.

## Paso 3 · Cálculo de la probabilidad (núcleo)

`_calcular_probabilidad(perfil, modelo, pipeline, df_ctx)` es el corazón del
flujo. En orden:

1. **Traduce** los textos del formulario a los códigos numéricos que espera el
   modelo (`_traducir_perfil_a_codigos`, usando `SEXO_MAP`, `VIA_ACCESO_MAP`,
   `RAMA_MAP`, etc.).
2. Toma como **fuente de verdad de las columnas** `pipeline.feature_names_in_`.
3. **Imputa por prioridad** cada columna que falte: (1) lo que rellenó el
   usuario → (2) media/moda del contexto `df_ctx` → (3) media del *training set*
   guardada en el `scaler` → (4) `0` como último recurso.
4. Construye `X_usuario` (una fila), aplica `fillna(0)` defensivo y lo pasa por
   `pipeline.transform()`, obteniendo `X_prep` como array de NumPy (se entrega
   como array para evitar el aviso de *feature names mismatch* de sklearn).
5. Llama a `modelo.predict_proba(X_prep)[0, 1]` → **probabilidad de abandono**
   entre 0 y 1.

## Paso 3.bis · Ajuste heurístico por titulación

Si el contexto es una titulación concreta, `_ajustar_prob_por_titulacion()`
aplica una corrección **post-hoc en espacio logit**:
`logit(p) + log(tasa_tit / tasa_rama)`. Sirve para diferenciar titulaciones de
la misma rama según su abandono histórico. **No forma parte del modelo
entrenado** y la app lo avisa explícitamente al usuario.

## Paso 4 · Visualización del resultado

Con la probabilidad final, la página pinta: velocímetro de riesgo, radar del
perfil frente a los patrones de éxito/abandono, cascada de contribuciones
(SHAP `TreeExplainer` calculado en vivo, o un proxy por diferencia de medias),
posición en percentil histórico y recomendaciones personalizadas.

---

### Flujo en una frase

**perfil del formulario → traducción a códigos → imputación por prioridad →
`pipeline.transform` → `modelo.predict_proba` (LightGBM) → ajuste logit opcional
por titulación → velocímetro / radar / cascada SHAP / percentil.**
