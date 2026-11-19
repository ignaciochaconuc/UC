"""Exportaciones y visualización de geometría REAL del kernel, no reconstruida."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from .cad import caras


def guardar_json(path,obj):
    def convertir(v):
        if isinstance(v,np.generic):return v.item()
        if isinstance(v,np.ndarray):return v.tolist()
        raise TypeError(type(v).__name__)
    Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=convertir,allow_nan=False),encoding='utf-8')


def diferencias_declaradas(config,dim):
    filas=[]
    for clave,valor in config['declarado_EP2'].items():
        real=dim['diametros_efectivos_mm'][0] if clave=='diametro_efectivo_mm' and len(dim['diametros_efectivos_mm'])==1 else dim.get(clave)
        coincide=isinstance(real,(int,float)) and math.isclose(real,valor,rel_tol=0,abs_tol=1e-5)
        filas.append(dict(parametro=clave,declarado_EP2=valor,extraido_STEP=real,coincide=coincide,
            accion='Conservar declaración histórica; geometría activa procede del STEP, sin editar EP2' if not coincide else 'Coincide nominalmente'))
    filas.append(dict(parametro='altura_total_vs_zona_perforada',declarado_EP2=config['declarado_EP2']['espesor_zona_perforada_mm'],
        extraido_STEP=dim['espesor_total_envolvente_mm'],coincide=math.isclose(dim['espesor_total_envolvente_mm'],dim['espesor_zona_perforada_mm']),
        accion='Distinguir envolvente total con resalte y longitud del cuerpo perforado; no usar altura total como L de extrusión'))
    return filas


def guardar_geometria(salida,config,solid,dim,agujeros,pares,inventario):
    salida.mkdir(parents=True,exist_ok=True)
    guardar_json(salida/'geometria_STEP.json',dim)
    guardar_json(salida/'inventario_caras.json',inventario)
    guardar_json(salida/'entidades_para_revision.json',dim['superficies_para_revision'])
    pd.DataFrame(agujeros).to_csv(salida/'perforaciones_STEP.csv',index=False)
    pd.DataFrame(pares,columns=['id1','id2','distancia_centros_mm','ligamento_cilindrico_mm','ligamento_bocas_mm']).sort_values('ligamento_cilindrico_mm').to_csv(salida/'distancias_y_ligamentos.csv',index=False)
    pd.DataFrame(diferencias_declaradas(config,dim)).to_csv(salida/'comparacion_declarado_EP2.csv',index=False)
    pd.DataFrame([{'dimension':k,'valor':json.dumps(v,ensure_ascii=False),'unidad':'según sufijo del campo; CAD en mm'}
                  for k,v in dim.items() if not isinstance(v,dict)]).to_csv(salida/'dimensiones_extraidas.csv',index=False)
    R=np.array(dim['sistema_local']['base_filas_x_y_z_en_CAD']);origen=np.array(dim['sistema_local']['origen_CAD_mm'])
    fig,ax=plt.subplots(figsize=(7,7))
    ex=TopExp_Explorer(solid,TopAbs_EDGE)
    while ex.More():
        curva=BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        a,b=curva.FirstParameter(),curva.LastParameter()
        if math.isfinite(a) and math.isfinite(b):
            puntos=np.array([curva.Value(float(t)).Coord() for t in np.linspace(a,b,33)])
            local=(puntos-origen)@R.T
            ax.plot(local[:,0],local[:,1],color='0.65',linewidth=.5)
        ex.Next()
    for h in agujeros:
        ax.add_patch(Circle((h['x_mm'],h['y_mm']),h['diametro_efectivo_mm']/2,fill=False,color='tab:blue',linewidth=.7))
        ax.text(h['x_mm'],h['y_mm'],str(h['id']),ha='center',va='center',fontsize=4)
    ax.set_aspect('equal');ax.set(xlabel='x local [mm]',ylabel='y local [mm]',title=f"{config['modelo']}: aristas STEP y conductos identificados\nGris: topología CAD; azul: diámetro efectivo; IDs de extracción")
    fig.tight_layout();fig.savefig(salida/'auditoria_contornos_STEP.png',dpi=180);plt.close(fig)
    # Triangulación únicamente para visualizar BRep; no es malla ni solución FEM.
    BRepMesh_IncrementalMesh(solid,.35,False,.25,True)
    triangulos=[]
    for face in caras(solid):
        loc=TopLoc_Location();tri=BRep_Tool.Triangulation_s(face,loc)
        if tri is None:continue
        pts=np.array([tri.Node(i).Transformed(loc.Transformation()).Coord() for i in range(1,tri.NbNodes()+1)])
        pts=(pts-origen)@R.T
        for i in range(1,tri.NbTriangles()+1):
            ids=tri.Triangle(i).Get();triangulos.append(pts[np.array(ids)-1])
    fig=plt.figure(figsize=(8,6));ax=fig.add_subplot(111,projection='3d')
    triangulos=np.asarray(triangulos)
    normales=np.cross(triangulos[:,1]-triangulos[:,0],triangulos[:,2]-triangulos[:,0])
    normales/=np.maximum(np.linalg.norm(normales,axis=1)[:,None],1e-20)
    luz=np.array([.3,-.5,1.]);luz/=np.linalg.norm(luz)
    brillo=.35+.65*np.abs(normales@luz)
    colores=np.array([.58,.72,.9])[None,:]*brillo[:,None]
    ax.add_collection3d(Poly3DCollection(triangulos,facecolors=colores,edgecolor='none',alpha=1))
    # Aristas del BRep superpuestas permiten ver conductos y resalte; no
    # son deformaciones ni un modelo de elementos finitos.
    ex=TopExp_Explorer(solid,TopAbs_EDGE)
    while ex.More():
        curva=BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        a,b=curva.FirstParameter(),curva.LastParameter()
        if math.isfinite(a) and math.isfinite(b):
            puntos=np.array([curva.Value(float(t)).Coord() for t in np.linspace(a,b,33)])
            local=(puntos-origen)@R.T
            ax.plot(local[:,0],local[:,1],local[:,2],color='0.2',linewidth=.3,alpha=.6)
        ex.Next()
    ax.view_init(elev=45,azim=-50)
    rad=dim['diametro_exterior_mm']/2
    zs=[v for f in inventario for k,v in f.items() if k in ('z_min_mm','z_max_mm','z_mm')]
    ax.set(xlim=(-rad,rad),ylim=(-rad,rad),zlim=(min(zs),max(zs)),xlabel='x local [mm]',ylabel='y local [mm]',zlabel='z local [mm]',
        title=f"{config['modelo']}: sólido STEP (no FEM)")
    ax.set_box_aspect((2*rad,2*rad,dim['espesor_total_envolvente_mm']))
    fig.tight_layout();fig.savefig(salida/'solido_STEP_3D.png',dpi=160);plt.close(fig)
