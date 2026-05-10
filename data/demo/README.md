# 🎒 Datos de demostración (50 alumnos)

Esta carpeta contiene una **muestra ficticia de 50 expedientes** derivada de los datos académicos
de la Universitat Jaume I (cohortes 2010–2020), generada mediante muestreo estratificado por
egresado/abandono.

---

## 📦 Contenido

| Fichero | Descripción |
|---|---|
| `demo_excel.zip` | Archivo comprimido con los 2 Excel de prueba (un solo descomprimir). |

Una vez descomprimido (manual o automáticamente vía `f0_setup_demo.ipynb`), se obtienen:

- `datos_proyecto_sin_preinscrip.xlsx` — 8 hojas, ~50 alumnos.
- `preinscripcion_si.xlsx` — 1 hoja, mismos alumnos.

---

## 🎯 Propósito

Permitir que cualquier persona (tribunal del TFM, profesorado, compañeras/os de clase) pueda
**reproducir el pipeline completo** sin necesidad de los datos institucionales reales (protegidos
por RGPD).

---

## ⚠️ Aviso importante

- Los identificadores de alumno (`Per_id_ficticio`) son **anonimizados en origen** por la UJI.
- Los datos reales (n = 30.872 estudiantes únicos) **no se distribuyen públicamente**: están
  protegidos bajo el Reglamento General de Protección de Datos (RGPD) y solo se utilizan en local
  con autorización del Servicio de Planificación de la UJI.
- **Las métricas obtenidas con estos datos DEMO no son las del informe del TFM.** El modelo
  necesita los 30.872 alumnos completos para alcanzar el F1 = 0,8334 y AUC = 0,9564
  documentados en la memoria. Los DEMO sirven **únicamente para verificar que el pipeline
  funciona técnicamente**.

---

## 🧭 Cómo usarlos

Hay dos formas, ambas explicadas en `docs/html/manual_inicio.html` (paso 4):

### Forma rápida (recomendada)

Ejecutar el notebook `notebooks/fase0_configuracion/f0_setup_demo.ipynb`. El notebook:

1. Detecta si en `data/00_raw/` ya hay datos reales y, si los hay, **NO los machaca**.
2. Si hay DEMO antiguos, los renombra como `_BACKUP_<fecha_hora>.xlsx`.
3. Descomprime `demo_excel.zip` directamente en `data/00_raw/` con los nombres correctos.

### Forma manual

1. Hacer doble clic sobre `demo_excel.zip` y extraer el contenido.
2. Mover los 2 ficheros `.xlsx` a `data/00_raw/`.

---

## 🔬 Trazabilidad

Los DEMO se generaron con el notebook `notebooks/fase0_configuracion/f0_generar_excel_prueba.ipynb`
ejecutado por la autora sobre los datos originales (semilla aleatoria fija = 42 para reproducibilidad).

**Estrategia de muestreo:**
- Muestreo estratificado por la columna `Egresado` (S/N).
- ~25 alumnos con `Egresado = N` (no finalizado, proxy de abandono).
- ~25 alumnos con `Egresado = S` (finalizado).
- Se conservan todos los registros relacionados (titulaciones, recibos, domicilios, etc.) de los
  50 alumnos seleccionados.

---

## 📧 Contacto

Para cualquier duda sobre estos datos o sobre el proyecto, contactar con la autora:

- mjmorteruiz@uoc.edu (UOC)
- morte@uji.es (UJI)
