import copy
import hashlib
import json
from pathlib import Path
import pytest
from simulacion_transmision import RAIZ
from simulacion_chavetas import leer_json
from simulacion_compatibilidad_motor import ejecutar
from transmision.motores import cabida_axial, comparar_motor, comprobar_carga_radial


def datos():
    return (leer_json(RAIZ/'parametros_motores.json')['motores'],
            leer_json(RAIZ/'parametros_poleas.json')['poleas']['motriz'])


def test_comparacion_nominal_no_infiere_marathon():
    motores,polea=datos()
    bevi,marathon=[comparar_motor(m,polea,1450) for m in motores]
    assert all(r['coincide_agujero_nominal'] for r in (bevi,marathon))
    assert bevi['coincide_ancho_nominal'] is True
    assert marathon['coincide_ancho_nominal'] is None
    assert bevi['diferencia_rpm']==20 and marathon['diferencia_rpm']==25
    assert bevi['diferencia_rpm_porcentaje']==pytest.approx(100*20/1450)
    assert not bevi['chaveta_resistencia_aprobada']
    assert not marathon['motor_seleccionado']


def test_incompatibilidad_sintetica_no_oculta():
    motores,polea=datos()
    m=copy.deepcopy(motores[0]);m['diametro_eje_mm']=35;m['ancho_chavetero_mm']=8
    r=comparar_motor(m,polea,1450)
    assert not r['coincide_agujero_nominal'] and not r['coincide_ancho_nominal']


def test_axial_necesaria_no_es_contacto_activo():
    r=cabida_axial(80,62)
    assert r['diferencia_extension_envolvente_mm']==18
    assert r['cabe_en_posicion_propuesta'] is None
    assert r['longitud_contacto_efectiva_mm'] is None
    assert cabida_axial(80,62,18)['cabe_en_posicion_propuesta']
    assert not cabida_axial(80,62,19)['cabe_en_posicion_propuesta']
    assert not cabida_axial(60,62)['cabe_envolvente_en_longitud_nominal']


@pytest.mark.parametrize('args',[(0,62,None),(80,-1,None),(80,62,-1),(float('nan'),62,None),(True,62,None)])
def test_axial_rechaza_invalidos(args):
    with pytest.raises(ValueError):
        cabida_axial(*args)


def test_capacidad_radial_ausente_y_condiciones_no_inventadas():
    assert comprobar_carga_radial(1169.524)['cumple_comparacion_carga_correas'] is None
    # Catálogo exclusivamente sintético para probar la función; no dato comercial.
    c={'admisible_n':1200,'distancia_mm':40,'referencia_axial':'hombro',
       'fuente':'catálogo sintético de prueba','condiciones':'rpm y vida sintéticas'}
    assert comprobar_carga_radial(1169,c,40,'hombro')['utilizacion_radial'] is None
    assert comprobar_carga_radial(1169,c,41,'hombro',True)['utilizacion_radial'] is None
    assert comprobar_carga_radial(1169,c,40,'punta',True)['utilizacion_radial'] is None
    r=comprobar_carga_radial(1169,c,40,'hombro',True)
    assert r['cumple_comparacion_carga_correas'] is True
    assert r['utilizacion_radial']==pytest.approx(1169/1200)
    assert not r['montaje_aprobado']
    assert not comprobar_carga_radial(1300,c,40,'hombro',True)['cumple_comparacion_carga_correas']
    with pytest.raises(ValueError):
        comprobar_carga_radial(10,{**c,'fuente':None})
    with pytest.raises(ValueError):
        comprobar_carga_radial(-10)


@pytest.mark.parametrize('campo,valor',[('polos',True),('fases',0),('rpm_nominal',float('inf')),
    ('eficiencia_electrica_nominal',1.1),('diametro_eje_mm',0),('ancho_chavetero_mm',-1)])
def test_motor_rechaza_invalidos(campo,valor):
    motores,polea=datos(); m=copy.deepcopy(motores[0]);m[campo]=valor
    with pytest.raises(ValueError):
        comparar_motor(m,polea,1450)


def test_integracion_historicos_y_escenarios_separados(tmp_path):
    r=ejecutar(salida=tmp_path)
    assert r['motor_seleccionado'] is None and not r['montaje_aprobado']
    assert not r['cad_modificado'] and not r['fem_ejecutado']
    assert all(c['admisible_catalogo_n'] is None for c in r['verificacion_radial'])
    assert r['verificacion_radial'][0]['carga_condicional_correas_n']==pytest.approx(1169.524320572512)
    assert r['verificacion_radial'][1]['carga_condicional_correas_n']==pytest.approx(1171.249898648466)
    previo=leer_json(RAIZ/'resultados/etapa_5e2a/resumen.json')
    assert r['alternativas_cubo_5e2a_sin_recalcular']==previo['ligamentos']
    assert r['comparacion_motores'][0]['eficiencia_electrica']==.898
    assert all(c['eficiencia_mecanica_correas'] is None for c in r['comparacion_motores'])
    hashes=json.loads((tmp_path/'trazabilidad_sha256.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==v for f,v in hashes.items())
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/'resultados/etapa_5e2a')
