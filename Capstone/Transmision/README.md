# Transmisión mecánica — Etapas 5A y 5B

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

Los diámetros suministrados de 100 y 280 mm **todavía deben identificarse como
exteriores o de referencia**. Todos los cálculos siguientes suponen diámetros
de referencia. Se asume rodadura ideal, sin deslizamiento ni elasticidad.
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
real y la velocidad de operación deben verificarse en 5C.

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

## Pendientes para 5C

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
