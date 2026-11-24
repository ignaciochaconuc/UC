"""Localiza máximos reales y comprueba la calidad geométrica del tetraedro crítico."""
import json
import numpy as np
from inspeccionar import ROOT
from preparar_modelo import basis

rows=[]
for h in [8,7,6]:
    folder=ROOT/f'componentes_t2.0_h{h}'
    r=json.loads((folder/'resultados.json').read_text()); m=np.load(folder/'modelo.npz')
    index=r['max_stress_element']-1; x=m['xyz'][m['elements'][index]-1]; dets=[]; conds=[]
    a=.5854101966249685; b=.1381966011250105
    for i in range(4):
        l=np.full(4,b); l[i]=a; _,dn=basis(l[1:]); jac=x.T@dn
        dets.append(float(np.linalg.det(jac))); conds.append(float(np.linalg.cond(jac)))
    rows.append(dict(h_mm=h,critical_solid=int(m['solid'][index]),element_id=r['max_stress_element'],
                     von_mises_GP_MPa=r['von_mises_max_integration_MPa'],von_mises_nodal_MPa=r['von_mises_max_nodal_MPa'],
                     critical_element_vertex_centroid_mm=r['max_stress_element_centroid_mm'],
                     critical_element_min_Jacobian_4GP=min(dets),critical_element_max_Jacobian_condition_4GP=max(conds)))
report=dict(cases=rows,interpretation='El máximo no se estabiliza y cambia de localización. Los elementos críticos tienen determinantes positivos; ello no demuestra exactitud del máximo. Posibles contribuciones de aristas/muescas sin radio y de la discretización de contactos adheridos no conformes. No se ha aislado una causa única ni demostrado una singularidad analítica.',decision='No usar el máximo puntual ni su factor nominal para certificar un espesor óptimo. Desplazamientos globales y masas se comparan separadamente.')
(ROOT/'diagnostico_maximos.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8'); print(json.dumps(report,indent=2,ensure_ascii=False))
