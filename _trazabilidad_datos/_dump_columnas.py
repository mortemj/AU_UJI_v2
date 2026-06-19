# -*- coding: utf-8 -*-
"""Solo lectura: vuelca columnas/filas de parquets y hojas Excel del pipeline.
No modifica ningun fichero del proyecto. Salida por stdout y a columnas.json."""
import pyarrow.parquet as pq
import pandas as pd
import glob, json, os

res = {}
for f in glob.glob('data/**/*.parquet', recursive=True):
    fn = f.replace('\\', '/')
    if '/automl/' in fn and 'models' in fn:
        continue
    try:
        pf = pq.ParquetFile(f)
        res[fn] = {'filas': pf.metadata.num_rows, 'cols': list(pf.schema_arrow.names)}
    except Exception as e:
        res[fn] = {'error': str(e)}

# Excel originales (hojas + columnas)
excels = [
    'data/00_raw/datos_proyecto_sin_preinscrip.xlsx',
    'data/00_raw/preinscripcion_si.xlsx',
]
for f in excels:
    if not os.path.exists(f):
        continue
    try:
        xls = pd.ExcelFile(f)
        for sh in xls.sheet_names:
            df = xls.parse(sh, nrows=5)
            res[f + '::' + sh] = {'filas': 'n/d', 'cols': list(df.columns)}
    except Exception as e:
        res[f] = {'error': str(e)}

with open('_trazabilidad_datos/columnas.json', 'w', encoding='utf-8') as fh:
    json.dump(res, fh, ensure_ascii=False, indent=2)

for k in sorted(res):
    v = res[k]
    if 'cols' in v:
        print(f"### {k}  [{v['filas']} filas x {len(v['cols'])} cols]")
        print("   " + ", ".join(str(c) for c in v['cols']))
    else:
        print(f"### {k}  ERROR {v['error']}")
