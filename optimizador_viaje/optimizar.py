"""Planificación discreta de noches y conexiones mediante MILP (SciPy/HiGHS)."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, timedelta
from html import escape
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def precio(opcion: dict, fecha: date) -> float | None:
    dia = fecha.isoformat()
    if dia in opcion.get("no_disponible", []):
        return None
    tabla = opcion["precio"]
    valor = tabla.get("por_fecha", {}).get(dia, tabla.get("base"))
    if valor is None:
        return None
    valor = float(valor)
    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"Precio inválido en {opcion.get('id', '?')}: {valor}")
    return valor


def construir_estancias(noches: list[dict]) -> list[dict]:
    """Agrupa noches consecutivas en etapas legibles de la ruta."""
    estancias = []
    for noche in noches:
        if (estancias and estancias[-1]["ciudad"] == noche["ciudad"]
                and estancias[-1]["hotel"] == noche["hotel"]):
            estancia = estancias[-1]
            estancia["fecha_ultima_noche"] = noche["fecha"]
            estancia["noches"] += 1
            estancia["costo_alojamiento"] = round(
                estancia["costo_alojamiento"] + noche["precio"], 2)
        else:
            estancias.append({
                "ciudad": noche["ciudad"],
                "hotel": noche["hotel"],
                "fecha_llegada": noche["fecha"],
                "fecha_ultima_noche": noche["fecha"],
                "noches": 1,
                "costo_alojamiento": noche["precio"],
            })
    for estancia in estancias:
        ultima = date.fromisoformat(estancia["fecha_ultima_noche"])
        estancia["fecha_salida"] = (ultima + timedelta(days=1)).isoformat()
    return estancias


def guardar_mapa(respuesta: dict, datos: dict, destino: Path) -> None:
    """Guarda un mapa HTML interactivo de la ruta europea elegida."""
    ciudad_por_id = {c["id"]: c for c in datos["ciudades"]}
    puntos = []
    for numero, estancia in enumerate(respuesta["estancias"], 1):
        ciudad = ciudad_por_id[estancia["ciudad"]]
        if "latitud" not in ciudad or "longitud" not in ciudad:
            raise ValueError(
                f"Faltan latitud y longitud para crear el mapa de {ciudad['id']}")
        puntos.append({
            "numero": numero,
            "ciudad": estancia["ciudad"],
            "lat": float(ciudad["latitud"]),
            "lon": float(ciudad["longitud"]),
            "noches": estancia["noches"],
            "hotel": estancia["hotel"],
        })

    etapas = "".join(
        f'<li><strong>{escape(p["ciudad"])}</strong>: '
        f'{p["noches"]} noches en {escape(p["hotel"])}</li>' for p in puntos)
    secuencia = " → ".join(
        [escape(str(datos["origen"]))]
        + [escape(p["ciudad"]) for p in puntos]
        + [escape(str(datos["origen"]))])
    puntos_json = json.dumps(puntos, ensure_ascii=False).replace("</", "<\\/")
    contenido = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Mapa de la ruta</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
 integrity="sha256-p4NxAoJBhIINfQ3ynhFwqKjMZjspuJbMZMzp+4uMqVY=" crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
 integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#172033}}
#mapa{{height:580px;border:1px solid #bdd0d7;border-radius:14px}}
.leaflet-container{{overflow:hidden;position:relative;outline:0;background:#ddd}}
.leaflet-pane,.leaflet-tile,.leaflet-marker-icon,.leaflet-marker-shadow,
.leaflet-tile-container,.leaflet-pane>svg,.leaflet-pane>canvas{{position:absolute;left:0;top:0}}
.leaflet-map-pane canvas{{z-index:100}}.leaflet-tile-pane{{z-index:200}}
.leaflet-overlay-pane{{z-index:400}}.leaflet-shadow-pane{{z-index:500}}
.leaflet-marker-pane{{z-index:600}}.leaflet-tooltip-pane{{z-index:650}}.leaflet-popup-pane{{z-index:700}}
.leaflet-tile{{visibility:hidden}}.leaflet-tile-loaded{{visibility:inherit}}
.leaflet-marker-icon,.leaflet-marker-shadow{{display:block}}
.leaflet-tooltip{{position:absolute;padding:6px;background:white;border:1px solid #aaa;border-radius:4px;
white-space:nowrap;box-shadow:0 1px 3px #999}}
.leaflet-control{{position:relative;z-index:800;pointer-events:auto}}
.leaflet-top,.leaflet-bottom{{position:absolute;z-index:1000;pointer-events:none}}
.leaflet-top{{top:0}}.leaflet-right{{right:0}}.leaflet-bottom{{bottom:0}}.leaflet-left{{left:0}}
.leaflet-control-attribution{{background:rgba(255,255,255,.8);padding:2px 5px;font-size:11px}}
.numero-ruta{{background:#173f5f;color:white;border:3px solid white;border-radius:50%;
box-shadow:0 1px 5px #333;width:30px;height:30px;line-height:30px;text-align:center;font-weight:700}}
.nota{{color:#52616b;font-size:.9rem}}
</style></head><body>
<h1>Ruta optimizada</h1><p><strong>{secuencia}</strong></p>
<div id="mapa" role="img" aria-label="Mapa interactivo de la ruta europea"></div>
<ol>{etapas}</ol>
<p>Costo total: <strong>{respuesta['costo_total']:.2f}</strong> · Horas de traslado: <strong>{respuesta['horas_traslado']:.1f}</strong></p>
<p class="nota">Las líneas conectan ciudades y no representan el trazado exacto del transporte. El fondo necesita conexión a internet.</p>
<script>
const puntos = {puntos_json};
const mapa = L.map('mapa');
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}}).addTo(mapa);
const coordenadas = puntos.map(p => [p.lat, p.lon]);
L.polyline(coordenadas, {{color:'#e4572e', weight:5, opacity:.9}}).addTo(mapa);
puntos.forEach(p => {{
  const icono = L.divIcon({{className:'', html:`<div class="numero-ruta">${{p.numero}}</div>`, iconSize:[36,36], iconAnchor:[18,18]}});
  L.marker([p.lat,p.lon], {{icon:icono}}).addTo(mapa)
    .bindPopup(`<strong>${{p.numero}}. ${{p.ciudad}}</strong><br>${{p.noches}} noches<br>${{p.hotel}}`)
    .bindTooltip(p.ciudad, {{permanent:true, direction:'right', offset:[14,0]}});
}});
mapa.fitBounds(coordenadas, {{padding:[55,55]}});
</script>
</body></html>"""
    destino.write_text(contenido, encoding="utf-8")


