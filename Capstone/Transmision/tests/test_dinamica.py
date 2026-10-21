import csv
import json
import math
import pytest
from simulacion_transmision import RAIZ
from simulacion_dinamica import ejecutar
from transmision.dinamica import diferencia_tensiones, reparto_simetrico, fuerzas_poleas, evaluar


def test_equilibrio_torque_y_reparto_uniforme():
    r = diferencia_tensiones(88.924, .14, 3)
    assert r["delta_total_n"]*.14 == pytest.approx(88.924)
    assert r["delta_individual_n"]*3 == pytest.approx(r["delta_total_n"])


def test_suma_vectorial_y_signos():
    alpha = .18
    r = fuerzas_poleas(300, 100, 3, alpha)
    assert r["conducida_fx_n"] == pytest.approx(1200*math.cos(alpha))
    assert r["conducida_fy_n"] == pytest.approx(600*math.sin(alpha))
    assert r["conducida_fx_n"] == pytest.approx(r["conducida_superior_fx_n"]+r["conducida_inferior_fx_n"])
    assert r["conducida_fy_n"] == pytest.approx(r["conducida_superior_fy_n"]+r["conducida_inferior_fy_n"])
    assert r["motriz_fx_n"] == -r["conducida_fx_n"]
    assert r["motriz_fy_n"] == -r["conducida_fy_n"]
    inverso = fuerzas_poleas(300, 100, 3, alpha, -1)
    assert inverso["conducida_fx_n"] == r["conducida_fx_n"]
    assert inverso["conducida_fy_n"] == -r["conducida_fy_n"]
    assert inverso["conducida_fr_n"] == r["conducida_fr_n"]
    # Tres correas idénticas suman exactamente tres fuerzas individuales.
    individual = fuerzas_poleas(300, 100, 1, alpha)
    assert r["conducida_fr_n"] == pytest.approx(3*individual["conducida_fr_n"])


def test_sin_torque_y_limite_admisibilidad():
    r = reparto_simetrico(200, 0)
    assert r["tenso_individual_n"] == r["flojo_individual_n"] == 200
    f = fuerzas_poleas(200, 200, 3, .18)
    assert f["conducida_fy_n"] == 0
    assert reparto_simetrico(200, 400)["admisible_no_negatividad"]
    assert not reparto_simetrico(200, 401)["admisible_no_negatividad"]
    p = json.loads((RAIZ/"parametros.json").read_text())
    no_valido = evaluar(1000, 10, p)
    assert not no_valido["admisible_no_negatividad"]
    assert no_valido["conducida_fr_n"] is None


def test_momentos_de_tangentes_en_ambas_poleas():
    alpha = .18
    c, s = math.cos(alpha), math.sin(alpha)
    # Contactos superior/inferior en conducida: r=(R sin a, +/- R cos a).
    # En motriz: r=(r sin a, +/- r cos a), fuerzas opuestas.
    for signo in (-1, 1):
        f = fuerzas_poleas(300, 100, 3, alpha, signo)
        torque = sum(.14*s*f[f"conducida_{rama}_fy_n"]-y*.14*c*f[f"conducida_{rama}_fx_n"]
                     for rama,y in (("superior",1),("inferior",-1)))
        assert torque == pytest.approx(signo*3*(300-100)*.14)
        torque_motriz = sum(.05*s*(-f[f"conducida_{rama}_fy_n"])-y*.05*c*(-f[f"conducida_{rama}_fx_n"])
                            for rama,y in (("superior",1),("inferior",-1)))
        assert torque_motriz == pytest.approx(-signo*3*(300-100)*.05)


@pytest.mark.parametrize("args", [(-1,.14,3),(1,0,3),(1,.14,0),(1,.14,3.5),(float('nan'),.14,3)])
def test_entradas_invalidas(args):
    with pytest.raises(ValueError):
        diferencia_tensiones(*args)


def test_ejecucion_escenarios_y_correlacion(tmp_path):
    r = ejecutar(salida=tmp_path)
    assert r["intervalos_3c"] == 1440
    with (tmp_path/"tensiones_y_fuerzas_condicionales_3c.csv").open(encoding="utf-8") as f:
        serie = list(csv.DictReader(f))
    assert len(serie) == 1440
    critico = next(c for c in r["casos_criticos_correlacionados"] if c["criterio"] == "torque_maximo")
    original = next(c for c in serie if int(c["paso"]) == critico["paso"])
    assert float(original["torque_conducida_magnitud_nm"]) == critico["torque_conducida_magnitud_nm"]
    assert r["motor_nominal_externo"]["escenario"] != serie[0]["escenario"]
    assert r["motor_nominal_externo"]["delta_total_n"] == pytest.approx(5500/7.592182246175334)
    assert all(s["escenario"] == "historial_3c_inclinacion" for s in serie)
    assert (tmp_path/"trazabilidad_sha256.json").exists()
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/"resultados/etapa_5d1")


def test_solo_equilibrio_opcional(tmp_path):
    r = ejecutar(salida=tmp_path, condicional=False)
    assert not r["modelo_condicional_activado"]
    assert "Ts_individual_n" not in r["motor_nominal_externo"]
    assert not (tmp_path/"tensiones_y_fuerzas_condicionales_3c.csv").exists()
