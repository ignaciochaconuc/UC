import json
import math

import pytest

from simulacion_transmision import RAIZ, ejecutar
from transmision.calculos import geometria, centros_para_longitud, dimensionar, balance_motor, resolver
from transmision.catalogo import capacidad_catalogo, factor_abrazamiento_conservador


def test_geometria_poleas_iguales_solucion_analitica():
    r = geometria(100, 100, 400, 1500)
    assert r["longitud_exacta_mm"] == pytest.approx(800+100*math.pi)
    assert r["abrazamiento_motriz_grados"] == pytest.approx(180)
    assert r["rpm_salida"] == pytest.approx(1500)


def test_longitud_exacta_inversion_y_aproximacion():
    r = geometria(100, 280, 493.316, 1450)
    assert r["relacion"] == pytest.approx(2.8)
    assert r["rpm_salida"] == pytest.approx(517.857142857)
    assert r["longitud_exacta_mm"] == pytest.approx(1600, abs=.002)
    assert r["longitud_exacta_mm"]-r["longitud_aproximada_mm"] == pytest.approx(.046004, abs=1e-6)
    assert r["longitud_exacta_mm"] > r["longitud_aproximada_mm"]
    a = centros_para_longitud(100, 280, 1600)
    assert geometria(100, 280, a, 1450)["longitud_exacta_mm"] == pytest.approx(1600)


def test_catalogo_construccion_y_no_extrapolacion():
    c = capacidad_catalogo(1450, 100, 2.8, 1600)
    assert c["basica_kw"] == 3.16
    assert c["adicional_relacion_kw"] == .54
    assert c["factor_longitud"] == .94
    with pytest.raises(ValueError):
        capacidad_catalogo(1400, 100, 2.8, 1600)
    with pytest.raises(ValueError):
        capacidad_catalogo(1450, 85, 2.8, 1600)
    with pytest.raises(ValueError):
        capacidad_catalogo(1450, 100, 4., 1600)
    assert factor_abrazamiento_conservador(.3649) == .94
    assert factor_abrazamiento_conservador(.3) == .96


def test_dimensionamiento_y_redondeo():
    r = dimensionar(5.5, 1.3, (3.16+.54)*.94*.94, 3)
    assert r["potencia_diseno_kw"] == pytest.approx(7.15)
    assert r["numero_minimo_correas"] == 3
    assert r["cumple_capacidad"]
    assert not dimensionar(5.5, 2., r["capacidad_correa_kw"], 3)["cumple_capacidad"]


def test_balance_separado_factor_servicio():
    assert balance_motor(5.5, .90, 4.805, 4.194)["margen_maximo_kw"] == pytest.approx(.145)
    assert not balance_motor(5.5, .85, 4.805, 4.194)["cubre_maximo_3c"]
    assert balance_motor(5.5, .85, 4.805, 4.194)["cubre_media_3c"]


@pytest.mark.parametrize("valores", [(0, 280, 493, 1450), (100, 280, 100, 1450),
                                  (100, 80, 493, 1450), (100, 280, 493, float('nan'))])
def test_geometria_invalida(valores):
    with pytest.raises(ValueError):
        geometria(*valores)


def test_parametros_incompatibles_y_eficiencia():
    p = json.loads((RAIZ/"parametros.json").read_text())
    p["construccion"] = "Super HC MN"
    with pytest.raises(ValueError):
        resolver(p)
    with pytest.raises(ValueError):
        balance_motor(5.5, 1.1, 4.805, 4.194)
    with pytest.raises(ValueError):
        dimensionar(5.5, 1.3, 3.3, 2.5)


def test_ejecucion_y_trazabilidad(tmp_path):
    resultado = ejecutar(salida=tmp_path)
    assert resultado["etapa_5b"]["numero_minimo_correas"] == 3
    assert (tmp_path/"balance_motor_eficiencias.csv").exists()
    fuente = json.loads((tmp_path/"fuentes_y_validacion.json").read_text(encoding="utf-8"))
    assert fuente["sha256_3c_conservado"]
