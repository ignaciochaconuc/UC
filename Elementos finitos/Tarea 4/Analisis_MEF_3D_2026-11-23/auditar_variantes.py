"""Auditoría de exportación STEP, espesores y auxiliares; gráficas geométricas."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inspeccionar import *
from generar_variantes import diffvolume,volume
from preparar_modelo import face_parameters
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.gp import gp_Pnt2d
from OCP.TopAbs import TopAbs_IN,TopAbs_ON

def sample_boundary(shape):
    points=[]
    for fs in explore(shape,TopAbs_FACE):
        face=TopoDS.Face_s(fs); surf=BRepAdaptor_Surface(face,True); classifier=BRepClass_FaceClassifier()
        for u in np.linspace(surf.FirstUParameter(),surf.LastUParameter(),13):
            for v in np.linspace(surf.FirstVParameter(),surf.LastVParameter(),13):
                classifier.Perform(face,gp_Pnt2d(float(u),float(v)),1e-7)
                if classifier.State() in (TopAbs_IN,TopAbs_ON): points.append(xyz(surf.Value(float(u),float(v))))
    return np.array(points)

reader=STEPControl_Reader(); reader.ReadFile(str(SOURCE)); reader.TransferRoots()
reference=list(explore(reader.OneShape(),TopAbs_SOLID))
checks=[]
for t in [2.,2.5,3.]:
    path=ROOT/f'cuadro_t{t:.1f}mm.stp'
    reader=STEPControl_Reader(); reader.ReadFile(str(path)); reader.TransferRoots()
    solids=list(explore(reader.OneShape(),TopAbs_SOLID))
    row=dict(t_mm=t,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),n_solids=len(solids),all_valid=all(BRepCheck_Analyzer(s).IsValid() for s in solids),aux_surface_checks=[],bbox_max_difference_mm=0.)
    for i,(a,b) in enumerate(zip(reference,solids),1):
        ba=Bnd_Box(); bb=Bnd_Box(); BRepBndLib.AddOptimal_s(a,ba,False,False); BRepBndLib.AddOptimal_s(b,bb,False,False)
        delta=float(np.max(np.abs(np.array(ba.Get())-np.array(bb.Get()))))
        row['bbox_max_difference_mm']=max(row['bbox_max_difference_mm'],delta)
        if i>12:
            forward=sample_boundary(a); reverse=sample_boundary(b)
            matched_f=face_parameters(b,forward,1e-5); matched_r=face_parameters(a,reverse,1e-5)
            row['aux_surface_checks'].append(dict(solid=i,forward_points=len(forward),forward_matched=len(matched_f),reverse_points=len(reverse),reverse_matched=len(matched_r),volume_difference_mm3=volume(b)-volume(a),max_sample_surface_distance_mm=max([*matched_f.values(),*matched_r.values()])))
    gmsh.initialize(); gmsh.option.setNumber('General.Terminal',0); gmsh.model.add('audit')
    vs=[v for v in gmsh.model.occ.importShapes(str(path)) if v[0]==3]
    before=sum(gmsh.model.occ.getMass(*v) for v in vs)
    out,maps=gmsh.model.occ.fragment(vs,[]); gmsh.model.occ.synchronize()
    mapped=[v for m in maps for v in m if v[0]==3]
    row['fragment_volume_count']=len(gmsh.model.getEntities(3))
    row['overlapping_volume_tags']=len(mapped)-len(set(mapped))
    after=sum(gmsh.model.occ.getMass(*v) for v in gmsh.model.getEntities(3))
    row['boolean_volume_change_mm3']=after-before
    gmsh.finalize(); checks.append(row); print(json.dumps(row),flush=True)
(ROOT/'auditoria_variantes.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
data=list(csv.DictReader((ROOT/'masas_geometricas.csv').open()))
t=[float(r['thickness_mm']) for r in data]; tubes=[float(r['tube_mass_kg']) for r in data]; total=[float(r['sum_mass_kg']) for r in data]
fig,ax=plt.subplots(figsize=(8,5)); ax.bar(t,tubes,width=.28,label='Tubos'); ax.bar(t,np.array(total)-tubes,bottom=tubes,width=.28,label='Remates y punteras (constantes)')
for x,y in zip(t,total): ax.text(x,y+.025,f'{y:.4f} kg',ha='center')
ax.set(xlabel='Espesor [mm]',ylabel='Masa geométrica [kg]',xticks=t,ylim=(0,3.3),title='Aluminio: densidad 2700 kg/m³ (no son resultados MEF)'); ax.legend(); ax.grid(axis='y',alpha=.2); fig.tight_layout(); fig.savefig(ROOT/'comparacion_masas.png',dpi=180)
inspection=json.loads((ROOT/'inspeccion.json').read_text(encoding='utf-8')); pairs=json.loads((ROOT/'espesores.json').read_text())
with (ROOT/'dimensiones_tubos.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.writer(f); writer.writerow(['solido','diametro_exterior_mm','espesor_referencia_mm','diametro_interior_t2_mm','diametro_interior_t2_5_mm','diametro_interior_t3_mm'])
    for row in pairs:
        pair=row['coaxial_pairs'][0]; d=pair['outer_diameter_mm']; writer.writerow([row['solid'],d,pair['thickness_mm'],d-4,d-5,d-6])
