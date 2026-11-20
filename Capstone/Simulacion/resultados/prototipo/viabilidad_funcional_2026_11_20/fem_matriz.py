"""Elasticidad 3D de la matriz STEP, sin modificar CAD ni contacto 3C.

N/mm/MPa. Geometría exacta importada por OCC; tetraedros P1 y refinamiento.
Modelo condicionado a fijación adherente bilateral en cara real de arandela.
Las fuerzas por canal se recuperan de las holguras guardadas, sin iteración.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from calculos import D,S,entradas,guardar,conservar
import sys,math,time,argparse,json
import numpy as np
import pandas as pd
import gmsh
import pyamg
from scipy.sparse.linalg import cg
from scipy.optimize import least_squares
from skfem import MeshTet,Basis,ElementVector,ElementTetP1,asm
from skfem.models.elasticity import linear_elasticity


def recuperar_cargas(row,a,holes):
    # Importar solo funciones puras EP2, nunca ModeloAcoplado ni su simular().
    from peletizadora.legado import coordenadas_locales
    from modelos.superposicion_variable import interseccion_disco_huella_variable
    xy=holes[['x_mm','y_mm']].to_numpy()/1000;theta=math.radians(row.angulo_grados)
    co=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
    xy_rot=xy@co.T;F=np.zeros(len(holes));CX=np.zeros((len(holes),2))
    for j,r in enumerate(a['rodillos'],1):
        loc=coordenadas_locales(xy_rot,r['angulo_rad']);rc=r['radio_posicion_mm']/1000
        area,cr,ct=interseccion_disco_huella_variable(loc,.003,(rc-.015,rc+.015),
            row[f'holgura_r{j}_centro_m'],row[f'inclinacion_radial_r{j}_rad'],rc,.052,.004,64)
        f=2258670.6718785944*area;phi=r['angulo_rad']
        centroides=np.column_stack([cr*np.cos(phi)-ct*np.sin(phi),cr*np.sin(phi)+ct*np.cos(phi)])@co
        centroides[~np.isfinite(centroides)]=0
        CX+=f[:,None]*centroides;F+=f
    mask=F>1e-10
    CX[mask]/=F[mask,None]
    if abs(F.sum()-row.fuerza_total_n)>2e-4:raise ValueError('La recuperación de cargas no reproduce el estado guardado')
    torque=.1*np.dot(F,np.linalg.norm(xy,axis=1))
    if abs(torque-row.torque_total_nm)>1e-6:raise ValueError('Torque de canales no conservado')
    return F,CX*1000


def malla(h):
    if not math.isfinite(h) or h<=0:raise ValueError('Tamaño de malla finito y positivo en mm')
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
    gmsh.option.setNumber('General.NumThreads',1)
    gmsh.model.occ.importShapes(str(S/'geometrias/Matriz_prototipo.stp'));gmsh.model.occ.synchronize()
    surfs=gmsh.model.getEntities(2)
    soporte=[t for d,t in surfs if gmsh.model.getType(d,t)=='Plane'
             and abs(gmsh.model.occ.getCenterOfMass(d,t)[1]-26)<1e-5]
    if len(soporte)!=1:raise ValueError('No se identificó cara plana real de apoyo')
    area=gmsh.model.occ.getMass(2,soporte[0])
    if not np.isclose(area,math.pi*(11.5**2-6.5**2),rtol=1e-7):raise ValueError('Área de apoyo inesperada')
    gmsh.option.setNumber('Mesh.MeshSizeMax',h);gmsh.option.setNumber('Mesh.MeshSizeMin',h*.32)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',max(16,round(44/h)))
    gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',1)
    gmsh.model.mesh.setSize(gmsh.model.getEntities(0),h)
    gmsh.model.mesh.generate(3)
    tags,coords,_=gmsh.model.mesh.getNodes();xyz=coords.reshape(-1,3)
    mapid=np.full(int(tags.max())+1,-1,dtype=int);mapid[tags]=np.arange(len(tags))
    types,_,nodes=gmsh.model.mesh.getElements(3)
    tet=mapid[nodes[int(np.flatnonzero(np.asarray(types)==4)[0])].reshape(-1,4)]
    gmsh.finalize()
    mesh=MeshTet(xyz.T,tet.T)
    return mesh


def gradientes(mesh):
    p=mesh.p.T[mesh.t.T]
    A=np.concatenate([np.ones((*p.shape[:2],1)),p],axis=2)
    grads=np.linalg.inv(A)[:,1:,:].transpose(0,2,1)
    volumes=abs(np.linalg.det(A))/6
    return grads,volumes


def tensiones(mesh,uv,E=200000.,nu=.30):
    grads,_=gradientes(mesh);mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu))
    grad=np.einsum('eia,eib->eab',uv[mesh.t.T],grads)
    strain=(grad+grad.transpose(0,2,1))/2
    stress=2*mu*strain+lam*np.trace(strain,axis1=1,axis2=2)[:,None,None]*np.eye(3)
    dev=stress-np.trace(stress,axis1=1,axis2=2)[:,None,None]*np.eye(3)/3
    return stress,np.sqrt(1.5*np.sum(dev*dev,axis=(1,2)))


def fuerzas(mesh,F,CX,holes):
    p=mesh.p.T;fac=mesh.facets[:,mesh.boundary_facets()].T
    ctr=p[fac].mean(axis=1);areas=np.linalg.norm(np.cross(p[fac[:,1]]-p[fac[:,0]],p[fac[:,2]]-p[fac[:,0]]),axis=1)/2
    hxy=holes[['x_mm','y_mm']].to_numpy();out=np.zeros_like(p);diagn=[]
    # Algunos centroides individuales del legado caen fuera del círculo.
    # No se interpretan como puntos físicos: conservar Fi y primer momento
    # GLOBAL, mediante un pequeño desplazamiento común de las tracciones.
    desplazamiento=(np.sum(F[:,None]*CX,axis=0)-np.sum(F[:,None]*hxy,axis=0))/F.sum()
    for i,fi in enumerate(F):
        if fi<1e-10:continue
        xc,yc=hxy[i];zc=-yc
        # Una cara triangular de la pared puede tener centroide dentro del cilindro.
        radnodes=np.hypot(p[fac,0]-xc,p[fac,2]-zc)
        wall=np.all(abs(radnodes-3)<2e-5,axis=1)&(ctr[:,1]>=-1e-6)&(ctr[:,1]<=10+1e-6)
        tr=fac[wall];ar=areas[wall]
        if not len(tr):raise ValueError('Canal sin pared mallada')
        w=np.bincount(tr.ravel(),weights=np.repeat(ar/3,3),minlength=len(p));ids=np.flatnonzero(w)
        base=w[ids]/w.sum();xy=p[ids][:,[0,2]]
        destino=hxy[i]+desplazamiento;target=np.array([destino[0],-destino[1]])
        loc=(xy-np.array([xc,zc]))/3;targetloc=(target-np.array([xc,zc]))/3
        # Distribución positiva sobre la pared que conserva primer momento normal.
        def prob(lam):
            ex=loc@lam;ex-=ex.max();z=base*np.exp(ex);return z/z.sum()
        fit=least_squares(lambda l:prob(l)@loc-targetloc,np.zeros(2),max_nfev=100,
                          ftol=1e-12,xtol=1e-12,gtol=1e-12)
        wn=prob(fit.x);err=np.linalg.norm(wn@xy-target)
        if err*fi>1e-3:raise ValueError(f'No se conserva centroide canal {i}: Nmm={err*fi}')
        out[ids,1]+=fi*wn
        # Tangente aplicada con distribución simétrica de pared. Torque se normaliza globalmente.
        r=math.hypot(xc,zc);out[ids,0]+= .1*fi*(zc/r)*base
        out[ids,2]+=-.1*fi*(xc/r)*base
        diagn.append(dict(id=int(holes.id.iloc[i]),F_n=fi,error_centroide_mm=err,
            desplazamiento_equivalente_x_mm=desplazamiento[0],desplazamiento_equivalente_y_mm=desplazamiento[1],
            distancia_centroide_individual_legado_al_centro_mm=float(np.linalg.norm(CX[i]-hxy[i])),
            centroide_individual_legado_fuera_agujero=bool(np.linalg.norm(CX[i]-hxy[i])>3.0001)))
    torque=np.sum(p[:,2]*out[:,0]-p[:,0]*out[:,2])
    targetT=.1*np.dot(F,np.linalg.norm(hxy,axis=1))
    out[:,[0,2]]*=targetT/torque
    return out,diagn


def ejecutar(h):
    a,df=entradas();ra=json.loads((D/'resumen_analitico.json').read_text(encoding='utf-8'))
    pasos=sorted(set([int(df.loc[df[c].idxmax(),'paso']) for c in ['fuerza_total_n','torque_total_nm','fuerza_r1_n','fuerza_r2_n']]
                     +[ra['matriz']['paso_momento_normales_max']]))
    holes=pd.read_csv(S/'resultados/prototipo/revision_ensamble_2026_11_19/perforaciones_STEP.csv')
    t0=time.monotonic();mesh=malla(h);p=mesh.p.T
    basis=Basis(mesh,ElementVector(ElementTetP1()))
    E=200000.;nu=.30;lam=E*nu/((1+nu)*(1-2*nu));mu=E/(2*(1+nu))
    K=asm(linear_elasticity(lam,mu),basis).tocsr()
    fixed=np.flatnonzero(abs(p[:,1]-26)<1e-6)
    dofs=basis.nodal_dofs[:,fixed].ravel();free=np.setdiff1d(np.arange(basis.N),dofs)
    Kf=K[free][:,free];grads,vols=gradientes(mesh)
    # Modos rígidos para precondicionador de elasticidad.
    B=np.zeros((basis.N,6))
    for j in range(3):B[basis.nodal_dofs[j],j]=1
    for j,e in enumerate(np.eye(3)):
        dis=np.cross(np.tile(e,(len(p),1)),p-p.mean(axis=0))
        for k in range(3):B[basis.nodal_dofs[k],j+3]=dis[:,k]
    ml=pyamg.smoothed_aggregation_solver(Kf,B=B[free],symmetry='symmetric')
    rows=[]
    for paso in pasos:
        row=df.loc[df.paso==paso].iloc[0];F,CX=recuperar_cargas(row,a,holes)
        out,diag=fuerzas(mesh,F,CX,holes);f=np.zeros(basis.N)
        for k in range(3):f[basis.nodal_dofs[k]]=out[:,k]
        its=[0]
        def cb(x):its[0]+=1
        sol,code=cg(Kf,f[free],M=ml.aspreconditioner(),rtol=1e-9,atol=0,maxiter=2000,callback=cb)
        if code:raise ValueError('Solver no convergió '+str(code))
        u=np.zeros(basis.N);u[free]=sol;uv=u[basis.nodal_dofs].T
        react=K@u-f;rf=react[basis.nodal_dofs].T
        stress,vm=tensiones(mesh,uv,E,nu)
        ct=p[mesh.t.T].mean(axis=1);r=np.hypot(ct[:,0],ct[:,2])
        libre=(r>14)&(ct[:,1]<15) # excluye borde de fijación, no perforaciones ni filete del cuerpo.
        plate=ct[:,1]<10
        res=np.linalg.norm(Kf@sol-f[free])/np.linalg.norm(f[free])
        fuerza_err=np.linalg.norm(rf[fixed].sum(axis=0)+out.sum(axis=0))
        momento_err=np.linalg.norm(np.cross(p[fixed],rf[fixed]).sum(axis=0)+np.cross(p,out).sum(axis=0))
        item=dict(h_mm=h,paso=paso,nodos=len(p),tetraedros=mesh.nelements,volumen_mm3=float(vols.sum()),
                  VM_max_MPa=float(vm.max()),VM_fuera_fijacion_MPa=float(vm[libre].max()),
                  VM_placa_perforada_MPa=float(vm[plate].max()),desplazamiento_max_mm=float(np.linalg.norm(uv,axis=1).max()),
                  residuo_relativo=res,error_equilibrio_fuerzas_n=fuerza_err,error_equilibrio_momentos_Nmm=momento_err,
                  reaccion_axial_negativa_n=float(np.maximum(rf[fixed,1],0).sum()),
                  fuerza_aplicada_n=float(out[:,1].sum()),torque_aplicado_Nmm=float(np.cross(p,out).sum(axis=0)[1]),
                  momento_normal_aplicado_Nmm=float(np.linalg.norm(np.cross(p,np.column_stack([np.zeros(len(p)),out[:,1],np.zeros(len(p))])).sum(axis=0))),
                  iteraciones=its[0],segundos=time.monotonic()-t0,
                  n_fluencia_referencia_global=210/float(vm.max()),estado='Condicionado a fijación y propiedades304 de referencia; no contacto no lineal')
        rows.append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
        np.savez_compressed(D/f'fem_h{h:g}_paso{paso}.npz',p=p,tet=mesh.t.T,u=uv,VM=vm,f=out,reacciones=rf)
        pd.DataFrame(diag).to_csv(D/f'cargas_canales_h{h:g}_paso{paso}.csv',index=False)
    pd.DataFrame(rows).to_csv(D/f'fem_h{h:g}.csv',index=False)
    guardar('conservacion_FEM.json',conservar())


if __name__=='__main__':
    import json
    ap=argparse.ArgumentParser();ap.add_argument('--h',type=float,required=True);args=ap.parse_args();ejecutar(args.h)
