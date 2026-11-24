"""Diagnóstico independiente por sólido sin fusiones ni reparaciones geométricas.
Uso: python mallar_componentes.py 2.0 4
Mallas no conformes: requieren contactos adheridos antes de cualquier solución.
"""
import argparse
import json
import numpy as np
from OCP.BRepTools import BRepTools
from inspeccionar import *

def main(t,h,only=None,refine=False,curvature=None):
    reader=STEPControl_Reader(); reader.ReadFile(str(ROOT/f'cuadro_t{t:.1f}mm.stp')); reader.TransferRoots()
    solids=list(explore(reader.OneShape(),TopAbs_SOLID))
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'; folder.mkdir(exist_ok=True)
    rows=[]
    curvature=curvature if curvature is not None else 16 if h>=8 else 24 if h>=7 else 32
    target=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]])
    for i,s in enumerate(solids,1):
        if only is not None and i!=only: continue
        path=folder/f'solido_{i:02}.brep'; BRepTools.Write_s(s,str(path))
        for algo in [1,10]:
            gmsh.initialize(); gmsh.model.add(f'SOLID_{i}')
            gmsh.option.setNumber('General.NumThreads',4)
            try:
                gmsh.model.occ.importShapes(str(path)); gmsh.model.occ.synchronize()
                gmsh.option.setNumber('Mesh.MeshSizeMin',h*.15)
                gmsh.option.setNumber('Mesh.MeshSizeMax',h)
                gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',curvature)
                gmsh.option.setNumber('Mesh.Algorithm3D',algo)
                if refine and i==7:
                    gmsh.option.setNumber('Mesh.MeshSizeMin',0.08)
                    field=gmsh.model.mesh.field.add('Ball')
                    for name,value in {'XCenter':-148.55,'YCenter':-323.58,'ZCenter':-34.0,'Radius':.8,'Thickness':2.0,'VIn':.08,'VOut':h}.items():
                        gmsh.model.mesh.field.setNumber(field,name,value)
                    gmsh.model.mesh.field.setAsBackgroundMesh(field)
                gmsh.model.mesh.generate(3); gmsh.model.mesh.setOrder(2)
                gmsh.model.mesh.optimize('HighOrder')
                ids,coords,_=gmsh.model.mesh.getNodes(); coords=np.array(coords).reshape(-1,3)
                types,eids,conn=gmsh.model.mesh.getElements(3)
                if len(types)!=1: raise RuntimeError('Mixed element types')
                name,dim,order,n,local,_=gmsh.model.mesh.getElementProperties(types[0])
                if n!=10: raise RuntimeError('Not tetra10')
                local=np.array(local).reshape(-1,3); perm=[int(np.argmin(np.linalg.norm(local-x,axis=1))) for x in target]
                ec=np.array(conn[0],dtype=np.int64).reshape(-1,10)[:,perm]
                q=np.array(gmsh.model.mesh.getElementQualities([int(e) for e in eids[0]],'minDetJac'))
                surfaces=[]
                for _,f in gmsh.model.getEntities(2):
                    ns,_,_=gmsh.model.mesh.getNodes(2,f,includeBoundary=True)
                    ft,fe,fc=gmsh.model.mesh.getElements(2,f)
                    if len(ft)!=1 or ft[0]!=9: raise RuntimeError('Expected triangle6')
                    surfaces.append(dict(face=f,type=gmsh.model.getType(2,f),nodes=[int(n) for n in ns],
                                         triangles=np.array(fc[0],dtype=np.int64).reshape(-1,6).tolist(),
                                         area=gmsh.model.occ.getMass(2,f),center=list(gmsh.model.occ.getCenterOfMass(2,f))))
                np.savez_compressed(folder/f'solido_{i:02}.npz',nodes=ids,xyz=coords,elements=ec,element_ids=eids[0])
                (folder/f'solido_{i:02}_superficies.json').write_text(json.dumps(surfaces),encoding='utf-8')
                gmsh.write(str(folder/f'solido_{i:02}.msh'))
                row=dict(solid=i,algorithm=algo,curvature_points_per_circle=curvature,nodes=len(ids),elements=len(ec),minDetJac=float(q.min()),nonpositive_Jacobians=int(np.sum(q<=0)),status='valid' if np.all(q>0) else 'invalid')
                rows.append(row); print('RESULT',row,flush=True); gmsh.finalize(); break
            except Exception as exc:
                print('FAILED',i,algo,str(exc),flush=True); gmsh.finalize()
                if algo==10: rows.append(dict(solid=i,status='failed',error=str(exc)))
        (folder/'resumen.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); p.add_argument('--only',type=int); p.add_argument('--refine',action='store_true'); p.add_argument('--curvature',type=int); a=p.parse_args(); main(a.t,a.h,a.only,a.refine,a.curvature)
