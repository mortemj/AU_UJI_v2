# Guía de reproducción desde cero — AU_UJI_v2

> **Proyecto:** Predicción del abandono universitario · Universitat Jaume I (UJI)
> **TFM** · Máster Universitario en Ciencia de Datos · Universitat Oberta de Catalunya (UOC)
> **Modelo ganador:** LightGBM (`LightGBM__none.pkl`)
> **Documento generado en modo SOLO LECTURA** — no se ha modificado ningún fichero del proyecto.

Esta guía explica, paso a paso, cómo regenerar **todo el proyecto desde cero**, respetando
el orden real de dependencias entre notebooks y datos. Allí donde el orden exacto no es
verificable solo con la inspección estática se indica con **(verificar)**.

---

## 0. Resumen de la cadena de dependencias

El proyecto se organiza en fases. Cada fase tiene un **orquestador** (`fX_m00_ejecucion.ipynb`)
que lanza sus submódulos en secuencia con `nbconvert --execute`. La cadena de datos es:

```
Datos originales UJI (Excel, data/00_raw/)
   │
   ▼  Fase 1 — Transformación       → data/01_interim/  + data/02_processed/df_alumno.parquet
   ▼  Fase 2 — EDA inicial          → informes HTML (no genera datos nuevos)
   ▼  Fase 3 — Feature engineering  → data/03_features/  + data/automl/dataset_final_tfm.parquet (target)
   ▼  AutoML  — Baseline            → data/automl/automl_comparativa_final.json (baseline a superar)
   ▼  Fase 4 — EDA final            → data/04_eda/df_eda_final.parquet
   ▼  Fase 5 — Modelado (69 modelos)→ data/05_modelado/models/*.pkl + results/fase5/resultados_maestro.parquet
   ▼  Fase 6 — Interpretabilidad    → data/06_evaluacion/metricas_modelo.json (fuente única) + results/fase6/
   ▼  Fase 7 — App Streamlit        → no se ejecuta como notebook; se lanza con streamlit run app/main.py
```

> **Importante:** las Fases 1–3 (y AutoML) requieren los **datos originales de la UJI**, que
> **no se incluyen en el repositorio** por confidencialidad. Las Fases 4–6 pueden ejecutarse
> con los datos derivados (`.parquet`) que sí están versionados.

---

## 1. Requisitos previos

### 1.1 Software base
- **Git** — para clonar el repositorio.
- **Anaconda** o **Miniconda** — para gestionar el entorno Python.
- **Python 3.11** (lo instala el entorno conda).

### 1.2 Crear y activar el entorno conda `tfm_abandono`

```bash
# 1. Clonar el proyecto
git clone https://github.com/mortemj/AU_UJI_v2.git
cd AU_UJI_v2

# 2. Crear el entorno (solo la primera vez)
conda create -n tfm_abandono python=3.11 -y

# 3. Activar el entorno
conda activate tfm_abandono

# 4. Instalar dependencias (entorno completo, recomendado para reproducir todo)
pip install -r requirements_proyecto.txt
```

### 1.3 Archivos de dependencias disponibles

| Archivo | Uso |
|---|---|
| [requirements_proyecto.txt](requirements_proyecto.txt) | **Todo el TFM** (todas las fases + app). Recomendado. |
| [requirements.txt](requirements.txt) | Despliegue de la app en Streamlit Cloud (mínimo). |
| [requirements_fase1.txt](requirements_fase1.txt) … [requirements_fase6.txt](requirements_fase6.txt) | Reproducir una fase concreta de forma aislada. |

> Las fases AutoML (H2O, AutoGluon) requieren **Java**; en la carpeta de Fase 3 existe
> [notebooks/fase3_features/install_java.bat](notebooks/fase3_features/install_java.bat) y
> [notebooks/fase3_features/verificar_librerias.py](notebooks/fase3_features/verificar_librerias.py) como apoyo.

### 1.4 Verificación opcional del entorno

```bash
pytest tests/ -v          # resultado esperado: 42 passed
```

### 1.5 Datos originales

