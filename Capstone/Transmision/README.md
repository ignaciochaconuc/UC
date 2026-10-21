# Transmisión mecánica — Etapas 5A, 5B y 5C

Modelo preliminar de una transmisión abierta por tres correas SPA 1600 entre el
motor de 5,5 kW a 1450 rpm y el eje vertical. Las etapas existentes se consultan
como entradas: [contacto y rodillos](../Simulación_peletizadora/README.md) y
[matriz/eje vertical](../Analisis_matriz_eje_vertical/README.md). Sus cálculos,
fuentes y resultados permanecen sin modificaciones. No se genera informe LaTeX.

## Ejecución y archivos

Desde `Capstone/Transmision`:

```powershell
python -m pip install -r requirements.txt
python simulacion_transmision.py
python -m pytest -q
# Otra parametrización o destino:
python simulacion_transmision.py --parametros parametros.json --salida resultados
```

La ejecución usa únicamente la biblioteca estándar; pytest es para las pruebas.
`parametros.json` contiene los datos de diseño y escenarios. `transmision/`
separa geometría, dimensionamiento, balance motor y datos de catálogo.
Las funciones validan valores positivos y finitos, geometría, eficiencia,
cantidad entera de correas y compatibilidad con el catálogo transcrito.
La geometría es parametrizable; la capacidad de catálogo se restringe a los
puntos verificados. Modificar rpm, diámetro pequeño o longitud exige ampliar
las tablas desde la fuente original; no se extrapolan capacidades.

`resultados/` contiene `geometria_5a.csv`, `capacidad_5b.csv`,
`sensibilidad_factor_servicio.csv`, `balance_motor_eficiencias.csv`,
`contraste_3c.csv`, `resumen.json`, `parametros_utilizados.json` y
`fuentes_y_validacion.json`. Este último registra la referencia y el SHA256 del
resumen 3C leído. Se comparan los datos declarados con la fila `inclinacion`
de `resumen_comparativo.csv` (tolerancia de redondeo: 0,001 kW o N·m).

## Catálogo y decisiones de lectura

