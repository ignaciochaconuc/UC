# Simulación geométrica de peletizadora de matriz plana

Primera etapa del modelo: geometría bidimensional, cinemática de una vuelta e
identificación de perforaciones bajo las zonas de compactación. En esta versión
**no** se calculan presiones, fuerzas ni torque.

## Ejecución

Desde este directorio:

```powershell
python -m pip install -r requirements.txt
python simulacion.py
pytest -q
```

`python simulacion.py --sin-gif` omite la animación y permite una comprobación
rápida. `--geometria provisional` fuerza el respaldo no CAD. La ejecución normal
usa `datos/agujeros_matriz.csv`; si aún no existe, extrae automáticamente los 102
centros de `cara_matriz.dxf` y crea el CSV.

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

Con 180 intervalos por vuelta y la huella radial provisional de 20 mm:

| Componente | Mínimo | Máximo | Promedio |
|---|---:|---:|---:|
| Rodillo 1 | 1 | 4 | 2,633 |
| Rodillo 2 | 1 | 4 | 2,633 |
| Total | 4 | 6 | 5,267 |

El promedio de **2,633 agujeros por rodillo** es 47,3 % menor que la estimación
preliminar de cinco. La diferencia no invalida por sí sola la Entrega 1: el
conteo actual usa los centros reales, pero depende de la posición radial supuesta
y de una huella rectangular aproximada que aún debe confirmarse en el conjunto.

## Hipótesis y limitaciones revisables

- El plano no fija inequívocamente la posición radial del rodillo. Su ancho de 20
  mm se centra provisionalmente en el anillo útil: contacto radial 52,5–72,5 mm.
- La proyección completa de cada rodillo se dibuja como una franja de 20 x 100 mm;
  la huella activa se aproxima mediante un rectángulo de 20 x 19,596 mm.
- No se considera deformación de biomasa, deslizamiento, holgura ni forma hertziana
  de contacto. `Lc` es una aproximación geométrica de la Entrega 1.
- El conteo depende del muestreo temporal de 180 intervalos por vuelta. El punto de
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
clasifica; `visualizacion.py` dibuja; `simulacion.py` coordina y exporta. El
directorio `modelos/` queda reservado para las etapas físicas posteriores.