Colocar los Excel originales de la UJI en [data/00_raw/](data/00_raw/) (p. ej.
`datos_proyecto_sin_preinscrip.xlsx` y `preinscripcion_si.xlsx`). Sin ellos solo se pueden
reproducir las Fases 4–6 a partir de los `.parquet` derivados ya versionados.

---

## 2. Orden EXACTO de ejecución

Hay dos formas de regenerar el proyecto:

- **A) Orquestador maestro** — [notebooks/fase0_configuracion/orquestador_maestro.ipynb](notebooks/fase0_configuracion/orquestador_maestro.ipynb)
  ejecuta todas las fases encadenadas con botones de pausa. La ejecución completa puede tardar
  **varias horas** (Fase 5 y SHAP de Fase 6 son las más lentas).
- **B) Fase a fase** — ejecutar el orquestador de cada fase (`fX_m00_ejecucion.ipynb`) en orden.
  Es lo recomendado para controlar el proceso. La descripción siguiente sigue este modo.

> En todos los notebooks la raíz del proyecto (`ROOT`) se detecta subiendo niveles hasta
> encontrar la carpeta `src/`. No es necesario configurar rutas a mano.

---

### Fase 0 — Configuración

**Orquestador / entrada:** [notebooks/fase0_configuracion/orquestador_maestro.ipynb](notebooks/fase0_configuracion/orquestador_maestro.ipynb)

| Orden | Notebook | Qué hace / genera |
|---|---|---|
| 1 | [00_configuracion_proyecto.ipynb](notebooks/fase0_configuracion/00_configuracion_proyecto.ipynb) | Crea la estructura de carpetas `data/01_interim … 06_evaluacion` y genera el `index.html` principal. |
| 2 | [f0_validar_excel.ipynb](notebooks/fase0_configuracion/f0_validar_excel.ipynb) | Validador de calidad del Excel original (5 niveles N1–N5). |
| — | [f0_setup_demo.ipynb](notebooks/fase0_configuracion/f0_setup_demo.ipynb), [f0_generar_excel_prueba.ipynb](notebooks/fase0_configuracion/f0_generar_excel_prueba.ipynb), [f0_actualizar_resumen.ipynb](notebooks/fase0_configuracion/f0_actualizar_resumen.ipynb) | Utilidades de apoyo (demo, Excel de prueba, refresco de HTML). No imprescindibles para la cadena de datos. **(verificar)** orden interno exacto. |

---

### Fase 1 — Transformación (ingesta y limpieza)

**Orquestador:** [notebooks/fase1_transformacion/f1_m00_ejecucion.ipynb](notebooks/fase1_transformacion/f1_m00_ejecucion.ipynb)
**Requiere:** datos originales en `data/00_raw/`.

Orden de la lista `NOTEBOOKS` del orquestador (literal):

| Orden | Notebook | Qué genera |
|---|---|---|
| 1 | [f1_m01_reportes_raw.ipynb](notebooks/fase1_transformacion/f1_m01_reportes_raw.ipynb) | Reportes Sweetviz de los datos **originales** (antes de limpiar). |
| 2 | [f1_m02_limpieza.ipynb](notebooks/fase1_transformacion/f1_m02_limpieza.ipynb) | Limpieza de las 9 tablas → parquets en `data/01_interim/`. |
| 3 | [f1_m03_reportes_clean.ipynb](notebooks/fase1_transformacion/f1_m03_reportes_clean.ipynb) | Reportes Sweetviz tras la limpieza. |
| 4 | [f1_m04_dataset_final.ipynb](notebooks/fase1_transformacion/f1_m04_dataset_final.ipynb) | Orquesta el dataset unido a nivel alumno. |
| 5 | [f1_m04a_union_tablas.ipynb](notebooks/fase1_transformacion/f1_m04a_union_tablas.ipynb) | Unión de tablas. |
| 6 | [f1_m04b_union_preinscripcion.ipynb](notebooks/fase1_transformacion/f1_m04b_union_preinscripcion.ipynb) | Unión con preinscripción. |
| 7 | [f1_m04c_correccion_notas.ipynb](notebooks/fase1_transformacion/f1_m04c_correccion_notas.ipynb) | Corrección de notas. |
| 8 | [f1_m04d_correccion_via_acceso.ipynb](notebooks/fase1_transformacion/f1_m04d_correccion_via_acceso.ipynb) | Corrección de vía de acceso. |
| 9 | [f1_m05_dashboard.ipynb](notebooks/fase1_transformacion/f1_m05_dashboard.ipynb) | Dashboard de la fase. |
| 10 | [f1_m06_grafo.ipynb](notebooks/fase1_transformacion/f1_m06_grafo.ipynb) | Grafo de trazabilidad. |
| 11 | [f1_m06_grafo_pyvis.ipynb](notebooks/fase1_transformacion/f1_m06_grafo_pyvis.ipynb) | Grafo interactivo (pyvis). |
| 12 | [f1_m00_indice.ipynb](notebooks/fase1_transformacion/f1_m00_indice.ipynb) | Índice HTML de la fase (al final). |

