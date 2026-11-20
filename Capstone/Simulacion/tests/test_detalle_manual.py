import copy
import json
import math
import re
import numpy as np
import pandas as pd
import pytest
import pymupdf
from pathlib import Path
from detalle_prototipo import RAIZ,ANTERIOR,SALIDA
from peletizadora.detalle_manual import (agua_base_humeda,fuerza_manual,presiones,radio_manivela_CAD,
    reparto_CAD,viga_detalle,seccion_arbol,referencia_608)
from herramientas.control_detalle import verificar,sha


@pytest.fixture(scope='module')
def datos():
    a=json.loads((ANTERIOR/'ensamble_auditado.json').read_text(encoding='utf-8'))
    c=json.loads((RAIZ/'configuraciones/detalle_manual.json').read_text(encoding='utf-8'))
    g=json.loads((ANTERIOR/'geometria_STEP.json').read_text(encoding='utf-8'))
    d=pd.read_csv(SALIDA/'historial_manual.csv.gz')
    return a,c,g,d


def test_documentos_revisados_e_inmutables():
    manifest=json.loads((RAIZ/'control/detalle_manual_2026_11_20/documentos_recibidos.json').read_text(encoding='utf-8'))
    for n,h in manifest.items():assert sha(RAIZ.parent/n)==h
    e=pymupdf.open(RAIZ.parent/'Documentacion/Entrega_2.pdf')
    assert len(e)==75 and 'A.2.2.' in e[13].get_text() and 'PN0' in e[13].get_text()
    detalles=pymupdf.open(RAIZ.parent/'Documentacion/Ingenieria_de_Detalles.pdf')
    assert len(detalles)==3 and all(not x.get_text().strip() for x in detalles)


def test_presiones_y_redondeos(datos):
    _,c,g,_=datos;p=presiones(c,g)
    assert p['P_CAD_pa']==pytest.approx(2258670.6718785944)
    assert p['P_literal_transcripcion_pa']/1e6==pytest.approx(2.259375739774007)
    assert p['P_comercial_L_D6_pa']/1e6==pytest.approx(43.70432961106003)
    assert round(p['P_comercial_L_D6_pa']/1e6)==44
    assert round(p['P_comercial_L_D6_pa']/1e6,2)==43.70
    assert p['L_D']==pytest.approx(10/6)
    assert p['lambda_p_CAD']==pytest.approx(.0517,abs=.0001)


def test_material_y_accionamiento_sin_motor_nominal(datos):
    _,c,_,d=datos
    assert c['accionamiento_principal']=='manual_manivela'
    assert c['material_impreso']['material_diseno']=='ABS'
    assert c['material_impreso']['filamento_definitivo'] is None
    assert d.tiempo_s.isna().all() and d.potencia_w.isna().all()


def test_radio_CAD_y_fuerza_manual(datos):
    a,_,_,_=datos
    assert radio_manivela_CAD(a)['radio_ejes_mm']==pytest.approx(165)
    assert fuerza_manual(3.255,.165)==pytest.approx(19.72727272727)
    assert fuerza_manual(0,.165)==0


@pytest.mark.parametrize('t,r',[(-1,.165),(1,0),(float('nan'),.165)])
def test_manivela_rechaza_invalidos(t,r):
    with pytest.raises(ValueError):fuerza_manual(t,r)


def test_balance_agua_seca():
    agua=agua_base_humeda(.5,.10,.15)
    assert agua*1000==pytest.approx(29.4117647059)
    assert .5*(1-.1)==pytest.approx((.5+agua)*(1-.15))
    assert agua_base_humeda(.5,.1,.1)==0


@pytest.mark.parametrize('m,w0,wf',[(0,.1,.15),(.5,.2,.15),(.5,.1,1),(.5,-.1,.15)])
def test_humedades_invalidas(m,w0,wf):
    with pytest.raises(ValueError):agua_base_humeda(m,w0,wf)


def test_presion_escalada_sin_cambiar_geometria(datos):
    _,c,g,d=datos;p=presiones(c,g)['P_CAD_pa'];viejo=pd.read_csv(ANTERIOR/'historial_escenarios.csv.gz')
    for h in c['escenarios_conservados']['capas_m']:
        nuevo=d[np.isclose(d.capa_biomasa_hipotetica_m,h)].reset_index(drop=True)
        previo=viejo[np.isclose(viejo.capa_biomasa_hipotetica_m,h)&np.isclose(viejo.presion_condicionada_pa,2260000)&np.isclose(viejo.mu_efectivo_hipotetico,.1)].reset_index(drop=True)
        assert len(nuevo)==1440 and nuevo.paso.nunique()==1440
        assert np.allclose(nuevo.fuerza_total_n,previo.fuerza_total_n*p/2260000)
        assert np.allclose(nuevo.torque_total_nm,previo.torque_total_nm*p/2260000)
        assert np.array_equal(nuevo.perforaciones_activas_r1,previo.perforaciones_activas_r1)
        assert np.allclose(nuevo.fuerza_total_n,nuevo.fuerza_r1_n+nuevo.fuerza_r2_n)
        assert np.allclose(nuevo.F_manivela_ideal_n,nuevo.torque_total_nm/.165)


