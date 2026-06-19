# Tiempos estimados de ejecución — AU_UJI_v2

> Estimación de duración por fase. Solo se reportan como exactos los datos
> **conocidos**; el resto se marca con **(verificar)** porque no consta una
> medición fiable en el repositorio. La ejecución completa del proyecto puede
> tardar **varias horas** (según el orquestador maestro), dominada por Fase 5,
> AutoML (TabPFN) y el cálculo SHAP de Fase 6.

## Datos de tiempo conocidos (medidos)

| Concepto | Tiempo | Fuente |
|---|---|---|
| Entrenamiento del modelo ganador **LightGBM** (estrategia `none`) | **11,247 s** | `tiempo_s` en `resultados_maestro.json` (valor canónico) |
| Inferencia de **TabPFN** (AutoML, desactivado en el orquestador) | **≈ 7,3 h** en CPU | nota en [fautoml_m00_ejecucion.ipynb](../notebooks/fase_automl/fautoml_m00_ejecucion.ipynb) |

> **Nota sobre otras cifras de tiempo de LightGBM:**
> - **25,15 s** — **no verificable en ficheros del repo**: no aparece en ningún
>   notebook, parquet, json ni HTML del proyecto (el clon de defensa
>   `sostenibilidad_defensa.ipynb` solo mide emisiones, no segundos).
> - **12,2 s** — corrida anterior, distinto hardware: es la salida de celda de
>   una ejecución previa de `f6_m00_preparacion.ipynb`; el valor actual en disco
>   (`resultados_maestro.json`) es 11,247 s.

## Estimación por fase

| Fase | Orquestador | Duración estimada | Comentario |
|---|---|---|---|
| **F0** · Configuración | `00_configuracion_proyecto` | Segundos–minutos **(verificar)** | Crea carpetas y `index.html`. |
| **F1** · Transformación | `f1_m00_ejecucion` | **(verificar)** | Incluye reportes Sweetviz (lentos sobre datos grandes). |
| **F2** · EDA inicial | `f2_m00_ejecucion` | **(verificar)** | Exploratoria. |
| **F3** · Feature engineering | `f3_m00_ejecucion` | **(verificar)** | Genera el dataset analítico + target. |
| **AutoML** · Baseline | `fautoml_m00_ejecucion` | Horas **(verificar total)** | Entrena en 4 frameworks. TabPFN (≈ 7,3 h) está **desactivado**; sus resultados ya están guardados. |
| **F4** · EDA final | `f4_m00_ejecucion` | **(verificar)** | Distribuciones, correlaciones, selección de features. |
| **F5** · Modelado | `f5_m00_ejecucion` | Es de las fases **más lentas** **(verificar total)** | Entrena **69 combinaciones** (23 algoritmos × estrategias `none`/`balanced`/`smote`). Referencia por modelo: LightGBM `tiempo_s` = 11,247 s. |
| **F6** · Interpretabilidad | `f6_m00_ejecucion` | El **cálculo SHAP** sobre el test completo es de lo más lento **(verificar total)** | 17 submódulos (SHAP, LIME, DiCE, fairness, calibración, robustez, sostenibilidad). Timeout configurado: 3.600 s por celda. |
| **F7** · App Streamlit | `streamlit run app/main.py` | Segundos (arranque) | No es un notebook; se lanza directamente. |

## Sobre los conteos de modelos

- **Fase 5:** 69 combinaciones (23 algoritmos × estrategias). Confirmado: el dato
  "69 configuraciones" corresponde a Fase 5 (69 filas en `resultados_maestro.json`),
  no a AutoML.
- **AutoML:** 83 modelos en 4 frameworks (AutoGluon, PyCaret, H2O, LazyPredict),
  según [README.md](../README.md) (87 brutos / 83 sin Dummy en
  `fautoml_m07_comparativa`).

---

> **Recomendación del orquestador maestro:** lanzar fase a fase usando los botones
> de pausa, ya que la ejecución completa puede tardar varias horas.