**Salida principal de la fase:** `data/01_interim/*.parquet` y `data/02_processed/df_alumno.parquet` (≈ 109.568 × 37).

> **Nota (verificar):** en la lista del orquestador `f1_m04_dataset_final` aparece **antes** que
> sus submódulos `m04a–m04d`. Funcionalmente `m04` actúa como coordinador; respetar el orden
> literal del orquestador.

---

### Fase 2 — EDA inicial

**Orquestador:** [notebooks/fase2_eda/f2_m00_ejecucion.ipynb](notebooks/fase2_eda/f2_m00_ejecucion.ipynb)
**Requiere:** `data/02_processed/df_alumno.parquet`.

| Orden | Notebook | Contenido |
|---|---|---|
| 1 | [f2_m00_indice.ipynb](notebooks/fase2_eda/f2_m00_indice.ipynb) | Índice de la fase. |
| 2 | [f2_m01_inspeccion.ipynb](notebooks/fase2_eda/f2_m01_inspeccion.ipynb) | Inspección general. |
| 3 | [f2_m02_calidad.ipynb](notebooks/fase2_eda/f2_m02_calidad.ipynb) | Calidad de datos. |
| 4 | [f2_m03_nulos.ipynb](notebooks/fase2_eda/f2_m03_nulos.ipynb) | Análisis de nulos. |
| 5 | [f2_m04_univariante_num.ipynb](notebooks/fase2_eda/f2_m04_univariante_num.ipynb) | Univariante numérico. |
| 6 | [f2_m05_univariante_cat.ipynb](notebooks/fase2_eda/f2_m05_univariante_cat.ipynb) | Univariante categórico. |
| 7 | [f2_m06_evolucion.ipynb](notebooks/fase2_eda/f2_m06_evolucion.ipynb) | Evolución. |
| 8 | [f2_m06b_temporal.ipynb](notebooks/fase2_eda/f2_m06b_temporal.ipynb) | Análisis temporal. |
| 9 | [f2_m07_conclusiones.ipynb](notebooks/fase2_eda/f2_m07_conclusiones.ipynb) | Conclusiones. |

**Salida:** informes HTML en `docs/html/fase2/`. Esta fase es **exploratoria**: no genera datos
que consuman fases posteriores.

---

### Fase 3 — Feature engineering (define el target `abandono`)

**Orquestador:** [notebooks/fase3_features/f3_m00_ejecucion.ipynb](notebooks/fase3_features/f3_m00_ejecucion.ipynb)
**Requiere:** salidas de Fase 1.

