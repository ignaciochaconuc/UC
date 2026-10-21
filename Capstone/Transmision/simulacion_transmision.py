"""Genera únicamente resultados 5A/5B; lee el resumen 3C sin recalcularlo."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from transmision.calculos import balance_motor, dimensionar, resolver, capacidad_corregida
from transmision.catalogo import FUENTE

RAIZ = Path(__file__).resolve().parent


def guardar_csv(ruta, filas):
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def ejecutar(parametros=RAIZ/"parametros.json", salida=RAIZ/"resultados"):
    p = json.loads(Path(parametros).read_text(encoding="utf-8"))
    r = resolver(p)
    entrada = RAIZ.parent/"Simulación_peletizadora/resultados/etapa_3c_acoplamiento/resumen_comparativo.csv"
    huella = hashlib.sha256(entrada.read_bytes()).hexdigest()
    with entrada.open(encoding="utf-8") as archivo:
        referencia = next(fila for fila in csv.DictReader(archivo) if fila["modelo"] == "inclinacion")
    contrastes = []
    for nombre, columna, escala, tolerancia in (
        ("potencia_max_kw", "potencia_max_w", .001, .001),
        ("potencia_media_kw", "potencia_media_w", .001, .001),
        ("torque_max_nm", "torque_max_nm", 1., .001),
    ):
        original = float(referencia[columna])*escala
        declarado = p["cargas_3c"][nombre]
        contrastes.append({"magnitud": nombre, "declarado": declarado, "original_3c": original,
                           "error_absoluto": abs(original-declarado), "coincide_redondeo": abs(original-declarado) <= tolerancia})
    if not all(fila["coincide_redondeo"] for fila in contrastes):
        raise ValueError("Los parámetros resistentes difieren del resumen 3C; revisar versión de entrada")
    b = r["etapa_5b"]
    sensibilidad = [{"factor_servicio": fs, **dimensionar(p["potencia_motor_kw"], fs,
                    b["capacidad_correa_kw"], p["numero_correas"])} for fs in p["factores_servicio_sensibilidad"]]
    balances = [balance_motor(p["potencia_motor_kw"], e, p["cargas_3c"]["potencia_max_kw"],
                p["cargas_3c"]["potencia_media_kw"]) for e in p["eficiencias_supuestas"]]
    capacidad_contraste = capacidad_corregida(b["basica_kw"], b["adicional_relacion_kw"], 0., .947, b["factor_longitud"])
    r["contraste_factor_0947_no_adoptado"] = dimensionar(p["potencia_motor_kw"], p["factor_servicio"], capacidad_contraste, p["numero_correas"])
    r["advertencias"] = [
        "Diámetros 100/280 mm supuestos de referencia; confirmar si son exteriores.",
        "8 h/día y FS=1,3 preliminares; clasificación de máquina y arranques por validar.",
        "Base de catálogo 12000 h con adicional de vida cero; no es vida garantizada ni requisito de proyecto.",
        "Se usa G conservador sin interpolar; G=0,947 es solo contraste aportado, excluido de la decisión.",
        "Salida 517,86 rpm; las cargas heredadas siguen correspondiendo a 516 rpm.",
        "Pendientes: correa comercial exacta DIN 7753, equivalencia con Gates, ramales, fuerzas en ejes y tensado.",
    ]
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"geometria_5a.csv", [r["etapa_5a"]])
    guardar_csv(salida/"capacidad_5b.csv", [b])
    guardar_csv(salida/"sensibilidad_factor_servicio.csv", sensibilidad)
    guardar_csv(salida/"balance_motor_eficiencias.csv", balances)
    guardar_csv(salida/"contraste_3c.csv", contrastes)
    (salida/"resumen.json").write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    (salida/"parametros_utilizados.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    fuente = {**FUENTE, "resumen_3c": str(entrada.relative_to(RAIZ.parent)), "sha256_3c": huella,
              "sha256_3c_conservado": hashlib.sha256(entrada.read_bytes()).hexdigest() == huella}
    (salida/"fuentes_y_validacion.json").write_text(json.dumps(fuente, indent=2, ensure_ascii=False), encoding="utf-8")
    return r


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parametros", type=Path, default=RAIZ/"parametros.json")
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados")
    args = parser.parse_args()
    print(json.dumps(ejecutar(args.parametros, args.salida), indent=2, ensure_ascii=False))
