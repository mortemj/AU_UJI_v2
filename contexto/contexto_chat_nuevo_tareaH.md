# 📋 Contexto chat nuevo — TAREA H: Git push V2

**Proyecto:** AU_UJI Dinámico (V2) — TFM Pronóstico de Abandono UJI
**Autora:** María José Morte · `mjmorteruiz@uoc.edu` · `morte@uji.es`
**Repo V2:** https://github.com/mortemj/AU_UJI_v2
**App V2:** https://tfm-abandono-dinamico.streamlit.app/ (despliegue pendiente — TAREA J)
**Pages V2:** https://mortemj.github.io/AU_UJI_v2 (creación pendiente — TAREA I)
**Local:** `C:\FF\AU_UJI_v2\`
**Entorno conda:** `tfm_abandono` (Python 3.13.5 en Windows)

---

## 🎯 Tarea pendiente: TAREA H — Git push V2

### **Objetivo**
Subir al repositorio `https://github.com/mortemj/AU_UJI_v2` **todos los cambios pendientes** (~250 ficheros) que se han acumulado desde el último commit. Es la **primera vez que se sube V2 completo** al repo nuevo.

### **Por qué es crítico**
- El repo está MUY desactualizado: dice "Stacking 0.9308" y "F6 en progreso" → información FALSA
- El tribunal/Raúl Parada pueden entrar en cualquier momento
- Hay trabajo de meses que NO está protegido en GitHub
- Sin push, un fallo de disco local = pérdida total

### **Por qué es PELIGROSO si se hace mal**
- 250 ficheros modificados/borrados/nuevos en un solo `git status`
- Hacer `git add .` + `git commit` a ciegas = mezclar todo en un commit gigante imposible de auditar
- Algunos ficheros NO deben subirse (backups personales, `_old`, scratch)
- Si se rompe algo, el rollback es complejo

---

## 🚨 ESTADO REAL del repo (verificado 04/05/2026)

### Lo que hay AHORA en GitHub (`AU_UJI_v2`)

```
- 25 commits (último hace tiempo)
- Carpetas raíz: app/, data/, docs/, notebooks/, project/, results/, src/, tests/, tribunal/, txt/
- Scripts raíz: comprimir_TODOS_modelos.py, comprimir_modelo_app.bat/.py, trazabilidad.py
- README dice: "Stacking 0.9308" · "19 features" · "F6 🔄 En progreso" · "Autora: María José Morte Ruiz"
- Pages enlazada: https://mortemj.github.io/AU_UJI/ (la de V1, no V2)
- NO menciona: app Streamlit, validador Excel, sistema dinámico
```

### Lo que tenemos en LOCAL pendiente de subir (~250 ficheros)

**Categorías principales:**

1. ✅ **Cambios sistema dinámico** (todos los HTMLs, notebooks, modelos `.pkl`, `metricas_modelo.json`)
2. ✅ **TAREA C** (validador Excel): `src/validacion/`, `tests/test_validador.py`, `notebooks/fase0_configuracion/f0_validar_excel.ipynb`, `docs/html/fase0/`
3. ✅ **TAREA B** (sistema HTML dinámico): `src/html/estado_proyecto.py`, `src/html/generar_resumen_proyecto.py`, `src/html/wilcoxon_block.py`
4. ✅ **TAREA D** (limpieza raíz hoy): `.gitignore` actualizado, `scripts/` nueva, borrados scratch/cachés
5. ✅ **README.md** (regenerado en TAREA D+, datos correctos V2)
6. ❓ **Wilcoxon**: `notebooks/fase5_modelado/f5_wilcoxon_top3.ipynb`, `f5_wilcoxon_xgb_vs_lgb.ipynb`
7. ❓ **F6 nuevos**: `notebooks/fase6_evaluacion/f6_m05_robustez_calibracion.ipynb`, `f6_m06_informe_final.ipynb`
8. ⚠️ **Ficheros `_old` y scratch**: hay decenas, NO deben subirse (revisar caso por caso)

---

## 🚦 Plan propuesto TAREA H (a refinar al arrancar)

### **Fase 0 — Verificación previa**
- `git status` para ver lista completa actual
- Verificar que rama es `master`
- Verificar que `git remote -v` apunta a `mortemj/AU_UJI_v2.git`
- Hacer `git stash` si hay algo sin commitear que NO queremos perder