| Orden | Notebook | Qué genera |
|---|---|---|
| 1 | [f3_m01_validacion.ipynb](notebooks/fase3_features/f3_m01_validacion.ipynb) | Validación de entrada. |
| 2 | [f3_m02_agregacion.ipynb](notebooks/fase3_features/f3_m02_agregacion.ipynb) | Agregación por expediente → `df_expediente_base.parquet`. |
| 3 | [f3_m03_features.ipynb](notebooks/fase3_features/f3_m03_features.ipynb) | Features temporales/derivadas → `df_expediente_features.parquet`. |
| 4 | [f3_m04_index.ipynb](notebooks/fase3_features/f3_m04_index.ipynb) | Índice intermedio. |
| 5 | [f3_m04a_automl_target.ipynb](notebooks/fase3_features/f3_m04a_automl_target.ipynb) | `df_exp_automl_target.parquet` (con `per_id_ficticio`). |
| 6 | [f3_m04b_eda_target.ipynb](notebooks/fase3_features/f3_m04b_eda_target.ipynb) | `df_exp_target_eda.parquet`. |
| 7 | [f3_m05_target_export.ipynb](notebooks/fase3_features/f3_m05_target_export.ipynb) | **Define el target `abandono`**, target encoding de `titulacion`, elimina leakage → **`data/automl/dataset_final_tfm.parquet`** (D_strict, dataset de modelado) + `df_eda_con_target.parquet`. |
| 8 | [f3_m06_alerta_temprana.ipynb](notebooks/fase3_features/f3_m06_alerta_temprana.ipynb) | Análisis de alerta temprana. |
| 9 | [f3_m07_validacion.ipynb](notebooks/fase3_features/f3_m07_validacion.ipynb) | Validación del dataset analítico. |
| 10 | [f3_m08_auditoria.ipynb](notebooks/fase3_features/f3_m08_auditoria.ipynb) | Auditoría. |
| 11 | [f3_m09_perfiles_riesgo.ipynb](notebooks/fase3_features/f3_m09_perfiles_riesgo.ipynb) | Perfiles de riesgo. |
| 12 | [f3_m00_indice.ipynb](notebooks/fase3_features/f3_m00_indice.ipynb) | Índice (al final — necesita los parquets de m01–m09). |

**Salida clave:** `data/automl/dataset_final_tfm.parquet` (≈ 33.621 × 25), el dataset analítico
por estudiante con el target `abandono`. Es la entrada del modelado (Fase 5) y de AutoML.

---

### AutoML — Baseline a superar

**Orquestador:** [notebooks/fase_automl/fautoml_m00_ejecucion.ipynb](notebooks/fase_automl/fautoml_m00_ejecucion.ipynb)
**Requiere:** `dataset_final_tfm.parquet` y `df_exp_automl_target.parquet` (Fase 3).
**Posición:** después de Fase 3 y **antes de Fase 5** (su baseline lo leen `f5_m07` y `f6_m00_preparacion`). Es independiente de Fase 4 **(verificar)** la posición relativa exacta respecto a Fase 4.

| Orden | Notebook | Contenido |
|---|---|---|
| 1 | [fautoml_m01_baselines.ipynb](notebooks/fase_automl/fautoml_m01_baselines.ipynb) | Baselines rápidos. |
| 2 | [fautoml_m02_lazypredict.ipynb](notebooks/fase_automl/fautoml_m02_lazypredict.ipynb) | LazyPredict. |
| 3 | [fautoml_m03_pycaret.ipynb](notebooks/fase_automl/fautoml_m03_pycaret.ipynb) | PyCaret. |
| 4 | [fautoml_m04_h2o.ipynb](notebooks/fase_automl/fautoml_m04_h2o.ipynb) | H2O (requiere Java). |
| 5 | [fautoml_m05_autogluon.ipynb](notebooks/fase_automl/fautoml_m05_autogluon.ipynb) | AutoGluon. |
| — | [fautoml_m06_tabpfn.ipynb](notebooks/fase_automl/fautoml_m06_tabpfn.ipynb) | TabPFN — **desactivado en el orquestador** (≈ 7,3 h en CPU). Sus resultados ya están en `results_tabpfn.parquet`. |
| 6 | [fautoml_m07_comparativa.ipynb](notebooks/fase_automl/fautoml_m07_comparativa.ipynb) | **Comparativa final → `data/automl/automl_comparativa_final.json`** (baseline definitivo). |
| 7 | [fautoml_m00_indice.ipynb](notebooks/fase_automl/fautoml_m00_indice.ipynb) | Índice (al final). |

