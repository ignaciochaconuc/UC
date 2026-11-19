"""Auditoría topológica OpenCascade. Longitudes de salida en mm.

La cantidad esperada de perforaciones NO interviene en la clasificación.
Se agrupan superficies coaxiales, se distingue material/vacío y se
contrasta la cuenta con circunferencias de borde independientes.
"""
import hashlib
import math
from collections import Counter
from pathlib import Path
import numpy as np
from OCP.STEPControl import STEPControl_Reader
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_EDGE, TopAbs_IN, TopAbs_OUT
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Plane, GeomAbs_Circle, GeomAbs_Torus
from OCP.TColStd import TColStd_SequenceOfAsciiString
from OCP.gp import gp_Pnt
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

TOL=1e-5  # mm, tolerancia de agrupación numérica, NO tolerancia de fabricación


def importar(path):
    path=Path(path)
    Interface_Static.SetCVal_s('xstep.cascade.unit','MM')
    reader=STEPControl_Reader()
    if reader.ReadFile(str(path))!=IFSelect_RetDone:
        raise ValueError('STEP no importable: '+str(path))
    longitudes,angulos,solidos=(TColStd_SequenceOfAsciiString() for _ in range(3))
    reader.FileUnits(longitudes,angulos,solidos)
    unidades=[longitudes.Value(i).ToCString() for i in range(1,longitudes.Length()+1)]
    reader.TransferRoots();shape=reader.OneShape()
    ex=TopExp_Explorer(shape,TopAbs_SOLID);lista=[]
    while ex.More(): lista.append(TopoDS.Solid_s(ex.Current()));ex.Next()
    if len(lista)!=1:
        raise ValueError('Se requiere una matriz sólida única; sólidos encontrados: '+str(len(lista)))
    if not BRepCheck_Analyzer(lista[0]).IsValid():
        raise ValueError('BRep inválido; no continuar con cargas')
    return lista[0],{'unidades_declaradas_STEP':unidades,'unidad_kernel':'mm','numero_solidos':len(lista),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archivo':path.name,
        'observacion':'Se usa el sólido; curvas auxiliares de presentación no se cuentan como piezas o agujeros.'}


def caras(solid):
    ex=TopExp_Explorer(solid,TopAbs_FACE);lista=[]
    while ex.More():
        lista.append(TopoDS.Face_s(ex.Current()));ex.Next()
    return lista


def estado(solid,xyz):
    return BRepClass3d_SolidClassifier(solid,gp_Pnt(*map(float,xyz)),1e-7).State()


def intervalos_unidos(intervalos):
    union=[]
    for a,b in sorted(intervalos):
        if not union or a>union[-1][1]+TOL: union.append([a,b])
        else: union[-1][1]=max(b,union[-1][1])
    return union


