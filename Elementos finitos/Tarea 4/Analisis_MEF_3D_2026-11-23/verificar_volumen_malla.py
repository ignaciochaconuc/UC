"""Integra volumen C3D10 con regla tetraédrica de grado 3 (5 puntos)."""
import argparse
import csv
import json
import numpy as np
from inspeccionar import ROOT
from preparar_modelo import basis

def main(t,h):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'
    model=np.load(folder/'modelo.npz'); xyz=model['xyz']; ec=model['elements']; labels=model['solid']
    points=[(np.array([.25,.25,.25]),-.8)]
    for i in range(4):
        l=np.ones(4)/6; l[i]=.5; points.append((l[1:],.45))
    total=0.; perbody={}; min_jac=np.inf
    for start in range(0,len(ec),10000):
        x=xyz[ec[start:start+10000]-1]; volumes=np.zeros(len(x))
        for q,w in points:
            _,dn=basis(q); jac=np.einsum('kni,nj->kij',x,dn); det=np.linalg.det(jac)
            min_jac=min(min_jac,float(det.min())); volumes+=w*det/6
        if np.any(volumes<=0): raise RuntimeError('Nonpositive element volumes')
        total+=float(volumes.sum())
        for label in np.unique(labels[start:start+len(x)]):
            perbody[str(label)]=perbody.get(str(label),0.)+float(volumes[labels[start:start+len(x)]==label].sum())
    masses=list(csv.DictReader((ROOT/'masas_geometricas.csv').open()))
    cad=float(next(r for r in masses if float(r['thickness_mm'])==t)['sum_volume_mm3'])
    result=dict(mesh_volume_mm3=total,CAD_sum_volume_mm3=cad,relative_volume_error=(total-cad)/cad,
                mesh_mass_kg=total*2.7e-6,body_volumes_mm3=perbody,min_determinant_5_quadrature_points=min_jac)
    result['passed']=bool(abs(result['relative_volume_error'])<.002 and min_jac>0)
    (folder/'volumen_malla.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); a=p.parse_args(); main(a.t,a.h)
