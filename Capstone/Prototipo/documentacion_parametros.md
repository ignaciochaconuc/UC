# Parámetros y materialidad — 18-11-2026

Unidades internas SI: m,N,Pa,N·m,W,s; coordenadas de archivos geométricos enmm.
El archivo `parametros.json` es la única configuración del prototipo. Los
valores de materiales y sus fuentes están en `materiales.json`; no son
certificados de compra. No había configuración previa de prototipo en las
carpetas revisadas. La actualización6B es del diseño comercial y no se altera.

## Valores nominales aportados y reconstrucción

| Parámetro | Valor | Unidad | Fuente | Confianza / uso |
|---|---:|---|---|---|
| Diámetro matriz |100|mm| Solicitud equipo | Nominal, pendiente medición |
| Espesor matriz |10|mm| Solicitud equipo | No es reducción homotética de36mm |
| Perforaciones / diámetro |102 /6|1 /mm| Solicitud equipo | Diámetro NO escalado |
| Bore central |≈13|mm| Solicitud equipo | Aproximado, no ajuste certificado |
| L/D geométrico |1,6667|1|10/6, calculado| No prueba presión de extrusión; falta longitud activa real |
| Centros de102agujeros |coordenadasEP2×0,5|mm| Aclaración expresa del equipo| Reconstrucción, no CAD medido |
| Diámetro / ancho rodillos |52 /30|mm| Solicitud equipo| No escalar a50/20 por analogía |
| Centro radial de rodillos |31,75|mm|63,5mm comercial×0,5| Hipótesis de semejanza, pendiente verificar montaje |
| Capa de biomasa de referencia |2|mm|4mm comercial×0,5| Escenario, sensibilidad1/2/4mm; no densidad o compactación medidas |
| Longitud tangencial de contacto |10|mm|sqrt(52×2−2²)| Geometría de escenario, no huella observada |
| Eje transversal |M6;L100|mm| Solicitud equipo| Paso y calidad desconocidos |
| NúcleoM6 de escenario |4,773|mm|TRFastenings, filaM6×1| Perfil de referencia, no medición; no tolerancia mínima garantizada |
| Posiciones de cuatro rodamientos |6,75 /29,75 /70,25 /93,25|mm| Rodillos centrados simétricos en eje100; dos608a ras de cada ancho30| Hipótesis de ensamblaje, no montaje confirmado |
| Árbol principal |12,7|mm| Solicitud equipo| Varilla1/2pulgada, no asumirUNC niM12 |
| Reducciones de núcleo para cribado árbol |0,75 /0,85 /1|1| Sensibilidad del analista| No son dimensiones normalizadas ni medidas de rosca |
| Rodamientos |4×608ZZ,8×22×7|mm| Adquiridos según equipo| Sin fabricante/comprobante incorporado |
| Motor |1LA7063-4AB10;180W;1350rpm|W/rpm| Solicitud equipo| Sin ficha oficial accesible ni placa incorporada |
| Alimentación motor |trifásico230/400|V| Solicitud equipo| Confirmar conexión y red; no simulación eléctrica |
| Reducción real |pendiente|1| No aportada| Escenarios1/2/4/8/16, no diseño seleccionado |
| Eficiencia mecánica |0,6 /0,8 /1|1| Sensibilidad| No eficiencia eléctrica ni pérdidas medidas |
| Presión preliminar |2,26|MPa| Equipo atribuye aEP2| Escenario NO calibrado, barrido1,13/2,26/4,52MPa |
| mu efectivo de torque |0,05 /0,1 /0,2|1| Sensibilidad alrededor de hipótesis comercial| No coeficiente de pared del modelo de extrusión |
| Carcasa |100/148|mm| Solicitud equipo| Diámetros de referencia, no espesor de pared comprobado |
| Tolva diámetro máximo |200|mm| Solicitud equipo| Faltan espesor y carga de biomasa |

## Materiales, propiedades y confianza

| Material/escenario | E | ν | Densidad | Fluencia / resistencia | Fuente y condición | Uso permitido |
|---|---|---|---|---|---|---|
| Core304/1.4301 de referencia |200GPa|Pendiente|7900kg/m³|Rp0,2=210MPa;Rm520–720MPa|Outokumpu Core, tablas5/7,p8/10; productos planosH/P a20°C| Referencia para el304previsto; no propiedades de rodillo/barra desconocida ni certificado del inoxidable comprado |
| Varillas zincadas adquiridas |Pendiente|Pendiente|Pendiente|Grado/Sy/Sut pendientes|Sin proveedor/documento local| Zincado es recubrimiento, no grado |
| Sensibilidad elástica varilla |180 /205 /220GPa|No requerido por vigaEB|No se usa peso desconocido|Sy hipotético200/400/600MPa|Escenarios numéricos propios;205GPa coincide con referencia elástica del modelo previo, NO identifica esta varilla| Comparar demanda y sensibilidad; cocienteSy/sigma no esFSaprobado |
| PLA de carcasa/tolva |Pendiente|Pendiente|Pendiente|Pendiente|PrusamentPLA v1.1 ilustra probetas/proceso, no producto adquirido| Ninguna asignación isótropa garantizada; requiere filamento, paredes, capas, relleno y ensayos |

No se asignan curvas de fatiga al304,PLA ni varillas. No se transfieren
Marin,Goodman,Kt/Kf ni propiedades del4140comercial al prototipo. La
resistencia de tuercas y transmisión por apriete sigue pendiente de contacto,
material, engrane, fricción y precarga justificados.

Todas las fuentes externas se consultaron el18-11-2026; URLs,títulos,
condición y límites se conservan en `materiales.json` y `referencias.bib`.
La tabla EZO608ZZ (Cr3300N/Cor1370N) sirve solo como referencia de fabricante
identificable: no se atribuyen esas capacidades a la marca comprada desconocida.

## Revisión de presión

Se verificó en el postprint de Stelte etal.,Fuel2011,DOI
10.1016/j.fuel.2011.05.011, ecuaciones1–2:

`Px = PN0/νLR * [exp(4 μpared νLR L_activa/D) − 1]`.

La función `presion_canal` exige esos parámetros explícitos; no se invoca
para fabricar un valor de presión por defecto. FaltanPN0,μpared,νLR y
calibración para biomasa/humedad/temperatura/granulometría del prototipo.
νLR es de biomasa, no Poisson del304;μpared tampoco esμefectivo del torque.
No se verificó que ésta sea la fórmula usada en la memoriaEP2 original,
que no está incorporada. Por ello2,26MPa permanece como dato preliminar del
equipo, no resultado confirmado de la bibliografía ni presión experimental.
Un L/Dmenor no basta para garantizar calidad de pellet o potencia de arranque.
