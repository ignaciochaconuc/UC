# Contexto para continuar el informe de CFD

## Objetivo

Resolver la pregunta 1 de `CFD/Tarea 2/Tarea2_2_2026.pdf`. Las preguntas 2–7 están en `CFD/Tarea 2/Tarea 2.ipynb`. Redactar el informe con las simulaciones y fotos ya obtenidas.

## Simulaciones realizadas

OpenFOAM Foundation 14, solver `foamRun` / `incompressibleFluid`, transiente PIMPLE, esquema temporal `backward`. Canal 100×20 m; cilindro D=2 m centrado en (6,10) m, interpretando los 5 m del dibujo hasta la superficie del cilindro. Modelo 2D con espesor 0.1 m y caras `empty`. Entrada uniforme U=1 m/s y nu=2/Re; paredes no deslizantes y salida p=0.

Re100 y Re1000: laminar 2D. Re10000 y Re100000: URANS k-omega SST, intensidad de entrada 1%, longitud de mezcla 0.14 m y función de pared Spalding para nut. Re1000 laminar 2D es una simplificación: no afirmar que el flujo físico sea estrictamente laminar y bidimensional.

Malla personalizada: blockMesh → snappyHexMesh → extrudeMesh → createPatch; 40.796 celdas, refinamiento del cilindro, estela y paredes; tres capas en el cilindro. checkMesh pasó. Todos los casos terminaron en t=400 s. Solver de presión optimizado de PCG a GAMG, conservando tolerancias; comparación corta documentada en VALIDACION.txt.

## Archivos principales

- `resultados/RESUMEN.md`: estadísticas y verificaciones.
- `resultados/resumen.csv` y `estadisticas.json`: resultados cuantitativos.
- `resultados/coeficientes_Re*.csv`: series temporales completas de fuerzas, sin tiempos duplicados de reinicios.
- `resultados/fuerzas_*.png`: gráficos de fuerzas.
- `resultados/*openfoam*.png` y `*openfooam*.png`: capturas tomadas por el estudiante en ParaView. Revisar su tiempo, leyenda y componente según la imagen, sin asumir que el nombre es exacto.
- `resultados/Re*_U.png`, `Re*_p.png`, `Re*_vorticity.png`: capturas automáticas comparables de t=400 s; vorticidad es componente Z, no magnitud.
- `Re100/Malla.png`, `Re100/Malla_cilindro.png`: capturas de malla.
- `resultados/verificaciones/`: extractos del fin de ejecución, balance de caudal y y+.
- `README.md`: configuración, ejecución y análisis.

## Método de análisis

Promedios y RMS ponderados por tiempo entre 200 y 400 s, porque el paso es adaptativo. Cl RMS se refiere a fluctuaciones respecto de su media. Frecuencia por cruces ascendentes de Cl respecto de su media, contrastada con FFT; St=fD/U=2f. Comparación de ventanas 200–300 y 300–400 s: variación Cd medio <0.15% y Cl RMS <0.85%. Esto indica consistencia temporal de estas estadísticas; no prueba independencia de malla ni exactitud física.

## Limitaciones que deben constar

No se ejecutó estudio de independencia de malla ni paso temporal. Modelos 2D, con limitaciones importantes para Re alto. y+ a t=400 s: en el cilindro Re10000 promedio 1.46 y máximo 2.95; Re100000 promedio 8.58 y máximo 18.01. El tratamiento de pared a Re100000 requiere sensibilidad adicional. No atribuir la reducción de Cd a una crisis de arrastre sin validación adicional. La longitud de recirculación del campo medio no se calculó.

## Qué se sube y qué queda local

GitHub incluye configuraciones, scripts, fotos, series CSV y análisis. Las mallas generadas, campos completos de los 201 tiempos, logs completos y respaldos están excluidos por tamaño; los campos y la malla pueden regenerarse con los scripts. Para analizar las fuerzas desde GitHub, `analizar.py` admite los CSV exportados si no están los registros originales. Para renderizar de nuevo con `visualizar.py` se necesitan los campos locales o volver a simular.

La interfaz de ParaView en WSL tuvo un problema de ventanas invisibles que se resolvió reiniciando Weston/WSLg; no estaba relacionado con la física ni con la ubicación del caso.
