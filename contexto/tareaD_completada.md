# ✅ TAREA D — Limpieza raíz V2 · COMPLETADA

**Fecha:** 04/05/2026
**Proyecto:** AU_UJI Dinámico (V2) — TFM Pronóstico de Abandono UJI
**Autora:** María José Morte · `mjmorteruiz@uoc.edu` · `morte@uji.es`
**Repo V2:** https://github.com/mortemj/AU_UJI_v2
**Local:** `C:\FF\AU_UJI_v2\`

---

## 🎯 Objetivo cumplido

Limpiar la raíz de `C:\FF\AU_UJI_v2\` que tenía scripts sueltos, notebooks scratch, ficheros temporales, cachés y carpetas obsoletas que ensuciaban el repositorio y dificultaban la lectura por parte del tribunal y otros revisores.

**Resultado:** raíz pasó de **33 ítems → 16 ítems** (limpieza del 51 %).

---

## 📋 Acciones realizadas

### 🟢 Movidos a `scripts/` (utilidades de mantenimiento)

| Fichero original (raíz) | Destino |
|---|---|
| `comprimir_modelo_app.bat` | `scripts/` |
| `comprimir_modelo_app.py` | `scripts/` |
| `comprimir_TODOS_modelos.py` | `scripts/` |
| `diagnostico_modelo.py` | `scripts/` |
| `ejecutar_streamlit.bat` | `scripts/` |
| `trazabilidad.py` | `scripts/` |
| `verificar_coherencia.py` | `scripts/` |
| `descubrir_columnas.py` | `scripts/` |

### 🟢 Movido a `tests/` (test pytest legítimo)

| Fichero | Destino |
|---|---|
| `test_validador.py` (raíz) | `tests/` |

### 🔴 Borrados — Notebooks scratch

| Fichero | Motivo |
|---|---|
| `Untitled.ipynb` | Scratch sin nombre |
| `Untitled1.ipynb` | Scratch sin nombre |
| `COMPROBA_STATIC_NO USO.ipynb` | El nombre lo declara explícitamente |

### 🔴 Borrados — Ficheros temporales raíz

| Fichero | Motivo |
|---|---|
| `verificacion_coherencia.json` | Output temporal |
| `todo.txt` | Lista personal de tareas |

### 🔴 Borradas — Cachés regenerables

| Carpeta | Motivo |
|---|---|
| `.ipynb_checkpoints/` | Auto-guardado Jupyter (regenerable) |
| `.pytest_cache/` | Caché pytest (regenerable) |
| `anaconda_projects/` | Caché Anaconda Navigator (regenerable) |
| `catboost_info/` | Logs internos CatBoost (regenerable) |

### 🔴 Borradas — Carpetas obsoletas V1

| Carpeta | Contenido | Motivo |
|---|---|---|
| `project/` | `TFM-Predccion.ipynb` | Notebook README V1 obsoleto (rutas `C:\Users\mjmor\AU_UJI`, estructura `src/config/` que ya no existe) |
| `logs/` | `tfm_abandono.log` (3.313 líneas) | Log obsoleto V1 (rutas `OneDrive\2.- AU_UJI`) |
| `txt/` | 7 ficheros de inventarios de kernels y librerías | Diagnósticos obsoletos |
| `notes/` | (vacía) | Sin uso |

### 🔴 Borrados — Backups en `app/` (V2 paso 1 → paso N)

10 ficheros `.bak.20260429.*` con sufijos descriptivos (`con_dupkey_bug`, `paso1`, `paso2_buggy`, `paso3prev`, `paso4prev`, `previo_aviso`, `fix_st_image`):

- `app/config_app.py.bak.20260429`
- `app/main.py.bak.20260429.fix_st_image`
- `app/pages/p00_inicio.py.bak.20260429`
- `app/utils/loaders.py.bak.20260429`
- `app/utils/pronostico_shared.py.bak.20260429.con_dupkey_bug`
- `app/utils/pronostico_shared.py.bak.20260429.paso1`
- `app/utils/pronostico_shared.py.bak.20260429.paso2_buggy`
- `app/utils/pronostico_shared.py.bak.20260429.paso3prev`
- `app/utils/pronostico_shared.py.bak.20260429.paso4prev`
- `app/utils/pronostico_shared.py.bak.20260429.previo_aviso`

---

## 📝 `.gitignore` actualizado

**Backup creado antes:** `.gitignore.bak.20260504`

### Cambios aplicados

1. **Cabecera actualizada:** "María José Morte" (sin "Ruiz") + fecha 04/05/2026
2. **Bloque añadido:** `anaconda_projects/` (nunca debe ir al repo)
3. **Bloque añadido:** `tree_proyexto.txt` (output local del comando `dir /S /B`)
4. **Patrón añadido:** `*.bak.*` (cubre backups con sufijo tipo `.bak.20260429.fix_st_image`)
5. **Bloque eliminado:** regla obsoleta para `comprimir_modelo_app.bat` en raíz (ya está en `scripts/`)

**Total líneas:** 168 → 163 (más limpio y más completo).

---

## 📊 Estado final raíz

```
C:\FF\AU_UJI_v2\
├── .gitignore                    ✅ Actualizado
├── README.md                     ✅ (actualizado en TAREA D+ — cierre)
├── requirements_fase1.txt        🟡 (TAREA E)
├── requirements_fase2.txt        🟡 (TAREA E)
├── requirements_fase3.txt        🟡 (TAREA E)
├── requirements_proyecto.txt     🟡 (TAREA E)
│
├── app/          ✅ Aplicación Streamlit
├── data/         ✅ Datasets
├── docs/         ✅ HTMLs y documentación
├── notebooks/    ✅ Notebooks de fases
├── results/      ✅ Outputs F6
├── scripts/      ✅ NUEVO — scripts de mantenimiento
├── src/          ✅ Código fuente
├── tests/        ✅ Tests pytest
└── tribunal/     ✅ Lanzadores app
```

---

## ✅ Verificaciones post-limpieza

| Verificación | Comando | Resultado |
|---|---|---|
| Tests pasan | `pytest tests/ -v` | **42 passed** ✅ |
| Imports OK | `python -c "from src.validacion import CONTRATO_EXCEL"` | **OK · 9 hojas** ✅ |
| `.gitignore` bien | `findstr "anaconda_projects tree_proyexto bak"` | 5 reglas presentes ✅ |

**Conclusión: la limpieza NO rompió nada del proyecto funcional.**

---

## 🚦 Lo que NO se hizo en esta tarea (intencionadamente)

| No hecho | Motivo | A qué tarea pertenece |
|---|---|---|
| Consolidar `requirements_*.txt` | Tarea delicada con riesgo de romper entorno | TAREA E |
| Limpieza profunda dentro de `app/` (más allá de los `.bak`) | Regla absoluta: NUNCA tocar `app/` sin foco específico | Futuro chat dedicado |
| `git add` / `commit` / `push` | Cientos de ficheros pendientes — necesita sesión propia | TAREA H |
| Reescribir `README.md` para reflejar V2 | Decidido hacerlo en TAREA D para no dejar repo con info falsa | Hecho en TAREA D+ (mismo chat) |
| Crear GitHub Pages V2 (`mortemj.github.io/AU_UJI_v2`) | Diseño + colores propios merece sesión dedicada | TAREA I |
| Desplegar app V2 (`tfm-abandono-dinamico.streamlit.app`) | Decisión nombre + duplicación entorno | TAREA J |

---

## 📚 Contexto técnico relevante

### Cambio de paradigma V1 → V2 (sistema dinámico)

V2 introduce un **patrón de selección dinámica del modelo ganador**:

- `data/06_evaluacion/metricas_modelo.json` es la **fuente única de verdad**
- `f6_m00_preparacion.ipynb` lee `resultados_maestro.parquet`, selecciona ganador por `f1_test` (desempate `recall_test`, umbral 0.001) y escribe el JSON
- App Streamlit, notebooks F6 y (próximamente) README leen del JSON
- Ya **no hay nombres de algoritmo hardcodeados** ("CatBoost", "Stacking") — todo es variable dinámica

### Modelo ganador actual

`LightGBM__none.pkl` · AUC=0.9564 · F1=0.8334 · n_test=6.725 (estado al 04/05/2026)

---

## 📦 Trazabilidad

Este `.md` complementa la serie:

- `tareaB_completada.md` — Sistema dinámico HTMLs
- `tareaC_completada.md` — Validador Excel 5 niveles
- **`tareaD_completada.md`** ← este fichero
- `contexto_chat_nuevo_tareaH.md` — Para el siguiente chat (Git push V2)

---

<sub>📅 Documento generado el 04/05/2026 · TAREA D · Limpieza raíz V2 · TFM AU_UJI_v2</sub>
