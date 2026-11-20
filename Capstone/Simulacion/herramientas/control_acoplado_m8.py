"""Protección estricta de todos los archivos anteriores a la revisión M8."""
from pathlib import Path
import hashlib,json
S=Path(__file__).resolve().parents[1]
C=S/'control/acoplado_m8_2026_11_20'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registrar():
    if (C/'estado_previo.json').exists():raise ValueError('Línea base ya registrada')
    C.mkdir(parents=True,exist_ok=True)
    datos={str(f.relative_to(S.parent)).replace('\\','/'):sha(f) for f in S.parent.rglob('*') if f.is_file() and not f.is_relative_to(C)
        and not any(k in f.parts for k in ('__pycache__','.pytest_cache','.venv'))}
    (C/'estado_previo.json').write_text(json.dumps(datos,indent=2,ensure_ascii=False),encoding='utf-8')
    return verificar()
def verificar():
    datos=json.loads((C/'estado_previo.json').read_text(encoding='utf-8'))
    errores=[n for n,h in datos.items() if not (S.parent/n).is_file() or sha(S.parent/n)!=h]
    if errores:raise ValueError('Archivos históricos alterados: '+str(errores))
    return dict(archivos_verificados=len(datos),alterados=0)
if __name__=='__main__':
    import sys
    print(json.dumps(registrar() if '--registrar' in sys.argv else verificar(),indent=2))
