# 5E.2-B — Motor comercial y unión con polea motriz

Se consultan las fichas oficiales de BEVI 121165 y Marathon
6RN132S04E30U24B3641-A el 21-10-2026. No se selecciona motor ni se
reemplaza el modelo de 5,5 kW/1450 rpm de 5A–5D. La transcripción y sus
campos pendientes están en parametros_motores.json; las fuentes se registran
en referencias.bib sin duplicar entradas. No se adoptan datos de otros
motores, montajes ni tamaños IEC por semejanza de carcasa.

## Evidencia comercial y límites de acceso

BEVI: ficha oficial, secciones de dimensiones del eje y datos 50 Hz.
Publica D38, E80, F10, GA41 y DH M12x28; montaje B3/B14, 1470 rpm,
5,5 kW y eficiencia eléctrica nominal 89,8 %. GA se conserva como cota
identificada por el fabricante, no como profundidad inferida sin esquema.
No se certifican tolerancias, altura de chaveta, radios, longitud útil o
capacidad radial a partir de esa tabla.

Marathon: contenido indexado de la página oficial consultado; petición
directa devuelve HTTP403. La ficha identifica extensión 80 y diámetro38,
eje con chaveta, B14 y velocidad nominal1475 rpm (no los1500 del título).
El enlace Outline6RN132S04E30_3641-A está anunciado pero no fue inspeccionado.
Se mantienen nulos ancho, profundidades, tolerancias, retención y hombros.
Los datos indexados deben ratificarse con revisión del plano del proveedor.
No se atribuye automáticamente el ancho10 al motor por compartir Ø38.

## Comprobaciones reproducibles

La comparación nominal reutiliza comprobar_eje_real. Igualdad Ø38 solo
demuestra coincidencia nominal; no define ajuste, interferencia ni juego.
Para BEVI F10 coincide nominalmente con el ancho CAD10 JS9; faltan
tolerancias y contacto. La candidata Ganter10×8 para d38 se conserva como
candidata de diseño, no como chaveta confirmada del motor comercial.

Cabida axial necesaria: extensión−envolvente =80−62=18 mm. No es holgura
axial instalada ni longitud activa de chaveta. Sin una posición del cubo,
su solape con tramo cilíndrico útil es desconocido. Si se proporciona inicio
z desde el hombro, se comprueba z>=0 y z+62<=80, todavía sin aprobar radios,
chaflanes, contacto, acceso de montaje ni retención. El tornillo axial BEVI
publicado permite estudiar una retención, no la dimensiona; el M5 radial CAD
no adquiere capacidad de torque ni retención por esta comparación.

Las diferencias con1450 son +20 rpm (1,37931 %) y +25 rpm (1,72414 %).
No se reejecuta geometría, velocidad de correas, capacidad Gates, tensado ni
torque histórico. Las rpm nominales tampoco aseguran velocidad exacta bajo
la carga real. A50Hz/cuatro polos la velocidad síncrona es1500; se distingue
de los valores nominales bajo carga publicados.

## Carga radial: comprobación preparada, pendiente

Se importan sin alterar los casos correlacionados del resumen5D.2:
máximo3C condicional1169,5243206 N; motor nominal ideal histórico1171,2498986 N.
No se mezclan con sensibilidades de pretensión de sensibilidad_Ts.csv, que
permanece como fuente separada. Son resultantes en la polea bajo la hipótesis
simétrica previa, no reacciones calculadas dentro del motor ni capacidades.

Para cada motor se necesita tabla o aprobación escrita del fabricante para
el punto de aplicación y referencia axial exactos, rpm, orientación, vida,
rodamientos y combinación de cargas. Se necesita plano de montaje que ubique
el plano resultante de tres gargantas; no se supone a mitad de los62 o80 mm.
También faltan masa/centro de gravedad de polea, dirección de gravedad y
otras acciones. No se convierte carga de correas en carga total de apoyo.

La función comprobar_carga_radial solo compara F/F_adm cuando hay fuente,
distancia coincidente, referencia axial y condiciones verificadas. No
interpela ni extrapola el catálogo, no inventa momento aplicado y no calcula
factor de seguridad. Incluso esa comparación de correas no aprueba montaje.
Ambas capacidades comerciales permanecen null. Para cambios de velocidad se
requiere una revisión nueva, sin sobrescribir los resultados anteriores.

## Eficiencias, montaje y continuidad

La eficiencia eléctrica es salida mecánica/entrada eléctrica. La eficiencia
de correas es salida mecánica de transmisión/entrada mecánica de transmisión.
No son intercambiables: no se reduce nuevamente por eficiencia eléctrica la
potencia de salida nominal5,5kW. No se usa la cifra89,8/89,6% como rendimiento
de correas. Tampoco se confunde el factor de servicio comercial del motor
con el factor1,3 de dimensionamiento de correas.

B3/B14 de BEVI y B14 de este Marathon no se consideran montajes idénticos.
La base móvil prevista en5C necesita confirmar patas, brida, fijaciones,
alineación y ajuste. Confirmar red disponible y conexión nominal; las fichas
publican tensiones distintas y no se presume instalación eléctrica compatible.

Se importan literalmente ligamentos Ø45/50/55/60 desde5E.2-A. Puede seguirse
el predimensionamiento de Ø55 en copia CAD con Ø38 provisional, sin aprobarlo:
faltan coordenadas de ocho aberturas, radios, espesores, material/condición
1045, largo activo, ajuste, chaveta, retención y carga admisible del motor.
No se cambia CAD ni parámetros históricos, no se ejecuta FEM, no se asignan
propiedades o factores de seguridad y no se selecciona motor.

Se guardan fuentes transcritas, resultados y requisitos; SHA256 cubre los
históricos, parámetros, planos y códigos. La reproducción es local y no
depende de acceso web. El hash de la transcripción no equivale a hash de un
PDF comercial descargado; no se presenta ningún outline no consultado como
evidencia dimensional verificada.
