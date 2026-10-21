# 5E.2-A — Alternativas del cubo motriz, no modificación del CAD

Se leen la revisión conjunta vigente 5E.1, los parámetros y resultados 5E.2
y los planos internos POLEA 2.pdf / POLEA 1 (1).pdf. Se conserva agujero
nominal 38 mm, candidata alta 10×8 y ocho aberturas Ø13. El cubo actual
sigue siendo Ø45; Ø50/55/60 son escenarios independientes. AISI 1045 no
tiene condición ni propiedades mecánicas asignadas.

## Geometría y unidades

Se reutiliza `transmision.chavetas.ligamento_cubo`, sin duplicar ecuaciones.
Con D exterior, d agujero, b ancho y q profundidad desde la tangente del
agujero al fondo plano (todo en mm):

- Pared lisa = (D−d)/2.
- Ligamento central = D/2−(d/2+q).
- Ligamento radial de esquina ideal = D/2−sqrt((b/2)²+(d/2+q)²).

q=3,3 y 3,5 mm corresponden al nominal y extremo superior del extracto
Ganter DIN 6885-1 para d38. No son profundidades CAD ya confirmadas.
No se incluyen radios, tolerancias de agujero/ancho/diámetro exterior ni
el taladro M5: los resultados son cribado, no espesor resistente mínimo.
Un valor negativo atraviesa la envolvente; cero no deja material.

Para un centro real (x,y) de abertura Ø13, la separación proyectada a un
cubo circular es sqrt(x²+y²)−D/2−6,5. Es una distancia firmada de cribado:
la tangencia ocurre a radios de centros 29 / 31,5 / 34 / 36,5 mm para
D=45/50/55/60. No se prescribe holgura mínima. Una separación negativa
indica invasión de envolventes en proyección; la interferencia 3D depende
del solapamiento axial real. Incluso una separación positiva no acredita
la resistencia del cuerpo ni sus transiciones. Las ocho coordenadas y
extensiones axiales faltan; no se deducen de píxeles ni simetría aparente.

## Cargas y verificaciones separadas

Se importan literalmente los casos correlacionados de 5E.2 procedentes de
5D.2; no se regenera ninguna etapa. Se conservan escenario máximo 3C y
motor nominal ideal separados (31,758559 / 36,221470 N·m; fuerza en unión
1671,503 / 1906,393 N). No se confunde fuerza tangencial en agujero con
fuerza lateral de correas. Las sensibilidades de pretensión previas no se
fusionan con estos escenarios ni se usan para aprobar el cubo.

Ampliar D manteniendo d y torque no cambia F=2T/d. La chaveta requiere
longitud activa real, alturas portantes, profundidades, radios y materiales
para usar tau=F/(b L) y p=F/(h_contacto L), ya implementadas en 5E.2.
La envolvente axial 62 mm no equivale a longitud activa. El cubo requiere
además comprobar sección debilitada, entallas, M5, contacto y unión con
cuerpo bajo cargas combinadas; no lo sustituye la torsión de anillo liso.

## Alternativas investigadas y alcance

El extracto Ganter DIN 6885-2, fila d38, indica b10/h8, profundidad en cubo
2,1 (+0,2) y en eje 6 (+0,2) mm. La posición radial es distinta de la forma
alta. Reduce invasión del cubo pero profundiza el eje; no puede sustituirse
sin rediseñar ambos mecanizados y verificar el eje real y contacto. No
se declara equivalente, conforme ni resistente. Fuente consultada:
https://live-katalog.ganternorm.com/pdf/ganter/en/6885-2.pdf?dispositiontype=attachment

Como familia comercial alternativa se revisó RINGFEDER RfN 7012, fijación
por fricción, no autocentrante y con necesidad de centrado previo según
fabricante. No es otra chaveta normalizada ni se confirma talla para Ø38.
Requiere catálogo de tamaño exacto, presiones admisibles, envolvente y
material del cubo/eje, cargas combinadas y procedimiento de montaje.
No se asigna torque transmisible a esa alternativa ni al M5 existente.
Fuente: https://www.ringfeder.com/products/locking-assemblies/rfn-7012/

## Prioridad de estudio, no selección

Estudiar primero Ø55 en una copia de Inventor: reserva geométrica intermedia
y menor ocupación que Ø60. Ø50 minimiza ampliación; Ø60 maximiza reserva
entre los ensayados pero ocupa más zona del cuerpo. No existe criterio
resistente validado para elegir entre ellos: revisar centros de aberturas,
eje real, radios, pared local, montaje y materiales antes de decidir.
Ninguna alternativa queda aprobada. No se ejecuta FEM ni se cambia CAD.

La ejecución guarda parámetros, ligamentos, interferencias pendientes,
alternativas, cargas y requisitos con SHA256 de fuentes e históricos.
