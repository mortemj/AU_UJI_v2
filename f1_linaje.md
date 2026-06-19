# Linaje fase1 · Transformación

## Nivel notebook (5 transiciones)

| # | Notebook | Función | Operación | Flujo | Filas | Δ filas | Motivo filas | Cols + |
|---|----------|---------|-----------|-------|-------|--------:|--------------|--------|
| 1 | f1_m02_limpieza | limpiar_dataframe / normalizar_nombre_columna | limpieza | datos_originales_excel → expedientes | -→109.568 | - | 9 hojas (1.050.793 reg. originales) → 9 tablas limpias, una a una sin pérdida de filas. La espina 'expedientes' queda en 109.568. | — |
| 2 | f1_m04a_union_tablas | pd.merge / drop_duplicates | merge (×8) + dedup | expedientes → tabla_unida | 109.568→- | - | Left join sobre 'expedientes' (espina) por per_id_ficticio/exp_tit_id; no altera el nº de filas. drop_duplicates elimina duplicados exactos. | id_beca, nombre_beca, mat_curso_aca, sexo, fecha_nacimiento, id_pais, pais_nombre, poblacion, provincia, pais, curso_aca, (+1), media_titulacion_curso, media_titulacion_alumno, nombre_recibos, forma_de_pago, numero_pagos, titulacion, rama, cred_titulacion, tipo, (+1), nombre_trabajo, mat_curso_aca |
| 3 | f1_m04b_union_preinscripcion | pd.merge / dropna / drop / loc | merge + filtro | tabla_unida → tabla_preins | -→- | - | Left join con preinscripción sobre la espina; filtros loc/dropna sanean registros sin alterar la cardinalidad de la espina. | — |
| 4 | f1_m04c_correccion_notas | normalizar_nota / pd.merge | merge (×3) + corrección | tabla_preins → tabla_notas_ok | -→- | - | Corrige y recalcula medias; sin cambio de filas. | — |
| 5 | f1_m04d_correccion_via_acceso | loc / asignación condicional | corrección (loc) | tabla_notas_ok → df_alumno | -→109.568 | - | Corrige 'vía de acceso' con reglas loc; sin cambio de filas. Resultado final: 109.568 filas × 37 columnas. | — |

## Nivel función (10 transiciones)

| # | Notebook | Función | Operación | Flujo | Filas | Δ filas | Motivo filas | Cols + |
|---|----------|---------|-----------|-------|-------|--------:|--------------|--------|
| 1 | f1_m04a_union_tablas | pd.merge(how='left') | merge | expedientes → +becas | 109.568→- | - | Left join de 'becas' sobre la espina por per_id_ficticio; no altera filas. | id_beca, nombre_beca, mat_curso_aca |
| 2 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +becas → +demograficos | -→- | - | Left join de 'demograficos' sobre la espina por per_id_ficticio; no altera filas. | sexo, fecha_nacimiento, id_pais, pais_nombre |
| 3 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +demograficos → +domicilios | -→- | - | Left join de 'domicilios' sobre la espina por per_id_ficticio; no altera filas. | poblacion, provincia, pais, curso_aca, (+1) |
| 4 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +domicilios → +notas | -→- | - | Left join de 'notas' sobre la espina por per_id_ficticio; no altera filas. | media_titulacion_curso, media_titulacion_alumno |
| 5 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +notas → +recibos | -→- | - | Left join de 'recibos' sobre la espina por per_id_ficticio; no altera filas. | nombre_recibos, forma_de_pago, numero_pagos |
| 6 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +recibos → +titulaciones | -→- | - | Left join de 'titulaciones' sobre la espina por per_id_ficticio; no altera filas. | titulacion, rama, cred_titulacion, tipo, (+1) |
| 7 | f1_m04a_union_tablas | pd.merge(how='left') | merge | +titulaciones → +trabajo | -→- | - | Left join de 'trabajo' sobre la espina por per_id_ficticio; no altera filas. | nombre_trabajo, mat_curso_aca |
| 8 | f1_m04a_union_tablas | drop_duplicates() | dedup | +trabajo → tras_dedup | -→- | - | Elimina filas duplicadas exactas tras la unión. | — |
| 9 | f1_m04c_correccion_notas | normalizar_nota() | corrección | tras_dedup → tras_norma_nota | -→- | - | Normaliza el formato de las notas; sin cambio de filas. | — |
| 10 | f1_m04d_correccion_via_acceso | loc / asignación condicional | corrección | tras_norma_nota → df_alumno | -→109.568 | - | Corrige 'vía de acceso'; resultado final 109.568 × 37. | — |
