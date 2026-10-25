# Etapa 6B — cierre preliminar de uniones (ingeniería básica)

Actualización del 25-10-2026. **No sustituye** los análisis 3C, 3D, 4A–4D ni la transmisión 5F. Se reutilizan resultados correlacionados de `Capstone/` sin reejecutar modelos. Todas las magnitudes de montajes no confirmados permanecen condicionadas.

## Resultados comprobados y decisiones

| Elemento | Resultado o solicitud | Estado |
|---|---|---|
| Eje transversal M24×2 | Reacción transversal máxima ideal por extremo 7,632 kN; momento de empotramiento máximo ideal 255,04 N·m; área resistente de rosca ~384,4 mm² | Verificar contacto, longitud de engrane, precarga cuando corresponda, retención y rigidez del soporte. La carga transversal **no equivale** a tracción de tuerca. |
| Rodamientos exteriores 6206 2RS | 1,6 mm de anillo interior sobre alivio Ø29,2; asiento Ø30 nominal continuo de 14,4/16 mm | Corregir/justificar asiento y hombros antes de validar montaje; la vida calculada en 4A queda condicionada. |
| Matriz–árbol | Torque 3C máximo 88,924 N·m; chaveta candidata 14×9 mm; anillo de apoyo supuesto Ø50/Ø58 | Chaveta para torque + hombro axial + retención positiva independiente; longitud activa y contacto reales pendientes. |
| Apoyos árbol vertical | Empuje máximo 14,071 kN; correa radial condicional 1,170 kN en 5F | Localizador axial + no localizador radial como concepto. No repartir empuje por mitades; faltan posiciones y referencias. |
| Soportes y bastidor | Camino de reacciones identificado | Cierre con cortes CAD, espesores, materiales, uniones y anclajes. |
| Transmisión | Rediseño cubo motriz Ø55/Ø38 propuesto; base ajustable 60 mm | Aún pendientes interferencias/chavetas, ángulo de garganta, radial admisible del motor y bloqueo de la base. |

## Fuente de valores

- [Auditoría 6A](../resultados_integracion/etapa_6a/) y [camino de cargas](../resultados_integracion/etapa_6a/camino_cargas_y_alcance_6b.md).
- [Historial 3C](../Simulación_peletizadora/resultados/etapa_3c_acoplamiento/resultados_estructurales.csv), modelo `3C_inclinacion`, 1440 posiciones.
- [Matriz 4C](../Analisis_matriz_eje_vertical/Etapa_4C_apoyos_union/) y [transmisión 5F](../Transmision/resultados/etapa_5f/).

## Contenido de esta actualización

El archivo `Etapa_6B_cierre_uniones_preliminar.zip` contiene el código Python, memoria técnica, `.tex` para cuerpo y anexo, CSV original de componentes y entradas pendientes. También se incluye un Excel formateado con pestañas «Resumen» y «Detalle completo» y un CSV delimitado por punto y coma compatible con Excel en español.

**No se ha aprobado la fabricación:** faltan los detalles reales de montaje de tuercas M24, asientos Ø30, retención matriz–árbol, apoyos verticales y bastidor.
