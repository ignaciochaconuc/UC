# Optimizador de viajes: primer prototipo

Un modelo entero mixto decide el orden de las ciudades, las noches en cada una, un alojamiento por ciudad y los transportes. Los precios del archivo de ejemplo **son ficticios** y están expresados en una misma moneda ilustrativa.

## Ejecutar

Con Python 3.10 o superior:

```bash
python -m pip install -r requirements.txt
python optimizar.py ejemplo.json
```

En Windows, si `python` abre el alias de Microsoft Store o muestra un error de
acceso, usa el lanzador incluido, que selecciona la instalacion local de Python
y activa UTF-8 para mostrar correctamente acentos y flechas:

```powershell
.\optimizar.cmd ejemplo.json
```

Para guardar además un mapa HTML interactivo de la ruta:

```powershell
.\optimizar.cmd ejemplo.json --mapa mapa_ruta.html --salida resultado.json
```

Cada ciudad necesita `latitud` y `longitud` para aparecer en el mapa. Ábrelo con
doble clic o ejecuta `Start-Process .\mapa_ruta.html` en PowerShell. El fondo de
OpenStreetMap necesita conexión a internet. Las líneas unen las ciudades, pero
no representan el trazado exacto del medio de transporte.

Para minimizar horas con un presupuesto, modifica `"objetivo": "tiempo"` y asigna un número a `presupuesto_maximo`. También puedes pasar `--objetivo tiempo --presupuesto 2500` sin cambiar el archivo. `--salida resultado.json` guarda la solución en JSON.

## Editar un viaje

- `fecha_primera_noche` y `noches`: rango del viaje europeo. El vuelo de ida llega el día de la primera noche; la vuelta sale el día después de la última.
- `ciudades`: indica `obligatoria`, `min_noches`, `max_noches` y hoteles aceptables. Se elige un solo hotel en cada ciudad visitada.
- `vuelos_internacionales`: opciones de entrada (`ida`) y salida (`vuelta`), asociadas a ciudades concretas.
- `traslados`: opciones dirigidas entre ciudades, con medio, duración total estimada puerta a puerta y precio. Si quieres ida y vuelta, agrega ambos sentidos.
- Cada `precio` admite `{"base": 100, "por_fecha": {"2027-05-12": 140}}`. Una fecha no indicada usa `base`; si se omite `base`, la opción solo existe en las fechas de `por_fecha`. Puedes agregar `"no_disponible": ["2027-05-13"]` a una opción.
- `horas_traslado_maximas` y `presupuesto_maximo` aceptan `null` si no quieres imponer ese límite. El modo tiempo exige presupuesto.

El modelo supone como máximo un traslado interurbano por día y ninguna ciudad se visita dos veces. Alojamiento se cobra por noche; el último día se vuelve sin añadir noche. Si no hay solución, revisa primero que existan conexiones y vuelos compatibles con los límites de noches y horas.

**Alcance de esta versión:** solo transporte y alojamiento. No calcula comida, actividades, seguros, equipaje ni traslados locales; agrégalos al presupuesto por separado. La duración de cada opción debe incluir esperas y viajes hasta el alojamiento si quieres limitar tiempo puerta a puerta. Los precios que ingreses son una captura para esas fechas, no una reserva ni una cotización garantizada. No se modelan horarios dentro del día ni combinaciones de vuelos con escalas.

### Formulación resumida

Sea `x[d,c,h]` la elección de hotel en la noche `d`, `a[d,i,j,m]` el desplazamiento entre dos noches consecutivas, `b[c]` y `e[c]` los vuelos de entrada y salida, y `y[c]` la visita a la ciudad. Todas son variables binarias. Una noche debe asignarse exactamente a una ciudad y hotel; la continuidad conecta noches consecutivas; la primera y última ciudad coinciden con los vuelos elegidos. La suma de entradas a una ciudad es `y[c]`, lo que impide volver a visitarla. Las noches están entre mínimo y máximo multiplicados por `y[c]`. La función objetivo suma vuelos, traslados y alojamientos, o bien minimiza horas sujeta al presupuesto.