def resolver(datos: dict, objetivo: str | None = None, presupuesto: float | None = None) -> dict:
    ciudades = datos["ciudades"]
    ids = [c["id"] for c in ciudades]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Las ciudades deben tener identificadores únicos")
    ciudad_por_id = {c["id"]: c for c in ciudades}
    D = int(datos["noches"])
    if D < 1:
        raise ValueError("El viaje debe incluir al menos una noche")
    inicio = date.fromisoformat(datos["fecha_primera_noche"])
    dias = [inicio + timedelta(days=d) for d in range(D)]
    objetivo = objetivo or datos.get("objetivo", "costo")
    if objetivo not in ("costo", "tiempo"):
        raise ValueError("Objetivo debe ser costo o tiempo")
    presupuesto = presupuesto if presupuesto is not None else datos.get("presupuesto_maximo")
    if objetivo == "tiempo" and presupuesto is None:
        raise ValueError("Para minimizar tiempo, indica presupuesto_maximo")

    # Cada variable contiene metadatos para reconstruir una solución legible.
    vars_ = []
    por_clave = {}
    def agregar(clave, tipo, costo, horas=0, **campos):
        pos = len(vars_)
        item = dict(tipo=tipo, costo=float(costo), horas=float(horas), **campos)
        if item["horas"] < 0 or not math.isfinite(item["horas"]):
            raise ValueError(f"Horas inválidas: {campos}")
        vars_.append(item)
        por_clave[clave] = pos
        return pos

    x = defaultdict(list)  # (día, ciudad) -> alojamientos
    for d, dia in enumerate(dias):
        for c in ciudades:
            for h in c["hoteles"]:
                p = precio(h, dia)
                if p is not None:
                    k = agregar(("x", d, c["id"], h["id"]), "hotel", p,
                                dia=d, ciudad=c["id"], hotel=h["id"])
                    x[d, c["id"]].append(k)

    a = defaultdict(list)  # (día de llegada, origen, destino) -> modos
    for d in range(1, D):
        for c in ids:
            k = agregar(("a", d, c, c, "estancia"), "estancia", 0,
                        dia=d, desde=c, hasta=c, medio="estancia")
            a[d, c, c].append(k)
        for t in datos["traslados"]:
            i, j = t["desde"], t["hasta"]
            if i not in ciudad_por_id or j not in ciudad_por_id or i == j:
                raise ValueError(f"Traslado inválido: {t['id']}")
            p = precio(t, dias[d])
            if p is not None:
                k = agregar(("a", d, i, j, t["id"]), "traslado", p,
                            t["horas"], dia=d, desde=i, hasta=j, medio=t["medio"], opcion=t["id"])
                a[d, i, j].append(k)

    b, e = defaultdict(list), defaultdict(list)
    for vuelo in datos["vuelos_internacionales"]:
        c, tipo = vuelo["ciudad"], vuelo["tipo"]
        if c not in ciudad_por_id or tipo not in ("ida", "vuelta"):
            raise ValueError(f"Vuelo inválido: {vuelo['id']}")
        dia = dias[0] if tipo == "ida" else dias[-1] + timedelta(days=1)
        p = precio(vuelo, dia)
        if p is not None:
            k = agregar((tipo, vuelo["id"]), tipo, p, vuelo["horas"],
                        ciudad=c, opcion=vuelo["id"], fecha=dia.isoformat())
            (b if tipo == "ida" else e)[c].append(k)
    y = {c: agregar(("y", c), "visita", 0, ciudad=c) for c in ids}
    w = {}  # Se fija un mismo hotel durante todas las noches en cada ciudad.
    for c in ciudades:
        hoteles = [h["id"] for h in c["hoteles"]]
        if len(hoteles) != len(set(hoteles)) or not hoteles:
            raise ValueError(f"Hoteles repetidos o ausentes en {c['id']}")
        for h in hoteles:
            w[c["id"], h] = agregar(("w", c["id"], h), "hotel_elegido", 0,
                                    ciudad=c["id"], hotel=h)

    filas, columnas, valores, limites_inf, limites_sup = [], [], [], [], []
    def restriccion(terminos, inferior=-np.inf, superior=np.inf):
        fila = len(limites_inf)
        for k, coef in terminos:
            filas.append(fila); columnas.append(k); valores.append(coef)
        limites_inf.append(inferior); limites_sup.append(superior)

    # Una ciudad y un hotel por noche; continuidad temporal de la ruta.
    for d in range(D):
        restriccion(((k, 1) for c in ids for k in x[d, c]), 1, 1)
    restriccion(((k, 1) for opciones in b.values() for k in opciones), 1, 1)
    restriccion(((k, 1) for opciones in e.values() for k in opciones), 1, 1)
    for c in ids:
        restriccion([(k, 1) for k in x[0, c]] + [(k, -1) for k in b[c]], 0, 0)
        restriccion([(k, 1) for k in x[D-1, c]] + [(k, -1) for k in e[c]], 0, 0)
        for d in range(1, D):
            restriccion([(k, 1) for k in x[d-1, c]] +
                        [(k, -1) for j in ids for k in a[d, c, j]], 0, 0)
            restriccion([(k, 1) for k in x[d, c]] +
                        [(k, -1) for i in ids for k in a[d, i, c]], 0, 0)

    for c in ciudades:
        cid = c["id"]
        entradas = [(k, 1) for k in b[cid]] + [
            (k, 1) for d in range(1, D) for i in ids if i != cid for k in a[d, i, cid]
        ]
        restriccion(entradas + [(y[cid], -1)], 0, 0)
        restriccion([(k, 1) for d in range(D) for k in x[d, cid]] +
                    [(y[cid], -int(c["min_noches"]))], 0, np.inf)
        restriccion([(k, 1) for d in range(D) for k in x[d, cid]] +
                    [(y[cid], -int(c["max_noches"]))], -np.inf, 0)
        if int(c["min_noches"]) < 1 or int(c["max_noches"]) < int(c["min_noches"]):
            raise ValueError(f"Rango de noches inválido en {cid}")
        if c.get("obligatoria", False):
            restriccion([(y[cid], 1)], 1, 1)
        restriccion([(w[cid, h["id"]], 1) for h in c["hoteles"]] + [(y[cid], -1)], 0, 0)
        for h in c["hoteles"]:
            for d in range(D):
                k = por_clave.get(("x", d, cid, h["id"]))
                if k is not None:
                    restriccion([(k, 1), (w[cid, h["id"]], -1)], -np.inf, 0)

    if datos.get("min_ciudades") is not None:
        restriccion([(k, 1) for k in y.values()], datos["min_ciudades"], np.inf)
    if datos.get("max_ciudades") is not None:
        restriccion([(k, 1) for k in y.values()], -np.inf, datos["max_ciudades"])
    if presupuesto is not None:
        restriccion([(k, v["costo"]) for k, v in enumerate(vars_) if v["costo"]],
                    -np.inf, float(presupuesto))
    if datos.get("horas_traslado_maximas") is not None:
        restriccion([(k, v["horas"]) for k, v in enumerate(vars_) if v["horas"]],
                    -np.inf, float(datos["horas_traslado_maximas"]))

    matriz = coo_matrix((valores, (filas, columnas)),
                        shape=(len(limites_inf), len(vars_))).tocsr()
    costos = np.array([v["costo"] for v in vars_])
    horas = np.array([v["horas"] for v in vars_])
    def optimizar(pesos, extra=()):
        restricciones = [LinearConstraint(matriz, limites_inf, limites_sup), *extra]
        return milp(pesos, integrality=np.ones(len(vars_)), bounds=Bounds(0, 1),
                    constraints=restricciones, options={"time_limit": 60, "mip_rel_gap": 0.0001})

    resultado = optimizar(costos if objetivo == "costo" else horas)
    if resultado.x is None:
        raise RuntimeError(f"No se encontró una ruta factible u óptima: {resultado.message}")
    if objetivo == "tiempo" and resultado.status == 0:
        # Desempate lexicográfico: el menor costo entre todas las rutas de tiempo mínimo.
        tiempo_optimo = float(horas @ (resultado.x > .5))
        desempate = optimizar(costos, [LinearConstraint(horas, -np.inf, tiempo_optimo + 1e-6)])
        if desempate.x is not None:
            resultado = desempate
    seleccion = [v for k, v in enumerate(vars_) if resultado.x[k] > .5]
    noches = []
    for d, dia in enumerate(dias):
        hotel = next(v for v in seleccion if v["tipo"] == "hotel" and v["dia"] == d)
        noches.append({"fecha": dia.isoformat(), "ciudad": hotel["ciudad"],
                       "hotel": hotel["hotel"], "precio": hotel["costo"]})
    vuelos = [v for v in seleccion if v["tipo"] in ("ida", "vuelta")]
    traslados = sorted([v for v in seleccion if v["tipo"] == "traslado"], key=lambda v: v["dia"])
    estancias = construir_estancias(noches)
    return {
        "estado": "óptimo" if resultado.status == 0 else resultado.message,
        "objetivo": objetivo, "origen": datos["origen"], "noches": noches,
        "ruta_ciudades": [e["ciudad"] for e in estancias], "estancias": estancias,
        "vuelos": vuelos, "traslados": [dict(fecha=dias[v["dia"]].isoformat(), **v) for v in traslados],
        "costo_alojamiento": round(sum(v["costo"] for v in seleccion if v["tipo"] == "hotel"), 2),
        "costo_transporte": round(sum(v["costo"] for v in seleccion if v["tipo"] in ("ida", "vuelta", "traslado")), 2),
        "costo_total": round(sum(v["costo"] for v in seleccion), 2),
        "horas_traslado": round(sum(v["horas"] for v in seleccion), 2),
    }


