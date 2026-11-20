"""Adaptación parametrizada de EP2/estructural/acoplamiento.py (3C).

Reutiliza la integral de huella variable y el solver EB de EP2. No cambia
PARAMETROS globales comerciales ni importa su runner. Estado: vc y pendiente
radial de cada rodillo; deformación positiva abre holgura (+YCAD).
"""
import math
import numpy as np
import pandas as pd
from .legado import repartir_entre_rodamientos,coordenadas_locales
from .verificaciones import resolver_viga
from .nucleo import positivo
from modelos.superposicion_variable import interseccion_disco_huella_variable


class ModeloAcoplado:
    def __init__(self,analisis,agujeros,config,varilla,E=None,divisiones=None):
        self.a=analisis;self.c=config;self.v=varilla;self.num=config['numerico']
        self.E=E or config['material']['E_referencia_pa'];self.d=varilla['nucleo_referencia_m']
        for k,v in [('E',self.E),('d',self.d),('p',config['presion_pa']),('mu',config['mu_efectivo'])]:positivo(v,k)
        if self.d>varilla['nominal_m']:raise ValueError('Núcleo mayor que diámetro nominal')
        if not 0<self.num['relajacion']<=1 or self.num['max_iteraciones']<1:raise ValueError('Iteración inválida')
        if self.num['tolerancia_holgura_m']<=0 or self.num['tolerancia_fuerza_relativa']<=0:raise ValueError('Tolerancias inválidas')
        self.xy=agujeros[['x_mm','y_mm']].to_numpy()/1000
        diam=agujeros.diametro_efectivo_mm.to_numpy()/1000
        if not np.allclose(diam,diam[0]):raise ValueError('Esta revisión requiere una familia de diámetros')
        self.rh=diam[0]/2;self.radios=np.linalg.norm(self.xy,axis=1)
        self.rodillos=analisis['rodillos'];self.T=np.array(analisis['correspondencia_matriz']['local_matriz_a_ensamble'])
        self.x0=analisis['eje_transversal']['bbox_mm'][0]/1000
        self.L=analisis['eje_transversal']['cilindros'][0]['largo_mm']/1000
        self.apoyos=np.sort([x['centro_eje_mm'][0]/1000-self.x0 for x in analisis['taladros_soporte_transversal']])
        self.pares=[];self.xb=[];self.signos=[];self.dirx=[];self.xc=[]
        for r in self.rodillos:
            par=sorted(sorted(analisis['rodamientos'],key=lambda b:np.linalg.norm(np.array(b['centro_CAD_mm'])-r['centro_CAD_mm']))[:2],key=lambda b:b['centro_CAD_mm'][0])
            xs=[b['centro_CAD_mm'][0]/1000-self.x0 for b in par]
            self.pares.append(par);self.xb.extend(xs)
            self.signos.extend([-np.sign(r['centro_CAD_mm'][0]-self.T[0,3])]*2)
            self.xc.append(r['centro_CAD_mm'][0]/1000-self.x0)
            phi=r['angulo_rad'];self.dirx.append(self.T[0,0]*math.cos(phi)+self.T[0,1]*math.sin(phi))
        if not np.allclose(abs(np.array(self.dirx)),1,atol=1e-6):raise ValueError('Ejes de rodillo no radiales/paralelos a XCAD')
        self.g0=np.array([r['separacion_envolvente_matriz_mm']/1000 for r in self.rodillos])
        if np.any(self.g0<0):raise ValueError('Interferencia CAD inicial')
        claves=np.unique(np.r_[0,self.L,self.apoyos,self.xb]);n=divisiones or self.num['divisiones_viga']
        self.nodos=np.unique(np.round(np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/(self.L/n)))+1) for a,b in zip(claves[:-1],claves[1:])]),12))
        self.indice=lambda x:int(np.argmin(abs(self.nodos-x)))
        self.gdl_b=[2*self.indice(x) for x in self.xb]
        self.restricciones=np.array([2*self.indice(x)+j for x in self.apoyos for j in (0,1)])
        unitarias=np.zeros((2*len(self.nodos),4))
        for j,g in enumerate(self.gdl_b):unitarias[g,j]=1
        seg=[dict(nombre='nucleo_uniforme_de_referencia',x_inicio_m=0,x_fin_m=self.L,diametro_exterior_m=self.d)]
        self.sistema,sol=resolver_viga(self.nodos,seg,self.E,unitarias,self.restricciones,
            'Doble empotramiento hipotético en centros de taladros de cámara; no rigidezABS comprobada')
        self.U=sol.desplazamientos;self.MV=self.sistema.fuerzas_extremo_elementos(self.U)
        self.peso=np.zeros((2*len(self.nodos),1));self.equivalentes=np.zeros((len(self.nodos)-1,4))
        if config['pesos']['incluir']:
            g=config['pesos']['g_m_s2'];rho=config['material']['densidad_varilla_referencia_kg_m3']
            q=-rho*g*math.pi*varilla['nominal_m']**2/4
            for e,l in enumerate(np.diff(self.nodos)):
                f=q*np.array([l/2,l*l/12,l/2,-l*l/12]);self.equivalentes[e]=f
                self.peso[2*e:2*e+4,0]+=f
            for rod,xs in zip(self.rodillos,np.array(self.xb).reshape(2,2)):
                pieza=next(p for p in analisis['inventario'] if p['id']==rod['solido_id'])
                F=-pieza['volumen_mm3']*1e-9*config['material']['densidad_rodillos_304_referencia_kg_m3']*g
                j=self.rodillos.index(rod);rep=repartir_entre_rodamientos(F,self.xc[j],*xs)
                for x,f in zip(xs,(rep.reaccion_a_n,rep.reaccion_b_n)):self.peso[2*self.indice(x),0]+=f
        self.Up=self.sistema.resolver(self.peso).desplazamientos[:,0]
        self.MVp=self.sistema.fuerzas_extremo_elementos(self.Up,self.equivalentes)[:,:,0]
        self.Sp=self.estado_desde_u(self.Up)
        self.S=np.column_stack([self.estado_desde_u(self.U[:,j]) for j in range(4)])

    def estado_desde_u(self,u):
        salida=[]
        for j,(xa,xb) in enumerate(np.array(self.xb).reshape(2,2)):
            va,vb=u[2*self.indice(xa)],u[2*self.indice(xb)]
            pendiente=(vb-va)/(xb-xa)
            salida.extend([va+pendiente*(self.xc[j]-xa),pendiente*self.dirx[j]])
        return np.array(salida)

    def perfiles(self,estado):
        return np.array([self.g0[j]+estado[2*j]+estado[2*j+1]*np.array([-r['ancho_mm']/2000,0,r['ancho_mm']/2000]) for j,r in enumerate(self.rodillos)])

    def contacto(self,locales,estado,h,orden):
        contactos=[];fy=[]
        for j,(loc,r) in enumerate(zip(locales,self.rodillos)):
            rc=r['radio_posicion_mm']/1000;w=r['ancho_mm']/1000
            areas,cr,ct=interseccion_disco_huella_variable(loc,self.rh,(rc-w/2,rc+w/2),
                self.g0[j]+estado[2*j],estado[2*j+1],rc,r['diametro_mm']/1000,h,orden)
            fuerzas=self.c['presion_pa']*areas;F=float(fuerzas.sum());validas=fuerzas>0
            rr=float(np.dot(fuerzas[validas],cr[validas])/F) if F else rc
            tt=float(np.dot(fuerzas[validas],ct[validas])/F) if F else 0.
            phi=r['angulo_rad'];x_local=np.array([rr*math.cos(phi)-tt*math.sin(phi),rr*math.sin(phi)+tt*math.cos(phi)])
            xf=float(self.T[0,:2]@x_local+self.T[0,3]/1000-self.x0)
            xa,xb=self.xb[2*j:2*j+2];rep=repartir_entre_rodamientos(F,xf,xa,xb)
            fy.extend([float(rep.reaccion_a_n),float(rep.reaccion_b_n)])
            contactos.append(dict(F=F,r=rr,t=tt,T=float(np.dot(fuerzas,self.radios)*self.c['mu_efectivo']),
                activos=int(validas.sum()),parciales=int(np.sum(validas&(areas<math.pi*self.rh**2*(1-1e-9))))))
        fy=np.array(fy);return contactos,fy,self.Sp+self.S@fy

    def estructura(self,fy):
        fz=fy*np.array(self.signos)*self.c['mu_efectivo']
        uy=self.Up+self.U@fy;uz=self.U@fz
        ey=self.MVp+np.einsum('eik,k->ei',self.MV,fy)
        ez=np.einsum('eik,k->ei',self.MV,fz)
        M=np.hypot(ey[:,[1,3]],ez[:,[1,3]]);V=np.hypot(ey[:,[0,2]],ez[:,[0,2]])
        sigma=32*M/(math.pi*self.d**3)
        cargas_y=self.peso[:,0].copy();cargas_z=np.zeros_like(cargas_y)
        for j,g in enumerate(self.gdl_b):cargas_y[g]+=fy[j];cargas_z[g]+=fz[j]
        ry=self.sistema.K@uy-cargas_y;rz=self.sistema.K@uz-cargas_z
        ix=np.unravel_index(np.argmax(sigma),sigma.shape)
        salida=dict(flecha_max_m=float(np.hypot(uy[::2],uz[::2]).max()),
            M_max_nm=float(M.max()),sigma_nominal_max_pa=float(sigma.max()),
            tau_corte_max_pa=float(16*V.max()/(3*math.pi*self.d**2)),
            x_sigma_max_m=float(self.nodos[ix[0]+ix[1]]))
        erroresF=[];erroresM=[]
        for reaccion,carga in ((ry,cargas_y),(rz,cargas_z)):
            fija=np.zeros_like(reaccion);fija[self.restricciones]=reaccion[self.restricciones]
            suma=fija+carga
            erroresF.append(abs(suma[::2].sum()))
            erroresM.append(abs(self.nodos@suma[::2]+suma[1::2].sum()))
        salida['residuo_equilibrio_fuerzas_n']=float(max(erroresF))
        salida['residuo_equilibrio_momentos_nm']=float(max(erroresM))
        # El equilibrio se contrasta con reacciones SOLO en los gdl fijos.
        for i,x in enumerate(self.apoyos,1):
            k=2*self.indice(x)
            for eje,rr in [('Y',ry),('Z',rz)]:salida[f'R_{eje}_A{i}_n']=float(rr[k]);salida[f'M_{eje}_A{i}_nm']=float(rr[k+1])
        return salida,uy,uz,ry,rz

    def simular(self,h,pasos=None,orden=None,relajacion=None,limite_iter=None,inicial_cero=False):
        positivo(h,'capa');n=pasos or self.num['estados'];orden=orden or self.num['cuadratura']
        lam=relajacion if relajacion is not None else self.num['relajacion']
        if not 0<lam<=1:raise ValueError('Relajación fuera de (0,1]')
        limite=limite_iter or self.num['max_iteraciones'];estado=np.zeros(4);filas=[];hist=[];detalle=[]
        indices=np.arange(n) if pasos is None else np.linspace(0,self.num['estados']-1,n,dtype=int)
        for paso in indices:
            theta=2*math.pi*paso/self.num['estados'];co=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
            xy=self.xy@co.T;locales=[coordenadas_locales(xy,r['angulo_rad']) for r in self.rodillos]
            if inicial_cero:estado=np.zeros(4)
            anterior=np.full(2,np.nan);convergio=False;motivo='max_iteraciones';res_final=math.inf
            for it in range(1,limite+1):
                try:c,fy,calculado=self.contacto(locales,estado,h,orden)
                except ValueError as e:motivo='geometria_no_admisible: '+str(e);break
                F=np.array([x['F'] for x in c]);perfil=self.perfiles(estado);calculados=self.perfiles(calculado)
                residuo=float(abs(calculados-perfil).max());actualizado=(1-lam)*estado+lam*calculado
                cambio=float(abs(self.perfiles(actualizado)-perfil).max())
                rel=float(np.max(abs(F-anterior)/np.maximum(abs(F),1))) if np.isfinite(anterior).all() else math.inf
                hist.append(dict(paso=int(paso),iteracion=it,residuo_holgura_m=residuo,cambio_holgura_m=cambio,cambio_fuerza_relativo=rel,F1_n=F[0],F2_n=F[1]))
                if residuo<=self.num['tolerancia_holgura_m'] and cambio<=self.num['tolerancia_holgura_m'] and rel<=self.num['tolerancia_fuerza_relativa']:
                    # Verificación posterior usando el contacto y la deformación
                    # que se exportan, no sólo el estado relajado intermedio.
                    try:cf,ff,rf=self.contacto(locales,calculado,h,orden)
                    except ValueError as e:motivo='estado_final_no_admisible: '+str(e);break
                    res_final=float(abs(self.perfiles(rf)-self.perfiles(calculado)).max())
                    rel_final=float(np.max(abs(np.array([x['F'] for x in cf])-F)/np.maximum(abs(np.array([x['F'] for x in cf])),1)))
                    if res_final<=self.num['tolerancia_holgura_m'] and rel_final<=self.num['tolerancia_fuerza_relativa']:
                        estado=calculado;c,fy=cf,ff;convergio=True;motivo='convergido_y_reverificado';break
                estado=actualizado;anterior=F
            fila=dict(paso=int(paso),angulo_grados=360*paso/self.num['estados'],convergio=convergio,motivo=motivo,iteraciones=it,
                varilla=self.v['nombre'],capa_m=h,E_pa=self.E,residuo_final_holgura_m=res_final)
            if not convergio:
                estado=np.zeros(4);filas.append(fila);continue
            datos,uy,uz,ry,rz=self.estructura(fy);fila.update(datos)
            perfiles=self.perfiles(estado);fila.update(fuerza_total_n=sum(x['F'] for x in c),torque_total_nm=sum(x['T'] for x in c),
                cambio_final_fuerza_relativo=rel_final,fuerza_manual_ideal_n=sum(x['T'] for x in c)/.165)
            for j,x in enumerate(c,1):
                fila.update({f'fuerza_r{j}_n':x['F'],f'torque_r{j}_nm':x['T'],f'centroide_radial_r{j}_m':x['r'],
                    f'centroide_tangencial_r{j}_m':x['t'],f'desplazamiento_centro_r{j}_m':estado[2*(j-1)],
                    f'inclinacion_radial_r{j}_rad':estado[2*(j-1)+1],f'holgura_r{j}_min_m':float(perfiles[j-1].min()),
                    f'holgura_r{j}_centro_m':float(perfiles[j-1,1]),f'holgura_r{j}_max_m':float(perfiles[j-1].max()),
                    f'perforaciones_activas_r{j}':x['activos'],f'perforaciones_parciales_r{j}':x['parciales']})
            for j,f in enumerate(fy):fila[f'carga_normal_608_{self.pares[j//2][j%2]["solido_id"]}_n']=float(f)
            filas.append(fila)
        return pd.DataFrame(filas),pd.DataFrame(hist)


