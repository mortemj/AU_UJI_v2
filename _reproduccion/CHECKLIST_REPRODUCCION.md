# Checklist de reproducción — AU_UJI_v2

> Lista de verificación de los **14 pasos** descritos en
> [GUIA_REPRODUCCION.md](GUIA_REPRODUCCION.md) (sección 5).
> Marca cada casilla a medida que completes el paso. No añade pasos nuevos.

## Preparación del entorno

- ☐ **1. Crear y activar el entorno conda** — `conda create -n tfm_abandono python=3.11 -y` y `conda activate tfm_abandono`.
- ☐ **2. Instalar dependencias** — `pip install -r requirements_proyecto.txt`.

## Configuración

- ☐ **3. Fase 0 — Estructura** — ejecutar [00_configuracion_proyecto.ipynb](../notebooks/fase0_configuracion/00_configuracion_proyecto.ipynb): crea las carpetas `data/01_interim … 06_evaluacion` y el `index.html`.

## Pipeline de datos (requiere datos originales en `data/00_raw/`)

- ☐ **4. Fase 1 — Transformación** — [f1_m00_ejecucion.ipynb](../notebooks/fase1_transformacion/f1_m00_ejecucion.ipynb) → `df_alumno.parquet`.
- ☐ **5. Fase 2 — EDA inicial** — [f2_m00_ejecucion.ipynb](../notebooks/fase2_eda/f2_m00_ejecucion.ipynb) (exploratoria; opcional para la cadena de datos).
- ☐ **6. Fase 3 — Feature engineering** — [f3_m00_ejecucion.ipynb](../notebooks/fase3_features/f3_m00_ejecucion.ipynb) → `dataset_final_tfm.parquet` + target `abandono`.
- ☐ **7. AutoML — Baseline** — [fautoml_m00_ejecucion.ipynb](../notebooks/fase_automl/fautoml_m00_ejecucion.ipynb) → `automl_comparativa_final.json`. *(verificar slot relativo a Fase 4)*
- ☐ **8. Fase 4 — EDA final** — [f4_m00_ejecucion.ipynb](../notebooks/fase4_eda/f4_m00_ejecucion.ipynb) → `df_eda_final.parquet`.

## Modelado y evaluación

- ☐ **9. Fase 5 — Modelado** — [f5_m00_ejecucion.ipynb](../notebooks/fase5_modelado/f5_m00_ejecucion.ipynb) → `models/*.pkl` (incl. `LightGBM__none.pkl`) + `resultados_maestro.parquet`.
- ☐ **10. Fase 6 — Preparación** — [f6_m00_preparacion.ipynb](../notebooks/fase6_evaluacion/f6_m00_preparacion.ipynb) → `metricas_modelo.json` + `meta_test.parquet`.
- ☐ **11. Fase 6 — Preparación app** — [f6_m00b_preparacion_app.ipynb](../notebooks/fase6_evaluacion/f6_m00b_preparacion_app.ipynb) → `meta_test_app.parquet`.
- ☐ **12. Fase 6 — Export de probabilidades** — [f6_m00c_export_probs.ipynb](../notebooks/fase6_evaluacion/f6_m00c_export_probs.ipynb) → probabilidades en `meta_test_app.parquet`.
- ☐ **13. Fase 6 — Interpretabilidad y equidad** — [f6_m00_ejecucion.ipynb](../notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb) (lanza los 17 submódulos SHAP/LIME/DiCE/fairness/robustez).

## Aplicación

- ☐ **14. Lanzar la app Streamlit** — `streamlit run app/main.py` (abre `http://localhost:8501`).

---

> **Alternativa global:** los pasos 3–13 pueden encadenarse desde
> [orquestador_maestro.ipynb](../notebooks/fase0_configuracion/orquestador_maestro.ipynb).
> **Comprobación opcional del entorno:** `pytest tests/ -v` → 42 passed.
