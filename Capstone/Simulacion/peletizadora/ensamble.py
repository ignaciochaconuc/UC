"""Lectura XCAF de instancias y geometría del ensamble, sin modificar CAD."""
import hashlib
import math
from pathlib import Path
from collections import Counter
import numpy as np
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence,TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFDoc import XCAFDoc_DocumentTool,XCAFDoc_ShapeTool
from OCP.TopLoc import TopLoc_Location
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_ON
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_Plane,GeomAbs_Torus,GeomAbs_Cone
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.STEPControl import STEPControl_Reader,STEPControl_Writer,STEPControl_AsIs
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TColStd import TColStd_SequenceOfAsciiString
from scipy.spatial import cKDTree
from tempfile import TemporaryDirectory
from .cad import extraer,importar


def transformar(shape,M):
    tr=gp_Trsf();tr.SetValues(*[float(v) for fila in np.asarray(M)[:3] for v in fila])
    return BRepBuilderAPI_Transform(shape,tr,True).Shape()


def frontera_muestreada(shape,otro,tolerancia=1e-5):
    puntos={};ex=TopExp_Explorer(shape,TopAbs_EDGE)
    while ex.More():
        a=BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()));u,v=a.FirstParameter(),a.LastParameter()
        if math.isfinite(u) and math.isfinite(v):
            for t in np.linspace(u,v,7):
                xyz=a.Value(float(t)).Coord();puntos[tuple(np.round(xyz,8))]=xyz
        ex.Next()
    clasificador=BRepClass3d_SolidClassifier(TopoDS.Solid_s(otro));fallos=0
    for xyz in puntos.values():
        clasificador.Perform(gp_Pnt(*xyz),tolerancia)
        fallos+=clasificador.State()!=TopAbs_ON
    return {'muestras':len(puntos),'no_sobre_frontera':int(fallos),'tolerancia_mm':tolerancia}


def nombre(label):
    atributo=TDataStd_Name()
    return atributo.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),atributo) else ''


def matriz_transformacion(loc):
    tr=loc.Transformation()
    return [[tr.Value(i,j) for j in range(1,5)] for i in range(1,4)]+[[0.,0.,0.,1.]]


def leer_ensamble(path):
    path=Path(path);doc=TDocStd_Document(TCollection_ExtendedString('ensamble'))
    lector=STEPCAFControl_Reader();lector.SetNameMode(True)
    if lector.ReadFile(str(path))!=IFSelect_RetDone or not lector.Transfer(doc):raise ValueError('No se importó ensambleSTEP')
    herramienta=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());raices=TDF_LabelSequence();herramienta.GetFreeShapes(raices)
    hojas=[];arbol=[]
    def recorrer(label,padre,ruta):
        referencia=XCAFDoc_ShapeTool.IsReference_s(label)
        definicion=TDF_Label()
        if referencia:XCAFDoc_ShapeTool.GetReferredShape_s(label,definicion)
        else:definicion=label
        loc=padre.Multiplied(XCAFDoc_ShapeTool.GetLocation_s(label)) if referencia else padre
        nombre_inst=nombre(label);nombre_def=nombre(definicion)
        es_ensamble=XCAFDoc_ShapeTool.IsAssembly_s(definicion)
        nodo=dict(ruta=ruta,nombre_instancia=nombre_inst,nombre_definicion=nombre_def,
            es_ensamble=es_ensamble,es_referencia=referencia,transformacion_acumulada=matriz_transformacion(loc))
        arbol.append(nodo)
        if es_ensamble:
            sec=TDF_LabelSequence();XCAFDoc_ShapeTool.GetComponents_s(definicion,sec,False)
            for i in range(1,sec.Length()+1):recorrer(sec.Value(i),loc,ruta+'/'+str(i))
        else:
            shape=XCAFDoc_ShapeTool.GetShape_s(definicion).Moved(loc)
            ex=TopExp_Explorer(shape,TopAbs_SOLID);j=0
            while ex.More():
                j+=1;hojas.append((TopoDS.Solid_s(ex.Current()),dict(nodo,id=len(hojas)+1,solido_en_instancia=j)))
                ex.Next()
    for i in range(1,raices.Length()+1):recorrer(raices.Value(i),TopLoc_Location(),str(i))
    # Contraste independiente frente a la forma global del lector STEP.
    raw=STEPControl_Reader();raw.ReadFile(str(path));raw.TransferRoots()
    u,a,s=(TColStd_SequenceOfAsciiString() for _ in range(3));raw.FileUnits(u,a,s)
    brutos=[];ex=TopExp_Explorer(raw.OneShape(),TopAbs_SOLID)
    while ex.More():
        pp=GProp_GProps();BRepGProp.VolumeProperties_s(ex.Current(),pp)
        brutos.append(pp.CentreOfMass().Coord());ex.Next()
    centros=[propiedades(shape,info)['centro_masa_geometrico_mm'] for shape,info in hojas]
    error=float(cKDTree(np.array(brutos)).query(np.array(centros))[0].max())
    if len(brutos)!=len(hojas) or error>1e-5:raise ValueError('Transformaciones XCAF no coinciden con sólidos globales STEP')
    return hojas,{'archivo':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'unidades_declaradas':[u.Value(i).ToCString() for i in range(1,u.Length()+1)],
        'error_max_centroides_XCAF_vs_STEP_mm':error,
        'unidades_kernel':'mm','numero_solidos':len(hojas),'estructura_componentes':arbol,
        'nota':'Clasificar por geometría/ubicación; los nombres son evidencia secundaria, no identificación suficiente.'}


