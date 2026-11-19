"""Diagnóstico de sección meridiana por pertenencia al sólido CAD."""
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Torus
from OCP.TopAbs import TopAbs_FACE
from OCP.gp import gp_Pnt

if __name__=='__main__':
    r=STEPControl_Reader();r.ReadFile(str(Path(__file__).resolve().parents[1]/'geometrias/Matriz_prototipo.stp'));r.TransferRoots()
    ex=TopExp_Explorer(r.OneShape(),TopAbs_SOLID);s=TopoDS.Solid_s(ex.Current())
    for y in (1,5,9,10.1,15,22,25,25.9):
        print(y,[(x,str(BRepClass3d_SolidClassifier(s,gp_Pnt(x,y,0),1e-7).State())) for x in (0,6,7,10,13,18,24,30,40)])
    ex=TopExp_Explorer(s,TopAbs_FACE)
    while ex.More():
        ad=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()))
        if ad.GetType()==GeomAbs_Torus:
            t=ad.Torus();print('TORUS',t.Location().Coord(),t.MajorRadius(),t.MinorRadius())
        ex.Next()
