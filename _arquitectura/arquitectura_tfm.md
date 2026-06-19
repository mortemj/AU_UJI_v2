# Arquitectura del sistema — TFM Predicción de Abandono Universitario (UJI)

Documento de apoyo para la defensa. Describe, capa por capa, cómo encajan las
piezas reales del proyecto. El diagrama acompañante está en
[`arquitectura_tfm.mmd`](arquitectura_tfm.mmd) (formato Mermaid).

> **Exportar a imagen:** en este entorno no había herramienta de renderizado
> (`mmdc`/`npx` no disponibles), por lo que solo se entrega el `.mmd`. Para
> obtener el `.png`/`.svg`: pegar el contenido en <https://mermaid.live> y
> exportar, o ejecutar `mmdc -i arquitectura_tfm.mmd -o arquitectura_tfm.png`
> si se instala `@mermaid-js/mermaid-cli`.

---

## Capa 1 · Datos (`data/`)

El dato fluye de los **Excel originales** del Servicio de Planificación de la
Universitat Jaume I (en `00_raw/`) hacia parquets cada vez más procesados,
organizados por fase: `01_interim` → `02_processed` (`df_alumno.parquet`) →
`03_features` → `04_eda` → `05_modelado` → `06_evaluacion`. La carpeta `automl/`
guarda los modelos de los frameworks AutoML (AutoGluon, H2O…), y
`06_interpretacion` y `07_aplicacion` recogen salidas posteriores. Cada fase de
notebooks lee el parquet de la anterior y escribe el suyo, manteniendo la
trazabilidad del dato.

## Capa 2 · Núcleo reutilizable (`src/`)

Es la biblioteca compartida que importan tanto los notebooks como la app, para
no duplicar lógica. Incluye **config** (`config.py` reexporta rutas, mapas de
codificación y constantes desde `config_entorno`, `config_datos`,
`config_proyecto` y `config_modelado`), **validacion** (contrato y validador de
los Excel de entrada), **linaje** (trazabilidad del dato: `core`, `exporters`,
`inventario`), **html** (renderizado de páginas con Jinja2 vía `render_pagina`,
navegación y componentes) y **utils** (gráficos, formateadores, logging,
orquestador). Es la "fuente única de verdad" del proyecto.

## Capa 3 · Notebooks de procesamiento (`notebooks/`)

El pipeline analítico está organizado en fases secuenciales: **fase0**
(configuración y validación de Excel), **fase1** (transformación: limpieza,
unión de tablas, dataset final), **fase2** (EDA inicial), **fase3** (features y
target, alerta temprana), **fase4** (EDA de features, selección),
**fase_automl** (baselines y frameworks AutoML, incl. TabPFN), **fase5**
(modelado: lineales, árboles, boosting y notebook maestro) y **fase6**
(evaluación: SHAP, LIME/DiCE, robustez, calibración, sostenibilidad y fairness).
Todos importan del núcleo `src/` y generan páginas HTML con `render_pagina(...)`.

## Capa 4 · Modelo ganador

La selección del ganador es **dinámica**: la Fase 6 (`f6_m00_preparacion`)
escribe `data/06_evaluacion/metricas_modelo.json`, que fija el modelo ganador
por criterio **F1 > Recall > AUC > Tiempo**. En el estado actual del fichero el
ganador es **LightGBM** (`LightGBM__none.pkl`, familia Gradient Boosting) con
F1 = 0,8334 y AUC = 0,9564. El `.pkl` vive en `data/05_modelado/models/` y se
acompaña del `pipeline_preprocesamiento.pkl` (imputación + codificación +
escalado) que debe aplicarse antes de predecir.

## Capa 5 · Aplicación Streamlit (`app/`)

`main.py` arranca la app (navegación por pestañas, sin sidebar) y verifica los
ficheros críticos. `config_app.py` centraliza rutas, colores y la definición de
las pestañas, e **importa de `src.config`** para no duplicar mapas. La lógica de
carga está en `utils/loaders.py`, que con caché de Streamlit lee el modelo
(resolviendo su ruta **dinámicamente desde `metricas_modelo.json`**), el
pipeline, `meta_test_app.parquet`, los valores SHAP y las métricas de fairness.
Las páginas `p00`–`p06` (inicio, institucional, titulación, prospecto, alumno en
curso, equidad, leyenda) consumen esos loaders para mostrar predicciones y
análisis a cada perfil de usuario.

> **Nota (verificar):** los comentarios de `loaders.py` mencionan "CatBoost"
> como ejemplo histórico, pero la carga es agnóstica al algoritmo: el modelo
> efectivo es siempre el que indique `metricas_modelo.json` (hoy LightGBM).

## Capa 6 · Resultados (`results/`, `docs/html/`)

Las salidas finales: páginas HTML por fase en `docs/html/` (generadas desde los
notebooks con `render_pagina`, nunca a mano), y artefactos de análisis en
`results/` — `fase5`, `fase6` (SHAP beeswarm, sostenibilidad, sankey, dashboard
shapash), además de `metricas`, `tablas` y `exports`. Son los materiales que
sustentan la memoria y la defensa.

## Componente transversal · `scripts/`

Utilidades de mantenimiento fuera del pipeline principal: compresión del modelo
para la app (`comprimir_modelo_app.py`), diagnóstico (`diagnostico_modelo.py`),
verificación de coherencia (`verificar_coherencia.py`) y trazabilidad
(`trazabilidad.py`).

---

### Flujo global en una frase

**Excel originales → parquets por fase (notebooks apoyados en `src/`) →
selección dinámica del modelo ganador (LightGBM, vía `metricas_modelo.json`) →
la app Streamlit carga modelo + pipeline + datos de test → predicciones y
resultados (HTML, SHAP, fairness) para la defensa.**
