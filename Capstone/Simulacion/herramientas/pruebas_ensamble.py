"""Verifica sin sobrescribir el registro de pruebas histórico."""
from pathlib import Path
import subprocess
import sys
import json
S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S))
from herramientas.control_ensamble import verificar

def ejecutar():
    verificar();base=S.parent
    grupos=[('unificado',S,['-m','pytest','tests','-q']),
        ('EP2',base/'Simulación_peletizadora',['-m','pytest','-q']),
        ('transmision',base/'Transmision',['-m','pytest','-q']),
        ('6a',base.parent,['-m','pytest','Capstone/integracion/test_auditoria_6a.py','-q']),
        ('4a',base/'Analisis_matriz_eje_vertical/Etapa_4A_matriz_y_arbol_principal',['test_etapa4a.py']),
        ('4b',base/'Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional',['test_etapa_4B.py']),
        ('4d',base/'Analisis_matriz_eje_vertical/Etapa_4D_FEM_preliminar',['validar_4D.py'])]
    resultados=[]
    for nombre,cwd,args in grupos:
        p=subprocess.run([sys.executable,*args],cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=400)
        resultados.append(dict(grupo=nombre,codigo=p.returncode,salida=p.stdout+p.stderr))
        print(nombre,p.returncode,(p.stdout+p.stderr)[-600:],flush=True)
    d=S/'resultados/revision_ensamble_2026_11_19';d.mkdir(exist_ok=True)
    (d/'pruebas_ejecutadas.json').write_text(json.dumps(dict(grupos=resultados,conservacion=verificar()),ensure_ascii=False,indent=2),encoding='utf-8')
    if any(r['codigo'] for r in resultados):raise SystemExit(1)

if __name__=='__main__':ejecutar()
