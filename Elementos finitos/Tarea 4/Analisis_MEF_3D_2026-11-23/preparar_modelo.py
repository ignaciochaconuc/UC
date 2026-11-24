"""Vínculos adheridos interpolados sobre tetraedros cuadráticos, sin mover nodos.
Verifica partición de unidad y reproducción afín (traslación/rotación rígida).
Las reacciones se recuperan en nodos auxiliares sin elementos.
Uso: python preparar_modelo.py 2.0 6
"""
import argparse
import csv
import json
import time
import numpy as np
from scipy.spatial import cKDTree
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_ON, TopAbs_IN
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.gp import gp_Pnt2d
from inspeccionar import *

EDGES=[(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]
DL=np.array([[-1.,-1.,-1.],[1.,0,0],[0,1.,0],[0,0,1.]])

def face_parameters(shape,points,tol):
    """Analytic distance to plane/cylinder plus classification in trimmed UV face."""
    accepted={}
    for fs in explore(shape,TopAbs_FACE):
        face=TopoDS.Face_s(fs); surf=BRepAdaptor_Surface(face,True); typ=str(surf.GetType())
        if 'Cylinder' in typ:
            geom=surf.Cylinder(); pos=geom.Position(); delta=points-np.array(xyz(pos.Location()))
            xx=delta@np.array(xyz(pos.XDirection())); yy=delta@np.array(xyz(pos.YDirection())); vv=delta@np.array(xyz(pos.Direction()))
            dist=np.abs(np.hypot(xx,yy)-geom.Radius()); uu=np.arctan2(yy,xx)
            umin=surf.FirstUParameter(); umax=surf.LastUParameter()
            uu=umin+np.mod(uu-umin,2*np.pi)
        elif 'Plane' in typ:
            geom=surf.Plane(); pos=geom.Position(); delta=points-np.array(xyz(pos.Location()))
            uu=delta@np.array(xyz(pos.XDirection())); vv=delta@np.array(xyz(pos.YDirection())); dist=np.abs(delta@np.array(xyz(pos.Direction())))
            umin=surf.FirstUParameter(); umax=surf.LastUParameter()
        else: raise RuntimeError(f'Unsupported contact surface {typ}')
        eligible=np.where((dist<=tol)&(uu>=umin-tol)&(uu<=umax+tol)&(vv>=surf.FirstVParameter()-tol)&(vv<=surf.LastVParameter()+tol))[0]
        classifier=BRepClass_FaceClassifier()
        for j in eligible:
            classifier.Perform(face,gp_Pnt2d(float(uu[j]),float(vv[j])),tol)
            if classifier.State() in (TopAbs_ON,TopAbs_IN): accepted[int(j)]=min(accepted.get(int(j),np.inf),float(dist[j]))
    return accepted

def basis(q):
    l=np.r_[1-np.sum(q),q]
    n=np.r_[l*(2*l-1),[4*l[i]*l[j] for i,j in EDGES]]
    dn=np.vstack(((4*l-1)[:,None]*DL,[4*(l[i]*DL[j]+l[j]*DL[i]) for i,j in EDGES]))
    return n,dn

def interpolate(point,body):
    k=min(80,len(body['elements']))
    _,inds=body['tree'].query(point,k=k)
    best=None
    for j in np.atleast_1d(inds):
        x=body['element_xyz'][j]
        try:
            q=np.linalg.solve((x[1:4]-x[0]).T,point-x[0])
            for _ in range(12):
                n,dn=basis(q); residual=n@x-point
                if np.linalg.norm(residual)<1e-9: break
                q-=np.linalg.solve(x.T@dn,residual)
            n,_=basis(q); error=np.linalg.norm(n@x-point)
            if error>1e-7: continue
            l=np.r_[1-q.sum(),q]
            score=np.sum(np.maximum(-l,0))+np.sum(np.maximum(l-1,0))
            if best is None or score<best[0]: best=(score,j,n,error)
            if score<1e-7: break
        except np.linalg.LinAlgError: continue
    if best is None or best[0]>.5 or np.max(np.abs(best[2]))>2.0:
        raise RuntimeError(f'Unreliable bonded interpolation at {point}: {None if best is None else best[0]}')
    _,j,n,error=best
    return body['elements'][j],n,error,best[0]

def interpolate_batch_candidates(point,body):
    """Vectorized inverse mapping; retains the same affine patch and extrapolation gates."""
    _,inds=body['tree'].query(point,k=min(120,len(body['elements'])))
    inds=np.atleast_1d(inds); x=body['element_xyz'][inds]
    q=np.linalg.solve(np.transpose(x[:,1:4]-x[:,0,None],(0,2,1)),(point-x[:,0])[...,None])[...,0]
    l=np.column_stack((1-q.sum(axis=1),q)); score=np.maximum(-l,0).sum(axis=1)+np.maximum(l-1,0).sum(axis=1)
    keep=np.argsort(score)[:24]; inds=inds[keep]; x=x[keep]; q=q[keep]
    for iteration in range(15):
        l=np.column_stack((1-q.sum(axis=1),q))
        n=np.column_stack((l*(2*l-1),*[4*l[:,i]*l[:,j] for i,j in EDGES]))
        dn=np.concatenate(((4*l-1)[:,:,None]*DL[None,:,:],np.stack([4*(l[:,i,None]*DL[j]+l[:,j,None]*DL[i]) for i,j in EDGES],axis=1)),axis=1)
        residual=np.einsum('ki,kij->kj',n,x)-point
        if np.max(np.linalg.norm(residual,axis=1))<1e-9: break
        jac=np.einsum('kni,knj->kij',x,dn)
        q-=np.linalg.solve(jac,residual[...,None])[...,0]
    l=np.column_stack((1-q.sum(axis=1),q)); n=np.column_stack((l*(2*l-1),*[4*l[:,i]*l[:,j] for i,j in EDGES]))
    error=np.linalg.norm(np.einsum('ki,kij->kj',n,x)-point,axis=1)
    score=np.maximum(-l,0).sum(axis=1)+np.maximum(l-1,0).sum(axis=1)
    score[(error>1e-7)|(np.max(np.abs(n),axis=1)>2.)]=np.inf
    j=int(np.argmin(score))
    if not np.isfinite(score[j]) or score[j]>.5: raise RuntimeError(f'Unreliable interpolation at {point}')
    return body['elements'][inds[j]],n[j],float(error[j]),float(score[j])

def load_meshes(folder):
    bodies={}; allxyz=[]; alle=[]; labels=[]; offset=0; eoffset=0
    for i in range(1,17):
        m=np.load(folder/f'solido_{i:02}.npz'); xyz=m['xyz']; ids=m['nodes']
        conv={int(n):k+offset+1 for k,n in enumerate(ids)}
        ec=np.array([[conv[int(n)] for n in row] for row in m['elements']],dtype=np.int64)
        surfaces=json.loads((folder/f'solido_{i:02}_superficies.json').read_text())
        for f in surfaces:
            f['nodes']=[conv[n] for n in f['nodes']]
            f['triangles']=[[conv[n] for n in tri] for tri in f['triangles']]
        exyz=xyz[np.array([[np.where(ids==n)[0][0] for n in row] for row in m['elements']])] if False else None
        exyz=xyz[ec-offset-1]
        boundary=sorted(set(n for f in surfaces for n in f['nodes']))
        bodies[i]=dict(xyz=xyz,elements=ec,surfaces=surfaces,boundary=boundary,
                       element_xyz=exyz,tree=cKDTree(exyz[:,:4].mean(axis=1)),offset=offset,eoffset=eoffset)
        allxyz.extend(xyz); alle.extend(ec); labels.extend([i]*len(ec))
        offset+=len(xyz); eoffset+=len(ec)
    return bodies,np.array(allxyz),np.array(alle),np.array(labels)

def main(t,h):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'
    quality=json.loads((folder/'resumen.json').read_text())
    if len(quality)!=16 or any(r['status']!='valid' for r in quality): raise RuntimeError('Meshes invalid/incomplete')
    bodies,xyz,elements,labels=load_meshes(folder)
    print('Loaded meshes',len(xyz),len(elements),flush=True)
    reader=STEPControl_Reader(); reader.ReadFile(str(ROOT/f'cuadro_t{t:.1f}mm.stp')); reader.TransferRoots()
    solids=list(explore(reader.OneShape(),TopAbs_SOLID))
    contacts=list(csv.DictReader((ROOT/'contactos.csv').open()))
    # Rear supports master; head cylinders precede frame members to reduce BC conflicts.
    priority={v:k for k,v in enumerate([15,16,4,5,1,2,3,6,7,8,9,10,11,12,13,14])}
    candidates={}; counts=[]
    for row in contacts:
        if not row['min_distance_mm']: continue
        a=int(row['solid_a']); b=int(row['solid_b']); distance=float(row['min_distance_mm'])
        gap_pair=(a,b) in [(7,16),(8,15),(9,15),(10,16)]
        if distance>1e-5 and not gap_pair: continue
        master,slave=sorted([a,b],key=lambda i:priority[i])
        tol=.151 if gap_pair else 2e-5
        box=Bnd_Box(); BRepBndLib.Add_s(solids[master-1],box); bb=np.array(box.Get())
        boundary=np.array(bodies[slave]['boundary']); points=xyz[boundary-1]
        keep=np.all(points>=bb[:3]-tol,axis=1)&np.all(points<=bb[3:]+tol,axis=1)
        boundary=boundary[keep]; points=points[keep]; tested=len(boundary)
        accepted=face_parameters(solids[master-1],points,tol); selected=len(accepted)
        for j,d in accepted.items():
            node=int(boundary[j]); option=(d,priority[master],master)
            if node not in candidates or option<candidates[node]: candidates[node]=option
        counts.append(dict(master=master,slave=slave,gap_pair=gap_pair,tested=tested,selected=selected))
        print('Contact',master,slave,'selected',selected,flush=True)
        if selected==0: raise RuntimeError(f'No bonded nodes found: {master}, {slave}')
    equations=[]; ties=[]; errors=[]; max_extrap=0
    for j,(slave,(_,_,master)) in enumerate(candidates.items()):
        mn,n,error,score=interpolate_batch_candidates(xyz[slave-1],bodies[master])
        errors.append(error); max_extrap=max(max_extrap,score)
        for dof in range(3):
            row={3*(slave-1)+dof:1.}
            for node,w in zip(mn,n):
                if abs(w)>1e-12: row[3*(int(node)-1)+dof]=-float(w)
            equations.append(row)
        ties.append((slave,master,mn,n))
        if j%250==0: print('Interpolated',j,'/',len(candidates),flush=True)
    # General elimination handles redundant support equations at glued interfaces.
    pivots={}; ordered=[]
    def add_equation(row,allow_dummy=False):
        row={d:v for d,v in row.items() if abs(v)>1e-12}
        while any(d in pivots for d in row):
            d=next(d for d in row if d in pivots); scale=row.pop(d)
            for k,v in pivots[d].items(): row[k]=row.get(k,0)-scale*v
            row={k:v for k,v in row.items() if abs(v)>1e-11}
        possible=[d for d in row if d<3*len(xyz)]
        if not possible:
            # A relation involving only fixed auxiliary DOFs is redundant.
            return False
        pivot=max(possible,key=lambda d:abs(row[d])); coeff=row.pop(pivot)
        row={d:v/coeff for d,v in row.items()}
        pivots[pivot]=row; ordered.append((pivot,row)); return True
    for row in equations:
        # Retain the slave DOF as dependent, even when extrapolation creates a
        # master weight >1. Choosing the numerically largest coefficient here
        # reverses the master/slave graph and creates severe cascade fill-in.
        pivot=next(iter(row)); coeff=row[pivot]
        if pivot in pivots: raise RuntimeError('Duplicate bonded slave DOF')
        terms={d:v/coeff for d,v in row.items() if d!=pivot}
        pivots[pivot]=terms; ordered.append((pivot,terms))
    # Cylinder-node selection uses exact imported STEP axes and measured radii.
    inspection=json.loads((ROOT/'inspeccion.json').read_text(encoding='utf-8'))
    support=[]; rigid_rows=[]; inherited_support=[]
    for solid,face,axial,radius in [(15,6,False,6.),(16,6,True,6.),(4,1,False,21.2-t),(5,1,False,21.2-t)]:
        f=inspection['solids'][solid-1]['faces'][face-1]
        origin=np.array(f['axis_origin_mm']); axis=np.array(f['axis_direction'])
        count=0
        for node in bodies[solid]['boundary']:
            p=xyz[node-1]; radial=p-origin-axis*np.dot(p-origin,axis); r=np.linalg.norm(radial)
            if abs(r-radius)>2e-4: continue
            count+=1
            # At the welded ring between coaxial head sections, impose the radial
            # condition on the master side only. A second collocated constraint
            # on the slave side becomes nearly redundant on nonmatching curved
            # meshes. Its residual is checked after solving, rather than creating
            # ill-conditioned opposing Lagrange reactions.
            if solid==5 and node in candidates and candidates[node][2]==4:
                inherited_support.append(dict(node=node,direction=(radial/r).tolist(),solid=solid))
                continue
            for direction in ([radial/r,axis] if axial else [radial/r]):
                dummy=len(xyz)+len(support)+1
                row={3*(node-1)+k:float(direction[k]) for k in range(3)}
                row[3*(dummy-1)]=-1.
                if not add_equation(row): continue
                support.append(dict(dummy=dummy,node=node,direction=direction.tolist(),solid=solid,position=p.tolist()))
                rigid_rows.append(np.r_[direction,np.cross(p,direction)/1000.])
        print('Support cylinder',solid,'nodes',count,flush=True)
        if count<8: raise RuntimeError('Support selection failed')
    singular=np.linalg.svd(np.array(rigid_rows),compute_uv=False)
    if np.linalg.matrix_rank(np.array(rigid_rows))!=6: raise RuntimeError('Rigid instability')
    # Consistent nodal traction, integrated with 7-point Dunavant quadrature.
    quadr=[(1/3,1/3,.225)]
    for a,b,w in [(.05971587178977,.470142064105115,.132394152788506),(.797426985353087,.101286507323456,.125939180544827)]:
        quadr.extend([(b,b,w),(a,b,w),(b,a,w)])
    forces={}; load_info=[]
    for solid,force,axis in [(13,600.,np.array([-.207911690817759, .978147600733806,0])),(14,100.,np.array([-.292371704722736,.956304755963036,0]))]:
        planes=[f for f in bodies[solid]['surfaces'] if f['type']=='Plane']
        face=max(planes,key=lambda f:np.dot(f['center'],axis)); weights={}
        for tri in face['triangles']:
            x=xyz[np.array(tri)-1]
            for q1,q2,w in quadr:
                l=np.array([1-q1-q2,q1,q2]); dl=np.array([[-1.,-1.],[1.,0],[0,1.]])
                n=np.r_[l*(2*l-1),4*l[0]*l[1],4*l[1]*l[2],4*l[2]*l[0]]
                dn=np.vstack(((4*l-1)[:,None]*dl,[4*(l[i]*dl[j]+l[j]*dl[i]) for i,j in [(0,1),(1,2),(2,0)]]))
                jac=x.T@dn; da=np.linalg.norm(np.cross(jac[:,0],jac[:,1]))*.5*w
                for node,v in zip(tri,n*da): weights[node]=weights.get(node,0)+float(v)
        area=sum(weights.values())
        if abs(area/face['area']-1)>.002: raise RuntimeError('Load integration area mismatch')
        for node,w in weights.items(): forces[node]=forces.get(node,np.zeros(3))-force*w/area*axis
        load_info.append(dict(solid=solid,face=face['face'],area_mesh_mm2=area,area_CAD_mm2=face['area'],resultant_N=(-force*axis).tolist(),center_mm=face['center']))
    resultant=sum(forces.values()); moment=sum(np.cross(xyz[n-1],v) for n,v in forces.items())
    metrics=dict(thickness_mm=t,h_mm=h,nodes=len(xyz),elements=len(elements),contacts=counts,
                 tied_nodes=len(candidates),max_affine_patch_error_mm=max(errors),max_extrapolation=max_extrap,
                 support_equations=len(support),rigid_constraint_singular_values=singular.tolist(),
                 rigid_constraint_rank=6,load_faces=load_info,load_resultant_N=resultant.tolist(),load_moment_Nmm=moment.tolist(),
                 status='preprocessor_checks_passed_not_solved')
    (folder/'modelo_resumen.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (folder/'apoyos.json').write_text(json.dumps(support),encoding='utf-8')
    (folder/'apoyos_heredados.json').write_text(json.dumps(inherited_support),encoding='utf-8')
    np.savez_compressed(folder/'modelo.npz',xyz=xyz,elements=elements,solid=labels,load_nodes=np.array(list(forces)),load_forces=np.array(list(forces.values())))
    with (folder/'modelo.inp').open('w',encoding='ascii') as out:
        out.write('*HEADING\nFrame 3D quadratic solid - mm N MPa tonne\n*NODE,NSET=PHYSICAL\n')
        for i,p in enumerate(xyz,1): out.write(f'{i},'+','.join(f'{v:.12g}' for v in p)+'\n')
        out.write('*NODE,NSET=REACTIONS\n')
        for s in support: out.write(str(s['dummy'])+','+','.join(str(v) for v in s['position'])+'\n')
        out.write('*ELEMENT,TYPE=C3D10,ELSET=ALLSOLIDS\n')
        for i,ec in enumerate(elements,1): out.write(str(i)+','+','.join(str(int(v)) for v in ec)+'\n')
        out.write('*MATERIAL,NAME=AL6061T6\n*ELASTIC\n68900.,0.33\n*DENSITY\n2.7E-9\n*SOLID SECTION,ELSET=ALLSOLIDS,MATERIAL=AL6061T6\n')
        for pivot,row in ordered:
            terms=[(pivot,1.)]+list(row.items())
            out.write('*EQUATION\n'+str(len(terms))+'\n')
            for start in range(0,len(terms),4):
                out.write(','.join(f'{d//3+1},{d%3+1},{v:.12g}' for d,v in terms[start:start+4])+'\n')
        out.write('*BOUNDARY\nREACTIONS,1,3,0.\n*STEP\n*STATIC\n*CLOAD\n')
        for node,f in forces.items():
            for k,v in enumerate(f,1):
                if abs(v)>1e-14: out.write(f'{node},{k},{v:.12g}\n')
        out.write('*NODE FILE\nU\n*EL FILE\nS\n*NODE PRINT,NSET=REACTIONS\nRF\n*NODE PRINT,NSET=PHYSICAL\nU\n*EL PRINT,ELSET=ALLSOLIDS\nS\n*END STEP\n')
    print(json.dumps(metrics,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); a=p.parse_args(); main(a.t,a.h)
