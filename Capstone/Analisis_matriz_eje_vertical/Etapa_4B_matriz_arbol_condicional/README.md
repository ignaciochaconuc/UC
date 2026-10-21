# Etapa 4B — Comprobaciones del árbol principal y la matriz

Este paquete continúa la etapa 4A usando sus **1.440 muestras correlacionadas** derivadas de 3C. No modifica los resultados de las etapas anteriores. No sustituye la simulación FEM; sus tensiones son **nominales** en secciones circulares lisas y el resto son análisis de sensibilidad condicionados.

## Ejecución

```bash
pip install numpy pandas matplotlib
python simulacion_etapa_4B.py
python crear_dcl_parametrico.py
```

La entrada `fuentes/series_resultantes_matriz_eje_4A.csv` se conserva sin modificar, para que no sea necesario recalcular 3C ni 4A. Todas las salidas se crean en `resultados`.

## Geometría observada en las capturas nuevas

- Orificio central de la matriz Ø50 mm, visible en la medida CAD; matriz Ø200 mm y 36 mm de espesor (plano anterior), 102 agujeros de Ø6 mm y bocas Ø9 mm.
- Un resalte del árbol de Ø58 mm en dos contornos separados axialmente 12 mm. El hecho de medir el resalte no demuestra por sí mismo el contacto completo ni la retención axial de la matriz.
- Hay transmisión al eje vertical mediante una polea inferior conectada a un motor por correa(s), y una caja que debe albergar los apoyos. **No se observan de forma confirmable el tipo, posiciones y fijaciones de los rodamientos, ni un chavetero, ajuste de interferencia o tornillería específicos en la unión matriz-eje.**

## Cargas heredadas y sincronizadas

- Fuerza axial máxima 14.070,987 N, media 12.398,879 N.
- Torque resistente máximo 88,923966 N·m, medio 77,623586 N·m.
- Momento global máximo debido a cargas axiales 153,801516 N·m, en 269,25° (F=12,864 kN y T=79,063 N·m en ese mismo instante).
- Fuerza lateral tangencial equivalente neta aproximada máxima |Fy|=250,006 N, desde la hipótesis de fricción efectiva de 3C.
- El instante de máximo F no es el de máximo M. Todas las tensiones combinadas se calculan en cada instante antes de extraer su máximo.

## Secciones del eje

Para una sección maciza *lisa* de diámetro `d` donde efectivamente circulen los esfuerzos considerados:

- `sigma_ax = Fz/A`.
- `tau_t = 16 T / (pi d^3)`.
- `sigma_b = 32 M / (pi d^3)`.
- `VM_axial_torsión = sqrt(sigma_ax^2 + 3 tau_t^2)`.
- `VM_condicional = sqrt((|sigma_ax| + |sigma_b|)^2 + 3 tau_t^2)`.

`VM_condicional` considera a modo de **sensibilidad** que la sección cargue con todo el momento externo de la matriz. **No** es la distribución real del momento interno; esta última exige resolver apoyos, carga de correas y posiciones axiales. La fórmula `sigma_ax+sigma_b` produce el máximo valor absoluto de esfuerzo normal en una fibra de la sección bajo la hipótesis planteada, pero no incorpora entallas, tensión de contacto, flexión adicional de las correas ni fatiga.

Módulos **supuestos exclusivamente para sensibilidad de deformación**: `E=210 GPa`, `G=80 GPa`. Se reporta deformación axial y giro unitarios *por 100 mm de longitud uniforme*, no desplazamientos ni giros del conjunto escalonado.

## Contacto matriz–resalte del eje: condicional

Si **y solo si** el apoyo inferior de la matriz se realiza sobre un anillo de diámetros interno 50 mm y externo 58 mm con **toda** el área en contacto, el área es 678,584 mm² y la presión media máxima es 20,736 MPa. Es una presión de aplastamiento promedio **idealizada**, no una presión local de contacto validada, ni un FEM. Una cara Ø58 seleccionada en CAD puede tener un área de superficie diferente, pero eso **no significa que toda ella toque la matriz**. Debe verificarse el ensamblaje y su retención superior.

Torque transmitido en radio 25 mm: fuerza tangencial neta máxima `2*Tmax/0.050 = 3.557 N`. Para comprobar chaveta/fijación deben especificarse sistema de unión, largo activo, ancho, alto y tratamiento.

## Transmisión

Con radio de polea conducida `rp=140 mm` y torque máximo de 3C, `|T1-T2|=635,17 N` es la diferencia **total** de tensiones de los ramales (sumada sobre correas paralelas si hay más de una). La fuerza radial aproximada es `T1+T2`, no la diferencia. Sin pretensión real ni coeficiente de fricción/ángulo de abrazamiento, el valor absoluto sigue indefinido. Se incluyen resultados para razones supuestas `T1/T2` entre 1,5 y 5, explícitamente NO diseñadas ni medidas. Para hallar reacciones también hacen falta `z_A,z_B,z_polea,z_matriz` y orientación horizontal de la correa.

## Materiales y factores de seguridad

