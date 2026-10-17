"""Elemento finito de viga Euler–Bernoulli en un plano de flexión."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import splu

from .config_eje import ConfiguracionEje
from .geometria_eje import propiedades_elementos


def rigidez_elemento(E: float, I: float, L: float) -> np.ndarray:
    return E * I / L**3 * np.array(
        [
            [12, 6 * L, -12, 6 * L],
            [6 * L, 4 * L**2, -6 * L, 2 * L**2],
            [-12, -6 * L, 12, -6 * L],
            [6 * L, 2 * L**2, -6 * L, 4 * L**2],
        ],
        dtype=float,
    )


def carga_uniforme_consistente(q_n_m: float, L: float) -> np.ndarray:
    return q_n_m * np.array([L / 2, L**2 / 12, L / 2, -L**2 / 12])


@dataclass
class SolucionViga:
    desplazamientos: np.ndarray
    reacciones: np.ndarray
    cargas: np.ndarray


class SistemaViga:
    def __init__(self, nodos_m: np.ndarray, config: ConfiguracionEje):
        self.nodos_m = np.asarray(nodos_m, dtype=float)
        self.config = config
        self.longitudes = np.diff(self.nodos_m)
        if np.any(self.longitudes <= 0):
            raise ValueError("Los nodos deben ser estrictamente crecientes")
        self.areas, self.inercias, self.radios, self.nombres_segmentos = propiedades_elementos(
            self.nodos_m, config.segmentos
        )
        self.numero_nodos = len(self.nodos_m)
        self.numero_gdl = 2 * self.numero_nodos
        self.rigideces_elementos = [
            rigidez_elemento(config.modulo_young_pa, I, L)
            for I, L in zip(self.inercias, self.longitudes, strict=True)
        ]
        self.K = self._ensamblar_rigidez()
        self.restringidos = np.array([0, 1, self.numero_gdl - 2, self.numero_gdl - 1])
        self.libres = np.setdiff1d(np.arange(self.numero_gdl), self.restringidos)
        self._factor = splu(self.K[self.libres][:, self.libres].tocsc())

    def _ensamblar_rigidez(self) -> csr_matrix:
        filas: list[int] = []
        columnas: list[int] = []
        valores: list[float] = []
        for e, ke in enumerate(self.rigideces_elementos):
            gdl = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            for i, gi in enumerate(gdl):
                for j, gj in enumerate(gdl):
                    filas.append(gi)
                    columnas.append(gj)
                    valores.append(ke[i, j])
        return coo_matrix((valores, (filas, columnas)), shape=(self.numero_gdl, self.numero_gdl)).tocsr()

    def cargas_vacias(self, numero_casos: int = 1) -> np.ndarray:
        return np.zeros((self.numero_gdl, numero_casos))

    def indice_nodo(self, x_m: float, tolerancia: float = 1e-10) -> int:
        indice = int(np.argmin(np.abs(self.nodos_m - x_m)))
        if abs(self.nodos_m[indice] - x_m) > tolerancia:
            raise ValueError(f"No existe nodo en x={x_m:.12g} m")
        return indice

    def agregar_carga_puntual(self, cargas: np.ndarray, x_m: float, valores_n) -> None:
        indice = self.indice_nodo(x_m)
        cargas[2 * indice, :] += np.asarray(valores_n)

    def agregar_peso_propio(self, cargas: np.ndarray) -> np.ndarray:
        equivalentes = np.zeros((len(self.longitudes), 4))
        for e, (area, L) in enumerate(zip(self.areas, self.longitudes, strict=True)):
            q = -self.config.densidad_eje_kg_m3 * self.config.gravedad_m_s2 * area
            fe = carga_uniforme_consistente(q, L)
            equivalentes[e] = fe
            gdl = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            cargas[gdl, :] += fe[:, None]
        return equivalentes

    def resolver(self, cargas: np.ndarray) -> SolucionViga:
        if cargas.ndim == 1:
            cargas = cargas[:, None]
        desplazamientos = np.zeros_like(cargas)
        desplazamientos[self.libres, :] = self._factor.solve(cargas[self.libres, :])
        reacciones = self.K @ desplazamientos - cargas
        return SolucionViga(desplazamientos, reacciones, cargas)

    def fuerzas_extremo_elementos(
        self,
        desplazamientos: np.ndarray,
        cargas_distribuidas_elemento: np.ndarray | None = None,
    ) -> np.ndarray:
        """Retorna [V_i, M_i, V_j, M_j] por elemento y caso."""
        if desplazamientos.ndim == 1:
            desplazamientos = desplazamientos[:, None]
        numero_casos = desplazamientos.shape[1]
        resultado = np.zeros((len(self.longitudes), 4, numero_casos))
        for e, ke in enumerate(self.rigideces_elementos):
            gdl = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            resultado[e] = ke @ desplazamientos[gdl, :]
            if cargas_distribuidas_elemento is not None:
                resultado[e] -= cargas_distribuidas_elemento[e, :, None]
        return resultado
