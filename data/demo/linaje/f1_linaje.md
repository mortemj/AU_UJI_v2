# Linaje fase1 · Transformación

## Nivel notebook (2 transiciones)

| # | Notebook | Función | Operación | Flujo | Filas | Δ filas | Motivo filas | Cols + |
|---|----------|---------|-----------|-------|-------|--------:|--------------|--------|
| 1 | f1_m04a_union_tablas | pd.merge / drop_duplicates | merge + dedup | expedientes → df_alumno_base | 109.568→109.568 | 0 (sin cambio) | m04a: left join de las tablas sobre la espina (expedientes) por clave; drop_duplicates elimina duplicados exactos. | pais_domicilio, vive_fuera, tiene_beca |
| 2 | f1_m04b–d | pd.merge / loc | merge + corrección | df_alumno_base → df_alumno | 109.568→109.568 | 0 (sin cambio) | m04b: añade preinscripción (left join). m04c/m04d: corrección de notas y vía de acceso sobre df_alumno. | via_acceso_exp, via_acceso, orden_preferencia, universidad_origen |

## Nivel función (9 transiciones)

| # | Notebook | Función | Operación | Flujo | Filas | Δ filas | Motivo filas | Cols + |
|---|----------|---------|-----------|-------|-------|--------:|--------------|--------|
| 1 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | becas → df_alumno | 70.524→109.568 | - |  | nombre_beca |
| 2 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | demograficos → df_alumno | 30.873→109.568 | - |  | sexo, fecha_nacimiento, id_pais, pais_nombre |
| 3 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | domicilios → df_alumno | 210.911→109.568 | - |  | poblacion, provincia, curso_aca |
| 4 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | expedientes → df_alumno | 109.568→109.568 | - |  | exp_tit_id, curso_aca_ini, curso_aca, curso_aca_fin, nota, seguro, nota_selectividad, nota_acceso, cred_matriculados, cred_superados, egresado, nuevo, media_curso |
| 5 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | notas → df_alumno | 107.908→109.568 | - |  | curso_aca, exp_tit_id, media_titulacion_curso, media_titulacion_alumno |
| 6 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | preinscripcion → df_alumno | 210.986→109.568 | - |  | cupo |
| 7 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | recibos → df_alumno | 114.454→109.568 | - |  | curso_aca, forma_de_pago, numero_pagos |
| 8 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | titulaciones → df_alumno | 45→109.568 | - |  | exp_tit_id, titulacion, rama, cred_titulacion |
| 9 | f1_m04a_union_tablas | pd.merge(how='left') | aporte de columnas | trabajo → df_alumno | 195.524→109.568 | - |  | exp_tit_id, nombre_trabajo |