Las columnas `n_min_1045...` y `n_min_4140...` son únicamente factores contra fluencia **nominales** condicionados a barras templadas y revenidas de diámetro inicial cercano a 58 mm, de las variantes de ficha:

- Atlas 1045 +QT, diámetro 40–100 mm: `Sy mínimo 370 MPa` según la ficha: https://www.atlassteels.com.au/documents/Atlas1045.pdf
- Ovako 42CrMo4, variante M 6082 +QT diámetro 40–100 mm: `Sy mínimo 650 MPa`. **No es automáticamente toda barra etiquetada “4140”**: https://steelnavigator.ovako.com/steel-grades/42crmo4/

No se asignan propiedades de ese diámetro de barra a la matriz Ø200 mm. No se verifica todavía fatiga, geometría real del chavetero, concentraciones `Kt/Kf`, contacto de matrices perforadas, rodamientos, interferencias ni cumplimiento higiénico.

## Modelo de reacciones por completar

Tomar eje longitudinal z. Dados dos apoyos radiales A y B en `z_A` y `z_B`, una fuerza lateral horizontal `F_P` aplicada en la polea a `z_P` y un momento externo coplanar `M_0` transmitido en la unión superior, las ecuaciones escalares (con signos consistentes) son:

`R_A + R_B + F_P = 0`

`R_B (z_B-z_A) + F_P (z_P-z_A) + M_0 = 0`

Esto se realiza **por cada plano horizontal** y se adicionan las fuerzas laterales y pares de la matriz en sus propias alturas. No se asignan números a `z_A,z_B,z_P` ni se impone que ambos apoyos reciban `F_z` por igual. La reacción axial debe repartirse según el diseño real del apoyo localizador, el apoyo flotante y/o el rodamiento de empuje.

## Matriz perforada: etapa FEM pendiente de datos

La matriz tiene mínimo paso entre centros 12,422 mm; entre orificios Ø6 la separación geométrica es 6,422 mm y entre entradas Ø9 es 3,422 mm, según el mapa geométrico de 4A. No se puede determinar tensión local `von Mises` ni desplazamientos máximos en esos ligamentos por analogía con un disco macizo.

Se requiere un modelo 3D STEP con perforaciones, bocas avellanadas y unión al eje; contacto o amarre justificado solo en superficies realmente restringidas; las cargas puntuales/áreas de los orificios sincronizadas de 3C; análisis de varios instantes críticos; refinamiento local y convergencia de malla. Se deben verificar también fatiga superficial, corrosión, desgaste de la biomasa y fabricación.

## Datos indispensables para cerrar el diseño

1. Corte CAD con las **distancias axiales desde plano medio de la matriz hasta centro de cada rodamiento y polea**, tipo exacto de cada rodamiento, soporte axial y retención en caja.
2. **Detalle de unión matriz–árbol**, chaveta, tornillos, tuercas, hombros, ajuste o interferencia y contacto real Ø58.
3. Poleas y correas exactas (cantidad, sección, separación entre centros, tensado/pretensión o catálogo), orientación del motor y condiciones de montaje.
4. Certificados y tratamiento térmico de los materiales disponibles, y cotizaciones de material, mecanizado y tratamiento para seleccionar el mejor costo.

## Archivos

`resultados/instantes_criticos_correlacionados.csv`, `verificaciones_nominales_eje.csv`, `presion_apoyo_condicional.json`, `transmision_condicional.csv`, `correlacion_cargas.png`, `sensibilidad_eje.png`, `sensibilidad_correas.png`, `dcl_parametrico.png`, `dcl_parametrico.svg`, `resumen_4B.json`.

## Control de potencia y rodamientos

La potencia máxima resistente sincronizada es aproximadamente `4,805 kW` a `516 rpm`. Como comprobación **condicional**, un motor de `5,5 kW` mecánicos y una eficiencia real de transmisión de `90 %` aportarían `4,95 kW`, con un margen instantáneo de `0,145 kW (2,9 %)`. Este margen es pequeño y NO comprueba la idoneidad térmica, la sobrecarga, el arranque, el suministro eléctrico, el tensado ni el factor de servicio de las correas.

El explosionado anterior menciona un rodamiento `6208-2RS`; la ficha SKF de la variante `6208-2RS1` incluye dimensiones `40×80×18 mm`, capacidad dinámica básica de `32,5 kN` y capacidad estática básica de `19 kN`. Esto **NO** significa que pueda aceptar directamente `14,071 kN` axiales: las capacidades C y C0 no son admisibles axiales directos, y se requiere calcular carga equivalente, factor estático, vida, orientación, fijación y apoyo axial real de la instalación. Fuente: https://www.tme.eu/Document/1125278243abb42e990d193517f57632/SKF6208-2RS1.pdf

La vida de fatiga del árbol tampoco se deduce de los factores contra fluencia nominales; a 516 rpm la rotación con flexión puede provocar tensión alternante en puntos materiales. Se evaluará tras definir apoyos y fuerzas laterales, usando concentraciones y el acabado real.
