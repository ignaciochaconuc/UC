# Simulación mecánica de peletizadora de matriz plana

El proyecto contiene la geometría y cinemática de la Etapa 1, el modelo
cuasiestático de presiones de la Etapa 2B y el modelo geométrico de superposición
de áreas de la Etapa 2C. No es una simulación DEM ni FEA y sus distribuciones de
carga no son leyes constitutivas experimentales.

## Ejecución

Desde este directorio:

```powershell
python -m pip install -r requirements.txt
python simulacion.py
python simulacion_cargas.py --modelo todos --animacion cuadratico
python simulacion_superposicion.py --modelo todos
pytest -q
```

`python simulacion.py --sin-gif` omite la animación y permite una comprobación
rápida. `--geometria provisional` fuerza el respaldo no CAD. La ejecución normal
usa `datos/agujeros_matriz.csv`; si aún no existe, extrae automáticamente los 102
centros de `cara_matriz.dxf` y crea el CSV.

Para la Etapa 2B, `--modelo` acepta `cuadratico`, `senoidal`, `constante` o
`todos`. `--animacion ninguna` omite el GIF; una animación solicitada usa solo 181
cuadros visuales, pero los cálculos y CSV conservan los 1440 intervalos.

## Datos y ecuaciones

Los parámetros se centralizan en `config.py` y usan SI internamente. La matriz
gira a 516 rpm:

```text
ω = 2π n / 60
θ_i(t) = θ_i(0) + ωt
T = 60 / n = 0,116279 s
```

La longitud tangencial aproximada de contacto es:

```text
Lc = sqrt(Dr h - h²) = 19,596 mm
```

Cada zona activa es una prueba de pertenencia a un rectángulo fijo en el marco
global. Los rodillos se ubican a 0° y 180°. Un centro es activo si su coordenada
radial está dentro del ancho del rodillo y su coordenada tangencial satisface
`|t| <= Lc/2`.

## Geometría utilizada

El DXF suministrado contiene exactamente 102 círculos repetidos de radio 4,5 mm,
interpretados como las entradas de Ø9 mm mostradas en el plano. Se usan solamente
sus centros; el diámetro efectivo de las perforaciones permanece en Ø6 mm. Los
centros están entre 47,030 y 79,865 mm de radio y su separación mínima es 12,422
mm, por lo que no se superponen.

La validación del anillo se aplica a los **centros**, consistente con el CAD: el
borde de algunas bocas de Ø9 mm cruza nominalmente los radios de 45 u 80 mm.

## Resultados de una revolución

Con 1440 intervalos por vuelta y la huella radial corregida de 40 mm:

| Componente | Mínimo | Máximo | Promedio |
|---|---:|---:|---:|
| Rodillo 1 | 2 | 8 | 5,1125 |
| Rodillo 2 | 2 | 8 | 5,1125 |
| Total | 7 | 14 | 10,225 |

El promedio de **5,1125 agujeros por rodillo** es 2,25 % mayor que la estimación
preliminar de cinco. El conteo actual usa los centros reales, pero sigue dependiendo
de la huella rectangular aproximada.

## Hipótesis y limitaciones revisables

- El ancho axial/radial correcto del rodillo es 40 mm. Los 20 mm del plano son la
  distancia desde un extremo hasta el plano medio. Con centro radial en 63,5 mm,
  la huella corregida abarca 43,5–83,5 mm.
- La proyección completa de cada rodillo se dibuja como una franja de 20 x 100 mm;
  la huella activa se aproxima mediante un rectángulo de 20 x 19,596 mm.
- No se considera deformación de biomasa, deslizamiento, holgura ni forma hertziana
  de contacto. `Lc` es una aproximación geométrica de la Entrega 1.
- El conteo depende del muestreo temporal de 1440 intervalos por vuelta. El punto de
  360° se exporta para verificar periodicidad, pero se excluye de los promedios.
