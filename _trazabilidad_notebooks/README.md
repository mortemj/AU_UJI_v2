# Trazabilidad de notebooks — AU_UJI_v2

Generado en modo **solo lectura**: este análisis se basa exclusivamente en lo leído
en los `.ipynb` (búsqueda de `read_*` / `to_*` / `joblib` / `render_pagina`, etc.).
Donde no se pudo confirmar algo se marca **(verificar)**. No se han modificado ficheros del repo.

## Contenido

- `inventario_notebooks.xlsx` — libro con 4 hojas:
  - **`inventario`** — una fila por notebook (117 en total): `notebook · fase · que_hace · entradas ·
    salidas · uso · huerfano` (la columna `huerfano` marca la categoría A/B/C, filtrable).
  - **`huerfanos`** — los 18 notebooks huérfanos clasificados (`categoria · notebook · fase · motivo`).
  - **`matriz_aristas`** — las 204 aristas de los grafos (`grafo · origen · sentido · tipo · etiqueta ·
    destino`) para auditar el grafo arista a arista.
  - **`auditoria_artefactos`** — auditoría a nivel de FICHERO (174 artefactos): quién produce y quién
    consume cada parquet/pkl/json/…, con detección de **enlaces rotos** y **salidas no consumidas**
    (heurística por nombre de fichero; ver más abajo).
- `index_grafos.html` — **página HTML autónoma navegable** que embebe los 10 grafos renderizados
  (pestañas por fase + maestro, con enlaces de descarga). Abrir en el navegador. No toca el `docs/html` del proyecto.
- `grafos/` — para cada grafo: fuente `.mmd` + render `.svg` + render `.png`:
  - `fase0`, `fase1`, `fase2`, `fase3`, `fase4`, `fase_automl`, `fase5`, `fase6`, `app` — encadenamiento interno de cada fase.
  - `maestro_fases` — relación **entre** fases con el **notebook puente** etiquetado en cada arista.
- Scripts auxiliares (regeneran el Excel; ejecutar en este orden): `_generar_inventario.py` →
  `_anadir_matriz_aristas.py` → `_auditoria_artefactos.py`.

> Para ver los grafos: abrir `index_grafos.html`, los `.svg`/`.png` de `grafos/`, o pegar el `.mmd`
> en https://mermaid.live / extensión Mermaid de VS Code.
> Convención de aristas: **flecha sólida** = el origen genera un artefacto que el destino consume;
> **flecha discontinua** = dependencia opcional, orquestación (`%run`/nbconvert) o paso a verificar.

> **Sobre la hoja `auditoria_artefactos`:** el emparejamiento productor↔consumidor se hace por NOMBRE de
> fichero (no por ruta), porque el inventario mezcla rutas largas y cortas. Las referencias con glob (`*`)
> o placeholder (`<ganador>`) se marcan "no auditable". Tras filtrar ese ruido, el único **enlace roto**
> real es `feature_ranking_m06.parquet` (lo consume `f4_m09_conclusiones_eda` como *fallback* pero ningún
> notebook lo produce); el resto de "enlaces rotos" son modelos `.pkl` listados como glob en el productor
> y por nombre exacto en el consumidor (no son fallos reales).

## Notebooks por fase

| Fase | Notebooks | Notebook(s) PUENTE hacia la fase siguiente |
|------|-----------|--------------------------------------------|
| fase0 (configuración) | 6 | `f0_setup_demo` → `data/00_raw/*.xlsx` |
| fase1 (transformación) | 14 | `f1_m04d_correccion_via_acceso` → `df_alumno.parquet` |
| fase2 (EDA descriptivo) | 10 | *(rama de análisis; no alimenta el modelado)* |
| fase3 (features + target) | 14 | `f3_m05_target_export` → `dataset_final_tfm.parquet`; `f3_m08_auditoria` → `df_eda_final.parquet` |
| fase_automl (benchmark frameworks) | 13 | `fautoml_m07_comparativa` → `automl_top_modelos.parquet` |
| fase4 (EDA features/target) | 11 | *(rama de análisis; produce `ranking_final_fase4`)* |
| fase5 (modelado) | 16 | `f5_m07_comparacion` → `resultados_maestro` + `top3_fase6`; `f5_m01a` → `*_prep`; `f5_m03` → modelos `.pkl` |
| fase6 (evaluación/interpretab.) | 26 | `f6_m00_preparacion` → `metricas_modelo.json`; `f6_m00b`/`f6_m00c` → `meta_test_app.parquet` |
| app (Fase 7, Streamlit) | 0 notebooks (módulos `.py`) | — |
| misc/utils/defensa/linaje | 7 | — |

