"""Malla tetraédrica cuadrática conforme en interfaces que se tocan.
python mallar.py 2.0 7
Las holguras de punteras se conservan; se vinculan posteriormente por MPC.
"""
import argparse
import json
import numpy as np
import gmsh
from inspeccionar import ROOT

def main(t,h):
    folder=ROOT/f't{t:.1f}_h{h:g}'; folder.mkdir(exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber('General.NumThreads',4)
    gmsh.option.setNumber('Geometry.OCCTargetUnit','MM') if False else None
    gmsh.model.add('cuadro')
    imported=gmsh.model.occ.importShapes(str(ROOT/f'cuadro_t{t:.1f}mm.stp'))
    volumes=[v for v in imported if v[0]==3]
    if len(volumes)!=16: raise RuntimeError(f'Expected 16 solids, got {len(volumes)}')
    mass_before=sum(gmsh.model.occ.getMass(*v) for v in volumes)
    # Bonded, touching frame components have the same material: fuse their domain.
    out,maps=gmsh.model.occ.fuse([volumes[0]],volumes[1:14])
    gmsh.model.occ.synchronize()
    mapping={'1':[v[1] for v in out if v[0]==3], '15':[volumes[14][1]], '16':[volumes[15][1]]}
    allvols=gmsh.model.getEntities(3)
    mass_after=sum(gmsh.model.occ.getMass(*v) for v in allvols)
    # Duplicated tags in maps indicate overlapping bodies, which are unacceptable.
    mapped=[tag for tags in mapping.values() for tag in tags]
    if len(mapped)!=len(set(mapped)) or len(allvols)!=3 or abs(mass_after-mass_before)>mass_before*1e-5:
        raise RuntimeError(f'Interference/fragment change: {len(allvols)} volumes, {mass_before-mass_after} mm3')
    for i,tags in mapping.items(): gmsh.model.addPhysicalGroup(3,tags,int(i),f'SOLID_{i}')
    gmsh.option.setNumber('Mesh.MeshSizeMin',h*0.25)
    gmsh.option.setNumber('Mesh.MeshSizeMax',h)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',24)
    gmsh.option.setNumber('Mesh.Algorithm3D',10)
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.setOrder(2)
    gmsh.model.mesh.optimize('HighOrder')
    gmsh.write(str(folder/'malla.msh'))
    nodeids,coords,_=gmsh.model.mesh.getNodes(); coords=np.array(coords).reshape(-1,3)
    byid={int(n):i for i,n in enumerate(nodeids)}
    elems=[]; elemids=[]; labels=[]
    # CCX C3D10 order: vertices, edges 12 23 31 14 24 34.
    target=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]])
    for label,tags in mapping.items():
        for tag in tags:
            types,ids,connect=gmsh.model.mesh.getElements(3,tag)
            for typ,eids,conn in zip(types,ids,connect):
                name,dim,order,n,local,_=gmsh.model.mesh.getElementProperties(typ)
                if n!=10: raise RuntimeError(f'Expected tetra10, got {name}')
                local=np.array(local).reshape(-1,3)
                perm=[int(np.argmin(np.linalg.norm(local-x,axis=1))) for x in target]
                ec=np.array(conn,dtype=np.int64).reshape(-1,10)[:,perm]
                elems.extend(ec); elemids.extend(eids); labels.extend([int(label)]*len(eids))
    # Save surface nodes and face identities for exact load and support selections.
    surfaces=[]
    for label,tags in mapping.items():
        faces=set(f[1] for v in tags for f in gmsh.model.getBoundary([(3,v)],oriented=False) if f[0]==2)
        for face in faces:
            ns,_,_=gmsh.model.mesh.getNodes(2,face,includeBoundary=True)
            surfaces.append(dict(solid=int(label),face=int(face),type=gmsh.model.getType(2,face),
                                 center=list(gmsh.model.occ.getCenterOfMass(2,face)),
                                 area=gmsh.model.occ.getMass(2,face),nodes=[int(n) for n in ns]))
    np.savez_compressed(folder/'malla.npz',nodes=nodeids,xyz=coords,elements=np.array(elems),element_ids=np.array(elemids),solid=np.array(labels))
    (folder/'superficies.json').write_text(json.dumps(surfaces),encoding='utf-8')
    metrics={'thickness_mm':t,'h_max_mm':h,'nodes':len(nodeids),'elements':len(elems),
             'volume_before_fragment_mm3':mass_before,'volume_after_fragment_mm3':mass_after,'solid_mapping':mapping}
    # Quality is diagnostic; positive det at quadrature is checked by solver too.
    qualities=gmsh.model.mesh.getElementQualities([int(e) for e in elemids],'minDetJac')
    metrics['minDetJac']=float(min(qualities)); metrics['nonpositive_Jacobians']=int(np.sum(np.array(qualities)<=0))
    (folder/'malla_resumen.json').write_text(json.dumps(metrics,indent=2))
    gmsh.finalize(); print(json.dumps(metrics,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); a=p.parse_args(); main(a.t,a.h)
