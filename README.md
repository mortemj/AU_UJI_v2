# 🎓 Pronóstico del Éxito y del Abandono en la Universitat Jaume I

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?logo=jupyter)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-ML-yellowgreen?logo=scikit-learn)
![LightGBM](https://img.shields.io/badge/LightGBM-Modelo%20ganador-025698)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-Listo%20para%20defensa-success)

> Trabajo Final de Máster (TFM) — Máster en Ciencia de Datos, Universitat Oberta de Catalunya (UOC)
> Datos: Universitat Jaume I (UJI) · Período 2010–2020 · Área 5 · Data Science in Social Systems

---

## 📌 Descripción

Sistema de **predicción temprana del abandono universitario** a partir de datos académicos,
demográficos y administrativos que la propia universidad ya recoge. El objetivo es identificar
al alumnado en riesgo de abandono **antes de que se produzca**, para facilitar intervenciones
institucionales a tiempo.

La aportación central de esta versión (V2) es la **selección dinámica del modelo**: el ganador
no se elige a ojo, sino mediante un criterio jerárquico fijado *antes* de ver resultados
(primero F1, desempate por recall, y validación de que supera el AUC del modelo de referencia),
recalculable sin reescribir código.

**Definición de abandono aplicada:**

> Estudiante que no ha egresado, que no ha completado créditos suficientes para considerarse
> egresado de hecho, y que lleva 2 o más años sin actividad académica.

---

## 🏆 Modelo ganador

| Métrica | Valor |
| --- | --- |
| **Modelo** | **LightGBM** (`LightGBM__none.pkl`) |
| **AUC** | **0,9564** |
| **F1** | **0,8334** |
| **Precisión** | **0,8641** |
| **Recall** | **0,8048** |
| Tamaño del modelo serializado | 932 KB |
| Tiempo de inferencia (lote de test) | 92,3 ms |

Métricas reportadas sobre el conjunto de **test** reservado. La fuente única de verdad de las
métricas es `data/06_evaluacion/metricas_modelo.json`; la app y los informes leen de ahí, sin
valores escritos a mano.

**Matriz de confusión (test):**

| | Predicho: NO abandono | Predicho: SÍ abandono |
| --- | --- | --- |
| **Real: NO abandono** | 4.401 | 246 |
| **Real: SÍ abandono** | 375 | 1.574 |

> **Coste asimétrico (FN > FP).** No detectar a quien abandona cuesta más que dar una falsa
> alarma. Por eso la selección optimiza F1 con desempate por recall, no el acierto global.

---

## 🌐 Demo en vivo

👉 **[Aplicación interactiva (Streamlit)](https://tfm-abandono-dinamico.streamlit.app/)**

La aplicación permite explorar el riesgo estimado por perfil de estudiante, por titulación y por
rama, con ajuste por titulación en espacio *logit*.

---

## 📊 Datos

- **Fuente:** Servicio de Planificación de la Universitat Jaume I (UJI) — datos originales, anonimizados.
- **Período:** 2010–2020 (11 cursos académicos consecutivos).
- **Universo:** 109.568 registros académicos · 30.872 estudiantes únicos · 40 titulaciones de grado (5 ramas).
- **Tasa global de abandono:** 29,25 % (con fuerte variación entre titulaciones: del 5 % al 50 %).
- **Dataset final de modelado:** 33.621 registros · 24 variables + variable objetivo `abandono`.

> ⚠️ Los datos son de carácter académico y uso restringido bajo acuerdo de confidencialidad.
> No se incluyen en el repositorio.

---

## 🔬 Fases del proyecto

| Fase | Descripción | Estado |
| --- | --- | --- |
| **F1** · Datos | Ingesta de las tablas originales de la UJI, auditoría de calidad, limpieza y trazabilidad | ✅ Completada |
| **F2** · EDA | Análisis exploratorio univariante y bivariante | ✅ Completada |
| **F3** · Features | Construcción del dataset analítico por estudiante (24 variables) y de la variable objetivo `abandono` | ✅ Completada |
| **F4** · AutoML (cribado) | Cribado con 83 configuraciones en 4 frameworks de AutoML | ✅ Completada |
| **F5** · Modelado clásico | 69 configuraciones (23 algoritmos × 3 estrategias de balanceo) y selección dinámica del modelo | ✅ Completada |
| **F6** · Evaluación e interpretabilidad | SHAP, LIME y DiCE; análisis de equidad por subgrupos; robustez temporal; sostenibilidad | ✅ Completada |
| **F7** · Aplicación | Despliegue de la app interactiva en Streamlit | ✅ Completada |

---

## 🧠 Variables más influyentes (SHAP)

Las cinco variables de mayor importancia global en el modelo ganador:

1. `n_anios_trabajando` — años trabajando durante los estudios
2. `n_anios_beca` — años con beca
3. `cred_superados_anio_1er` — créditos superados en el primer año
4. `nota_1er_anio` — nota media del primer año
5. `n_anios_sin_notas` — años sin calificaciones registradas

---

## 🗂️ Estructura del repositorio

```
AU_UJI_v2/
├── app/              # Aplicación Streamlit (V2, selección dinámica)
├── data/             # Datos por fase (03_features, 05_modelado, 06_evaluacion, …)
├── docs/             # Informes HTML por fase
├── notebooks/        # Jupyter Notebooks organizados por fase
├── results/          # Resultados intermedios y figuras
├── src/              # Módulos Python reutilizables
├── tests/            # Pruebas
├── tribunal/         # Material de defensa
└── README.md
```

---

## 🛠️ Tecnologías

- **Lenguaje y entorno:** Python 3.11 · Anaconda (`conda`) · Jupyter Notebook
- **Machine Learning:** scikit-learn · LightGBM · XGBoost · InterpretML (EBM)
- **AutoML:** cribado con 4 frameworks
- **Interpretabilidad:** SHAP · LIME · DiCE · Fairlearn
- **Visualización:** Plotly · Matplotlib · Seaborn
- **App e infraestructura:** Streamlit · GitHub · GitHub Pages

---

## 👩‍💻 Autora

**María José Morte Ruiz**
Máster en Ciencia de Datos — Universitat Oberta de Catalunya (UOC)
📧 [mjmorteruiz@uoc.edu](mailto:mjmorteruiz@uoc.edu)

Tutor: Raúl Parada Medina · [rparada@uoc.edu](mailto:rparada@uoc.edu)

---

## 📄 Licencia

Proyecto académico. Datos proporcionados por la Universitat Jaume I bajo acuerdo de
confidencialidad. Uso restringido a fines de investigación y formación.