**Total: 117 notebooks.**

## Cadena principal del pipeline (puentes)

```
fase0 ──(00_raw/*.xlsx · f0_setup_demo)──▶ fase1
fase1 ──(df_alumno.parquet · f1_m04d)──▶ fase2 (EDA) y fase3
fase3 ──(dataset_final_tfm · f3_m05)──▶ fase_automl y fase5
fase3 ──(df_eda_final · f3_m08)──▶ fase4
fase_automl ──(automl_top_modelos · fautoml_m07)──▶ fase4
fase5 ──(modelos + resultados_maestro + *_prep · f5_m07/f5_m01a/f5_m03)──▶ fase6
fase6 ──(meta_test_app.parquet + metricas_modelo.json · f6_m00b/m00c/m00_preparacion)──▶ app
```

`metricas_modelo.json` es la **fuente única de métricas**: la genera `f6_m00_preparacion` y
la actualizan `f6_m00c_export_probs` y `f6_m04d_robustez_temporal` (resto solo lee). El modelo
ganador `LightGBM__none.pkl` nunca se hardcodea: se lee del JSON y se carga con `joblib`.

## Notebooks huérfanos (nadie consume su salida en el pipeline)

**A) Utilidades / diagnóstico** (no producen artefactos del pipeline; solo imprimen o verifican):
- `leer_parquet`, `verificar_df_alumno`, `columnas_parquet`
- `ver_entornos`, `comproba_parquet_2`, `comprobar_existe_parquet`, `fautoml_setup_entornos`
- `modelos`, `shap_importancia_comparativa`, `verificacion_pre_m01a`
- `plantilla_fX_m0Y` (andamiaje para crear nuevos módulos)

**B) Terminales / laterales** (producen salidas que ningún otro notebook consume; son entregables finales o para la memoria/defensa):
- `explorar_titulaciones` → `titulaciones_inventario.xlsx`
- `extraer_datos_ilustraciones_v3` → `output_para_claude/*.json`
- `f1_linaje` → `docs/html/linaje/...` (documentación de linaje)
- `energy_consumed`, `sostenibilidad_defensa` → sostenibilidad para la defensa
- `f0_actualizar_resumen` → regenera HTML (no encadenado)

**C) Duplicado confirmado (resuelto):**
- `f6_m05_robustez_calibracion` es un **duplicado** de `f6_m04d_robustez_temporal`: ambos calculan las
  mismas métricas (Sec 4.8) y **escriben los mismos ficheros** en `data/06_interpretacion/robustez/`,
  y ambos actualizan el mismo bloque `robustez_calibracion_sostenibilidad` de `metricas_modelo.json`.
  **`m04d` es el vigente** (es el único de los dos incluido en la lista `NOTEBOOKS` del orquestador
  `f6_m00_ejecucion`). **`m05` NO está orquestado** (ejecución manual), aunque su salida
  `auc_por_cohorte.parquet` la consume `extraer_datos_ilustraciones_v3`. → Tras la defensa, eliminar `m05`.

> Nota: los notebooks `*_m00_indice` (portadas HTML) y `*_m00_ejecucion` (orquestadores) son
> **hojas terminales esperadas** del pipeline (su producto es la web / la ejecución), no se cuentan como huérfanos.

