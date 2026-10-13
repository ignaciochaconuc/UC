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

Con 1440 intervalos por vuelta y la huella radial provisional de 20 mm:

| Componente | Mínimo | Máximo | Promedio |
|---|---:|---:|---:|
| Rodillo 1 | 1 | 4 | 2,925 |
| Rodillo 2 | 1 | 4 | 2,925 |
| Total | 4 | 8 | 5,850 |

El promedio de **2,925 agujeros por rodillo** es 41,5 % menor que la estimación
preliminar de cinco. La diferencia no invalida por sí sola la Entrega 1: el
conteo actual usa los centros reales, pero depende de la posición radial supuesta
y de una huella rectangular aproximada que aún debe confirmarse en el conjunto.

## Hipótesis y limitaciones revisables

- El plano no fija inequívocamente la posición radial del rodillo. Su ancho de 20
  mm se ubica provisionalmente con centro en 63,5 mm: contacto radial 53,5–73,5 mm.
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
| A: cuadrático | 2,499 | 3,880 / 2,428 | 25,197 / 15,592 | 1,362 / 0,843 |
| B: senoidal | 2,606 | 5,195 / 4,626 | 34,216 / 29,707 | 1,849 / 1,605 |
| C: constante | 4,976 | 9,953 / 7,278 | 64,689 / 46,741 | 3,496 / 2,526 |

Frente a la Entrega 1, el máximo constante por rodillo baja de 6,180 a 4,976 kN
porque la geometría real presenta como máximo cuatro agujeros activos, no cinco.
El torque máximo constante es 64,689 N m frente a 78 N m; además del conteo, el
nuevo cálculo utiliza el radio real de cada perforación. Los modelos variables
reducen las cargas porque no asignan 44 MPa simultáneamente a todos los centros.
Esto no justifica descartar el caso constante ni concluir que el motor está
sobredimensionado.

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
53,5–73,5 mm y tangencial `-Lc/2 ... +Lc/2`. La intersección se obtiene mediante
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
| A: cuadrático | 3,880 / 2,428 | 25,197 / 15,592 | 1,362 / 0,843 |
| B: senoidal | 5,195 / 4,626 | 34,216 / 29,707 | 1,849 / 1,605 |
| C: constante binario | 9,953 / 7,278 | 64,689 / 46,741 | 3,496 / 2,526 |
| D: superposición | 7,976 / 7,286 | 50,673 / 46,781 | 2,738 / 2,528 |

En el modelo D, cada rodillo alcanza 4,443 kN y promedia 3,643 kN. Se detectan
entre 4 y 7 perforaciones con superposición positiva por rodillo; en total son
8–11, con promedio 9,744. La cobertura media de los contactos positivos es 0,601.
El valor mínimo positivo puede aproximarse arbitrariamente a cero cuando aparece
un solapamiento tangencial muy pequeño; en la discretización actual es
`3,88e-10`.

La fuerza total máxima ocurre a `t=0,058140 s`, `θ=180°`. En ese instante, las
resultantes basadas en centroides se ubican a 63,190 mm radialmente y a +0,611 mm
para el rodillo 1 / -0,611 mm para el rodillo 2 en dirección tangencial local.

El promedio de fuerza del modelo D es 0,12 % superior al constante binario. No es
una inconsistencia: las contribuciones parciales de centros exteriores elevan el
número medio de contactos efectivos. Su máximo es menor porque las transiciones
de entrada y salida ya no asignan instantáneamente el área completa. El límite
`N_superpuestas P_max A_h` se comprueba en cada instante.

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
