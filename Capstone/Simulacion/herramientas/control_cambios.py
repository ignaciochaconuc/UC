"""Inventario previo y comprobación reversible; nunca modifica EP2."""
import hashlib
import json
from pathlib import Path

RAIZ=Path(__file__).resolve().parents[2]
NUEVO=RAIZ/'Simulacion'
ARCHIVO=RAIZ/'archivo/Prototipo_escalado_2026_11_18'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def registrar():
    control=NUEVO/'control';control.mkdir(parents=True,exist_ok=True)
    destino=control/'estado_previo.json'
    if destino.exists():
        raise RuntimeError('Ya hay un inventario previo; no sobrescribir')
    archivos=[f for f in RAIZ.rglob('*') if f.is_file() and not f.is_relative_to(NUEVO)
              and not any(k in f.parts for k in ('__pycache__','.pytest_cache','.venv'))]
    previo={str(f.relative_to(RAIZ)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in archivos}
    retiro=[dict(archivo=k,**v,destino_archivo=str(Path('archivo/Prototipo_escalado_2026_11_18')/Path(k).relative_to('Prototipo')),
        proposito='Implementación y resultados basados en patrón escalado; retirados del uso activo, conservados íntegros para reversión y trazabilidad')
        for k,v in previo.items() if Path(k).parts[0]=='Prototipo']
    plan={'fecha':'2026-11-19','estado_git':'git status no disponible: git.exe no ejecutable válido en este entorno; no se infiere worktree limpio',
        'crear':['Simulacion/ (arquitectura, configuraciones, STEP, pruebas, resultados y documentación)',
                 'archivo/Prototipo_escalado_2026_11_18/ (retiro reversible)', 'Prototipo/README.md (aviso de migración)'],
        'mover_sin_alterar':retiro,'modificar_EP2':[], 'eliminar_irrecuperablemente':[],
        'protegidos':'Todos los archivos existentes salvo retirada reversible de Prototipo; se exige SHA256 idéntico en destino para cada archivo retirado'}
    destino.write_text(json.dumps(previo,indent=2,ensure_ascii=False),encoding='utf-8')
    (control/'plan_de_cambios.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Inventario previo: {len(previo)} archivos; retiro reversible: {len(retiro)}')


def verificar():
    previo=json.loads((NUEVO/'control/estado_previo.json').read_text(encoding='utf-8'))
    fallos=[]
    for nombre,v in previo.items():
        relative=Path(nombre)
        p=ARCHIVO/relative.relative_to('Prototipo') if relative.parts[0]=='Prototipo' else RAIZ/relative
        if not p.is_file() or sha(p)!=v['sha256']:
            fallos.append(str(p))
    if fallos:
        raise RuntimeError('Archivos alterados o ausentes: '+str(fallos))
    return {'archivos_anteriores_verificados':len(previo),'alterados':0,'retiro_reversible':True}


def cerrar():
    resultado=verificar()
    plan=json.loads((NUEVO/'control/plan_de_cambios.json').read_text(encoding='utf-8'))
    nuevos=[str(f.relative_to(RAIZ)) for f in NUEVO.rglob('*') if f.is_file()
        and not any(k in f.parts for k in ('__pycache__','.pytest_cache','.venv'))
        and f.name!='cierre_de_cambios.json']
    resultado.update(archivos_creados_en_arquitectura=nuevos,
        archivos_retirados_del_uso_activo=[r['archivo'] for r in plan['mover_sin_alterar']],
        reemplazos_activos=[{'archivo':'Prototipo/README.md','proposito':'Aviso de migración; original conservado en archivo'}],
        archivos_eliminados_irrecuperablemente=[],EP2_modificado=False,commit_o_push=False)
    (NUEVO/'control/cierre_de_cambios.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in resultado.items() if k not in ('archivos_creados_en_arquitectura','archivos_retirados_del_uso_activo')},indent=2,ensure_ascii=False))


if __name__=='__main__':
    import sys
    if '--registrar' in sys.argv: registrar()
    elif '--cerrar' in sys.argv:cerrar()
    else: print(json.dumps(verificar(),indent=2))
