# 5E.2 — ecuaciones, fuentes y límites

Unidades: fuerzas N, dimensiones mm, torque N·m convertido a N·mm,
presiones/esfuerzos N/mm²=MPa. Las fórmulas son equilibrio y resistencia media
elementales; no se atribuyen a Gates ni sustituyen un cálculo de unión real.

## Fuentes verificadas

- Extracto Ganter DIN 6885-1, página 2078: filas Ø35 y Ø38, ancho 10,
  altura 8, profundidad de cubo 3,3 (+0,2/0), profundidad de eje 5 (+0,2/0).
  El dibujo del proveedor usa t2 para cubo, t4 para eje y t1=d+t2 como
  medida de control sobre agujero; no intercambiar esa nomenclatura con
  otras tablas donde t1 designa la profundidad del eje.
- Ficha comercial Ganter DIN 6885: candidata 10x8 para rango de diámetro
  más de 30 hasta 38 mm, inclusive; ancho de chaveta h9. Solo se usan las
  dimensiones, no las propiedades del acero inoxidable del producto consultado.
- DIN Media: identifica DIN 6885-1:2021-11 de forma alta como vigente.
  No se leyó el texto completo de pago; no se declara conformidad integral.
- ISO confirma ISO/R 773:1969 retirada el 03-11-1998. Se trata como antecedente,
  no como una norma actual equivalente que certifique por sí sola la unión.

URLs, claves BibTeX y fecha se registran en `fuentes.json`. Las dos filas
de Ganter se consultaron directamente en su PDF; los valores no provienen de
una tabla genérica sin autor. No se transfieren cotas de norma a los planos
como si ya estuvieran mecanizadas.

## Fuerza de contacto, cortante y aplastamiento

Con una chaveta paralela que transmite todo el torque:

```text
F_contacto = 2 abs(T) 1000 / d
tau_media = F_contacto / (b L_activa)
p_cubo_media = F_contacto / (h_contacto_cubo L_activa)
p_eje_media = F_contacto / (h_contacto_eje L_activa)
```

Las fuerzas son de contacto de unión sobre Ø38/Ø35, no las diferencias de
tensión de correa sobre Ø100/Ø280 ni fuerzas laterales de polea. Los torques
se importan por polea y escenario desde la última revisión conjunta, conservando
el paso original de 3C y sin asignar tiempo al motor nominal ideal.

El ancho 10 JS9 del plano motriz es coherente nominalmente con b=10 y con
una clase de chavetero de cubo admitida en el extracto Ganter. JS9 no es la
tolerancia de ancho de la chaveta h9 ni el ajuste diametral eje–agujero.
El extracto asocia cubo JS9/eje N9 con asiento suelto y exige cotejar el plano
de producto. No se asignan desviaciones numéricas JS9 ni se aprueba el ajuste
completo sin especificación de eje y chaveta.

La sensibilidad usa largos **activos** de 20, 30, 40 y 50 mm, todos menores
que las envolventes 62 y 78,6 mm. Esa condición es necesaria, no suficiente:
faltan largo real del eje, hombros y extremos. Para una chaveta de extremos
redondeados, el largo total no es automáticamente el área de flanco portante;
se debe confirmar la longitud efectiva y forma antes de seleccionar el producto.

Solo como escenario geométrico nominal de candidata 10x8 se usan alturas de
contacto cubo=8−5=3 mm y eje=5 mm, sin reducir por chaflanes, tolerancias o
redistribución. Profundidad del chavetero de cubo 3,3 mm no es altura activa:
la diferencia 0,3 corresponde a holgura de fondo nominal. Las alturas reales
y los materiales siguen pendientes. No se calculan FS ni longitudes mínimas
resistentes sin esfuerzos admisibles trazables.

## Cubo debilitado: geometría antes de resistencia

Para exterior cilíndrico De, agujero d, ranura rectangular b y profundidad q
medida desde la tangente superior del agujero al fondo:

```text
pared_lisa = (De-d)/2
y_fondo = d/2 + q
ligamento_central = De/2 - y_fondo
ligamento_radial_esquina_ideal = De/2 - sqrt((b/2)^2 + y_fondo^2)
De_min_envolvente_sin_reserva = 2 sqrt((b/2)^2 + y_fondo^2)
```

Son condiciones de contención geométrica del fondo plano y sus esquinas
ideales, **no ecuaciones de resistencia ni criterios de espesor mínimo admisible**.
Se deben cotejar filetes reales: las esquinas ideales pueden recortarse por radios,
pero no crean margen central donde no lo hay. Este cribado no modela fisuración,
flexión local de paredes, presión real, fatiga ni interacción con M5.

Para motriz Ø45/Ø38, la pared lisa de 3,5 mm se reduce a 0,2 mm en el centro
con q=3,3; con q=3,5 se anula. La envolvente de esquina ideal ya sale del
exterior a profundidad nominal. Por ello no es aceptable usar la tensión
torsional del anillo liso de 5E.1 como evidencia de un cubo resistente con esa
ranura. La cifra de diámetro mínimo de envolvente se entrega sin reserva:
**no es una propuesta de diámetro resistente**.

La profundidad real del CAD no está acotada: no se afirma que la pieza CAD
ya tenga esa profundidad o ruptura. Se identifica la incompatibilidad al
intentar adaptar la candidata de forma alta normalizada. Debe revisarse el cubo
o una unión alternativa documentada antes de fabricar. No se selecciona
automáticamente un mayor cubo, chaveta baja o ajuste de interferencia.

En conducida Ø75/Ø35 el ligamento nominal es mayor; eso solo evita esta
incompatibilidad geométrica inmediata. La resistencia sigue pendiente de
dimensiones locales y material. La eventual unión FEM debe incluir la ranura,
filetes y M5 sobre geometría real, sin convertir los valores medios en máximos.

## Tres funciones diferentes de la unión

1. Transmisión de torque: candidata chaveta con apoyo de flancos, por verificar.
2. Centrado: ajuste diametral real eje–cubo, aún sin tolerancias confirmadas.
3. Retención axial: solución diseñada independiente, actualmente no definida.

El M5 radial solo prueba que existe una rosca. Sin grado, punta, engrane,
precarga y contacto no se le atribuye torque ni capacidad axial. Ø38 del
agujero no acredita disponibilidad de ese eje en un motor de 5,5 kW; tampoco
Ø35 demuestra el diámetro del asiento real del árbol vertical. Se requieren
planos/fichas y mediciones de ambos ejes, y verificación de montaje.

La discrepancia SPA de conducida 34° CAD frente a 38° Gates sigue pendiente.
No se modifican los resultados de capacidad, pretensión, contacto ni ejes.
