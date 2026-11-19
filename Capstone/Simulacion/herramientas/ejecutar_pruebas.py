"""Pruebas aisladas: sistema nuevo y suites históricas sin regenerar EP2."""
from pathlib import Path
import json
import subprocess
import sys

SISTEMA=Path(__file__).resolve().parents[1]
if str(SISTEMA) not in sys.path:sys.path.insert(0,str(SISTEMA))
from herramientas.control_cambios import verificar


def ejecutar():
    base=SISTEMA.parent;verificar()
    grupos=[('sistema_STEP',SISTEMA,['-m','pytest','tests','-q']),
        ('EP2_contacto_eje_rodamientos',base/'Simulación_peletizadora',['-m','pytest','-q']),
        ('transmision',base/'Transmision',['-m','pytest','-q']),
        ('auditoria6a',base.parent,['-m','pytest','Capstone/integracion/test_auditoria_6a.py','-q']),
        ('matriz4a',base/'Analisis_matriz_eje_vertical/Etapa_4A_matriz_y_arbol_principal',['test_etapa4a.py']),
        ('matriz4b',base/'Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional',['test_etapa_4B.py']),
        ('matriz4d_validacion_no_simulacion',base/'Analisis_matriz_eje_vertical/Etapa_4D_FEM_preliminar',['validar_4D.py'])]
    resultados=[]
    for nombre,cwd,args in grupos:
        proc=subprocess.run([sys.executable,*args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            encoding='utf-8',errors='replace',timeout=300)
        resultados.append(dict(grupo=nombre,comando=[sys.executable,*args],cwd=str(cwd),codigo_salida=proc.returncode,salida=proc.stdout))
        print(nombre,proc.returncode,proc.stdout[-500:])
    destino=SISTEMA/'resultados';destino.mkdir(exist_ok=True)
    (destino/'pruebas_ejecutadas.json').write_text(json.dumps({'grupos':resultados,'conservacion':verificar(),
        'nota':'Las11pruebas del prototipo escalado se preservan archivadas, no son validación del nuevo STEP.'},ensure_ascii=False,indent=2),encoding='utf-8')
    if any(r['codigo_salida'] for r in resultados):raise SystemExit('Existen pruebas fallidas')


if __name__=='__main__':ejecutar()
