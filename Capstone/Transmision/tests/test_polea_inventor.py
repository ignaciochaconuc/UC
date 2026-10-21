import copy
import hashlib
import json
import math
import pytest
from simulacion_transmision import RAIZ
from actualizacion_polea_inventor import ejecutar
from transmision.polea_inventor import verificar_inventor, torsion_cubo_liso
from transmision.poleas import verificar_resistencia


def config():
    return json.loads((RAIZ/"parametros_poleas.json").read_text(encoding="utf-8"))


def test_cotas_vigentes_y_superficies():
    c=config()
    p=c["poleas"]["conducida"]
    r=verificar_inventor(c)
    assert p["diametro_exterior_cubo_mm"] == 75
    assert p["diametro_interior_cubo_mm"] == 35
    assert p["ancho_llanta_cad_mm"] == 60
    assert p["longitud_cubo_mm"] == 78.6
    assert r["diametro_fondo_verificado_mm"] == pytest.approx(258)
    assert p["diametro_interior_llanta_mm"] is None
    assert r["saliente_cubo_sobre_cara_exterior_pestana_mm"] == pytest.approx(18.6)
    assert r["area_total_aberturas_proyeccion_mm2"] == pytest.approx(6*math.pi*70**2/4)
    assert p["numero_radios"] is None
    assert p["tipo_cuerpo"] == "aligerado_aberturas_circulares"
    assert not r["compatibilidad_normativa_aprobada"]
    assert r["diferencia_angulo_grados"] == -4


def test_torsion_lisa_no_acepta_resistencia_total():
    c=config()
    r=torsion_cubo_liso(88.92396579145439,c)
    J=math.pi*(75**4-35**4)/32
    assert r["tau_torsion_nominal_lisa_mpa"] == pytest.approx(88.92396579145439*1000*37.5/J)
    checks=verificar_resistencia({"torque_correas_firmado_nm":88.924,"fr_n":1169.524},c["poleas"]["conducida"],c["material"])
    assert not any(v["comprobacion"] == "cuerpo_disco_torsion_media" for v in checks)
    assert all(v["estado"] == "pendiente" for v in checks)
    assert c["material"]["modulo_young_mpa"] is None


@pytest.mark.parametrize("cambio", [
    {"diametro_interior_llanta_mm":258}, {"numero_aberturas":0},
    {"profundidad_radial_garganta_mm":10}, {"numero_radios":6},
    {"tipo_cuerpo":"disco"}, {"diametro_pestanas_mm":270}])
def test_no_mezclar_interpretaciones(cambio):
    c=config()
    c["poleas"]["conducida"].update(cambio)
    with pytest.raises(ValueError):
        verificar_inventor(c)


def test_revision_conserva_linea_base_y_cargas(tmp_path):
    base=RAIZ/"resultados/etapa_5e1/resumen.json"
    antes=hashlib.sha256(base.read_bytes()).hexdigest()
    r=ejecutar(tmp_path)
    assert antes == hashlib.sha256(base.read_bytes()).hexdigest()
    assert r["factores_seguridad"] is None
    assert not r["fem_ejecutado"] and not r["resistencia_aprobada"]
    assert len(r["cargas_conducida"]) == 4
    assert r["cargas_conducida"][-1]["escenario"] == "motor_nominal_ideal_externo_a_3c"
    assert (tmp_path/"dimensiones_confirmadas_y_pendientes.csv").exists()
    with pytest.raises(ValueError):
        ejecutar(RAIZ/"resultados/etapa_5e1")
