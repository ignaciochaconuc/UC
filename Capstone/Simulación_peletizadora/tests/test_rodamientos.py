import numpy as np
import pandas as pd
import pytest

from config import PARAMETROS, RAIZ_PROYECTO
from estructural.config_eje import CONFIG_EJE
from estructural.rodamientos import (
    CONFIG_RODAMIENTO, carga_dinamica_equivalente, carga_radial_resultante,
    cargas_rodamientos_3c, factor_estatico, vida_l10_horas, vida_l10_millones,
    velocidad_rodillo_rpm,
)


@pytest.fixture(scope="module")
def serie_3c():
    ruta = RAIZ_PROYECTO/"resultados"/"etapa_3c_acoplamiento"/"series_temporales_acopladas.csv"
    d = pd.read_csv(ruta)
    return d[d.modelo == "inclinacion"].reset_index(drop=True)


def test_velocidad_rodadura_y_conversiones():
    rpm = velocidad_rodillo_rpm(516, .0635, .05)
    assert rpm == pytest.approx(655.32)
    assert 60/rpm == pytest.approx(0.0915583227)


def test_resultante_radial():
    assert carga_radial_resultante([3, 5], [4, 12]).tolist() == pytest.approx([5, 13])


def test_carga_equivalente_constante_y_variable():
    assert carga_dinamica_equivalente([2500]*8) == pytest.approx(2500)
    esperada = ((1000**3 + 2000**3)/2)**(1/3)
    assert carga_dinamica_equivalente([1000, 2000]) == pytest.approx(esperada)
    assert carga_dinamica_equivalente([1000, 2000], [1, 3]) == pytest.approx(
        ((1000**3 + 3*2000**3)/4)**(1/3))


def test_vida_analitica_carga_constante():
    assert vida_l10_millones(20_000, 10_000) == pytest.approx(8)
    assert vida_l10_horas(8, 1000) == pytest.approx(133.3333333)


def test_factor_estatico():
    assert factor_estatico(11_300, 5650) == pytest.approx(2)


def test_1440_intervalos_y_conservacion_fuerza_momento(serie_3c):
    assert len(serie_3c) == PARAMETROS.pasos_por_revolucion == 1440
    cargas = cargas_rodamientos_3c(serie_3c, CONFIG_EJE)
    assert len(cargas) == 4*1440
    for numero, nombres, posiciones in (
        (1, ("R1_A", "R1_B"), CONFIG_EJE.rodamientos_izquierdos_m),
        (2, ("R2_A", "R2_B"), CONFIG_EJE.rodamientos_derechos_m),
    ):
        a = cargas[cargas.rodamiento == nombres[0]].reset_index(drop=True)
        b = cargas[cargas.rodamiento == nombres[1]].reset_index(drop=True)
        f = serie_3c[f"fuerza_rodillo_{numero}_n"].to_numpy()
        r = serie_3c[f"resultante_radial_r{numero}_m"].to_numpy()
        xf = CONFIG_EJE.centro_matriz_m + (-r if numero == 1 else r)
        assert a.carga_vertical_compactacion_n.to_numpy()+b.carga_vertical_compactacion_n.to_numpy() == pytest.approx(f)
        assert (a.carga_vertical_compactacion_n.to_numpy()*posiciones[0]
                + b.carga_vertical_compactacion_n.to_numpy()*posiciones[1]) == pytest.approx(f*xf)


def test_simetria_rodillos_y_consistencia_3c(serie_3c):
    assert serie_3c.fuerza_total_n.max() == pytest.approx(14071.128, rel=1e-5)
    assert serie_3c.fuerza_rodillo_1_n.max() == pytest.approx(
        serie_3c.fuerza_rodillo_2_n.max(), rel=1e-10)
    cargas = cargas_rodamientos_3c(serie_3c, CONFIG_EJE)
    r1a = cargas[cargas.rodamiento == "R1_A"].carga_radial_resultante_n.to_numpy()
    r2b = cargas[cargas.rodamiento == "R2_B"].carga_radial_resultante_n.to_numpy()
    assert np.sort(r1a) == pytest.approx(np.sort(r2b), rel=2e-10, abs=1e-8)


def test_ficha_referencia_unidades():
    assert CONFIG_RODAMIENTO.diametro_interior_m == pytest.approx(.030)
    assert CONFIG_RODAMIENTO.diametro_exterior_m == pytest.approx(.062)
    assert CONFIG_RODAMIENTO.ancho_m == pytest.approx(.016)
    assert CONFIG_RODAMIENTO.capacidad_dinamica_n == pytest.approx(20_700)
