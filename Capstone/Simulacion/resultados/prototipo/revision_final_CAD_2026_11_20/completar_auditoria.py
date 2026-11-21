from auditar import *

def main():
    a=json.loads((D/'ensamble_solver.json').read_text(encoding='utf-8'))
    old=json.loads((S/'resultados/prototipo/revision_ensamble_2026_11_19/ensamble_auditado.json').read_text(encoding='utf-8'))
    t=pd.read_csv(D/'comparacion_todos_solidos.csv')
    # Completar explícitamente componentes anteriores sin asociación.
    faltan=[p for p in old['inventario'] if p['id'] not in set(t.id_anterior.dropna().astype(int))]
    if faltan:
        extra=pd.DataFrame([dict(id_anterior=p['id'],id_nuevo=None,nombre_anterior=p['nombre_instancia'],nombre_nuevo=None,
            volumen_anterior_mm3=p['volumen_mm3'],volumen_nuevo_mm3=None,variacion_volumen_pct=None,
            estado='Anterior sin equivalente unívoco, retirado o sustituido',costo_asociacion=None) for p in faltan])
        t=pd.concat([t,extra],ignore_index=True);t.to_csv(D/'comparacion_todos_solidos.csv',index=False)
    rows=[]
    def add(n,x,y,u,estado,why):rows.append(dict(parametro=n,anterior=x,definitivo=y,unidad=u,estado=estado,implicacion=why))
    add('Número sólidos',39,67,'unidad','Modificado','Se incorporan fijaciones, soporte y buje; se comparan todos los sólidos por medidas')
    for n,x,y in [('Diámetro matriz',99,99),('Espesor perforado',10,10),('Diámetro canales',6,6),('Número canales',102,102),('Bore matriz',13,13),('Cuerpo central envolvente',26,26)]:
        add(n,x,y,'mm' if n!='Número canales' else 'unidad','Reutilizado verificado','Frontera y 102 centros coinciden a tolerancia1e-5mm')
    for j in range(2):
        x=old['rodillos'][j];y=a['rodillos'][j]
        for lab,key in [('Radio centro','radio_posicion_mm'),('Diámetro','diametro_mm'),('Ancho radial','ancho_mm'),('Holgura inicial','separacion_envolvente_matriz_mm')]:
            add(f'Rodillo{j+1} {lab}',x[key],y[key],'mm','Verificado / recalculado','Cotas cilíndricas y posición respecto de la matriz')
    add('Separación centros rodillos',np.linalg.norm(np.array(old['rodillos'][0]['centro_CAD_mm'])-old['rodillos'][1]['centro_CAD_mm']),55.5,'mm','Conservado','Nuevos centros simétricos ±27,75mm')
    add('Diámetro cilindro transversalCAD',6,8,'mm','Modificado','El cálculo anterior ya usaba M8: ahora el CAD refleja8 nominal, EI sigue núcleo6,466')
    add('Núcleo usado en cálculo M8',6.466,6.466,'mm','Reutilizado','No usar cilindro macizo8 para la varilla M8×1,25')
    add('Longitud transversal',160,160,'mm','Conservado','Nuevo eje centrado respecto del árbol')
    lo=abs(old['taladros_soporte_transversal'][1]['centro_eje_mm'][0]-old['taladros_soporte_transversal'][0]['centro_eje_mm'][0]);ln=abs(a['taladros_soporte_transversal'][1]['centro_eje_mm'][0]-a['taladros_soporte_transversal'][0]['centro_eje_mm'][0])
    add('Luz fijaciones M8',lo,ln,'mm','Recalculado','Centros de los dos taladros de carcasa, hipótesis doble empotramiento')
    add('Taladros fijación M8CAD',6,8,'mm','Modificado','Compatibles nominalmente conM8; no prueba rigidez del ABS')
    add('Alojamiento exterior608',24,22,'mm','Corregido','Elimina1mm radial sin apoyo; contacto nominal22/22')
    add('608 bore/exterior/ancho','8/22/7','8/22/7','mm','Conservado','Cilindros8/22 y tramo activo6,4 más chaflanes')
    add('Separación608 parR1',23.5,23.6,'mm','Modificado','Nuevas reacciones calculadas por sus centros cilíndricos')
    add('Separación608 parR2',23.6,23.6,'mm','Conservado','No repartir a cuartos la fuerza total')
    add('Árbol diámetro exterior',12.7,12.7,'mm','Conservado','Producto roscado, falta raíz/propiedad como antes')
    add('Árbol longitud',200,235,'mm','Modificado','Recalcular axial, torsión y flexión con nuevas estaciones')
    add('Radio manivela',165,165,'mm','Reutilizado verificado','Misma geometría local del brazo: cambian su estación y fase')
    add('Tuercas del árbolCAD','M12','1/2-13','designación y bore','Corregido nominal','Nuevas caras y agujeros compatibles con familia de diseño1/2')
    add('Cara apoyo inferior matriz radio exterior',11.5,9.525,'mm','Modificado relevante','Se elimina arandela inferior; diámetro de cara nut19,05 medido por bordes circulares')
    add('Apoyo central inferior área',np.pi*(11.5**2-6.5**2),np.pi*(9.525**2-6.5**2),'mm2','FEM repetido','Reducción46,14%; no reutilizar restricción del anillo anterior')
    add('Rodamiento árbol principal','No presente','Sólido53 dentro de52','estado','Incorporado','Bore25,4mm, C/C0 no identificadas; demandas calculadas, no capacidad inventada')
    add('Buje de adaptación','No presente','12,7/25,4×36','mm','Incorporado','Solape completo del tramo31,013mm del bore; retención árbol-buje no está demostrada')
    add('Placa superior','95×95×5','110×110×5','mm','Modificada','Taladro13 y patrón de fijación40mm conservados')
    add('Placa inferior','95×95×5','135×135×5','mm','Modificada','Nuevo patrón de pernosM14 del soporte, bore13')
    add('Fijaciones adicionales','No presentes','M5/M8/M14 y tuercas','familia','Incorporadas','Diámetros nominales/bores medidos; no convertir volumen de rosca cosmética en interferencia física')
    pd.DataFrame(rows).to_csv(D/'comparacion_geometrica_funcional.csv',index=False)
    apoyos=[]
    for ro in a['rodillos']:
        pieza=a['inventario'][ro['solido_id']-1]
        seats=[c for c in pieza['cilindros'] if abs(c['radio_mm']-11)<1e-5 and abs(c['largo_mm']-7)<1e-5]
        for s in seats:
            b=min(a['rodamientos'],key=lambda b:np.linalg.norm(np.array(b['centro_CAD_mm'])-s['centro_eje_mm']))
            off=abs(b['centro_CAD_mm'][0]-s['centro_eje_mm'][0]);apoyos.append(dict(rodillo_id=ro['solido_id'],bearing_id=b['solido_id'],asiento_diam_mm=22,rodamiento_diam_mm=22,
                asiento_largo_mm=7,tramo_cilindrico_anillo_mm=6.4,desfase_centros_mm=off,margen_cilindro_activo_mm=3.5-3.2-off,
                estado='Tramo activo dentro del asiento a tolerancia; no bloqueo por el saliente nominal de chaflán'))
    pd.DataFrame(apoyos).to_csv(D/'montaje_608_verificado.csv',index=False)
    guardar('dictamen_geometrico.json',dict(antiguos_cubiertos=len(set(t.id_anterior.dropna())),nuevos_cubiertos=len(set(t.id_nuevo.dropna())),
        matriz_identica=True,matriz_L_D_conservado=True,alojamientos_608_corregidos=True,rodamiento_principal_presente=True,
        buje_dimensionalmente_compatible=True,retencion_axial_arbol_buje_verificada=False,uniones_torque_verificadas=False,
        nota='No se considera que nombres, contactosgeométricos o roscas cosméticas acrediten apriete, capacidad o resistencia'))

if __name__=='__main__':main()
