"""Ejecuta 5C sin regenerar ni sobrescribir los resultados de 5A/5B."""

import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from transmision.calculos import resolver
from transmision.tensado import resolver_5c, FUENTE_5C


def ejecutar(parametros=RAIZ/"parametros.json", salida=RAIZ/"resultados/etapa_5c"):
    p = json.loads(Path(parametros).read_text(encoding="utf-8"))
    historico = RAIZ/"resultados/resumen.json"
    h = json.loads(historico.read_text(encoding="utf-8"))
    archivos = sorted((RAIZ/"resultados").glob("*.*"))
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in archivos if f.is_file()}
    recalculado = resolver(p)
    validaciones = [{"validacion": f"conservacion_{etapa}", "cumple": recalculado[etapa] == h[etapa]}
                    for etapa in ("etapa_5a", "etapa_5b")]
    if not all(v["cumple"] for v in validaciones):
        raise ValueError("Los parámetros no reproducen el histórico 5A/5B; usar otra línea base explícita")
    r = resolver_5c(p)
    validaciones.append({"validacion": "geometria_nominal_reutilizada", "cumple": all(
        r["geometria_nominal"][k] == h["etapa_5a"][k] for k in r["geometria_nominal"])})
    salida = Path(salida).resolve()
    # Evitar sobrescribir una carpeta de resultados previa por error de CLI.
    if salida == (RAIZ/"resultados").resolve() or salida in historico.resolve().parents:
        raise ValueError("La salida 5C debe ser una carpeta separada del histórico")
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"poleas_y_gargantas.csv", r["poleas"])
    guardar_csv(salida/"ajuste_centros.csv", [{**r["recorridos"], **r["ajuste_centros"]}])
    guardar_csv(salida/"geometria_nominal.csv", [r["geometria_nominal"]])
    conservados = all(hashlib.sha256((RAIZ/"resultados"/n).read_bytes()).hexdigest() == valor for n, valor in hashes.items())
    validaciones.append({"validacion": "archivos_5a_5b_sin_cambios_sha256", "cumple": conservados})
    guardar_csv(salida/"validaciones.csv", validaciones)
    if not all(v["cumple"] for v in validaciones):
        raise RuntimeError("No se conservó la línea base 5A/5B")
    for nombre, contenido in (("resumen", r), ("parametros_utilizados", p),
                              ("fuentes_y_trazabilidad", {**FUENTE_5C, "sha256_historicos": hashes})):
        (salida/f"{nombre}.json").write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")
    return r


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parametros", type=Path, default=RAIZ/"parametros.json")
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados/etapa_5c")
    args = parser.parse_args()
    print(json.dumps(ejecutar(args.parametros, args.salida), indent=2, ensure_ascii=False))
