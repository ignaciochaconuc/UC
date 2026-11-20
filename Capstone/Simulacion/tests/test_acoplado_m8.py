import copy,json,math
import numpy as np
import pandas as pd
import pytest
from acoplado_m8 import entradas,SALIDA,RAIZ
from peletizadora.acoplado_prototipo import ModeloAcoplado,resumir_acoplado
from peletizadora.nucleo import cargas_angulares
from herramientas.control_acoplado_m8 import verificar,sha

@pytest.fixture(scope='module')
def datos():return entradas()

def test_raices_y_propiedades_no_4140(datos):
    _,c,_=datos
    assert c['varillas'][0]['nucleo_referencia_m']==.004773
    assert c['varillas'][1]['nucleo_referencia_m']==.006466
    assert c['varillas'][1]['paso_m']==.00125
    assert c['material']['E_referencia_pa']==210e9
    assert c['material']['Sy_pa'] is None and c['material']['Sut_pa'] is None

def test_empotramientos_geometria_real(datos):
    a,c,h=datos;m=ModeloAcoplado(a,h,c,c['varillas'][1])
    assert m.L==pytest.approx(.160)
    assert np.diff(m.apoyos)[0]==pytest.approx(.10841175573598)
    assert 0<m.apoyos[0]<m.apoyos[1]<m.L
    assert len(m.restricciones)==4
    assert np.max(abs(m.U[m.restricciones]))==0
    assert np.max(abs(m.Up[m.restricciones]))==0

def test_influencia_equivale_solver_EP2(datos):
    a,c,h=datos;m=ModeloAcoplado(a,h,c,c['varillas'][1]);F=np.array([30.,50.,80.,40.])
    carga=m.peso[:,0].copy()
    for j,k in enumerate(m.gdl_b):carga[k]+=F[j]
    directa=m.sistema.resolver(carga).desplazamientos[:,0]
    assert np.allclose(directa,m.Up+m.U@F,rtol=1e-8,atol=1e-12)
    assert np.allclose(m.estado_desde_u(directa),m.Sp+m.S@F,rtol=1e-8,atol=1e-12)

def test_caso_sin_contacto_no_fuerza(datos):
    a,c,h=datos;c=copy.deepcopy(c);c['pesos']['incluir']=False
    m=ModeloAcoplado(a,h,c,c['varillas'][1]);d,_=m.simular(.0001,pasos=4)
    assert d.convergio.all() and np.allclose(d.fuerza_total_n,0)
    assert np.allclose(d.torque_total_nm,0) and np.allclose(d.flecha_max_m,0)
    assert np.allclose(d.holgura_r1_centro_m,.0005)

def test_no_forzar_convergencia(datos):
    a,c,h=datos;m=ModeloAcoplado(a,h,c,c['varillas'][1]);d,hist=m.simular(.002,pasos=4,limite_iter=1)
    assert not d.convergio.any()
    assert set(d.motivo)=={'max_iteraciones'}
    assert resumir_acoplado(d)['convergidos']==0
    assert 'fuerza_total_n' not in d

@pytest.mark.parametrize('parametro,valor',[('relajacion',0),('tolerancia_holgura_m',-1),('max_iteraciones',0)])
def test_parametros_invalidos(datos,parametro,valor):
    a,c,h=datos;c=copy.deepcopy(c);c['numerico'][parametro]=valor
    with pytest.raises(ValueError):ModeloAcoplado(a,h,c,c['varillas'][1])

def test_seccion_invalida(datos):
    a,c,h=datos;v=copy.deepcopy(c['varillas'][1]);v['nucleo_referencia_m']=.01
    with pytest.raises(ValueError):ModeloAcoplado(a,h,c,v)

def test_limite_rigido_recupera_contacto_EP2(datos):
    a,c,h=datos;c=copy.deepcopy(c);c['pesos']['incluir']=False
    m=ModeloAcoplado(a,h,c,c['varillas'][1],E=1e24);d,_=m.simular(.002,pasos=4)
    cfg=json.loads((RAIZ/'resultados/prototipo/revision_ensamble_2026_11_19/parametros_utilizados.json').read_text(encoding='utf-8'))
    cfg['rodillos'].update(espesor_biomasa_m=.002,contacto_escenario_explicito=True)
    cfg['torque']['mu_efectivo']=.1;cfg['presion']['valor_pa']=c['presion_pa'];cfg['numerico']['estados']=4
    previo,_=cargas_angulares(h.to_dict('records'),cfg)
    assert d.iloc[0].fuerza_total_n==pytest.approx(previo.iloc[0].fuerza_total_n,rel=2e-4)
    assert d.iloc[0].torque_total_nm==pytest.approx(previo.iloc[0].torque_total_nm,rel=2e-4)

def test_6_casos_y_1440_estados():
    tabla=pd.read_csv(SALIDA/'comparacion_M6_M8.csv')
    assert len(tabla)==6 and (tabla.estados==1440).all() and tabla.todos_convergieron.all()
    for _,r in tabla.iterrows():
        d=pd.read_csv(SALIDA/f'serie_{r.varilla}_h{r.capa_m*1000:g}mm.csv')
        assert len(d)==1440 and d.paso.nunique()==1440
        assert (d.residuo_final_holgura_m<=1e-9).all()
        assert (d.cambio_final_fuerza_relativo<=1e-5).all()
        assert np.allclose(d.fuerza_total_n,d.fuerza_r1_n+d.fuerza_r2_n)
        assert np.allclose(d.torque_total_nm,d.torque_r1_nm+d.torque_r2_nm)
        assert np.allclose(d.fuerza_manual_ideal_n,d.torque_total_nm/.165)
        assert d.residuo_equilibrio_fuerzas_n.max()<1e-5
        assert d.residuo_equilibrio_momentos_nm.max()<1e-6

def test_cuadratura_relajacion_malla():
    t=pd.read_csv(SALIDA/'validaciones_numericas.csv')
    assert len(t)==24 and t.todos_convergieron.all()
    assert t[t.contraste=='cuadratura'].error_Fmax_rel.max()<1e-4
    assert t[t.contraste=='relajacion'].error_g_abs_m.max()<1e-8
    assert t[t.contraste=='malla'].error_g_abs_m.max()<1e-8

def test_no_inventar_adecuacion_o_grado():
    t=pd.read_csv(SALIDA/'efecto_del_cambio_M6_M8.csv')
    assert t.holgura_M8_positiva.all() and t.holgura_M8_menor_capa.all()
    assert not t.tolerancia_funcional_aprobada.any()
    assert (t.reduccion_flecha_porcentaje>0).all()
    r=json.loads((SALIDA/'resumen_integral.json').read_text(encoding='utf-8'))
    assert not r['seguridad_aprobada'] and not r['CAD_modificado']

def test_conservacion_historicos():
    assert verificar()['alterados']==0
    for n,h in json.loads((SALIDA/'fuentes_sha256.json').read_text(encoding='utf-8')).items():assert sha(RAIZ/n)==h
