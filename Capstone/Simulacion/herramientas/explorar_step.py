"""Diagnóstico OpenCascade: ninguna geometría se reconstruye por texto/píxeles."""
from collections import Counter
from pathlib import Path
import json
from OCP.STEPControl import STEPControl_Reader
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE,TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_Cone,GeomAbs_Plane
from OCP.TColStd import TColStd_SequenceOfAsciiString
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


def explorar(path):
    Interface_Static.SetCVal_s('xstep.cascade.unit','MM')
    r=STEPControl_Reader()
    if r.ReadFile(str(path))!=IFSelect_RetDone: raise RuntimeError('No importado')
    u,a,s=(TColStd_SequenceOfAsciiString() for _ in range(3));r.FileUnits(u,a,s)
    unidades=[u.Value(i).ToCString() for i in range(1,u.Length()+1)]
    r.TransferRoots();shape=r.OneShape()
    box=Bnd_Box();BRepBndLib.AddOptimal_s(shape,box,False,False)
    ex=TopExp_Explorer(shape,TopAbs_FACE);caras=[]
    while ex.More():
        face=TopoDS.Face_s(ex.Current());ad=BRepAdaptor_Surface(face,True)
        b=Bnd_Box();BRepBndLib.AddOptimal_s(face,b,False,False)
        d=dict(id=len(caras)+1,tipo=str(ad.GetType()),bbox=b.Get())
        if ad.GetType()==GeomAbs_Cylinder:
            c=ad.Cylinder();d.update(r=c.Radius(),origen=c.Location().Coord(),eje=c.Axis().Direction().Coord(),U=(ad.FirstUParameter(),ad.LastUParameter()),V=(ad.FirstVParameter(),ad.LastVParameter()))
        if ad.GetType()==GeomAbs_Cone:
            c=ad.Cone();d.update(r=c.RefRadius(),origen=c.Location().Coord(),eje=c.Axis().Direction().Coord(),semiangulo=c.SemiAngle())
        caras.append(d);ex.Next()
    return dict(archivo=path.name,unidades=unidades,bbox=box.Get(),tipos=dict(Counter(c['tipo'] for c in caras)),caras=caras)


if __name__=='__main__':
    for path in (Path(__file__).resolve().parents[1]/'geometrias').glob('*.stp'):
        d=explorar(path)
        print(json.dumps({k:v for k,v in d.items() if k!='caras'},indent=2))
        print('Cilindros agrupados',Counter(round(c['r'],6) for c in d['caras'] if c['tipo']=='GeomAbs_SurfaceType.GeomAbs_Cylinder'))
        print(json.dumps(d['caras'][:4],indent=2))