- La comparación con cinco agujeros activos no valida todavía el dimensionamiento
  mecánico; depende especialmente de la posición radial asumida para los rodillos.

## Salidas

`resultados/` contiene:

- `animacion_matriz.gif`: matriz, rodillos fijos, huellas y agujeros activos.
- `instante_30_grados.png`: figura estática para el informe.
- `actividad_vs_tiempo.png`: conteos de ambos rodillos y total.
- `actividad_una_revolucion.csv`: serie temporal completa.
- `resumen_actividad.csv`: mínimo, máximo y promedio.

La separación modular es: `geometria.py` carga y valida; `cinematica.py` rota y
clasifica; `visualizacion.py` dibuja; `simulacion.py` coordina y exporta la Etapa 1.

## Etapa 2B: ecuaciones de carga

La coordenada tangencial normalizada aumenta en el sentido antihorario real de la
matriz: `u=0` en la entrada y `u=1` en la salida. Fuera de la huella la presión es
cero. Dentro de ella se comparan:

```text
Modelo A: P(u) = P_max u²
Modelo B: P(u) = P_max sin(πu)
Modelo C: P(u) = P_max

A_h = π D_p² / 4
F_i = P_i A_h
T_i = r_i μ_eff F_i
P_resistente = T ω
```

Se usan `P_max=44 MPa`, `D_p=6 mm` y `μ_eff=0,1`. Cada `r_i` proviene de las
coordenadas reales del DXF. La separación mínima rodillo–matriz (`0,1 mm`) y el
espesor inicial de biomasa (`4 mm`) son parámetros independientes.

A 44 MPa resulta `F_i=1244,071 N`. Los 1236 N de la Entrega 1 corresponden a una
presión no redondeada cercana a 43,7 MPa; no se aplicó ninguna corrección para
forzar coincidencia.

## Resultados de la Etapa 2B

Los promedios excluyen el estado duplicado de 360°:

| Modelo | F máx. por rodillo [kN] | F total máx./media [kN] | Torque máx./medio [N m] | Potencia máx./media [kW] |
|---|---:|---:|---:|---:|
| A: cuadrático | 4,015 | 6,769 / 4,247 | 42,789 / 26,583 | 2,312 / 1,436 |
| B: senoidal | 5,195 | 9,051 / 8,070 | 56,708 / 50,510 | 3,064 / 2,729 |
| C: constante | 9,953 | 17,417 / 12,721 | 108,821 / 79,617 | 5,880 / 4,302 |

Frente a la Entrega 1, el máximo constante por rodillo aumenta de 6,180 a 9,953
kN porque la geometría corregida presenta hasta ocho agujeros activos, no cinco.
El torque máximo constante es 108,821 N m frente a 78 N m. Además del conteo, el
nuevo cálculo utiliza el radio real de cada perforación. Los modelos variables
reducen las cargas porque no asignan 44 MPa simultáneamente a todos los centros.

No se proporcionó una eficiencia de transmisión. Por ello, los 5,5 kW nominales
del motor aparecen en la gráfica solo como referencia y no como potencia disponible
en la matriz.

## Salidas de la Etapa 2B

`resultados/etapa_2b/` contiene un CSV agregado y un `csv.gz` individual por
modelo, además de los cinco tipos de gráfico y la animación del modelo principal.
Los archivos individuales guardan solo estados activos; todo estado omitido tiene
presión, fuerza y torque nulos. Incluyen identificador, tiempo, rodillo, radio,
`u`, presión, fuerza y contribución al torque.

`modelos/presion.py`, `modelos/fuerzas.py` y `modelos/torque.py` contienen las
relaciones de la Etapa 2B; `simulacion_cargas.py` coordina la ejecución y
`visualizacion_cargas.py` genera sus figuras.

## Corrección del ancho del rodillo: 20 a 40 mm

