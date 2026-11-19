# Prototipo físico — configuración independiente de EP2

Se conserva íntegramente el modelo comercial. Esta carpeta no redefine
`Simulación_peletizadora/config.py` ni escribe resultados en los otros
subsistemas. Los datos nominales proceden de la solicitud del18-11-2026.
La aclaración del equipo permite reconstruir centros de agujeros con escala
0,5 respecto al radio comercial. **No se escalan automáticamente** diámetros
de perforaciones, ancho/diámetro de rodillos, espesor, eje o motor dados
explícitamente. No hay CAD ni registro de compras del prototipo en el repositorio.

## Ejecución

Desde `Capstone/Prototipo`:

```powershell
python -m pip install -r requirements.txt
python simular_prototipo.py
python -m pytest -q
# Pruebas del prototipo y regresión histórica en procesos aislados:
python ejecutar_pruebas.py
# Variante explícita, sin tocar EP2:
python simular_prototipo.py --parametros parametros.json --salida resultados/mi_revision
```

Configuración geométrica y escenarios en `parametros.json`; propiedades
documentadas en `materiales.json`; unidades, fuentes, materialidad y confianza
en [documentacion_parametros.md](documentacion_parametros.md). Referencias
propias en `referencias.bib`, sin alterar bibliografías comerciales. Para
comparar y reproducir los históricos ejecutar sus pruebas en procesos
separados desde sus carpetas, según sus README: no mezclar módulos `config`
de proyectos distintos en un único intérprete.

`resultados/revision_nominal_2026_11_18/` contiene CSV/JSON, el mapa de
perforaciones reconstruido,1440estados angulares, detalle por perforación
comprimido, sensibilidad, figuras y SHA256. Los archivos nuevos son:

- `parametros.json`, `materiales.json`, `reutilizacion.py` y
  `modelo_prototipo.py`: entradas y adaptación parametrizada.
- `simular_prototipo.py`: ejecución, gráficos, comparación y conservación.
- `test_prototipo.py`, `requirements.txt`, `referencias.bib` y esta documentación.
- `ejecutar_pruebas.py`: guarda comandos, salidas y estados en
  `pruebas_ejecutadas.json`, sin regenerar simulaciones comerciales.

No se modifican archivos de los proyectos anteriores. Los resultados
nuevos se generan en esta carpeta; al cambiar hipótesis usar otro destino
para conservar la revisión nominal. Las salidas CSV tienen unidades en
los nombres de sus columnas; todas las ecuaciones se evalúan enSI.

## Reutilización y dependencias

| Modelo existente | Adaptación | Límite |
|---|---|---|
| `modelos/superposicion.py` | Intersección disco–rectángulo y coordenadas locales reutilizadas | Agujeros parcialmente cubiertos, no conteo binario; se reconstruye patrón antes de usarlo |
| `modelos/torque.py` | T=ΣμFᵢrᵢ, P=Tω reutilizadas |μefectivo del torque es hipótesis, no coeficiente de pared validado |
| `estructural/viga_eb.py` | VigaEB reutilizada con secciónM6y longitud100mm; adaptador añade apoyo simple | No usa segmentos270mm, rodamientos6206ni constantes de resistencia4140 |
| `estructural/cargas_eje.py` | Reparto de fuerza/momento entre cada par de apoyos | Posiciones reales ausentes; escenario de rodamientos a ras, no montaje aprobado |
| `estructural/rodamientos.py` | Peq,L10,L10h,S0 y cinemática reutilizados con parámetros explícitos | No usa C/C0del6206; referenciaEZOno necesariamente pieza adquirida |
| Matriz4D comercial | Se revisa, no se ejecuta/importa como prototipo | Espesor36, collar58, bore50, carga y bordes codificados; no válidos para matriz100×10con tuercas |
| Transmisión5A–5F | Se reutilizan conceptos de balance y trazabilidad, no selecciónGates | No se conocen poleas/engranajes/reducción reales; no copiar3SPAni1450/516rpm |
| Acoplamiento3C comercial | No se traslada automáticamente | Pretensión, contacto, soporte y asientos del prototipo sin confirmar; se ejecuta modelo desacoplado de cribado |

