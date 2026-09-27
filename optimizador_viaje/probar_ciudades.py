"""Pruebas manuales de seleccion de ciudades y rangos de noches."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from optimizar import resolver


def mostrar(nombre: str, datos: dict) -> None:
    print(f"\n--- {nombre} ---")
    try:
        resultado = resolver(datos)
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return

    noches = Counter(noche["ciudad"] for noche in resultado["noches"])
    print(f"Ciudades/noches: {dict(noches)}")
    print(f"Costo: {resultado['costo_total']:.2f}")
    print(f"Horas: {resultado['horas_traslado']:.1f}")


base = json.loads(Path("ejemplo.json").read_text(encoding="utf-8"))

mostrar("Caso actual", deepcopy(base))

datos = deepcopy(base)
next(c for c in datos["ciudades"] if c["id"] == "Madrid")["obligatoria"] = True
mostrar("Madrid obligatoria", datos)

datos = deepcopy(base)
for hotel in next(c for c in datos["ciudades"] if c["id"] == "Madrid")["hoteles"]:
    hotel["precio"]["base"] = 1000
mostrar("Madrid cara y opcional", datos)

datos = deepcopy(datos)
next(c for c in datos["ciudades"] if c["id"] == "Madrid")["obligatoria"] = True
mostrar("Madrid cara pero obligatoria", datos)

datos = deepcopy(base)
madrid = next(c for c in datos["ciudades"] if c["id"] == "Madrid")
madrid["min_noches"] = 1
madrid["max_noches"] = 1
mostrar("Madrid con exactamente una noche si se visita", datos)

datos = deepcopy(base)
datos["noches"] = 3
mostrar("Caso imposible: solo tres noches", datos)