def extraer(path):
    solid,meta=importar(path);faces=caras(solid)
    clasificador=BRepClass3d_SolidClassifier(solid)
    def pertenece(xyz):
        clasificador.Perform(gp_Pnt(*map(float,xyz)),1e-7)
        return clasificador.State()
    adaptadores=[BRepAdaptor_Surface(f,True) for f in faces]
    cilindros=[a for a in adaptadores if a.GetType()==GeomAbs_Cylinder]
    if not cilindros: raise ValueError('No hay cilindros identificables')
    mayor=max(cilindros,key=lambda a:a.Cylinder().Radius()).Cylinder()
    n=np.array(mayor.Axis().Direction().Coord())
    if n[np.argmax(abs(n))]<0:n=-n
    x=np.array([1.,0.,0.]);x=x-n*np.dot(x,n)
    if np.linalg.norm(x)<1e-8:x=np.array([0.,1.,0.])-n*n[1]
    x/=np.linalg.norm(x);y=np.cross(n,x)
    centro=np.array(mayor.Location().Coord());centro-=n*np.dot(centro,n)
    R=np.array([x,y,n])
    def local(xyz):return R@(np.array(xyz)-centro)
    inventario=[];internos=[];conos=[];centrales=[];dudosas=[];bordes={}
    for idx,a in enumerate(adaptadores,1):
        tipo=a.GetType();fila={'cara_id':idx,'tipo':str(tipo).split('.')[-1]}
        if tipo in (GeomAbs_Cylinder,GeomAbs_Cone):
            c=a.Cylinder() if tipo==GeomAbs_Cylinder else a.Cone()
            eje=np.array(c.Axis().Direction().Coord());loc=local(c.Location().Coord())
            paralela=abs(np.dot(eje,n))>1-1e-8
            radio=c.Radius() if tipo==GeomAbs_Cylinder else c.RefRadius()
            um=(a.FirstUParameter()+a.LastUParameter())/2
            vm=(a.FirstVParameter()+a.LastVParameter())/2
            superficie=np.array(a.Value(um,vm).Coord())
            eje_pt=np.array(c.Location().Coord());eje_pt+=eje*np.dot(superficie-eje_pt,eje)
            radial=superficie-eje_pt;radial/=np.linalg.norm(radial)
            menos=pertenece(superficie-radial*.001);mas=pertenece(superficie+radial*.001)
            interna=menos==TopAbs_OUT and mas==TopAbs_IN
            z=sorted([float(local(a.Value(um,v).Coord())[2]) for v in (a.FirstVParameter(),a.LastVParameter())])
            completa=a.LastUParameter()-a.FirstUParameter()>=2*math.pi-1e-6
            fila.update(x_mm=float(loc[0]),y_mm=float(loc[1]),radio_mm=radio,
                z_min_mm=z[0],z_max_mm=z[1],angular_completa=completa,
                axial=bool(paralela),superficie_interna=bool(interna))
            if tipo==GeomAbs_Cone:fila['semiangulo_grados']=math.degrees(c.SemiAngle())
            if paralela and math.hypot(loc[0],loc[1])<TOL:
                fila['clasificacion']='bore_central' if interna else 'exterior_coaxial'
                centrales.append(fila)
            elif paralela and completa and interna:
                fila['clasificacion']='candidato_canal' if tipo==GeomAbs_Cylinder else 'transicion_canal'
                (internos if tipo==GeomAbs_Cylinder else conos).append(fila)
            else:
                fila['clasificacion']='superficie_parcial_o_auxiliar_revisar_no_contada_como_agujero'
                dudosas.append(fila)
        elif tipo==GeomAbs_Plane:
            plano=a.Plane();paralela=abs(np.dot(np.array(plano.Axis().Direction().Coord()),n))>1-1e-8
            fila['paralela_plato']=bool(paralela)
            if paralela:
                z=float(local(plano.Location().Coord())[2]);fila['z_mm']=z
                ex=TopExp_Explorer(faces[idx-1],TopAbs_EDGE)
                while ex.More():
                    curva=BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
                    if curva.GetType()==GeomAbs_Circle:
                        c=curva.Circle();cc=local(c.Location().Coord())
                        if math.hypot(cc[0],cc[1])>TOL:
                            clave=tuple(np.round(cc,5))+(round(c.Radius(),5),)
                            b=bordes.setdefault(clave,dict(x_mm=float(cc[0]),y_mm=float(cc[1]),z_mm=z,
                                radio_mm=c.Radius(),cara_id=idx,arcos=[]))
                            valores=np.array([local(curva.Value(float(t)).Coord()) for t in np.linspace(curva.FirstParameter(),curva.LastParameter(),17)])
                            theta=np.unwrap(np.arctan2(valores[:,1]-cc[1],valores[:,0]-cc[0]))
                            inicio=float(min(theta[0],theta[-1])%(2*math.pi));ancho=float(abs(theta[-1]-theta[0]))
                            if ancho>=2*math.pi-1e-6:b['arcos'].append([0.,2*math.pi])
                            elif inicio+ancho<=2*math.pi:b['arcos'].append([inicio,inicio+ancho])
                            else:b['arcos'].extend([[inicio,2*math.pi],[0.,inicio+ancho-2*math.pi]])
                    ex.Next()
        elif tipo==GeomAbs_Torus:
            t=a.Torus();fila.update(clasificacion='redondeo_toroidal',radio_mayor_mm=t.MajorRadius(),radio_menor_mm=t.MinorRadius(),
                                   centro_CAD_mm=list(t.Location().Coord()))
        else:
            fila['clasificacion']='tipo_no_resuelto';dudosas.append(fila)
        inventario.append(fila)
    # Una circunferencia puede estar dividida en varios EDGE_CURVE: unir arcos,
    # no exigir que cada arista sea por sí sola un círculo de360°.
    for b in bordes.values():
        b['cobertura_angular_rad']=sum(v-u for u,v in intervalos_unidos(b['arcos']))
    bordes={k:b for k,b in bordes.items() if b['cobertura_angular_rad']>=2*math.pi-1e-5}
    grupos=[]
    for f in internos:
        grupo=next((g for g in grupos if math.hypot(g['x']-f['x_mm'],g['y']-f['y_mm'])<TOL),None)
        if grupo is None:
            grupo=dict(x=f['x_mm'],y=f['y_mm'],caras=[]);grupos.append(grupo)
        grupo['caras'].append(f)
    for g in grupos:
        g['conos']=[c for c in conos if math.hypot(g['x']-c['x_mm'],g['y']-c['y_mm'])<TOL]
    agujeros=[]
    for ident,g in enumerate(sorted(grupos,key=lambda g:(g['y'],g['x'])),1):
        cilindros=g['caras'];radio=min(f['radio_mm'] for f in cilindros)
        estrechos=[f for f in cilindros if abs(f['radio_mm']-radio)<TOL]
        todos=cilindros+g['conos'];union=intervalos_unidos([(f['z_min_mm'],f['z_max_mm']) for f in todos])
        z0=min(f['z_min_mm'] for f in todos);z1=max(f['z_max_mm'] for f in todos)
        estrecha=intervalos_unidos([(f['z_min_mm'],f['z_max_mm']) for f in estrechos])
        bordes_canal=[b for b in bordes.values() if math.hypot(g['x']-b['x_mm'],g['y']-b['y_mm'])<TOL]
        entrada_salida=all(any(abs(b['z_mm']-z)<TOL for b in bordes_canal) for z in (z0,z1))
        vacio=all(pertenece(centro+R.T@np.array([g['x'],g['y'],z]))==TopAbs_OUT
                  for z in np.linspace(z0-.001,z1+.001,13))
        pasante=len(union)==1 and entrada_salida and vacio
        if not pasante:
            dudosas.append({'grupo_id':ident,'motivo':'No comprobado como canal pasante mediante contornos extremos y vacío axial'})
        agujeros.append(dict(id=ident,x_mm=g['x'],y_mm=g['y'],radio_posicion_mm=math.hypot(g['x'],g['y']),
            angulo_grados=math.degrees(math.atan2(g['y'],g['x']))%360,diametro_efectivo_mm=2*radio,
            diametro_boca_mm=2*max(f['radio_mm'] for f in cilindros),
            longitud_cilindrica_restrictiva_mm=sum(b-a for a,b in estrecha),
            longitud_boca_cilindrica_mm=sum(f['z_max_mm']-f['z_min_mm'] for f in cilindros if f['radio_mm']>radio+TOL),
            longitud_transicion_conica_mm=sum(f['z_max_mm']-f['z_min_mm'] for f in g['conos']),
            recorrido_axial_total_mm=z1-z0,z_min_mm=z0,z_max_mm=z1,
            numero_avellanados=len(g['conos']),pasante_verificado=pasante,
            caras_cilindricas=[f['cara_id'] for f in cilindros],caras_conicas=[f['cara_id'] for f in g['conos']],
            numero_contornos_circulares_extremos=len(bordes_canal)))
    # Cuenta independiente: centros únicos de círculos no centrales en cada plano extremo.
    por_plano={}
    for b in bordes.values():por_plano.setdefault(round(b['z_mm'],5),set()).add((round(b['x_mm'],5),round(b['y_mm'],5)))
    b=Bnd_Box();BRepBndLib.AddOptimal_s(solid,b,False,False);bounds=b.Get()
    tr=gp_Trsf();tras=-R@centro
    tr.SetValues(*[float(v) for fila,t in zip(R,tras) for v in (*fila,t)])
    local_shape=BRepBuilderAPI_Transform(solid,tr,True).Shape()
    bb=Bnd_Box();BRepBndLib.AddOptimal_s(local_shape,bb,False,False)
    zglobal=[bb.Get()[2],bb.Get()[5]]
    bore=[f for f in centrales if f['clasificacion']=='bore_central']
    if not agujeros or not bore:raise ValueError('No identificados canales/bore; revisión manual necesaria')
    xy=np.array([[h['x_mm'],h['y_mm']] for h in agujeros]);diam=np.array([h['diametro_efectivo_mm'] for h in agujeros])
    pares=[]
    for i in range(len(agujeros)):
        for j in range(i+1,len(agujeros)):
            distancia=float(np.linalg.norm(xy[i]-xy[j]))
            pares.append(dict(id1=i+1,id2=j+1,distancia_centros_mm=distancia,
                ligamento_cilindrico_mm=distancia-(diam[i]+diam[j])/2,
                ligamento_bocas_mm=distancia-(agujeros[i]['diametro_boca_mm']+agujeros[j]['diametro_boca_mm'])/2))
    centro_bore=min(f['radio_mm'] for f in bore)*2
    familias=Counter((round(h['diametro_efectivo_mm'],6),round(h['longitud_cilindrica_restrictiva_mm'],6),
                      round(h['recorrido_axial_total_mm'],6)) for h in agujeros)
    dimensiones={**meta,'diametro_exterior_mm':2*mayor.Radius(),
        'espesor_total_envolvente_mm':float(max(zglobal)-min(zglobal)),
        'espesor_zona_perforada_mm':max(h['recorrido_axial_total_mm'] for h in agujeros),
        'diametro_bore_mm':centro_bore,'numero_canales':len(agujeros),
        'diametros_efectivos_mm':sorted(set(round(h['diametro_efectivo_mm'],8) for h in agujeros)),
        'longitudes_cilindricas_restrictivas_mm':sorted(set(round(h['longitud_cilindrica_restrictiva_mm'],8) for h in agujeros)),
        'relaciones_Lcil_D':sorted(set(round(h['longitud_cilindrica_restrictiva_mm']/h['diametro_efectivo_mm'],8) for h in agujeros)),
        'area_abierta_efectiva_mm2':float(np.sum(np.pi*diam**2/4)),
        'distancia_min_centros_mm':min((p['distancia_centros_mm'] for p in pares),default=None),
        'ligamento_min_cilindrico_mm':min((p['ligamento_cilindrico_mm'] for p in pares),default=None),
        'ligamento_min_bocas_mm':min((p['ligamento_bocas_mm'] for p in pares),default=None),
        'numero_transiciones_conicas':len(conos),'cuenta_independiente_circulos_por_plano':{str(k):len(v) for k,v in por_plano.items()},
        'sistema_local':{'origen_CAD_mm':centro.tolist(),'base_filas_x_y_z_en_CAD':R.tolist(),
            'definicion':'local=R@(CAD-origen), dextrógiro; z es normal canónica a la matriz. No supone orientación del ensamble.'},
        'bbox_CAD_mm':list(bounds),'caras_por_tipo':dict(Counter(f['tipo'] for f in inventario)),
        'validacion_pasantes':all(h['pasante_verificado'] for h in agujeros),
        'geometria_valida':True,'superficies_para_revision':dudosas,
        'familias_de_canales':[{ 'diametro_mm':k[0],'Lcil_mm':k[1],'recorrido_mm':k[2],'cantidad':v} for k,v in familias.items()],
        'clasificacion_funcional_ambigua':len(familias)>1,
        'bore_central_no_circular':any(not f.get('angular_completa',True) for f in bore),
        'bore_y_resaltes_coaxiales':centrales,
        'advertencias':['Longitud cilíndrica restrictiva no equivale por sí sola a longitud de fricción calibrada o presión de extrusión.',
            'Caras parciales auxiliares se reportan, no se convierten en agujeros adicionales.',
            'La geometría de matriz no determina posiciones de rodillos, material ni apoyos.']}
    if len(familias)>1:
        dimensiones['advertencias'].append('Hay familias distintas de pasos: revisar función de posibles perforaciones auxiliares antes de aplicar cargas.')
    if pares and min(p['ligamento_cilindrico_mm'] for p in pares)<=0:
        dimensiones['advertencias'].append('Intersección/tangencia de canales: no calcular cargas sin revisión')
    return solid,dimensiones,agujeros,pares,inventario
