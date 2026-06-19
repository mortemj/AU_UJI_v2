# -*- coding: utf-8 -*-
"""Solo lectura: mapea lectura/escritura de parquet por notebook.
Recorre celdas de codigo de cada .ipynb y de los .py, detecta read_parquet/
to_parquet y captura el nombre de fichero .parquet de la misma linea o de
asignaciones de variables RUTA_*/path cercanas. No modifica nada."""
import json, glob, re, os
from collections import defaultdict

# 1) Mapa variable -> nombre de fichero .parquet (resolucion simple por notebook)
PARQ = re.compile(r"([A-Za-z0-9_\-./\\]+\.parquet)")
ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=.*?([A-Za-z0-9_\-./\\]+\.parquet)")

def stem(fn):
    return os.path.basename(fn.replace('\\', '/'))

def scan_code(lines):
    """Devuelve (lee, escribe) sets de nombres de fichero parquet."""
    var2file = {}
    text = "".join(lines)
    # registrar asignaciones var = '...parquet' o var = DIR / '...parquet'
    for ln in text.splitlines():
        m = ASSIGN.search(ln)
        if m:
            var2file[m.group(1)] = stem(m.group(2))
    lee, escribe = set(), set()
    for ln in text.splitlines():
        low = ln
        if 'read_parquet' in low:
            mm = PARQ.search(low)
            if mm:
                lee.add(stem(mm.group(1)))
            else:
                # buscar variable argumento read_parquet(VAR ...)
                v = re.search(r"read_parquet\(\s*([A-Za-z_][A-Za-z0-9_]*)", low)
                if v and v.group(1) in var2file:
                    lee.add(var2file[v.group(1)])
        if 'to_parquet' in low:
            mm = PARQ.search(low)
            if mm:
                escribe.add(stem(mm.group(1)))
            else:
                v = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\.to_parquet\(\s*([A-Za-z_][A-Za-z0-9_]*)", low)
                if v and v.group(2) in var2file:
                    escribe.add(var2file[v.group(2)])
    return lee, escribe

gen = defaultdict(list)   # fichero -> [notebooks que lo escriben]
con = defaultdict(list)   # fichero -> [notebooks que lo leen]

def proc_nb(path):
    try:
        nb = json.load(open(path, encoding='utf-8'))
    except Exception:
        return
    name = path.replace('\\', '/').split('notebooks/')[-1]
    allcode = []
    for c in nb.get('cells', []):
        if c.get('cell_type') == 'code':
            allcode += c.get('source', [])
    lee, escribe = scan_code(allcode)
    for f in escribe:
        gen[f].append(name)
    for f in lee:
        con[f].append(name)

for p in glob.glob('notebooks/**/*.ipynb', recursive=True):
    if 'checkpoint' in p:
        continue
    proc_nb(p)

# .py (app + src + scripts)
for p in glob.glob('app/**/*.py', recursive=True) + glob.glob('src/**/*.py', recursive=True) + glob.glob('scripts/*.py'):
    try:
        lee, escribe = scan_code(open(p, encoding='utf-8').readlines())
    except Exception:
        continue
    name = p.replace('\\', '/')
    for f in escribe:
        gen[f].append(name)
    for f in lee:
        con[f].append(name)

allf = sorted(set(list(gen) + list(con)))
out = {}
for f in allf:
    out[f] = {'genera': sorted(set(gen.get(f, []))), 'consume': sorted(set(con.get(f, [])))}
json.dump(out, open('_trazabilidad_datos/io_map.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

for f in allf:
    g = out[f]['genera']; c = out[f]['consume']
    print(f"\n### {f}")
    print(f"   GENERA : {', '.join(g) if g else '— (huérfano de generador detectado)'}")
    print(f"   CONSUME: {', '.join(c) if c else '— NINGUNO (posible huérfano)'}")
