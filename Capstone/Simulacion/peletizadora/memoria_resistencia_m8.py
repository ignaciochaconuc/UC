"""Documentación de verificaciones justificadas y límites, sin editar informes históricos."""
import json
import pandas as pd
from .informes import guardar_json

def generar(salida,a,c,estaticos,fatiga,apoyos):
    montaje=[
        ('Superficie bajo608','Crestas de roscaM8, sin asiento cilíndrico continuo','Tramo cilíndricoØ8 con ajuste por definir','El bore8 no verifica por sí solo ajuste. Rosca y asiento liso no son equivalentes'),
        ('Sección resistente','Núcleo de referencia6,466mm a todo lo largo','Ø8solo donde exista tramo liso; extremosM8 conservan raíz','No usar8mm en la sección roscada ni trasladar315MPa a166MPa como aprobación del eje completo'),
        ('Rigidez','EI del modelo3C existente','EI escalonado distinto, pendienteslongitudes','Un eje liso requiere geometría y futuro recálculo acoplado; aquí no se cambia3C'),
        ('Concentraciones','Raíz, primera espira, apoyo en crestas y contacto con tuerca','Salida de rosca, hombros y filetes, más raíz de extremos','Kt yKf propios de sección nominal elegida; no duplicar corrección nominal/root'),
        ('Alojamiento exterior608','RodilloCADØ24 frente608Ø22','Misma incompatibilidad aunque se cambie el eje','Redefinir asiento o adaptadorØ24/22 de1mm nominalradial; interferencias/tolerancias y resistencia pendientes'),
        ('Retención axial608','Tuercas/arandelas sin pila axial verificada','Hombros, separadores y extremos roscados por definir','Separadores apoyan sólo anillo interior; no introducir precarga axial por error'),
        ('Capacidad de material','Clase de varilla comprada sólo si certificada','Material de barra/proceso propios','La clase8.8de un producto roscado no se hereda por una barraC45 mecanizada'),
        ('Doble empotramiento','No acreditado por tuercas sobreABS','Tampoco acreditado sólo por tramo liso','Ambos necesitan soportes con capacidad de fuerza, par y rigidez cuantificadas')]
    pd.DataFrame([dict(aspecto=k,varilla_roscada=r,eje_liso_extremos_M8=l,conclusion=v) for k,r,l,v in montaje]).to_csv(salida/'comparacion_montaje_roscado_liso.csv',index=False)
    pd.DataFrame([dict(diametro_raiz_m=.006466,diametro_liso_m=.008,
        I_liso_sobre_I_raiz=(.008/.006466)**4,W_liso_sobre_W_raiz=(.008/.006466)**3,
        sigma_lisa_sobre_sigma_raiz_mismo_momento=(.006466/.008)**3,
        estado='Sólo propiedades de una sección. No representa EI del eje mixto ni resistencia global; extremosM8siguen teniendo raíz y transiciones pendientes.')
    ]).to_csv(salida/'comparacion_secciones_geometricas.csv',index=False)
    cambios=[
        ('P1','Taladros de cámaraØ6','Definir pasos/asientos paraM8sin cambiar centros como primera propuesta; verificar pared y soporte. No basta aumentar nominal a8.'),
        ('P1','Fijación a carcasaABS','Definir apoyo metálico, collar o placas solidarias al bastidor con reacción y par. No presuponer empotramiento de plástico.'),
        ('P1','Asientos interiores608','Definir cuatro tramos lisos, longitudes efectivas, ajustes y alineación, o adaptación independiente documentada.'),
        ('P1','Alojamientos rodillosØ24','Cambiar nominal/asiento de acuerdo con608Ø22 o definir adaptador con ajustes y resistencia.'),
        ('P1','Posiciones axiales','Resolver desfases0,2–0,3mm de asientos y rodamientos; revisar anchos7mm y pila de ambos rodillos.'),
        ('P1','Raíz, transiciones y tuercas','Especificar paso1,25, tolerancia, proceso laminado/cortado, radio raíz, salida de rosca, filetes, longitud engranada y clase de tuercas.'),
        ('P2','Arandelas/placas/separadores','Definir superficies planas, áreas efectivas y distribución de apriete; impedir contacto de separador con anillo exterior o blindaje.'),
        ('P2','Acabado y mantenimiento','Definir rugosidad/asiento y recubrimiento sin asumir equivalencia del10.9bright con8.8zincado; documentar bloqueo y desmontaje.')]
    pd.DataFrame([dict(prioridad=p,elemento=e,modificacion_requerida=m,CAD_editado=False) for p,e,m in cambios]).to_csv(salida/'modificaciones_geometricas_pendientes.csv',index=False)
    pd.DataFrame([
        dict(grado='42CrMo4+QT',producto='NossolDIN976-1, gamaM2–M72; Bonfatti clase8.8y10.9 admite42CrMo4',
            propiedad_documentada='Propiedades mínimas de la clase concreta que se contrate; no resistencia única por nombre42CrMo4',
            Sy_referencia_barra_pa=None,Sut_tipico_barra_pa=None,aplicacion='Candidato comercial material/producto, no selecciona grado de lote ni importa variante4140 histórica'),
        dict(grado='C45 variante047A +N',producto='Ovako, barra redonda normalizada diámetro<10mm',
            propiedad_documentada='Ficha debarra: Sy mínimo320MPa; Rm660MPa es TÍPICO, no mínimo garantizado de varilla',
            Sy_referencia_barra_pa=320e6,Sut_tipico_barra_pa=660e6,aplicacion='Referencia para futuro eje mecanizado; sin geometría completa niFS, no clase8.8automática'),
        dict(grado='Composición no publicada de varillaDIN9768.8/10.9',producto='Böllhoff, acero por clase de producto',
            propiedad_documentada='Mínimos de clase publicados; composición y tratamiento exactos deben quedar en documentación de suministro',
            Sy_referencia_barra_pa=None,Sut_tipico_barra_pa=None,aplicacion='Base de factores condicionados, sin certificado del producto adquirido')
    ]).to_csv(salida/'grados_materiales_vs_productos.csv',index=False)
    texto=r"""% Memoria independiente para incorporación posterior. Requiere amsmath,booktabs,biblatex.
\section{Verificación resistente y montaje del eje transversal M8}
\subsection{Alcance y propiedades}
Se conserva M8 como alternativa preferente, sin aprobar seguridad ni editar geometría.
Se utilizan exclusivamente los1440estados correlacionados por capa del modelo3Cya ejecutado.
No se repite la iteración de contacto ni se modifica la presión, las fuerzas o la holgura convergida.
Se reconstruyen los esfuerzos firmados mediante las funciones y matricesEB de EP2.
El eje permanece fijo: no se supone flexión rotativa completamente alternante.

Se identificaron varillas DIN976M8en clases4.6(norelem),8.8zincada(Böllhoff/norelem)
y10.9bright(Böllhoff)\parencite{boellhoff_varilla_m8_88_2026,boellhoff_varilla_m8_109_2026}.
No se selecciona proveedor ni se acredita el producto adquirido.
Los mínimos publicados por Böllhoff, tabla3.2 basada en ISO898-1\parencite{boellhoff_manual_8100_2023}, son:
\begin{center}\begin{tabular}{lrr}\toprule
Clase&$S_y$ o $R_{p0,2,\min}$ [MPa]&$S_{ut,\min}$ [MPa]\\\midrule
4.6&240&400\\8.8,$d\leq16$mm&640&800\\10.9&940&1040\\\bottomrule
\end{tabular}\end{center}
Una clase de resistencia especifica propiedades de producto; no identifica por sí solaC45,
4140o una condición de barra. El zincado no es grado de acero.
Estas propiedades son condicionales a suministro conforme a la clase y no garantizan fatiga,
geometría de raíz ni resistencia del montaje. La referencia10.9consultada no es zincada.
Nossol documenta varillas en42CrMo4+QT, y Bonfatti admite42CrMo4en productos8.8y10.9\parencite{nossol_materiales_varilla_2026,bonfatti_clases_materiales_2026}:
el nombre del acero no fija una resistencia única. Como referencia alternativa de barra
para mecanizado, OvakoC45variante047A+N, redondo menor que10mm, publica$S_y\geq320$MPa
y$R_m=660$MPa típico\parencite{ovako_C45_normalizado_2026}. No se utiliza ese valor típico para garantizar una varilla o su fatiga,
ni se transfiere la propiedad de barras4140de otro diámetro aM8.

\subsection{Resistencia estática}
Se mantiene el núcleo de referencia$d=6,466$mm. La recuperación de momentos reproduce
los esfuerzos originales3Csin cambios. Para cada sección y estado se conserva la correlación
de ambos planos. El factor de flexión condicional es
\[
n_{y,b}=\frac{S_y}{K_t\sigma_{b,\max}},\qquad
\sigma_b=\frac{32\sqrt{M_Y^2+M_Z^2}}{\pi d^3}.
\]
La flexión superficial y el corte máximo central no se suman como esfuerzos co-localizados.
La precarga axial de montaje no se conoce y no está incluida. Los valores$K_t=1;1,5;2,5$
son referencias nominal y sensibilidades heredadas deEP2, no concentradores identificadosM8.
Se requeriría comprobar raíz, primera espira cargada, apoyo, contacto y salida de rosca,
con$K_t$referido a tensión nominal de raíz para evitar doble contabilización.

\begin{center}\begin{tabular}{lrrrr}\toprule
Clase&Capa[mm]&$K_t=1$&$K_t=1,5$&$K_t=2,5$\\\midrule
"""
    for clase in c['clases']:
        for h in (.001,.002,.004):
            rows=[r for r in estaticos if r['clase']==clase['clase'] and r['capa_m']==h]
            texto+=f"{clase['clase']} & {h*1000:g} & "+' & '.join(f"{r['n_flexion_condicional']:.3f}" for r in rows)+r"\\"+"\n"
    texto+=r"""\bottomrule\end{tabular}\end{center}
Los factores son de flexión condicionada, no factores aprobados del componente.
Si el cociente nominal ya es inferior a uno, el caso no queda justificado ni siquiera sin entalla.

\subsection{Fatiga recuperada de EP2}
Se analizan144fibras fijas y ambos lados de fijaciones y puntos de carga, con contraste72fibras.
Se reutilizan tensión firmada y conteo rainflow periódico de EP2, conservando amplitud,
media y conteo del mismo ciclo. No se convierte una envolvente positiva en alternancia.
El criterio original es
\[
\frac1{n_f}=\frac{K_f\sigma_a}{S_e}
 +\frac{K_t\max(\sigma_m,0)}{S_{ut}},\qquad K_f=1+q(K_t-1).
\]
Se recuperó también Marin, pero no se asignan acabado, confiabilidad, límites de fatiga
ni efecto del recubrimiento que no estén documentados. Una clase8.8o10.9no garantiza$S_e$.
Por tanto, el factor real de fatiga queda pendiente. Se cuantifica el requisito
\[
S_{e,\rm req}=\max_{\rm ciclos}\frac{K_f\sigma_a}
 {1-K_t\max(\sigma_m,0)/S_{ut}}
\]
para$n_f=1$, siempre que el denominador sea positivo; si no, ninguna resistencia a fatiga
finita satisface ese escenario de Goodman. No constituye vida a fatiga ni daño acumulado:
faltan$S_e$,entallas reales y régimen de uso. Los factores de Marin de4140no se transfieren.

\subsection{Empotramientos sobre ABS}
El soporte debe transmitir conjuntamente reacción radial y par flector, no sólo fuerza.
Para un alojamiento corto de diámetro propuesto$d_h$y longitud de paredCAD$t$,
se evalúa como diagnóstico una tracción proyectada firmada lineal
\[
\mathbf p_\pm=\frac{\mathbf R}{d_ht}\pm\frac{6\mathbf M_{\rm conjugada}}{d_ht^2}.
\]
Las fuerzas y pares se combinan en el mismo estado. No es distribución real de presión,
FEM ni admisible deABS; los cambios de signo requieren contacto en lados distintos del bore.
La pared medida corresponde al CADactualØ6, no a una geometríaM8ya aprobada.
No se compara esta tracción con resistencia a tracción de probetas para fabricar unFS.
En el caso4mm las demandas alcanzan aproximadamente457N y8,37Nm por fijación;
el diagnóstico proyectado incorpora el par y es del orden153MPa, frente a8,7MPa
si se ignorase el par. Esto no es prueba de falla deABS ni presión local validada,
pero impide justificar el empotramiento sólo con el promedio$R/(dt)$.
El ABS de diseño presenta proceso, orientación, relleno, paredes y fluencia lenta pendientes.
Se requiere área de reparto, capacidad de par, precarga/retención y rigidez verificadas.

Se realiza una sensibilidad elástica de resortes de traslación y giro con las mismas cargas
congeladas; no se presenta como otro equilibrio3C. El presupuesto de incremento de holgura
$0,05$mm es ilustrativo y no una especificación aprobada. Es necesario ensayar o modelar
las fijaciones reales antes de sustituir el resorte por una propiedad del soporte.
Para4mm, en este cribado, $k_\theta=10^4$Nm/rad con traslación prácticamente fija
limita el incremento a unos0,021mm; $k_v=10^7$N/m con giro prácticamente fijo
lo limita a unos0,046mm. Son ensayos numéricos separados: no se deben combinar
esos dos valores como mínimos simultáneos sin comprobar el presupuesto conjunto.
Una solución a estudiar es descargar fuerza y par en soportes/collares metálicos y bastidor,
evitando atribuir empotramiento sólo a tuercas apretadas contra pared curva deABS.

\subsection{Montaje y conclusión}
La varilla totalmente roscada no ofrece un asiento lisoØ8continuo. El bore608Ø8no acredita
ajuste sobre crestas de rosca ni resistencia a fretting. Un eje lisoØ8con extremosM8mejora
la definición de asiento, pero requiere tramos, radios, salida de rosca y material propios.
Las raíces de extremos mantienen su diámetro resistente: no cabe usarØ8en todo el eje ni
aplicar directamente propiedades de producto8.8a una barra mecanizada.
La rigidez escalonada cambiaría el contacto: las cargas3Cactuales sólo sirven para comparación
condicionada de secciones; una vez definido el eje debe recalcularse su modelo.
Persisten alojamientoØ24frente608Ø22, desfasesaxiales y taladros de cámaraØ6.
Se requiere resolverlos en una propuesta posterior de CAD.

M8se conserva como alternativa preferente, sin aprobación. La clase4.6no cubre el escenario4mm
ni siquiera en flexión nominal;8.8y10.9aportan margen condicionado, pero una clase superior
no resuelve fijaciónABS, asiento608o fatiga desconocida. El montaje sobre tramo liso y
soporte metálico merece estudiarse antes de aprobar la varilla totalmente roscada sobre plástico.
"""
    (salida/'memoria_resistencia_y_montaje_M8.tex').write_text(texto,encoding='utf-8')
    import re
    raiz=salida.parents[2]
    bibliografia=(raiz/'fisica/referencias_resistencia_m8.bib').read_text(encoding='utf-8')
    (salida/'referencias_reutilizables.bib').write_text(bibliografia,encoding='utf-8')
    fuentes={
        'fecha_consulta':'2026-11-20',
        'propiedades_producto':{'url':'https://eshop-tr.boellhoff.com/out/media/pdf/the_manual_of_fastening__8100-en.pdf','localizador':'Tabla3.2, edición8; tabla publicada/indexada revisada, no texto completoISO898-1','acceso':'Lector web inicial disponible; relecturas y descarga local devolvieron timeout/403'},
        'producto8_8':{'url':'https://eshop.boellhoff.de/out/media/pdf/DIN_976_A_Stahl_8.8_gv___en.pdf','localizador':'PDFp1 filaM8, paso1,25, zincado'},
        'producto10_9':{'url':'https://eshop.boellhoff.de/out/media/pdf/DIN_976_A_Stahl_10.9___en.pdf','localizador':'PDFp1 filaM8, paso1,25, bright'},
        'producto4_6':{'fuente':'norelem07640, ficha oficial DIN976-1, PDFpp1–2 indexadas','referencia':'07640-081M8x1000 acero4.6zincado;07640-0838.8zincado','nota':'No sustituir acero4.6por4.8'},
        'grado42CrMo4':{'url':'https://www.nossolgmbh.de/htmlgb/produkt_01.html','localizador':'DIN976-1,M2–M72, materiales42CrMo4+QT y42CrMoS4+QT'},
        'clase_vs_grado':{'url':'https://www.bonfattifilettature.it/en/threaded-rods-2/','localizador':'Apartados8.8y10.9;42CrMo4en ambos; requisitos mecánicos por clase'},
        'barraC45':{'url':'https://steelnavigator.ovako.com/steel-grades/c45/','localizador':'TablaMechanicalProperties,047A,+N,Roundbar,<10mm,Sy320mínimo,Rm660típico','limite':'Referencia de barra normalizada, no claseISO898 ni varilla adquirida'},
        'EZO608':{'url':'https://www.ezo-brg.co.jp/english/product/spec.php?eid=00913','dimensiones_mm':[8,22,7],'nota':'Referencia, no fabricante adquirido. Ajustes y hombros se deben verificar para variante real.'},
        'procedimiento_EP2':'estructural/resistencia_fatiga.py: tension_flexion_punto,contar_rainflow,factor_goodman,Marin; no se ejecuta su runner ni sus propiedades4140',
        'concentradores':'Sólo sensibilidadesEP2; faltan perfil/raíz/proceso y primera espira. No atribuir estosKt a un catálogo deM8.',
        'propiedades_ABS':'fisica/ABS_referencia.json: probetas específicas, no valores garantizados de un soporte fabricado'
    }
    guardar_json(salida/'fuentes_documentales.json',fuentes)
    (salida/'LEEME.txt').write_text("""Resistencia y montajeM8 — revisión20-11-2026
Desde Capstone/Simulacion: python verificar_m8.py
Pruebas: python herramientas/pruebas_resistencia_m8.py
Sólo se postprocesan3series3Cexistentes de1440estados. No se llama a simular().
Factores estáticos: cocientes de flexión condicionados a mínimos de clase yKt supuestos;
no FS del producto adquirido ni de la fijación. Fatiga: rainflow real del historial y
Se requerido; FS real queda nulo por falta deSe ynotchas reales.
La rigidez de fijaciones se explora con cargas congeladas, no se cambia3C.
MomentoM_Y_A es conjugado al giro del planoY y corresponde a eje globalZ;
M_Z_A es conjugado al giro del planoZ y corresponde a eje global-Y.
La memoriaLaTeX es un archivo de inclusión posterior, no compilado aquí.
Referencias verificadas en fuentes_documentales.json y referencias_reutilizables.bib.
No se modificaCAD, EP2, fuentes originales ni resultados históricos.
""",encoding='utf-8')
