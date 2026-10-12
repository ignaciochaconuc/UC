"""Carga, generación y validación de la geometría de perforaciones."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv
import math

import numpy as np

from config import Parametros


def cargar_agujeros_csv(ruta: Path) -> np.ndarray:
    """Lee columnas ``x_mm`` e ``y_mm`` y retorna coordenadas SI (m)."""
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    try:
        return np.array(
            [[float(f["x_mm"]), float(f["y_mm"])] for f in filas], dtype=float
        ) / 1_000.0
    except (KeyError, ValueError) as error:
        raise ValueError(f"CSV inválido en {ruta}: se requieren x_mm e y_mm") from error


def guardar_agujeros_csv(coordenadas_m: np.ndarray, ruta: Path, fuente: str) -> None:
    """Guarda centros en milímetros, con un identificador estable."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["id", "x_mm", "y_mm", "fuente"])
        for indice, (x_m, y_m) in enumerate(coordenadas_m, start=1):
            escritor.writerow(
                [indice, f"{x_m * 1_000:.6f}", f"{y_m * 1_000:.6f}", fuente]
            )


def _entidades_circulo_dxf(ruta: Path) -> list[tuple[float, float, float]]:
    """Extrae CIRCLE de un DXF ASCII sin agregar una dependencia CAD."""
    lineas = ruta.read_text(encoding="cp1252", errors="replace").splitlines()
    if len(lineas) % 2:
        raise ValueError("El DXF no contiene pares código/valor completos")
    pares = [(lineas[i].strip(), lineas[i + 1].strip()) for i in range(0, len(lineas), 2)]
    en_entidades = False
    tipo: str | None = None
    datos: list[tuple[str, str]] = []
    circulos: list[tuple[float, float, float]] = []

    def terminar_entidad() -> None:
        if tipo != "CIRCLE":
            return
        grupos = {codigo: valor for codigo, valor in datos}
        try:
            circulos.append(
                (float(grupos["10"]), float(grupos["20"]), float(grupos["40"]))
            )
        except KeyError as error:
            raise ValueError("Entidad CIRCLE incompleta en el DXF") from error

    for codigo, valor in pares:
        if codigo == "2" and valor == "ENTITIES":
            en_entidades = True
            continue
        if not en_entidades:
            continue
        if codigo == "0" and valor == "ENDSEC":
            terminar_entidad()
            break
        if codigo == "0":
            terminar_entidad()
            tipo, datos = valor, []
        else:
            datos.append((codigo, valor))
    return circulos


def cargar_agujeros_dxf(ruta: Path, cantidad_esperada: int = 102) -> np.ndarray:
    """Obtiene los centros del grupo repetido de 102 círculos del DXF.

    En el archivo suministrado esos círculos son la boca de Ø9 mm; el modelo
    usa sus centros y conserva el diámetro efectivo de paso de Ø6 mm.
    """
    circulos = _entidades_circulo_dxf(ruta)
    conteos = Counter(round(radio, 6) for _, _, radio in circulos)
    radios_candidatos = [radio for radio, n in conteos.items() if n == cantidad_esperada]
    if len(radios_candidatos) != 1:
        raise ValueError(
            f"No se identificó un grupo único de {cantidad_esperada} círculos en {ruta}"
        )
    radio_objetivo = radios_candidatos[0]
    centros_mm = [
        (x, y) for x, y, radio in circulos if round(radio, 6) == radio_objetivo
    ]
    return np.asarray(centros_mm, dtype=float) / 1_000.0


def generar_geometria_provisional(parametros: Parametros) -> np.ndarray:
    """Respaldo determinista de 102 centros en cuatro anillos; no representa el CAD."""
    cantidades = (22, 25, 27, 28)
    radios = np.linspace(0.048, 0.077, len(cantidades))
    puntos: list[tuple[float, float]] = []
    for anillo, (radio, cantidad) in enumerate(zip(radios, cantidades, strict=True)):
        desfase = (anillo % 2) * math.pi / cantidad
        for angulo in np.linspace(0.0, 2.0 * math.pi, cantidad, endpoint=False) + desfase:
            puntos.append((radio * math.cos(angulo), radio * math.sin(angulo)))
    return np.asarray(puntos)


def validar_geometria(coordenadas_m: np.ndarray, parametros: Parametros) -> dict[str, float]:
    """Valida cantidad, anillo de centros y ausencia de superposiciones."""
    if coordenadas_m.shape != (parametros.numero_agujeros, 2):
        raise ValueError(
            f"Se esperaban {parametros.numero_agujeros} centros y se obtuvo "
            f"{coordenadas_m.shape}"
        )
    radios = np.linalg.norm(coordenadas_m, axis=1)
    tolerancia = 1e-9
    if np.any(radios < parametros.radio_util_interior_m - tolerancia):
        raise ValueError("Hay centros bajo el radio útil interior")
    if np.any(radios > parametros.radio_util_exterior_m + tolerancia):
        raise ValueError("Hay centros sobre el radio útil exterior")
    diferencias = coordenadas_m[:, None, :] - coordenadas_m[None, :, :]
    distancias = np.linalg.norm(diferencias, axis=2)
    np.fill_diagonal(distancias, np.inf)
    separacion_minima = float(np.min(distancias))
    if separacion_minima < parametros.diametro_agujero_m - tolerancia:
        raise ValueError("Existen perforaciones superpuestas")
    return {
        "radio_minimo_m": float(np.min(radios)),
        "radio_maximo_m": float(np.max(radios)),
        "separacion_minima_m": separacion_minima,
    }
