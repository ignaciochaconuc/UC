#!/usr/bin/env python3
"""Etapa 4D: FEA 3D lineal de cribado para matriz peletizadora.
Modelo paramétrico deliberadamente simplificado: placa uniforme con 102 perforaciones
pasantes Ø6; no incorpora avellanados Ø9, chavetero, collar Ø58 real ni contacto unilateral.
Fuentes 3C/4A se copian sin cambios a fuentes/. Unidades: N, mm, MPa.
Requiere numpy, scipy, pandas, matplotlib.
"""
from pathlib import Path
import argparse, json, time
import numpy as np, pandas as pd
from scipy.spatial import Delaunay, cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg, LinearOperator, spsolve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'fuentes'
OUT=ROOT/'resultados'
OUT.mkdir(exist_ok=True)
E=210000.0; NU=0.30
H=36.0; R_OUT=100.; R_IN=25.; R_HOLE=3.; R_SUPPORT=29.; R_LOAD=5.5
S_Y_REFERENCE=340.0 # Atlas1045 +QT, round bar >100 to 250 mm: material coupon only, no design certification


def circles_points(radius,n,xc=0.,yc=0.,phase=0.):
    theta=np.linspace(0,2*np.pi,n,endpoint=False)+phase
    return np.c_[xc+radius*np.cos(theta),yc+radius*np.sin(theta)]


def mesh_surface(holes,ds):
    """Delaunay punctured polygon mesh from CAD centers, explicit hole boundary points."""
    pts=[]; hole_ids=[]
    for radius in (R_IN, 27., R_SUPPORT, R_OUT):
        n=max(28, int(np.ceil(2*np.pi*radius/(ds*0.72))))
        pts.extend(circles_points(radius,n).tolist())
    for ci,(xc,yc) in enumerate(holes):
        n=14 if ds<=5.5 else 12
        p=circles_points(R_HOLE,n,xc,yc)
        for xy in p:
            hole_ids.append((len(pts),ci))
            pts.append(xy.tolist())
        pts.extend(circles_points(R_LOAD,n,xc,yc).tolist())
    xg=np.arange(-R_OUT+ds/2,R_OUT,ds)
    X,Y=np.meshgrid(xg,xg)
    g=np.c_[X.ravel(),Y.ravel()]
    r=np.linalg.norm(g,axis=1)
    tree=cKDTree(holes)
    nearest=tree.query(g)[0]
    keep=(r>R_IN+ds*.47)&(r<R_OUT-ds*.30)&(nearest>R_HOLE+ds*.50)
    pts.extend(g[keep].tolist())
    xy=np.asarray(pts,dtype=float)
    tri=Delaunay(xy).simplices
    centroid=xy[tri].mean(axis=1)
    cc=np.linalg.norm(centroid,axis=1)
    keep=(cc>R_IN-0.20)&(cc<R_OUT+0.02)
    # cut holes with a centroid and three edge midpoint tests
    for f in (.5,):
        p=xy[tri]
        checks=[centroid,(p[:,0]+p[:,1])*f,(p[:,1]+p[:,2])*f,(p[:,2]+p[:,0])*f]
        for coords in checks:
            near=tree.query(coords)[0]
            keep &= near>R_HOLE*np.cos(np.pi/(14 if ds<=5.5 else 12))-0.07
    tri=tri[keep]
    # enforce triangle handedness and remove tiny triangles
    cr=(xy[tri[:,1],0]-xy[tri[:,0],0])*(xy[tri[:,2],1]-xy[tri[:,0],1])-(xy[tri[:,1],1]-xy[tri[:,0],1])*(xy[tri[:,2],0]-xy[tri[:,0],0])
    tri[cr<0,1],tri[cr<0,2]=tri[cr<0,2].copy(),tri[cr<0,1].copy()
    tri=tri[np.abs(cr)>1e-6]
    used=np.unique(tri.ravel())
    remap=np.full(len(xy),-1,dtype=np.int32);remap[used]=np.arange(len(used))
    rings=np.array([[remap[i],h] for i,h in hole_ids if remap[i]>=0],dtype=np.int32)
    return xy[used],remap[tri],rings


def volume_mesh(xy,tri,nlayers):
    n=len(xy)
    points=np.concatenate([np.c_[xy,np.full(n,H*k/nlayers)] for k in range(nlayers+1)])
    tri=np.sort(tri,axis=1)
    tetra=[]
    for k in range(nlayers):
        a,b,c=(tri+k*n).T
        A,B,C=(tri+(k+1)*n).T
        tetra.append(np.column_stack((a,b,c,C)))
        tetra.append(np.column_stack((a,b,B,C)))
        tetra.append(np.column_stack((a,A,B,C)))
    tets=np.vstack(tetra).astype(np.int32)
    return points,tets


