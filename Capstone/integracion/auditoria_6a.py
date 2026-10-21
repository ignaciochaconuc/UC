"""Auditoría documental 6A. Sin simulaciones ni modificación de subsistemas."""
import csv
import hashlib
import json
from pathlib import Path

RAIZ=Path(__file__).resolve().parents[1]
SALIDA=RAIZ/'resultados_integracion/etapa_6a'
S='Simulación_peletizadora'
V='Analisis_matriz_eje_vertical'
T='Transmision'


def inventario():
    filas=[]
    def item(id,nombre,evidencia,funcion,cargas,geometria,hecho,falta,importancia,decision,datos,fuentes):
        filas.append(dict(id=id,componente=nombre,evidencia=evidencia,funcion_mecanica=funcion,
            acciones=cargas,geometria_disponible=geometria,verificaciones_realizadas=hecho,
            verificaciones_faltantes=falta,importancia=importancia,clasificacion=decision,
            datos_necesarios=datos,fuentes=fuentes))
    item('C01','Rodillos y alojamiento de rodamientos','plano y modelo',
        'Compactar biomasa y transmitir reacción a pistas y eje fijo',
        'Normales y tangenciales3C; peso estimado; no empuje axial documentado',
        'Ø99,99; ancho40; alojamientosØ62, profundidad16 por lado; agujeroØ56',
        'Contacto2C/3C, masa estimada, giro; no resistencia local del rodillo',
        'Comprobar hombros/pared de alojamientos y continuidad de reacción; confirmar retención de pistas',
        'Alta: asiento y giro de rodillos','basica_condicionada_a_montaje',
        'Corte ensamblado, tolerancias, hombros, radios, ajuste, material/condición y volumen CAD',
        [f'{S}/Plano_rodillo.png',f'{S}/README.md'])
    item('C02','Cuatro KOYO/JTEKT6206 2RS de rodillos','selección documentada; montaje incompleto',
        'Permitir giro del rodillo sobre eje transversal estacionario',
        'Historias individuales radiales4A; Fa=0 provisional, no evidencia de empuje',
        '30×62×16; centros59,5/83,5/186,5/210,5mm; no confundir con apoyos verticales',
        'Equivalentes, S0 y L10/L10h; mínimo nominal aproximado8531h; no requisito obligatorio10000h',
        'Montaje, desalineación admisible, holgura, ajustes, retención, servicio y vida objetivo',
        'Alta: montaje puede invalidar vida calculada','revision_geometrica_previa',
        'Planos de conjunto, holgura interna, límites fabricante y tolerancias; régimen real',
        [f'{S}/README.md',f'{S}/resultados/etapa_4a_rodamientos_rodillos/resumen_rodamientos_nominal.csv'])
    item('C03','Asientos exterioresØ30 y aliviosØ29,2','plano y modelo, incompatibilidad documentada',
        'Apoyar anillos interiores exteriores sin carga de borde no justificada',
        'Cargas radiales individuales4A, no carga axial de tuerca',
        'Rodamiento izq51,5–67,5, asiento53,1–91,5; der202,5–218,5, asiento178,5–216,9mm; exceso1,6mm por lado sobre alivio',
        'Incompatibilidad identificada, no aprobación del voladizo',
        'Confirmar ancho útil apoyado/hombro y admisibilidad o corregir posiciones/asientos',
        'Crítica: contacto y montaje','revision_geometrica_previa',
        'Detalle axial y radios admisibles del rodamiento, tolerancias, intención del alivio; consulta fabricante si se conserva',
        [f'{S}/Plano_eje_transversal.png',f'{S}/estructural/config_eje.py',f'{S}/README.md'])
    item('C04','Eje transversal escalonado','plano y modelos3A–3D',
        'Recibir cargas de rodamientos y transferirlas a soportes extremos',
        'Flexión en dos planos, cortante y pesos; reacciones y momentos correlacionados3C',
        'L270; Ø30/36; extremosM24×2 equivalentesØ21,5463 en modelo',
        'Rigidez3A/B, acoplamiento3C, estática/fatiga3D con entallas y material condicionales',
        'Validar restricción real y entallas/raíz; certificado del material. No repetir viga antes de definir montaje',
        'Crítica: rigidez afecta holgura y cargas','basica_prioritaria',
        'Montaje de extremos, material comprado/diámetro de suministro y radios reales; no trasladar factores condicionales como aprobación',
        [f'{S}/README.md',f'{S}/resultados/etapa_3d_resistencia_fatiga/resumen_factores_seguridad.csv'])
    item('C05','Roscas M24×2 y tuercas del eje transversal','roscas dibujadas; tuercas y función exacta no confirmadas',
        'Posible fijación/retención del eje en soporte; no se acredita que compriman pistas o generen el empotramiento',
        'Solo acciones obtenidas del DCL real: precarga si existe y esfuerzos de fijación. Fr del rodillo es transversal al eje, NO axial sobre tuerca por defecto',
        'Plano:2×M24×2-6g, tramos extremos29mm; longitud engranada real y tuerca sin especificar',
        '3A/3D usan sección equivalente en flexión; NO verifican filetes, arrancamiento, tuerca ni apriete',
        'Definir función, precarga si requerida, tracción/arrancamiento de ambos roscados, contacto de apoyo y retención contra aflojamiento',
        'Crítica: puede invalidar empotramiento y resistencia existente','basica_prioritaria_tras_definir_union',
        'Corte con soporte/hombros; norma y material tuerca, altura, engrane útil descontando chaflanes, arandela/contacto, fricción y método de bloqueo/apriete',
        [f'{S}/Plano_eje_transversal.png',f'{S}/README.md',f'{S}/resultados/etapa_3c_acoplamiento/resultados_estructurales.csv'])
    item('C06','Soportes/paredes y unión del eje transversal','empotramientos modelados; unión física sin detalle verificable',
        'Cerrar fuerzas y momentos de extremos hacia estructura',
        'Reacciones y pares3C sincronizados;3A-D es envolvente artificial separada',
        'Sin espesores, ancho de apoyo, luz de soporte ni patrón de fijación confirmados',
        'Equilibrio de viga ideal; no rigidez/capacidad de unión',
        'DCL de unión, capacidad de apoyo/cortante/momento y rigidez compatible con empotramiento',
        'Crítica: condición de borde gobierna3C/3D','basica_prioritaria',
        'Corte, espesor/material pared, contacto eje-soporte, tornillos/soldaduras si existen, distancias y brazo resistente',
        [f'{S}/resultados/etapa_3c_acoplamiento/resultados_estructurales.csv',f'{S}/README.md'])
    item('C07','Matriz perforada','plano/DXF y FEM histórico simplificado',
        'Recibir compactación y llevar normal, momento y torque a unión con árbol',
        'Fz,T,M de4A correlacionados; no combinar máximos de distintos instantes',
        'Ø200, espesor36, agujeroØ50;102 perforacionesØ6 y entradasØ9',
        '4D existente: rigidez y sensibilidad de borde; máximos locales no convergidos ni geometría completa',
        'Antes del cierre: justificar apoyo/material y no declarar resistencia aprobada; FEM local con avellanados es detalle si no se reivindica seguridad final',
        'Alta: apoyo puede modificar conclusión resistente','basica_definir_apoyo_detalle_local_diferible',
        'Geometría de unión/retención, condición y sección de material; radios/chavetero/avellanados para futuro detalle',
        [f'{S}/Plano_matriz.png',f'{V}/Etapa_4D_FEM_preliminar/README.md'])
    item('C08','Unión matriz–árbol y retención axial','resalte observado en documentación; mecanismo de unión pendiente',
        'Transmitir Fz, momento y torque; centrar y retener matriz sin apertura no controlada',
        '4C contacto anular hipotético50/58; fricción sola no confirmada; reacciones negativas4D son diagnóstico, NO carga de una tuerca',
        'Bore matrizØ50, resalteØ58 y referencia axial12 en4B; contacto real no confirmado; chavetero visible en plano de matriz no define chaveta completa',
        '4C presión/excentricidad condicional;4D apoyo bilateral, no retención real',
        'Definir unión; equilibrio y contacto unilateral/retención, torque por elemento real, corte/aplastamiento si chaveta',
        'Crítica: camino de cargas incompleto','basica_prioritaria',
        'Corte ensamblado, plano de tope y área real, chaveta/ajuste, retención superior y precarga si existe, materiales y longitudes activas',
        [f'{V}/Etapa_4B_matriz_arbol_condicional/README.md',f'{V}/Etapa_4C_apoyos_union/README.md',f'{V}/Etapa_4D_FEM_preliminar/README.md',f'{S}/Plano_matriz.png'])
    item('C09','Árbol vertical y apoyos radiales/axiales','árbol modelado nominalmente; apoyos sin posición confirmada',
        'Transmitir torque y conducir Fz/laterales a carcasa y estructura',
        'Matriz Fz/T/M y fuerza de polea5D.2 condicional; reparto axial depende de apoyo localizador',
        'Config4C zA,zB,zM,zP nulos;118mm documentados son caras del eje transversal, NO vano vertical',
        '4A/B secciones lisas/sensibilidades; NO diagrama real del árbol con apoyos y correa',
        'Resolver reacciones y empuje con geometría real; verificar selección de rodamientos, retención y sección gobernante',
        'Crítica: puede cambiar selección de apoyos/árbol','basica_prioritaria_tras_geometria',
        'Centros axiales, diámetro y tipo real de rodamientos, apoyo localizador/flotante, orientación global y plano de polea; pesos',
        [f'{V}/Etapa_4C_apoyos_union/config_apoyos.json',f'{V}/Etapa_4B_matriz_arbol_condicional/README.md',f'{T}/resultados/etapa_5f/interfaz_eje_vertical.json'])
    item('C10','6208-2RS mencionado para árbol vertical','mención documental de explosionado; no selección verificada',
        'Posible apoyo del árbol, función axial por definir',
        'Cargas combinadas futuras, no aplicar Fz total como admisible axial',
        '4B cita ficha SKF6208-2RS1; no demuestra variante realmente montada',
        'Ficha citada, sin carga equivalente/vida del montaje real',
        'Confirmar tipo, orientación, Fa/Fr, retención, P/P0 y vida con servicio definido',
        'Crítica: no hay selección axial justificada','basica_prioritaria_tras_geometria',
        'Plano y referencia comercial, admisibles/factores del fabricante, función localizador/flotante y vida requerida',
        [f'{V}/Etapa_4B_matriz_arbol_condicional/README.md'])
    item('C11','Poleas y uniones polea–eje','planos vigentes y propuesta diferenciados',
        'Transmitir torque y carga de correas a ejes',
        '3C y nominal motor separados5D.2; fuerzas laterales condicionales',
        'Motriz CAD45/38, propuesta55/38; conducida75/35;M5 radial; candidata10×8',
        '5E geometría/ligamentos/nominales;5F cierre no aprobación',
        'Resolver cubo original incompatible, interferencias55, chaveta activa, ajuste y retención. No atribuir torque alM5',
        'Crítica: puede impedir montaje o transmisión','basica_prioritaria_acotada',
        'Geometría real de aligeramientos, largos/contacto chaveta, radios y materiales; no otro barrido de cubos',
        [f'{T}/resultados/etapa_5f/resumen_integral.json',f'{T}/parametros_poleas.json'])
    item('C12','Motor y carga radial admisible','dos candidatos comerciales, ninguno seleccionado',
        'Entregar potencia y soportar polea en eje de salida',
        'Fuerza de correas heredada1169,524N3C y1171,250N nominal externo; no cargas totales de motor',
        'Ejes nominales38×80; cubo envolvente62; BEVI ancho10 confirmado, Marathon pendiente',
        '5E.2-B compatibilidad nominal; no admisible radial',
        'Confirmar montaje/punto de aplicación y capacidad radial del fabricante',
        'Alta: puede cambiar motor/montaje','basica_consulta_fabricante',
        'Plano específico, distancia de aplicación, peso polea, vida, orientación y tabla de capacidad',
        [f'{T}/resultados/etapa_5e2b/resumen.json'])
    item('C13','Base móvil de motor y fijaciones','propuesta5C, no conjunto dimensionado',
        'Guiar ajuste y bloquear motor contra acciones de correas',
        'Resultante correas en motor y peso real; no obtener carga de perno dividiendo sin DCL',
        'Recorrido25+35=60mm; patrón B3 o B14 por confirmar; sin pernos/ranuras/material definidos',
        'Geometría de ajuste, no capacidad de bloqueo',
        'Predimensionar bloqueo y apoyo si define viabilidad; roscas/ranuras finales en detalle',
        'Alta: pérdida de tensado o desplazamiento','basica_envolvente_fijacion_detalle_final',
        'Motor confirmado, montaje, masa, puntos de anclaje, guías, bloqueo, espesor y material base',
        [f'{T}/resultados/etapa_5c/resumen.json',f'{T}/resultados/etapa_5e2b/resumen.json'])
    item('C14','Bastidor, carcasa y anclajes','necesarios por equilibrio, geometría no verificada en fuentes revisadas',
        'Cerrar el lazo de carga matriz–rodillos y motor hacia estructura/fundación',
        'Fuerzas/pares de soportes y motor; cargas internas no deben sumarse dos veces como externas',
        'No plano completo de perfiles, uniones, soldaduras o anclajes confirmable en los archivos revisados',
        'No cálculo de estructura documentado',
        'Definir esquema y comprobar camino global/rigidez local antes de atribuir empotramientos; detalles de cordones/anclajes después',
        'Crítica: no existe cierre resistente del lazo','basica_prioritaria_esquema',
        'Ensamble general, perfiles/espesores/materiales, apoyos al suelo, uniones reales y coordenadas',
        [f'{S}/README.md',f'{V}/Etapa_4C_apoyos_union/README.md',f'{T}/resultados/etapa_5f/resumen_integral.json'])
    item('C15','Arandelas, seguros, pasadores, tornillos y soldaduras no detallados','no confirmados como piezas instaladas',
        'Posibles medios de reparto, retención o fijación; función a identificar en cada unión real',
        'Solo las que asigne el DCL del montaje, no cargas inventadas',
        'Sin cantidad/clase/diámetro/posición confirmados salvo roscasM24 yM5 ya inventariadas',
        'No comprobación individual documentada',
        'Identificar en BOM/cortes; calcular solo los que cierren caminos críticos, no inventar fijaciones',
        'Depende de función; alta si soporta reacción/retención','revision_documental_y_detalle_condicionado',
        'Lista de materiales y cortes con función, geometría, material, cantidad y montaje',
        [f'{S}/Plano_eje_transversal.png',f'{T}/parametros_poleas.json'])
    item('C16','Resguardos y protección de puntos de atrapamiento','necesidad documentada, solución no definida',
        'Impedir acceso a correas/poleas y partes giratorias',
        'Acceso, mantenimiento, posibles proyecciones; no energía de impacto inventada',
        'Sin envolvente/material/fijaciones confirmados',
        'Pendiente en5F',
        'Definir concepto de resguardo y mantenimiento antes del cierre; detalle constructivo después',
        'Crítica para seguridad de operación','basica_conceptual_detalle_constructivo',
        'Envolvente del conjunto, acceso, anclajes, procedimiento de parada y evaluación de riesgos',
        [f'{T}/resultados/etapa_5f/pendientes_priorizados.csv'])
    return filas


