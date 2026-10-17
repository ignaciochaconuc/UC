import math

import numpy as np
import pandas as pd

from estructural.resistencia_fatiga import (
    ENTALLAS, MATERIALES, MATERIAL_OVAKO, EscenarioMaterial, contar_rainflow,
    factor_goodman, factores_marin, limite_fatiga_efectivo,
    seleccionar_ciclo_goodman, tension_flexion_punto,
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


def test_propiedades_ovako_documentadas_y_trazables():
    assert MATERIAL_OVAKO.material == "SAE 4140 +QT"
    assert MATERIAL_OVAKO.fabricante == "Ovako"
    assert MATERIAL_OVAKO.variante == "6115"
    assert MATERIAL_OVAKO.sy_pa == 940e6
    assert MATERIAL_OVAKO.sut_pa == 1040e6
    assert MATERIAL_OVAKO.fuente == "ovako_4140_qt_2026"


def test_marin_aplica_todos_los_factores():
    from estructural.resistencia_fatiga import escenarios_ovako_marin
    material = next(m for m in escenarios_ovako_marin()
                    if m.acabado_superficial == "mecanizado" and m.confiabilidad_porcentaje == 95)
    factores = factores_marin(material, .0215463)
    esperado = factores["se_prima_pa"]*factores["ka"]*factores["kb"]*factores["kc"]*factores["kd"]*factores["ke"]*factores["k_misc"]
    assert np.isclose(limite_fatiga_efectivo(material, .0215463), esperado)
    assert factores["se_prima_pa"] == .5*1040e6
    assert 0 < factores["ka"] <= 1 and 0 < factores["kb"] <= 1


def test_fatiga_sin_parametros_permanece_indefinida():
    assert limite_fatiga_efectivo(MATERIAL_OVAKO, .0215463) is None
    assert math.isnan(factor_goodman(50e6, 100e6, MATERIAL_OVAKO, ENTALLAS[1], .0215463))


def test_ciclo_critico_se_selecciona_independientemente_por_material():
    ciclos = [
        pd.DataFrame([{"amplitud_pa": 100e6, "media_pa": 0.0, "conteo": 1.0}]),
        pd.DataFrame([{"amplitud_pa": 20e6, "media_pa": 300e6, "conteo": 1.0}]),
    ]
    domina_amplitud = EscenarioMaterial("a", 500e6, 2000e6, 100e6, "prueba")
    domina_media = EscenarioMaterial("b", 500e6, 400e6, 1000e6, "prueba")
    _, j_a, _ = seleccionar_ciclo_goodman(ciclos, domina_amplitud, ENTALLAS[0], .03)
    _, j_m, _ = seleccionar_ciclo_goodman(ciclos, domina_media, ENTALLAS[0], .03)
    assert j_a == 0
    assert j_m == 1
