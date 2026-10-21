"""Pruebas elementales y de integridad de la etapa 4D, sin re-ejecutar FEM completo."""
import numpy as np,pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from simulacion_4D import (mesh_surface,volume_mesh,element_stress,
                           forces_at_event,get_events,stiffness_matrix,R_IN,R_OUT,R_HOLE,H,E,NU)
from pathlib import Path
base=Path(__file__).resolve().parent
holes=pd.read_csv(base/'fuentes/agujeros_matriz_CAD.csv').sort_values('id')[['x_mm','y_mm']].to_numpy()
xy,tri,rings=mesh_surface(holes,5.5)
assert len(holes)==102
assert len(np.unique(rings[:,1]))==102
rows=np.r_[tri[:,0],tri[:,1],tri[:,2],tri[:,1],tri[:,2],tri[:,0]]
cols=np.r_[tri[:,1],tri[:,2],tri[:,0],tri[:,0],tri[:,1],tri[:,2]]
G=coo_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(xy),len(xy))).tocsr()
ncomps,_=connected_components(G)
assert ncomps==1
pts,tets=volume_mesh(xy,tri,2)
# approximate sum of volume via TET, no need assemble full matrix
p=pts[tets];det=np.linalg.det(np.stack([p[:,1]-p[:,0],p[:,2]-p[:,0],p[:,3]-p[:,0]],axis=2))
vol=np.abs(det).sum()/6
ref=np.pi*(R_OUT**2-R_IN**2-len(holes)*R_HOLE**2)*H
assert abs(vol-ref)/ref<.012, (vol,ref)
# linear displacement field must reproduce constant stress exactly (patch test)
one=tets[:300];pp=pts[one];mat=np.concatenate([np.ones((len(one),4,1)),pp],axis=2)
inv=np.linalg.inv(mat);grads=inv[:,1:,:].transpose(0,2,1)
U=np.zeros_like(pts); eps=1e-4;U[:,0]=eps*pts[:,0]
sigma,vm=element_stress(one,grads,U.ravel())
la=E*NU/((1+NU)*(1-2*NU));mu=E/(2*(1+NU))
assert np.max(abs(sigma[:,0,0]-(la+2*mu)*eps))<1e-7
assert np.max(abs(sigma[:,1,1]-la*eps))<1e-7
assert np.max(abs(sigma[:,0,1]))<1e-7
forces,hist=get_events()
for event in ('max_fuerza_total','max_momento_normales'):
 f,out=forces_at_event(pts,xy,tri,holes,event,hist,forces)
 assert abs(out['F_model_N']-out['F_3C_N'])<1e-5
 assert abs(out['T_model_Nm']-out['T_3C_Nm'])<1e-8
 assert abs(np.hypot(out['Mx_mat_Nm'],out['My_mat_Nm'])-out['M_normales_Nm'])<0.15
# existing solution residuals and force equilibrium
for ds in ('7.5','5.5','4'):
 results=pd.read_csv(base/'resultados'/f'resultados_FEM_p{ds}.csv')
 assert len(results)==4
 assert all(results.cg_info==0)
 assert all(results.relative_force_residual<1e-6)
 assert np.max(abs(results.F_model_N-results.F_3C_N))<1e-5
 assert np.max(abs(results.T_model_Nm-results.T_3C_Nm))<1e-6
 assert np.max(abs(results.reaction_z_N-results.F_model_N))<2e-1
print('Correcto: 102 perforaciones, malla conectada, volumen, campo afín 3D, F/T correlacionados, 12 soluciones y equilibrio.')
