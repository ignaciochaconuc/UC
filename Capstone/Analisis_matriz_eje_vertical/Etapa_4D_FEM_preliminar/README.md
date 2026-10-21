# ETAPA 4D — FEM PRELIMINAR DE LA MATRIZ PERFORADA

**Peletizadora de matriz plana.** Análisis propio por elementos finitos tetraédricos de elasticidad 3D lineal. Los datos de 3C y de 4A se incorporan como copias en `fuentes/` y NO fueron modificados. Esta etapa evalúa la rigidez global y la sensibilidad a las condiciones de borde; **no certifica** la resistencia final ni reemplaza un FEM con geometría completa/contacto.

## 1. Ejecución

```bash
python -m pip install numpy scipy pandas matplotlib
python simulacion_4D.py --paso 5.5 --capas 4
python simulacion_4D.py --paso 4 --capas 4
python validar_4D.py
python resumir_4D.py
```

Los resultados pre-calculados de las tres mallas están contenidos en `resultados/`. Se recomienda ejecutar con `OPENBLAS_NUM_THREADS=1` en equipos con poca RAM. Con un paso de 4 mm y cuatro capas se generan 90.600 tetraedros y 22.615 nodos.

## 2. Datos procedentes de 3C y 4A

- Fuerza axial máxima = **14.070,987 N**; media = 12.398,879 N.
- Torque máximo = **88,923966 N·m**; medio = 77,623586 N·m.
- Máximo momento de las fuerzas normales = **153,801516 N·m**, en 269,25°. Fuerza correlacionada = 12.863,869 N, torque correlacionado = 79,063175 N·m.
- Velocidad = 516 rpm.
- Se importan fuerzas por perforación de los estados `max_fuerza_total` y `max_momento_normales`, no máximos de distintos instantes combinados.

Las coordenadas de los 102 agujeros se importan del CSV extraído de `Simulación_peletizadora.zip`. Las fuerzas en el CSV 4A están en el marco global; para el mallado se asignan a los mismos ID de perforación en el marco giratorio solidario con la matriz, por lo que los resultantes mantienen su magnitud.

## 3. Modelo geométrico FEM

- Disco de Ø200 mm, **espesor 36 mm**; bore central Ø50 mm.
- 102 perforaciones pasantes Ø6 mm ubicadas en los centros CAD.
- No están incluidos el avellanado de entrada **Ø9 mm**, su profundidad, el chavetero, filetes, resalte real, tuerca y pretensión. Los poros se representan con polígonos de 14 lados en las mallas media/fina.
- Malla de triángulos perforados extruida en capas axiales y subdividida en tetraedros lineales de cuatro nodos (P1). Solver CG con precondicionamiento diagonal.
- Propiedades elásticas supuestas para acero: **E=210.000 MPa, ν=0,30**. Unidades coherentes: mm, N y MPa.
- Cargas equivalentes sobre zonas anulares **3 < radio local < 5,5 mm** en cara superior de cada perforación activa. Esta zona de aplicación de carga **es una hipótesis**; no representa una presión de contacto medida ni reproduce directamente las paredes del avellanado. Los pesos y cargas centrífugas se omiten.

## 4. Dos hipótesis de apoyo

1. `EMPOTRADO_ANILLO`: todos los desplazamientos nulos en la cara inferior del collar Ø50/Ø58. Representa una unión idealizada **demasiado rígida**, útil como referencia comparativa.
2. `APOYO_Z_CHAVETA`: desplazamiento vertical nulo en ese mismo anillo inferior y desplazamientos horizontales nulos en un sector del borde del Ø50 (±18°) a modo de soporte tangencial. **No es una chaveta real modelada**; su geometría ni los esfuerzos de corte/aplastamiento de la chaveta están incluidos.

Ambos imponen reacción axial bilateral sobre el anillo, sin contacto unilateral, deslizamiento o apertura. Si aparecen reacciones negativas sobre algunas partes del anillo, la hipótesis requeriría una retención axial/precompresión o un modelo de contacto: **no** interpretar esas reacciones negativas como cargas de diseño definitivas de una tuerca.

## 5. Fórmulas y solución

Se resuelve: K u = f; σ = C ε; ε = (∇u + ∇uᵀ)/2, con material isotrópico lineal. De cada tetraedro se extraen σ_VM y su posición, y de cada nodo u_x,u_y,u_z. El torque resistente se modela distribuyendo componentes tangenciales proporcionales a cada fuerza normal, normalizadas para reproducir exactamente el torque de 3C.

Dos instantes calculados:

| Instante 3C | Fuerza aplicada (N) | Torque aplicado (N·m) | Momento debido a normales (N·m) |
|---|---:|---:|---:|
| Máx. fuerza, 274,25° | 14.070,987 | 88,924 | 131,566 |
| Máx. momento, 269,25° | 12.863,869 | 79,063 | 153,802 |

El mapa de fuerzas de cada agujero se recupera por `id_agujero`; no se sustituye la variación por una única carga puntual global.

## 6. Resultados de la malla más fina (paso nominal 4 mm, 4 capas)