def resumir_acoplado(df):
    validas=df[df.convergio];r=dict(estados=len(df),convergidos=len(validas),todos_convergieron=bool(df.convergio.all()),
        iteraciones_max=int(df.iteraciones.max()),no_convergidos=df.loc[~df.convergio,['paso','motivo']].to_dict('records'))
    if validas.empty:return r
    r.update(Fmax_n=float(validas.fuerza_total_n.max()),Fmedia_n=float(validas.fuerza_total_n.mean()),
        Tmax_nm=float(validas.torque_total_nm.max()),Tmedio_nm=float(validas.torque_total_nm.mean()),
        flecha_max_m=float(validas.flecha_max_m.max()),sigma_max_pa=float(validas.sigma_nominal_max_pa.max()),
        residuo_final_max_m=float(validas.residuo_final_holgura_m.max()),seguridad_aprobada=False)
    for j in (1,2):
        r.update({f'g{j}_min_m':float(validas[f'holgura_r{j}_min_m'].min()),f'g{j}_max_m':float(validas[f'holgura_r{j}_max_m'].max()),
            f'g{j}_media_centro_m':float(validas[f'holgura_r{j}_centro_m'].mean()),f'F{j}_max_n':float(validas[f'fuerza_r{j}_n'].max()),
            f'u{j}_centro_max_m':float(validas[f'desplazamiento_centro_r{j}_m'].max())})
    return r
