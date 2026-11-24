ANÁLISIS MEF SÓLIDO 3D DE CUADRO DE BICICLETA
Carpeta independiente. Ninguna tarea anterior ni archivo fuente se modifica.

REFERENCIA ÚNICA
El pedido nombraba Ensamblaje 2(1).stp, pero ese archivo no estaba disponible.
El usuario confirmó explícitamente: «el archivo que te subi es el correcto».
Se usó exclusivamente Ensamblaje 2.stp, copiado como referencia_confirmada.stp.
SHA-256: ba2c52efd6c433d9304675e9439e2ed1f717e5a9d8a5371ea77ef2b5c8e2c4b7
No se abrió ni comparó otro STEP anterior. Las imágenes existentes de Inventor
se consultaron sólo como evidencia de cargas y máximos de referencia.

HERRAMIENTAS
Python 3.14, gmsh 4.15.2, cadquery-ocp 7.9.3.1.1, numpy 2.3.4,
scipy 1.17.1, matplotlib 3.10.7; versiones en entorno.json.
Ruta final: CalculiX 2.24 oficial con PARDISO e Intel MKL 2026.2.1, cuatro hilos.
Ejecutables, wheels y procedencia con SHA-256 están en herramientas/.
Descarga oficial: https://www.dhondt.de/calculix_2.24_4win.zip
También se conserva CalculiX 2.23 usado en los ensayos iniciales.
Instalación de módulos si se reproduce en otro entorno:
python -m pip install gmsh==4.15.2 cadquery-ocp==7.9.3.1.1 numpy==2.3.4 scipy==1.17.1 matplotlib==3.10.7

REPRODUCCIÓN (PowerShell, dentro de esta carpeta)
1. python inspeccionar.py
2. python verificar_geometria.py
3. python generar_variantes.py
4. python auditar_variantes.py
5. python validar_solucionador.py
   El runtime MKL ya está extraído en herramientas/mkl_runtime. Si se reconstruye:
   python instalar_mkl.py
   Los wheels provienen de PyPI: mkl 2026.2.1, intel-openmp 2026.2.0, tbb 2023.2.0.
6. Para t=2.0 y h=8, 7 y 6; y para t=2.5, 3.0 con h=8 y 6:
   python mallar_componentes.py 2.0 6 --refine
   python preparar_modelo.py 2.0 6
   python verificar_volumen_malla.py 2.0 6
   python verificar_conectividad.py 2.0 6
   python verificar_pasadores.py 2.0 6
   python resolver.py 2.0 6
   python postprocesar.py 2.0 6
   Cambiar los dos argumentos para cada combinación.
   Excepción documentada para 3,0 mm, h=6: limitar curvatura a 28 puntos:
   python mallar_componentes.py 3.0 6 --refine --curvature 28
   Esa malla reemplaza el intento de 32 puntos detenido por memoria insuficiente.
7. python generar_informe.py
8. Opcional: python revisar_entrega.py (requiere PyMuPDF; versión en entorno.json).

Cada script toma rutas relativas a su propio directorio. Los STEP originales
permanecen intactos. Ejecutar de nuevo reemplaza los productos de esta carpeta.
Los parámetros efectivos están fijados en los scripts; configuracion.json es
un registro descriptivo y no un controlador automático de esos parámetros.
Resolver secuencialmente para limitar memoria. resolver.py usa CalculiX 2.24 y
SOLVER=PARDISO por defecto, con DLL locales y sin modificar PATH del sistema.
--solver direct selecciona SPOOLES; --solver iterative selecciona Cholesky
incompleto. Se conservaron registros de los intentos con alto consumo de
memoria y terminación 0xC0000005; su causa exacta no quedó aislada. El método
iterativo se detuvo sin convergencia y PaStiX no estaba vinculado en el binario,
a pesar de la descripción del paquete. Esos intentos no aportan resultados.

