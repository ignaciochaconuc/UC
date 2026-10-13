import math

import numpy as np
import pytest

from cinematica import estado_contacto
from config import DXF_MATRIZ, PARAMETROS
from geometria import cargar_agujeros_dxf
from modelos.fuerzas import area_perforacion_m2, fuerzas_axiales_n
from modelos.presion import calcular_presion_pa, factor_presion
from modelos.torque import contribuciones_torque_nm
from simulacion_cargas import simular_modelo


def test_perfiles_en_puntos_notables():
    assert factor_presion(np.array([0.0, 1.0]), "cuadratico").tolist() == [0.0, 1.0]
    np.testing.assert_allclose(
        factor_presion(np.array([0.0, 0.5, 1.0]), "senoidal"),
        [0.0, 1.0, 0.0],
        atol=1e-15,
    )
    np.testing.assert_allclose(
        factor_presion(np.array([0.0, 0.3, 1.0]), "constante"), 1.0
    )


def test_u_aumenta_desde_entrada_hasta_salida_antihoraria():
    semi = PARAMETROS.longitud_contacto_m / 2
    x = PARAMETROS.centro_radial_rodillo_m
    puntos = np.array([[x, -semi], [x, 0.0], [x, semi]])
    activa, u = estado_contacto(puntos, 0.0, PARAMETROS)
    assert activa.all()
    np.testing.assert_allclose(u, [0.0, 0.5, 1.0])


@pytest.mark.parametrize("modelo", ["cuadratico", "senoidal", "constante"])
def test_presion_acotada_y_nula_fuera(modelo):
    u = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    activa = np.array([False, True, True, True, False])
    presion = calcular_presion_pa(u, activa, PARAMETROS.presion_maxima_pa, modelo)
    assert np.all(presion >= 0.0)
    assert np.all(presion <= PARAMETROS.presion_maxima_pa)
    assert presion[0] == 0.0 and presion[-1] == 0.0


def test_fuerza_es_presion_por_area_y_maximo_cercano_a_1244_n():
    presiones = np.array([0.0, PARAMETROS.presion_maxima_pa])
    fuerzas = fuerzas_axiales_n(presiones, PARAMETROS.diametro_agujero_m)
    np.testing.assert_allclose(
        fuerzas, presiones * area_perforacion_m2(PARAMETROS.diametro_agujero_m)
    )
    assert fuerzas[1] == pytest.approx(1244.071, rel=1e-5)


@pytest.fixture(scope="module")
def simulaciones():
    coordenadas = cargar_agujeros_dxf(DXF_MATRIZ, PARAMETROS.numero_agujeros)
    return {
        modelo: simular_modelo(coordenadas, modelo)
        for modelo in ("cuadratico", "senoidal", "constante")
    }


def test_sumatorias_fuerza_y_torque(simulaciones):
    for agregados, individuales in simulaciones.values():
        por_paso = individuales.groupby("paso")
        fuerzas = por_paso["fuerza_axial_n"].sum()
        torques = por_paso["torque_nm"].sum()
        indices = fuerzas.index.to_numpy()
        np.testing.assert_allclose(agregados.loc[indices, "fuerza_total_n"], fuerzas)
        np.testing.assert_allclose(agregados.loc[indices, "torque_resistente_nm"], torques)
        assert (agregados["torque_resistente_nm"] >= 0).all()
        assert (agregados["potencia_resistente_w"] >= 0).all()


def test_torque_individual_usa_radio_real():
    fuerzas = np.array([100.0, 200.0])
    radios = np.array([0.05, 0.075])
    esperado = radios * PARAMETROS.coeficiente_resistencia_tangencial * fuerzas
    np.testing.assert_allclose(
        contribuciones_torque_nm(
            fuerzas, radios, PARAMETROS.coeficiente_resistencia_tangencial
        ),
        esperado,
    )


def test_periodicidad_y_envolvente_constante(simulaciones):
    constante = simulaciones["constante"][0]
    for modelo, (agregados, _) in simulaciones.items():
        columnas = [
            "activos_total",
            "fuerza_total_n",
            "torque_resistente_nm",
            "potencia_resistente_w",
        ]
        np.testing.assert_allclose(agregados.iloc[0][columnas], agregados.iloc[-1][columnas])
        if modelo != "constante":
            assert np.all(agregados["fuerza_total_n"] <= constante["fuerza_total_n"] + 1e-9)
            assert np.all(agregados["torque_resistente_nm"] <= constante["torque_resistente_nm"] + 1e-9)