Dependencias:NumPy/Pandas, SciPy(viga dispersa), Matplotlib y pytest. El puente
de importación no cambia los objetos comerciales ni ejecuta sus runners.
El FEMcomercial4D crea rutas al importarse; por ello no se usa como biblioteca
del prototipo. Sus validaciones existentes se pueden ejecutar aparte sin
resolver de nuevo sus12casosFEM completos.

## Hipótesis operativas explícitas

Las cargas no son aún estimaciones validadas del prototipo. El escenario de
referencia usa patrón escalado, centro radial31,75mm, rodillos52×30mm,
capa2mm y huella tangencial10mm. Centro/capa son hipótesis de semejanza,
no mediciones. Se calcula cobertura parcial con presión constante2,26MPa,
sin extrapolar el44MPacomercial ni asumir presión experimental. Los
barridos usan1,13/2,26/4,52MPa,μefectivo0,05/0,1/0,2 y capa1/2/4mm.
Cada escenario conserva su identidad; no se mezclan máximos de estados
distintos. No se duplica el extremo360° en los1440intervalos.

La velocidad real de la matriz queda pendiente. El balance usa1350rpm del
motor y reducciones hipotéticas1/2/4/8/16, conηmecánica0,6/0,8/1. Son
escenarios matemáticos, **no una selección de transmisión**. No se utiliza
516rpm ni se aplica la eficiencia eléctrica del motor como pérdida mecánica
adicional. La serie base solo lleva ángulo/paso, sin tiempo real inventado.

## Resultados de referencia condicionados

| Magnitud | Resultado | Interpretación |
|---|---:|---|
| L/D geométrico |1,667| La longitud activa real puede cambiar si existen entradas/alivios |
| Ligamento mínimo entre agujeros |0,211mm| Positivo idealmente, sin tolerancias ni margen resistente acreditados |
| Holgura diametral bore13/árbol12,7 |0,300mm| No define ajuste/centrado correcto |
| Fuerza total máxima /media |734,70 /666,80N| p2,26MPa,capa2mm, patrón y contacto supuestos |
| Torque máximo /medio |2,306 /2,086N·m|μefectivo0,1, sin pérdidas adicionales ni arranque |
| Agujeros activos por rodillo |7–11| Incluye parcialmente cubiertos; no son todos plenamente cargados |
| EsfuerzoM6equivalente, biempotrado |512,4MPa| Nominal lineal, no entalla máxima ni material verificado |
| EsfuerzoM6equivalente, biapoyado |680,0MPa| Misma carga, restricción distinta |
| Flecha lineal biempotrado /biapoyado |0,264 /1,488mm| Ehipotético205GPa; desacoplada del contacto |

Los ligamentos0,211mm hacen prioritario confirmar taladros, tolerancias y
proceso de fabricación; un pequeño error de posición/diámetro puede alterar
su continuidad. No se copian las bocas comercialesØ9mm al prototipo. El
material304previsto no queda confirmado por llamar «inoxidable» a la compra.

La vigaM6usa núcleo de referencia4,773mm deM6×1; paso real pendiente. Los
apoyos en extremos y los centros6,75/29,75/70,25/93,25mm son escenarios
explícitos, no cotas medidas. El modelo omite peso, concentración real de
rosca, precarga, plasticidad, flexibilidadPLA y adaptador. La flecha es
aproximadamente13%/74% de la capa de2mm: **el contacto desacoplado debe
revisarse**, aunqueu/Lno supere el umbral de alerta2% en el caso central.
Ese2%solo es un control numérico de cribado, no criterio normativo de seguridad.
No se adjudica seguridad estática ni fatiga sin grado, montaje y contacto.
Los cocientesSy/sigmade sensibilidad no son factores de seguridad aprobados.

## Motor180W: comprobación, no aprobación

Para el escenario central yηmecánicahipotética0,8 hay144Wdisponibles:

