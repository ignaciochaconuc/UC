"""Distancias, intersecciones y vista de inspección. No ejecuta MEF."""
import csv
import json
import itertools
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Defeaturing
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from inspeccionar import *

reader = STEPControl_Reader()
reader.ReadFile(str(SOURCE)); reader.TransferRoots()
solids = list(explore(reader.OneShape(), TopAbs_SOLID))
rows = []
for (i,a),(j,b) in itertools.combinations(enumerate(solids,1),2):
    ba=Bnd_Box(); bb=Bnd_Box(); BRepBndLib.Add_s(a,ba); BRepBndLib.Add_s(b,bb)
    aa=np.array(ba.Get()); ab=np.array(bb.Get())
    lower=float(np.linalg.norm(np.maximum(0,np.maximum(aa[:3]-ab[3:],ab[:3]-aa[3:]))))
    if lower>1.0:
        rows.append(dict(solid_a=i,solid_b=j,min_distance_mm=None,intersection_mm3=0.0,bbox_lower_bound_mm=lower))
        continue
    print('Checking',i,j,flush=True)
    dist = BRepExtrema_DistShapeShape(a,b)
    if not dist.IsDone():
        raise RuntimeError(f'Distance failed: {i}, {j}')
    d = dist.Value()
    vol = 0.0
    if d < 1e-5:
        common = BRepAlgoAPI_Common(a,b)
        if not common.IsDone():
            raise RuntimeError(f'Common failed: {i}, {j}')
        p=GProp_GProps(); BRepGProp.VolumeProperties_s(common.Shape(),p)
        vol=p.Mass()
    rows.append(dict(solid_a=i,solid_b=j,min_distance_mm=d,intersection_mm3=vol,bbox_lower_bound_mm=lower))
with (ROOT/'contactos.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    if r['min_distance_mm'] is not None and r['min_distance_mm']<1.0:
        print(r)

fig=plt.figure(figsize=(13,8)); ax=fig.add_subplot(projection='3d')
for i,s in enumerate(solids,1):
    BRepMesh_IncrementalMesh(s,0.8,False,0.3,False).Perform()
    triangles=[]
    for f in explore(s,TopAbs_FACE):
        loc=TopLoc_Location(); tri=BRep_Tool.Triangulation_s(TopoDS.Face_s(f),loc)
        if tri is None: continue
        transform=loc.Transformation()
        for k in range(1,tri.NbTriangles()+1):
            triangles.append([xyz(tri.Node(n).Transformed(transform)) for n in tri.Triangle(k).Get()])
    color=plt.get_cmap('tab20')((i-1)%20)
    ax.add_collection3d(Poly3DCollection(triangles,facecolor=color,edgecolor='none',alpha=0.85))
    p=GProp_GProps(); BRepGProp.VolumeProperties_s(s,p); c=xyz(p.CentreOfMass())
    ax.text(*c,str(i),color='black',fontsize=10)
ax.set(xlim=(-600,380),ylim=(-360,370),zlim=(-150,80),xlabel='X [mm]',ylabel='Y [mm]',zlabel='Z [mm]',title='STEP autorizado: identificación de sólidos (sin resultados MEF)')
ax.set_box_aspect((980,730,230)); ax.view_init(elev=35,azim=-70)
fig.tight_layout(); fig.savefig(ROOT/'geometria_identificada.png',dpi=180); plt.close(fig)

data=json.loads((ROOT/'inspeccion.json').read_text(encoding='utf-8'))
thickness=[]
for s,record in zip(solids[:12],data['solids'][:12]):
    pairs=[]
    faces=list(explore(s,TopAbs_FACE))
    for f,g in itertools.combinations(record['faces'],2):
        if 'radius_mm' not in f or 'radius_mm' not in g: continue
        d=np.array(f['axis_direction']); e=np.array(g['axis_direction'])
        delta=np.array(g['axis_origin_mm'])-np.array(f['axis_origin_mm'])
        if np.linalg.norm(np.cross(d,e))<1e-6 and np.linalg.norm(np.cross(delta,d))<1e-5 and abs(f['radius_mm']-g['radius_mm'])>1e-5:
            inner=min((f,g),key=lambda z:z['radius_mm']); outer=max((f,g),key=lambda z:z['radius_mm'])
            pairs.append({'inner_face':inner['id'],'outer_face':outer['id'],'outer_diameter_mm':2*outer['radius_mm'],'thickness_mm':outer['radius_mm']-inner['radius_mm']})
    thickness.append({'solid':record['id'],'coaxial_pairs':pairs})
    if len(pairs)==1:
        op=BRepAlgoAPI_Defeaturing(); op.SetShape(s); op.AddFaceToRemove(faces[pairs[0]['inner_face']-1]); op.Build()
        print('Bore removal trial',record['id'],op.IsDone(), 'valid',BRepCheck_Analyzer(op.Shape()).IsValid() if op.IsDone() else None)
(ROOT/'espesores.json').write_text(json.dumps(thickness,indent=2),encoding='utf-8')
print('DONE')