### **Fase 1 — Limpieza pre-commit**
- Identificar y borrar/ignorar ficheros que NO deben ir al repo:
  - `- copia.gitignore` (typo + backup tuyo)
  - `.gitignore_old`
  - `notebooks/Untitled.ipynb`, `notebooks/prueba1.ipynb`
  - Todos los `*_old.ipynb`, `*OLD*`, `*old/` (carpetas)
  - `notebooks/fase0_configuracion/old/` (carpeta entera)
  - `docs/html/static/style_OLD.css`
  - `docs/html/fase_automl/m06_comparativa_olf.html` (typo)
  - `src/html/generar_resumen_proyecto_old.py`
- **DECISIONES caso por caso (preguntar a María José):**
  - `notebooks/verificar_df_alumno.ipynb` → ¿útil o scratch?
  - `notebooks/wilcoxon_real.py` → ¿útil o scratch?
  - `notebooks/fase6_evaluacion/modelos.ipynb` → ¿útil o scratch?
  - `notebooks/fase6_evaluacion/shap_importancia_comparativa.ipynb` → ¿útil o scratch?
  - `notebooks/fase6_evaluacion/verificacion_pre_m01a.ipynb` → ¿útil o scratch?
  - `notebooks/fase0_configuracion/00_configuracion_proyecto_old.ipynb` → confirmar borrado
  - `data/06_interpretacion/` → verificar contenido

### **Fase 2 — Mejorar `.gitignore`**
Añadir patrones que cubran todos los `_old` futuros automáticamente:

```gitignore
# Versiones legacy de notebooks/scripts
*_old.ipynb
*_old.py
*_old.html
*_old.css
*_OLD*
*OLD*

# Carpetas legacy
**/old/

# Backups personales (ampliación del bloque actual)
- copia.*
.gitignore_old

# Scratch
notebooks/Untitled*.ipynb
notebooks/prueba*.ipynb
```

Backup `.gitignore` antes (`.gitignore.bak.YYYYMMDD`).

### **Fase 3 — Commits por bloques temáticos**
NO hacer un único commit gigante. Dividir en bloques lógicos:

| # | Bloque | Ficheros aprox |
|---|---|---|
| 1 | `.gitignore` actualizado + README.md V2 | 2 |
| 2 | TAREA D limpieza raíz: borrar `comprimir_*` + `trazabilidad.py` (movidos a `scripts/`) | ~10 |
| 3 | TAREA D + TAREA C: añadir `scripts/` + `src/validacion/` + `tests/test_validador.py` + `docs/html/fase0/` | ~10 |
| 4 | TAREA B: sistema HTML dinámico (`src/html/`) | ~5 |
| 5 | Sistema dinámico modelo ganador: `metricas_modelo.json`, `meta_test_app.parquet`, modelos `.pkl` | ~60 |
| 6 | Notebooks F1-F4 actualizados | ~50 |
| 7 | Notebooks F5 + Wilcoxon | ~20 |
| 8 | Notebooks F6 + nuevos (`f6_m05_robustez`, `f6_m06_informe`) | ~30 |
| 9 | App Streamlit V2 (`app/`) | ~12 |
| 10 | HTMLs `docs/` actualizados | ~150 |
| 11 | Resultados `results/fase6/` SHAP/LIME/fairness | ~50 |
| 12 | `tribunal/lanzar_app_windows.bat` corregido (sin "Ruiz", 2026) | 1 |

Cada commit con mensaje descriptivo en español:
```
git commit -m "TAREA D: limpieza raíz V2 + .gitignore actualizado"
git commit -m "TAREA C: validador Excel 5 niveles N1-N5"
git commit -m "Sistema dinámico: metricas_modelo.json como fuente única"
...
```

### **Fase 4 — Push y verificación**
- `git push origin master`
- Abrir `https://github.com/mortemj/AU_UJI_v2` en navegador
- Verificar que README muestra V2 correcto
- Verificar que carpetas legacy (`project/`, `txt/`) ya NO aparecen
- Verificar que `scripts/` aparece como nueva
- Hacer captura del estado para registro histórico

---

## ✅ Estado del proyecto al 04/05/2026 (tras TAREA D)

