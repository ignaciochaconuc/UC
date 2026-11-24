"""Verifica los movimientos locales libres/bloqueados de cada apoyo real."""
import argparse
import json
import numpy as np
from inspeccionar import ROOT

def main(t,h):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'; data=json.loads((ROOT/'inspeccion.json').read_text(encoding='utf-8'))
    supports=json.loads((folder/'apoyos.json').read_text()); grouped={}
    for s in supports: grouped.setdefault((s['solid'],s['node']),[]).append(s)
    max_tangent=0.; max_free_axis=0.; max_orthogonality=0.; ranks={}
    for (solid,node),ss in grouped.items():
        face=data['solids'][solid-1]['faces'][5 if solid in [15,16] else 0]
        axis=np.array(face['axis_direction']); delta=np.array(ss[0]['position'])-np.array(face['axis_origin_mm']); radial=delta-axis*np.dot(delta,axis); radial/=np.linalg.norm(radial)
        tangent=np.cross(axis,radial); c=np.array([s['direction'] for s in ss]); rank=int(np.linalg.matrix_rank(c))
        expected=2 if solid==16 else 1
        if rank!=expected: raise RuntimeError('Incorrect local support rank')
        ranks[str(solid)]=rank; max_tangent=max(max_tangent,float(np.max(np.abs(c@tangent))))
        if solid!=16: max_free_axis=max(max_free_axis,float(np.max(np.abs(c@axis))))
        max_orthogonality=max(max_orthogonality,float(np.max(np.abs(c@c.T-np.eye(len(c))))))
    result=dict(local_constraint_ranks=ranks,max_tangential_constraint_residual=max_tangent,max_free_axial_constraint_residual=max_free_axis,max_direction_orthogonality_error=max_orthogonality,
                passed=bool(max_tangent<1e-10 and max_free_axis<1e-10 and max_orthogonality<1e-10))
    (folder/'equivalencia_pasadores.json').write_text(json.dumps(result,indent=2)); print(folder.name,result)
    if not result['passed']: raise RuntimeError('Pin equivalence failed')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); a=p.parse_args(); main(a.t,a.h)
