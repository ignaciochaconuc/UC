import copy
import hashlib
import json
from pathlib import Path
import pytest
from simulacion_transmision import RAIZ
from cierre_transmision import ejecutar, tabla
from transmision.cierre import parametro, verificar_utilizacion, verificar_historial, estado_cierre


def test_unidades_y_trazabilidad():
    assert parametro('T',88.924,'N m','verificado','archivo','3c')['unidad']=='N m'
    for u in ('Nm_inventado','kg'):
        with pytest.raises(ValueError):
            parametro('T',1,u,'verificado','archivo','3c')
    with pytest.raises(ValueError):
        parametro('T',float('nan'),'N','verificado','archivo','3c')


def test_limite_utilizacion_y_sobrecarga():
    assert verificar_utilizacion(10,10,1)
    assert not verificar_utilizacion(11,10,1.1)
    with pytest.raises(ValueError):
        verificar_utilizacion(7.15,9.80796,.9)


def test_identidad_historial_sin_mezclar_escenarios():
    a=tabla('resultados/etapa_5d2/diferencias_tensiones_3c.csv')
    b=tabla('resultados/etapa_5d2/tensiones_y_fuerzas_condicionales_3c.csv')
    assert verificar_historial(a,b,1440)
    alterado=copy.deepcopy(b);alterado[0]['escenario']='motor_nominal_externo'
    with pytest.raises(ValueError):
        verificar_historial(a,alterado,1440)
    with pytest.raises(ValueError):
        verificar_historial(a,list(reversed(b)),1440)
    with pytest.raises(ValueError):
        verificar_historial(a[:-1],b,1440)


def test_no_confundir_cierre_documental_con_aprobacion():
    r=estado_cierre([dict(verificacion='resistencia',estado='pendiente',esencial_aprobacion=True)])
    assert r['listo_redaccion_ingenieria_basica'] and not r['transmision_aprobada']
    assert not r['autorizado_fabricacion']
    assert r['motor_seleccionado'] is None


def test_cierre_integral_coherente_y_conserva_historia(tmp_path):
    r=ejecutar(salida=tmp_path)
    assert not r['transmision_aprobada'] and not r['historial_3c_modificado']
    parametros={p['parametro']:p for p in r['parametros_predimensionamiento']}
    assert parametros['cubo_motriz_CAD_exterior']['valor']==45
    assert parametros['cubo_motriz_propuesto_exterior']['valor']==55
    assert parametros['cubo_motriz_propuesto_exterior']['estado']=='propuesta'
    assert parametros['velocidad_correa']['unidad']=='m/s'
    assert parametros['capacidad_total_kw']['valor']==pytest.approx(9.80796)
    assert r['eficiencia_mecanica_minima_maximo']==pytest.approx(4.805/5.5)
    assert r['eficiencia_mecanica_minima_media']==pytest.approx(4.194/5.5)
    interfaz=r['interfaz_eje_vertical']
    assert interfaz['numero_estados']==1440
    assert not interfaz['reacciones_rodamientos_calculadas']
    assert interfaz['caso_3c_correlacionado']['escenario']!=interfaz['caso_nominal_ideal_externo']['escenario']
    assert interfaz['caso_3c_correlacionado']['conducida_fr_n']==pytest.approx(1169.52432057)
    hashes=json.loads((tmp_path/'trazabilidad_sha256.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items())
    for item in r['anexos']:
        assert (RAIZ/item['archivo']).is_file()
    assert len(r['bibliografia'])==len({f['clave_bibtex'] for f in r['bibliografia']})
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/'resultados/etapa_5e2b')