**Salida clave:** `data/automl/automl_comparativa_final.json`, leído dinámicamente como baseline.

---

### Fase 4 — EDA final

**Orquestador:** [notebooks/fase4_eda/f4_m00_ejecucion.ipynb](notebooks/fase4_eda/f4_m00_ejecucion.ipynb)
**Requiere:** dataset con target de Fase 3.

| Orden | Notebook | Qué genera |
|---|---|---|
| 1 | [f4_m00_indice.ipynb](notebooks/fase4_eda/f4_m00_indice.ipynb) | Índice. |
| 2 | [f4_m01_inspeccion.ipynb](notebooks/fase4_eda/f4_m01_inspeccion.ipynb) | Inspección del dataset procesado. |
| 3 | [f4_m02_target.ipynb](notebooks/fase4_eda/f4_m02_target.ipynb) | Análisis del target. |
| 4 | [f4_m03_distribuciones_num.ipynb](notebooks/fase4_eda/f4_m03_distribuciones_num.ipynb) | Distribuciones numéricas. |
| 5 | [f4_m04_distribuciones_cat.ipynb](notebooks/fase4_eda/f4_m04_distribuciones_cat.ipynb) | Distribuciones categóricas. |
| 6 | [f4_m05_bivariante.ipynb](notebooks/fase4_eda/f4_m05_bivariante.ipynb) | Bivariante. |
| 7 | [f4_m06_correlaciones.ipynb](notebooks/fase4_eda/f4_m06_correlaciones.ipynb) | Correlaciones. |
| 8 | [f4_m07_seleccion_features.ipynb](notebooks/fase4_eda/f4_m07_seleccion_features.ipynb) | Selección de features. |
| 9 | [f4_m08_perfiles_riesgo.ipynb](notebooks/fase4_eda/f4_m08_perfiles_riesgo.ipynb) | Perfiles de riesgo. |
| 10 | [f4_m09_conclusiones_eda.ipynb](notebooks/fase4_eda/f4_m09_conclusiones_eda.ipynb) | Conclusiones. |

**Salida clave:** `data/04_eda/df_eda_final.parquet` (≈ 33.621 × 26), con `titulacion`, `rama` y
contexto. Lo consume `f6_m00_preparacion` para construir `meta_test`.

---

### Fase 5 — Modelado (69 modelos)

**Orquestador:** [notebooks/fase5_modelado/f5_m00_ejecucion.ipynb](notebooks/fase5_modelado/f5_m00_ejecucion.ipynb)
**Requiere:** `data/automl/dataset_final_tfm.parquet` (Fase 3) y el baseline AutoML.

| Orden | Notebook | Qué genera |
|---|---|---|
| 1 | [f5_m01a_preparacion.ipynb](notebooks/fase5_modelado/f5_m01a_preparacion.ipynb) | Split 80/20 (`random_state=42`) y pipeline → `X_train/X_test(_prep).parquet`, `y_train/y_test.parquet`, **`pipeline_preprocesamiento.pkl`**, `meta_preparacion.json`. |
| 2 | [f5_m01b_lineales_basico.ipynb](notebooks/fase5_modelado/f5_m01b_lineales_basico.ipynb) | Lineales básicos. |
| 3 | [f5_m01c_lineales_ext.ipynb](notebooks/fase5_modelado/f5_m01c_lineales_ext.ipynb) | Lineales extendidos. |
| 4 | [f5_m01d_lineales.ipynb](notebooks/fase5_modelado/f5_m01d_lineales.ipynb) | Consolida → `results_lineales_completo.parquet`. |
| 5 | [f5_m02_arboles.ipynb](notebooks/fase5_modelado/f5_m02_arboles.ipynb) | Árboles → `results_arboles.parquet`. |
| 6 | [f5_m03_boosting.ipynb](notebooks/fase5_modelado/f5_m03_boosting.ipynb) | **Gradient boosting (incluye LightGBM) → `LightGBM__none.pkl` y demás `.pkl` en `data/05_modelado/models/` + `results_boosting.parquet`.** |
| 7 | [f5_m04_otros.ipynb](notebooks/fase5_modelado/f5_m04_otros.ipynb) | Otros (KNN, etc.) → `results_otros.parquet`. |
| 8 | [f5_m05_mlp_ebm.ipynb](notebooks/fase5_modelado/f5_m05_mlp_ebm.ipynb) | MLP + EBM → `results_mlp_ebm.parquet`. |
| 9 | [f5_m06_ensambles.ipynb](notebooks/fase5_modelado/f5_m06_ensambles.ipynb) | Ensambles → `results_ensambles.parquet`. |
| 10 | [f5_m07_comparacion.ipynb](notebooks/fase5_modelado/f5_m07_comparacion.ipynb) | **Tabla maestra de 69 combinaciones → `data/05_modelado/results/resultados_maestro.parquet`** + `top3_fase6.json`. |
| 11 | [f5_m00_indice.ipynb](notebooks/fase5_modelado/f5_m00_indice.ipynb) | Índice (al final). |

