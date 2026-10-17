import math

import numpy as np

from estructural.resistencia_fatiga import (
    ENTALLAS, MATERIALES, contar_rainflow, factor_goodman, tension_flexion_punto,
)


def test_reconstruccion_flexion_en_dos_planos():
    d = .03; z = math.pi*d**3/32
    mv, mh = 100.0, 50.0
    assert np.isclose(tension_flexion_punto(mv, mh, d, 0), mv/z)
    assert np.isclose(tension_flexion_punto(mv, mh, d, math.pi/2), mh/z)
    phi = math.atan2(mh, mv)
    assert np.isclose(tension_flexion_punto(mv, mh, d, phi), math.hypot(mv, mh)/z)


def test_historial_nulo_da_tension_y_ciclos_nulos():
    s = tension_flexion_punto(np.zeros(100), np.zeros(100), .03, .7)
    assert np.all(s == 0)
    assert contar_rainflow(s).empty


def test_rainflow_flexion_constante_pulsante_y_alternante():
    t = np.linspace(0, 2*math.pi, 360, endpoint=False)
    assert contar_rainflow(np.ones_like(t)*12).empty
    alternante = contar_rainflow(10*np.sin(t))
    pulsante = contar_rainflow(5*(1+np.sin(t)))
    assert np.isclose(alternante.amplitud_pa.max(), 10, rtol=1e-6)
    assert np.isclose(alternante.loc[alternante.amplitud_pa.idxmax(), "media_pa"], 0, atol=1e-10)
    assert np.isclose(pulsante.amplitud_pa.max(), 5, rtol=1e-6)
    assert np.isclose(pulsante.loc[pulsante.amplitud_pa.idxmax(), "media_pa"], 5, rtol=1e-6)
    assert np.isclose(alternante.conteo.sum(), 1.0)


def test_material_no_especificado_no_produce_factor_falso():
    assert math.isnan(factor_goodman(100e6, 50e6, MATERIALES[0], ENTALLAS[0]))


def test_goodman_disminuye_al_aumentar_concentracion():
    factores = [factor_goodman(100e6, 40e6, MATERIALES[2], e) for e in ENTALLAS]
    assert factores[0] > factores[1] > factores[2]


def test_media_compresiva_no_aumenta_artificialmente_el_factor():
    n_cero = factor_goodman(100e6, 0, MATERIALES[2], ENTALLAS[1])
    n_comp = factor_goodman(100e6, -200e6, MATERIALES[2], ENTALLAS[1])
    assert n_comp == n_cero


def test_refinamiento_angular_converge_al_resultante():
    mv, mh, d = 123.0, 79.0, .03
    exacta = math.hypot(mv, mh)/(math.pi*d**3/32)
    errores = []
    for n in (18, 36, 72, 144):
        valores = [abs(tension_flexion_punto(mv, mh, d, p)) for p in np.linspace(0, 2*math.pi, n, endpoint=False)]
        errores.append(abs(max(valores)-exacta))
    assert errores[-1] <= errores[0]
    assert errores[-1]/exacta < 3e-4