Fuente: [Gates, Industrial V-Belt Drive Design Manual, 2004](https://www.gates.com/content/dam/documents-library/catalogs/industrial-v-belt-design-manual-kr.pdf).
Se inspeccionaron visualmente las tablas originales. Las páginas impresas
56–57 son las de SPA (páginas PDF 58–59, contando desde uno). La impresa 55
contiene correcciones SPZ y no se utiliza para SPA.

Se utiliza **SPA Super HC convencional envuelta**, no la construcción MN.
El encabezado excluye las columnas en cursiva para la construcción convencional;
la columna de 100 mm utilizada está en letra normal.

- Potencia básica A: 3,16 kW/correa, intersección exacta de 1450 rpm y 100 mm.
- Adicional B: 0,54 kW/correa, fila exacta de 1450 rpm e intervalo rotulado
  de relación 1,95–3,38 que contiene 2,8. No se interpola entre columnas.
- Factor CL: 0,94 para longitud de referencia SPA 1600, punto exacto.
- Adicional de vida C: cero, base de catálogo de 12.000 h. Esta base permite
  reproducir el dimensionamiento preliminar; no es una vida requerida ni
  una predicción de duración real. Las 8 h/día no fijan por sí solas una vida.
- Para G se obtiene `(D-d)/a=0,364878`. Las filas vecinas dan 0,96 y 0,94.
  No se encontró una autorización explícita para interpolar en el manual
  consultado. Se adopta como decisión conservadora propia el menor factor
  entre ambos extremos: **G=0,94**. No se presenta esa regla como instrucción
  literal del fabricante. La interpolación daría aproximadamente 0,947;
  el contraste con 0,947 se exporta por separado y no gobierna la selección.

Las potencias de estas tablas son específicas de la construcción Gates.
Que una correa genérica cumpla DIN 7753 no confirma idéntica capacidad: falta
verificar fabricante, referencia comercial, longitud de referencia y juego
de tres correas compatibles antes de aprobar la compra.

## 5A: cinemática y geometría

En 5A/5B se adoptaron diámetros de referencia de 100 y 280 mm; 5C confirma
esa identificación y registra los exteriores CAD de 105,6 y 285,6 mm.
Los resultados históricos y su campo `diametros_son_referencia_supuesto`
se conservan; la confirmación actual se registra en `etapa_5c` de los parámetros.
Se asume rodadura ideal, sin deslizamiento ni elasticidad.
Con `d`, `D` y `a` en mm:

```text
i = D/d; n_salida = n_motor/i; v = pi d n_motor / 60000
alpha = asin((D-d)/(2a)); beta_pequeña = pi - 2 alpha
L_aprox = 2a + pi(D+d)/2 + (D-d)^2/(4a)
L_exacta = 2 sqrt(a²-((D-d)/2)²) + pi(D+d)/2 + (D-d) alpha
```

La longitud exacta es la geometría ideal de tangentes y arcos de dos círculos.
Se invierte numéricamente por bisección para comprobar los centros comerciales.

| Magnitud | Resultado |
|---|---:|
| Relación | 2,8 |
| Salida teórica | 517,857 rpm |
| Velocidad de correa | 7,592 m/s |
| Centros suministrados | 493,316 mm |
| Longitud aproximada / exacta | 1599,9541 / 1600,0001 mm |
| Centros para longitud exacta de 1600 mm | 493,31595 mm |
| Abrazamiento motriz / conducida | 158,976° / 201,024° |

La longitud coincide geométricamente con 1600 mm. La velocidad de salida
supera en 1,857 rpm (0,360 %) las 516 rpm usadas en 3C. Se conservan las cargas
heredadas a 516 rpm, sin escalarlas ni recalcular el contacto. El deslizamiento
real y la velocidad de operación siguen pendientes de medición.

## 5B: capacidad y sensibilidad

```text
P_diseño = FS P_motor
P_correa = (A+B+C) G CL
z_mínimo = ceil(P_diseño/P_correa)
margen relativo = (z P_correa/P_diseño - 1) × 100
```

Para FS preliminar 1,3: potencia de diseño **7,15 kW**, capacidad corregida
**3,26932 kW/correa**, capacidad de tres correas **9,80796 kW** y mínimo
**3 correas**. El margen es **2,65796 kW (37,17 % sobre la potencia de diseño)**;
la utilización de capacidad es 72,90 %. Con G=0,947, el contraste da
3,29367 kW/correa, 9,88100 kW totales y también tres correas.

La capacidad adoptada admite FS hasta aproximadamente **1,7833**. Por ejemplo,
FS=1,0 exige dos correas, FS=1,3 y 1,6 exigen tres, y FS=1,8 y 2,0 exigen
cuatro. El CSV incluye todos los escenarios. FS=1,3 es una hipótesis recibida:
faltan confirmar severidad de compactación, arranques, atascos y régimen para
validarla con la clasificación de servicio del fabricante.

## Potencia disponible del motor: comprobación independiente

Se supone que 5,5 kW es potencia mecánica nominal de eje. La potencia de diseño
de correas incorpora servicio; no es una nueva demanda de 7,15 kW al motor.
Para cada eficiencia total supuesta se calcula `P_disponible=eta × 5,5 kW` y
se compara con los valores heredados 4,805 kW máximos y 4,194 kW medios.

| Eficiencia supuesta | Disponible [kW] | Margen máximo [kW] | Margen medio [kW] |
|---:|---:|---:|---:|
| 0,85 | 4,675 | −0,130 | 0,481 |
| 0,87 | 4,785 | −0,020 | 0,591 |
| 0,90 | 4,950 | 0,145 | 0,756 |
| 0,95 | 5,225 | 0,420 | 1,031 |
| 1,00, límite ideal | 5,500 | 0,695 | 1,306 |

La eficiencia mínima aritmética para cubrir el máximo es **87,36 %**; para
la media, **76,25 %**. No se midió una eficiencia ni se comprobaron arranque,
sobrecarga, temperatura o atascos. El torque máximo heredado es 88,924 N·m;
se registra para trazabilidad, sin duplicar los modelos estructurales ni usarlo
para inventar tensiones de ramales.

## Pendientes de selección comercial y cargas (5D)

- Referencias comerciales exactas de las tres correas y poleas, construcción,
  norma y equivalencia de capacidad; confirmar tipo de longitud y de diámetros.
- Perfil de canales, alineación, ancho, número de gargantas y fijaciones.
- Método y valor de tensado del fabricante, recorrido de instalación y retensado,
  posibilidad de mover centros y compatibilidad del conjunto de correas.
- Disposición espacial de motor y eje vertical, orientación de ramales,
  posiciones axiales de polea y apoyos, y voladizos para calcular fuerzas/reacciones.
- Pretensión, masa lineal y datos del fabricante necesarios para separar ramal
  tenso/flojo y efectos centrífugos. Las fuerzas sobre ejes quedan pendientes.
- Arranques, aceleración, régimen real, atascos, condiciones ambientales y
  eficiencia; confirmar si debe alcanzarse exactamente 516 rpm.

Las pruebas cubren geometría analítica, inversión de longitud, unidades,
tabla específica, selección conservadora, redondeo de cantidad, sensibilidad,
balance de potencia, rechazo de entradas incompatibles y trazabilidad de 3C.

## 5C: geometría comercial y recorrido de tensado

Ejecutar separadamente para conservar los archivos históricos de 5A/5B:

```powershell
python simulacion_tensado.py
python -m pytest -q
```

El ejecutable reutiliza `geometria()` de 5A y contrasta `resolver()` con el
histórico validado de 5A/5B, sin regenerarlo. Las salidas propias se guardan en
`resultados/etapa_5c/`: `resumen.json`, `poleas_y_gargantas.csv`,
`ajuste_centros.csv`, `geometria_nominal.csv`, `validaciones.csv`,
`parametros_utilizados.json` y `fuentes_y_trazabilidad.json`.
Los SHA256 permiten comprobar que los archivos originales siguen idénticos.
Los avisos en el resumen histórico reflejan el estado de conocimiento de 5A/5B;
las confirmaciones actuales están en 5C.

### Diámetros confirmados y cotejo de gargantas

| Polea | Referencia [mm] | Exterior CAD [mm] | Diferencia diametral [mm] |
|---|---:|---:|---:|
| Motriz | 100 | 105,6 | 5,6 |
| Conducida | 280 | 285,6 | 5,6 |

La diferencia corresponde a 2,8 mm radiales desde la referencia hasta el
exterior CAD en ambas poleas. La cinemática y longitud utilizan exclusivamente
100 y 280 mm; los exteriores solo se usan para cotejo geométrico e interferencias.

Se verificó visualmente la tabla 18 del mismo manual Gates, página impresa 40
(PDF 42). Su fila SPA remite a DIN 2211 e ISO 4183. Para tres correas
independientes se requieren **tres gargantas SPA alineadas en cada polea**.
Los datos de referencia para cotejar los planos son:

| Magnitud | Motriz | Conducida |
|---|---:|---:|
| Ángulo de garganta | 34° ±1° | 38° ±1° |
| Ancho de referencia lp | 11 mm | 11 mm |
| Paso e entre centros | 15 ±0,30 mm | 15 ±0,30 mm |
| Distancia f del centro extremo al borde | 10 ±0,6 mm | 10 ±0,6 mm |
| Profundidad d de la tabla | 13,75 (+0,25/−0) mm | 13,75 (+0,25/−0) mm |
| Ancho de boca go tabulado | 12,68 mm | 12,89 mm |
| Altura b sobre referencia | 2,75 mm | 2,75 mm |

El ángulo depende del diámetro de referencia: la fila de 90–118 mm usa 34°
y la de más de 118 mm usa 38°. El ancho nominal de llanta calculado es
`B=(z−1)e+2f=50 mm` en ambas poleas. Es una dimensión de referencia, no
un ancho comercial verificado ni el ancho total de una polea con cubo.

**Diferencia pendiente de cotejo CAD:** b=2,75 mm implica exteriores derivados
de 105,50 y 285,50 mm; Inventor muestra 105,60 y 285,60 mm. La diferencia
es +0,10 mm diametral (+0,05 mm radial). Se registran ambos juegos de valores;
no se declara equivalencia exacta ni se inventa una tolerancia para b. Confirmar
el perfil usado por Inventor y el plano/catálogo comercial. Los diámetros por sí
solos no verifican los ángulos, pasos ni la geometría completa de las gargantas.

### Reserva mecánica de ajuste

Se volvió a comprobar la **tabla 11, impresa 32 (PDF 34)**: para SPA con
longitud de referencia 1200–1999 mm corresponden 25 mm mínimos de acercamiento
y 35 mm mínimos de alejamiento. Se selecciona la fila que contiene 1600 mm,
sin interpolación. Estos recorridos son variaciones de distancia entre centros,
no variaciones de longitud de correa.

| Posición/reserva | Distancia entre centros [mm] |
|---|---:|
| Extremo de acercamiento para instalar | 468,316 |
| Referencia nominal geométrica | 493,316 |
| Extremo de alejamiento para retensado | 528,316 |
| Recorrido útil total mínimo | **60,000** |

En nominal se conservan longitud exacta de 1600,0001 mm, abrazamientos
158,976°/201,024°, relación 2,8 y salida 517,857 rpm. La posición nominal es
la referencia geométrica; el punto real de operación depende del tensado y
del estado de la correa. **Los extremos son reservas de montaje y retensado,
no puntos normales de funcionamiento de una correa inextensible de 1600 mm.**
No se calcula una tensión inicial ni se deduce de la diferencia de longitudes.

### Propuesta preliminar de base móvil y pendientes para 5D

Se propone una base del motor guiada longitudinalmente en la línea de centros,
con regulación de desplazamiento y bloqueo posterior independiente. Debe
permitir como mínimo 25 mm hacia la polea conducida y 35 mm hacia afuera,
mantener paralelismo de ejes y coplanaridad de gargantas, y bloquearse después
de ajustar mediante el procedimiento del fabricante. Si la disposición real
de ejes no permite este movimiento, habrá que adaptar el concepto de base.

Los **60 mm son carrera útil de centros**, no longitud final de una ranura:
esta última también depende del diámetro del perno, extremos, arandelas,
holguras de montaje y distancias a bordes. No se asignan dimensiones de pernos,
ranuras, espesores ni capacidad estructural de la base todavía.

Para 5D necesitamos:

- Fabricante y referencia exactos de correas, método de tensado aplicable
  (fuerza-deflexión o frecuencia), parámetros y límites para correas nuevas y
  usadas, y pauta de retensado. No basta la designación DIN 7753 para fijar tensión.
- Masa lineal de la correa, tramo libre real, comportamiento elástico y datos
  necesarios para los efectos centrífugos y reparto entre las tres correas.
- Condición de carga que gobernará ramales (nominal, arranque o atasco),
  aceleración y pérdidas; no se adopta una relación arbitraria entre tensiones.
- Plano de la transmisión: coordenadas y orientación de ejes/ramales, alturas
  axiales de poleas, centros de rodamientos, voladizos y referencia espacial.
  Las cargas laterales requieren sumar vectorialmente las fuerzas de los ramales;
  la diferencia de tensiones por torque no basta para determinar esa suma.
- Plano y masa del motor, posiciones y medidas de patas/agujeros, materiales
  y espesores de base/bastidor, sistema de guía y bloqueo, clase de pernos,
  fricción de contacto y cargas dinámicas para dimensionar uniones y soportes.

Las pruebas 5C incluyen diferencias diametrales/radiales, frontera de tabla,
recorridos, centros, garganta por correa, dimensiones tabuladas y ángulos por
diámetro, rechazo de valores inválidos y conservación numérica y por SHA256
de 5A/5B. No se calculan reacciones del eje vertical ni se modifica su modelo.