def propiedades(solid,info):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(solid,b,False,False);bb=b.Get()
    prop=GProp_GProps();BRepGProp.VolumeProperties_s(solid,prop)
    cilindros=[];planos=[];toros=[];tipos=Counter();ex=TopExp_Explorer(solid,TopAbs_FACE);idcara=0
    while ex.More():
        idcara+=1;a=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()),True);tipo=a.GetType();tipos[str(tipo).split('.')[-1]]+=1
        if tipo==GeomAbs_Cylinder:
            c=a.Cylinder();u=(a.FirstUParameter()+a.LastUParameter())/2
            extremos=[a.Value(u,v).Coord() for v in (a.FirstVParameter(),a.LastVParameter())]
            eje=np.array(c.Axis().Direction().Coord());centro=np.mean(extremos,axis=0)
            # Proyectar a eje; puntos sobre superficie no son centros del cilindro.
            origen=np.array(c.Location().Coord());centro=origen+eje*np.dot(centro-origen,eje)
            cilindros.append(dict(cara=idcara,radio_mm=c.Radius(),eje=eje.tolist(),centro_eje_mm=centro.tolist(),
                largo_mm=abs(a.LastVParameter()-a.FirstVParameter()),
                amplitud_rad=a.LastUParameter()-a.FirstUParameter()))
        if tipo==GeomAbs_Plane:
            pl=a.Plane();planos.append(dict(cara=idcara,normal=list(pl.Axis().Direction().Coord()),punto_mm=list(pl.Location().Coord())))
        if tipo==GeomAbs_Torus:
            t=a.Torus();toros.append(dict(radio_mayor_mm=t.MajorRadius(),radio_menor_mm=t.MinorRadius()))
        ex.Next()
    return dict(info,bbox_mm=list(bb),dimensiones_bbox_mm=[bb[i+3]-bb[i] for i in range(3)],
        volumen_mm3=prop.Mass(),centro_masa_geometrico_mm=list(prop.CentreOfMass().Coord()),
        caras_por_tipo=dict(tipos),cilindros=cilindros,planos=planos,toros=toros)