GEOMETRÍA
16 sólidos válidos. Los sólidos 1–12 son tubos de 2,5 mm medidos por pares de
cilindros coaxiales, no por sus nombres. Los sólidos 13 y 14 son remates de
5 mm; 15 y 16, punteras. Se cambian sólo los radios interiores de los tubos.
Se conserva una envolvente exterior por tubo: eliminación del taladro original
y corte coaxial con radio exterior menos el espesor solicitado. La reconstrucción
a 2,5 mm debe recuperar el sólido original antes de aceptar las variantes.
Los cuatro auxiliares se incorporan como los mismos objetos CAD, sin editarlos.
La auditoría de exportación compara superficies analíticas muestreadas y cajas
óptimas, y registra las limitaciones numéricas de operaciones booleanas coincidentes.

CONDICIONES MECÁNICAS
Unidades: mm, N, MPa; densidad 2,7e-9 tonne/mm³ en CalculiX.
Aluminio 6061-T6 isotrópico: E=68900 MPa, nu=0,33, rho=2700 kg/m³,
fluencia nominal de material base=276 MPa en todos los sólidos.
Cargas totales normales compresivas: 600 N en remate 13 y 100 N en remate 14.
No son presiones de 600 y 100 MPa: se integran tracciones sobre sus áreas reales.

La última aclaración del usuario reemplaza la asignación inicial de lados:
puntera derecha, sólido 16 (Z negativo), radial+axial; izquierda, sólido 15
(Z positivo), radial. Agujeros interiores R6 mm; tangencial libre en ambas.
Dirección: radial en las superficies interiores de sus tramos coaxiales 4 y 5;
axial y tangencial libres. Se usan los ejes reales del STEP. Los agujeros de
punteras NO son paralelos; no se sustituyeron por un eje trasero común.

Para un eje unitario a y posición x respecto de su origen o:
er = ((x-o) - a[(x-o)·a]) / norma((x-o) - a[(x-o)·a]).
Restricción radial: er·u=0. Axial adicional: a·u=0.
No se impone u=0 en las tres direcciones ni se modela un pasador como empotramiento.

El usuario confirmó contacto adherido (bonded) en las holguras reales de las
punteras (~0,05 y ~0,10 mm). No se mueven piezas para cerrar esas holguras.
Las uniones se idealizan como adheridas mediante interpolación C3D10 en el
sólido maestro. Las ecuaciones reproducen campos afines, incluidas rotaciones
rígidas infinitesimales, y permiten comprobar la transferencia de momentos.
Las reacciones de restricciones radiales se recuperan con nodos auxiliares sin
elementos; no se confía en RF de nodos físicos sujetos a MPC en coordenadas locales.

En el anillo adherido entre tramos de dirección, la condición radial del borde
esclavo se hereda del maestro para evitar restricciones casi redundantes. Su
residuo se mide explícitamente después de resolver. Se exige <1e-5 mm en ese
anillo y <1e-6 mm en apoyos impuestos directamente. El equilibrio relativo de
fuerzas y momentos debe ser <0,1%. Se rechazan resultados que fallen estos controles.

