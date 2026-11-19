import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pytest
from peletizadora.cad import extraer,intervalos_unidos
from peletizadora import legado
from peletizadora.nucleo import cargas_angulares,requisitos_carga
from peletizadora.verificaciones import resolver_viga,vida_bolas,presion_canal,balance_potencia
from simular import RAIZ,cargar_configuracion,ejecutar,regresion_real
from herramientas.control_cambios import verificar


@pytest.fixture(scope='module')
def geometria():
    return {m:extraer(RAIZ/'geometrias'/f'Matriz_{m}.stp') for m in ('real','prototipo')}


@pytest.mark.parametrize('modelo,diam,alto,bore,L,gap',[
    ('real',200,36,50,31.5,6.422),('prototipo',99,26,13,10,1.36)])
def test_step_importado_y_dimensiones(geometria,modelo,diam,alto,bore,L,gap):
    _,d,a,pares,caras=geometria[modelo]
    assert d['unidades_declaradas_STEP']==['millimetre']
    assert d['unidad_kernel']=='mm' and d['geometria_valida']
    assert d['diametro_exterior_mm']==pytest.approx(diam)
    assert d['espesor_total_envolvente_mm']==pytest.approx(alto)
    assert d['diametro_bore_mm']==pytest.approx(bore)
    assert d['longitudes_cilindricas_restrictivas_mm']==[L]
    assert d['ligamento_min_cilindrico_mm']==pytest.approx(gap)
    assert len(a)==102 and d['numero_canales']==102
    assert d['validacion_pasantes']
    assert all(v==102 for v in d['cuenta_independiente_circulos_por_plano'].values())
    assert all(h['pasante_verificado'] and h['diametro_efectivo_mm']==6 for h in a)
    assert len(pares)==102*101//2
    assert d['area_abierta_efectiva_mm2']==pytest.approx(102*math.pi*3**2)


def test_avellanados_y_filetes_no_son_perforaciones(geometria):
    real=geometria['real'];proto=geometria['prototipo']
    assert real[1]['numero_transiciones_conicas']==102
    assert all(h['numero_avellanados']==1 and h['diametro_boca_mm']==9 for h in real[2])
    assert all(h['longitud_boca_cilindrica_mm']==pytest.approx(3) for h in real[2])
    assert all(h['longitud_transicion_conica_mm']==pytest.approx(1.5) for h in real[2])
    assert len(real[1]['superficies_para_revision'])==2
    assert all(f['radio_mm']==.25 and not f['angular_completa'] for f in real[1]['superficies_para_revision'])
    assert proto[1]['numero_transiciones_conicas']==0
    assert proto[1]['caras_por_tipo']['GeomAbs_Torus']==4
    assert all(h['recorrido_axial_total_mm']==10 for h in proto[2])


def test_arcos_compartidos_no_se_cuentan_dos_veces():
    assert intervalos_unidos([(0,math.pi),(math.pi,2*math.pi),(0,1)])==[[0,2*math.pi]]


def test_extraccion_no_impone102_y_detecta_familias_auxiliares(tmp_path):
    # Geometría exclusivamente sintética de prueba, nunca usada como una matriz del equipo.
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
    from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
    from OCP.Interface import Interface_Static
    base=BRepPrimAPI_MakeCylinder(10,5).Shape()
    centro=BRepPrimAPI_MakeCylinder(1,5).Shape()
    hueco=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(5,0,0),gp_Dir(0,0,1)),.5,5).Shape()
    pieza=BRepAlgoAPI_Cut(BRepAlgoAPI_Cut(base,centro).Shape(),hueco).Shape()
    for nombre,shape,numero in [('un_canal',pieza,1),('dos_familias',BRepAlgoAPI_Cut(pieza,
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(-5,0,0),gp_Dir(0,0,1)),.75,5).Shape()).Shape(),2)]:
        path=tmp_path/(nombre+'.stp');w=STEPControl_Writer();Interface_Static.SetCVal_s('write.step.unit','MM')
        w.Transfer(shape,STEPControl_AsIs);w.Write(str(path))
        _,d,_,_,_=extraer(path)
        assert d['numero_canales']==numero
        assert d['clasificacion_funcional_ambigua']==(numero==2)
        assert d['diametro_exterior_mm']==pytest.approx(20)
        assert d['validacion_pasantes']


def test_no_patron_escalado_y_marco_explicito(geometria):
    a=np.array([[h['x_mm'],h['y_mm']] for h in geometria['real'][2]])
    b=np.array([[h['x_mm'],h['y_mm']] for h in geometria['prototipo'][2]])
    from scipy.spatial import cKDTree
    assert cKDTree(a*.5).query(b)[0].max()>1
    R=np.array(geometria['prototipo'][1]['sistema_local']['base_filas_x_y_z_en_CAD'])
    assert np.allclose(R@R.T,np.eye(3)) and np.linalg.det(R)==pytest.approx(1)
    assert np.allclose(R,[[1,0,0],[0,0,-1],[0,1,0]])


def test_configuraciones_independientes_sin_posiciones_heredadas():
    r=cargar_configuracion('real');p=cargar_configuracion('prototipo')
    assert r['rodillos']['centros_radiales_m']==[.0635,.0635]
    assert p['rodillos']['centros_radiales_m'] is None
    assert p['rodillos']['espesor_biomasa_m'] is None
    assert p['torque']['mu_efectivo'] is None
    assert p['operacion']['rpm_matriz'] is None
    assert p['operacion']['rpm_motor']==1350 and p['operacion']['potencia_motor_w']==180
    p['numerico']['estados']=16
    assert cargar_configuracion('real')['numerico']['estados']==1440
    assert requisitos_carga(p)