| Reducción hipotética | rpm matriz | Potencia resistente máxima | Margen máximo |
|---|---:|---:|---:|
|1:1|1350|326,1W|−182,1W|
|2:1|675|163,0W|−19,0W|
|4:1|337,5|81,5W|+62,5W|
|8:1|168,75|40,8W|+103,2W|

El límite matemático de reducción en ese escenario seríai≥2,264, **no una
recomendación comercial**: depende de presión, huella, fricción y pérdidas.
No asegura arranque, calidad de pellet, caudal, ausencia de atasco o torque
transmisible por tuercas. La matriz comercial y el prototipo no operan en
condiciones equivalentes; `comparacion_no_equivalente.csv` deja velocidad y
potencia del prototipo sin un único valor ficticio.

## Rodamientos y árbol: qué se obtuvo y qué no

Los608ZZ aportados son8×22×7mm; elM6nominal deja2mmdiametrales de diferencia
(1mmradial ideal), no un asiento válido. Falta adaptador/asiento real,
concentricidad, hombros y retención. `vidas_referencia_EZO.csv` calcula
Peq,S0,L10yL10h conCr3300N/Cor1370NdeEZOidentificado yFa0hipotético;
**no valida la vida de los rodamientos comprados**, su fabricante ni su montaje.
No se reparte fuerza por cuatro: se conserva fuerza y momento en cada par.

`arbol_demanda_nominal.csv` evalúaN/Ay16T/(πd³) y su combinación correlacionada
si la sección transmite toda la demanda. Los núcleos0,75/0,85/1del12,7son
sensibilidades, no pasos ni perfiles normalizados elegidos. Excluye flexión,
entallas, precarga, roscas de tuercas y retención; sin apoyos y paso real no
se declara resistencia del árbol. No se heredan propiedades deSAE4140.

## Pendientes que no se simularon

- **MatrizFEM:** hacen falta apoyo real de tuercas/arandelas, retención,
  contacto, condición de material yνrespaldado. Se reconstruyó el patrón,
  pero no se resolvió unFEMcon bordes inventados ni se transfirió el deEP2.
- **CarcasaPLA:** aclarar si sostiene elM6o los apoyos del árbol. Si cierra
  el camino de compactación es crítica; diámetros100/148no bastan para
  inferir pared uniforme, resistencia o rigidez. Faltan paredes, orientación,
  relleno, filamento, uniones y temperatura/fluencia lenta.
- **TolvaPLA:** requieren masa de biomasa, apoyos y paredes; no asignarle
  la fuerza de compactación automáticamente. Sin esos datos no hayFEMniFS.
- **Uniones por tuercas:** definir contacto, engrane, precarga y mecanismo
  de torque; una fijación apretada no acredita torque transmisible.
- **Presión:** conseguir memoriaEP2y parámetros de biomasa o ensayo de
  extrusión. La función publicada se verificó, el valor2,26MPano.

## Control de calidad y conservación

`historicos_sha256.json` congela todos los archivos anteriores deCapstone
excepto cachés, incluyendo6B. `entradas_prototipo_sha256.json` identifica
configuración, fuentes y código nuevos. La ejecución verifica que ningún
histórico cambió. `validaciones.json` registra equilibrio y1440estados;
`viga_convergencia.csv` contrasta pasos2/1mm y se contrasta cuadratura64/128.
Las diferencias numéricas pequeñas no validan las hipótesis físicas.

La revisión nominal registra204pruebas aprobadas (11prototipo,66contacto/eje/
rodamientos,125transmisión y2auditoría), además de los validadores históricos
4A,4By4D. El de4Dcomprueba malla, elemento y resultados existentes; no
resuelve nuevos casos de la matriz. Las salidas completas se guardan en
`pruebas_ejecutadas.json`. El manifiestoSHA256se comprueba después de las pruebas.

Pruebas nuevas: parámetros/unidades, ligamentos, cobertura parcial,
ecuación de presión con coeficientes sintéticos, soluciones analíticas de
viga, reparto de fuerzas, balance P=Tω, ausencia de516rpmheredadas, bloqueo
de salidas históricas y SHA256. Los resultados físicos siguen condicionados.