**Salidas clave:**
- `data/05_modelado/models/*.pkl` — los 69 modelos entrenados (entre ellos `LightGBM__none.pkl`).
- `data/05_modelado/pipeline_preprocesamiento.pkl` — pipeline de preprocesamiento.
- `data/05_modelado/results/resultados_maestro.parquet` — tabla de resultados sobre la que se
  selecciona el ganador.

> **Nota metodológica:** `f5_m07` ordena por AUC en validación cruzada (lidera XGBoost en CV).
> El **modelo definitivo NO se fija aquí**: se selecciona en Fase 6 sobre el conjunto de test con
> criterio F1 (desempate por recall). Ver sección 3.

---

### Fase 6 — Interpretabilidad, equidad y evaluación final

**Preparación previa (ejecutar ANTES del orquestador, en este orden):**

| Orden | Notebook | Qué genera |
|---|---|---|
| P1 | [f6_m00_preparacion.ipynb](notebooks/fase6_evaluacion/f6_m00_preparacion.ipynb) | **Selecciona el modelo ganador y genera `data/06_evaluacion/metricas_modelo.json`** (fuente única de verdad) + `meta_test.parquet` + `X_test_prep_ids.parquet`; regenera `index.html` y `fase7_index.html`. |
| P2 | [f6_m00b_preparacion_app.ipynb](notebooks/fase6_evaluacion/f6_m00b_preparacion_app.ipynb) | `meta_test_app.parquet` (metadatos + features originales + flags `_missing`) para la app. |
| P3 | [f6_m00c_export_probs.ipynb](notebooks/fase6_evaluacion/f6_m00c_export_probs.ipynb) | Añade las probabilidades del modelo ganador a `meta_test_app.parquet`. |

**Orquestador:** [notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb](notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb)
(lanza los 17 notebooks siguientes; requiere `meta_test.parquet` ya generado):

