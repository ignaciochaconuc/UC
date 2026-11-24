"""Cambiar sólo taladros coaxiales de 12 tubos, conservando envolventes y auxiliares.
La reconstrucción de cada tubo a 2.5 mm debe reproducir el sólido original.
"""
import csv
import json
import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing, BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from inspeccionar import *

def volume(shape):
    p=GProp_GProps(); BRepGProp.VolumeProperties_s(shape,p); return p.Mass()

def cut(a,b):
    op=BRepAlgoAPI_Cut(a,b); op.SetFuzzyValue(1e-6); op.Build()
    if not op.IsDone(): raise RuntimeError('Cut failed')
    return op.Shape()

def diffvolume(a,b):
    return volume(cut(a,b))+volume(cut(b,a))

def main():
    data=json.loads((ROOT/'inspeccion.json').read_text(encoding='utf-8'))
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=data['sha256']:
        raise RuntimeError('Input STEP changed since inspection')
    pairs=json.loads((ROOT/'espesores.json').read_text(encoding='utf-8'))
    reader=STEPControl_Reader(); reader.ReadFile(str(SOURCE)); reader.TransferRoots()
    solids=list(explore(reader.OneShape(),TopAbs_SOLID))
    stocks=[]; specs=[]; validations=[]
    for s,record,item in zip(solids[:12],data['solids'][:12],pairs):
        if len(item['coaxial_pairs'])!=1: raise RuntimeError('Ambiguous bore')
        pair=item['coaxial_pairs'][0]; f=record['faces'][pair['inner_face']-1]
        faces=list(explore(s,TopAbs_FACE))
        op=BRepAlgoAPI_Defeaturing(); op.SetShape(s); op.AddFaceToRemove(faces[pair['inner_face']-1]); op.Build()
        if not op.IsDone() or not BRepCheck_Analyzer(op.Shape()).IsValid():
            raise RuntimeError('Bore removal failed')
        stock=op.Shape(); stocks.append(stock)
        origin=np.array(f['axis_origin_mm']); axis=np.array(f['axis_direction'])
        b=np.array(record['bbox_mm']); corners=np.array(list(__import__('itertools').product(*zip(b[:3],b[3:]))))
        ext=(corners-origin)@axis; start=origin+axis*(ext.min()-10); length=ext.max()-ext.min()+20
        xdir=BRepAdaptor_Surface(TopoDS.Face_s(faces[pair['inner_face']-1])).Cylinder().Position().XDirection()
        specs.append((pair['outer_diameter_mm']/2,start,axis,length,xdir))
        ro,point,direction,length,xdir=specs[-1]
        bore=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*point),gp_Dir(*direction),xdir),ro-2.5,length).Shape()
        recreated=cut(stock,bore); error=diffvolume(s,recreated)
        validations.append(dict(solid=record['id'],reconstruction_symdiff_mm3=error))
        if error>max(1e-4,volume(s)*1e-8):
            raise RuntimeError(f"Reconstruction changes exterior at solid {record['id']}: {error}")
    rows=[]
    for t in [2.0,2.5,3.0]:
        variant=[]
        for i,(stock,(ro,point,direction,length,xdir)) in enumerate(zip(stocks,specs)):
            bore=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*point),gp_Dir(*direction),xdir),ro-t,length).Shape()
            s=solids[i] if t==2.5 else cut(stock,bore)
            if not BRepCheck_Analyzer(s).IsValid() or len(list(explore(s,TopAbs_SOLID)))!=1:
                raise RuntimeError('Invalid variant')
            # Every variant is the SAME outer stock minus one coaxial cylinder.
            # No displacement, scaling, exterior offset or trim changes are used.
            variant.append(s)
        variant.extend(solids[12:])
        compound=TopoDS_Compound(); builder=BRep_Builder(); builder.MakeCompound(compound)
        for s in variant: builder.Add(compound,s)
        writer=STEPControl_Writer(); writer.Transfer(compound,STEPControl_AsIs)
        dest=ROOT/f'cuadro_t{t:.1f}mm.stp'
        if writer.Write(str(dest))!=IFSelect_RetDone: raise RuntimeError('STEP write failed')
        vt=sum(volume(s) for s in variant[:12]); va=sum(volume(s) for s in variant[12:])
        rows.append(dict(thickness_mm=t,tube_volume_mm3=vt,aux_volume_mm3=va,
                         sum_volume_mm3=vt+va,tube_mass_kg=vt*2.7e-6,
                         sum_mass_kg=(vt+va)*2.7e-6,aux_same_shapes=all(s.IsSame(q) for s,q in zip(variant[12:],solids[12:]))))
    with (ROOT/'masas_geometricas.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (ROOT/'validacion_reconstruccion.json').write_text(json.dumps(validations,indent=2),encoding='utf-8')
    print(json.dumps(rows,indent=2))

if __name__=='__main__': main()
