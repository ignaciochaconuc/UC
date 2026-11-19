"""Pruebas aisladas por subsistema; no reejecuta simulaciones comerciales."""
import json
from pathlib import Path
import subprocess
import sys
from simular_prototipo import RAIZ, SALIDA, congelar_historicos, verificar_hashes


def ejecutar():
    hashes=congelar_historicos();capstone=RAIZ.parent
    pruebas=[
        ('prototipo',RAIZ,['-m','pytest','-q']),
        ('contacto_eje_rodamientos',capstone/'Simulación_peletizadora',['-m','pytest','-q']),
        ('transmision',capstone/'Transmision',['-m','pytest','-q']),
        ('auditoria6a',capstone.parent,['-m','pytest','Capstone/integracion/test_auditoria_6a.py','-q']),
        ('matriz4a',capstone/'Analisis_matriz_eje_vertical/Etapa_4A_matriz_y_arbol_principal',['test_etapa4a.py']),
        ('matriz4b',capstone/'Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional',['test_etapa_4B.py']),
        ('matriz4d_validaciones',capstone/'Analisis_matriz_eje_vertical/Etapa_4D_FEM_preliminar',['validar_4D.py'])]
    resultados=[]
    for nombre,cwd,args in pruebas:
        proc=subprocess.run([sys.executable,*args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            encoding='utf-8',errors='replace',timeout=300)
        resultados.append({'grupo':nombre,'comando':[sys.executable,*args],'cwd':str(cwd),
            'codigo_salida':proc.returncode,'salida':proc.stdout})
        print(nombre,proc.returncode,proc.stdout[-500:])
    verificar_hashes(hashes)
    SALIDA.mkdir(parents=True,exist_ok=True)
    (SALIDA/'pruebas_ejecutadas.json').write_text(json.dumps({'historicos_conservados':True,
        'nota':'4D solo pruebas de malla/elemento/archivos, no resolución FEM nueva completa',
        'grupos':resultados},ensure_ascii=False,indent=2),encoding='utf-8')
    if any(r['codigo_salida'] for r in resultados):
        raise SystemExit('Existen pruebas fallidas; revisar pruebas_ejecutadas.json')


if __name__=='__main__':
    ejecutar()
