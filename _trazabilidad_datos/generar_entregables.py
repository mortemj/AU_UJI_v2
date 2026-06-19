# -*- coding: utf-8 -*-
"""
Genera los entregables de trazabilidad de datos (PARTES A, B, C).
SOLO LECTURA sobre el proyecto: lee esquemas reales de columnas.json y escribe
unicamente dentro de _trazabilidad_datos/. No toca ningun fichero del proyecto.

Salidas:
  - inventario_datasets.csv          (PARTE A, conteos + generador/consumidores)
  - genealogia_variables.xlsx        (PARTE B, una fila por variable)
  - sankey_flujo_datos.mmd           (PARTE C, Mermaid sankey-beta)
  - sankey_flujo_datos.png           (PARTE C, imagen matplotlib, etiquetas en diagonal)
"""
import json, csv, os
import pandas as pd

BASE = os.path.dirname(__file__)
COLS = json.load(open(os.path.join(BASE, 'columnas.json'), encoding='utf-8'))
IO   = json.load(open(os.path.join(BASE, 'io_map.json'), encoding='utf-8'))

def cols_of(path):
    return [c.lower() for c in COLS.get(path, {}).get('cols', [])]
def ncols(path):
    return len(COLS.get(path, {}).get('cols', []))
def nfilas(path):
    return COLS.get(path, {}).get('filas', 'n/d')

# --------------------------------------------------------------------------- #
# PARTE A — inventario de la cadena (orden canonico) con generador/consumidores
# Generadores/consumidores confirmados leyendo los .ipynb (io_map.json + verif).
# --------------------------------------------------------------------------- #
# (ruta, etiqueta_corta, fase, generador, nota)
CADENA = [
 ('data/00_raw/datos_proyecto_sin_preinscrip.xlsx::Expedientes', 'Excel: 8 hojas academicas', 'F0/datos originales', '— (origen, Servicio de Planificacion UJI)', 'datos originales'),
 ('data/00_raw/preinscripcion_si.xlsx::Hoja1', 'Excel: preinscripcion', 'F0/datos originales', '— (origen, Servicio de Planificacion UJI)', 'datos originales'),
 ('data/01_interim/expedientes.parquet', '01_interim/expedientes', 'F1 m02_limpieza', 'f1_m02_limpieza', 'espina; 9 tablas limpias (1 por hoja)'),
 ('data/01_interim/becas.parquet', '01_interim/becas', 'F1 m02_limpieza', 'f1_m02_limpieza', 'hoja Circunstancias'),
 ('data/01_interim/demograficos.parquet', '01_interim/demograficos', 'F1 m02_limpieza', 'f1_m02_limpieza', 'hoja Nac-Sexo_Nacionalidad'),
 ('data/01_interim/domicilios.parquet', '01_interim/domicilios', 'F1 m02_limpieza', 'f1_m02_limpieza', ''),
 ('data/01_interim/notas.parquet', '01_interim/notas', 'F1 m02_limpieza', 'f1_m02_limpieza', ''),
 ('data/01_interim/recibos.parquet', '01_interim/recibos', 'F1 m02_limpieza', 'f1_m02_limpieza', ''),
 ('data/01_interim/titulaciones.parquet', '01_interim/titulaciones', 'F1 m02_limpieza', 'f1_m02_limpieza', '45 titulaciones'),
 ('data/01_interim/trabajo.parquet', '01_interim/trabajo', 'F1 m02_limpieza', 'f1_m02_limpieza', ''),
 ('data/01_interim/preinscripcion.parquet', '01_interim/preinscripcion', 'F1 m02_limpieza', 'f1_m02_limpieza', ''),
 ('data/02_processed/df_alumno_base.parquet', '02_processed/df_alumno_base', 'F1 m04a_union_tablas', 'f1_m04a_union_tablas', 'merge expedientes + 8 tablas'),
 ('data/02_processed/df_alumno.parquet', '02_processed/df_alumno', 'F1 m04b/c/d', 'f1_m04b/c/d (+preinscripcion, correcciones)', 'salida final Fase 1 (37 col)'),
 ('data/03_features/df_alumno_limpio.parquet', '03_features/df_alumno_limpio', 'F3 m01_validacion', 'f3_m01_validacion', 'validacion + derivadas iniciales'),
 ('data/03_features/df_longitudinal_trayectoria.parquet', '03_features/df_longitudinal_trayectoria', 'F3 m01_validacion', 'f3_m01_validacion', 'nivel curso-alumno (auxiliar)'),
 ('data/03_features/df_expediente_base.parquet', '03_features/df_expediente_base', 'F3 m02_agregacion', 'f3_m02_agregacion', 'agrega a nivel expediente (109.568->33.621)'),
 ('data/03_features/df_expediente_features.parquet', '03_features/df_expediente_features', 'F3 m03_features', 'f3_m03_features', 'feature engineering'),
 ('data/03_features/df_exp_automl_target.parquet', '03_features/df_exp_automl_target', 'F3 m04a_automl_target', 'f3_m04a_automl_target', 'anade target abandono'),
 ('data/03_features/df_exp_target_eda.parquet', '03_features/df_exp_target_eda', 'F3 m04b_eda_target', 'f3_m04b_eda_target', 'variante para EDA'),
 ('data/03_features/df_eda_con_target.parquet', '03_features/df_eda_con_target', 'F3 m05_target_export', 'f3_m05_target_export', ''),
 ('data/automl/df_exp_automl_D.parquet', 'automl/df_exp_automl_D', 'F3 m05_target_export', 'f3_m05_target_export', 'caso D para AutoML'),
 ('data/03_features/dataset_final_tfm.parquet', '03_features/dataset_final_tfm', 'F3 m05_target_export', 'f3_m05_target_export', 'DATASET FINAL (24 feat + target)'),
 ('data/04_eda/df_eda_final.parquet', '04_eda/df_eda_final', 'F3 m08_auditoria', 'f3_m08_auditoria', 'version EDA (con titulacion)'),
 ('data/04_eda/df_eda_perfiles.parquet', '04_eda/df_eda_perfiles', 'F3 m09_perfiles_riesgo', 'f3_m09_perfiles_riesgo', 'anade score/perfil de riesgo'),
 ('data/05_modelado/X_train.parquet', '05_modelado/X_train', 'F5 m01a_preparacion', 'f5_m01a_preparacion', 'split train (sin preprocesar)'),
 ('data/05_modelado/X_test.parquet', '05_modelado/X_test', 'F5 m01a_preparacion', 'f5_m01a_preparacion', 'split test (sin preprocesar)'),
 ('data/05_modelado/X_train_prep.parquet', '05_modelado/X_train_prep', 'F5 m01a_preparacion', 'f5_m01a_preparacion', 'train preprocesado (pipeline)'),
 ('data/05_modelado/X_test_prep.parquet', '05_modelado/X_test_prep', 'F5 m01a_preparacion', 'f5_m01a_preparacion', 'test preprocesado (pipeline)'),
 ('data/06_evaluacion/meta_test.parquet', '06_evaluacion/meta_test', 'F6 m00_preparacion', 'f6_m00_preparacion', 'metadatos del test'),
 ('data/06_evaluacion/meta_test_app.parquet', '06_evaluacion/meta_test_app', 'F6 m00b_preparacion_app', 'f6_m00b_preparacion_app', 'meta + features + prob (app)'),
]