def stiffness_matrix(pts,tets,E=E,nu=NU,chunk=1600):
    from scipy.sparse import coo_matrix
    n=len(pts); n3=n*3
    lam=E*nu/((1+nu)*(1-2*nu)); mu=E/(2*(1+nu))
    rows=[];cols=[];data=[];volumes=[]; allgrads=[]
    eye=np.eye(3)
    for start in range(0,len(tets),chunk):
        tet=tets[start:start+chunk]
        p=pts[tet]
        V=np.concatenate([np.ones((len(tet),4,1)),p],axis=2) # Nt,4 nodes,4 polynomials
        det=np.linalg.det(V)
        if np.any(abs(det)<1e-7):
            raise RuntimeError('Tet degenerado')
        vols=abs(det)/6
        inv=np.linalg.inv(V)
        grads=inv[:,1:,:].transpose(0,2,1) # Nt, 4 nodes,3 spatial derivatives
        allgrads.append(grads)
        volumes.append(vols)
        # K_iα,jβ = λ g_iα g_jβ + μ g_jα g_iβ + μ deltaαβ gi.gj
        gg=np.einsum('nia,nja->nij',grads,grads)
        K=(lam*np.einsum('nia,njb->niajb',grads,grads)
           +mu*np.einsum('nja,nib->niajb',grads,grads)
           +mu*np.einsum('nij,ab->niajb',gg,eye)) * vols[:,None,None,None,None]
        # indexing second μ term: should ∂β Ni ∂α Nj, i.e grads[i,b]*grads[j,a]
        # Above term is grads[j,a]*grads[i,b], correct.
        dof=(tet[:,:,None]*3+np.arange(3)[None,None,:]).reshape(-1,12)
        rows.append(np.broadcast_to(dof[:,:,None],(len(tet),12,12)).ravel().astype(np.int32))
        cols.append(np.broadcast_to(dof[:,None,:],(len(tet),12,12)).ravel().astype(np.int32))
        data.append(K.reshape(-1))
    A=coo_matrix((np.concatenate(data),(np.concatenate(rows),np.concatenate(cols))),shape=(n3,n3)).tocsr()
    A.sum_duplicates()
    return A,np.vstack(allgrads),np.concatenate(volumes)


def get_events():
    df=pd.read_csv(SOURCE/'fuerzas_por_agujero_4A.csv')
    hist=pd.read_csv(SOURCE/'historial_4A.csv')
    return df,hist


def forces_at_event(pts,xy,tri,holes,event,source_hist,source_forces):
    """Equivalent traction over top *solid* annulus 3<r<5.5 mm around each hole.
    Exactly preserves hole forces and the original resisting torque (within numerical tolerance).
    This load patch geometry is a sensitivity assumption, not measured pressure.
    """
    a=source_forces[source_forces.evento==event].copy()
    if len(a)==0: raise ValueError(event)
    step=int(a.paso.iloc[0]);h=source_hist[source_hist.paso==step].iloc[0]
    agg=a.groupby('id_agujero')['fuerza_normal_N'].sum()
    ct=xy[tri].mean(axis=1)
    edges=xy[tri]
    e1=edges[:,1]-edges[:,0];e2=edges[:,2]-edges[:,0]
    area=np.abs(e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0])/2
    tree=cKDTree(holes)
    dst,nearest=tree.query(ct)
    allpatch=(dst<=R_LOAD+0.01)&(dst>=R_HOLE-0.3)
    patches={}
    for i in agg.index:
        inds=np.where(allpatch&(nearest==int(i)-1))[0]
        if len(inds)==0:raise RuntimeError(f'No hay area de parche {i}')
        areas=area[inds]
        weights=np.bincount(tri[inds].ravel(),weights=np.repeat(areas/3,3),minlength=len(xy))
        weights/=weights.sum()
        patches[int(i)]=(weights,holes[int(i)-1])
    # Normalize torque using actual FE nodal positions, not just theoretical hole centers.
    torquebase=0
    for id,F in agg.items():
        w,c=patches[int(id)];r=np.hypot(*c)
        tx,ty=c[1]/r,-c[0]/r
        torquebase += F*(np.sum((xy[:,0]*ty-xy[:,1]*tx)*w)) # N.mm
    scale=abs(float(h.T_resistente_3C_Nm)*1000 / torquebase)
    f=np.zeros(len(pts)*3); nxy=len(xy); top_offset=len(pts)-nxy
    for id,F in agg.items():
        w,c=patches[int(id)];r=np.hypot(*c)
        tx,ty=c[1]/r,-c[0]/r
        idx=np.flatnonzero(w>0); ni=idx+top_offset
        f[3*ni+0]+=F*scale*tx*w[idx]
        f[3*ni+1]+=F*scale*ty*w[idx]
        f[3*ni+2]-=F*w[idx]
    nodal=f.reshape(-1,3)
    R=nodal.sum(axis=0)
    Mz=(pts[:,0]*nodal[:,1]-pts[:,1]*nodal[:,0]).sum()/1000
    Mx=(pts[:,1]*nodal[:,2]).sum()/1000
    My=-(pts[:,0]*nodal[:,2]).sum()/1000
    return f,dict(event=event,step=step,angle_deg=float(h.angulo_grados),
      F_model_N=-float(R[2]),F_3C_N=float(h.Fz_normal_N),T_model_Nm=abs(float(Mz)),T_3C_Nm=float(h.T_resistente_3C_Nm),Fx_model_N=float(R[0]),Fy_model_N=float(R[1]),Mx_mat_Nm=float(Mx),My_mat_Nm=float(My),My_Nm=float(h.My_normales_Nm),Mx_Nm=float(h.Mx_normales_Nm),M_normales_Nm=float(h.M_flexion_normales_Nm))


