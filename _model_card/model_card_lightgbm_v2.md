# Tarjeta del Modelo (Model Card) — Modelo ganador

> Documento generado en modo **solo lectura**. Todos los valores numéricos se han
> leído directamente de `data/06_evaluacion/metricas_modelo.json` y de los
> ficheros de `results/fase6/`. No se ha recalculado, deducido ni inventado
> ninguna cifra. Los datos no disponibles se marcan como **(verificar)**.

---

## 1. Identificación del modelo

| Campo | Valor |
|---|---|
| Nombre | **LightGBM** |
| Familia | Gradient Boosting (boosting de gradiente basado en histogramas) |
| Descripción | Gradient boosting basado en histogramas — rápido y eficiente |
| Estrategia | `none` (sin remuestreo / sin reponderación) |
| Artefacto | `LightGBM__none.pkl` |
| Tamaño del artefacto | 932,67 KB (955.053 bytes) |
| Fecha de cálculo de métricas | 2026-05-14 |

El modelo LightGBM es el **modelo ganador** del proyecto y nunca es sustituido por
otro en ese papel.

---

## 2. Qué predice

El modelo predice el **abandono universitario**: estima la probabilidad de que un
estudiante abandone sus estudios de grado en la Universitat Jaume I.

- **Tarea:** clasificación binaria (abandono / no abandono).
- **Variable objetivo:** etiqueta binaria de abandono por estudiante-titulación.
- **Definición exacta de la variable objetivo:** `abandono = 1` cuando se cumplen
  las tres condiciones a la vez: (1) **no ha obtenido el título** (`egresado = "N"`),
  (2) **no es egresado de hecho** (`egresado_de_hecho = 0`), y (3) **lleva ≥ 2 años
  sin actividad académica** (`curso_ultimo ≤ 2019`, con curso de referencia 2021).
  En cualquier otro caso, `abandono = 0`. Las variables usadas para construir el
  target se eliminan tras la construcción para evitar *leakage*.
  Fuente: `notebooks/fase3_features/f3_m05_target_export.ipynb`.
- **Tasa de abandono observada (conjunto global):** 29,25 %.
- **Tasa de abandono en el conjunto de test:** 29,55 %.

---

## 3. Datos de entrenamiento

| Campo | Valor |
|---|---|
| Origen | Universitat Jaume I — datos atribuidos al Servicio de Planificación de la UJI |
| Tipo | Datos originales (registros académicos y administrativos) |
| Periodo | Cohortes 2010 – 2020 |
| Registros (estudiante-titulación) | 33.621 |
| Estudiantes únicos | 30.872 |
| Titulaciones | 40 |
| Nº de *features* (modelado) | 24 |
| Nº de *features* técnicas | 27 |
| *Features* de indicador de ausente (*missing*) | 3 |
| Tamaño del conjunto de test (total) | 6.725 |
| Tamaño del conjunto de test (evaluado) | 6.596 |

---

## 4. Métricas de rendimiento

Métricas sobre el conjunto de test (fuente única: `metricas_modelo.json`):

| Métrica | Valor |
|---|---|
| F1 | 0,8334 |
| AUC (ROC) | 0,9564 |
| Recall (sensibilidad) | 0,8048 |
| Precisión | 0,8641 |
| Accuracy | 0,9059 |

### Criterio de selección del ganador

Orden de prioridad: **F1 > Recall > AUC > Tiempo**.

- Criterio principal: `f1_test`.
- Criterio de desempate: `recall_test`.
- A igualdad, se considera AUC y, por último, el tiempo / coste computacional.

### Referencia (*baseline*) comparativa

| Modelo | AUC | F1 |
|---|---|---|
| LightGBM (ganador) | 0,9564 | 0,8334 |
| TabPFN v2 (*baseline*, dataset `D_strict`) | 0,9644 | 0,8496 |

> Nota: TabPFN v2 se reporta como referencia comparativa; el modelo desplegable y
> seleccionado como ganador es LightGBM.

---

## 5. Robustez

### Robustez temporal (validación por cohortes)

Evaluación sobre 10 cohortes (2010 – 2019):

| Métrica AUC | Valor |
|---|---|
| AUC media | 0,9645 |
| AUC mínima | 0,9168 |
| AUC máxima | 0,9919 |
| Desviación típica | 0,0273 |
| Rango | 0,0751 |

### Pruebas de estrés (`stress_resultados`)

- **Ruido:** F1 desciende de 0,8255 (5 % de ruido) a 0,7149 (50 %).
- **Outliers:** F1 desciende de 0,8314 (1 %) a 0,6882 (30 %).
- **Valores ausentes:** degradación marcada al eliminar las *features* más
  importantes; con 1 *feature* ausente (`cred_superados_anio_1er`) F1 = 0,7073, y
  cae hasta 0,4565 al ocultar las 5 más relevantes.

