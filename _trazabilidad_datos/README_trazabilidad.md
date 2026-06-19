# Trazabilidad de datos — TFM Predicción de Abandono Universitario (UJI)

Documentación del **viaje de los datos**, desde los Excel originales del Servicio
de Planificación de la Universitat Jaume I hasta el dataset final de modelado y
la app. Generada en **modo solo lectura**: todo el contenido de esta carpeta se
ha producido leyendo los esquemas reales de los `.parquet`/`.xlsx` y rastreando
los notebooks; **no se ha modificado ningún fichero del proyecto**.

## Contenido de la carpeta
| Fichero | Parte | Qué es |
|---|---|---|
| `inventario_datasets.csv` | A | Cadena de datasets: fase, nº filas, nº campos, generador y consumidores. |
| `genealogia_variables.xlsx` | B | Una fila por variable: origen → final, estado y motivo. |
| `sankey_flujo_datos.mmd` | C | Sankey en Mermaid (`sankey-beta`); valor = campos compartidos. |
| `sankey_flujo_datos.png` | C | Imagen del Sankey (espina principal, etiquetas en diagonal). |
| `columnas.json` | evidencia | Volcado literal de columnas/filas de cada dataset. |
| `io_map.json` | evidencia | Lectura/escritura de cada parquet por notebook/.py. |
| `_dump_columnas.py`, `_map_io.py`, `generar_entregables.py` | método | Scripts solo-lectura que producen lo anterior (reproducibilidad). |

> **Cómo exportar el Sankey Mermaid a imagen:** pegar `sankey_flujo_datos.mmd`
> en <https://mermaid.live>. La imagen `.png` ya está generada con matplotlib.

---

## PARTE A — Flujo de datasets (el recorrido de los ficheros)

Grano del dato: las tablas originales están a nivel **curso-alumno**; en la
Fase 3 se **agregan a nivel expediente** (un alumno-titulación por fila), pasando
de **109.568 → 33.621 filas**. Después se hace el split y el preprocesado.

### Cadena canónica (espina principal)

| # | Dataset | Fase · notebook generador | Filas | Campos | Principales consumidores |
|---|---------|---------------------------|------:|------:|--------------------------|
| 0a | `00_raw/datos_proyecto_sin_preinscrip.xlsx` (8 hojas) | datos originales (Servicio de Planificación UJI) | n/d | 4–15 por hoja | `f1_m02_limpieza` |
| 0b | `00_raw/preinscripcion_si.xlsx` (1 hoja) | datos originales | n/d | 24 | `f1_m02_limpieza` |
| 1 | `01_interim/*.parquet` (9 tablas) | **F1 · f1_m02_limpieza** | varía | 4–24 | `f1_m04a`, `f1_m04b/c` |
| 2 | `02_processed/df_alumno_base.parquet` | **F1 · f1_m04a_union_tablas** | 109.568 | 33 | `f1_m04b` |
| 3 | `02_processed/df_alumno.parquet` | **F1 · f1_m04b/c/d** | 109.568 | 37 | toda la Fase 2 (EDA) y `f3_m01`; **app** (p01) |
| 4 | `03_features/df_alumno_limpio.parquet` | **F3 · f3_m01_validacion** | 109.568 | 43 | `f3_m02`, `f3_m03`, `f6_m00` |
| 5 | `03_features/df_expediente_base.parquet` | **F3 · f3_m02_agregacion** | 33.621 | 41 | `f3_m03`, `f3_m08` |
| 6 | `03_features/df_expediente_features.parquet` | **F3 · f3_m03_features** | 33.621 | 51 | `f3_m04a`, `f3_m04b` |
| 7 | `03_features/df_exp_automl_target.parquet` | **F3 · f3_m04a_automl_target** | 33.621 | 49 | `f3_m04_index`, `f6_m00` |
| 8 | `03_features/dataset_final_tfm.parquet` | **F3 · f3_m05_target_export** | 33.621 | **25** (24 feat + target) | Fase AutoML, **F5 · f5_m01a** |
| 9 | `05_modelado/X_train / X_test (.parquet)` | **F5 · f5_m01a_preparacion** | 26.896 / 6.725 | 28 | todos los `f5_m0*` y `f6_*` |
| 10 | `05_modelado/X_train_prep / X_test_prep` | **F5 · f5_m01a_preparacion** | 26.896 / 6.725 | 28 | `f6_*` (SHAP, fairness…); **app** (pipeline) |
| 11 | `06_evaluacion/meta_test.parquet` | **F6 · f6_m00_preparacion** | 6.725 | 15 | `f6_m00b` |
| 12 | `06_evaluacion/meta_test_app.parquet` | **F6 · f6_m00b_preparacion_app** | 6.725 | 37 | **app** (loaders.py) |

