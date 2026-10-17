# Resultados de las cuatro simulaciones

Estadísticas ponderadas por tiempo entre 200 y 400 s (paso adaptativo). La frecuencia se calcula con cruces ascendentes de Cl respecto de su media; se contrasta con FFT sobre una señal interpolada uniformemente.

| Re | Modelo | Cd medio | Cl medio | Cl RMS | f [Hz] | St | Cambio Cd [%] | Cambio Cl RMS [%] |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | Laminar 2D | 1.69305 | -0.00155 | 0.29025 | 0.09920 | 0.1984 | 0.004 | 0.380 |
| 1000 | Laminar 2D | 1.71365 | -0.00167 | 1.16338 | 0.12625 | 0.2525 | 0.093 | 0.407 |
| 10000 | URANS SST 2D | 1.50238 | -0.00866 | 1.10475 | 0.11637 | 0.2327 | 0.140 | 0.842 |
| 100000 | URANS SST 2D | 0.93676 | 0.00016 | 0.35729 | 0.12706 | 0.2541 | 0.025 | 0.173 |

Los cambios comparan ventanas 200–300 y 300–400 s; no son estimaciones del error físico ni pruebas de independencia de malla. La media de Cl puede no ser exactamente cero por usar ventanas con ciclos incompletos.

Re1000 es laminar 2D: no resuelve la transición tridimensional real. Los casos SST son URANS 2D y no resuelven las estructuras turbulentas 3D. El cilindro está confinado en un canal con D/H=0.1, paredes no deslizantes y entrada uniforme; no comparar directamente con un cilindro no confinado.

La menor Cd obtenida a Re100000 no demuestra una crisis de arrastre: revisar sensibilidad a SST, malla y tratamiento de pared antes de atribuirle un mecanismo físico.

Pendientes: sensibilidad espacial y temporal, y+ desarrollado, balance de caudal y longitud de recirculación del campo medio. Las imágenes instantáneas no representan el campo medio.

## Balance de caudal a t=400 s

- Re=100: caudales orientados de entrada/salida -2 / 2 m³/s; desequilibrio relativo 0.000e+00 (a la precisión de salida).
- Re=1000: caudales orientados de entrada/salida -2 / 2 m³/s; desequilibrio relativo 0.000e+00 (a la precisión de salida).
- Re=10000: caudales orientados de entrada/salida -2 / 2 m³/s; desequilibrio relativo 0.000e+00 (a la precisión de salida).
- Re=100000: caudales orientados de entrada/salida -2 / 2 m³/s; desequilibrio relativo 0.000e+00 (a la precisión de salida).

## y+ a t=400 s

| Re | Superficie | Mínimo | Máximo | Promedio |
|---:|---|---:|---:|---:|
| 10000 | walls | 28.332 | 43.637 | 31.306 |
| 10000 | cylinder | 0.052 | 2.951 | 1.459 |
| 100000 | walls | 231.753 | 318.193 | 252.558 |
| 100000 | cylinder | 0.989 | 18.009 | 8.584 |

Estos y+ son instantáneos. El cilindro a Re100000 alcanza y+≈18: comprobar sensibilidad del tratamiento de pared y de las capas antes de presentar sus fuerzas como validadas.
