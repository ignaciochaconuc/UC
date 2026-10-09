"""Barrido geométrico y carga equivalente de dos rodillos sobre una matriz.

Dependencias: pip install ezdxf numpy
Ejecutar junto al archivo cara_matriz.dxf.
Distribución de presión TRIANGULAR: hipótesis de ingeniería, NO ley validada.
Las perforaciones se consideran activas por la posición de sus centros.
"""
from pathlib import Path
import numpy as np
import ezdxf

DXF = Path(__file__).with_name('cara_matriz.dxf')
R_RODILLO = 49.0  # mm
ANCHO = 50.4  # mm
R_CENTRO = 68.7  # mm, desde centro de matriz
HOLGURA = 0.4  # mm
H_INICIAL = 4.0  # mm, hipótesis de Entrega 1
P_MAX = 44.0  # N/mm², equivalente extrusión, no presión de contacto medida
D_AGUJERO = 6.0  # mm, garganta efectiva (DXF representa Ø9 avellanado)
PASO_GRADOS = 0.05

modelo = ezdxf.readfile(DXF)
centros = np.array([
    [ent.dxf.center.x, ent.dxf.center.y]
    for ent in modelo.modelspace()
    if ent.dxftype() == 'CIRCLE' and np.isclose(ent.dxf.radius, 4.5)
])
assert len(centros) == 102, 'Se esperaban 102 avellanados de Ø9 mm.'
Lc = np.sqrt(2 * R_RODILLO * (H_INICIAL - HOLGURA) - (H_INICIAL - HOLGURA)**2)
A = np.pi * D_AGUJERO**2 / 4
F_POR_AGUJERO_MAX = P_MAX * A
angulos = np.deg2rad(np.arange(0, 360, PASO_GRADOS))

def barrido(offset):
    a = angulos + offset
    er = np.stack((np.cos(a), np.sin(a)), axis=1)
    et = np.stack((-np.sin(a), np.cos(a)), axis=1)
    radial = er @ centros.T
    tangencial = et @ centros.T
    activos = ((radial >= R_CENTRO - ANCHO/2) &
               (radial <= R_CENTRO + ANCHO/2) &
               (tangencial >= -Lc) & (tangencial <= 0))
    pesos = np.where(activos, (tangencial + Lc)/Lc, 0.0)
    fuerza = F_POR_AGUJERO_MAX * pesos.sum(axis=1)
    return activos.sum(axis=1), fuerza, pesos, radial

n1, f1, w1, r1 = barrido(0.0)
n2, f2, w2, r2 = barrido(np.pi)
imax = np.argmax(f1)
itotal = np.argmax(f1 + f2)
r_eq = np.sum(w1[imax] * r1[imax]) / np.sum(w1[imax])
print(f'Perforaciones DXF: {len(centros)}')
print(f'Longitud geométrica de compresión: {Lc:.3f} mm')
print(f'Fuerza máxima por perforación: {F_POR_AGUJERO_MAX:.3f} N')
print(f'Perforaciones activas: min {n1.min()}, media {n1.mean():.3f}, max {n1.max()}')
print(f'Fuerza media por rodillo: {f1.mean()/1000:.3f} kN')
print(f'Fuerza máxima por rodillo: {f1[imax]/1000:.3f} kN, ángulo {np.rad2deg(angulos[imax]):.2f}°')
print(f'Perforaciones en máximo de fuerza: {n1[imax]}')
print(f'Radio equivalente en máximo: {r_eq:.3f} mm')
print(f'Máxima suma simultánea: {(f1+f2)[itotal]/1000:.3f} kN')