VERIFICACIONES Y TRAZABILIDAD
inspeccion.json: sólidos, caras, ejes, radios, áreas, volúmenes y hash.
componentes.csv: identificación geométrica de los 16 sólidos y clasificación.
espesores.json y dimensiones_tubos.csv: dimensiones medidas y radios variantes.
contactos.csv: distancias exactas en pares cercanos; los pares separados por
cajas >1 mm conservan una cota inferior, sin presentarla como distancia exacta.
masas_geometricas.csv y comparacion_masas.png: masas CAD, no resultados MEF.
validacion_reconstruccion.json y auditoria_variantes.json: preservación geométrica.
componentes_t.../: BREP, mallas MSH/NPZ por sólido, calidades y selecciones de caras.
modelo.inp, modelo_resumen.json: ecuaciones, apoyos y cargas del solucionador.
estabilidad.json: 96 movimientos rígidos de los 16 cuerpos; rango 90 sin apoyos,
96 con apoyos. Además se comprueba reproducción afín de cada vínculo adherido.
verificacion_cubo/: ensayo de parche independiente con solución analítica conocida.
calculix.log, modelo.dat y modelo.frd: salidas originales del solucionador.
resultados.json: máximos, localizaciones, reacciones, equilibrio y residuos de apoyos.
campos.npz y PNG: campos extraídos de las salidas reales.
informe_MEF_cuadro.pdf: informe universitario con figuras y limitaciones.
comparacion_resultados.csv: tabla final con ambas convenciones de tensión.
reacciones.csv: componentes globales por sólido de apoyo, respecto del origen.
sensibilidad_malla.csv y sensibilidad_por_espesor.csv: estudios de discretización.
diagnostico_maximos.json y detalle_union_critica.png: localización y diagnóstico
del máximo no estabilizado. No se ha aislado una causa única o demostrado una
singularidad analítica; no se oculta la sensibilidad modificando la geometría.
validacion_final.json: controles aprobados en siete cálculos reales y comparación
del caso inicial entre motores/versiones; hash del original intacto.

Los primeros intentos de mallado global y fusión están registrados en los logs;
mallar.py es un ensayo exploratorio rechazado, no la ruta reproducible aceptada.
Los intentos con reacciones mal condicionadas se guardan en rechazado_redundancia/;
sus máximos NO son resultados aceptados. La ruta final usa mallar_componentes.py.

INTERPRETACIÓN
Se informan por separado máximos de von Mises en puntos de integración y máximos
nodales extrapolados/promediados. No son magnitudes idénticas. El factor nominal
conservador utiliza 276 dividido por el mayor de ambos máximos.
Los valores de Inventor 54,71 MPa y 0,4716 mm son referencia preliminar; no se
ajustó E, cargas, geometría ni apoyos para forzar coincidencia.
El tamaño medio 0,015 de Inventor es un parámetro relativo a la dimensión del
modelo según su documentación; no se interpreta como 0,015 mm ni se iguala
directamente con h de Gmsh. La opción de medida por pieza y las adaptaciones
locales originales no están completamente documentadas en las capturas.
La serie de malla compara tres discretizaciones en el caso de 2 mm. Un jacobiano
positivo o equilibrio correcto no demuestran convergencia de máximos de tensión.
Si la tensión local no se estabiliza, no se presenta como un máximo convergido.
Las posiciones de máximos en puntos de integración se acompañan del centroide
del elemento que los contiene, identificado expresamente como tal.

LIMITACIONES
Elasticidad lineal, desplazamientos pequeños, soldaduras adheridas ideales.
No se modelan cordones, zonas afectadas térmicamente ni pérdida de propiedades
por soldadura; 276 MPa sólo define un factor nominal de material base.
No se evalúan fatiga, pandeo local/global ni cargas de impacto. No se indicó
un desplazamiento admisible ni un factor de seguridad mínimo de diseño; por
ello la comparación no certifica un espesor óptimo o la seguridad de una bicicleta.

DOCUMENTACIÓN PRIMARIA CONSULTADA
Autodesk Inventor, Pin Constraint:
https://help.autodesk.com/cloudhelp/2014/ENU/Inventor/files/GUID-2F7EFB6C-C523-419D-A453-CD855DAB4B81.htm
Autodesk Inventor, Mesh Settings:
https://help.autodesk.com/cloudhelp/2022/ENU/Inventor-Help/files/GUID-3B9869A5-578B-456F-9AB4-8EB7AD534A7B.htm
CalculiX, manual: *EQUATION, *STATIC, C3D10 y límites de RF en MPC:
https://www.dhondt.de/ccx_2.22.pdf
Código y distribución Windows:
https://github.com/calculix/CalculiX-Windows