def consumidores(path):
    stem = os.path.basename(path).split('::')[0]
    info = IO.get(stem, {})
    cons = [c for c in info.get('consume', [])]
    return cons

with open(os.path.join(BASE, 'inventario_datasets.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['dataset', 'fase', 'n_filas', 'n_campos', 'generador', 'consumidores_detectados', 'nota'])
    for path, lab, fase, gen, nota in CADENA:
        cons = consumidores(path)
        cons_txt = ', '.join(cons) if cons else 'NINGUNO (posible huerfano)'
        w.writerow([lab, fase, nfilas(path), ncols(path), gen, cons_txt, nota])
print('OK inventario_datasets.csv')

# --------------------------------------------------------------------------- #
# PARTE B — genealogia de variables (curada con evidencia; (verificar) si dudoso)
# --------------------------------------------------------------------------- #
# Filas: (nombre_origen, nombre_final, fase_donde_nace, estado, motivo)
GEN = [
 # --- Claves / identificadores ---
 ('Per_id_ficticio (Expedientes)', 'per_id_ficticio', 'F1 (origen)', 'RENOMBRADA', 'Normalizacion a snake_case minusculas (f1_m02). Clave de alumno. No entra como feature del modelo.'),
 ('Exp_Tit_Id (Expedientes)', 'exp_tit_id', 'F1 (origen)', 'RENOMBRADA', 'Normalizacion a snake_case (f1_m02). Clave expediente-titulacion. No es feature.'),
 # --- Variables academicas que sobreviven al dataset final ---
 ('Nota_Acceso (Expedientes)', 'nota_acceso', 'F1 (origen)', 'SIN CAMBIOS', 'Solo normalizacion de nombre a minusculas; valor academico conservado.'),
 ('Nota_selectividad (Expedientes)', 'nota_selectividad', 'F1 (origen)', 'SIN CAMBIOS', 'Solo normalizacion de nombre; corregida en f1_m04c (normalizar_nota).'),
 ('Rama (Titulaciones)', 'rama', 'F1 (origen)', 'SIN CAMBIOS', 'Rama de conocimiento de la titulacion; normalizacion de nombre.'),
 ('Sexo (Nac-Sexo_Nacionalidad)', 'sexo', 'F1 (origen)', 'SIN CAMBIOS', 'Normalizacion de nombre; codificada despues en F3.'),
 ('Pais_Nombre (Nac-Sexo_Nacionalidad)', 'pais_nombre', 'F1 (origen)', 'SIN CAMBIOS', 'Normalizacion de nombre.'),
 ('Provincia (Domicilios)', 'provincia', 'F1 (origen)', 'SIN CAMBIOS', 'Normalizacion de nombre.'),
 # --- Renombrados con cambio semantico (preinscripcion) ---
 ('ORDEN_TITULACION (preinscripcion)', 'orden_preferencia', 'F1 m04b', 'RENOMBRADA', 'Orden de preferencia de la titulacion en preinscripcion; renombrada al unir preinscripcion.'),
 ('CUPO (preinscripcion)', 'cupo', 'F1 m04b', 'RENOMBRADA', 'Cupo de acceso; normalizacion de nombre.'),
 ('VIA_ESTUDIOS (preinscripcion)', 'via_acceso', 'F1 m04b/d', 'RENOMBRADA', 'Via de acceso; corregida y mapeada en f1_m04d (str.replace + relleno de NaN).'),
 ('UNIVERSIDAD / NOMBRE_UNIVERSIDAD (preinscripcion)', 'universidad_origen', 'F1 m04b', 'RENOMBRADA', 'Universidad de origen del alumno. (verificar) columna fuente exacta entre UNIVERSIDAD y NOMBRE_UNIVERSIDAD.'),
 # --- Features NUEVAS creadas en feature engineering (F3) ---
 ('— (derivada)', 'edad_entrada', 'F3 m02/m03', 'NUEVA', 'Calculada a partir de Fecha_nacimiento y curso de inicio (edad_entrada_calc en F3).'),
 ('— (derivada de Cred_Superados)', 'cred_superados_anio_1er', 'F3 m03', 'NUEVA', 'Creditos superados en el 1er anio; agregacion longitudinal por expediente.'),
 ('— (derivada de Media_Curso/Nota)', 'nota_1er_anio', 'F3 m03', 'NUEVA', 'Nota media del 1er anio; agregacion longitudinal.'),
 ('— (derivada de Cred_Matriculados/Superados)', 'cred_repetidos', 'F3 m03', 'NUEVA', 'Creditos repetidos; feature de rendimiento. (verificar) formula exacta.'),
 ('— (derivada)', 'tasa_repeticion', 'F3 m03', 'NUEVA', 'Tasa de repeticion; feature de rendimiento. (verificar) formula exacta.'),
 ('— (derivada por titulacion)', 'tasa_abandono_titulacion', 'F3 m03', 'NUEVA', 'Tasa historica de abandono de la titulacion (agregado por titulacion).'),
 ('— (derivada de Nombre_beca)', 'n_anios_beca', 'F3 m02', 'NUEVA', 'Numero de cursos con beca: suma de tiene_beca por alumno (f3_m02).'),
 ('— (derivada)', 'anios_sin_beca', 'F3 m03', 'NUEVA', 'n_cursos - n_anios_beca (f3_m03).'),
 ('— (derivada de Nombre_trabajo)', 'situacion_laboral', 'F3 m03', 'NUEVA', 'Situacion laboral derivada de la tabla Trabajo. (verificar) regla de codificacion.'),
 ('— (derivada de Nombre_trabajo)', 'n_anios_trabajando', 'F3 m03', 'NUEVA', 'Numero de cursos trabajando; agregacion de la tabla Trabajo.'),
 ('— (derivada de Numero_Pagos)', 'max_pagos', 'F3 m03', 'NUEVA', 'Maximo de numero_pagos (tabla Recibos) por alumno. (verificar) agregador exacto.'),
 ('— (derivada)', 'indicador_interrupcion', 'F3 m01/m03', 'NUEVA', 'Indicador de interrupcion de matricula (gaps en cursos).'),
 ('— (derivada)', 'anios_gap', 'F3 m01/m03', 'NUEVA', 'Numero de cursos de interrupcion (gap) en la trayectoria.'),
 ('— (derivada)', 'n_anios_sin_notas', 'F3 m03', 'NUEVA', 'Numero de cursos sin notas registradas.'),
 ('Egresado (Expedientes) + trayectoria', 'abandono', 'F3 m04a', 'NUEVA', 'TARGET: derivado de egresado/trayectoria (egresado_de_hecho) en f3_m04a_automl_target.'),
 # --- Variables ELIMINADAS (existen en origen/intermedios, no en dataset_final) ---
 ('Seguro (Expedientes)', '—', 'F1', 'ELIMINADA', 'No aporta valor predictivo; descartada en F3. (verificar) celda exacta.'),
 ('Nuevo (Expedientes)', '—', 'F1', 'ELIMINADA', 'Bandera de matricula nueva; no usada como feature final.'),
 ('Egresado (Expedientes)', '—', 'F3', 'ELIMINADA', 'Se usa para construir el target abandono y luego se descarta (riesgo de leakage).'),
 ('Fecha_nacimiento (Nac-Sexo)', '—', 'F3', 'ELIMINADA', 'Sustituida por la feature derivada edad_entrada.'),
 ('Id_Pais (Nac-Sexo)', '—', 'F1', 'ELIMINADA', 'Redundante con pais_nombre.'),
 ('Poblacion (Domicilios)', '—', 'F3', 'ELIMINADA', 'Granularidad excesiva; se conserva provincia.'),
 ('Pais (Domicilios)', '—', 'F3', 'ELIMINADA', 'pais_domicilio redundante; se conserva pais_nombre/provincia.'),
 ('Tipo_Domicilio (Domicilios)', '—', 'F1/F3', 'ELIMINADA', 'Usada para derivar vive_fuera; no entra al dataset final. (verificar).'),
 ('Media_Titulacion_Curso (Notas)', '—', 'F3', 'ELIMINADA', 'Agregado de titulacion no usado como feature final. (verificar).'),
 ('Media_Titulacion_Alumno (Notas)', '—', 'F3', 'ELIMINADA', 'Idem; descartada en seleccion de features.'),
 ('Nombre_recibos (Recibos)', '—', 'F3', 'ELIMINADA', 'Texto del recibo; solo se usa numero_pagos -> max_pagos.'),
 ('Forma_De_Pago (Recibos)', '—', 'F3', 'ELIMINADA', 'No seleccionada como feature final. (verificar).'),
 ('Tipo / Tipo_Estudio (Titulaciones)', '—', 'F1/F3', 'ELIMINADA', 'Metadatos de titulacion no usados como feature final.'),
 ('Cred_Titulacion (Titulaciones)', '—', 'F3', 'ELIMINADA', 'Usada en derivadas (pct_titulacion, cred_faltantes); no en dataset_final.'),
 ('Media_Curso (Expedientes)', '—', 'F3', 'ELIMINADA', 'Insumo de nota_1er_anio/nota_ultimo_anio; no entra directa.'),
]

dfB = pd.DataFrame(GEN, columns=['nombre_origen', 'nombre_final', 'fase_donde_nace', 'estado', 'motivo'])
xlsx_path = os.path.join(BASE, 'genealogia_variables.xlsx')
with pd.ExcelWriter(xlsx_path, engine='openpyxl') as xw:
    dfB.to_excel(xw, sheet_name='genealogia', index=False)
    # resumen por estado
    dfB['estado'].value_counts().rename_axis('estado').reset_index(name='n').to_excel(
        xw, sheet_name='resumen', index=False)
print('OK genealogia_variables.xlsx  (', len(dfB), 'filas )')

# --------------------------------------------------------------------------- #
# PARTE C — Sankey: nodos=datasets, valor del flujo = nº de campos COMPARTIDOS
# (interseccion de nombres de columna, en minusculas) entre dataset origen->destino.
# --------------------------------------------------------------------------- #
def shared(a_path, b_path):
    a, b = set(cols_of(a_path)), set(cols_of(b_path))
    if not a or not b:
        return 0
    return len(a & b)

# Espina principal + ramas documentadas (origen, destino)
EDGES = [
 ('data/01_interim/expedientes.parquet', 'data/02_processed/df_alumno_base.parquet'),
 ('data/02_processed/df_alumno_base.parquet', 'data/02_processed/df_alumno.parquet'),
 ('data/02_processed/df_alumno.parquet', 'data/03_features/df_alumno_limpio.parquet'),
 ('data/03_features/df_alumno_limpio.parquet', 'data/03_features/df_expediente_base.parquet'),
 ('data/03_features/df_expediente_base.parquet', 'data/03_features/df_expediente_features.parquet'),
 ('data/03_features/df_expediente_features.parquet', 'data/03_features/df_exp_automl_target.parquet'),
 ('data/03_features/df_exp_automl_target.parquet', 'data/03_features/dataset_final_tfm.parquet'),
 ('data/03_features/dataset_final_tfm.parquet', 'data/05_modelado/X_train.parquet'),
 ('data/05_modelado/X_train.parquet', 'data/05_modelado/X_train_prep.parquet'),
 # ramas
 ('data/03_features/df_expediente_features.parquet', 'data/03_features/df_exp_target_eda.parquet'),
 ('data/03_features/df_exp_automl_target.parquet', 'data/04_eda/df_eda_final.parquet'),
 ('data/04_eda/df_eda_final.parquet', 'data/04_eda/df_eda_perfiles.parquet'),
 ('data/05_modelado/X_test.parquet', 'data/06_evaluacion/meta_test_app.parquet'),
 ('data/03_features/dataset_final_tfm.parquet', 'data/05_modelado/X_test.parquet'),
]

def short(p):
    return os.path.basename(p).split('::')[0].replace('.parquet', '')

# ---- Mermaid sankey-beta ----
mmd = ['---', 'title: Trazabilidad de datos TFM (flujo de datasets; valor = nº de campos compartidos)', '---', 'sankey-beta', '']
for a, b in EDGES:
    v = shared(a, b)
    mmd.append(f'{short(a)},{short(b)},{max(v,1)}')
open(os.path.join(BASE, 'sankey_flujo_datos.mmd'), 'w', encoding='utf-8').write('\n'.join(mmd) + '\n')
print('OK sankey_flujo_datos.mmd')

# ---- PNG matplotlib (Sankey simplificado, etiquetas en diagonal) ----
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Layout por capas (x) de la espina principal
SPINE = [
 'data/01_interim/expedientes.parquet',
 'data/02_processed/df_alumno_base.parquet',
 'data/02_processed/df_alumno.parquet',
 'data/03_features/df_alumno_limpio.parquet',
 'data/03_features/df_expediente_base.parquet',
 'data/03_features/df_expediente_features.parquet',
 'data/03_features/df_exp_automl_target.parquet',
 'data/03_features/dataset_final_tfm.parquet',
 'data/05_modelado/X_train.parquet',
 'data/05_modelado/X_train_prep.parquet',
]
fig, ax = plt.subplots(figsize=(16, 8))
xstep = 1.6
ybar = 0.0
maxc = max(ncols(p) for p in SPINE)
scale = 4.0 / maxc  # altura visual de la barra proporcional al nº de columnas
xs = {}
for i, p in enumerate(SPINE):
    h = ncols(p) * scale
    x = i * xstep
    xs[p] = (x, h)
    ax.add_patch(Rectangle((x, ybar - h/2), 0.45, h, color='#1e4d8c', alpha=0.85, zorder=3))
    ax.text(x + 0.22, ybar - h/2 - 0.12, f'{short(p)}\n({ncols(p)} col)',
            rotation=30, ha='right', va='top', fontsize=8.5, color='#0d2b50')
# enlaces espina con grosor ∝ campos compartidos
for a, b in zip(SPINE[:-1], SPINE[1:]):
    (xa, ha), (xb, hb) = xs[a], xs[b]
    v = shared(a, b)
    lw = max(v * scale, 0.05)
    y0 = ybar
    ax.fill_between([xa + 0.45, xb], [y0 - lw/2]*2, [y0 + lw/2]*2,
                    color='#4a9fd8', alpha=0.55, zorder=1)
    ax.text((xa + 0.45 + xb)/2, y0 + lw/2 + 0.05, str(v), ha='center', va='bottom',
            fontsize=8, color='#b03000', fontweight='bold')
ax.set_xlim(-0.8, (len(SPINE)-1)*xstep + 0.8)
ax.set_ylim(-3.2, 3.2)
ax.axis('off')
ax.set_title('Trazabilidad de datos — espina principal (grosor/etiqueta = nº de campos compartidos entre datasets)',
             fontsize=11, color='#1e4d8c')
fig.tight_layout()
fig.savefig(os.path.join(BASE, 'sankey_flujo_datos.png'), dpi=150, bbox_inches='tight')
print('OK sankey_flujo_datos.png')
