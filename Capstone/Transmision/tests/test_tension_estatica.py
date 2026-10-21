import pytest
from simulacion_tension_estatica import ejecutar
from transmision.tension_estatica import (
    tension_estatica, tramo_libre, deflexion_recomendada, fuerzas_deflexion,
    constantes_spa, FUENTE_5D1,
)


def test_constantes_y_construccion():
    assert constantes_spa() == {"R": 2.5, "M": .12, "Y_n": 20.}
    assert FUENTE_5D1["tabla"] == 13
    with pytest.raises(ValueError):
        constantes_spa(construccion="Super HC MN")


def test_valores_referencia_y_potencia_correcta():
    v = 7.592182246175334
    Ts = tension_estatica(5.5, 3, v, .94)
    assert Ts == pytest.approx(197.27, abs=.02)
    t = tramo_libre(493.316, 100, 280)
    assert t == pytest.approx(485.04, abs=.01)
    assert deflexion_recomendada(t) == pytest.approx(4.85, abs=.01)
    f = fuerzas_deflexion(Ts, t, 1600)
    assert f["fuerza_minima_n"] == pytest.approx(8.13, abs=.01)
    assert f["fuerza_maxima_n"] == pytest.approx(12.08, abs=.01)
    assert tension_estatica(7.15, 3, v, .94) > Ts


def test_comprobacion_dimensional_y_numero_correas():
    # 1 kW / 1 m/s = 1000 N; 475 incorpora unidades y factor del fabricante.
    assert tension_estatica(1, 1, 1, 1, R=2, M=.12) == pytest.approx(475.12)
    assert tramo_libre(400, 100, 100) == 400
    assert fuerzas_deflexion(200, 500, 1600)["fuerza_minima_n"] == pytest.approx(8.25)
    assert fuerzas_deflexion(200, 500, 1600, polea_libre=False)["fuerza_minima_n"] == pytest.approx(8.8)
    assert tension_estatica(5.5, 2, 7.59, .94) > tension_estatica(5.5, 3, 7.59, .94)


@pytest.mark.parametrize("args", [(0,3,7.59,.94),(5.5,0,7.59,.94),(5.5,2.5,7.59,.94),
                                 (5.5,3,0,.94),(5.5,3,7.59,1.1),(5.5,3,float('nan'),.94)])
def test_rechazo_entradas(args):
    with pytest.raises(ValueError):
        tension_estatica(*args)


def test_ejecucion_conserva_historicos_y_separa_salidas(tmp_path):
    r = ejecutar(salida=tmp_path)
    assert len(r["correas_individuales"]) == 3
    assert r["tensiones_dinamicas_ramales"] is None
    assert (tmp_path/"validaciones.csv").exists()
    from simulacion_transmision import RAIZ
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/"resultados/etapa_5c")
