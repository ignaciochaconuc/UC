import math
import numpy as np

from cinematica import mascaras_rodillos, rotar
from config import DXF_MATRIZ, PARAMETROS
from geometria import cargar_agujeros_dxf, validar_geometria
from simulacion import simular_revolucion


def geometria_real():
    return cargar_agujeros_dxf(DXF_MATRIZ, PARAMETROS.numero_agujeros)


def test_dxf_contiene_102_agujeros_validos():
    coordenadas = geometria_real()
    metricas = validar_geometria(coordenadas, PARAMETROS)
    assert coordenadas.shape == (102, 2)
    assert metricas["separacion_minima_m"] >= PARAMETROS.diametro_agujero_m


def test_velocidad_y_periodo_de_diseno():
    assert math.isclose(PARAMETROS.omega_rad_s, 2 * math.pi * 516 / 60)
    assert math.isclose(PARAMETROS.periodo_revolucion_s, 0.1162790698, rel_tol=1e-8)


def test_rotacion_conserva_radios_y_se_repite():
    coordenadas = geometria_real()
    rotadas = rotar(coordenadas, 1.234)
    vuelta = rotar(coordenadas, 2 * math.pi)
    np.testing.assert_allclose(np.linalg.norm(rotadas, axis=1), np.linalg.norm(coordenadas, axis=1))
    np.testing.assert_allclose(vuelta, coordenadas, atol=1e-12)


def test_serie_completa_una_revolucion():
    coordenadas = geometria_real()
    resultados = simular_revolucion(coordenadas)
    assert math.isclose(resultados.iloc[-1]["angulo_rad"], 2 * math.pi)
    assert resultados.iloc[0]["activos_total"] == resultados.iloc[-1]["activos_total"]


def test_agujeros_activos_pertenecen_a_huellas():
    coordenadas = rotar(geometria_real(), 0.73)
    m1, m2 = mascaras_rodillos(coordenadas, PARAMETROS)
    r_min, r_max = PARAMETROS.limite_radial_rodillo_m
    semi_largo = PARAMETROS.longitud_contacto_m / 2
    assert np.all((coordenadas[m1, 0] >= r_min) & (coordenadas[m1, 0] <= r_max))
    assert np.all(np.abs(coordenadas[m1, 1]) <= semi_largo)
    assert np.all((-coordenadas[m2, 0] >= r_min) & (-coordenadas[m2, 0] <= r_max))
    assert np.all(np.abs(coordenadas[m2, 1]) <= semi_largo)