def ejecutar(salida=SALIDA):
    salida=Path(salida).resolve()
    if salida!=SALIDA.resolve() and (salida.is_relative_to(RAIZ.resolve()) or salida in RAIZ.resolve().parents):
        raise ValueError('Salida exclusiva6A o temporal externo')
    entradas=[f for carpeta in (S,V,T) for f in (RAIZ/carpeta).rglob('*') if f.is_file()
              and not any(k in f.parts for k in ('__pycache__','.pytest_cache'))]
    entradas += [Path(__file__),Path(__file__).with_name('camino_cargas_6a.md')]
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    filas=inventario()
    for fila in filas:
        for f in fila['fuentes']:
            if not (RAIZ/f).is_file():
                raise ValueError(f'Fuente no encontrada: {f}')
    prioridades=[
        ('P0','Congelar configuración de montaje','C03,C05,C06,C08,C09,C14','Obtener cortes/datum/BOM antes de nuevos cálculos; revisar alivio1,6mm y confirmar contacto de tuercas','Bloquea montaje y definición de cargas','Revisión geométrica, no simulación'),
        ('P1','Unión transversal yM24','C04,C05,C06','DCL de soporte con reacciones y pares correlacionados3C; precarga si función la exige, rosca/tuerca y presión de apoyo; rigidez suficiente','Empotramiento ideal gobierna holgura, cargas y fatiga existentes','Cálculo básico de unión; no convertir Fr en Fa'),
        ('P1','Unión matriz–árbol y retención','C07,C08','Contacto/retención axial y transmisión de torque con mecanismo confirmado','Apoyo bilateral4D no es contacto real ni tuerca diseñada','Equilibrio/contacto simplificado justificado; FEM local diferible'),
        ('P1','Apoyos del árbol vertical','C09,C10','Tras definir zA/zB/zM/zP, DCL3D, reparto axial y selección/verificación de apoyo crítico','Puede cambiar tipo de rodamiento y eje;C/C0 no son admisibles axiales','Usar interfaz5F y estados simultáneos, sin rehacer contacto'),
        ('P1','Cierre básico del soporte estructural','C06,C14','Camino global y rigidez/capacidad local de soportes y uniones principales','No se justifica empotramiento ni soporte de empuje sin estructura','Modelo estático básico y envolvente, no FEM completo'),
        ('P2','Bloqueos de transmisión ya detectados','C11,C12,C13','Confirmar admisible radial motor, interferencia cubo55, chaveta/retención y bloqueo de base','Pueden cambiar selección o impedir montaje','No repetir5E; completar solo datos y comprobación gobernante'),
        ('P2','Seguridad conceptual','C16','Definir resguardos, acceso y procedimiento seguro','Necesario antes de afirmar operación segura','Evaluación conceptual, sin cálculo de impacto sin datos')]
    pendientes=[dict(prioridad=p,trabajo=n,componentes=ids,alcance=a,justificacion=j,limite=l)
                for p,n,ids,a,j,l in prioridades]
    matriz=[{k:r[k] for k in ('id','componente','verificaciones_realizadas','verificaciones_faltantes','clasificacion','importancia','fuentes')} for r in filas]
    datos=[dict(id=r['id'],componente=r['componente'],datos_necesarios=r['datos_necesarios'],fuentes=r['fuentes']) for r in filas]
    # Lectura documental de consistencia, sin alterar ni resolver ningún modelo.
    def leer_csv(p):
        with p.open(encoding='utf-8',newline='') as f:
            return list(csv.DictReader(f))
    serie=[r for r in leer_csv(RAIZ/S/'resultados/etapa_3c_acoplamiento/series_temporales_acopladas.csv') if r['modelo']=='inclinacion']
    maximo=max(float(r['fuerza_total_n']) for r in serie)
    c4=json.loads((RAIZ/V/'Etapa_4C_apoyos_union/resultados/resumen_4C.json').read_text(encoding='utf-8'))
    resumen={'etapa':'6A','tipo':'auditoria documental, sin nuevas simulaciones','componentes':filas,
        'prioridades':pendientes,'nuevos_factores_seguridad':None,'fem_ejecutado':False,'cad_modificado':False,
        'hallazgo_consistencia':{'estados_serie_actual':len(serie),'maximo_serie_3c_n':maximo,
            'maximo_copia4c_n':c4['Fz_max_N'],'nota':'Coinciden archivos actuales; advertencia14071,128N del README del subsistema vertical no se reproduce en esta lectura. No editar históricos ni asumir que toda copia restante queda validada.'},
        'alcance_6b':pendientes[:5],
        'condicion_inicio_6b':'Primero cortes de montaje y resolución geométrica; si no hay datos, entregar requisitos pendientes y no fabricar precargas o fijaciones.',
        'diferible':'Convergencia FEM local completa, optimización, detalles finales de ranuras/cordones, vida ajustada y desgaste experimental; no usarlos para declarar aprobación existente.',
        'estado':'Auditoría completa; cierre resistente y de montaje no aprobado por omisiones esenciales.'}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,obj in (('inventario_componentes',filas),('resumen_auditoria',resumen),('trazabilidad_sha256',hashes)):
        (salida/f'{nombre}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    for nombre,rows in (('inventario_componentes',filas),('matriz_verificaciones',matriz),('calculos_adicionales_priorizados',pendientes),('datos_necesarios',datos)):
        with (salida/f'{nombre}.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
            w.writerows([{k:'; '.join(v) if isinstance(v,list) else v for k,v in r.items()} for r in rows])
    (salida/'camino_cargas_y_alcance_6b.md').write_text(Path(__file__).with_name('camino_cargas_6a.md').read_text(encoding='utf-8'),encoding='utf-8')
    if not all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items()):
        raise RuntimeError('Archivo histórico modificado')
    (salida/'validacion_conservacion.json').write_text(json.dumps({'entradas':len(hashes),'sha256_conservados':True,'simulaciones_ejecutadas':False},indent=2),encoding='utf-8')
    return resumen


if __name__=='__main__':
    r=ejecutar()
    print(json.dumps({'componentes':len(r['componentes']),'estado':r['estado'],'consistencia':r['hallazgo_consistencia']},ensure_ascii=False,indent=2))
