import math

import numpy as np
import pytest

from config import PARAMETROS
from modelos.superposicion import interseccion_disco_rectangulo, limites_huella
from modelos.superposicion_variable import (
    interseccion_disco_huella_variable,
    longitud_contacto_desde_holgura,
)
from simulacion import obtener_geometria
from estructural.acoplamiento import (
    ConfiguracionAcoplamiento, EstadoContacto, _resolver_estructura, simular_acoplado,
)
from estructural.config_eje import CONFIG_EJE
from estructural.geometria_eje import crear_malla
from estructural.viga_eb import SistemaViga


def test_longitud_contacto_disminuye_y_se_anula():
    g = np.array([0, .0001, .001, .004, .005])
    lc = longitud_contacto_desde_holgura(g, .1, .004)
    assert np.all(np.diff(lc) <= 0)
    assert lc[-2] == 0 and lc[-1] == 0


def test_holgura_negativa_se_rechaza():
    with pytest.raises(ValueError, match="Holgura negativa"):
        longitud_contacto_desde_holgura(-1e-9, .1, .004)


def test_areas_variables_estan_acotadas_y_convergen_en_cuadratura():
    centros = np.array([[.043, .009], [.0635, 0], [.083, -.009]])
    resultados = []
    for orden in (32, 64, 128):
        areas, _, _ = interseccion_disco_huella_variable(
            centros, .003, PARAMETROS.limite_radial_rodillo_m, .0001, .001,
            PARAMETROS.centro_radial_rodillo_m, .1, .004, orden,
        )
        assert np.all((areas >= 0) & (areas <= math.pi*.003**2*(1+1e-12)))
        resultados.append(areas)
    assert np.max(np.abs(resultados[-1]-resultados[-2])) < 2e-9


def test_limite_holgura_cero_reproduce_huella_fija_2c():
    centros = np.array([[.043, .009], [.0635, 0], [.083, -.009], [.05, .006]])
    variable = interseccion_disco_huella_variable(
        centros, .003, PARAMETROS.limite_radial_rodillo_m, 0, 0,
        PARAMETROS.centro_radial_rodillo_m, .1, .004, 128,
    )[0]
    fija = interseccion_disco_rectangulo(centros, .003, limites_huella(PARAMETROS), 128)[0]
    assert np.allclose(variable, fija, rtol=2e-5, atol=2e-10)


def test_fuerzas_nulas_recuperan_deformacion_por_peso():
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)
    cero = EstadoContacto(0, PARAMETROS.centro_radial_rodillo_m, 0, 0,
                          np.zeros(1), np.full(1, np.nan), np.full(1, np.nan))
    estado, _, _ = _resolver_estructura(sistema, (cero, cero))
    assert estado[0] < 0 and estado[2] < 0
    assert np.isclose(estado[0], estado[2], rtol=1e-8)


def test_relajaciones_razonables_convergen_a_la_misma_solucion():
    coords, _ = obtener_geometria("auto")
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)
    resultados = []
    for lam in (.35, .7):
        serie, historia, _ = simular_acoplado(
            coords, sistema, "inclinacion",
            ConfiguracionAcoplamiento(relajacion=lam), pasos=2,
        )
        assert serie.convergio.all()
        final = historia.sort_values("iteracion").groupby("paso").tail(1)
        assert final.residuo_compatibilidad_m.max() <= 1e-9
        assert final.cambio_fuerza_relativo.max() <= 1e-5
        resultados.append(serie.fuerza_total_n.to_numpy())
    assert np.allclose(resultados[0], resultados[1], rtol=2e-5)


def test_geometria_es_periodica_entre_cero_y_360():
    coords, _ = obtener_geometria("auto")
    c, s = math.cos(2*math.pi), math.sin(2*math.pi)
    rotada = coords @ np.array([[c, s], [-s, c]])
    assert np.allclose(coords, rotada, atol=1e-15)
