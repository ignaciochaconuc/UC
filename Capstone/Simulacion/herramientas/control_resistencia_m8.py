"""Conservación estricta anterior al postproceso resistente M8."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parents[1]
C=S/'control/resistencia_m8_2026_11_20'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registrar():
    if (C/'estado_previo.json').exists():raise ValueError('Ya existe línea base')
    C.mkdir(parents=True,exist_ok=True)
    datos={str(f.relative_to(S.parent)).replace('\\','/'):sha(f) for f in S.parent.rglob('*') if f.is_file() and not f.is_relative_to(C)
        and not any(x in f.parts for x in ('__pycache__','.pytest_cache','.venv'))}
    (C/'estado_previo.json').write_text(json.dumps(datos,indent=2,ensure_ascii=False),encoding='utf-8')
    return verificar()
def verificar():
    datos=json.loads((C/'estado_previo.json').read_text(encoding='utf-8'))
    cambios=[p for p,h in datos.items() if not (S.parent/p).is_file() or sha(S.parent/p)!=h]
    if cambios:raise ValueError('Histórico alterado: '+str(cambios))
    return dict(archivos_verificados=len(datos),alterados=0)
if __name__=='__main__':
    import sys
    print(json.dumps(registrar() if '--registrar' in sys.argv else verificar(),indent=2))
