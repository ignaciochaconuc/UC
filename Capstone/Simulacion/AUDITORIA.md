# Auditoría y control de cambios — 19-11-2026

## Estado inicial registrado antes del retiro

Se inventariaron486archivos previos deCapstone, excluyendo cachés. No fue
posible obtener `git status`: el `git.exe` instalado no es un ejecutable
válido para esta plataforma. No se infiere que el worktree esté limpio ni
se modifica Git. El inventario SHA256 es la evidencia de conservación.

Los archivos exactos y tamaños previos están en `control/estado_previo.json`.
`control/plan_de_cambios.json` identifica los39archivos retirados, su destino,
procedencia y propósito. Se trasladó completa la carpetaPrototipo a
`../archivo/Prototipo_escalado_2026_11_18/`, sin borrar sus fuentes,
documentación ni pruebas. No hay eliminación irreversible. Cachés también
viajan con la carpeta pero no forman parte de la línea base científica.

En el proyecto activo se retiraron: configuración con coordenadas×0,5,
runner y adaptación asociados, resultados, tablas/gráficos, comparación y
síntesis derivadas. Las funciones genéricas deEP2siguen siendo la fuente
activa única y no se eliminan. La formulación genérica de presión se migró
sin parametrización hipotética al módulo de verificaciones. Las referencias
verificadas se conservaron también en la bibliografía vigente. Las11pruebas
del prototipo escalado se preservan archivadas, no se ejecutan como pruebas
de validez de la nueva geometría. Las pruebas originales deEP2no cambian.

Para revertir el retiro, primero guardar el aviso actual `Prototipo/README.md`
y trasladar el archivo completo a su ubicación anterior **sin mezclar ni
sobrescribir carpetas**; comprobar hashes del inventario. Esta restauración
es histórica y no convierte el modelo escalado en fuente válida. No se ha
ejecutado ninguna restauración ni limpieza masiva.

## Archivos inspeccionados y decisiones de reutilización

| Subsistema/fuente | Dependencia geométrica encontrada | Decisión |
|---|---|---|
| EP2 `config.py`, `geometria.py`, `cinematica.py` | Matriz200, 102agujeros, diámetro6, rodillos100×40 y centros63,5; CSV/DXF | Conservar intactos; configuraciónnueva explícita y geometríaSTEP |
| `modelos/superposicion.py` | Integral disco–rectángulo y transformación independientes; `limites_huella` usa objeto de parámetros | Reutilizar integral y transformación directamente con límites nuevos, sin leer límites globales |
| `modelos/fuerzas.py`, `modelos/torque.py` | F=pA; T=ΣμFᵢrᵢ; P=Tω genéricos | Reutilizar la integral y funciones de torque/potencia; no cambiar ecuaciones para forzar regresión |
| `simulacion_superposicion.py` | LeePARAMETROSglobal y genera1441filas con extremo duplicado | No importar runner; nuevo orquestador mantiene1440estados y contrasta las primeras1440filas históricas |
| `superposicion_variable.py` y `estructural/acoplamiento.py` | Matemática de huella variable reutilizable; acoplamiento usa globales, orientación y montaje comercial | No trasladar automáticamente3C; referencia histórica queda aparte |
| `config_eje.py`, `geometria_eje.py`, `viga_eb.py` | Nueve tramos/270mm y posiciones en configuración; elemento y ensamblaje son generales | EP2intacto; adaptador compartido recibe segmentos,E,cargas y restricciones explícitas |
| `rodamientos.py` | C/C0yselección6206 globales, pero equivalentes/vida son funciones generales | Reutilizar solo funciones con argumentos; exigir fabricante y condición axial |
| Matriz/eje vertical4A–4D | 4DcodificaR100,H36,bore25,apoyo29 y zona de carga; creaOUTal importar | No importar ni modificar ese runner; apoyos nuevos siguen pendientes |
| Transmisión5A–5F | Catálogo específicoGatesSPA1450rpm/100mm; balance de potencia general | Reutilizar balance con conversión W↔kW; no asignar3SPAal prototipo |
| Prototipo18-11 | Centros escalados y montaje a ras hipotético; casos de presión/velocidad sin ensamble | Retiro reversible completo; no fuente de geometría ni de posiciones nuevas |
| STEP entregados | Matrices, no ensamble | Extraer BRep real, comprobar unidades/clasificación; no deducir rodillos/apoyos |

No se editan módulos generales deEP2para eliminar sus constantes históricas:
sería contrario a su conservación. Se dejan fuera del núcleo activo los
runners que dependen de ellas y se reutilizan las funciones puras por
argumentos. No existen dos implementaciones activas de superposición,
torque, potencia, elemento de viga o vida de rodamientos.

## Auditoría CAD y discrepancias antes de cargas

Se usaOpenCascade7.9.3mediantecadquery-ocp7.9.3.1.1. El lector informa
`millimetre`; la unidad destino se fija aMM. El textoSTEPcontiene también
unidades auxiliares de propiedades/presentación: no se interpretan como
factor de escala del sólido. Se exige un sólido BRep válido.

El marco local de ambas matrices es x=XCAd,y=−ZCAD,z=YCAD, origen en el
eje central próximo al origen mundial, dextrógiro. La transformación exacta
está en cada JSON. No define la orientación del ensamble completo.

El extractor NO recibe102como requisito de clasificación. Agrupa superficies
internas coaxiales y asocia cilindros/conos por centro y eje. Comprueba
vacío axial, continuidad y contornos circulares en ambos extremos. Se
contrasta con cuenta independiente de círculos de borde en planos. Varias
aristas pueden componer una circunferencia: se unen sus intervalos angulares,
sin contar cada arco como otro agujero. Las seis bocas divididas de la matriz
real se resuelven así, no ajustando la cantidad esperada.

| Dimensión | Matriz real | Matriz prototipo |
|---|---:|---:|
| Exterior |200mm|99mm (frente100declarados)|
| Envolvente axial total |36mm|26mm, incluye prolongación central|
| Zona perforada / recorrido de conductos |36mm|10mm|
| Bore central |50mm, perfil recortado compatible con chavetero|13mm|
| Conductos de extrusión independientes |102|102|
| Diámetro efectivo |6mm|6mm|
| Cilindro restrictivo |31,5mm|10mm|
| Lcil/D |5,25|1,6667|
| Bocas/transición |102bocasØ9, cilindro3mm y cono1,5mm|Sin conos detectados;4superficies toroidales de redondeo|
| Distancia mínima de centros |12,422mm|7,360mm|
| Ligamento cilíndrico mínimo |6,422mm|1,360mm|
| Área de conductos efectiva total |2883,982mm²|2883,982mm²|

Las102transiciones cónicas no son102agujeros adicionales. Los dos cilindros
parcialesR0,25del real se informan como superficies auxiliares compatibles
con filetes del cajeado central; no son agujerosØ0,5. Su detalle de unión
queda para revisión. Se conserva inventario de todas las caras y figura
de contornos reales y visualización3Ddel sólido. La triangulación de esa
figura NO es un cálculoFEM.

El ligamento1,36mm del prototipo se comprueba contra duplicados, unidades,
diámetros efectivos y cilindros pasantes. No proviene de una coordenada
comercial escalada. El antiguo0,211mm no describe esteSTEP. No se modificó
CADpara obtener el resultado ni para conservar una cifra deEP2.

Los31,5mm no se declaran longitud equivalente de fricción total: las bocas
y entrada también pueden influir en la extrusión. Sin parámetros de biomasa
no se recalculan44MPani2,26MPaa partir deL/Dsolamente.