El modelo es sensible a la ausencia de las variables académicas de primer curso
(ver sección 7).

---

## 6. Calibración

| Método | Brier score |
|---|---|
| Original (sin recalibrar) | 0,0702 |
| Isotónico | 0,0711 |
| Platt | 0,0726 |

- ECE (10 *bins*): 0,0137.
- La calibración **original** ya es la mejor (menor Brier); el recalibrado
  isotónico o de Platt no la mejora.

---

## 7. Interpretabilidad — variables más influyentes (SHAP)

Importancia SHAP global del modelo ganador (10 primeras por *rank*):

| # | *Feature* | Importancia SHAP (LightGBM) |
|---|---|---|
| 1 | `cred_superados_anio_1er` | 0,7467 |
| 2 | `n_anios_trabajando` | 0,6960 |
| 3 | `n_anios_beca` | 0,6280 |
| 4 | `cred_repetidos` | 0,4479 |
| 5 | `anios_sin_beca` | 0,4231 |
| 6 | `situacion_laboral` | 0,4124 |
| 7 | `nota_1er_anio` | 0,3697 |
| 8 | `n_anios_sin_notas` | 0,3466 |
| 9 | `nota_acceso` | 0,2046 |
| 10 | `tasa_abandono_titulacion` | 0,1327 |

El rendimiento y la progresión académica del **primer curso** (créditos
superados, créditos repetidos, nota del primer año) junto con la situación
laboral y de beca son los factores dominantes.

---

## 8. Análisis de equidad (*fairness*)

Métricas por grupo (fuente: `fairness_metricas.parquet`). Se reportan recall y F1
por grupo y las diferencias de paridad demográfica (`dp_diff`), ratio de paridad
(`dp_ratio`) e igualdad de oportunidad (`eq_opp_diff`) por variable sensible.

| Variable sensible | Grupo | Recall | F1 | dp_diff | dp_ratio | eq_opp_diff |
|---|---|---|---|---|---|---|
| Sexo | Hombre | 0,8246 | 0,8428 | 0,1450 | 0,5884 | 0,0457 |
| Sexo | Mujer | 0,7789 | 0,8207 | 0,1450 | 0,5884 | 0,0457 |
| Beca | Con beca | 0,7293 | 0,7752 | 0,2890 | 0,3999 | 0,1644 |
| Beca | Sin beca | 0,8937 | 0,8982 | 0,2890 | 0,3999 | 0,1644 |
| Trabaja | No trabaja | 0,7179 | 0,7313 | 0,0925 | 0,6819 | 0,1008 |
| Trabaja | Trabaja | 0,8188 | 0,8501 | 0,0925 | 0,6819 | 0,1008 |
| Origen | España | 0,8098 | 0,8393 | 0,0740 | 0,7833 | 0,0598 |
| Origen | Extranjero | 0,7500 | 0,7688 | 0,0740 | 0,7833 | 0,0598 |
| Rama | Artes y Humanidades | 0,7466 | 0,8074 | 0,2287 | 0,3722 | 0,0725 |
| Rama | Ciencias Experimentales | 0,8095 | 0,8793 | 0,2287 | 0,3722 | 0,0725 |
| Rama | Ciencias Sociales y Jurídicas | 0,8153 | 0,8420 | 0,2287 | 0,3722 | 0,0725 |
| Rama | Ciencias de la Salud | 0,8190 | 0,8687 | 0,2287 | 0,3722 | 0,0725 |
| Rama | Ingeniería y Arquitectura | 0,7969 | 0,8130 | 0,2287 | 0,3722 | 0,0725 |

Observaciones de equidad:

- **Beca:** es la variable con mayor diferencia de igualdad de oportunidad
  (`eq_opp_diff` = 0,1644). El recall del grupo *con beca* (0,7293) es
  notablemente inferior al de *sin beca* (0,8937): el modelo detecta peor el
  abandono entre el estudiantado becado.
- **Sexo:** recall algo mayor en hombres (0,8246) que en mujeres (0,7789);
  `eq_opp_diff` = 0,0457 (la más baja entre las variables comparadas).
- **Origen:** recall menor para estudiantado extranjero (0,7500 frente a 0,8098).
- **Vía de acceso:** existen grupos con muy pocos casos (p. ej. «Deportistas de
  élite», «Minusválidos») con métricas degeneradas (F1 = 0); su `dp_diff` global
  de 0,6250 está muy condicionado por tamaños muestrales mínimos y **no debe
  interpretarse como sesgo robusto (verificar)**.

### Equidad interseccional (`fairness_interseccional.parquet`)