### Ramas laterales (variantes y análisis, no entran al modelo)
- `03_features/df_exp_target_eda.parquet` (33.621×49) — **f3_m04b_eda_target**; usado por `f6_m01c`, `f6_m03a/b`.
- `03_features/df_eda_con_target.parquet` (33.621×41) — **f3_m05_target_export**; usado por `f3_m08`.
- `automl/df_exp_automl_D.parquet` (33.621×39) — **f3_m05_target_export**; caso D para AutoML.
- `04_eda/df_eda_final.parquet` (33.621×26) — **f3_m08_auditoria**; base de toda la Fase 4 (EDA).
- `04_eda/df_eda_perfiles.parquet` (33.621×28) — **f3_m09_perfiles_riesgo**; añade `score_riesgo`/`perfil_riesgo`.
- `automl/ranking_final_fase4.parquet`, `03_features/f4_m07_features_seleccionadas.parquet` — metadatos de selección de variables (F4).

### Datasets huérfanos detectados (se generan pero ningún notebook/.py los lee)
> Detección automática (`io_map.json`) + verificación. El parser solo ve lecturas
> con nombre de fichero literal; lecturas vía variable de ruta (p. ej. la app, que
> usa `RUTAS[...]`) pueden no aparecer. Por eso se marcan **(verificar)**.

1. **`df_longitudinal_trayectoria.parquet`** (109.568×23) — generado en `f3_m01_validacion`; **ningún consumidor detectado**. Parece tabla auxiliar de trayectoria. (verificar)
2. **`df_eda_perfiles.parquet`** (33.621×28) — generado en `f3_m09_perfiles_riesgo`; **ningún consumidor detectado**. Salida terminal de perfiles de riesgo (posible uso en informe/HTML). (verificar)
3. **`ranking_final_fase4.parquet`** (24×11) — generado en `f4_m09_conclusiones_eda`; **ningún consumidor detectado** (lectura probable vía variable en `f3_m08`/informes). (verificar)

> No son huérfanos: `df_alumno.parquet`, `X_*_prep.parquet` y `meta_test_app.parquet`
> sí se consumen, aunque desde la **app** (lecturas vía `RUTAS`, fuera del rastreo literal).

---

## PARTE B — Genealogía de variables

Tabla completa en `genealogia_variables.xlsx` (hoja `genealogia` + hoja `resumen`).
Columnas: `nombre_origen`, `nombre_final`, `fase_donde_nace`, `estado`, `motivo`.

- **Normalización general:** en `f1_m02_limpieza` todos los nombres de columna se
  pasan a `snake_case` minúsculas (`normalizar_nombre_columna`). Esto se refleja
  como `RENOMBRADA`/`SIN CAMBIOS` según si además cambia el significado.
- **Motivos:** se rellenan solo cuando se deducen del código; donde no hay
  evidencia clara se marca **(verificar)** en vez de inventar.

Resumen por estado (sobre las variables documentadas):

| estado | nº | ejemplos |
|---|---:|---|
| **NUEVA** (feature engineering, F3) | 15 | `abandono` (target), `edad_entrada`, `n_anios_beca`, `situacion_laboral`, `tasa_abandono_titulacion`, `anios_gap` |
| **RENOMBRADA** | 6 | `ORDEN_TITULACION→orden_preferencia`, `VIA_ESTUDIOS→via_acceso`, `CUPO→cupo` |
| **SIN CAMBIOS** (solo minúsculas) | 6 | `nota_acceso`, `nota_selectividad`, `rama`, `sexo`, `pais_nombre`, `provincia` |
| **ELIMINADA** | 15 | `Egresado` (→ se usa para el target y se descarta), `Fecha_nacimiento` (→ `edad_entrada`), `Seguro`, `Media_Titulacion_*` |

---

## PARTE C — Sankey del flujo de datasets

- **Nodos** = datasets. **Valor del flujo** = nº de **campos compartidos** (nombres
  de columna en común, en minúsculas) entre el dataset origen y el destino.
- Las **etiquetas de los nodos van en diagonal** (rotadas 30°) para no solaparse.
- **No** aparecen nombres de variables en el gráfico (esos están solo en el Excel).
- Dos formatos: `sankey_flujo_datos.mmd` (Mermaid) y `sankey_flujo_datos.png`
  (matplotlib). El `.png` muestra además la altura de cada nodo ∝ su nº de columnas.

> Nota metodológica: "campos que pasan al siguiente" se ha operacionalizado como
> **intersección de nombres de columna**, medida reproducible y literal. En los
> pasos donde cambia el grano (agregación F3) o hay renombrados, la intersección
> baja aunque la información se conserve transformada (p. ej. `df_exp_automl_target`
> → `dataset_final_tfm` comparte 23 nombres porque se seleccionan/renombran features).
