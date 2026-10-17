import copy
import numpy as np
import pytest

from config import PARAMETROS
from estructural.analisis import resolver_casos
from estructural.cargas_eje import cargar_serie_2c, tabla_fuerzas_rodamientos
from estructural.config_eje import CONFIG_EJE, SegmentoEje
from estructural.geometria_eje import crear_malla
from estructural.holgura_rodillos import (
    calcular_cinematica_y_holgura,
    cinematica_lineal_rodillo,
    desplazamientos_rodamientos,
    geometria_rodillos,
    interpolar_viga_hermite,
)
from estructural.viga_eb import SistemaViga


@pytest.fixture(scope="module")
def resultados_reales():
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)
    tabla = tabla_fuerzas_rodamientos(cargar_serie_2c(CONFIG_EJE), CONFIG_EJE)
    casos, _ = resolver_casos(sistema, tabla)
    return sistema, casos


def test_eje_sin_desplazamiento_da_holgura_nominal(resultados_reales):
    sistema, casos = resultados_reales
    casos_cero = {"A": copy.deepcopy(casos["A"])}
    casos_cero["A"].solucion_vertical.desplazamientos[:] = 0
    casos_cero["A"].solucion_horizontal.desplazamientos[:] = 0
    _, h = calcular_cinematica_y_holgura(casos_cero, sistema, .0001)
    assert np.allclose(h[["holgura_extremo_izquierdo_m", "holgura_centro_m", "holgura_extremo_derecho_m"]], .0001)


def test_desplazamientos_iguales_implican_inclinacion_nula():
    geo = geometria_rodillos(CONFIG_EJE)[0]
    centro, alpha, izq, der = cinematica_lineal_rodillo(2e-5, 2e-5, geo)
    assert centro == 2e-5 and alpha == 0 and izq == der == 2e-5


def test_diferencia_conocida_da_inclinacion_analitica_y_signo():
    geo = geometria_rodillos(CONFIG_EJE)[0]
    _, alpha, izq, der = cinematica_lineal_rodillo(0.0, 24e-6, geo)
    assert np.isclose(alpha, 24e-6/.024)
    assert der > izq


def test_interpolacion_hermite_reproduce_campo_lineal():
    config = type("Cfg", (), {"segmentos": (SegmentoEje("u", 0, 1, .04),), "modulo_young_pa": 205e9})()
    sistema = SistemaViga(np.array([0., 1.]), config)
    # v=2e-3*x + 1e-3 y giro dv/dx constante.
    u = np.array([1e-3, 2e-3, 3e-3, 2e-3])
    v, giro = interpolar_viga_hermite(sistema, u, .5)
    assert np.isclose(v[0], 2e-3) and np.isclose(giro[0], 2e-3)


def test_extremos_de_ambos_rodillos_separados_40_mm():
    assert all(np.isclose(g.ancho_m, .040) for g in geometria_rodillos(CONFIG_EJE))


def test_series_conservan_1440_instantes_y_unidades(resultados_reales):
    sistema, casos = resultados_reales
    c, h = calcular_cinematica_y_holgura(casos, sistema, PARAMETROS.separacion_minima_rodillo_matriz_m)
    for caso in ("B", "C"):
        assert len(c[(c.caso == caso) & (c.rodillo == "izquierdo")]) == 1440
    assert c.v_centro_rodillo_m.abs().max() < .01
    assert h.holgura_nominal_m.unique().tolist() == [.0001]


def test_rodamientos_exportados_coinciden_con_solucion_3a(resultados_reales):
    sistema, casos = resultados_reales
    tabla = desplazamientos_rodamientos(casos, sistema)
    fila = tabla[tabla.caso == "C"].iloc[123]
    nodo = sistema.indice_nodo(CONFIG_EJE.rodamientos_izquierdos_m[0])
    assert fila.v_izquierdo_a_m == casos["C"].solucion_vertical.desplazamientos[2*nodo, 123]


def test_convencion_signo_holgura_es_explicita(resultados_reales):
    sistema, casos = resultados_reales
    _, h = calcular_cinematica_y_holgura({"A": casos["A"]}, sistema, .0001)
    fila = h.iloc[0]
    # El peso da v<0 (hacia la matriz) y reduce la holgura.
    assert fila.holgura_centro_m < .0001