| Caso | Condición de borde | σ_VM máxima (MPa) | máx. |u_z| (mm) | σ_VM máxima fuera de r<34 mm (MPa) |
|---|---|---:|---:|---:|
| Máx. fuerza | Empotramiento ideal de anillo | 51,05 | 0,01182 | 29,91 |
| Máx. fuerza | Apoyo vertical + sector de chaveta | 77,55 | 0,01355 | 37,38 |
| Máx. momento | Empotramiento ideal de anillo | 49,74 | 0,01094 | 25,17 |
| Máx. momento | Apoyo vertical + sector de chaveta | 67,86 | 0,01265 | 31,77 |

`σ_VM máxima` ocurre con singularidades/artefactos posibles cerca de zonas restringidas. No identifica necesariamente el punto crítico real con el chavetero y avellanados modelados.

Reacciones axiales negativas sumadas sobre la superficie inferior (solo **diagnóstico** de la hipótesis de contacto bilateral): 0,374 kN para anillo empotrado y 3,940 kN para apoyo vertical+sector de chaveta en el caso de fuerza máxima. Indican que la cara inferior no puede tratarse sin más como contacto de compresión en toda el área.

## 7. Verificación numérica y sensibilidad de malla

- Conectividad del mallado en planta: una sola región sólida; no hay islas aisladas.
- Volumen discretizado en la malla fina ≈ 959.947 mm³, valor de referencia del disco y perforaciones Ø6 ≈ 956.464 mm³: discrepancia ≈ 0,36 % por discretización de contornos.
- Reproducción de fuerzas y torque de 3C a tolerancia numérica.
- Momento de las normales reconstruido dentro de ≈0,05 N·m de 4A.
- Prueba de deformación afín de elemento tetraédrico de tensión constante superada.
- Equilibrio global y residuo relativo del solver menores a 10⁻⁶ en los 12 casos comparados.
- Entre 5,5 y 4 mm, el desplazamiento máximo cambia aproximadamente 0,5 % (anillo fijo) o 0,9 % (apoyo+sector). Sin embargo, la tensión local máxima sigue siendo sensible al refinamiento y al tamaño/forma de la zona artificialmente restringida.

**Consecuencia:** el desplazamiento del disco es un resultado preliminar útil de rigidez; las tensiones máximas, especialmente en chavetero y puentes avellanados, **no han convergido ni quedan validadas**. No adjudicar un factor de seguridad de diseño a partir de la tensión máxima de esta etapa.

## 8. Materiales y selección

Para comparación *meramente indicativa*, la ficha de Atlas Steels para barra de acero 1045 templada y revenida de diámetro >100 hasta 250 mm indica un límite de fluencia mínimo de **340 MPa**. Si, y solo si, la matriz se fabrica a partir de una materia prima y tratamiento de esa especificación, el cociente **340/77,55 ≈ 4,4** sería una razón nominal de cribado contra fluencia del FEM simplificado. **No es un factor de seguridad aprobado:** faltan chavetero, avellanados, contacto/retención, tolerancias, fatiga y desgaste.

Fuente: Atlas Steels, `Atlas1045.pdf`, https://www.atlassteels.com.au/documents/Atlas1045.pdf (p. 3).

Para 4140/42CrMo4 hay fichas de propiedades por sección y variante, pero no se debe transferir una propiedad de barras Ø40–100 mm a una matriz de Ø200 mm. Fuente: Ovako 42CrMo4 https://steelnavigator.ovako.com/steel-grades/42crmo4/ . El 420 martensítico también requeriría ficha particular y tratamiento térmico documentado. Para elegir material y costo comparar límite de fluencia del material realmente suministrado, endurecimiento superficial, desgaste, higiene, cotización de acero + mecanizado + tratamiento térmico y reemplazo en servicio.

## 9. Siguiente trabajo obligatorio para completar ingeniería de detalle

1. Incorporar en el modelo geométrico avellanados Ø9, ancho/profundidad real del chavetero y filetes.
2. Diseñar hombro y tuerca/placa de retención (posición, precarga, materiales, rosca, posibilidad de desmontaje); usar contacto **sin tracción** con la cara inferior y contactos positivos en la cara de retención.
3. Refinar localmente cerca de los ligamentos avellanados, cubo y chaveta; evaluar **convergencia de σ_VM**, no solo desplazamiento.
4. Comprobar corte/aplastamiento de chaveta, esfuerzos en matriz al lado del chavetero, presión superficial y pérdida de contacto.
5. Diseñar apoyos radiales y rodamiento axial del árbol vertical más adelante; incluir fuerza real de las correas, flexión, fatiga e inestabilidades.
6. Seleccionar material con certificado mecánico de diámetro/espesor y cotizaciones, más análisis de desgaste y corrosión con la biomasa.

**Archivos**: `simulacion_4D.py` (modelo), `validar_4D.py` (pruebas), `resumir_4D.py` (gráficos/tablas), `fuentes/` (copias 3C/4A/CAD), `resultados/*.csv`, `resultados/*.png`, `resultados/malla*.npz`. El archivo `seccion_informe_4D.tex` contiene texto listo para adaptar a Overleaf.
