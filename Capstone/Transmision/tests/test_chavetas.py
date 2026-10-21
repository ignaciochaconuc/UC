import hashlib
import json
from pathlib import Path
import pytest
from simulacion_transmision import RAIZ
from simulacion_chavetas import ejecutar
from transmision.chavetas import (candidata_normalizada, fuerza_tangencial_union,
    ligamento_cubo, comprobar_eje_real, verificar_longitud_activa, sensibilidad_chaveta)


def test_filas_normalizadas_y_frontera_38():
    for d in (35,38):
        c=candidata_normalizada(d)
        assert (c["b_mm"],c["h_mm"]) == (10,8)
        assert c["profundidad_cubo_nominal_mm"] == 3.3
        assert c["profundidad_cubo_max_mm"] == 3.5
        assert c["profundidad_eje_nominal_mm"] == 5
    for d in (30,38.01,0,float('nan')):
        with pytest.raises(ValueError):
            candidata_normalizada(d)


def test_equilibrio_fuerza_contacto_y_unidades():
    assert fuerza_tangencial_union(1,20) == pytest.approx(100)
    assert fuerza_tangencial_union(-1,20) == pytest.approx(100)
    assert fuerza_tangencial_union(0,20) == 0
    F=fuerza_tangencial_union(31.75855921123371,38)
    assert F*38/2000 == pytest.approx(31.75855921123371)


def test_ligamento_motriz_centro_y_esquina():
    r=ligamento_cubo(45,38,10,3.3)
    assert r["pared_radial_lisa_mm"] == 3.5
    assert r["ligamento_central_fondo_mm"] == pytest.approx(.2)
    assert r["ligamento_radial_esquina_ideal_mm"] < 0
    assert not r["fondo_plano_contenido_en_exterior_ideal"]
    assert r["diametro_exterior_minimo_envolvente_sin_reserva_mm"] > 45
    superior=ligamento_cubo(45,38,10,3.5)
    assert superior["ligamento_central_fondo_mm"] == pytest.approx(0)
    assert not superior["fondo_plano_contenido_en_exterior_ideal"]


def test_ligamento_conducida_no_es_factor_seguridad():
    r=ligamento_cubo(75,35,10,3.3)
    assert r["ligamento_central_fondo_mm"] == pytest.approx(16.7)
    assert r["ligamento_radial_esquina_ideal_mm"] > 0
    assert r["fondo_plano_contenido_en_exterior_ideal"]


def test_sensibilidad_largo_activo_y_alturas_explicitas():
    c=candidata_normalizada(38)
    r=sensibilidad_chaveta(1,20,c,[20,40],62)
    assert r[0]["tau_media_chaveta_mpa"] == pytest.approx(.5)
    assert r[0]["presion_media_cubo_mpa"] == pytest.approx(100/(3*20))
    assert r[0]["presion_media_eje_mpa"] == pytest.approx(1)
    assert r[1]["tau_media_chaveta_mpa"] == pytest.approx(r[0]["tau_media_chaveta_mpa"]/2)
    with pytest.raises(ValueError):
        verificar_longitud_activa(63,62)


def test_eje_real_no_se_deduce_del_motor():
    assert comprobar_eje_real(38,None)["coincidencia_nominal"] is None
    with pytest.raises(ValueError):
        comprobar_eje_real(38,38)
    assert comprobar_eje_real(38,38,"plano motor sintético")["coincidencia_nominal"]
    assert not comprobar_eje_real(38,35,"plano motor sintético")["coincidencia_nominal"]


@pytest.mark.parametrize("args",[(45,45,10,3.3),(45,38,40,3.3),(45,38,10,-1),(0,38,10,3.3)])
def test_geometria_invalida(args):
    with pytest.raises(ValueError):
        ligamento_cubo(*args)


def test_ejecucion_conserva_y_no_aprueba(tmp_path):
    f=RAIZ/"resultados/etapa_5e1/revision_ambas_poleas_2026_10_21/resumen.json"
    antes=hashlib.sha256(f.read_bytes()).hexdigest()
    r=ejecutar(salida=tmp_path)
    assert antes == hashlib.sha256(f.read_bytes()).hexdigest()
    assert not r["uniones_aprobadas"] and not r["fem_ejecutado"]
    assert r["factores_seguridad"] is None
    assert r["candidatas"][0]["ancho_cad_coincide_nominal"]
    assert r["candidatas"][1]["ancho_cad_coincide_nominal"] is None
    assert len(r["fuerzas_correlacionadas"]) == 8
    hashes=json.loads((tmp_path/"trazabilidad_sha256.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==v for n,v in hashes.items())
    assert (tmp_path/"sensibilidad_longitud_activa.csv").exists()
    with pytest.raises(ValueError):
        ejecutar(salida=RAIZ/"resultados/etapa_5e1")
