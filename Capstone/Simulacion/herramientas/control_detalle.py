"""Línea base inmutable de la revisión manual; no modifica controles previos."""
from pathlib import Path
import hashlib
import json
import zipfile
S=Path(__file__).resolve().parents[1]
C=S/'control/detalle_manual_2026_11_20'
EDITABLES={'Simulacion/README.md','Simulacion/INFORME_TECNICO.md'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def registrar():
    if (C/'estado_previo.json').exists():raise ValueError('Línea base ya existe')
    C.mkdir(parents=True,exist_ok=True)
    archivos={str(p.relative_to(S.parent)).replace('\\','/'):sha(p) for p in S.parent.rglob('*') if p.is_file()
        and not p.is_relative_to(C) and not any(x in p.parts for x in ('__pycache__','.pytest_cache','.venv'))}
    (C/'estado_previo.json').write_text(json.dumps(archivos,indent=2,ensure_ascii=False),encoding='utf-8')
    with zipfile.ZipFile(C/'documentacion_previa.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in EDITABLES:z.write(S.parent/n,n)
    return verificar()

def verificar():
    datos=json.loads((C/'estado_previo.json').read_text(encoding='utf-8'));editados=[]
    with zipfile.ZipFile(C/'documentacion_previa.zip') as z:
        for nombre,h in datos.items():
            if not (S.parent/nombre).exists() or sha(S.parent/nombre)!=h:
                if nombre not in EDITABLES or hashlib.sha256(z.read(nombre)).hexdigest()!=h:raise ValueError('Histórico alterado: '+nombre)
                editados.append(nombre)
    return dict(archivos_previos=len(datos),historicos_intactos=True,documentacion_actualizada_con_respaldo=editados)

if __name__=='__main__':
    import sys
    print(json.dumps(registrar() if '--registrar' in sys.argv else verificar(),indent=2,ensure_ascii=False))