| Grupo | n | Recall | F1 | diff_recall |
|---|---|---|---|---|
| Mujer + Sin beca | 874 | 0,8740 | 0,8898 | 0,0692 |
| Mujer + Trabaja | 2.945 | 0,7929 | 0,8374 | -0,0119 |
| Mujer + Extranjero | 276 | 0,7349 | 0,7485 | -0,0698 |
| Hombre + Sin beca | 982 | 0,9071 | 0,9037 | 0,1023 |
| Hombre + Trabaja | 2.453 | 0,8385 | 0,8596 | 0,0338 |
| Trabaja + Sin beca | 1.666 | 0,8981 | 0,9079 | 0,0933 |
| Extranjero + Trabaja | 338 | 0,7626 | 0,8000 | -0,0422 |
| Extranjero + Sin beca | 104 | 0,7600 | 0,7600 | -0,0448 |

El recall más bajo se concentra en perfiles de **mujer extranjera** (0,7349) y
**extranjero con beca** (0,7600), coherente con las observaciones univariantes.

---

## 9. Sostenibilidad y eficiencia

Fuente: `metricas_modelo.json` y `sostenibilidad_metricas.parquet`.

| Métrica | Valor |
|---|---|
| Tiempo de predicción (test completo) | 71,74 ms |
| Tiempo por estudiante | 0,0109 ms |
| Throughput | 91.938 estudiantes/segundo |
| Tamaño del modelo | 932,67 KB |
| CO₂ por inferencia (test) | 0,000254 g |
| Ratio F1 / CO₂ | 3.276,59 |

Comparativa de sostenibilidad frente a otros modelos:

| Modelo | F1 | CO₂ (g) | F1/CO₂ | Ganador |
|---|---|---|---|---|
| LightGBM | 0,8334 | 0,000254 | 3.276,59 | Sí |
| Stacking | 0,8273 | 0,000469 | 1.762,10 | No |
| EBM | 0,8071 | 0,000145 | 5.571,91 | No |

LightGBM ofrece el mejor F1 con un coste computacional bajo; EBM es más eficiente
en CO₂ pero con menor F1.

---

## 10. Uso previsto

- **Uso previsto:** apoyo a la **detección temprana** de estudiantado en riesgo de
  abandono en la UJI, como herramienta de priorización para acciones de tutoría y
  orientación académica.
- **Usuarios previstos:** servicios institucionales de la UJI (planificación,
  tutoría/orientación) con conocimiento del contexto.
- **Modo de uso recomendado:** como **señal de apoyo**, siempre acompañada de las
  explicaciones individuales (SHAP/LIME) y bajo supervisión humana.

## 11. Usos NO recomendados

- **No** debe usarse para decisiones automáticas adversas (denegación de plaza,
  beca, recursos o servicios) sin intervención humana.
- **No** debe aplicarse fuera del contexto de la UJI ni a poblaciones, periodos o
  titulaciones distintos de los de entrenamiento sin revalidación.
- **No** debe interpretarse como predicción individual determinista: el modelo
  estima probabilidades, no certezas.
- **No** debe emplearse para clasificar o penalizar a grupos sensibles (sexo,
  origen, situación de beca, etc.) dadas las diferencias de equidad detectadas
  (sección 8).

---

## 12. Limitaciones conocidas

- **Dependencia de variables de primer curso:** el rendimiento cae de forma
  acusada si faltan `cred_superados_anio_1er`, `cred_repetidos` o `nota_1er_anio`
  (ver pruebas de *missing*, sección 5). El modelo es menos fiable antes de
  disponer de resultados del primer año.
- **Sensibilidad al ruido y a outliers:** la degradación es notable con niveles
  altos de perturbación (sección 5).
- **Equidad:** menor capacidad de detección (recall) en estudiantado con beca,
  extranjero y, en menor medida, mujeres (sección 8).
- **Grupos minoritarios:** algunas vías de acceso tienen muy pocos casos y sus
  métricas no son interpretables de forma robusta.
- **Ámbito temporal y geográfico:** entrenado con cohortes 2010 – 2020 de la UJI;
  su validez fuera de ese marco no está garantizada.
- **Definición de la variable objetivo:** documentada en la sección 2 a partir de
  `notebooks/fase3_features/f3_m05_target_export.ipynb`.

---

## 13. Procedencia de los datos de esta tarjeta

- `data/06_evaluacion/metricas_modelo.json` — métricas, datos de entrenamiento,
  robustez, calibración y sostenibilidad (campo
  `robustez_calibracion_sostenibilidad`).
- `results/fase6/fairness_metricas.parquet`,
  `results/fase6/fairness_interseccional.parquet` — análisis de equidad.
- `results/fase6/calibracion_metricas.parquet` — calibración.
- `results/fase6/sostenibilidad_metricas.parquet` — sostenibilidad.
- `results/fase6/stress_resultados.parquet` — pruebas de estrés.
- `results/fase6/shap_importancia_comparativa.parquet` — importancia de
  variables (SHAP).
- `notebooks/fase3_features/f3_m05_target_export.ipynb` — definición de la
  variable objetivo `abandono`.

*Fecha de generación de la tarjeta: 2026-06-17.*
