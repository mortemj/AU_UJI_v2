# 🎓 AU_UJI_v2 · Predicción de Abandono Universitario · UJI

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![LightGBM](https://img.shields.io/badge/Modelo-LightGBM-success?logo=leaflet)](https://lightgbm.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/App-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Estado](https://img.shields.io/badge/Estado-V2%20Sistema%20Din%C3%A1mico-brightgreen)](https://github.com/mortemj/AU_UJI_v2)
[![Licencia](https://img.shields.io/badge/Licencia-Acad%C3%A9mica-lightgrey)](#-licencia)

> **Trabajo Final de Máster (TFM)** — Universitat Oberta de Catalunya (UOC)
> **Datos:** Universitat Jaume I (UJI) · Período 2010–2020
> **Autora:** María José Morte · Tutor: Raúl Parada (UOC) · Supervisión institucional: Servicio de Planificación de la UJI

---

## 📌 Descripción

Sistema de **predicción temprana del abandono universitario** desarrollado a partir de datos académicos, demográficos y administrativos de la Universitat Jaume I (UJI), con el objetivo de identificar al estudiantado en riesgo y facilitar intervenciones institucionales eficaces.

El proyecto combina técnicas avanzadas de *machine learning* con análisis interpretativo (SHAP, LIME, DiCE), evaluación de equidad (*fairness*) y una aplicación web interactiva orientada a personal de gestión académica, profesorado y al propio estudiantado.

**Definición operativa de abandono aplicada:**

> Persona estudiante que no ha egresado, no ha completado créditos suficientes para considerarse egresada de hecho, y lleva 2 o más años sin actividad académica.

---

## 🆕 Versión V2 — Sistema Dinámico

Esta es la **versión 2** del proyecto, con mejoras sustanciales respecto a V1:

| Aspecto | V1 (legado) | V2 (actual) |
|---|---|---|
| Modelo ganador | Stacking (hardcodeado) | **LightGBM** (selección dinámica) |
| Fuente métricas | Variables fijas en código | `metricas_modelo.json` (fuente única de verdad) |
| Nº de features | 19 | **24** (+ 3 *missing flags* = 27 técnicas) |
| Cambio de ganador | Requiere reentrenar y editar código | Recalcula al regenerar el JSON |
| Evaluación de equidad | Parcial | Completa (sexo, vía acceso, beca, rama, origen) |
| Aplicación web | No disponible | Streamlit con 7 páginas |
| Validador de calidad de datos | No disponible | 5 niveles N1–N5 (1.060.292 filas validadas) |

> 🔄 **Filosofía V2:** *Reproducibilidad total y trazabilidad*. Todo modelo, métrica y resultado se regenera ejecutando los notebooks por orden, sin valores numéricos incrustados en código.

---

## 🌐 Recursos del proyecto

| Recurso | URL | Estado |
|---|---|---|
| 📂 **Repositorio V2** (este) | [github.com/mortemj/AU_UJI_v2](https://github.com/mortemj/AU_UJI_v2) | ✅ Activo |
| 🚀 **App Streamlit V2** | [tfm-abandono-dinamico.streamlit.app](https://tfm-abandono-dinamico.streamlit.app/) | ✅ Activo |
| 🌍 **GitHub Pages V2** | [mortemj.github.io/AU_UJI_v2](https://mortemj.github.io/AU_UJI_v2) | ✅ Activo |
| 📦 Repositorio V1 (legado) | [github.com/mortemj/AU_UJI](https://github.com/mortemj/AU_UJI) | 🟡 Archivado |
| 🚀 App Streamlit V1 (legado) | [tfm-abandono.streamlit.app](https://tfm-abandono.streamlit.app/) | 🟡 No dinámica |
| 🌍 GitHub Pages V1 (legado) | [mortemj.github.io/AU_UJI](https://mortemj.github.io/AU_UJI/) | 🟡 No actualizada |

---

## 🏆 Modelo y resultados

### Modelo final seleccionado

| Métrica | Valor | Observación |
|---|---|---|
| **Algoritmo** | LightGBM (`none`) | Familia: Gradient Boosting |
| **AUC-ROC** | 0.9564 | Test |
| **F1-score** | 0.8334 | Criterio de selección |
| **Precision** | 0.8641 | Test |
| **Recall** | 0.8048 | Criterio de desempate |
| **Accuracy** | 0.9059 | Test |
| **n_test** | 6.725 estudiantes | Tasa abandono = 29,25 % |

### Comparación con baseline AutoML

CatBoost AutoGluon BAG L2 (D_strict): AUC = 0.9365 · F1 = 0.797 · superado por el modelo final.

### Volumen de modelos evaluados

**69 modelos** entrenados en Fase 5 (23 algoritmos × estrategias `none` / `balanced` / `smote`) + **168 modelos AutoML** en 4 frameworks (AutoGluon, PyCaret, H2O, LazyPredict).

---

## 🗺️ Fases del proyecto

| Fase | Descripción | Estado |
|---|---|---|
| **F0** · Configuración | Estructura de proyecto, validador Excel 5 niveles (N1–N5), entorno reproducible | ✅ |
| **F1** · Ingesta y limpieza | Carga de 9 tablas fuente, auditoría, limpieza, trazabilidad (109.568 × 37) | ✅ |
| **F2** · EDA inicial | Análisis exploratorio univariante, bivariante y temporal con Plotly | ✅ |
| **F3** · Feature engineering | Dataset analítico por estudiante, definición del *target* `abandono` (33.621 × 25) | ✅ |
| **AutoML** | Baseline con 4 frameworks (AutoGluon, PyCaret, H2O, LazyPredict) — 168 modelos | ✅ |
| **F4** · EDA final | Distribuciones, anomalías, correlaciones, perfiles de riesgo | ✅ |
| **F5** · Modelado | 69 modelos, 6 familias, comparación cruzada, selección por F1+recall | ✅ |
| **F6** · Interpretabilidad y equidad | SHAP, LIME, DiCE, *fairness*, calibración, robustez, sostenibilidad | ✅ |
| **F7** · App Streamlit | 7 páginas: institucional, titulación, prospecto, en curso, equidad, leyenda | ✅ |

---

## 🗂️ Estructura del proyecto

```
AU_UJI_v2/
│
├── app/                    # Aplicación Streamlit (7 páginas)
│   ├── main.py             # Punto de entrada
│   ├── pages/              # p00_inicio … p06_leyenda
│   └── utils/              # loaders, ui_helpers, pronostico_shared
│
├── data/
│   ├── 00_raw/             # Datos originales UJI (no se publica)
│   ├── 01_interim/         # Datos intermedios (regenerables)
│   ├── 02_processed/       # df_alumno (109.568 × 37)
│   ├── 03_features/        # dataset_final_tfm (33.621 × 25)
│   ├── 04_eda/             # Métricas EDA exportadas
│   ├── 05_modelado/        # Modelos .pkl + pipeline preprocesamiento
│   └── 06_evaluacion/      # metricas_modelo.json (fuente única de verdad)
│
├── docs/html/              # Informes HTML por fase (visualización web)
├── notebooks/              # Notebooks Jupyter por fase (F0–F6 + AutoML)
├── results/fase6/          # SHAP, LIME, fairness, calibración, sostenibilidad
├── scripts/                # Utilidades de mantenimiento (compresión, diagnóstico)
├── src/
│   ├── config_proyecto.py  # Identidad y rutas
│   ├── config_entorno.py   # Detección entorno (local / Colab / Cloud)
│   ├── html/               # Generadores HTML (estado_proyecto, render…)
│   └── validacion/         # Validador Excel N1–N5 (TAREA C)
├── tests/                  # Tests automáticos pytest (42 tests TAREA C)
└── tribunal/               # Lanzadores app (Windows + macOS)
```

---

## 🛠️ Tecnologías

**Lenguaje y entorno:** Python 3.11 · Anaconda · Jupyter · Conda env `tfm_abandono`

**Machine Learning:** scikit-learn · LightGBM · XGBoost · CatBoost · InterpretML (EBM)

**Interpretabilidad y equidad:** SHAP · LIME · DiCE · Fairlearn · Shapash

**AutoML (baseline):** AutoGluon · PyCaret · H2O · LazyPredict

**Visualización:** Plotly · Matplotlib · Seaborn · D3.js (grafos)

**Aplicación web:** Streamlit · Pandas · joblib (compress=3)

**Sostenibilidad:** CodeCarbon (huella de carbono del entrenamiento)

**Calidad y reproducibilidad:** pytest · validador Excel propio (5 niveles N1–N5)

---

## 📊 Datos

- **Fuente:** Universitat Jaume I (UJI) — datos anonimizados bajo acuerdo de confidencialidad
- **Período:** cursos académicos 2010–2020
- **Universo:** ~30.872 estudiantes únicos · 40 titulaciones de grado
- **Tablas fuente:** 9 tablas Excel · ~37 columnas originales
- **Dataset analítico:** 33.621 registros · 24 *features* + *target* `abandono`

> ⚠️ **Aviso de privacidad:** los datos contienen información personal y son de uso restringido. **No se incluyen en el repositorio**. Pueden regenerarse las fases intermedias ejecutando los notebooks 1–3 con los datos originales.

---

## 🚀 Reproducir el proyecto desde cero

Esta sección está pensada para que **cualquier persona** (incluso sin experiencia en Python) pueda poner en marcha el proyecto en su ordenador. Sigue los pasos en orden.

### 📥 Requisitos previos

Antes de empezar, debes tener instalado:

1. **Git** — para descargar el código del proyecto
   👉 [Descargar Git](https://git-scm.com/downloads)

2. **Anaconda** o **Miniconda** — para gestionar el entorno Python
   👉 [Descargar Anaconda](https://www.anaconda.com/download) (recomendado para no técnicos)

> 💡 **Si nunca has usado estas herramientas:** instálalas con las opciones por defecto. Tras instalar Anaconda, en Windows tendrás un programa llamado **"Anaconda Prompt"**, en macOS/Linux usarás el **Terminal**.

### 📋 Pasos para reproducir (copiar y pegar uno a uno)

Abre **Anaconda Prompt** (Windows) o **Terminal** (macOS/Linux) y ejecuta los siguientes comandos uno a uno (espera a que cada uno termine antes de lanzar el siguiente):

```bash
# 1. Descargar el proyecto desde GitHub
git clone https://github.com/mortemj/AU_UJI_v2.git

# 2. Entrar en la carpeta del proyecto
cd AU_UJI_v2

# 3. Crear el entorno virtual (solo la primera vez, tarda ~1 minuto)
conda create -n tfm_abandono python=3.11 -y

# 4. Activar el entorno
conda activate tfm_abandono

# 5. Instalar todas las dependencias (tarda ~5-10 minutos)
pip install -r requirements_proyecto.txt

# 6. Arrancar la aplicación web (Streamlit)
streamlit run app/main.py
```

Si todo va bien, se abrirá automáticamente una pestaña en tu navegador con la aplicación. Si no se abre sola, copia la URL que aparece en la terminal (algo como `http://localhost:8501`) y pégala en el navegador.

> ✅ **Reproducibilidad verificada:** estos comandos se han probado en una máquina con Windows 11 + Python 3.11 + entorno conda limpio. Resultado: instalación correcta de las 170+ dependencias sin errores.

### 📦 Archivos de dependencias (requirements)

El proyecto incluye varios archivos `requirements*.txt`. Cada uno cubre un caso de uso:

| Archivo | ¿Cuándo usarlo? |
|---|---|
| **`requirements_proyecto.txt`** | 🎯 **Para reproducir el TFM completo** (todas las fases + app). Es el archivo recomendado para el tribunal. |
| `requirements.txt` | Solo si vas a desplegar la app Streamlit en producción (Streamlit Cloud). Dependencias mínimas. |
| `requirements_fase1.txt` | Solo si quieres reproducir la **Fase 1** (limpieza y EDA) de forma aislada. |
| `requirements_fase2.txt` | Solo si quieres reproducir la **Fase 2** (EDA inicial) de forma aislada. |
| `requirements_fase3.txt` | Solo si quieres reproducir la **Fase 3** (feature engineering) de forma aislada. |
| `requirements_fase4.txt` | Solo si quieres reproducir la **Fase 4** (EDA final) de forma aislada. |
| `requirements_fase5.txt` | Solo si quieres reproducir la **Fase 5** (modelado, 69 modelos) de forma aislada. |
| `requirements_fase6.txt` | Solo si quieres reproducir la **Fase 6** (interpretabilidad + fairness) de forma aislada. |

> 💡 **Recomendación:** usar `requirements_proyecto.txt` salvo que sepas exactamente lo que estás haciendo.

### 🧪 Ejecutar los tests automáticos

```bash
pytest tests/ -v
```

Resultado esperado: **42 passed**.

### 🔁 Regenerar las fases (orden recomendado)

Si quieres regenerar todos los resultados desde cero, ejecuta los notebooks orquestadores de cada fase **en este orden**:

1. `notebooks/fase0_configuracion/orquestador_maestro.ipynb`
2. `notebooks/fase1_transformacion/f1_m00_ejecucion.ipynb`
3. `notebooks/fase2_eda/f2_m00_ejecucion.ipynb`
4. `notebooks/fase3_features/f3_m00_ejecucion.ipynb`
5. `notebooks/fase4_eda/f4_m00_ejecucion.ipynb`
6. `notebooks/fase5_modelado/f5_m00_ejecucion.ipynb`
7. `notebooks/fase6_evaluacion/f6_m00_ejecucion.ipynb`

> ⚠️ **Importante:** las fases 1–3 requieren los datos originales de la UJI (no incluidos en el repo). Las fases 4–6 pueden ejecutarse con los datos derivados que sí están en el repo.

### 🖱️ Atajo: lanzadores automáticos

Si prefieres no usar la terminal, dentro de la carpeta del proyecto encontrarás:

- **Windows:** doble clic en `arrancar_proyecto.bat`
- **macOS/Linux:** ejecutar `./arrancar_proyecto.sh` desde Terminal

Ambos activan el entorno y lanzan Jupyter Notebook automáticamente.

---

## 👩‍💻 Autora

**María José Morte**
Máster Universitario en Ciencia de Datos · Universitat Oberta de Catalunya (UOC)

📧 [mjmorteruiz@uoc.edu](mailto:mjmorteruiz@uoc.edu) · [morte@uji.es](mailto:morte@uji.es)
🐙 [github.com/mortemj](https://github.com/mortemj)

**Tutor académico:** Raúl Parada · [rparada@uoc.edu](mailto:rparada@uoc.edu)
**Supervisión institucional:** Servicio de Planificación de la UJI

---

## 📄 Licencia

Proyecto académico desarrollado en el marco del TFM de la UOC (curso 2025–2026).
Datos proporcionados por la Universitat Jaume I bajo acuerdo de confidencialidad.
Uso restringido a fines de investigación y formación académica.

---

<sub>Última actualización del README: 18/05/2026 · Versión 2 (sistema dinámico)</sub>
