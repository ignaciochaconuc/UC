import hashlib
import json
from pathlib import Path
import pytest
from simulacion_transmision import RAIZ
from simulacion_redisenio_cubo import ejecutar
from transmision.redisenio_cubo import comparar_cubos, comprobar_aberturas


def test_ligamentos_contraste_y_separacion_resistencia():
    r=comparar_cubos([45,50,55,60],38,10,[3.3,3.5])
    assert [x['ligamento_central_fondo_mm'] for x in r] == pytest.approx([.2,0,2.7,2.5,5.2,5,7.7,7.5])
    assert [x['ligamento_radial_esquina_ideal_mm'] for x in r[1::2]] == pytest.approx([-.548861143,1.951138857,4.451138857,6.951138857])
    assert not r[0]['fondo_plano_contenido_en_exterior_ideal']
    assert all(x['fondo_plano_contenido_en_exterior_ideal'] for x in r[2:])


def test_interferencias_sin_coordenadas_no_inventadas():
    for D,radio in ((45,29),(50,31.5),(55,34),(60,36.5)):
        r=comprobar_aberturas(D,13)[0]
        assert r['radio_centro_abertura_para_tangencia_mm']==radio
        assert r['interferencia_3d'] is None
        assert r['separacion_proyectada_mm'] is None


def test_interferencia_sintetica_y_axial():
    puntos=[[30+i,0] for i in range(8)]
    r=comprobar_aberturas(55,13,puntos,'CAD sintético de prueba',True)
    assert r[0]['separacion_proyectada_mm']==-4
    assert r[0]['interferencia_3d'] is True
    assert r[4]['separacion_proyectada_mm']==0
    assert r[-1]['interferencia_3d'] is False
    assert comprobar_aberturas(55,13,puntos,'sintético')[0]['interferencia_3d'] is None
    assert comprobar_aberturas(55,13,puntos,'sintético',False)[0]['interferencia_3d'] is False


@pytest.mark.parametrize('puntos,fuente', [([[30,0]]*8,'CAD'),([[30,0]],'CAD'),
    ([[30+i,0] for i in range(8)],None),([[float('nan'),i] for i in range(8)],'CAD')])
def test_rechaza_coordenadas_invalidas(puntos,fuente):
    with pytest.raises(ValueError):
        comprobar_aberturas(55,13,puntos,fuente)


@pytest.mark.parametrize('D', [0,-1,True,float('inf')])
def test_rechaza_dimensiones_invalidas(D):
    with pytest.raises(ValueError):
        comparar_cubos([D],38,10,[3.3])


def test_integracion_conserva_cad_y_todos_historicos(tmp_path):
    r=ejecutar(salida=tmp_path)
    assert not r['cad_modificado'] and not r['resistencia_aprobada']
    assert r['factores_seguridad'] is None and not r['fem_ejecutado']
    assert r['eje_real']['coincidencia_nominal'] is None
    assert all(c['polea']=='motriz' for c in r['cargas_motriz_importadas'])
    anterior=json.loads((RAIZ/'resultados/etapa_5e2/resumen.json').read_text(encoding='utf-8'))
    assert r['cargas_motriz_importadas']==[c for c in anterior['fuerzas_correlacionadas'] if c['polea']=='motriz']
    hashes=json.loads((tmp_path/'trazabilidad_sha256.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items())
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/'resultados/etapa_5e2')