def constrained_dofs(pts,mode):
    rr=np.hypot(pts[:,0],pts[:,1])
    bottom=np.isclose(pts[:,2],0.)&(rr<=R_SUPPORT+0.15)&(rr>=R_IN-0.15)
    if mode=='EMPOTRADO_ANILLO':
        return np.unique((np.where(bottom)[0][:,None]*3+np.arange(3)[None,:]).ravel())
    if mode=='APOYO_Z_CHAVETA':
        # Bottom annular collar offers vertical reaction; key sector restrains inplane
        alpha=np.mod(np.arctan2(pts[:,1],pts[:,0])+np.pi,2*np.pi)-np.pi
        key=(rr<=R_IN+0.12)&(np.abs(alpha)<np.deg2rad(18))
        widx=np.where(bottom)[0]*3+2
        uv=(np.where(key)[0][:,None]*3+np.arange(2)[None,:]).ravel()
        return np.unique(np.r_[widx,uv])
    raise ValueError(mode)


def solve_static(A,forces,fix,tol=4e-8,maxiter=4200):
    free=np.ones(len(forces),dtype=bool); free[fix]=False
    rhs=forces[free]
    Af=A[free][:,free].tocsr()
    diag=Af.diagonal();diag=np.maximum(diag,1e-14)
    M=LinearOperator(Af.shape,matvec=lambda x:x/diag)
    count=0
    def cb(x):
        nonlocal count; count+=1
    x,info=cg(Af,rhs,M=M,rtol=tol,atol=1e-8,maxiter=maxiter,callback=cb)
    u=np.zeros(len(forces));u[free]=x
    residual=Af @ x-rhs
    return u,{'cg_info':int(info),'iterations':count,'relative_force_residual':float(np.linalg.norm(residual)/(np.linalg.norm(rhs)+1e-12))},(A@u-forces)


def element_stress(tets,grads,u,E=E,nu=NU):
    uu=u.reshape(-1,3)[tets]
    grad_u=np.einsum('nia,nib->nab',uu,grads) # first displacement index a, derivative b
    strain=.5*(grad_u+grad_u.transpose(0,2,1))
    lam=E*nu/((1+nu)*(1-2*nu));mu=E/(2*(1+nu))
    sigma=lam*np.trace(strain,axis1=1,axis2=2)[:,None,None]*np.eye(3)[None,:,:]+2*mu*strain
    sx,sy,sz=sigma[:,0,0],sigma[:,1,1],sigma[:,2,2]
    vm=np.sqrt(.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(sigma[:,0,1]**2+sigma[:,1,2]**2+sigma[:,0,2]**2))
    return sigma,vm