| Fase | Estado | Señal en disco |
|---|---|---|
| F0 | ✅ Completada **+ validador profesional N1-N5 (TAREA C)** | `docs/html/fase0/validacion_excel.html` |
| F1 | ✅ Completada | `data/02_processed/df_alumno.parquet` (109.568 × 37) |
| F2 | ✅ Completada | `docs/html/fase2/m07_conclusiones.html` |
| F3 | ✅ Completada | `data/03_features/dataset_final_tfm.parquet` (33.621 × 25) |
| AutoML | ✅ Completada | 168 modelos en 4 frameworks |
| F4 | ✅ Completada | `docs/html/fase4/m09_conclusiones_eda.html` |
| F5 | ✅ Completada | `data/05_modelado/results/resultados_maestro.parquet` (69 modelos) |
| F6 | ✅ Completada | `data/06_evaluacion/metricas_modelo.json` (LightGBM ganador) |
| F7 (App) | ⚠️ Local OK · despliegue pendiente | `app/main.py` |

### **Modelo ganador (de `metricas_modelo.json`)**
- LightGBM (estrategia `none`) · Familia: Gradient Boosting
- AUC: 0.9564 · F1: 0.8334 · n_test: 6.725
- Features: 24 (+ 3 _missing = 27 técnicas) · Tasa abandono: 29,25 % · Período: 2010-2020

---

## 📦 Lo que YA está hecho en TAREA D (NO duplicar)

### **Limpieza física raíz (33 → 16 ítems)**
- ✅ 8 scripts movidos a `scripts/`
- ✅ `test_validador.py` movido a `tests/`
- ✅ 3 notebooks scratch borrados (`Untitled*`, `COMPROBA_NO USO`)
- ✅ 4 cachés borradas (`.ipynb_checkpoints`, `.pytest_cache`, `anaconda_projects`, `catboost_info`)
- ✅ 4 carpetas obsoletas borradas (`project/`, `logs/`, `txt/`, `notes/`)
- ✅ 10 ficheros `.bak.20260429.*` borrados de `app/`
- ✅ `verificacion_coherencia.json` y `todo.txt` borrados

### **`.gitignore` actualizado**
- ✅ Cabecera: "María José Morte" (sin "Ruiz") + fecha 04/05/2026
- ✅ Añadido: `anaconda_projects/`, `tree_proyexto.txt`, `*.bak.*`
- ✅ Eliminada regla obsoleta `comprimir_modelo_app.bat`
- ✅ Backup: `.gitignore.bak.20260504`

### **README.md V2 regenerado** (en TAREA D+)
- ✅ Estilo mixto profesional (badges + tablas + texto académico)
- ✅ Datos reales: LightGBM 0.9564, 24 features, F6 ✅, sin "Ruiz"
- ✅ Tabla "Versiones" V1 vs V2 con todas las URLs (con estados)
- ✅ Mención app Streamlit V2 + validador Excel + 42 tests
- ✅ Solo Autora + Tutor (sin tribunal, sin reclutadores, sin Susana)

### **Trazabilidad creada**
- `zzz_contexto_chats/tareaD_completada.md` (registro histórico)
- `zzz_contexto_chats/contexto_chat_nuevo_tareaH.md` ← este fichero

---

## 🛠️ Sistema dinámico ya en marcha (desde TAREA B)

`src/html/estado_proyecto.py` es la **fuente única de verdad** para detección de fases:

```python
from src.html.estado_proyecto import detectar_estado_fases
estados = detectar_estado_fases()  # devuelve lista de 9 fases con su estado
```

`data/06_evaluacion/metricas_modelo.json` es la **fuente única de verdad** del modelo ganador.

→ **NO duplicar lógica**. Si TAREA H necesita saber qué fases están hechas o qué modelo gana, usar siempre estas fuentes.

---

## 📋 Estándares ABSOLUTOS del proyecto (NO negociables)

- **ROOT robusto**: subir niveles hasta encontrar `src/`, nunca hardcodear path
- **`sys.path.insert(0, str(ROOT))`** — nunca `str(ROOT/'src')`
- **Sin hardcodes** de valores numéricos en `src/` (paths van a `config_entorno.py`)
- **Todo en español** (variables, mensajes, comentarios visibles al usuario)
- **Nunca "datos crudos/brutos/raw"** → siempre **"datos originales"**
- **Comentarios 20-50 % por celda** explicando el por qué
- **Verificar sintaxis con `ast.parse()`** tras cada edición
- **Una modificación a la vez** — leer fichero existente antes de modificar
- **No inventar nombres de columnas** — pedir o derivar del código existente
- **Backup `.bak` antes de tocar ficheros críticos**
- **Una pregunta a la vez** con opciones concretas (no avalanchas)
- **Nunca asumir** — siempre preguntar antes de inventar
- **NUNCA tocar:** `app/`, fases F1-F7, `src/config_entorno.py`, modelos `.pkl`, datasets `.parquet`

