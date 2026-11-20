import copy,json,math
import numpy as np
import pandas as pd
import pytest
from acoplado_m8 import entradas
from verificar_m8 import RAIZ,ORIGEN,SALIDA
from peletizadora.acoplado_prototipo import ModeloAcoplado
from peletizadora.resistencia_m8 import (reconstruir,Se_requerido,factor_estatico_nominal,
    contar_rainflow,EscenarioMaterial,EscenarioEntalla,factor_goodman)
from herramientas.control_resistencia_m8 import verificar,sha

@pytest.fixture(scope='module')
def modelo():
    a,c,h=entradas()
    m=ModeloAcoplado(a,h,c,c['varillas'][1])
    d=pd.read_csv(ORIGEN/'serie_M8x1.25_h4mm.csv')
    return m,d

def test_reconstruccion_sin_iterar_contacto(modelo,monkeypatch):
    m,d=modelo
    def prohibido(*args,**kwargs):raise AssertionError('No recalcular3C')
    monkeypatch.setattr(ModeloAcoplado,'simular',prohibido)
    fy,fz,my,mz,s=reconstruir(m,d)
    assert fy.shape==(4,1440) and s.shape[-1]==1440
    assert np.allclose(s.max(axis=(0,1)),d.sigma_nominal_max_pa)
    assert np.allclose(fy.sum(axis=0),d.fuerza_total_n)

def test_momentos_internos_con_signo_continuo(modelo):
    m,d=modelo;_,_,my,mz,_=reconstruir(m,d)
    for x in m.xb:
        j=m.indice(x)
        assert np.allclose(my[j-1,3],-my[j,1],atol=1e-7)
        assert np.allclose(mz[j-1,3],-mz[j,1],atol=1e-7)

def test_rechazo_historial_incompleto(modelo):
    m,d=modelo
    with pytest.raises(ValueError):reconstruir(m,d.iloc[:-1])
    d=d.copy();d.loc[0,'convergio']=False
    with pytest.raises(ValueError):reconstruir(m,d)

def test_factor_estatico_catalogo():
    assert factor_estatico_nominal(640e6,315.361913336e6)==pytest.approx(2.029414,rel=1e-6)
    assert factor_estatico_nominal(640e6,315.361913336e6,2.5)<1
    assert factor_estatico_nominal(240e6,315.361913336e6)<1
    with pytest.raises(ValueError):factor_estatico_nominal(640e6,300e6,.5)

def test_Se_requerido_contra_Goodman_original_EP2():
    e=EscenarioEntalla('prueba',1.5,.7,'Sintética')
    Se=Se_requerido(20e6,200e6,800e6,e.kt,e.kf)
    mat=EscenarioMaterial('sintetico',640e6,800e6,Se,'No material real')
    assert factor_goodman(20e6,200e6,mat,e)==pytest.approx(1)
    assert Se_requerido(20e6,900e6,800e6,1,1) is None
    assert Se_requerido(20e6,-200e6,800e6,1,1)==20e6

def test_no_inventar_Se_factor_fatiga():
    e=EscenarioEntalla('prueba',1,.0,'Sintética')
    mat=EscenarioMaterial('clase8_8',640e6,800e6,None,'SinSe')
    assert math.isnan(factor_goodman(20e6,200e6,mat,e))
    t=pd.read_csv(SALIDA/'requisitos_fatiga_Goodman.csv')
    assert t.factor_fatiga_real.isna().all()
    assert len(t)==27

def test_rainflow_media_y_amplitud_correlacionadas():
    t=contar_rainflow(np.array([100,300,100,300,100])*1e6)
    assert np.allclose(t.amplitud_pa,100e6)
    assert np.allclose(t.media_pa,200e6)
    assert t.conteo.sum()>0

def test_factores_condicionados_no_aprobados():
    t=pd.read_csv(SALIDA/'factores_estaticos_condicionados.csv')
    assert len(t)==27 and not t.aprobado.any()
    assert t.factor_estatico_real.isna().all()
    for _,g in t.groupby(['capa_m','clase']):
        assert np.allclose(g.n_flexion_condicional*g.Kt_sensibilidad,g.Kt_max_permitido_solo_n1)

def test_media_no_permite_Se_finito():
    t=pd.read_csv(SALIDA/'requisitos_fatiga_Goodman.csv')
    assert t.loc[t.imposible_por_media,'Se_min_requerido_n1_pa'].isna().all()
    assert (t.loc[~t.imposible_por_media,'Se_min_requerido_n1_pa']>=0).all()

def test_convergencia_fibras_y_reconstruccion():
    t=pd.read_csv(SALIDA/'validaciones_numericas.csv')
    assert t.error_reconstruccion_sigma_pa.max()<.01
    assert t.error_Se_requerido_relativo.dropna().max()<.02

def test_apoyos_incluyen_pares_correlacionados():
    t=pd.read_csv(SALIDA/'demandas_apoyos_ABS.csv')
    assert len(t)==6
    assert (t.traccion_proyectada_extrema_con_par_pa>t.p_media_corte_max_pa).all()
    fila=t[t.capa_m==.004].iloc[0]
    assert fila.M_resultante_max_nm>8 and fila.R_max_n>450
    assert fila.traccion_proyectada_extrema_con_par_pa>100e6

def test_sensibilidad_rigidez_sin_nuevo3C():
    t=pd.read_csv(SALIDA/'sensibilidad_rigidez_fijaciones.csv')
    for _,g in t[t.kv_hipotetico_n_m==1e12].groupby('capa_m'):
        delta=g.sort_values('kr_hipotetico_nm_rad').incremento_holgura_abs_max_con_cargas_congeladas_m
        assert np.all(np.diff(delta)<0)
    r=json.loads((SALIDA/'resumen.json').read_text(encoding='utf-8'))
    assert not r['modelo_3C_modificado'] and not r['resultados_3C_recalculados']

def test_montajes_no_equivalentes_y_sin_CAD():
    t=pd.read_csv(SALIDA/'comparacion_montaje_roscado_liso.csv')
    assert len(t)>=6
    g=pd.read_csv(SALIDA/'modificaciones_geometricas_pendientes.csv')
    assert not g.CAD_editado.any()
    r=json.loads((SALIDA/'resumen.json').read_text(encoding='utf-8'))
    assert r['factor_fatiga_real'] is None and r['factor_estatico_real'] is None

def test_fuentes_e_historicos_intactos():
    assert verificar()['alterados']==0
    for nombre,h in json.loads((SALIDA/'fuentes_sha256.json').read_text(encoding='utf-8')).items():
        assert sha(RAIZ/nombre)==h