| Orden | Notebook | Contenido |
|---|---|---|
| 1–4 | f6_m01/m02/m03/m04 `_indice.ipynb` | Índices de grupo (SHAP, interpretabilidad, fairness, robustez). |
| 5 | [f6_m01a_shap_global.ipynb](notebooks/fase6_evaluacion/f6_m01a_shap_global.ipynb) | SHAP global. |
| 6 | [f6_m01b_shap_local.ipynb](notebooks/fase6_evaluacion/f6_m01b_shap_local.ipynb) | SHAP local. |
| 7 | [f6_m01c_shap_cohortes.ipynb](notebooks/fase6_evaluacion/f6_m01c_shap_cohortes.ipynb) | SHAP por cohortes. |
| 8 | [f6_m01d_shapash.ipynb](notebooks/fase6_evaluacion/f6_m01d_shapash.ipynb) | Dashboard Shapash. |
| 9 | [f6_m02a_lime.ipynb](notebooks/fase6_evaluacion/f6_m02a_lime.ipynb) | LIME. |
| 10 | [f6_m02b_dice.ipynb](notebooks/fase6_evaluacion/f6_m02b_dice.ipynb) | Contrafactuales DiCE. |
| 11 | [f6_m03a_fairness.ipynb](notebooks/fase6_evaluacion/f6_m03a_fairness.ipynb) | Equidad (sexo, vía acceso, beca, rama, origen). |
| 12 | [f6_m03b_errores_fpfn.ipynb](notebooks/fase6_evaluacion/f6_m03b_errores_fpfn.ipynb) | Análisis de errores FP/FN. |
| 13 | [f6_m04a_stress.ipynb](notebooks/fase6_evaluacion/f6_m04a_stress.ipynb) | Stress test. |
| 14 | [f6_m04b_calibracion.ipynb](notebooks/fase6_evaluacion/f6_m04b_calibracion.ipynb) | Calibración. |
| 15 | [f6_m04c_sostenibilidad.ipynb](notebooks/fase6_evaluacion/f6_m04c_sostenibilidad.ipynb) | Sostenibilidad (CodeCarbon). |
| 16 | [f6_m04d_robustez_temporal.ipynb](notebooks/fase6_evaluacion/f6_m04d_robustez_temporal.ipynb) | Robustez temporal. |
| 17 | [f6_m06_informe_final.ipynb](notebooks/fase6_evaluacion/f6_m06_informe_final.ipynb) | Informe ejecutivo final. |

**Salida clave:** `data/06_evaluacion/metricas_modelo.json` (fuente única de verdad de la app) y
los resultados de interpretabilidad/equidad en `results/fase6/`.

> **(verificar):** la lista de `f6_m00_ejecucion` no incluye `m05` (`f6_m05_robustez_calibracion`,
> que parece una versión consolidada alternativa de `m04a/m04b`). Seguir el orden literal del orquestador.

---

## 3. Cómo se obtiene el modelo ganador

El proyecto es un **sistema dinámico**: el ganador **no está hardcodeado**, se selecciona por reglas.

1. **Fase 5** entrena los 69 modelos y guarda sus `.pkl` y la tabla `resultados_maestro.parquet`.
2. **`f6_m00_preparacion.ipynb`** (celda de selección) lee `resultados_maestro.parquet` y aplica
   los criterios definidos en [src/config_modelado.py](src/config_modelado.py), en cascada:
   1. **F1** sobre test (`criterio_seleccion`) — métrica principal.
   2. **Recall** (`criterio_desempate`) — desempate (coste de un falso negativo > falso positivo).
   3. **AUC** — segundo desempate.
   4. **Tiempo** — tercer desempate (eficiencia).
3. El ganador resultante es **LightGBM** con estrategia `none` → `LightGBM__none.pkl`:
   - F1 = 0,8334 · Recall = 0,8048 · AUC = 0,9564 · Precision = 0,8641 · Accuracy = 0,9059.
   - Baseline AutoML de referencia: TabPFN v2 (D_strict), AUC ≈ 0,9644 · F1 = 0,8496.
4. Esas cifras se escriben en `data/06_evaluacion/metricas_modelo.json`, que la app y los informes
   leen como **única fuente de verdad** (sin valores numéricos incrustados en código).

> Si se reentrena la Fase 5 con datos distintos y otro modelo gana por estos criterios, basta con
> regenerar el JSON: la app y los HTML reflejan el nuevo ganador automáticamente. El rol de ganador
> está fijado a LightGBM con los datos actuales; **no debe sustituirse manualmente**.

---

## 4. Cómo se lanza la app Streamlit (Fase 7)

La Fase 7 **no es un notebook**: es la aplicación web en [app/](app/).

### 4.1 Ficheros que la app necesita (críticos)

Definidos en [app/config_app.py](app/config_app.py) y verificados al arrancar
(`verificar_ficheros_criticos`):

