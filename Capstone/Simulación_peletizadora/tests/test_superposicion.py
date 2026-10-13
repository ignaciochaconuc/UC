import math

import numpy as np
import pytest

from config import DXF_MATRIZ, PARAMETROS
from geometria import cargar_agujeros_dxf
from modelos.superposicion import (
    fraccion_cobertura,
    interseccion_disco_rectangulo,
    limites_huella,
)
from simulacion_cargas import simular_modelo
from simulacion_superposicion import simular_area_superposicion


RADIO = PARAMETROS.diametro_agujero_m / 2
AREA = math.pi * RADIO**2
LIMITES = limites_huella(PARAMETROS)
X_MIN, X_MAX, Y_MIN, Y_MAX = LIMITES
X_MEDIO = (X_MIN + X_MAX) / 2


def cobertura(centros, orden=64):
    areas, cx, cy = interseccion_disco_rectangulo(
        np.asarray(centros, dtype=float), RADIO, LIMITES, orden
    )
    return fraccion_cobertura(areas, RADIO), areas, cx, cy


def test_casos_fuera_contenido_parcial_y_esquina():
    fracciones, areas, cx, cy = cobertura(
        [
            [X_MEDIO, Y_MAX + 2 * RADIO],
            [X_MEDIO, 0.0],
            [X_MEDIO, Y_MAX],
            [X_MIN, Y_MIN],
        ]
    )
    assert fracciones[0] == 0.0
    assert np.isnan(cx[0]) and np.isnan(cy[0])
    assert fracciones[1] == 1.0
    assert 0.0 < fracciones[2] < 1.0
    assert fracciones[2] == pytest.approx(0.5, abs=2e-6)
    assert fracciones[3] == pytest.approx(0.25, abs=2e-6)
    assert np.all(areas >= 0.0)
    assert np.all(areas <= AREA)


def test_cobertura_es_continua_al_cruzar_un_borde():
    posiciones = np.linspace(Y_MAX + 1.05 * RADIO, Y_MAX - 1.05 * RADIO, 401)
    centros = np.column_stack((np.full_like(posiciones, X_MEDIO), posiciones))
    fracciones, _, _, _ = cobertura(centros)
    # Al entrar desde fuera, la cobertura crece sin saltos binarios.
    assert np.all(np.diff(fracciones) >= -1e-10)
    assert np.max(np.diff(fracciones)) < 0.01
    assert len(np.unique(np.round(fracciones, 4))) > 100


def test_cotas_y_fuerzas_de_referencia():
    fracciones, areas, _, _ = cobertura([[X_MEDIO, 0.0], [X_MEDIO, Y_MAX]])
    fuerzas = PARAMETROS.presion_maxima_pa * areas
    assert np.all((fracciones >= 0.0) & (fracciones <= 1.0))
    assert fuerzas[0] == pytest.approx(1244.071, rel=1e-5)
    assert fuerzas[1] == pytest.approx(622.035, rel=1e-5)


def test_convergencia_orden_64_frente_a_512():
    casos = np.array(
        [
            [X_MEDIO, Y_MAX],
            [X_MIN + 0.35 * RADIO, Y_MAX - 0.20 * RADIO],
            [X_MIN - 0.25 * RADIO, Y_MIN + 0.40 * RADIO],
        ]
    )
    area_64 = interseccion_disco_rectangulo(casos, RADIO, LIMITES, 64)[0]
    area_512 = interseccion_disco_rectangulo(casos, RADIO, LIMITES, 512)[0]
    np.testing.assert_allclose(area_64, area_512, rtol=5e-6)


@pytest.fixture(scope="module")
def simulacion_area():
    coordenadas = cargar_agujeros_dxf(DXF_MATRIZ, PARAMETROS.numero_agujeros)
    return simular_area_superposicion(coordenadas)


def test_sumatorias_periodicidad_y_limite_uniforme(simulacion_area):
    agregados, individuales = simulacion_area
    por_paso = individuales.groupby("paso")
    fuerzas = por_paso["fuerza_axial_n"].sum()
    torques = por_paso["torque_nm"].sum()
    indices = fuerzas.index.to_numpy()
    np.testing.assert_allclose(agregados.loc[indices, "fuerza_total_n"], fuerzas)
    np.testing.assert_allclose(agregados.loc[indices, "torque_resistente_nm"], torques)
    assert np.all(
        agregados["fuerza_total_n"]
        <= agregados["limite_uniforme_superpuestos_n"] + 1e-9
    )
    columnas = [
        "fuerza_total_n",
        "torque_resistente_nm",
        "potencia_resistente_w",
        "perforaciones_superpuestas_total",
        "resultante_centroide_radial_r1_m",
        "resultante_centroide_tangencial_r1_m",
    ]
    np.testing.assert_allclose(agregados.iloc[0][columnas], agregados.iloc[-1][columnas])


def test_cobertura_parcial_activa_centros_exteriores(simulacion_area):
    agregados, _ = simulacion_area
    centros = agregados["centros_activos_rodillo_1"] + agregados["centros_activos_rodillo_2"]
    superpuestas = agregados["perforaciones_superpuestas_total"]
    assert np.all(superpuestas >= centros)
    assert np.any(superpuestas > centros)


def test_modelos_2b_mantienen_resultados_de_regresion():
    coordenadas = cargar_agujeros_dxf(DXF_MATRIZ, PARAMETROS.numero_agujeros)
    esperados = {
        "cuadratico": (3879.598992, 2427.766477, 25.196534, 15.592362),
        "senoidal": (5194.653865, 4625.620531, 34.215931, 29.707469),
        "constante": (9952.565527, 7277.813541, 64.689344, 46.741487),
    }
    for modelo, esperado in esperados.items():
        agregados, _ = simular_modelo(coordenadas, modelo)
        muestra = agregados.iloc[:-1]
        obtenido = (
            muestra["fuerza_total_n"].max(),
            muestra["fuerza_total_n"].mean(),
            muestra["torque_resistente_nm"].max(),
            muestra["torque_resistente_nm"].mean(),
        )
        # Los valores de referencia se documentan con seis decimales.
        np.testing.assert_allclose(obtenido, esperado, rtol=1e-7)
