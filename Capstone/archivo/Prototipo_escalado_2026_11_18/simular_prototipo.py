"""Configuración independiente y escenarios; nunca escribe en EP2."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from modelo_prototipo import (validar_parametros,reconstruir_patron,contacto_angular,cargas,
    eje_transversal,vida_referencia,balance_potencia,demanda_arbol,posiciones_rodamientos)
from reutilizacion import PARAMETROS_COMERCIAL as COM

RAIZ=Path(__file__).resolve().parent
SALIDA=RAIZ/'resultados/revision_nominal_2026_11_18'


def json_escribir(path,obj):
    def convertir(x):
        if isinstance(x,np.generic): return x.item()
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=convertir,allow_nan=False),encoding='utf-8')


def congelar_historicos():
    return {str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in RAIZ.parent.rglob('*') if f.is_file() and not f.is_relative_to(RAIZ)
        and not any(k in f.parts for k in ('__pycache__','.pytest_cache'))}


def verificar_hashes(hashes):
    alterados=[f for f,h in hashes.items() if not Path(f).is_file() or hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h]
    if alterados: raise RuntimeError('Se alteraron archivos históricos: '+str(alterados))


def ejecutar(parametros=RAIZ/'parametros.json',salida=SALIDA):
    parametros=Path(parametros).resolve();salida=Path(salida).resolve()
    if salida.is_relative_to(RAIZ.parent.resolve()) and not salida.is_relative_to((RAIZ/'resultados').resolve()):
        raise ValueError('Dentro de Capstone, salida solo en Prototipo/resultados')
    if salida in RAIZ.parent.resolve().parents:
        raise ValueError('No sobrescribir raíz')
    hashes=congelar_historicos()
    p=json.loads(parametros.read_text(encoding='utf-8'));validar_parametros(p)
    materiales=json.loads((RAIZ/'materiales.json').read_text(encoding='utf-8'))
    xy,patron,geom=reconstruir_patron(p,RAIZ/p['patron']['archivo_origen'])
    g,detalle,longitud=contacto_angular(p,xy)
    p0=p['presion']['referencia_equipo_pa'];mu0=p['resistencia_tangencial']['mu_referencia_escenario']
    d=cargas(p,g,p0,mu0)
    detalle['presion_escenario_pa']=p0
    detalle['fuerza_axial_escenario_n']=detalle['area_superpuesta_m2']*p0
    radios=np.linalg.norm(xy,axis=1)
    detalle['torque_escenario_nm']=detalle['fuerza_axial_escenario_n']*mu0*radios[detalle['id_agujero'].to_numpy(dtype=int)-1]
    contacto_sensible=[]
    for factor in p['sensibilidad_contacto']['factores_espesor_biomasa']:
        ps=copy.deepcopy(p);ps['rodillos']['espesor_biomasa_escenario_m']*=factor
        validar_parametros(ps)
        gs,_,ls=contacto_angular(ps,xy) if factor!=1 else (g,detalle,longitud)
        ds=cargas(ps,gs,p0,mu0)
        contacto_sensible.append(dict(espesor_biomasa_hipotetico_m=ps['rodillos']['espesor_biomasa_escenario_m'],
            longitud_contacto_hipotetica_m=ls,fuerza_total_max_n=float(ds.fuerza_total_n.max()),
            torque_max_nm=float(ds.torque_total_nm.max()),estado='geometría de contacto hipotética, no cargas medidas'))
    g2,_,_=contacto_angular(p,xy,p['numerico']['cuadratura_contraste'])
    error_area=float(np.max(np.abs(g2.area_total_m2-g.area_total_m2))/g2.area_total_m2.max())
    estructuras=[];resumen_eje=[];sensibilidades=[];convergencia=[]
    for apoyo in p['eje_transversal']['apoyos_escenarios']:
        se,re=eje_transversal(p,d,apoyo);estructuras.append(se);resumen_eje.append(re)
        _,fina=eje_transversal(p,d,apoyo,p['numerico']['paso_viga_contraste_m'])
        convergencia.append(dict(apoyo=apoyo,desplazamiento_referencia_m=fina['desplazamiento_max_m'],
            diferencia_relativa_u=abs(re['desplazamiento_max_m']/fina['desplazamiento_max_m']-1),
            diferencia_relativa_sigma=abs(re['sigma_nominal_max_pa']/fina['sigma_nominal_max_pa']-1),
            nota='Solo convergencia de viga lineal, no validación del montaje ni de grandes flechas'))
        for factor in p['presion']['factores_sensibilidad']:
            for E in p['eje_transversal']['E_escenarios_pa']:
                sigma=re['sigma_nominal_max_pa']*factor
                u=re['desplazamiento_max_m']*factor*p['eje_transversal']['E_referencia_escenario_pa']/E
                for Sy in p['eje_transversal']['Sy_escenarios_pa']:
                    sensibilidades.append(dict(apoyo_hipotetico=apoyo,presion_hipotetica_pa=p0*factor,E_hipotetico_pa=E,
                        Sy_hipotetico_pa=Sy,sigma_lineal_pa=sigma,flecha_lineal_m=u,
                        cociente_Sy_sigma_solo_cribado=Sy/sigma,fuera_pequena_deformacion=u/p['eje_transversal']['longitud_m']>.02,
                        estado='E y Sy son ejes de sensibilidad, NO propiedades de varilla comprada;sinFSaprobado'))
    vidas=vida_referencia(p,d);potencias=balance_potencia(p,g);arbol=demanda_arbol(p,d)
    grupos=[]
    for factor in p['presion']['factores_sensibilidad']:
        for mu in p['resistencia_tangencial']['mu_escenarios']:
            dc=cargas(p,g,p0*factor,mu)
            grupos.append(dict(presion_escenario_pa=p0*factor,mu_escenario=mu,
                fuerza_total_max_n=float(dc.fuerza_total_n.max()),fuerza_total_media_n=float(dc.fuerza_total_n.mean()),
                fuerza_r1_max_n=float(dc.fuerza_r1_n.max()),fuerza_r1_media_n=float(dc.fuerza_r1_n.mean()),
                fuerza_r2_max_n=float(dc.fuerza_r2_n.max()),fuerza_r2_media_n=float(dc.fuerza_r2_n.mean()),
                torque_max_nm=float(dc.torque_total_nm.max()),torque_medio_nm=float(dc.torque_total_nm.mean()),
                estado='escenario desacoplado, no resultado experimental ni modelo3C acoplado'))
    datos_param=[]
    def aplanar(obj,prefijo=''):
        for k,v in obj.items():
            clave=prefijo+k
            if isinstance(v,dict): aplanar(v,clave+'.')
            else: datos_param.append(dict(parametro=clave,valor=json.dumps(v,ensure_ascii=False),
                origen='equipo/hipótesis explícita; consultar campo fuente y README',confianza='nominal o escenario, no medición'))
    aplanar(p)
    estado=[
        dict(modelo='geometria',estado='reconstruida_por_indicacion_equipo',detalle='Centros escala0,5; diámetros de perforación6mm no escalados; no CAD medido'),
        dict(modelo='presion_extrusion',estado='pendiente_validacion',detalle='LD calculado;2,26MPa es dato preliminar aportado; fórmula y biomasa no disponibles'),
        dict(modelo='cargas_globales',estado='escenarios_ejecutados',detalle='Superposición parcial1440estados; presión constante de escenario; rodillos y biomasa por semejanza explícita'),
        dict(modelo='eje_transversal',estado='cribado_lineal_condicionado',detalle='NúcleoM6x1, apoyos y posiciones de rodamientos hipotéticos; si u/L>2% se marca alerta, no predicción física de flecha'),
        dict(modelo='rodamientos',estado='referencia_no_producto_adquirido',detalle='EZO608ZZ identificado; marca comprada y montajeM6/8 sin confirmar;vidas condicionadasFa0'),
        dict(modelo='matriz_FEM',estado='pendiente_no_ejecutado',detalle='Faltan apoyo/retención reales, condición304 y nu respaldado; FEM comercial con36mm/collar58 no es reutilizable directamente'),
        dict(modelo='arbol_principal',estado='demanda_nominal_sensibilidad',detalle='Familia/paso/núcleo/apoyos y precarga desconocidos; sección lisa variable es cribado, no rosca aprobada'),
        dict(modelo='carcasa_PLA',estado='pendiente',detalle='Si transmite reacciones de eje/apoyos es crítica; faltan camino de cargas, espesor e impresión. No modelo isotrópico garantizado'),
        dict(modelo='tolva_PLA',estado='pendiente',detalle='Carga de biomasa, uniones, espesor e impresión pendientes; no asignar compactación completa a tolva'),
        dict(modelo='accionamiento',estado='sensibilidad_no_configuracion_real',detalle='1350rpm motor;reducciones1/2/4/8/16 hipotéticas, no mantener516rpm;sin aprobación del motor')]
    comercial=pd.read_csv(RAIZ.parent/'Simulación_peletizadora/resultados/etapa_3c_acoplamiento/resumen_comparativo.csv')
    anterior=comercial[comercial.modelo=='inclinacion'].iloc[0]
    comparacion=pd.DataFrame([
        dict(configuracion='comercial_3C_inclinacion',diametro_matriz_mm=2*COM.radio_matriz_m*1000,espesor_mm=COM.espesor_matriz_m*1000,
            presion_pa=COM.presion_maxima_pa,fuerza_total_max_n=float(anterior.fuerza_total_max_n),torque_max_nm=float(anterior.torque_max_nm),
            rpm_matriz=COM.rpm_matriz,potencia_max_w=float(anterior.potencia_max_w),
            alcance='Histórico3C acoplado; condiciones no equivalentes al prototipo'),
        dict(configuracion='prototipo_escenario_base_no_validado',diametro_matriz_mm=p['matriz']['diametro_m']*1000,
            espesor_mm=p['matriz']['espesor_m']*1000,presion_pa=p0,fuerza_total_max_n=float(d.fuerza_total_n.max()),
            torque_max_nm=float(d.torque_total_nm.max()),rpm_matriz=None,potencia_max_w=None,
            alcance='Desacoplado; rpm y potencia solo por escenarios; no comparar como ensayo a igualdad de servicio')])
    maxk=int(d.fuerza_total_n.idxmax())
    resumen={'configuracion':p['version'],'validado_experimentalmente':False,'seguridad_estructural_aprobada':False,
        'geometria':geom,'longitud_contacto_escenario_mm':longitud*1000,
        'centros_rodamientos_escenario_mm':(posiciones_rodamientos(p)*1000).tolist(),
        'incompatibilidad_M6_608_diametral_mm':1000*(p['rodamientos']['diametro_interior_m']-p['eje_transversal']['diametro_nominal_m']),
        'escenario_referencia':{'presion_pa':p0,'mu':mu0,'estados':len(d),
            'fuerza_total_max_n':float(d.fuerza_total_n.max()),'fuerza_total_media_n':float(d.fuerza_total_n.mean()),
            'torque_max_nm':float(d.torque_total_nm.max()),'torque_medio_nm':float(d.torque_total_nm.mean()),
            'estado_fuerza_max_correlacionado':d.iloc[maxk].to_dict(),
            'perforaciones_activas_r1_min_max':[int(g.perforaciones_activas_r1.min()),int(g.perforaciones_activas_r1.max())]},
        'convergencia_area_error_relativo_max':error_area,'eje_transversal_lineal':resumen_eje,
        'matriz_fem_ejecutado':False,'propiedades_materiales':materiales,'estado_modelos':estado,
        'advertencias':['No equivalencia de operación entre histórico comercial acoplado y escenario prototipo desacoplado',
            '2,26MPa no verificado por fórmula ni ensayo; no extrapolar44MPa por semejanza geométrica',
            'mu0,1 y espesor de biomasa2mm son hipótesis, no propiedades medidas',
            'M6 requiere asiento/adaptador para608 de8mm; no inferir centrado por tuercas',
            'E y Sy de varillas solo sensibilidad; zincado no identifica grado',
            'Rodillos/matriz304 previstos, no certificados; marca del rodamiento comprado no acreditada',
            'Modelo de viga lineal desacoplado sin pesos por geometría/material incompletos ni precarga, entallas o flexibilidadPLA',
            'Gran flecha o esfuerzo nominal elevado exigen revisar montaje/carga, no publicar seguridad mediante extrapolación elástica',
            'No aprobación de torque por fricción de tuercas, arrancamiento, apoyo axial ni arranque del motor',
            'Paso/familia de varilla1/2pulgada desconocidos; no asumirUNC niM12',
            'No se midió transmisión real; potencia se calcula por escenarios, no por516rpm'],
        'datos_fisicos_prioritarios':['Separación real de rodillos, holgura, espesor de capa y marcas de huella',
            'Confirmar coordenadas reconstruidas, ligamentos y acabado de102perforaciones',
            'Accionamiento real: relación, tipo y pérdidas; placa del motor',
            'Asientos/adaptadores608–M6, posiciones de rodamientos y apoyos de eje',
            'Familia/paso de varilla1/2, grado y comprobantes de varillas, inox y608',
            'Corte matriz-tuercas-árbol con retención, contactos, precarga y apoyos',
            'Paredes, orientación, relleno y material de impresión; función soportante de carcasa',
            'Memoria de presión2,26MPa y datos de biomasa/humedad/fricción/temperatura; ensayos de carga y consumo']}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,df in [('patron_reconstruido',patron),('parametros_documentados',pd.DataFrame(datos_param)),
        ('sensibilidad_geometria_contacto',pd.DataFrame(contacto_sensible)),
        ('geometria_angular',g),('cargas_escenario_referencia',d),('cargas_sensibilidad',pd.DataFrame(grupos)),
        ('eje_transversal_series',pd.concat(estructuras)),('eje_transversal_sensibilidad',pd.DataFrame(sensibilidades)),
        ('viga_convergencia',pd.DataFrame(convergencia)),('vidas_referencia_EZO',vidas),('balance_potencia',potencias),
        ('arbol_demanda_nominal',arbol),('comparacion_no_equivalente',comparacion),('estado_modelos',pd.DataFrame(estado)),
        ('materiales_y_confianza',pd.DataFrame(materiales['materiales']))]:
        df.to_csv(salida/f'{nombre}.csv',index=False)
    detalle.to_csv(salida/'superposicion_por_agujero.csv.gz',index=False,compression='gzip')
    for nombre,obj in [('resumen',resumen),('parametros_utilizados',p),('historicos_sha256',hashes),('fuentes_materiales',materiales)]:
        json_escribir(salida/f'{nombre}.json',obj)
    json_escribir(salida/'revision_presion_extrusion.json',{
        'fuente':'stelte_presion_2011','formula_referencia':'Px=PN0/nuLR * expm1(4*mu_pared*nuLR*L_activa/D)',
        'formula_ep2_encontrada':False,'PN0_pa':None,'mu_pared':None,'nu_biomasa_LR':None,
        'presion_calibrada_pa':None,'presion_escenario_equipo_pa':p0,
        'aplicabilidad':'Régimen estacionario de canal con material calibrado; no garantiza densificación, calidad o arranque del prototipo',
        'conclusion':'L/D1,667 no basta para verificar2,26MPa; longitud activa puede diferir del espesor si hay entrada/alivio. No copiar propiedades de biomasa de otra especie.'})
    entradas=[f for f in RAIZ.iterdir() if f.is_file()]+[parametros]
    json_escribir(salida/'entradas_prototipo_sha256.json',{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas})
    fig,ax=plt.subplots(1,2,figsize=(11,4))
    for x,y in patron[['x_mm','y_mm']].to_numpy():
        ax[0].add_patch(Circle((x,y),p['matriz']['diametro_agujero_m']*500,fill=False,color='tab:blue',linewidth=.6))
    ax[0].add_patch(Circle((0,0),p['matriz']['diametro_m']*500,fill=False,color='k'))
    ax[0].add_patch(Circle((0,0),p['matriz']['diametro_central_m']*500,fill=False,color='k'))
    r0=p['rodillos']['centro_radial_m']*1000;w=p['rodillos']['ancho_m']*1000
    for x in (r0-w/2,-r0-w/2):
        ax[0].add_patch(Rectangle((x,-longitud*500),w,longitud*1000,alpha=.12,color='tab:orange'))
    limite=p['matriz']['diametro_m']*550
    ax[0].set_aspect('equal');ax[0].set(xlim=(-limite,limite),ylim=(-limite,limite),xlabel='x [mm]',ylabel='y [mm]',title='Patrón ×0,5, agujerosØ6 (no medición)')
    ax[1].plot(d.angulo_grados,d.fuerza_r1_n,label='Rodillo1');ax[1].plot(d.angulo_grados,d.fuerza_total_n,label='Total')
    ax[1].set(xlabel='Ángulo [°]',ylabel='F [N]',title=f'Escenario p={p0/1e6:g}MPa, contacto supuesto');ax[1].legend()
    fig.tight_layout();fig.savefig(salida/'geometria_y_cargas.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4))
    for factor in p['presion']['factores_sensibilidad']:
        parte=potencias[(potencias.presion_pa==p0*factor)&(potencias.mu_escenario==mu0)&(potencias.eficiencia_mecanica_hipotetica==.8)]
        ax.plot(parte.rpm_matriz_hipotetica,parte.potencia_max_w,'o-',label=f'p={p0*factor/1e6:g}MPa (hipótesis)')
    ax.axhline(p['motor']['potencia_mecanica_nominal_w']*.8,color='k',linestyle='--',label='Disponible si η mec.=0,8')
    ax.set(xlabel='rpm matriz hipotéticas',ylabel='Potencia [W]',title='Sensibilidad; no transmisión seleccionada');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(salida/'sensibilidad_potencia.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4))
    for df in estructuras:
        ax.plot(df.angulo_grados,df.desplazamiento_lineal_max_m*1000,label=df.apoyo_escenario.iloc[0])
    ax.set(xlabel='Ángulo [°]',ylabel='Flecha lineal [mm]',title='Cribado M6: apoyos supuestos; no flecha física validada');ax.legend()
    fig.tight_layout();fig.savefig(salida/'eje_transversal_cribado.png',dpi=150);plt.close(fig)
    verificar_hashes(hashes)
    json_escribir(salida/'validaciones.json',{'historicos_intactos':True,'archivos_historicos':len(hashes),
        'estados_angulares':len(g),'patron_sin_intersecciones':True,'cuadratura_contrastada':True,
        'equilibrio_vertical_max_error_n':max(r['equilibrio_vertical_error_n'] for r in resumen_eje),
        'no_equivale_a_validacion_experimental':True})
    return resumen


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parametros',type=Path,default=RAIZ/'parametros.json')
    parser.add_argument('--salida',type=Path,default=SALIDA);args=parser.parse_args()
    r=ejecutar(args.parametros,args.salida)
    print(json.dumps({k:r[k] for k in ('geometria','escenario_referencia','eje_transversal_lineal')},indent=2,ensure_ascii=False))