La interpretación inicial del plano era incorrecta: 20 mm corresponde a la
distancia entre un extremo y el plano medio, no al ancho total. Desde esta
corrección, `ancho_rodillo_m=0.040`; con el centro conservado en 63,5 mm, todos los
módulos obtienen desde `config.py` los límites radiales 43,5–83,5 mm. Se mantienen
`Lc=19,596 mm`, `P_max=44 MPa` y todas las ecuaciones de 2B y 2C.

Comparación 2B, expresada como **20 mm → 40 mm**:

| Modelo | Activos por rodillo media/máx. | F rodillo máx./media [kN] | F total máx./media [kN] | Torque máx./medio [N m] | Potencia máx./media [kW] |
|---|---:|---:|---:|---:|---:|
| Cuadrático | 2,925/4 → 5,1125/8 | 2,499/1,214 → 4,015/2,124 | 3,880/2,428 → 6,769/4,247 | 25,197/15,592 → 42,789/26,583 | 1,362/0,843 → 2,312/1,436 |
| Senoidal | 2,925/4 → 5,1125/8 | 2,606/2,313 → 5,195/4,035 | 5,195/4,626 → 9,051/8,070 | 34,216/29,707 → 56,708/50,510 | 1,849/1,605 → 3,064/2,729 |
| Constante | 2,925/4 → 5,1125/8 | 4,976/3,639 → 9,953/6,360 | 9,953/7,278 → 17,417/12,721 | 64,689/46,741 → 108,821/79,617 | 3,496/2,526 → 5,880/4,302 |

En la Etapa 1, el total activo medio/máximo cambia de `5,850/8` a
`10,225/14`. En 2C, las superposiciones positivas medias/máximas por rodillo
cambian de `4,872/7` a `6,692/10`; la fuerza por rodillo máxima/media pasa de
`4,443/3,643 kN` a `8,249/6,350 kN`; la fuerza total de `7,976/7,286 kN` a
`14,433/12,699 kN`; el torque de `50,673/46,781 N m` a `91,029/79,486 N m`; y la
potencia de `2,738/2,528 kW` a `4,919/4,295 kW`.

La tabla completa, incluidos mínimos y cambios porcentuales, se exporta en
`resultados/comparacion_correccion_ancho_rodillo.csv`. Los resúmenes originales se
conservan en `resultados/referencia_ancho_20mm/`.

La huella corregida 43,5–83,5 mm rebasa el anillo útil nominal 45–80 mm en 1,5
mm hacia el interior y 3,5 mm hacia el exterior. No queda fuera de la matriz de
radio 100 mm, pero significa que parte del rodillo trabaja sobre zonas sin centros
de perforación. El modelo conserva esta geometría sin recortarla al anillo útil.

## Limitaciones físicas

- Los perfiles cuadrático y senoidal son hipótesis espaciales no validadas para la
  mezcla de biomasa; el constante es una envolvente dentro del modelo adoptado.
- `μ_eff=0,1` es una equivalencia de resistencia tangencial heredada, no una
  relación fuerza axial/fricción validada experimentalmente.
- La huella sigue siendo rectangular y su posición radial debe confirmarse.
- No se modelan flujo en perforaciones, contacto 3D, corte, deformación, fatiga ni
  capacidad de producción. Los resultados son escenarios preliminares de carga.

## Etapa 2C: superposición geométrica

El cuarto modelo sustituye la activación binaria por la fracción cubierta del
disco efectivo de cada canal:

```text
A_h = π r_h²,  r_h = 3 mm
f_i = A_c,i / A_h
F_i = P_max A_c,i = P_max A_h f_i
```

`A_c,i` es la intersección entre el disco y la huella rectangular radial
43,5–83,5 mm y tangencial `-Lc/2 ... +Lc/2`. La intersección se obtiene mediante
integración determinista 1D de Gauss–Legendre: en cada coordenada radial se recorta
analíticamente el segmento vertical del círculo contra el rectángulo. No se usa
Monte Carlo ni se aproxima solamente por distancia al borde.

