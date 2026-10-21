# Especificación de futuro FEM de poleas — 5E.1

Estado: **preparación, no ejecutado**. No existen resultados FEM de poleas en
esta etapa. El FEM previo de la matriz perforada no sirve como FEM de poleas.

## Geometría y materiales de entrada

Importar STEP/Inventor de cada polea con revisión y unidades. Conservar cubo,
cuerpo o radios, llanta, tres gargantas, filetes, vaciados y unión al eje.
Verificar volumen, conectividad y ausencia de cuerpos desconectados. Resolver
la diferencia de 0,10 mm exterior CAD frente al perfil tabulado de 5C.
Confirmar espesores bajo raíces de garganta: ni diámetro exterior ni profundidad
tabulada permiten deducir espesor residual de llanta sin su diámetro interior.

Material candidato AISI 1045. Antes del cálculo declarar producto, condición
de suministro/tratamiento y sección de materia prima, fuente o certificado,
E, nu y Sy; para giro/peso, densidad y orientación; para fatiga, Sut y datos S-N,
acabado y espectro. No copiar E/Sy de los escenarios Atlas del eje o la matriz.
Si se emplean elasticidad lineal o sensibilidades, identificarlas explícitamente.

## Casos y transferencia de cargas

Usar `cargas_poleas.csv`, conservando escenario, criterio, paso, ángulo y tiempo.
La motriz recibe su propio torque (radio 50 mm), la conducida radio 140 mm.
Las fuerzas vectoriales heredan el cierre de tensiones condicional de 5D.2;
el equilibrio de torque no certifica esas tensiones ni la adherencia.

Aplicar sobre cada garganta tracciones o contacto correa–garganta que reproduzcan
el vector y momento resultantes de la misma fila. Definir primero la distribución
azimutal/axial y la presión en flancos: las resultantes globales no determinan
una presión local única. La carga por garganta presupone reparto uniforme.
No aplicar simultáneamente fuerzas tangentes que ya generan el torque y un
segundo par equivalente, ni añadir otra fuerza global duplicando las tracciones.
Una fuerza remota más un par equivalente sirve solo para rigidez global; no
valida tensiones en flancos ni raíces de garganta. Evaluar por separado el
motor nominal ideal y los escenarios de pretensión. El CSV heredado de
sensibilidades solo contiene máximos: recuperar los estados correlacionados
de esa sensibilidad antes de usar fuerzas/componentes/torques en FEM.

El marco de 5D.2 tiene x de conducida a motor, y perpendicular, z=x cruz y.
Transformarlo al CAD con una matriz de rotación documentada. Al analizar radios,
referir también la orientación de la polea al instante: las dos poleas giran a
velocidades distintas. La fuerza puede gobernar con una orientación diferente
de radios; estudiar varios ángulos de fase, además del instante de máximo torque.
El ángulo original 3C no es automáticamente el ángulo material de la polea motriz.

La rotación de la polea como sólido genera esfuerzos propios que requieren
densidad/geometría; el peso y esa carga se estudiarán por separado cuando se
confirmen sus datos. No añadir una tensión centrífuga a ramales heredados sin
revisar la convención dinámica para evitar duplicaciones.

## Unión y restricciones

Representar el asiento/cubo y unión realmente diseñados: chaveta, interferencia,
casquillo o pernos, con longitud activa, tolerancias, contacto, fricción o
precarga trazables. Confirmar la retención axial. Si se usa un apoyo ideal para
cribado, etiquetarlo como tal y comparar sensibilidad de rigidez. No empotrar
arbitrariamente todos los nodos del agujero ni atribuir sus picos a una pieza real.
Comprobar que las restricciones eliminan solo movimientos rígidos físicamente
impedidos. Las reacciones internas del modelo de polea no equivalen a reacciones
de los rodamientos del eje vertical.

## Mallado, validación y convergencia

Propuesta de protocolo propio (no instrucción Gates): sólidos 3D, preferentemente
elementos de orden cuadrático; refinamiento local en raíces de garganta, filetes,
uniones radio–cubo/radio–llanta y chavetero. Modelar los radios reales, no esquinas
singulares. Comparar al menos tres mallas con refinamiento documentado y calidad
controlada, además de refinamiento de contacto y tamaño de zona cargada.

Registrar suma de fuerzas y momentos externos/reacciones en un origen común,
residuo del solver, energía de deformación y balance de trabajo. Comparar volumen,
desplazamientos, giro relativo cubo–llanta, tensión nominal de secciones, tensiones
locales en rutas físicas fijas, presiones de contacto y deslizamiento/apertura.
Propuesta preliminar a aprobar: errores de equilibrio relativos <1e-6 y variación
entre las dos mallas más finas <5 % en desplazamiento/giro y tensiones no singulares.
La convergencia de desplazamiento no prueba la convergencia del esfuerzo local.
No declarar convergencia usando solo el máximo nodal de una restricción singular.

## Comparaciones y entrega

Contrastar, cuando aplique, tau del cubo liso T*r/J, sigma_b=Fr*e*r/I,
flujo torsional medio en disco T/(2*pi*r²*t) y corte/contacto medios en una
chaveta confirmada. Son referencias nominales parciales, no validación local.
Cuantificar sensibilidad a carga distribuida, apoyo, fase angular y pretensión.
Entregar CAD, parámetros, versión de solver, mallas, convergencia, reacciones,
mapas y rutas de tensión con unidades. Calcular factores de seguridad solo con
propiedades de condición confirmada, esfuerzos convergidos y criterio aprobado.
La fatiga de radios/cubo bajo carga fija en el espacio exige historia en puntos
materiales y espectro de servicio; una verificación estática no la sustituye.
