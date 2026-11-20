"""Pruebas aisladas, sin sobrescribir registros anteriores."""
from pathlib import Path
import sys,json,subprocess
S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S))
from herramientas.control_resistencia_m8 import verificar
def ejecutar():
    verificar();b=S.parent
    grupos=[('unificado',S,['-m','pytest','tests','-q']),('EP2',b/'Simulación_peletizadora',['-m','pytest','-q']),
        ('transmision',b/'Transmision',['-m','pytest','-q']),('integracion',b.parent,['-m','pytest','Capstone/integracion/test_auditoria_6a.py','-q']),
        ('4A',b/'Analisis_matriz_eje_vertical/Etapa_4A_matriz_y_arbol_principal',['test_etapa4a.py']),
        ('4B',b/'Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional',['test_etapa_4B.py']),
        ('4D',b/'Analisis_matriz_eje_vertical/Etapa_4D_FEM_preliminar',['validar_4D.py'])]
    datos=[]
    for nombre,cwd,args in grupos:
        p=subprocess.run([sys.executable,*args],cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
        datos.append(dict(grupo=nombre,codigo=p.returncode,salida=p.stdout+p.stderr))
        print(nombre,p.returncode,(p.stdout+p.stderr)[-1000:],flush=True)
    (S/'resultados/prototipo/resistencia_m8_2026_11_20/pruebas.json').write_text(json.dumps(dict(grupos=datos,conservacion=verificar()),ensure_ascii=False,indent=2),encoding='utf-8')
    if any(g['codigo'] for g in datos):raise SystemExit(1)
if __name__=='__main__':ejecutar()