La cuadratura de orden 64 calcula área y momentos de primer orden. En los tres
casos parciales del estudio de convergencia, su error relativo frente a orden 512
es menor que `3,5e-6`. Los casos geométricos de control entregan cobertura 0 para
un disco exterior, 1 para uno contenido, aproximadamente 0,5 sobre un borde recto
y aproximadamente 0,25 con el centro en una esquina.

Para el torque se conserva el radio real del **centro del agujero**, según la
definición de la Entrega 1. Para la ubicación espacial de la resultante se exportan
dos alternativas claramente separadas:

- promedio ponderado de los centros de agujeros;
- promedio ponderado de los centroides de las áreas superpuestas, preferido para
  el análisis geométrico posterior del eje de rodillos.

### Resultados de una revolución

| Modelo | Fuerza total máx./media [kN] | Torque máx./medio [N m] | Potencia máx./media [kW] |
|---|---:|---:|---:|
| A: cuadrático | 6,769 / 4,247 | 42,789 / 26,583 | 2,312 / 1,436 |
| B: senoidal | 9,051 / 8,070 | 56,708 / 50,510 | 3,064 / 2,729 |
| C: constante binario | 17,417 / 12,721 | 108,821 / 79,617 | 5,880 / 4,302 |
| D: superposición | 14,433 / 12,699 | 91,029 / 79,486 | 4,919 / 4,295 |

En el modelo D, cada rodillo alcanza 8,249 kN y promedia 6,350 kN. Se detectan
entre 5 y 10 perforaciones con superposición positiva por rodillo; en total son
10–18, con promedio 13,383. La cobertura media de los contactos positivos es
0,7627.
El valor mínimo positivo puede aproximarse arbitrariamente a cero cuando aparece
un solapamiento tangencial muy pequeño; en la discretización actual es
`2,36e-4`.

La fuerza total máxima ocurre a `t=0,027778 s`, `θ=86°`. En ese instante, la
resultante basada en centroides del rodillo 1 se ubica en 61,709 mm radial y
+0,541 mm tangencial; la del rodillo 2, en 63,579 mm radial y +0,150 mm tangencial.

El promedio de fuerza del modelo D es 0,17 % inferior al constante binario. Sus
contactos parciales incrementan el número de perforaciones consideradas, mientras
que la ponderación por área reduce la carga de las que cruzan los bordes. Su máximo
es 17,1 % menor porque las transiciones ya no asignan instantáneamente el área
completa. El límite `N_superpuestas P_max A_h` se comprueba en cada instante.

### Ejecución y salidas 2C

```powershell
# Comparación completa y GIF reducido de cobertura
python simulacion_superposicion.py --modelo todos

# Solo el modelo nuevo, sin animación
python simulacion_superposicion.py --modelo area_superposicion --sin-animacion
```

`resultados/etapa_2c/` contiene las cargas agregadas, las contribuciones por
perforación en CSV comprimido, resumen estadístico con instantes de máximos,
comparación de cuatro modelos, resultantes, ejemplos geométricos, convergencia y
animación. Los CSV individuales incluyen centros globales y locales, áreas,
cobertura, centroides, fuerza y torque.

### Interpretación y limitaciones 2C

El modelo de superposición es el más adecuado de los cuatro para **describir
geométricamente** la entrada y salida de carga, porque elimina el salto binario y
considera bordes y esquinas. No es necesariamente el modelo físico más exacto: la
presión uniforme de 44 MPa sobre el área cubierta sigue siendo una hipótesis.
Persisten las incertidumbres sobre la ley constitutiva y flujo de biomasa, presión
real de contacto, historia de compactación, `μ_eff`, geometría 3D, deformación,
atascamientos y capacidad másica. El modelo proporciona escenarios equivalentes de
carga para ingeniería estructural preliminar, no consumos reales ni resultados FEA.