## ⚠️ PENDIENTE POST-DEFENSA: discrepancia `dataset_final_tfm.parquet`

Confirmado leyendo `src/config_entorno.py` y los notebooks (solo lectura): **Fase 3 y Fase 5
usan rutas distintas** para `dataset_final_tfm.parquet`.

- **Fase 3 ESCRIBE en `data/automl/` (ruta LEGACY)**: `f3_m05_target_export` →
  `RUTA_AUTOML / 'dataset_final_tfm.parquet'`; `f3_m08_auditoria` también opera sobre esa misma ruta.
- **Fase 5 LEE de `data/03_features/` (ruta canónica)**: `f5_m01a_preparacion` →
  `pd.read_parquet(DATASET_MODELADO)`, con `DATASET_MODELADO = RUTA_FEATURES / 'dataset_final_tfm.parquet'`.
- En `config_entorno.py` conviven `DATASET_MODELADO` (`data/03_features/`, canónica) y
  `DATASET_MODELADO_LEGACY` (`data/automl/`, marcada como *"alias temporal — eliminar tras Chat 3/4/8"* con TODOs).
- **Ambos ficheros existen y su contenido es IDÉNTICO byte a byte** (verificado con hash, solo lectura):
  mismo tamaño (432.346 bytes), mismo `MD5 = 3c44cc369d12ebce3d7f9cfb22641fa2` y
  mismo `SHA-256 = 209e2097bd573f886241bb4b8952bba450abae7fe7cb4e1bd68e8cb83573f8a4`.
  Solo difiere la fecha: la copia canónica (`data/03_features/`, mtime 2026-05-18) es ~1 mes más antigua
  que la de `data/automl/` (mtime 2026-06-15).
- **Ningún notebook ni script copia de una ruta a la otra**: la sincronización es manual o quedó de una
  versión previa. Como los hashes coinciden, **a día de hoy Fase 5 lee exactamente los mismos datos que
  produce Fase 3** (no hay divergencia de contenido).

> **Riesgo real: solo de MANTENIMIENTO futuro, no de datos divergentes ahora.** Hoy las dos copias son el
> mismo fichero. El peligro es que una reejecución de Fase 3 (que escribe en `data/automl/`) actualice esa
> copia mientras la de `data/03_features/` que lee Fase 5 se quede atrás, sin nadie que las sincronice.
> Diagnóstico, no corrección: no se ha modificado ningún fichero del pipeline. Resolver tras la defensa
> (unificar a `DATASET_MODELADO` = `data/03_features/` y eliminar el alias LEGACY).

## Puntos a verificar (no se inventan)

1. **Ruta de `dataset_final_tfm.parquet`** → confirmado: ver sección ⚠️ PENDIENTE POST-DEFENSA arriba
   (Fase 3 escribe en `data/automl/`, Fase 5 lee de `data/03_features/`; contenido idéntico por hash).
2. ~~Nombre del Excel de `f3_m06_alerta_temprana`~~ → **resuelto**: `data/automl/quick_baseline_casoD.xlsx`
   (hojas `todos` + por caso); además `quick_baseline_casoD.parquet` y `feature_importance_caso{caso}.png` en `data/automl/`.
3. ~~Carpeta de los PNG de trazabilidad de Fase 1~~ → **resuelto**: el código los escribe en
   `docs/html/fase1/trazabilidad_fase1.png/.jpg` (`RUTA_FASE1 = RUTA_HTML/'fase1'`); el texto que decía
   `results/fase1/` era solo de la celda markdown, no del código.
4. ~~Vigencia entre `f6_m04d` y `f6_m05`~~ → **resuelto**: `m04d` vigente, `m05` duplicado no orquestado
   (ver sección de huérfanos, apartado C).
5. Las rutas absolutas que aparecen en los *outputs* cacheados de algunas celdas
   (`C:\PRUEBAS\...`, `C:\FF\...`) son de ejecuciones en otras máquinas; las rutas reales
   se derivan de `ROOT`/`src.config` en tiempo de ejecución.
