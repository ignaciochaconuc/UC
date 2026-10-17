# Tarea 2, pregunta 1 — OpenFOAM Foundation 14

Caso preparado con los tutoriales instalados `incompressibleFluid/cylinder`,
`mesh/snappyHexMesh/flange` y la extrusión `plane` del tutorial de aerofoil.

## Geometría e hipótesis

- Canal: x=0..100 m, y=0..20 m.
- Cilindro: diámetro D=2 m, centro (6,10) m. Se interpreta que la cota de
  5 m llega hasta la cara anterior del cilindro; confirmar esta interpretación
  con el profesor si la cota debía referirse al centro.
- Modelo 2D: sección extruida a una sola capa, espesor 0.1 m, caras `empty`.
- Entrada uniforme U=1 m/s; salida p=0 (presión cinemática), velocidad `inletOutlet`.
- Paredes y cilindro con no deslizamiento.
- Reynolds basado en D: Re=UD/nu. Se varía nu para mantener la misma escala
  temporal; no se supone que los cuatro casos sean el mismo fluido físico.

| Re | nu [m²/s] | Modelo |
|---:|---:|---|
| 100 | 0.02 | Laminar 2D |
| 1000 | 0.002 | Laminar 2D, aproximación del flujo transicional |
| 10000 | 0.0002 | URANS k-omega SST |
| 100000 | 0.00002 | URANS k-omega SST |

El flujo real alrededor de un cilindro desarrolla estructuras tridimensionales
antes de Re=1000. El caso laminar 2D a ese Re es una simplificación, no una
simulación resuelta de toda la transición. Los casos URANS 2D tampoco resuelven
la turbulencia tridimensional. Documentar estas hipótesis en el informe.

## Mallado personalizado

1. `blockMesh`: malla base de 0.5 m en x,y,z.
2. `snappyHexMesh`: cilindro analítico (sin STL), eliminación del sólido y ajuste
   de su superficie. Niveles de refinamiento sobre la base:
   - Cilindro: 4 (~0.03125 m antes de añadir capas).
   - Región cercana: x=3..12, y=7..13, nivel 3 (~0.0625 m).
   - Estela: x=7..40, y=6..14, nivel 2 (~0.125 m).
   - Estela lejana: x=40..80, y=7..13, nivel 1 (~0.25 m).
   - Bandas junto a las paredes del canal: 0.6 m, nivel 1.
   - Tres capas sobre el cilindro, expansión 1.2; espesor relativo exterior 0.3.
3. `extrudeMesh`: se toma la sección del frente de la malla 3D y se extruye
   una sola capa de 0.1 m. Así el refinamiento octree no deja varias capas en z.
4. `createPatch`: caras frontal y posterior `empty`.
5. `checkMesh`: verificar el resultado antes de simular.

Las mallas de los cuatro Reynolds comparten un enlace a `mesh2d/constant/polyMesh`.
No modificar ni regenerar la malla mientras haya simulaciones usando esos enlaces.

## Ejecutar

Desde una terminal Bash:

```bash
cd /home/chaco/proyectos/UC/CFD/Tarea2_OpenFOAM
source /opt/openfoam14/etc/bashrc
./Allmesh
python3 vista_malla.py
./Allrun 100
# Después, los casos restantes:
./Allrun 1000 10000 100000
```

`Allrun` sin argumentos ejecuta los cuatro casos secuencialmente. Los logs quedan
junto a cada caso. El script se detiene si ya existe un `log.foamRun`, para evitar
sobrescribir una ejecución previa sin revisión.

Abrir `mesh2d/mesh2d.foam` para revisar la malla en ParaView y `Re100/Re100.foam`
(o el Reynolds correspondiente) para visualizar resultados.

`./Allmesh --fine` genera una variante con tamaño base 0.25 m, conservando los
niveles de refinamiento. Antes de hacerlo, guardar por separado los resultados
base: este comando regenera los diccionarios y sustituye la malla compartida.
No ejecutar `preparar.py` sobre casos con configuraciones manuales sin guardar
esas modificaciones, porque reescribe los diccionarios.

## Simulación y verificación pendiente

- Solver `foamRun` / `incompressibleFluid`, transiente PIMPLE y esquema `backward`.
- Paso inicial 0.005 s, adaptativo con Co máximo 0.5 y paso máximo 0.05 s.
- Fin provisional 400 s, salida cada 2 s; comprobar si alcanza un régimen
  periódico o estadísticamente estable. Un tiempo fijado no garantiza convergencia.
- Se escriben Cd y Cl mediante `forceCoeffs`: Uref=1, D=2 y área de referencia
  D*espesor=0.2 m². La normalización usa rhoInf=1.
- Intensidad de turbulencia de entrada asumida 1%, longitud de mezcla 0.14 m.
- Para SST se usa `nutUSpaldingWallFunction`. Falta evaluar y+ en cilindro y
  paredes con resultados desarrollados y ajustar la primera celda/capas si hace
  falta. La malla actual es un punto de partida, no una malla validada para todos
  los Reynolds.
- Comparar mallas base/fina y reducir el paso temporal: Cd medio, amplitud de Cl,
  frecuencia de desprendimiento (St=fD/U) y longitud de recirculación.
- Revisar balance de caudal, residuos por paso y sensibilidad a turbulencia de entrada.

Las mallas, logs y resultados se excluyen de Git mediante `.gitignore`.

Referencia de la herramienta: [guía oficial de snappyHexMesh](https://doc.cfd.direct/openfoam/user-guide/snappyhexmesh).

## Análisis de los resultados completados

`python3 analizar.py` combina los registros de fuerzas de los reinicios, elimina
los tiempos duplicados y calcula promedios y RMS ponderados por tiempo (paso
adaptativo). Usa 200–400 s y compara ventanas 200–300 / 300–400 s. Genera gráficos,
CSV y `resultados/RESUMEN.md` con los límites de interpretación.

Los campos finales se procesaron con:

```bash
foamPostProcess -case Re100 -solver incompressibleFluid -funcs '(vorticity patchFlowRate(patch=inlet) patchFlowRate(patch=outlet))' -time 400
foamPostProcess -case Re10000 -solver incompressibleFluid -func yPlus -time 400
```

Repetir el primer comando para los cuatro Re y `yPlus` para los dos casos SST.
`pvpython --force-offscreen-rendering visualizar.py` exporta U, presión cinemática
y vorticidad z a t=400 s con escalas comunes. La vorticidad proviene de OpenFOAM,
para evitar errores de derivación de VTK en poliedros descompuestos.