def analizar(path,matriz_path):
    hojas,meta=leer_ensamble(path)
    inventario=[propiedades(s,i) for s,i in hojas];solidos={i['id']:s for s,i in hojas}
    ref_solid,ref_dim,ref_holes,_,_=extraer(matriz_path)
    candidatos=[p for p in inventario if any(abs(2*c['radio_mm']-ref_dim['diametro_exterior_mm'])<1e-4 for c in p['cilindros'])
                and p['caras_por_tipo'].get('GeomAbs_Cylinder',0)>len(ref_holes)/2]
    if len(candidatos)!=1:raise ValueError('Matriz del ensamble ambigua: '+str([c['id'] for c in candidatos]))
    matriz=candidatos[0];M_inst=np.array(matriz['transformacion_acumulada']);inversa=np.linalg.inv(M_inst)
    local_def=transformar(solidos[matriz['id']],inversa)
    with TemporaryDirectory(prefix='auditoria_instancia_') as tmp:
        fichero=Path(tmp)/'matriz_extraida_del_ensamble.stp';wr=STEPControl_Writer()
        wr.Transfer(local_def,STEPControl_AsIs);wr.Write(str(fichero))
        _,d_inst,h_inst,_,_=extraer(fichero)
    xy=np.array([[h['x_mm'],h['y_mm']] for h in ref_holes]);xya=np.array([[h['x_mm'],h['y_mm']] for h in h_inst])
    error_centros=float(cKDTree(xy).query(xya)[0].max())
    comparados=['diametro_exterior_mm','espesor_total_envolvente_mm','espesor_zona_perforada_mm','diametro_bore_mm','numero_canales']
    iguales=all(math.isclose(ref_dim[k],d_inst[k],abs_tol=1e-5,rel_tol=0) for k in comparados)
    iguales=iguales and ref_dim['diametros_efectivos_mm']==d_inst['diametros_efectivos_mm'] and error_centros<1e-5
    ref_prop=GProp_GProps();BRepGProp.VolumeProperties_s(ref_solid,ref_prop)
    pp=GProp_GProps();BRepGProp.VolumeProperties_s(local_def,pp)
    residuo_vol=abs(pp.Mass()/ref_prop.Mass()-1)
    fronteras=[frontera_muestreada(local_def,ref_solid),frontera_muestreada(ref_solid,local_def)]
    if not iguales or residuo_vol>1e-6 or any(f['no_sobre_frontera'] for f in fronteras):raise ValueError('Matriz/transformación por revisar: '+str({'error_centros':error_centros,'residuo_volumen':residuo_vol,
        'dim_aislada':{k:ref_dim[k] for k in comparados},'dim_instancia':{k:d_inst[k] for k in comparados},
        'ejemplo_ref':xy[:2].tolist(),'ejemplo_inst':xya[:2].tolist()}))
    R=np.array(ref_dim['sistema_local']['base_filas_x_y_z_en_CAD']);o=np.array(ref_dim['sistema_local']['origen_CAD_mm'])
    B=np.eye(4);B[:3,:3]=R;B[:3,3]=-R@o
    T=B@inversa  # Ensamble mundial → sistema LOCAL de matriz aislada.
    Ti=np.linalg.inv(T)
    def punto(p):return (T@np.r_[p,1])[:3]
    def vector(v):return T[:3,:3]@np.array(v)
    # El montaje real ubica los rodillos del lado opuesto al resalte central.
    tipos={};rodillos=[]
    for p in inventario:
        cmax=max(p['cilindros'],key=lambda c:c['radio_mm'],default=None)
        rol='pieza_ambigua';evidencia='Sin clasificación funcional suficiente; revisar visualización y nombre como evidencia secundaria'
        if p['id']==matriz['id']:rol='matriz';evidencia='Geometría, volumen y frontera coincidentes verificados con STEP individual'
        elif cmax and .15*ref_dim['diametro_exterior_mm']<cmax['radio_mm']<.4*ref_dim['diametro_exterior_mm'] and abs(vector(cmax['eje'])[2])<1e-6 and cmax['largo_mm']<2*cmax['radio_mm']:
            rol='rodillo';evidencia='Envolvente cilíndrica perpendicular a normal de matriz, compacta, coaxial con eje transversal'
            centro=punto(cmax['centro_eje_mm']);eje=vector(cmax['eje']);radial=math.hypot(*centro[:2])
            rodillos.append(dict(solido_id=p['id'],centro_CAD_mm=cmax['centro_eje_mm'],centro_local_matriz_mm=centro.tolist(),
                eje_CAD=cmax['eje'],eje_local_matriz=eje.tolist(),diametro_mm=2*cmax['radio_mm'],ancho_mm=cmax['largo_mm'],
                radio_posicion_mm=radial,angulo_rad=math.atan2(centro[1],centro[0]),
                eje_radial_compatible=bool(abs(np.dot(eje[:2],centro[:2]/radial))>1-1e-6),
                geometria='Cilindro envolvente de rodillo ranurado, no contacto real de ranuras con biomasa'))
        elif cmax and abs(cmax['radio_mm']-11)<1e-5 and abs(cmax['largo_mm']-6.4)<1e-4 and any(abs(c['radio_mm']-4)<1e-5 for c in p['cilindros']):
            rol='rodamiento_608_geometrico';evidencia='8×22×7 por cilindros y envolvente; nombreSKF no acredita pieza comprada'
        elif len(p['cilindros'])==1 and cmax and cmax['largo_mm']>10*cmax['radio_mm']:
            rol='eje_transversal' if abs(vector(cmax['eje'])[2])<1e-6 else 'arbol_principal'
            evidencia='Cilindro esbelto y orientación; CAD liso, no rosca resuelta'
        elif len(p['cilindros'])==2 and len(p['planos'])==2:
            rol='arandela';evidencia='Anillo plano y cilindros interior/exterior; función por montaje'
        elif 'ISO 4035' in p['nombre_definicion'] and len(p['planos'])>=6:
            rol='tuerca_declarada_M12';evidencia='Nombre normalizado más caras hexagonales y bore; no verifica compatibilidad con varilla1/2'
        elif cmax and cmax['radio_mm']>ref_dim['diametro_exterior_mm']/2:
            if max(p['dimensiones_bbox_mm'])>2*ref_dim['diametro_exterior_mm'] and p['caras_por_tipo'].get('GeomAbs_Cone',0):
                rol='tolva';evidencia='Recipiente cónico coaxial ensanchado sobre cámara, no solo nombre'
            elif any(abs(c['radio_mm']-3)<1e-5 and abs(vector(c['eje'])[2])<1e-6 for c in p['cilindros']):
                rol='camara_soporte_transversal';evidencia='Cuerpo anular con taladros laterales coaxiales al ejeØ6 y bridas'
            else:rol='carcasa_anular_inferior_candidata';evidencia='Cuerpo anular coaxial bajo matriz; función específica por confirmar, no polea demostrada'
        elif p['caras_por_tipo']=={'GeomAbs_Plane':10} and min(p['dimensiones_bbox_mm'])>10:
            rol='elemento_bastidor';evidencia='Perfil prismático repetido; dimensiones y disposición de estructura'
        elif len(p['cilindros'])==3 and sorted(round(c['radio_mm'],4) for c in p['cilindros'])==[2.5,2.5,6.5]:
            rol='placa_soporte';evidencia='Placa de5mm con bore13 y dos taladros5; función axial no acreditada'
        elif p['volumen_mm3']<100 and len(p['planos'])==6:
            rol='lamina_cuchilla_propuesta';evidencia='Lámina0,5mm cerca de matriz; nombrecuchilla apoya función sin verificar fijación'
        elif 'MANIVELA' in p['nombre_instancia']:
            rol='brazo_manivela';evidencia='Brazo largo, ejes y empuñadura; no relación de transmisión motorizada'
        p['clasificacion']=rol;p['evidencia_clasificacion']=evidencia;tipos.setdefault(rol,[]).append(p['id'])
    if len(rodillos)!=2:raise ValueError('No identificados exactamente dos rodillos por geometría')
    plano=float(np.median([h['z_min_mm'] for h in ref_holes])) # Cara perforada de menorz de aislada.
    normales=[np.sign(r['centro_local_matriz_mm'][2]-plano) for r in rodillos]
    if len(set(normales))!=1:raise ValueError('Rodillos en lados distintos de matriz')
    signo=normales[0]
    for r in rodillos:
        altura=signo*(r['centro_local_matriz_mm'][2]-plano)
        r['altura_centro_sobre_trabajo_mm']=altura;r['separacion_envolvente_matriz_mm']=altura-r['diametro_mm']/2
        distancia=BRepExtrema_DistShapeShape(solidos[r['solido_id']],solidos[matriz['id']]);distancia.Perform()
        r['distancia_min_solidos_mm']=distancia.Value()
    cojinetes=[]
    for p in inventario:
        if p['clasificacion']=='rodamiento_608_geometrico':
            c=max(p['cilindros'],key=lambda c:c['radio_mm']);cojinetes.append(dict(solido_id=p['id'],
                centro_CAD_mm=c['centro_eje_mm'],centro_local_matriz_mm=punto(c['centro_eje_mm']).tolist(),
                diametro_interior_mm=8.,diametro_exterior_mm=22.,ancho_envolvente_mm=float(min(p['dimensiones_bbox_mm']))))
    eje=next(p for p in inventario if p['clasificacion']=='eje_transversal')
    principal=next(p for p in inventario if p['clasificacion']=='arbol_principal')
    # Los alojamientos del rodillo son medidos, no iguales a la dimensión del608.
    montaje=[]
    for rod in rodillos:
        pieza=next(p for p in inventario if p['id']==rod['solido_id'])
        asientos=[c for c in pieza['cilindros'] if abs(c['largo_mm']-7)<1e-4 and c['radio_mm']<rod['diametro_mm']/2]
        detalle_axial=[]
        for asiento in asientos:
            bearing=min(cojinetes,key=lambda b:np.linalg.norm(np.array(b['centro_CAD_mm'])-asiento['centro_eje_mm']))
            diferencia=float(np.dot(np.array(bearing['centro_CAD_mm'])-asiento['centro_eje_mm'],np.array(rod['eje_CAD'])))
            detalle_axial.append(dict(rodamiento_id=bearing['solido_id'],diferencia_centros_axial_mm=diferencia,
                anillo_fuera_de_tramo_axial_asiento_mm=abs(diferencia),nota='Coincidencia axial solamente; la holgura diametral exterior sigue sin resolver'))
        adaptadores=[p['id'] for p in inventario if max(p['dimensiones_bbox_mm'])<rod['diametro_mm'] and len(p['cilindros'])<=4
            and all(abs(np.dot(c['eje'],rod['eje_CAD']))>1-1e-6 for c in p['cilindros'])
            and ({3.,4.}.issubset(set(round(c['radio_mm'],5) for c in p['cilindros']))
                or {11.,12.}.issubset(set(round(c['radio_mm'],5) for c in p['cilindros'])))]
        montaje.append(dict(rodillo_id=rod['solido_id'],diametros_alojamientos_mm=sorted(set(2*c['radio_mm'] for c in asientos)),
            centros_alojamientos_CAD_mm=[c['centro_eje_mm'] for c in asientos],
            diferencia_diametral_alojamiento_608_mm=(2*asientos[0]['radio_mm']-22) if asientos else None,
            diferencia_diametral_608_eje_mm=8-2*eje['cilindros'][0]['radio_mm'],
            detalle_axial=detalle_axial,adaptadores_candidatos=adaptadores,
            adaptador_identificado=bool(adaptadores),estado='Dos interfaces con holgura nominal requieren asiento/adaptador verificable; no resueltas por el nombre de pieza'))
    placas=sorted([p for p in inventario if p['clasificacion']=='placa_soporte'],key=lambda p:p['centro_masa_geometrico_mm'][1])
    inferior=placas[0];fijaciones=[c for c in inferior['cilindros'] if abs(c['radio_mm']-2.5)<1e-5]
    espacio={'placa_candidata_id':inferior['id'],'bbox_CAD_mm':inferior['bbox_mm'],
        'dimensiones_placa_mm':inferior['dimensiones_bbox_mm'],'taladros_fijacion_CAD_mm':[c['centro_eje_mm'] for c in fijaciones],
        'diametros_taladros_mm':[2*c['radio_mm'] for c in fijaciones],
        'separacion_centros_taladros_mm':float(np.linalg.norm(np.array(fijaciones[0]['centro_eje_mm'])-fijaciones[1]['centro_eje_mm'])),
        'diametro_arbol_mm':2*principal['cilindros'][0]['radio_mm'],
        'posicion_axial_definitiva_soporte':None,'rodamiento_presente':False,'tornillos_apoyo_inferior_presentes':False,
        'candidatos_no_seleccionados':['UCF201-8','UCFL201-8'],
        'pendientes':['Ficha dimensional de variante real: bore, altura de centro, flange y patrón de pernos',
            'Comprobar envolvente y distancia a manivela, montaje por arriba/abajo y acceso de apriete',
            'Espesor/material/resistencia de placa y transmisión a bastidor; orientación y reparto de empuje',
            'No inferir empotramiento ni fijación axial suficiente del soporte ausente']}
    manivela=next((p for p in inventario if p['clasificacion']=='brazo_manivela'),None)
    if manivela:
        espacio['separacion_placa_inferior_a_envolvente_manivela_mm']=inferior['bbox_mm'][1]-manivela['bbox_mm'][4]
    camara=next((p for p in inventario if p['clasificacion']=='camara_soporte_transversal'),None)
    taladros=[]
    if camara:
        taladros=[dict(c,centro_local_matriz_mm=punto(c['centro_eje_mm']).tolist()) for c in camara['cilindros']
                  if abs(c['radio_mm']-3)<1e-5 and abs(vector(c['eje'])[2])<1e-6]
    return {'meta':meta,'inventario':inventario,'clasificacion':tipos,'matriz_id':matriz['id'],
        'correspondencia_matriz':{'coincide':iguales and residuo_vol<1e-6,'error_max_centros_mm':error_centros,
            'residuo_volumen_relativo':residuo_vol,'fronteras_bidireccionales':fronteras,'transformacion_instancia_CAD':M_inst.tolist(),
            'ensamble_a_local_matriz':T.tolist(),'local_matriz_a_ensamble':Ti.tolist(),
            'metodo':'Transformación XCAF verificada contra geometría, volumen y frontera muestreada bidireccional; no supuesto de origen común'},
        'rodillos':rodillos,'plano_trabajo_local_z_mm':plano,'normal_trabajo_local':[0,0,float(signo)],
        'rodamientos':cojinetes,'eje_transversal':eje,'arbol_principal':principal,
        'montaje_608':montaje,'apoyo_inferior':espacio,'transmision':{'relacion_real':None,'motor_CAD_identificado':False,
            'nota':'Se reconoce manivela, no par de poleas/engranajes con diámetros primitivos y accionamiento motorizado definidos.'},
        'taladros_soporte_transversal':taladros,
        'incompatibilidades':['Eje transversalCADØ6x160 frente longitud nominal previa100mm; CAD no modela raíz de rosca.',
            '608Ø8 sobre ejeØ6 y alojamientos de rodilloØ24 frente608Ø22: dos diferencias diametrales2mm, sin adaptador identificado.',
            'TuercasCADdeclaradasM12 sobre árbolØ12,7: verificar familia y paso; no equivalenciaM12/1/2pulgada.',
            'NombreSKFdel modelo de608 no acredita fabricante comprado, capacidades ni materialidad física.']},solidos


if __name__=='__main__':
    import json
    p=Path(__file__).resolve().parents[1]/'geometrias/Prototipo.stp'
    hojas,meta=leer_ensamble(p)
    print('SOLIDOS',len(hojas))
    for s,i in hojas:
        d=propiedades(s,i)
        print(json.dumps({k:d[k] for k in ('id','nombre_instancia','nombre_definicion','dimensiones_bbox_mm','centro_masa_geometrico_mm','volumen_mm3','caras_por_tipo')},ensure_ascii=False))
        print('Cilindros:',[(round(c['radio_mm'],4),round(c['largo_mm'],3),[round(v,3) for v in c['eje']]) for c in d['cilindros'][:12]])
