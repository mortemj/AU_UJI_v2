# Estado de traspaso — prompts 6 y 7

## Carpetas generadas en C:\TFM_Claude\ (pendientes de copiar)
| Carpeta | Contenido | Estado |
|---|---|---|
| _arquitectura/ | diagrama 6 capas .mmd + .md | ✅ Prompt 1 |
| _trazabilidad_datos/ | inventario datasets, Sankey, genealogía variables | ✅ Prompt 2 |
| _model_card/ | model_card v1 + v2 | ✅ Prompt 3 |
| _trazabilidad_notebooks/ | 117 notebooks, grafos, Excel, HTML navegable | ✅ Prompt 4 |
| _catalogo_funciones/ | 384 funciones, Excel 8 columnas | ✅ Prompt 5 |
| _reproduccion/ | GUIA, CHECKLIST, TIEMPOS, DEPENDENCIAS, TROUBLESHOOTING, LIMITACIONES_ETICA, ESTADO_TRASPASO | ✅ Prompts 6+7 |

## Correcciones aplicadas en C:\TFM_Claude\
- README.md líneas 78 y 90: 168 → 83 modelos AutoML
- src/config_modelado.py línea 278: 168 → 83
- _reproduccion/TIEMPOS_ESTIMADOS.md: tiempo LightGBM corregido a 11,247 s

## Pendientes post-defensa
- Copiar todo a C:\FF\AU_UJI_v2\ y push a GitHub
- Unificar ruta dataset_final_tfm.parquet (eliminar alias LEGACY)
- Investigar feature_ranking_m06.parquet
- OfflineEmissionsTracker ESP + JSON desde f6_m04c
- Corrección README:74 baseline (CatBoost → TabPFN)
