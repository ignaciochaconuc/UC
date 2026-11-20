"""Línea base incremental anterior a integrar el ensamble; retiro inexistente."""
import hashlib
import json
from pathlib import Path
import zipfile

SISTEMA=Path(__file__).resolve().parents[1]
CONTROL=SISTEMA/'control/ensamble_2026_11_19'
EDITABLES={'Simulacion/simular.py','Simulacion/peletizadora/nucleo.py',
    'Simulacion/configuraciones/prototipo.json','Simulacion/README.md','Simulacion/INFORME_TECNICO.md'}


def registrar():
    if (CONTROL/'estado_previo.json').exists():raise RuntimeError('Línea base ya registrada')
    CONTROL.mkdir(parents=True,exist_ok=True)
    fs=[f for f in SISTEMA.parent.rglob('*') if f.is_file() and not f.is_relative_to(CONTROL)
        and not any(k in f.parts for k in ('__pycache__','.pytest_cache','.venv'))]
    estado={str(f.relative_to(SISTEMA.parent)).replace('\\','/'):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
        'editable':str(f.relative_to(SISTEMA.parent)).replace('\\','/') in EDITABLES} for f in fs}
    (CONTROL/'estado_previo.json').write_text(json.dumps(estado,indent=2,ensure_ascii=False),encoding='utf-8')
    with zipfile.ZipFile(CONTROL/'fuentes_previas.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for nombre,info in estado.items():
            if info['editable']:z.write(SISTEMA.parent/nombre,nombre)
    (CONTROL/'plan.json').write_text(json.dumps({'editar':sorted(EDITABLES),'agregar':'Importación de ensamble, escenarios, pruebas y nueva revisión de resultados',
        'no_sobrescribir':'Resultados anteriores, STEP previos, configuración real ni código EP2',
        'git':'git.exe no ejecutable válido en revisión previa; evidencia por SHA256, sin commit/push'},indent=2,ensure_ascii=False),encoding='utf-8')
    print('Registrados',len(estado),'archivos; fuentes editables respaldadas')


def verificar():
    estado=json.loads((CONTROL/'estado_previo.json').read_text(encoding='utf-8'));errores=[];editados=[]
    with zipfile.ZipFile(CONTROL/'fuentes_previas.zip') as z:
        for nombre,info in estado.items():
            p=SISTEMA.parent/nombre
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:
                if info['editable'] and hashlib.sha256(z.read(nombre)).hexdigest()==info['sha256']:editados.append(nombre)
                else:errores.append(nombre)
    if errores:raise RuntimeError('Se alteraron archivos protegidos: '+str(errores))
    return {'archivos_previos':len(estado),'protegidos_intactos':True,'fuentes_editadas_con_respaldo':editados}


if __name__=='__main__':
    import sys
    if '--registrar' in sys.argv:registrar()
    else:print(json.dumps(verificar(),ensure_ascii=False,indent=2))
