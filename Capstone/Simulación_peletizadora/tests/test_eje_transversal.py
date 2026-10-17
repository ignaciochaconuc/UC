from types import SimpleNamespace

import numpy as np
import pandas as pd

from estructural.cargas_eje import (
    cargar_serie_2c,
    tabla_fuerzas_rodamientos,
    validar_conservacion_reparto,
)
from estructural.config_eje import CONFIG_EJE, SegmentoEje
from estructural.geometria_eje import crear_malla, validar_segmentos
from estructural.viga_eb import SistemaViga, carga_uniforme_consistente


def _viga_uniforme(longitud=1.0, elementos=40):
    segmento = SegmentoEje("uniforme", 0.0, longitud, 0.04)
    config = SimpleNamespace(
        segmentos=(segmento,), modulo_young_pa=205e9,
        densidad_eje_kg_m3=0.0, gravedad_m_s2=9.80665,
    )
    return SistemaViga(np.linspace(0, longitud, elementos + 1), config), segmento


def test_geometria_segmentada_continua_y_cotas_principales():
    validar_segmentos(CONFIG_EJE.segmentos, CONFIG_EJE.longitud_m)
    assert CONFIG_EJE.longitud_m == 0.270
    assert CONFIG_EJE.segmentos[0].diametro_exterior_m < 0.024
    assert CONFIG_EJE.segmentos[4].diametro_exterior_m == 0.036
    assert np.isclose(sum(s.longitud_m for s in CONFIG_EJE.segmentos), 0.270)


def test_malla_incluye_cambios_y_rodamientos():
    nodos = crear_malla(CONFIG_EJE, [])
    requeridos = [s.x_inicio_m for s in CONFIG_EJE.segmentos] + [s.x_fin_m for s in CONFIG_EJE.segmentos]
    requeridos += list(CONFIG_EJE.rodamientos_izquierdos_m + CONFIG_EJE.rodamientos_derechos_m)
    assert all(np.any(np.isclose(nodos, x, atol=1e-12)) for x in requeridos)
    assert np.diff(nodos).max() <= CONFIG_EJE.longitud_maxima_elemento_m + 1e-12


def test_reparto_rodamientos_conserva_cargas_y_resultantes_quedan_dentro():
    tabla = tabla_fuerzas_rodamientos(cargar_serie_2c(CONFIG_EJE), CONFIG_EJE)
    validar_conservacion_reparto(tabla)
    assert not tabla.resultante_r1_fuera_rodamientos.any()
    assert not tabla.resultante_r2_fuera_rodamientos.any()


def test_reproduce_maximos_de_etapa_2c():
    datos = cargar_serie_2c(CONFIG_EJE)
    assert np.isclose((datos.fuerza_rodillo_1_n + datos.fuerza_rodillo_2_n).max(), 14432.818, rtol=1e-6)
    assert np.isclose(max(datos.fuerza_rodillo_1_n.max(), datos.fuerza_rodillo_2_n.max()), 8249.372, rtol=1e-6)


def test_viga_biempotrada_carga_central_vs_solucion_analitica():
    sistema, segmento = _viga_uniforme(elementos=40)
    P = 1000.0; L = 1.0; E = sistema.config.modulo_young_pa; I = segmento.inercia_m4
    cargas = sistema.cargas_vacias(); sistema.agregar_carga_puntual(cargas, 0.5, P)
    solucion = sistema.resolver(cargas)
    assert np.isclose(solucion.desplazamientos[2*20, 0], P*L**3/(192*E*I), rtol=2e-6)
    assert np.allclose(solucion.reacciones[sistema.restringidos[[0, 2]], 0], [-P/2, -P/2], rtol=2e-6)
    assert np.allclose(np.abs(solucion.reacciones[sistema.restringidos[[1, 3]], 0]), P*L/8, rtol=2e-6)


def test_viga_biempotrada_carga_distribuida_vs_solucion_analitica():
    sistema, segmento = _viga_uniforme(elementos=40)
    q = 1000.0; L = 1.0; E = sistema.config.modulo_young_pa; I = segmento.inercia_m4
    cargas = sistema.cargas_vacias(); equivalentes = np.zeros((40, 4))
    for e, le in enumerate(sistema.longitudes):
        fe = carga_uniforme_consistente(q, le); equivalentes[e] = fe
        cargas[2*e:2*e+4, 0] += fe
    solucion = sistema.resolver(cargas)
    assert np.isclose(solucion.desplazamientos[2*20, 0], q*L**4/(384*E*I), rtol=2e-6)
    assert np.allclose(solucion.reacciones[sistema.restringidos[[0, 2]], 0], [-q*L/2, -q*L/2], rtol=2e-6)
    assert np.allclose(np.abs(solucion.reacciones[sistema.restringidos[[1, 3]], 0]), q*L**2/12, rtol=2e-6)


def test_empatramientos_equilibrio_y_simetria():
    sistema, _ = _viga_uniforme(elementos=20)
    cargas = sistema.cargas_vacias()
    sistema.agregar_carga_puntual(cargas, .3, 400)
    sistema.agregar_carga_puntual(cargas, .7, 400)
    solucion = sistema.resolver(cargas)
    assert np.all(solucion.desplazamientos[sistema.restringidos, 0] == 0)
    assert abs(solucion.reacciones[0, 0] + solucion.reacciones[-2, 0] + 800) < 1e-8
    desplazamientos = solucion.desplazamientos[0::2, 0]
    assert np.allclose(desplazamientos, desplazamientos[::-1], rtol=1e-10, atol=1e-14)


def test_convergencia_desplazamiento_central():
    errores = []
    for elementos in (4, 8, 16):
        sistema, segmento = _viga_uniforme(elementos=elementos)
        cargas = sistema.cargas_vacias(); sistema.agregar_carga_puntual(cargas, .5, 1000)
        u = sistema.resolver(cargas).desplazamientos[elementos, 0]
        exacta = 1000/(192*sistema.config.modulo_young_pa*segmento.inercia_m4)
        errores.append(abs(u-exacta))
    assert max(errores) < 1e-12