def test_funciones_matematicas_no_duplicadas():
    from modelos.superposicion import interseccion_disco_rectangulo
    from modelos.torque import contribuciones_torque_nm,potencia_resistente_w
    assert legado.interseccion_disco_rectangulo is interseccion_disco_rectangulo
    assert legado.contribuciones_torque_nm is contribuciones_torque_nm
    assert legado.potencia_resistente_w is potencia_resistente_w
    area,_,_=interseccion_disco_rectangulo(np.array([[0.,0.]]),.003,(0,.01,-.01,.01),128)
    assert area[0]==pytest.approx(math.pi*.003**2/2,rel=1e-5)


def test_rechaza_cargas_sin_montaje(geometria):
    with pytest.raises(ValueError,match='Cargas pendientes'):
        cargas_angulares(geometria['prototipo'][2],cargar_configuracion('prototipo'))


def test_equilibrio_torque_potencia_y_regresion1440(geometria,tmp_path):
    cfg=cargar_configuracion('real');df,_=cargas_angulares(geometria['real'][2],cfg)
    assert len(df)==1440 and df.angulo_grados.iloc[-1]==359.75
    assert np.allclose(df.fuerza_r1_n+df.fuerza_r2_n,df.fuerza_total_n)
    assert np.allclose(df.torque_r1_nm+df.torque_r2_nm,df.torque_total_nm)
    assert np.allclose(df.potencia_w,df.torque_total_nm*2*math.pi*516/60)
    reg=regresion_real(cfg,geometria['real'][2],df,tmp_path)
    assert reg['coincide_2C_numerico']
    assert reg['distancia_max_centros_STEP_vs_CSV_EP2_mm']<1e-6
    assert reg['fuerza_total_n_error_abs_max']<1e-5
    assert df.fuerza_total_n.max()==pytest.approx(14432.817684259224)


def test_nucleo_unico_con_configuracion_sintetica_explicita(geometria):
    # No es montaje del prototipo: usar una copia de configREAL con solo12estados.
    cfg=cargar_configuracion('real');cfg['numerico']['estados']=12
    df,_=cargas_angulares(geometria['real'][2],cfg)
    cfg['presion']['valor_pa']*=2
    doble,_=cargas_angulares(geometria['real'][2],cfg)
    assert np.allclose(doble.fuerza_total_n,2*df.fuerza_total_n)
    assert np.allclose(doble.torque_total_nm,2*df.torque_total_nm)


def test_viga_y_rodamientos_solo_con_argumentos_propios():
    L=.1;E=200e9;diam=.005;F=1;I=math.pi*diam**4/64
    nodos=np.linspace(0,L,11);f=np.zeros((22,1));f[10,0]=-F
    seg=[dict(nombre='sintetico',x_inicio_m=0,x_fin_m=L,diametro_exterior_m=diam)]
    s,u=resolver_viga(nodos,seg,E,f,[0,20],'Caso sintético de prueba, no máquina')
    assert abs(u.desplazamientos[10,0])==pytest.approx(F*L**3/(48*E*I))
    with pytest.raises(ValueError):resolver_viga(nodos,seg,E,f,[0,20],None)
    with pytest.raises(ValueError):vida_bolas([100,100],1000,500,100,None,'sintetico')
    r=vida_bolas([100,100],1000,500,100,0,'sintetico')
    assert r['L10_millones']==pytest.approx(1000) and r['S0']==5
    assert presion_canal(1e6,.2,.3,.01,.006)==pytest.approx(1e6/.3*math.expm1(4*.2*.3*10/6))
    b=balance_potencia(180,.8,100,80)
    assert b['potencia_disponible_w']==144 and b['margen_maximo_w']==pytest.approx(44)


def test_retiro_reversible_y_conservacion():
    r=verificar()
    assert r['alterados']==0 and r['archivos_anteriores_verificados']==486
    assert not (RAIZ.parent/'Prototipo/parametros.json').exists()
    assert (RAIZ.parent/'archivo/Prototipo_escalado_2026_11_18/test_prototipo.py').exists()
    assert (RAIZ.parent/'archivo/Prototipo_escalado_2026_11_18/referencias.bib').exists()


def test_cli_prototipo_genero_solo_auditoria_y_pendientes():
    # Comprobar entregables reales, sin ejecutar otra visualización costosa.
    p=RAIZ/'resultados/prototipo/resumen.json'
    assert p.is_file()
    r=json.loads(p.read_text(encoding='utf-8'))
    assert r['estado']=='pendiente_datos_contacto' and r['cargas'] is None
    assert not r['seguridad_estructural_aprobada']
    assert not (p.parent/'historial_cargas.csv').exists()
    with pytest.raises(ValueError):ejecutar('real',salida=RAIZ.parent/'Simulación_peletizadora/resultados')


def test_no_sobrescribir_resultados_de_otra_configuracion(tmp_path):
    (tmp_path/'parametros_utilizados.json').write_text(json.dumps(cargar_configuracion('real')),encoding='utf-8')
    with pytest.raises(ValueError,match='otra configuración'):
        ejecutar('prototipo',salida=tmp_path)