| Fichero | Generado en |
|---|---|
| `data/06_evaluacion/metricas_modelo.json` | Fase 6 — `f6_m00_preparacion` (define `modelo_pkl`). |
| `data/05_modelado/models/LightGBM__none.pkl` | Fase 5 — `f5_m03_boosting` (nombre leído del JSON). |
| `data/05_modelado/pipeline_preprocesamiento.pkl` | Fase 5 — `f5_m01a_preparacion`. |
| `data/06_evaluacion/meta_test.parquet` | Fase 6 — `f6_m00_preparacion`. |
| `data/06_evaluacion/meta_test_app.parquet` | Fase 6 — `f6_m00b` + `f6_m00c`. |

### 4.2 Lanzar la app

```bash
conda activate tfm_abandono
streamlit run app/main.py
```

Se abrirá el navegador en `http://localhost:8501`. La app tiene 7 páginas
([app/pages/](app/pages/)): inicio, institucional, titulación, prospecto, en curso, equidad y leyenda.

> **Atajos:** [arrancar_proyecto.bat](arrancar_proyecto.bat) (Windows) y
> [arrancar_proyecto.sh](arrancar_proyecto.sh) (macOS/Linux) activan el entorno y lanzan Jupyter;
> [scripts/ejecutar_streamlit.bat](scripts/ejecutar_streamlit.bat) lanza directamente la app.

---

## 5. Secuencia mínima para reproducir desde cero (resumen)

Con los datos originales en `data/00_raw/`:

```
1. conda create -n tfm_abandono python=3.11 -y  &&  conda activate tfm_abandono
2. pip install -r requirements_proyecto.txt
3. notebooks/fase0_configuracion/00_configuracion_proyecto.ipynb   (estructura de carpetas)
4. notebooks/fase1_transformacion/f1_m00_ejecucion.ipynb           (→ df_alumno.parquet)
5. notebooks/fase2_eda/f2_m00_ejecucion.ipynb                      (EDA inicial, opcional para datos)
6. notebooks/fase3_features/f3_m00_ejecucion.ipynb                 (→ dataset_final_tfm.parquet + target)
7. notebooks/fase_automl/fautoml_m00_ejecucion.ipynb               (→ baseline JSON)   (verificar slot vs F4)
8. notebooks/fase4_eda/f4_m00_ejecucion.ipynb                      (→ df_eda_final.parquet)
9. notebooks/fase5_modelado/f5_m00_ejecucion.ipynb                 (→ *.pkl + resultados_maestro.parquet)
10. notebooks/fase6_evaluacion/f6_m00_preparacion.ipynb            (→ metricas_modelo.json + meta_test)
11. notebooks/fase6_evaluacion/f6_m00b_preparacion_app.ipynb       (→ meta_test_app.parquet)
12. notebooks/fase6_evaluacion/f6_m00c_export_probs.ipynb          (→ probabilidades en meta_test_app)
13. notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb              (interpretabilidad + equidad)
14. streamlit run app/main.py                                      (app web)
```

(Alternativa: ejecutar todo desde
[notebooks/fase0_configuracion/orquestador_maestro.ipynb](notebooks/fase0_configuracion/orquestador_maestro.ipynb).)

---

## Resumen final

Este proyecto se regenera ejecutando, en orden, los **orquestadores de fase**
(`fX_m00_ejecucion.ipynb`), encadenados por la cadena de datos
`00_raw → 01_interim/02_processed → 03_features (+ AutoML) → 04_eda → 05_modelado → 06_evaluacion`,
y se corona con la app Streamlit. El **modelo ganador (LightGBM, `LightGBM__none.pkl`)** no está
fijado en el código: la Fase 5 entrena los 69 modelos y **`f6_m00_preparacion`** lo selecciona por
criterios en cascada (F1 → recall → AUC → tiempo), volcando todo a `metricas_modelo.json`, la
**fuente única de verdad** que alimenta informes y app. Las Fases 1–3 y AutoML exigen los datos
originales de la UJI (no versionados); las Fases 4–6 son reproducibles con los `.parquet` derivados.
Para ver el resultado final basta con `streamlit run app/main.py` tras haber generado los ficheros
críticos. Los puntos marcados **(verificar)** son matices de orden interno que conviene contrastar
ejecutando, ya que la inspección estática no los resuelve con total certeza.
