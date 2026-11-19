import copy
import json
import math
from pathlib import Path
import numpy as np
import pytest
from modelo_prototipo import (validar_parametros,reconstruir_patron,contacto_angular,cargas,
    VigaEscenario,presion_canal,repartir_cargas,posiciones_rodamientos,balance_potencia)
from simular_prototipo import RAIZ, ejecutar, verificar_hashes
from reutilizacion import interseccion_disco_rectangulo


@pytest.fixture
def p():
    return json.loads((RAIZ/'parametros.json').read_text(encoding='utf-8'))


def test_nominales_no_sustituyen_comercial(p):
    assert validar_parametros(p)
    assert p['matriz']['diametro_m']==.1 and p['eje_transversal']['diametro_nominal_m']==.006
    assert p['motor']['relacion_reduccion_real'] is None
    assert p['motor']['rpm_nominal']==1350
    assert p['rodamientos']['fabricante_adquirido'] is None
    assert p['eje_transversal']['clase_resistencia_real'] is None


@pytest.mark.parametrize('campo,valor',[('diametro_m',0),('espesor_m',float('nan')),('diametro_agujero_m',True)])
def test_rechazo_geometria(p,campo,valor):
    p['matriz'][campo]=valor
    with pytest.raises(ValueError):
        validar_parametros(p)


def test_patron_por_escala_y_ligamentos(p):
    xy,df,g=reconstruir_patron(p,RAIZ/p['patron']['archivo_origen'])
    assert xy.shape==(102,2)
    assert g['ligamento_min_agujeros_mm']==pytest.approx(.211)
    assert g['L_sobre_D']==pytest.approx(10/6)
    assert g['holgura_diametral_bore_arbol_mm']==pytest.approx(.3)
    p['patron']['factor_coordenadas']=.4
    with pytest.raises(ValueError):
        reconstruir_patron(p,RAIZ/p['patron']['archivo_origen'])


def test_interseccion_parcial_no_cuenta_agujero_completo():
    r=.003
    areas,_,_=interseccion_disco_rectangulo(np.array([[0,0]]),r,(0,.01,-.01,.01),128)
    assert areas[0]==pytest.approx(math.pi*r*r/2,rel=1e-5)


def test_presion_canal_no_copia_mu_torque():
    # Coeficientes exclusivamente sintéticos para verificar ecuación/unidades.
    a=presion_canal(1e6,.2,.3,.01,.006)
    assert a==pytest.approx(1e6/.3*math.expm1(4*.2*.3*10/6))
    assert presion_canal(2e6,.2,.3,.01,.006)==pytest.approx(2*a)
    with pytest.raises(ValueError):
        presion_canal(None,.2,.3,.01,.006)


@pytest.mark.parametrize('apoyo,factor',[('biapoyado',48),('biempotrado',192)])
def test_viga_reutilizada_con_solucion_analitica(apoyo,factor):
    L=.1;diam=.004773;E=205e9;F=10
    s=VigaEscenario(np.linspace(0,L,11),L,diam,E,apoyo)
    f=s.cargas_vacias();s.agregar_carga_puntual(f,L/2,-F)
    u=s.resolver(f).desplazamientos[0::2,0]
    I=math.pi*diam**4/64
    assert max(abs(u))==pytest.approx(F*L**3/(factor*E*I),rel=1e-9)


def test_angular_reparto_y_balance_unidades(p):
    p['numerico']['posiciones_angulares']=24
    xy,_,_=reconstruir_patron(p,RAIZ/p['patron']['archivo_origen'])
    g,detalle,long=contacto_angular(p,xy)
    assert long==pytest.approx(.010)
    d=cargas(p,g,2260000,.1);doble=cargas(p,g,4520000,.1)
    assert np.allclose(doble.fuerza_total_n,2*d.fuerza_total_n)
    assert np.allclose(doble.torque_total_nm,2*d.torque_total_nm)
    f=repartir_cargas(p,d)
    assert np.allclose(f.sum(axis=0),d.fuerza_total_n)
    pos=posiciones_rodamientos(p)
    assert np.allclose(pos,[.00675,.02975,.07025,.09325])
    assert ((detalle.fraccion>0)&(detalle.fraccion<=1)).all()
    assert (detalle.fraccion<1).any()
    b=balance_potencia(p,g)
    assert np.allclose(b.potencia_max_w,b.torque_max_nm*2*np.pi*b.rpm_matriz_hipotetica/60)
    assert np.allclose(b.margen_potencia_max_w,b.potencia_disponible_w-b.potencia_max_w)
    assert not (b.rpm_matriz_hipotetica==516).any()


def test_ejecucion_completa_y_historicos(p,tmp_path):
    # Ejecución completa1440estados una vez; ninguna configuración comercial modificada.
    r=ejecutar(salida=tmp_path)
    assert r['escenario_referencia']['estados']==1440
    assert not r['seguridad_estructural_aprobada'] and not r['matriz_fem_ejecutado']
    assert r['escenario_referencia']['fuerza_total_max_n']==pytest.approx(734.7033636,rel=1e-7)
    assert r['escenario_referencia']['torque_max_nm']==pytest.approx(2.30642478,rel=1e-7)
    assert r['incompatibilidad_M6_608_diametral_mm']==pytest.approx(2)
    assert r['convergencia_area_error_relativo_max']<1e-3
    assert max(e['equilibrio_vertical_error_n'] for e in r['eje_transversal_lineal'])<1e-4
    assert any(e['contacto_rigido_desacoplado_por_revisar'] for e in r['eje_transversal_lineal'])
    h=json.loads((tmp_path/'historicos_sha256.json').read_text(encoding='utf-8'))
    verificar_hashes(h)
    assert (tmp_path/'superposicion_por_agujero.csv.gz').is_file()
    presion=json.loads((tmp_path/'revision_presion_extrusion.json').read_text(encoding='utf-8'))
    assert presion['presion_calibrada_pa'] is None
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ.parent/'Simulación_peletizadora/resultados')
