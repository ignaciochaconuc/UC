"""Ejecuta 5D.1; conserva los archivos históricos 5A/5B/5C por SHA256."""

import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from transmision.tension_estatica import FUENTE_5D1, resolver_5d1, sensibilidad


def archivos_historicos():
    return sorted([f for f in (RAIZ/"resultados").glob("*.*") if f.is_file()]
                  + [f for f in (RAIZ/"resultados/etapa_5c").rglob("*") if f.is_file()])


def ejecutar(parametros=RAIZ/"parametros.json", salida=RAIZ/"resultados/etapa_5d1"):
    salida = Path(salida).resolve()
    protegidos = [(RAIZ/"resultados").resolve(), (RAIZ/"resultados/etapa_5c").resolve()]
    if salida in protegidos or salida in protegidos[0].parents or protegidos[1] in salida.parents:
        raise ValueError("Usar una subcarpeta 5D.1 separada de los históricos")
    archivos = archivos_historicos()
    hashes = {str(f.relative_to(RAIZ)): hashlib.sha256(f.read_bytes()).hexdigest() for f in archivos}
    p = json.loads(Path(parametros).read_text(encoding="utf-8"))
    h = json.loads((RAIZ/"resultados/resumen.json").read_text(encoding="utf-8"))
    c = json.loads((RAIZ/"resultados/etapa_5c/resumen.json").read_text(encoding="utf-8"))
    r = resolver_5d1(p, h["etapa_5b"])
    principal = r["principal"]
    if principal["velocidad_m_s"] != h["etapa_5a"]["velocidad_correa_m_s"] or p["centros_mm"] != c["ajuste_centros"]["centros_nominales_mm"]:
        raise ValueError("Geometría distinta de la línea base histórica")
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"tensado_individual.csv", r["correas_individuales"])
    guardar_csv(salida/"sensibilidad.csv", sensibilidad(p, h["etapa_5b"]))
    validaciones = [{"validacion": "historicos_5a_5b_5c_conservados_sha256", "cumple": all(
        hashlib.sha256((RAIZ/n).read_bytes()).hexdigest() == valor for n, valor in hashes.items())},
        {"validacion": "potencia_accionamiento_5_5_kw", "cumple": principal["potencia_accionamiento_kw"] == 5.5}]
    if not all(v["cumple"] for v in validaciones):
        raise RuntimeError("Falló la validación 5D.1")
    guardar_csv(salida/"validaciones.csv", validaciones)
    for nombre, contenido in (("resumen", r), ("parametros_utilizados", p),
                              ("fuentes_y_trazabilidad", {**FUENTE_5D1, "sha256_historicos": hashes})):
        (salida/f"{nombre}.json").write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")
    return r


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parametros", type=Path, default=RAIZ/"parametros.json")
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados/etapa_5d1")
    args = parser.parse_args()
    print(json.dumps(ejecutar(args.parametros, args.salida), indent=2, ensure_ascii=False))
