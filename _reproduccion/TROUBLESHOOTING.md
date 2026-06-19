# Troubleshooting — problemas conocidos AU_UJI_v2

> Problemas ya documentados en el propio proyecto y cómo resolverlos.
> Las rutas y comportamientos están verificados contra el código fuente.

---

## (a) Enlace/nombre roto: `feature_ranking_m06.parquet`

**Síntoma:** al ejecutar [f4_m09_conclusiones_eda.ipynb](../notebooks/fase4_eda/f4_m09_conclusiones_eda.ipynb)
aparece:

```
⚠️  ranking M06 no encontrado — columna AutoML será 0. Ejecuta f4_m06 primero.
```

**Causa:** el notebook busca el ranking de features bajo **varios nombres posibles**
según la versión ejecutada:

```python
_NOMBRES_RANKING = [
    'f4_m06_correlaciones_tabla.parquet',   # nombre vigente (lo genera f4_m06)
    'feature_ranking_m06.parquet',          # nombre antiguo
    'ranking_final_fase4.parquet',
]
```

Si no encuentra ninguno, usa como *fallback* la ruta antigua
`RUTA_AUTOML / 'feature_ranking_m06.parquet'`, que puede no existir → la columna
AutoML queda a 0.

**Solución:** ejecutar antes [f4_m06_correlaciones.ipynb](../notebooks/fase4_eda/f4_m06_correlaciones.ipynb),
que genera `f4_m06_correlaciones_tabla.parquet` (nombre vigente). Respetar el orden
del orquestador de Fase 4 evita el problema.

---

## (b) Alias LEGACY de `dataset_final_tfm.parquet`

**Contexto:** en [src/config_entorno.py](../src/config_entorno.py) conviven dos rutas
para el dataset de modelado:

```python
DATASET_MODELADO        = RUTA_FEATURES / 'dataset_final_tfm.parquet'   # ubicación definitiva (data/03_features/)
DATASET_MODELADO_LEGACY = RUTA_AUTOML   / 'dataset_final_tfm.parquet'   # alias de compatibilidad (data/automl/)
```

**Causa:** el fichero se generó originalmente en `data/automl/` y se trasladó a
`data/03_features/`. El alias `DATASET_MODELADO_LEGACY` se mantiene como compatibilidad
mientras se actualizan los notebooks (hay TODOs pendientes en el fichero para Fase 3,
AutoML y `config_app.py`).

**Implicación / solución:**
- Usar siempre **`DATASET_MODELADO`** (ruta `data/03_features/`) en código nuevo.
- No confiar en `DATASET_MODELADO_LEGACY`: es transitorio y está marcado para eliminación.
- Si un notebook antiguo de AutoML lee de `data/automl/`, asegurarse de que el fichero
  existe en ambas ubicaciones o actualizar la referencia. **(verificar)** qué ubicación
  física está realmente presente tras regenerar Fase 3.

---

## (c) `f6_m05` vs `f6_m04d` — cuál es el vigente

**Contexto:** existen dos notebooks con la **misma descripción** ("métricas de robustez
temporal, calibración y sostenibilidad para la sección 4.8"):

- [f6_m04d_robustez_temporal.ipynb](../notebooks/fase6_evaluacion/f6_m04d_robustez_temporal.ipynb) — **vigente**.
- [f6_m05_robustez_calibracion.ipynb](../notebooks/fase6_evaluacion/f6_m05_robustez_calibracion.ipynb) — versión consolidada alternativa.

**Cuál usar:** **`f6_m04d` es el vigente**. Es el que figura en la lista `NOTEBOOKS`
del orquestador [f6_m00_ejecucion.ipynb](../notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb);
`f6_m05` **no** aparece en esa lista.

**Solución:** ejecutar la Fase 6 mediante su orquestador, que ya lanza `m04d` y omite
`m05`. No ejecutar `f6_m05` de forma manual salvo que se quiera comparar.

---

## (d) Problema "Canadá" en CodeCarbon (geolocalización por IP)

**Síntoma:** al medir emisiones con CodeCarbon, la huella se calcula con el mix
energético de un país equivocado (p. ej. Canadá) porque CodeCarbon **geolocaliza por
la IP** (afectado por VPN, proxy o servidor en el extranjero).

**Solución (ya aplicada en el proyecto):** usar `OfflineEmissionsTracker` fijando el
país a España, como en [notebooks/defensa/sostenibilidad_defensa.ipynb](../notebooks/defensa/sostenibilidad_defensa.ipynb):

```python
from codecarbon import OfflineEmissionsTracker

tracker = OfflineEmissionsTracker(
    country_iso_code="ESP",          # fija España: ni VPN ni IP cambian esto
    project_name="TFM_defensa_LightGBM",
    output_dir=str(OUTPUT_DIR),
    output_file="emissions.csv",
    measure_power_secs=1,
    log_level="error",
)
tracker.start()
modelo.fit(X_train, y_train)
emisiones_kg = tracker.stop()
```

Con `country_iso_code="ESP"` la medición es independiente de la ubicación o de la VPN.
Salida: `data/06_evaluacion/sostenibilidad_defensa/emissions.csv`.

> El cálculo de sostenibilidad dentro de la Fase 6 está en
> [f6_m04c_sostenibilidad.ipynb](../notebooks/fase6_evaluacion/f6_m04c_sostenibilidad.ipynb).
> **(verificar)** si ese módulo usa también `OfflineEmissionsTracker` con `country_iso_code="ESP"`.
