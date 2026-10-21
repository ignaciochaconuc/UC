import hashlib
import json
import math
from pathlib import Path
import pytest
from simulacion_transmision import RAIZ
from actualizacion_ambas_poleas import ejecutar
from transmision.polea_inventor import verificar_motriz_inventor, torsion_cubo_liso_polea


def config():
    return json.loads((RAIZ/"parametros_poleas.json").read_text(encoding="utf-8"))


def test_motriz_cotas_y_envolventes():
    c=config(); p=c["poleas"]["motriz"]
    g=verificar_motriz_inventor(c)
    assert p["diametro_interior_cubo_mm"] == 38
    assert p["diametro_exterior_cubo_mm"] == 45
    assert p["numero_aberturas"] == 8 and p["diametro_aberturas_mm"] == 13
    assert p["ancho_chaveta_mm"] == 10 and p["tolerancia_ancho_chavetero"] == "JS9"
    assert p["longitud_activa_chaveta_mm"] is None
    assert p["altura_contacto_chaveta_mm"] is None
    assert p["diametro_interior_llanta_mm"] is None
    assert p["ancho_llanta_cad_mm"] == 54
    assert p["distancia_caras_interiores_pestanas_mm"] == 50
    assert p["longitud_cubo_mm"] == 62
    assert g["diametro_fondo_verificado_mm"] == pytest.approx(78)
    assert g["saliente_cubo_sobre_cara_exterior_pestana_mm"] == 8
    assert g["espesor_radial_nominal_cubo_liso_mm"] == 3.5
    assert g["coincidencia_angulo_nominal_gates"]
    assert not g["compatibilidad_normativa_completa_aprobada"]


def test_conducida_configuracion_no_alterada():
    historico=json.loads((RAIZ/"resultados/etapa_5e1/revision_inventor_2026_10_21/parametros_utilizados.json").read_text(encoding="utf-8"))
    assert config()["poleas"]["conducida"] == historico["poleas"]["conducida"]
    assert config()["material"] == historico["material"]


def test_torsion_motriz_radio_y_unidades():
    c=config(); T=31.75855921123371
    r=torsion_cubo_liso_polea(T,c,"motriz")
    J=math.pi*(45**4-38**4)/32
    assert r["tau_torsion_nominal_lisa_mpa"] == pytest.approx(T*1000*22.5/J)
    assert torsion_cubo_liso_polea(0,c,"motriz")["tau_torsion_nominal_lisa_mpa"] == 0
    with pytest.raises(ValueError):
        torsion_cubo_liso_polea(T,c,"otra")


@pytest.mark.parametrize("cambio", [
    {"diametro_interior_llanta_mm":78}, {"profundidad_radial_garganta_mm":12},
    {"ancho_llanta_cad_mm":50}, {"numero_radios":8}, {"numero_aberturas":0},
    {"longitud_cubo_mm":50}, {"saliente_cubo_hasta_cara_interior_pestana_mm":12}])
def test_rechazo_mezcla_de_cotas(cambio):
    c=config(); c["poleas"]["motriz"].update(cambio)
    with pytest.raises(ValueError):
        verificar_motriz_inventor(c)


def test_revision_conjunta_conservacion_y_escenarios(tmp_path):
    archivo=RAIZ/"resultados/etapa_5e1/revision_inventor_2026_10_21/resumen.json"
    antes=hashlib.sha256(archivo.read_bytes()).hexdigest()
    r=ejecutar(tmp_path)
    assert antes == hashlib.sha256(archivo.read_bytes()).hexdigest()
    assert len(r["cargas"]) == 8
    assert {c["polea"] for c in r["cargas"]} == {"motriz","conducida"}
    assert not r["resistencia_aprobada"] and not r["fem_ejecutado"]
    assert r["factores_seguridad"] is None
    assert len(r["fuentes"]) == 2
    assert all(len(f["sha256"]) == 64 for f in r["fuentes"])
    assert r["geometria"]["conducida"]["diferencia_angulo_grados"] == -4
    hashes=json.loads((tmp_path/"trazabilidad_sha256.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    assert (tmp_path/"sensibilidad_pretension_separada.csv").exists()
    with pytest.raises(ValueError):
        ejecutar(RAIZ/"resultados/etapa_5e1/revision_inventor_2026_10_21")
