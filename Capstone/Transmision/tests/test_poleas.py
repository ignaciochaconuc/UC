import copy
import csv
import hashlib
import json
import math
import pytest
from simulacion_transmision import RAIZ
from simulacion_poleas import ejecutar, separar_cargas
from transmision.poleas import (seccion_anular, esfuerzo_cubo, cortante_disco,
    chaveta_nominal, validar_parametros, verificar_resistencia)


def config():
    return json.loads((RAIZ/"parametros_poleas.json").read_text(encoding="utf-8"))


def test_anillo_unidades_y_soluciones_analiticas_sinteticas():
    # Dimensiones sintéticas de prueba; no se incorporan al diseño de poleas.
    s = seccion_anular(20, 0)
    assert s["J_mm4"] == pytest.approx(math.pi*20**4/32)
    assert s["J_mm4"] == pytest.approx(2*s["I_mm4"])
    r = esfuerzo_cubo(1, 0, 0, 20, 0)
    assert r["tau_torsion_mpa"] == pytest.approx(16*1000/(math.pi*20**3))
    assert r["von_mises_parcial_mpa"] == pytest.approx(math.sqrt(3)*r["tau_torsion_mpa"])
    b = esfuerzo_cubo(0, 100, 10, 20, 0)
    assert b["sigma_flexion_mpa"] == pytest.approx(32*1000/(math.pi*20**3))


def test_disco_chaveta_sinteticos_y_limite_sin_torque():
    assert cortante_disco(2, 10, 5) == pytest.approx(2000/(2*math.pi*100*5))
    c = chaveta_nominal(1, 20, 2, 1, 10)
    assert c["fuerza_tangencial_union_n"] == pytest.approx(100)
    assert c["tau_chaveta_mpa"] == pytest.approx(5)
    assert c["presion_contacto_media_mpa"] == pytest.approx(10)
    assert cortante_disco(0, 10, 5) == 0


@pytest.mark.parametrize("fn,args", [(seccion_anular,(20,20)), (seccion_anular,(20,-1)),
    (seccion_anular,(float('nan'),1)), (esfuerzo_cubo,(1,100,-1,20,10)),
    (cortante_disco,(1,10,0)), (chaveta_nominal,(1,20,0,1,10))])
def test_dimensiones_invalidas(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def test_geometria_incompleta_es_pendiente_sin_inventar():
    p = config()
    r = verificar_resistencia({"torque_correas_firmado_nm": 10, "fr_n": 100}, p["poleas"]["motriz"], p["material"])
    assert all(c["estado"] == "pendiente" and c["resultado"] is None for c in r)
    assert p["material"]["limite_fluencia_mpa"] is None
    assert all(v is None for v in p["poleas"]["motriz"].values())


def test_material_sin_condicion_rechazado():
    c = config()
    c["material"]["limite_fluencia_mpa"] = 370
    with pytest.raises(ValueError):
        validar_parametros(c["poleas"]["motriz"], c["material"], 105.6)
    c = config()
    c["poleas"]["motriz"].update(diametro_interior_cubo_mm=50, diametro_exterior_cubo_mm=40)
    with pytest.raises(ValueError):
        validar_parametros(c["poleas"]["motriz"], c["material"], 105.6)


def test_radios_propios_cargas_sin_mezclar_escenarios():
    with (RAIZ/"resultados/etapa_5d2/casos_criticos_correlacionados.csv").open(encoding="utf-8") as f:
        fila = next(csv.DictReader(f))
    m, c = separar_cargas(fila, "motriz", 50), separar_cargas(fila, "conducida", 140)
    assert abs(c["torque_correas_firmado_nm"])/abs(m["torque_correas_firmado_nm"]) == pytest.approx(2.8)
    assert m["fx_n"] == pytest.approx(-c["fx_n"])
    assert m["paso"] == c["paso"] == 377
    with pytest.raises(ValueError):
        separar_cargas(fila, "motriz", 140)
    alterada = copy.copy(fila)
    alterada["conducida_fr_n"] = '10'
    with pytest.raises(ValueError):
        separar_cargas(alterada, "conducida", 140)


def test_ejecucion_sin_fem_conserva_anteriores(tmp_path):
    archivo = RAIZ/"resultados/etapa_5d2/resumen.json"
    antes = hashlib.sha256(archivo.read_bytes()).hexdigest()
    r = ejecutar(salida=tmp_path)
    assert not r["fem_ejecutado"]
    assert r["factores_seguridad"] is None
    assert len(r["cargas"]) == 8
    assert {c["escenario"] for c in r["cargas"]} == {"historial_3c_inclinacion", "motor_nominal_ideal_externo_a_3c"}
    assert all(c["paso"] is None for c in r["cargas"] if c["escenario"].startswith("motor"))
    assert antes == hashlib.sha256(archivo.read_bytes()).hexdigest()
    hashes = json.loads((tmp_path/"trazabilidad_sha256.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256(__import__('pathlib').Path(n).read_bytes()).hexdigest() == h for n,h in hashes.items())
    assert (tmp_path/"especificacion_fem.md").exists()
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/"resultados/etapa_5d2")