def main():
    p = argparse.ArgumentParser(description="Optimiza ciudades, noches, hoteles y transportes")
    p.add_argument("datos", type=Path)
    p.add_argument("--objetivo", choices=["costo", "tiempo"])
    p.add_argument("--presupuesto", type=float)
    p.add_argument("--salida", type=Path)
    p.add_argument("--mapa", type=Path, help="guarda un mapa interactivo de la ruta en HTML")
    args = p.parse_args()
    try:
        datos = json.loads(args.datos.read_text(encoding="utf-8"))
        respuesta = resolver(datos, args.objetivo, args.presupuesto)
        if args.mapa:
            guardar_mapa(respuesta, datos, args.mapa)
    except (ValueError, KeyError, RuntimeError) as exc:
        p.exit(2, f"Error: {exc}\n")
    print(f"Estado: {respuesta['estado']}")
    print(f"Costo total: {respuesta['costo_total']:.2f} "
          f"(alojamiento {respuesta['costo_alojamiento']:.2f}; transporte {respuesta['costo_transporte']:.2f})")
    print(f"Horas de traslado: {respuesta['horas_traslado']:.1f}")
    print("Ruta: " + " → ".join(
        [respuesta["origen"], *respuesta["ruta_ciudades"], respuesta["origen"]]))
    for v in respuesta["vuelos"]:
        print(f"{v['tipo'].capitalize()}: {v['opcion']} ({v['fecha']})")
    for n in respuesta["noches"]:
        print(f"{n['fecha']}: {n['ciudad']} — {n['hotel']} ({n['precio']:.2f})")
        for t in respuesta["traslados"]:
            if t["fecha"] == n["fecha"]:
                print(f"  Traslado: {t['desde']} → {t['hasta']} en {t['medio']}, {t['costo']:.2f}")
    if args.salida:
        args.salida.write_text(json.dumps(respuesta, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.mapa:
        print(f"Mapa: {args.mapa}")


if __name__ == "__main__":
    main()