def test_maximos_sin_mezclar_estados():
    d=pd.read_csv(SALIDA/'solicitaciones_manuales.csv')
    r=d.iloc[-1]
    assert r.suma_maximos_independientes_n>r.fuerza_max_n
    assert (d.paso_fuerza_max!=d.paso_torque_max).any()
    k=pd.read_csv(SALIDA/'casos_criticos_correlacionados.csv')
    h=pd.read_csv(SALIDA/'historial_manual.csv.gz')
    for _,fila in k.iterrows():
        original=h[(h.escenario==fila.escenario)&(h.paso==fila.paso)].iloc[0]
        assert fila.fuerza_total_n==pytest.approx(original.fuerza_total_n)
        assert fila.torque_total_nm==pytest.approx(original.torque_total_nm)


def test_reparto_fuerza_y_momento(datos):
    a,_,_,d=datos;d=d[d.escenario==d.escenario.iloc[0]]
    t,e=reparto_CAD(d,a,.1)
    assert e['error_fuerzas_n']<1e-10 and e['error_momentos_nm']<1e-10
    assert np.allclose(sum(t[f'Y_b{b["solido_id"]}_n'] for b in a['rodamientos']),d.fuerza_total_n)


def test_limite_viga_sin_carga_y_no_FS(datos):
    a,_,_,d=datos;d=d.iloc[:4].copy()
    for col in d:
        if col.startswith(('fuerza_','torque_')):d[col]=0.
    t,_=reparto_CAD(d,a,.1);serie,r=viga_detalle(t,a,.006,205e9,20)
    assert r['flecha_resultante_max_m']==0 and r['sigma_flexion_nominal_max_pa']==0
    assert r['factor_seguridad_aprobado'] is None
    assert np.allclose(serie.R_Y_apoyo1_n,0)


def test_convergencia_y_equilibrio():
    d=pd.read_csv(SALIDA/'convergencia_viga.csv')
    for _,g in d.groupby('escenario'):
        a=g[g.divisiones==80].iloc[0];b=g[g.divisiones==160].iloc[0]
        assert abs(a.flecha_resultante_max_m/b.flecha_resultante_max_m-1)<.002
        assert abs(a.sigma_flexion_nominal_max_pa/b.sigma_flexion_nominal_max_pa-1)<1e-5
        assert g.equilibrio_error_fuerzas_n.max()<.01
        assert g.equilibrio_error_momentos_nm.max()<.001


def test_modulo_y_diametro_sensibilidad():
    d=pd.read_csv(SALIDA/'eje_sensibilidad.csv')
    for _,g in d.groupby(['escenario','diametro_resistente_hipotetico_m']):
        assert np.allclose(g.flecha_resultante_max_m*g.E_hipotetico_pa,(g.flecha_resultante_max_m*g.E_hipotetico_pa).iloc[0])
        assert np.allclose(g.sigma_flexion_nominal_max_pa,g.sigma_flexion_nominal_max_pa.iloc[0])
    assert d.factor_seguridad_aprobado.isna().all()
    assert d.cambio_holgura_sobre_gap_CAD.max()>1


def test_arbol_casos_correlacionados_y_unidades():
    s,t,vm=seccion_arbol(np.array([100.,200.]),np.array([3.,1.]),.0127)
    assert np.allclose(s,4*np.array([100,200])/(np.pi*.0127**2))
    assert np.allclose(vm**2,s**2+3*t**2)
    with pytest.raises(ValueError):seccion_arbol([1],[1,2],.0127)


def test_608_referencia_no_certificacion():
    d=pd.read_csv(SALIDA/'rodamientos_EZO_referencia.csv')
    assert len(d)==24 and set(d.fuente)=={'ezo_608zz_2026'}
    assert np.allclose(d.L10_millones,(3300/d.Peq_n)**3)
    assert np.allclose(d.L10h,1e6*d.L10_millones/(60*d.rpm_rodillo_hipotetica))
    assert d.estado.str.contains('asientos no resueltos').all()


def test_ABS_fuente_proceso_y_no_FS():
    fuente=json.loads((RAIZ/'fisica/ABS_referencia.json').read_text(encoding='utf-8'))
    assert fuente['material_diseno']=='ABS' and not fuente['seleccion_comercial_definitiva']
    assert '0,254' in fuente['condiciones']
    d=pd.read_csv(SALIDA/'ABS_comparacion_propiedades_y_rigidez.csv')
    assert set(d.orientacion_referencia)=={'XZ','ZX'}
    assert np.allclose(d.epsilon_indicador_uniaxial_homogeneo,d.presion_proyectada_pa/d.E_compresion_referencia_pa)
    assert d.factor_seguridad.isna().all()


def test_latex_estructural_y_citas():
    bib=(SALIDA/'referencias_reutilizables.bib').read_text(encoding='utf-8')
    claves=re.findall(r'@\w+\{([^,]+),',bib);assert len(claves)==len(set(claves))
    for nombre in ('seccion_informe.tex','anexo_calculos.tex','revision_independiente.tex'):
        t=(SALIDA/nombre).read_text(encoding='utf-8')
        assert t.count('{')==t.count('}')
        pila=[]
        for tipo,entorno in re.findall(r'\\(begin|end)\{([^}]+)\}',t):
            if tipo=='begin':pila.append(entorno)
            else:assert pila.pop()==entorno
        assert not pila
        for k in re.findall(r'\\parencite\{([^}]+)\}',t):assert k in claves


def test_conservacion_y_estado_aprobacion():
    assert verificar()['historicos_intactos']
    r=json.loads((SALIDA/'resumen.json').read_text(encoding='utf-8'))
    assert r['documentos_originales_detalles_disponibles'] and not r['seguridad_aprobada']
    assert r['nominal_fisico_unico'] is None
    for ruta,h in json.loads((SALIDA/'fuentes_sha256.json').read_text(encoding='utf-8')).items():assert sha(RAIZ/ruta)==h
