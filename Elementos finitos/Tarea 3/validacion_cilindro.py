import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import spsolve

# Leer solo las funciones generales del notebook para validar el codigo actual.
ruta = Path(__file__).with_name("Tarea_3.ipynb")
with ruta.open(encoding="utf-8") as archivo:
    notebook = json.load(archivo)

for celda in notebook["cells"]:
    codigo = "".join(celda["source"])
    if celda["cell_type"] == "code" and "def funciones_forma(" in codigo:
        exec(compile(codigo, str(ruta), "exec"))
        break
else:
    raise ValueError("No se encontro la celda de funciones generales.")

E = 210000  # MPa
nu = 0.3
radio = 10  # mm
L = 100  # mm
sigma_0 = 100  # MPa
P = sigma_0*np.pi*radio**2

coordenadas = np.array([[0, 0], [radio, 0], [0, L], [radio, L]])
conectividad = np.array([[0, 1, 3], [0, 3, 2]])
F = np.zeros(2*len(coordenadas))
F[5] = P/3
F[7] = 2*P/3
gdl_restringidos = [0, 4, 1, 3]

K = ensamblar_rigidez_global(coordenadas, conectividad, E, nu)
U, R = resolver_sistema(K, F, gdl_restringidos)
D = matriz_constitutiva(E, nu)
puntos = [[1/6, 1/6], [2/3, 1/6], [1/6, 2/3]]
tensiones = np.zeros((len(conectividad), len(puntos), 4))
sigma_vm = np.zeros((len(conectividad), len(puntos)))

for e in range(len(conectividad)):
    nodos = conectividad[e]
    gdl = gdl_elemento(nodos)
    tensiones[e] = calcular_tensiones(coordenadas[nodos], U[gdl], D, puntos)
    for k in range(len(puntos)):
        sigma_vm[e, k] = von_mises(tensiones[e, k])

U_analitico = np.zeros(len(U))
for i in range(len(coordenadas)):
    r, z = coordenadas[i]
    U_analitico[2*i] = -nu*sigma_0*r/E
    U_analitico[2*i+1] = sigma_0*z/E

sigma_analitica = np.array([0, sigma_0, 0, 0])
error_U = np.max(np.abs(U-U_analitico))
error_sigma = np.max(np.abs(tensiones-sigma_analitica))
error_vm = np.max(np.abs(sigma_vm-sigma_0))
error_simetria = abs(K-K.T).max()/abs(K).max()
reaccion_axial = R[1]+R[3]
error_equilibrio = abs(reaccion_axial+P)/P
Kt = np.max(sigma_vm)/sigma_0

print("Nodo      ur MEF       ur analitico       uz MEF       uz analitico [mm]")
for i in range(len(coordenadas)):
    print(f"{i:4d} {U[2*i]:13.6e} {U_analitico[2*i]:17.6e} {U[2*i+1]:13.6e} {U_analitico[2*i+1]:17.6e}")
print("\nTensiones [rr, zz, tt, rz] en el primer punto de cada elemento [MPa]:")
for e in range(len(conectividad)):
    print(f"Elemento {e}: {tensiones[e, 0]}")
print(f"\nError maximo de desplazamientos: {error_U:.3e} mm")
print(f"Error maximo de tensiones: {error_sigma:.3e} MPa")
print(f"Error maximo de Von Mises: {error_vm:.3e} MPa")
print(f"Error relativo de simetria de K: {error_simetria:.3e}")
print(f"Carga aplicada: {P:.6f} N")
print(f"Reaccion axial: {reaccion_axial:.6f} N")
print(f"Error relativo de equilibrio axial: {error_equilibrio:.3e}")
print(f"Kt del cilindro uniforme: {Kt:.6f}")

assert np.allclose(U, U_analitico, rtol=1e-8, atol=1e-10)
assert np.allclose(tensiones, sigma_analitica, rtol=1e-8, atol=1e-8)
assert np.allclose(sigma_vm, sigma_0, rtol=1e-8, atol=1e-8)
assert error_simetria < 1e-10
assert error_equilibrio < 1e-10
print("Prueba del cilindro uniforme: correcta.")
