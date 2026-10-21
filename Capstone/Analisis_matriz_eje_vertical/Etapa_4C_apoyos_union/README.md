# Etapa 4C — Comprobación de cotas, contacto matriz–árbol y apoyos

## Qué se hizo

Se reutilizaron **sin modificar** las 1440 muestras `series_4A_sin_modificar.csv`, generadas a partir de la etapa 3C. El programa `analisis_4C.py` reconstruye en cada ángulo de giro la fuerza normal total, el momento de desbalance y el torque, y desarrolla un análisis de contacto **condicional** para una supuesta cara anular entre Ø50 y Ø58 mm.

**Importante:** no se declara haber resuelto el FEM de la matriz perforada ni la distribución real de momento flector y cortante en el árbol vertical. Ambos requieren el posicionamiento real y la condición axial de los rodamientos, el mecanismo de unión y la carga total de correa.

## Dimensiones actualizadas observadas

- Eje transversal de rodillos: la nueva medida CAD indica **118 mm de distancia mínima entre dos caras anulares Ø40 mm** y **0 mm entre centros de sus ejes geométricos** (caras coaxiales); no demuestra que los rodamientos del árbol VERTICAL estén separados 118 mm.
- `l1=50.3 mm`: desde centro de rodillo hasta la cota de matriz dibujada, compatible con radio 50 mm y holgura 0.3 mm.
- `l2=62.5 mm`: radio de ubicación anotado para el rodillo; **no** distancia axial entre rodamientos.
- `l3=343.3 mm`: referencia vertical desde zona de eje de rodillos hasta parte inferior de polea, **no** claro como distancia entre apoyos radiales.
- Holgura croquis `g=0.3 mm` difiere de la referencia `g=0.1 mm` usada en 3C. Los resultados de 3C permanecen intactos; la diferencia geométrica de longitud de entrada se analiza como sensibilidad.
- Nota de consistencia: el archivo de geometría previa del eje transversal tiene centros de rodillos separados 127 mm (0.1985−0.0715 m), mientras que el nuevo croquis anota 62.5 mm de brazo radial, equivalentes a 125 mm entre centros. Confirmar la versión definitiva antes de modificar el modelo 3A–3D.

## Cargas 3C (inalteradas)

- Máximo Fz = 14070.987 N.
- Máximo torque = 88.923966 N m.
- Máximo momento normal = 153.801516 N m.
- Variaciones y valores correlacionados, disponibles en el archivo `datos`.

## Contacto anular HIPOTÉTICO

**Exclusivamente si** la cara plana anular Ø50–Ø58 mm transmite el total de la fuerza normal y el momento externo de compactación y permanece en contacto elástico completo:

- A = π(ro²−ri²) = 678.584 mm².
- I = π/4(ro⁴−ri⁴) = 248701.041 mm⁴.
- W = I/ro = 8575.898 mm³.
- pmed(t) = Fz(t)/A.
- pmax/min(t) = pmed(t) ± M(t)*1000/W.
- e(t) = M(t)*1000/Fz(t); el valor umbral de ausencia de tracción es ecrit = W/A = 12.638 mm.

El historial da pmax global = 37.382 MPa, pmin global = 0.713 MPa y excentricidad máxima de 12.149 mm; ese valor cercano a ecrit indica muy poco margen geométrico de contacto completo **bajo estas hipótesis**. No es una predicción de presión local ni de deformaciones de perforaciones.

La transmisión del torque **solo por fricción idealizada** requeriría un coeficiente máximo a lo largo del historial ~0.234, usando radio equivalente de 27.049 mm. NO se ha medido ese coeficiente ni la capacidad de una chaveta o retención axial.

## ¿Se pueden obtener reacciones en los rodamientos verticales?

Con los datos disponibles **NO de manera única**: no hay centros zA,zB de los rodamientos del árbol vertical; la imagen de 118 mm es del conjunto transversal. Tampoco se conoce la pretensión y orientación de la correa para obtener su carga radial real. Una polea Ø280 mm solo permite obtener de la carga máxima de 3C la diferencia de tensiones ~635 N, no su suma.

`config_apoyos.json` deja en null las seis entradas requeridas. Si se completan con **datos CAD reales**, el script calcula las reacciones radiales de A y B en los dos planos para cada instante. Modelo de equilibrio, z vertical y positiva hacia arriba, 2 apoyos ideales radiales, fuerza lateral de correa con dirección medida, y momento normal Mx/My reducido en la altura de unión a la matriz:

- ΣFx= RAx+RBx+Fmx+Fbx=0
- ΣFy= RAy+RBy+Fmy+Fby=0
- ΣMy respecto A= (zB-zA)RBx+(zM-zA)Fmx+(zP-zA)Fbx+My=0
- ΣMx respecto A= −(zB-zA)RBy−(zM-zA)Fmy−(zP-zA)Fby+Mx=0

**El resultado no modela** fijación rotacional de apoyos, interacción flexible eje-rodamiento, deflexiones ni flexión interna del árbol escalonado. La componente Fmy de 4A es una aproximación tangencial equivalente; no sustituye todas las cargas laterales reales. Para reacciones AXIALES se necesita especificar qué apoyo es localizador/de empuje y el otro flotante o describir el reparto de rigideces.

## Archivos

- `analisis_4C.py`: ejecutable Python (`numpy`, `pandas`, `matplotlib`).
- `config_apoyos.json`: completar **solo con dimensiones reales**, ninguna inventada.
- `datos/series_4A_sin_modificar.csv`: copia inalterada de 4A.
- `resultados/casos_criticos_union.csv`: datos sincronizados en seis estados críticos.
- `resultados/envolvente_anillo_condicional.csv`: historia de 1440 instantes, presiones y excentricidad.
- `resultados/presiones_anillo_condicional.png` y `excentricidad_vs_limite.png`.
- `resultados/resumen_4C.json`: resultados y estado de apoyos.
- `seccion_informe_4C.tex`: inserción sintética para memoria de cálculo.

## Próximos datos esenciales

1. En un **corte del soporte del árbol vertical**, señalar los centros de los dos rodamientos de ese árbol, el plano medio de la polea y el plano de aplicación equivalente de las cargas de matriz, todos medidos desde un mismo datum (mm).
2. Tipo de rodamientos y cuál absorbe el empuje axial; si ambos deben absorberlo, modelo de precarga/rigidez.
3. Detalle de chaveta, longitud útil, resalte y retención superior de la matriz; especificación de contacto real.
4. Número/sección de correas, distancias, orientación, pretensión o catálogo y condición de tensado.
5. Para FEM definitivo, exportación STEP de matriz y su apoyo/retención con tolerancias y material certificado.
