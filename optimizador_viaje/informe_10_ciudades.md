# Simulación de 10 ciudades — marzo de 2027

Consulta realizada el 27 de septiembre de 2026. Esta es una prueba de escala del
modelo, no una cotización reservable.

## Supuestos

- Primera noche: 1 de marzo de 2027; regreso: 31 de marzo de 2027.
- Cuatro adultos y dos habitaciones dobles.
- Los días indicados por el usuario se interpretan como noches: 30 en total.
- Todos los importes se normalizan a EUR y representan el total del grupo.
- Hoteles de categoría media estimada; no se seleccionaron propiedades reales.
- Las duraciones de vuelos son estimaciones puerta a puerta cuando corresponde.
- Solo se cargó una red pequeña de conexiones plausibles, no todos los pares de ciudades.

## Resultado de costo mínimo

Ruta: Santiago → Madrid → Sevilla → Barcelona → Londres → París → Berlín →
Praga → Zagreb → Milán → Roma → Santiago.

- Alojamiento estimado: 8.164 EUR.
- Transporte estimado: 6.423 EUR.
- Total: 14.587 EUR (3.646,75 EUR por persona).
- Traslados: 85,5 horas, incluidos vuelos internacionales.

## Resultado de tiempo mínimo con presupuesto de 15.000 EUR

Ruta: Santiago → Madrid → Sevilla → Barcelona → Londres → París → Berlín →
Praga → Milán → Zagreb → Roma → Santiago.

- Total: 14.959 EUR.
- Traslados: 81 horas.

## Fuentes utilizadas como referencias

- [Air Europa: Santiago–Madrid](https://www.aireuropa.com/es-cl/ofertas-de-vuelos-a-madrid):
  referencia publicada para salida el 1 de marzo de 2027; el sitio advierte que
  la tarifa puede dejar de estar disponible y que pueden aplicarse extras.
- [COCHA: multidestino Santiago–Madrid–Roma–Santiago](https://www.cocha.com/vuelos/multidestino/santiago/madrid/roma):
  referencias mensuales alrededor de CLP 1,219 millones por persona para marzo
  de 2027. No apareció una combinación exacta 1–31 de marzo.
- [Trivago: Madrid](https://www.trivago.es/es/odr/hoteles-madrid-espa%C3%B1a?search=200-13628):
  promedio publicado de 184 EUR por habitación para marzo de 2027.
- [HotelMonitor: París](https://hotelmonitor.co.uk/hotels/paris/march-2027):
  promedio publicado de 109 GBP por habitación para marzo de 2027.
- [SNCF Connect: Barcelona–París](https://www.sncf-connect.com/en-en/train/route/barcelona/paris):
  desde 69 EUR por persona y aproximadamente 6 h 50 min; se usó una referencia
  conservadora de 79 EUR por persona.
- [Eurostar: París–Londres](https://www.eurostar.com/uk-en/train/paris-to-london):
  desde 39 GBP por persona y 2 h 17 min de viaje; el modelo incorpora margen de
  llegada, seguridad y embarque.
- [Deutsche Bahn: Berlín–Praga](https://www.bahn.de/reisen/view/verbindung/berlin/prag.shtml):
  referencias desde 19,98–49,99 EUR y viajes directos cercanos a cuatro horas.
- [HŽPP: Zagreb–Praga](https://www.hzpp.hr/en/international/prague):
  desde 57 EUR por persona; se usó como referencia también en sentido Praga–Zagreb.
- [FlixBus: Zagreb–Milán](https://global.flixbus.com/bus-routes/bus-zagreb-milan):
  desde 34,98 EUR y duración mínima publicada de 8 h 50 min.
- [Trenitalia: Milán–Roma](https://www.trenitalia.com/it/frecciarossa/collegamenti-frecciarossa/viaggia-tra-roma-e-milano-con-frecciarossa.app.html):
  servicios de alta velocidad cercanos a tres horas; el precio usado es una
  estimación y debe cotizarse para la fecha concreta.

## Advertencias

Los precios de Sevilla, Barcelona, Berlín, Praga, Londres, Milán, Roma y Zagreb
son referencias conservadoras de mercado, no resultados de disponibilidad de
dos habitaciones concretas. Las tarifas internacionales se dividieron entre ida
y vuelta para adaptarlas al modelo actual. Antes de reservar hay que volver a
cotizar la combinación multidestino completa, confirmar equipaje, impuestos,
cancelación y capacidad para cuatro adultos.
