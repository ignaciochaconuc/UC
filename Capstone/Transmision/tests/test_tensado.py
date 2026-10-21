import json
import pytest
from simulacion_transmision import RAIZ
from simulacion_tensado import ejecutar
from transmision.tensado import comprobar_diametros, ajuste_centros, recorridos_catalogo, gargantas_spa, resolver_5c
from transmision.calculos import resolver


def parametros():
    return json.loads((RAIZ/"parametros.json").read_text(encoding="utf-8"))


def test_diametros_exteriores_y_referencia():
    for ref, ext in ((100., 105.6), (280., 285.6)):
        r = comprobar_diametros(ref, ext)
        assert r["diferencia_diametral_mm"] == pytest.approx(5.6)
        assert r["altura_radial_cad_mm"] == pytest.approx(2.8)
        assert r["desviacion_diametral_cad_vs_tabla_mm"] == pytest.approx(.1)
        assert not r["compatibilidad_exacta_tabla"]


def test_recorridos_centros_y_unidades():
    r = recorridos_catalogo(1600)
    assert r == {"acercamiento_instalacion_mm": 25., "alejamiento_tensado_mm": 35.}
    a = ajuste_centros(493.316, 25, 35)
    assert a["centros_minimos_mm"] == pytest.approx(468.316)
    assert a["centros_maximos_mm"] == pytest.approx(528.316)
    assert a["recorrido_total_minimo_mm"] == pytest.approx(60.)
    assert a["centros_maximos_mm"]-a["centros_minimos_mm"] == pytest.approx(60.)


def test_gargantas_normalizadas_y_angulo_por_diametro():
    for d, angulo in ((100, 34), (280, 38)):
        r = gargantas_spa(d, 3, 3)
        assert r["ancho_llanta_nominal_mm"] == 50
        assert r["angulo_garganta_grados"] == angulo
        assert r["paso_e_mm"] == 15
    assert gargantas_spa(118, 3, 3)["angulo_garganta_grados"] == 34


def test_conservacion_5ab_y_solo_diametros_referencia():
    p = parametros()
    r = resolver_5c(p)
    anterior = json.loads((RAIZ/"resultados/resumen.json").read_text(encoding="utf-8"))
    calculado = resolver(p)
    for etapa in ("etapa_5a", "etapa_5b"):
        assert calculado[etapa] == anterior[etapa]
    for clave, valor in r["geometria_nominal"].items():
        assert valor == anterior["etapa_5a"][clave]
    assert r["geometria_nominal"]["longitud_exacta_mm"] == pytest.approx(1600, abs=.001)
    assert r["tension_inicial_n"] is None


@pytest.mark.parametrize("funcion,args", [
    (comprobar_diametros, (100, 99)), (comprobar_diametros, (0, 105.6)),
    (comprobar_diametros, (100, float('nan'))), (ajuste_centros, (20, 25, 35)),
    (ajuste_centros, (493, -25, 35)), (recorridos_catalogo, (1.6,)),
    (recorridos_catalogo, (2000,)), (recorridos_catalogo, (1600, 'SPB')),
    (gargantas_spa, (100, 2, 3)), (gargantas_spa, (100, 3.5, 3)),
    (gargantas_spa, (80, 3, 3)), (gargantas_spa, (100, True, 3)),
])
def test_rechazo_parametros_invalidos(funcion, args):
    with pytest.raises(ValueError):
        funcion(*args)


def test_ejecucion_5c_y_hash_historico(tmp_path):
    ejecutar(salida=tmp_path)
    assert (tmp_path/"ajuste_centros.csv").exists()
    trazabilidad = json.loads((tmp_path/"fuentes_y_trazabilidad.json").read_text(encoding="utf-8"))
    assert "geometria_5a.csv" in trazabilidad["sha256_historicos"]
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/"resultados")
