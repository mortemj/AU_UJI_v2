# Dependencias críticas — AU_UJI_v2

> Solo se listan las dependencias que **bloquean toda la cadena** si faltan:
> el fichero que produce cada fase y las fases siguientes que lo necesitan.
> Si uno de estos ficheros no se genera, las fases consumidoras fallan.
> Información extraída de los apartados *Requisitos/Genera* de los notebooks.

## Cadena lineal de ficheros bloqueantes

```
data/00_raw/*.xlsx                              (datos originales UJI — sin ellos no arranca F1)
        │  Fase 1
        ▼
data/02_processed/df_alumno.parquet             (dataset unido a nivel alumno)
        │  Fase 3
        ▼
data/automl/dataset_final_tfm.parquet           (dataset analítico + target `abandono`)
        ├──────────────► AutoML ─► data/automl/automl_comparativa_final.json   (baseline)
        │  Fase 5                                         │
        ▼                                                 │
data/05_modelado/                                         │
  ├─ models/LightGBM__none.pkl  (+ resto de .pkl)         │
  ├─ pipeline_preprocesamiento.pkl                        │
  ├─ X_test_prep.parquet / y_test.parquet                 │
  └─ results/resultados_maestro.parquet ◄─────────────────┘ (f5_m07 lee el baseline)
        │  Fase 4 (en paralelo) ─► data/04_eda/df_eda_final.parquet
        ▼
data/06_evaluacion/metricas_modelo.json         (fuente única de verdad — selecciona el ganador)
        │  Fase 6 (m00b + m00c)
        ▼
data/06_evaluacion/meta_test_app.parquet        (con probabilidades del ganador)
        │  Fase 7
        ▼
App Streamlit  (streamlit run app/main.py)
```

## Tabla: productor → consumidores

| Fichero crítico | Lo produce | Lo necesitan (consumidores) |
|---|---|---|
| `data/00_raw/*.xlsx` (datos originales) | — (aportados) | Fase 1 |
| `data/02_processed/df_alumno.parquet` | Fase 1 (`f1_m04*`) | Fase 3 |
| `data/automl/dataset_final_tfm.parquet` (+ target) | Fase 3 (`f3_m05_target_export`) | AutoML · Fase 4 · Fase 5 (`f5_m01a_preparacion`) |
| `data/03_features/df_exp_automl_target.parquet` | Fase 3 (`f3_m04a`) | AutoML · Fase 6 (`f6_m00_preparacion`) |
| `data/automl/automl_comparativa_final.json` (baseline) | AutoML (`fautoml_m07`) | Fase 5 (`f5_m07`) · Fase 6 (`f6_m00_preparacion`) |
| `data/04_eda/df_eda_final.parquet` | Fase 4 (`f4_m0*`) | Fase 6 (`f6_m00_preparacion`) |
| `data/05_modelado/models/LightGBM__none.pkl` (+ `.pkl`) | Fase 5 (`f5_m03_boosting`) | Fase 6 · App (modelo ganador) |
| `data/05_modelado/pipeline_preprocesamiento.pkl` | Fase 5 (`f5_m01a_preparacion`) | Fase 6 · App |
| `data/05_modelado/X_test_prep.parquet` · `y_test.parquet` | Fase 5 (`f5_m01a_preparacion`) | Fase 6 (`f6_m00_preparacion`, `f6_m00c`) |
| `data/05_modelado/results/resultados_maestro.parquet` | Fase 5 (`f5_m07_comparacion`) | Fase 6 (`f6_m00_preparacion`, selección del ganador) |
| `data/06_evaluacion/meta_test.parquet` | Fase 6 (`f6_m00_preparacion`) | Todos los submódulos de Fase 6 · `f6_m00b` |
| `data/06_evaluacion/metricas_modelo.json` (fuente única) | Fase 6 (`f6_m00_preparacion`) | App · informes · `f6_m00c` (lee `modelo_pkl`) |
| `data/06_evaluacion/meta_test_app.parquet` | Fase 6 (`f6_m00b` + `f6_m00c`) | App Streamlit |

## Ficheros críticos que verifica la app al arrancar

`app/config_app.py` → `verificar_ficheros_criticos()` exige **modelo**, **pipeline** y
**meta_test**:

- `data/06_evaluacion/metricas_modelo.json` (define `modelo_pkl`)
- `data/05_modelado/models/LightGBM__none.pkl`
- `data/05_modelado/pipeline_preprocesamiento.pkl`
- `data/06_evaluacion/meta_test.parquet`
- `data/06_evaluacion/meta_test_app.parquet`

Si falta alguno, la app muestra un cartel indicando que hay que ejecutar
`f6_m00_preparacion` y/o la Fase 5 completa.
