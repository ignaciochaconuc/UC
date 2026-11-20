import copy
import json
import numpy as np
import pytest
from simular import RAIZ,cargar_configuracion
from peletizadora.ensamble import analizar
from peletizadora.escenarios_ensamble import incorporar_montaje
from peletizadora.cad import extraer
from peletizadora.nucleo import cargas_angulares
from herramientas.control_ensamble import verificar


@pytest.fixture(scope='module')
def montaje():
    return analizar(RAIZ/'geometrias/Prototipo.stp',RAIZ/'geometrias/Matriz_prototipo.stp')[0]


def test_lectura_y_clasificacion(montaje):
    assert montaje['meta']['numero_solidos']==39
    assert len(montaje['inventario'])==39
    assert len(montaje['rodillos'])==2
    assert len(montaje['rodamientos'])==4
    assert montaje['meta']['unidades_declaradas']==['millimetre']
    assert montaje['meta']['error_max_centroides_XCAF_vs_STEP_mm']<1e-6
    assert montaje['meta']['sha256']=='673f539ad5a94baa0a41d790fd4d92e4dec35df40ca4392c66db746a2a673b83'


def test_transformacion_y_correspondencia(montaje):
    c=montaje['correspondencia_matriz']
    assert c['coincide'] and c['error_max_centros_mm']<1e-8
    assert c['residuo_volumen_relativo']<1e-8
    assert np.allclose(np.array(c['ensamble_a_local_matriz'])@np.array(c['local_matriz_a_ensamble']),np.eye(4))


@pytest.mark.parametrize('indice,radio',[(0,27.8380640336),(1,27.6619359664)])
def test_posiciones_y_unidades(montaje,indice,radio):
    r=montaje['rodillos'][indice]
    assert r['radio_posicion_mm']==pytest.approx(radio)
    assert r['diametro_mm']==pytest.approx(52)
    assert r['ancho_mm']==pytest.approx(30)
    assert r['separacion_envolvente_matriz_mm']==pytest.approx(.5)
    assert r['eje_radial_compatible']


def test_incompatibilidades_no_resueltas(montaje):
    for m in montaje['montaje_608']:
        assert m['diferencia_diametral_alojamiento_608_mm']==pytest.approx(2)
        assert m['diferencia_diametral_608_eje_mm']==pytest.approx(2)
        assert not m['adaptador_identificado']
    assert montaje['eje_transversal']['cilindros'][0]['largo_mm']==pytest.approx(160)


def test_apoyo_ausente_y_transmision(montaje):
    a=montaje['apoyo_inferior']
    assert not a['rodamiento_presente']
    assert a['posicion_axial_definitiva_soporte'] is None
    assert len(a['candidatos_no_seleccionados'])==2
    assert a['separacion_centros_taladros_mm']==pytest.approx(40)
    assert a['diametro_arbol_mm']==pytest.approx(12.7)
    assert montaje['transmision']['relacion_real'] is None


def test_independencia_configuraciones(montaje):
    original=cargar_configuracion('prototipo');copia=copy.deepcopy(original)
    real=cargar_configuracion('real');resuelto=incorporar_montaje(original,montaje)
    assert original==copia
    assert original['rodillos']['centros_radiales_m'] is None
    assert resuelto['rodillos']['centros_radiales_m'][0]==pytest.approx(.0278380640336)
    assert real==cargar_configuracion('real')
    assert resuelto['operacion']['rpm_matriz'] is None
    assert not resuelto['rodillos']['contacto_documentado']


def test_limite_sin_contacto_y_equilibrio(montaje):
    cfg=incorporar_montaje(cargar_configuracion('prototipo'),montaje)
    cfg['numerico']['estados']=8
    cfg['rodillos'].update(contacto_escenario_explicito=True,espesor_biomasa_m=.0001)
    cfg['torque']['mu_efectivo']=.1
    agujeros=extraer(RAIZ/cfg['step'])[2]
    df,_=cargas_angulares(agujeros,cfg)
    assert (df.fuerza_total_n==0).all()
    cfg['rodillos']['espesor_biomasa_m']=.002
    cfg['operacion']['rpm_matriz']=120
    df,_=cargas_angulares(agujeros,cfg)
    assert np.allclose(df.fuerza_total_n,df.fuerza_r1_n+df.fuerza_r2_n)
    assert np.allclose(df.torque_total_nm,df.torque_r1_nm+df.torque_r2_nm)
    assert np.allclose(df.potencia_w,df.torque_total_nm*4*np.pi)
    assert (df.perforaciones_parciales_r1>0).any()
    from peletizadora.escenarios_ensamble import ejecutar_escenarios
    cfg['sensibilidades_ensamble']['eficiencia_mecanica']=[1.1]
    with pytest.raises(ValueError,match='Eficiencia'):
        ejecutar_escenarios(cfg,agujeros,montaje,None)


def test_conservacion():
    assert verificar()['protegidos_intactos']
