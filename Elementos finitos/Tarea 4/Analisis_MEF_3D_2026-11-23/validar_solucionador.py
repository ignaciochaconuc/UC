"""Ensayo independiente de parche: cubo 1 mm, compresión uniforme 1 MPa.
Comprueba C3D10, unidades y recuperación de reacciones mediante nodos auxiliares.
No sustituye las simulaciones del cuadro.
"""
import json
import subprocess
import os
import numpy as np
import gmsh
from inspeccionar import ROOT
from postprocesar import parse_dat

folder=ROOT/'verificacion_cubo'; folder.mkdir(exist_ok=True)
gmsh.initialize(); gmsh.option.setNumber('General.Terminal',0); gmsh.model.add('cube'); gmsh.model.occ.addBox(0,0,0,1,1,1); gmsh.model.occ.synchronize()
gmsh.option.setNumber('Mesh.MeshSizeMax',.5); gmsh.model.mesh.generate(3); gmsh.model.mesh.setOrder(2)
ids,coords,_=gmsh.model.mesh.getNodes(); coords=np.array(coords).reshape(-1,3); conv={int(n):k+1 for k,n in enumerate(ids)}
types,eids,conn=gmsh.model.mesh.getElements(3); _,_,_,_,local,_=gmsh.model.mesh.getElementProperties(types[0]); local=np.array(local).reshape(-1,3)
target=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]])
perm=[int(np.argmin(np.linalg.norm(local-x,axis=1))) for x in target]
ec=np.array([[conv[int(n)] for n in row] for row in np.array(conn[0]).reshape(-1,10)[:,perm]])
forces={}
for _,f in gmsh.model.getEntities(2):
    center=gmsh.model.occ.getCenterOfMass(2,f)
    if abs(center[0]-1)>1e-8: continue
    ts,es,cs=gmsh.model.mesh.getElements(2,f)
    for tri in np.array(cs[0]).reshape(-1,6):
        ns=[conv[int(n)] for n in tri]; x=coords[np.array(ns)-1]; area=np.linalg.norm(np.cross(x[1]-x[0],x[2]-x[0]))/2
        for n in ns[3:]: forces[n]=forces.get(n,0)-area/3
gmsh.finalize()
supports=[]
for node,p in enumerate(coords,1):
    for k in range(3):
        if abs(p[k])<1e-8: supports.append((node,k,len(coords)+len(supports)+1))
with (folder/'cubo.inp').open('w') as out:
    out.write('*NODE,NSET=PHYSICAL\n')
    for i,p in enumerate(coords,1): out.write(str(i)+','+','.join(str(v) for v in p)+'\n')
    out.write('*NODE,NSET=REACTIONS\n')
    for node,k,dummy in supports: out.write(f'{dummy},0,0,0\n')
    out.write('*ELEMENT,TYPE=C3D10,ELSET=ALL\n')
    for i,row in enumerate(ec,1): out.write(str(i)+','+','.join(str(n) for n in row)+'\n')
    out.write('*MATERIAL,NAME=AL\n*ELASTIC\n68900,0.33\n*SOLID SECTION,ELSET=ALL,MATERIAL=AL\n')
    for node,k,dummy in supports: out.write(f'*EQUATION\n2\n{node},{k+1},1.,{dummy},1,-1.\n')
    out.write('*BOUNDARY\nREACTIONS,1,3,0\n*STEP\n*STATIC,SOLVER=PARDISO\n*CLOAD\n')
    for n,f in forces.items(): out.write(f'{n},1,{f}\n')
    out.write('*NODE PRINT,NSET=REACTIONS\nRF\n*NODE PRINT,NSET=PHYSICAL\nU\n*EL PRINT,ELSET=ALL\nS\n*END STEP\n')
official=list((ROOT/'herramientas'/'oficial_2.24').rglob('ccx_i4.exe'))
exe=official[0] if official else next((ROOT/'herramientas').rglob('ccx.exe'))
env=os.environ.copy(); env['PATH']=str(ROOT/'herramientas'/'mkl_runtime')+os.pathsep+env['PATH']; env['OMP_NUM_THREADS']='4'; env['MKL_NUM_THREADS']='4'
with (folder/'calculix.log').open('w') as log: subprocess.run([str(exe),'-i','cubo'],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
u,rf,smax,loc=parse_dat(folder/'cubo.dat',len(coords))
expected=coords*np.array([-1.,.33,.33])/68900
reaction=np.zeros(3)
for node,k,dummy in supports: reaction[k]+=rf[dummy][0]
error=float(np.max(np.abs(u-expected))); balance=reaction+np.array([sum(forces.values()),0,0])
result=dict(executable=str(exe),max_absolute_displacement_error_mm=error,stress_max_MPa=smax,expected_stress_MPa=1.,reaction_N=reaction.tolist(),equilibrium_residual_N=balance.tolist())
result['passed']=bool(error<1e-9 and abs(smax-1)<1e-4 and np.linalg.norm(balance)<1e-5)
(folder/'validacion.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if not result['passed']: raise RuntimeError('Cube validation failed')
