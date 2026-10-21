# Revisión conjunta 5E.1 — planos vigentes de ambas poleas

Estado: **preparación, FEM no ejecutado, resistencia no aprobada**.
Fuentes internas: `POLEA 2.pdf` motriz y `POLEA 1 (1).pdf` conducida, una
hoja cada una, cajetines ag_go 21-10-2026; REV vacío, identificar por SHA256.
No mezclar cotas de una pieza con otra ni con revisiones anteriores.

## Geometrías a modelar

Motriz: crestas Ø105,60, pestañas Ø120, fondos Ø78; tres gargantas de 34° ±0,5°,
profundidad radial 13,80. Ocho aberturas circulares Ø13, no ocho radios
rectangulares. Cubo Ø45, agujero R19 (Ø38 derivado), chavetero de ancho
10 JS9 y rosca radial M5x0.8-6H. La pared anular lisa nominal de 3,5 mm no es
el ligamento mínimo real con chavetero: definir profundidad/radios del chavetero
y posición/longitud roscada antes de aceptar integridad del cubo.

En lateral, 54 es ancho exterior entre pestañas, 50 el interior y 2 el espesor
axial de pestaña representada: 54=50+2x2. En A-A, 62 es envolvente axial total
cubo–cara posterior común. Saliente sobre cara exterior: 8 mm; cota 10 lateral
hasta cara interior: 8+2. Las cotas 10 y 12 del corte usan caras interior/exterior
de pestaña y el plano indicado de garganta; no son espesores uniformes de cuerpo
ni longitudes activas de chaveta. Solicitar el CAD para ubicar ese perfil y
las superficies ocultas sin medir píxeles.

Conducida: mantener sin cambios la interpretación vigente de Ø285,60 crestas,
Ø300 pestañas, Ø258 fondos, cuerpo de seis aberturas Ø70, cubo Ø75/Ø35 circular,
envolventes axiales 60/78,60 y M5. Usar el perfil real CAD 34° ±0,5°, con
discrepancia normativa pendiente respecto de 38° de Gates. La motriz coincide
en ángulo nominal de 34° con la tabla de 5C; ello no certifica el resto del perfil.
Los Ø78 y Ø258 son fondos de garganta, no diámetros interiores de llanta.

Para ambas faltan coordenadas y orientación del patrón de aligeramientos,
espesores/perfiles de cuerpo, llanta interior y filetes; no convertirlas a discos
macizos ni repartir cargas arbitrariamente entre supuestos radios iguales.

## Material, cargas y restricciones

AISI 1045 candidato: condición de suministro, producto y propiedades pendientes;
no reutilizar E/Sy del eje o matriz. Antes de resolver aportar E, nu y fuente
trazable, y Sy/Sut para resistencia; densidad para masa, peso y rotación.

Importar las filas correlacionadas de 5D.2 separadas por escenario y polea.
El máximo 3C usa |T|=31,75856 N·m en motriz y 88,92397 N·m en conducida;
el motor nominal ideal usa 36,22147 y 101,42012 N·m. Fuerzas con el marco/signos
de 5D.2, dependientes del cierre simétrico. No aplicar el torque de una polea
a la otra ni usar diámetro de pestañas para el equilibrio de transmisión.

Distribuir contacto/tracciones en cada garganta reproduciendo fuerza y momento,
sin duplicar el par con otra carga equivalente. La distribución local real aún
no está determinada por las resultantes. Sensibilidades de pretensión deben
mantenerse fuera de los casos nominales: recuperar filas completas antes de FEM.

Definir unión eje–cubo según diseño, no por la sola presencia de chavetero/M5.
Modelar longitud activa, ajustes, retención y contacto; no empotrar todo el
agujero como si fuera unión real sin declarar y estudiar esa idealización.
No confundir reacciones de ese modelo con las de rodamientos del eje vertical.

## Convergencia y zonas críticas

Aplicar el protocolo general de `especificacion_fem_poleas.md`: al menos tres
mallas, equilibrio, energía, desplazamiento/giro y tensiones en rutas físicas
no singulares. Refinar raíces de gargantas, pestañas, bordes y ligamentos de
aberturas, uniones cubo–cuerpo–llanta, chaveteros y taladros M5. Comparar fases
angulares de aberturas respecto de cargas; no igualar ángulo de motriz al de 3C.
El anillo liso Ø45/Ø38 y Ø75/Ø35 sirve solo como contraste nominal torsional,
no como FS de los sólidos perforados. Aceptación y fatiga requieren información
de material, geometría local, espectro y criterios de proyecto.

## Entradas para 5E.2 de chavetas/uniones

Confirmar para cada pieza diámetro y tolerancia del eje real compatible con
el agujero, ajuste y zona de contacto, tipo de unión transmisora, dimensiones
de chaveta (b, h, largo activo), profundidades de ambos chaveteros, radios y
altura de contacto efectiva con cada miembro. Motriz solo aporta ancho nominal
10 JS9 de chavetero, sin límites numéricos de tolerancia transcritos. Conducida
no aporta todas esas cotas. Definir material de chaveta y condición, tornillos
M5 (grado, punta, longitud engranada y precarga si aplica), papel de fricción y
retención axial. Las envolventes 62 y 78,60 no fijan el largo activo de chaveta.
