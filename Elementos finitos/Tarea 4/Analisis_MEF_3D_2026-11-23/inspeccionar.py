"""Inspección de la única geometría autorizada; unidades internas OCC: mm.
Ejecutar: python inspeccionar.py
No modifica el STEP ni interpreta automáticamente pares de radios como espesor.
"""
import hashlib
import csv
import json
import sys
from pathlib import Path
from collections import Counter
import gmsh
import OCP
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'referencia_confirmada.stp'
if not SOURCE.is_file():
    SOURCE = ROOT.parent / 'Ensamblaje 2.stp'
ROLES = {
    1:'Tubo de asiento inferior',2:'Prolongación superior del asiento',3:'Tubo superior',
    4:'Tubo de dirección inferior',5:'Tubo de dirección superior',6:'Tubo diagonal',
    7:'Vaina derecha (Z negativo)',8:'Vaina izquierda (Z positivo)',
    9:'Tirante izquierdo (Z positivo)',10:'Tirante derecho (Z negativo)',
    11:'Puente entre tirantes',12:'Caja tubular del pedalier',
    13:'Remate del asiento',14:'Remate delantero',15:'Puntera izquierda (Z positivo)',16:'Puntera derecha (Z negativo)'
}

def xyz(p):
    return [p.X(), p.Y(), p.Z()]

def explore(shape, kind):
    ex = TopExp_Explorer(shape, kind)
    while ex.More():
        yield ex.Current()
        ex.Next()

def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    config=json.loads((ROOT/'configuracion.json').read_text(encoding='utf-8'))
    if digest!=config['sha256']: raise RuntimeError('El STEP no coincide con la referencia autorizada')
    out = {'source': str(SOURCE), 'sha256': digest,
           'authorization': 'Usuario confirmó que el archivo subido es el correcto.',
           'units': 'mm, mm2, mm3; OCC target unit MM',
           'tools': {'python': sys.version, 'OCP': OCP.__version__, 'gmsh': gmsh.__version__},
           'solids': []}
    reader = STEPControl_Reader()
    reader.SetSystemLengthUnit(1.0)
    if reader.ReadFile(str(SOURCE)) != IFSelect_RetDone:
        raise RuntimeError('STEP read failed')
    reader.TransferRoots()
    shape = reader.OneShape()
    out['assembly_valid'] = BRepCheck_Analyzer(shape).IsValid()
    for i, s in enumerate(explore(shape, TopAbs_SOLID), 1):
        prop = GProp_GProps()
        BRepGProp.VolumeProperties_s(s, prop)
        box = Bnd_Box()
        BRepBndLib.Add_s(s, box)
        record = {'id': i, 'role':ROLES[i], 'classification':'tubo estructural' if i<=12 else 'auxiliar sin modificar', 'valid': BRepCheck_Analyzer(s).IsValid(),
                  'volume_mm3': prop.Mass(), 'center_mm': xyz(prop.CentreOfMass()),
                  'bbox_mm': list(box.Get()), 'faces': []}
        for j, f in enumerate(explore(s, TopAbs_FACE), 1):
            face = TopoDS.Face_s(f)
            surf = BRepAdaptor_Surface(face, True)
            typ = str(surf.GetType()).split('.')[-1]
            area = GProp_GProps()
            BRepGProp.SurfaceProperties_s(face, area)
            r = {'id': j, 'type': typ, 'area_mm2': area.Mass(),
                 'center_mm': xyz(area.CentreOfMass()), 'orientation': str(face.Orientation())}
            if 'Cylinder' in typ:
                cyl = surf.Cylinder()
                r.update(radius_mm=cyl.Radius(), axis_origin_mm=xyz(cyl.Location()),
                         axis_direction=xyz(cyl.Axis().Direction()))
            elif 'Plane' in typ:
                plane = surf.Plane()
                r.update(plane_origin_mm=xyz(plane.Location()),
                         geometric_normal=xyz(plane.Axis().Direction()))
            record['faces'].append(r)
        record['surface_types'] = dict(Counter(f['type'] for f in record['faces']))
        out['solids'].append(record)
    out['sum_solid_volumes_mm3'] = sum(s['volume_mm3'] for s in out['solids'])
    # This sum is NOT a union volume; touching/intersecting bodies require inspection.
    (ROOT / 'inspeccion.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    with (ROOT/'componentes.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f); writer.writerow(['solido','identificacion_geometrica','clasificacion','volumen_referencia_mm3','masa_referencia_kg','caras'])
        for s in out['solids']: writer.writerow([s['id'],s['role'],s['classification'],s['volume_mm3'],s['volume_mm3']*2.7e-6,len(s['faces'])])
    print(json.dumps({k:v for k,v in out.items() if k != 'solids'}, indent=2, ensure_ascii=False))
    for s in out['solids']:
        print('SOLID', s['id'], 'V=', round(s['volume_mm3'],3), 'bbox=',s['bbox_mm'],s['surface_types'])
        for f in s['faces']:
            if 'radius_mm' in f:
                print(' CYL', f['id'], 'R=', f['radius_mm'], 'O=',f['axis_origin_mm'],'D=',f['axis_direction'])

if __name__ == '__main__':
    main()
