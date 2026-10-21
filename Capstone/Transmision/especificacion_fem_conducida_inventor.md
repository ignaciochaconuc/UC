# 5E.1 revisión Inventor — polea conducida

Fuente vigente única de geometría: `POLEA 1 (1).pdf`, página 1, dibujante ag_go,
fecha de cajetín 21-10-2026. Fuente interna del equipo; no es norma. El PDF no
declara identificador REV. Registrar SHA256 y mantener separada la línea base.
Este documento complementa el protocolo general de `especificacion_fem_poleas.md`;
las cotas de la conducida de esta revisión prevalecen sobre el inventario anterior.

## Modelo geométrico

Construir **cuerpo aligerado con seis aberturas circulares Ø70** y ligamentos
de ancho variable. No sustituirlo por disco macizo ni por seis vigas rectangulares.
Confirmar coordenadas/diámetro de reparto y patrón angular con CAD original;
no obtenerlos de la escala o píxeles del PDF. Importar STEP/Inventor con unidades.

Conservar crestas Ø285,60, pestañas Ø300 y perfil de tres gargantas de
**34° ±0,5°** y profundidad radial 13,80. El Ø258 oculto coincide con fondo
de garganta, no confirma diámetro interior de llanta. Obtener esa superficie
interior y espesor residual real antes de construir un sólido resistente.
El ángulo de 38° de Gates no se usará para reemplazar el CAD: la discrepancia
34/38 queda como compatibilidad normativa no aprobada.

Cubo Ø75 con agujero circular R17,50 (Ø35 derivado), chavetero visible y rosca
radial M5x0.8-6H. Medir ancho/profundidad/radios del chavetero, longitud efectiva
de contacto, posición y longitud roscada y unión real al eje. La presencia de
M5 no demuestra que el tornillo sea el único transmisor del torque.

78,60 es envolvente axial total del cubo y 60 es envolvente axial de llanta
con pestañas. No son espesor uniforme de cuerpo ni longitud activa de unión.
Las cotas 5 y 23,60 son compatibles con saliente exterior 18,60; no sustituyen
el desfase entre plano efectivo de las tres correas y sección resistente del cubo.
Solicitar perfil y espesor de cuerpo/pestañas, filetes y superficies ocultas.

## Cargas y restricciones

Usar sin reescalar los casos correlacionados de 5D.2: máximo 3C y motor nominal
ideal en filas distintas; sensibilidades de pretensión en archivo separado.
Radio de referencia 140 mm para torque: no usar Ø300 ni Ø285,60. Usar fuerzas
de las correas sobre cada garganta y contacto distribuido, reproduciendo
Fx/Fy/T simultáneos sin duplicar fuerzas/par. Las cargas condicionales existentes
no son una distribución local de presión: esta requiere modelar el contacto.
Definir la unión al eje según montaje real; evitar empotrar todo el agujero
sin declarar y estudiar el efecto de esa idealización.

Mantener AISI 1045 como candidato; E, nu, Sy, Sut y densidad siguen pendientes
de condición/producto y ficha o certificado trazables. No asignar propiedades
de la matriz ni declarar resultados hasta contar con datos.

## Zonas críticas y convergencia

Refinar bordes y ligamentos entre aberturas, unión de ligamentos con llanta y
cubo, raíces y paredes de las tres gargantas, pestañas, escalones del cubo,
chavetero y taladro roscado. Estudiar fase angular de aberturas respecto de carga.
Usar filetes reales. Seguir las tres mallas y controles de equilibrio, energía,
desplazamiento/giro, presión y esfuerzos no singulares del protocolo general.
La torsión de un anillo liso Ø75/Ø35 sirve solo como contraste nominal de
componente torsional; no valida el máximo local ni el FS del modelo perforado.

Estado: **FEM no ejecutado; resistencia y compatibilidad normativa pendientes**.