def run(args):
    times={};start=time.perf_counter()
    cad=pd.read_csv(SOURCE/'agujeros_matriz_CAD.csv').sort_values('id')
    holes=cad[['x_mm','y_mm']].to_numpy()
    xy,tri,rings=mesh_surface(holes,args.paso)
    pts,tets=volume_mesh(xy,tri,args.capas)
    # sanity: hole ring top mapping assumes xy vertices indexed before extruding
    np.savez_compressed(OUT/f'malla_p{args.paso:g}_c{args.capas}.npz',xy=xy,tri=tri,points=pts,tets=tets)
    print('MALLA',args.paso,len(xy),len(tri),len(pts),len(tets),'rings',len(rings),flush=True)
    A,grads,vols=stiffness_matrix(pts,tets)
    print('ENSAMBLE',A.nnz, 'volume mesh',vols.sum(), 'time',time.perf_counter()-start,flush=True)
    forces,hist=get_events()
    results=[]
    for mode in args.apoyos:
        fix=constrained_dofs(pts,mode)
        for event in args.eventos:
            fb,load=forces_at_event(pts,xy,tri,holes,event,hist,forces)
            u,diagnostic,reaction=solve_static(A,fb,fix)
            sigma,vm=element_stress(tets,grads,u)
            center=pts[tets].mean(axis=1)
            rr=np.linalg.norm(center[:,:2],axis=1)
            valid=(rr>34)&(rr<95)
            umax=np.max(np.linalg.norm(u.reshape(-1,3),axis=1))
            wmax=np.max(abs(u[2::3]))
            peak=np.max(vm);peak_bulk=np.max(vm[valid]);p95=float(np.percentile(vm[valid],95))
            idx=np.argmax(vm[valid]);imax=np.where(valid)[0][idx]
            idxglobal=int(np.argmax(vm));i=idxglobal
            reactions=np.sum(reaction.reshape(-1,3),axis=0)
            bottom_idx=np.where(np.isclose(pts[:,2],0.) & (np.hypot(pts[:,0],pts[:,1])<=R_SUPPORT+.15))[0]
            rz=reaction.reshape(-1,3)[bottom_idx,2]
            neg_react_N=float(-np.minimum(rz,0).sum())
            pos_react_N=float(np.maximum(rz,0).sum())
            out={**load,**diagnostic, "mode":mode,"step_mesh_mm":args.paso,"layers":args.capas,"n_vertices":len(pts),"n_tets":len(tets),"volume_mm3":float(vols.sum()),"umax_mm":float(umax),"wmax_mm":float(wmax),"vm_max_MPa":float(peak),"vm_max_excl_hub_MPa":float(peak_bulk),"vm_p95_excl_hub_MPa":p95,"critical_x_mm":float(center[imax,0]),"critical_y_mm":float(center[imax,1]),"critical_z_mm":float(center[imax,2]),"reaction_x_N":float(reactions[0]),"reaction_y_N":float(reactions[1]),"reaction_z_N":float(reactions[2]),"reaction_z_negative_support_N":neg_react_N,"reaction_z_positive_support_N":pos_react_N,"relative_energy_balance":float((u@ (A@u))/(u@fb+1e-20)),"n_screen_1045_340MPa":float(S_Y_REFERENCE/peak_bulk)}
            results.append(out)
            print(mode,event,'VM',round(peak,2),'VM excl hub',round(peak_bulk,2),'w',round(wmax,5),'negative contact',round(neg_react_N),'iter',diagnostic['iterations'],'err',diagnostic['relative_force_residual'],flush=True)
            # Plot element scalar top surface by tetra centroid near upper z
            upper=center[:,2]>H-H/max(1,args.capas)*.66
            fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
            m=ax.tripcolor(center[upper,0],center[upper,1],vm[upper],shading='gouraud',cmap='Greys',vmin=0,vmax=np.quantile(vm[upper],.98)) if False else ax.scatter(center[upper,0],center[upper,1],c=vm[upper],s=5,cmap='Greys',vmin=0,vmax=np.quantile(vm[upper],.98),rasterized=True)
            fig.colorbar(m,ax=ax,label='von Mises [MPa] — centroides de tetraedros')
            th=np.linspace(0,2*np.pi,240)
            for xx,yy in holes:
                ax.plot(xx+3*np.cos(th),yy+3*np.sin(th),c='black',lw=.18,alpha=.6)
            for r in [R_IN,R_OUT]:ax.plot(r*np.cos(th),r*np.sin(th),c='black',lw=.7)
            ax.set_aspect('equal');ax.set_xlabel('x de la matriz [mm]');ax.set_ylabel('y [mm]')
            ax.set_title(f'{event} | {mode}\nMalla simplificada, no validación de diseño',fontsize=10)
            fig.savefig(OUT/f'vm_{mode}_{event}_p{args.paso:g}.png',dpi=155)
            plt.close(fig)
    res=pd.DataFrame(results)
    res.to_csv(OUT/f'resultados_FEM_p{args.paso:g}.csv',index=False)
    report={'model':'elasticidad 3D tetra P1, perforaciones Ø6 sin avellanados Ø9 ni chavetero, matriz uniforme h=36. Fuerzas sobre coronas superiores de radio 3 a 5.5mm.','status':'preliminar, no validación de tensión máxima local ni FS definitivo','E_MPa':E,'nu':NU,'mesh_step_mm':args.paso,'n_layers':args.capas,'n_vertices':len(pts),'n_tetra':len(tets),'volume_mesh_mm3':vols.sum(),'time_sec':time.perf_counter()-start,'cases':results}
    (OUT/f'metadata_FEM_p{args.paso:g}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    return res

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--paso',type=float,default=5.5)
    p.add_argument('--capas',type=int,default=2)
    p.add_argument('--apoyos',nargs='+',default=['EMPOTRADO_ANILLO','APOYO_Z_CHAVETA'])
    p.add_argument('--eventos',nargs='+',default=['max_fuerza_total','max_momento_normales'])
    run(p.parse_args())