---

## 🌐 Identidad del proyecto V2

```python
# src/config_proyecto.py
AUTORA            = "María José Morte"  # SIN "Ruiz"
EMAIL_UOC         = "mjmorteruiz@uoc.edu"
EMAIL_UJI         = "morte@uji.es"
GITHUB_REPO       = "https://github.com/mortemj/AU_UJI_v2"
URL_APP_STREAMLIT = "https://tfm-abandono-dinamico.streamlit.app/"
```

**V1 (versión anterior estable, NO tocar):**
- Repo: https://github.com/mortemj/AU_UJI
- App: https://tfm-abandono.streamlit.app
- Pages: https://mortemj.github.io/AU_UJI/

---

## 🎯 Pendientes futuros (NO en este chat H)

| Tarea | Descripción |
|---|---|
| **TAREA E** | `requirements.txt` consolidado raíz + 4 obsoletos a mover/eliminar |
| **TAREA G** | Limpieza profunda dentro de `app/` (revisar contenido tras `.bak` ya borrados) |
| **TAREA H+** | Crear `scripts/generar_readme.py` que regenere `README.md` desde `metricas_modelo.json` (README dinámico) |
| **TAREA I** | Crear GitHub Pages V2 (`mortemj.github.io/AU_UJI_v2`) con colores y diseño propios |
| **TAREA J** | Despliegue app V2 en Streamlit Cloud (`tfm-abandono-dinamico.streamlit.app`) |
| **TAREA F** | Revisión final rúbrica profesor + UOC |

---

## 📝 Cómo arrancar el chat H

Pegar este contexto en el primer mensaje y decir:

> "Tengo este contexto del TFM. Quiero hacer **TAREA H — Git push V2**. Lee el contexto, hazme preguntas si te falta algo, y propón un plan paso a paso. Recuerda mis premisas: **pregunta antes de hacer**, **una modificación a la vez**, **una pregunta a la vez (no avalanchas)**, **NUNCA borres nada sin mi confirmación expresa**, y **JAMÁS hagas `git add .` + `git commit -m` sin auditar antes**. Vamos por bloques temáticos, despacio, con backup mental antes de cada paso. NUNCA hacer push si hay dudas."

---

## 🆘 Cosas que el chat nuevo te pedirá probablemente

Para arrancar TAREA H te pedirá:

1. **`git status` actualizado**:
   ```cmd
   cd C:\FF\AU_UJI_v2
   git status > git_status_tareaH.txt
   ```
   (pegar el contenido del fichero, o ejecutar y copiar la salida)

2. **`git remote -v`** para confirmar que apunta a `AU_UJI_v2`

3. **`git log --oneline -10`** para ver últimos commits del repo

4. **Tu visto bueno** caso por caso para ficheros `❓` listados en Fase 1

5. **Confirmación explícita** antes de cada `git add`, `git commit` y `git push`

---

## ✅ TAREA D completada (resumen rápido)

Ver `tareaD_completada.md` para detalle completo. Resumen:

- ✅ Raíz pasó de 33 → 16 ítems (51 % limpieza)
- ✅ `.gitignore` actualizado y verificado (5 reglas críticas presentes)
- ✅ `README.md` V2 regenerado con datos reales
- ✅ 42 tests siguen pasando · imports funcionan
- ✅ Trazabilidad documentada en `zzz_contexto_chats/`

**La limpieza NO rompió nada. Todo listo para el chat H.**

---

## ⚠️ Aviso final crítico para el chat H

> 250 ficheros pendientes. La forma RÁPIDA de hacer Git push es la forma de PERDER trabajo. Vamos despacio, por bloques temáticos, con commits descriptivos. **Si hay dudas → preguntar. Si hay error → parar. Si todo va bien → seguir despacio.**

<sub>📅 Documento generado el 04/05/2026 · Para arrancar TAREA H · TFM AU_UJI_v2</sub>
