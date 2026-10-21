ETAPA 4A — MATRIZ Y ÁRBOL PRINCIPAL — INGENIERÍA DE SOLUCIÓN

Propósito
  Extiende la etapa 3C sin modificarla, exportando 1440 estados correlacionados
  de fuerza, momento y torque sobre la matriz, distribución por orificio
  en eventos críticos, y tensiones NOMINALES paramétricas del eje vertical.

Ejecución (Windows/Colab, Python 3.11+)
  1. Descomprime el ZIP original Simulación_peletizadora.zip.
  2. Instala numpy, pandas, matplotlib.
  3. Ejecuta desde la carpeta de este archivo:
     python simulacion_matriz_eje_4A.py --proyecto "RUTA/Simulación_peletizadora" --salida resultados
  4. Opcional: python crear_dcl.py
  NO es necesario recalcular las etapas 3A, 3B ni 3C.

Archivos
  simulacion_matriz_eje_4A.py : código de postproceso
  crear_dcl.py : esquema de cargas/reacciones no especificadas
  seccion_informe_etapa_4A.tex : sección LaTeX para informe (con ecuaciones)
  resultados/historial_cargas_y_momentos.png : carga vs ángulo
  resultados/mapa_max_fuerza_total.png : distribución de fuerza por perforación
  resultados/mapa_max_momento_normales.png : idem estado de momento extremo
  resultados/dcl_provisionales_matriz_arbol.png : bosquejo de los DCL simbólicos
  resultados/series_resultantes_matriz_eje.csv : 1440 valores correlacionados
  resultados/casos_criticos_correlacionados.csv : estados de máximos sin mezclarlos
  resultados/fuerzas_por_agujero_casos_criticos.csv : cargas por canal en cuatro estados
  resultados/secciones_eje_nominales.csv : barrido paramétrico de diámetros
  resultados/geometria_perforada.json : puentes mínimos y área aproximada
  resultados/informe_resultados.md : memoria preliminar y pendientes

CRÍTICO — LÍMITES DE INTERPRETACIÓN
  - NO ES UNA SIMULACIÓN POR ELEMENTOS FINITOS, ni sustituye FEA/DEM.
  - No se ha justificado apoyo radial/axial, unión matriz/eje, geometría de
    contacto claveta/chavetero, ni cargas laterales de las correas.
  - No se pueden certificar flechas de la matriz, tensiones locales de sus
    perforaciones ni resistencia a fatiga/fluencia global del árbol.
  - Las tensiones de secciones sólidas lisas son sensibilidad exclusivamente
    a F axial, torque, y por separado hipótesis de MOMENTO COMPLETO pasando
    por la sección, NO un momento interno resuelto por equilibrio de apoyos.
  - Los n nominales de materiales son números condicionados a estado térmico,
    tipo y tamaño de producto y no califican la pieza real.
  - En los mapas, el tono significa fuerza aplicada al agujero, NO tensión.
  - Masa del disco ignora avellanados y chavetero: solo orientación.
  - La ficha del acero 4140 utilizada corresponde a Ovako variante 6115 +QT
    en barras redondas 25--60 mm, NO demuestra propiedades de matriz Ø200 mm.

FUENTES DE PROPIEDADES CONDICIONALES
  https://atlassteels.com.au/documents/Atlas1045.pdf
  https://steelnavigator.ovako.com/steel-grades/42crmo4/
  Matriz: 420 tratable térmicamente como opción de estudio;
  https://www.atlassteels.com.au/documents/Atlas%20Grade%20datasheet%20420%20rev%20May%202008.pdf

SIGUIENTE ETAPA REQUERIDA
  Confirmar superficie de apoyo bajo la matriz, fijación axial (hombro,
  brida, tornillos), ubicación y tipo de rodamientos radial/axial,
  medidas del chavetero, y las tensiones/dirección de correas.
  Con esos datos sí se define una simulación FEM 3D y el cálculo combinado
  definitivo del árbol y la selección por factor de seguridad y costos.
