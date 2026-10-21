"""ETAPA 4A: postproceso estructural PRELIMINAR de matriz + árbol vertical.

Lee SIN MODIFICAR la Etapa 3C (modelo `inclinacion`) y la geometría CAD.
Produce reacciones/resultantes externas equivalentes, cargas síncronas de eje
nominal, comparación de materiales CONDICIONAL y mapa por perforación.

NO calcula tensiones de flexión de placa ni deflexiones del eje: requieren
condiciones de contorno, apoyo axial, fijación de matriz y cargas de correa.
NO es FEA/DEM; NO atribuir sus imágenes a tensiones de elementos finitos.

Ejecución:
 python simulacion_matriz_eje_4A.py --proyecto RUTA_ZIP_EXTRAIDO --salida RESULTADOS
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

DENSIDAD_ACERO_REFERENCIA_KG_M3 = 7850.0 # supuesto para masa geométrica
RADIO_MATRIZ_M = .100
RADIO_AGUJERO_CENTRAL_M = .025
RADIO_PERFORACION_M = .003
RADIO_AVELLANADO_M = .0045
ESPESOR_MATRIZ_M = .036
OMEGA_RAD_S = 2*math.pi*516/60
# LIMITES PRELIMINARES, por material y condición de entrega (no certificados del prototipo)
MATERIALES_EJE = [
    ('SAE 1045 +QT (>40 a 100 mm, Atlas)', 370e6,
     'https://atlassteels.com.au/documents/Atlas1045.pdf'),
    ('SAE 4140 / 6115 +QT (barra >25 a <60 mm, Ovako)', 940e6,
     'https://steelnavigator.ovako.com/steel-grades/42crmo4/'),
]


def _leer(ruta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    serie = pd.read_csv(ruta/'resultados/etapa_3c_acoplamiento/series_temporales_acopladas.csv')
    serie = serie[serie['modelo']=='inclinacion'].sort_values('paso').copy().reset_index(drop=True)
    assert len(serie)==1440 and bool(serie['convergio'].all()), 'Historia 3C incompleta'
    hoyos = pd.read_csv(ruta/'datos/agujeros_matriz.csv')
    assert len(hoyos)==102, 'Se esperaban 102 agujeros del CSV CAD'
    for f in ['fuerza_total_n','torque_resistente_nm','fuerza_rodillo_1_n','fuerza_rodillo_2_n',
              'resultante_radial_r1_m','resultante_radial_r2_m','resultante_tangencial_r1_m',
              'resultante_tangencial_r2_m']:
        assert serie[f].notna().all(),f
    # Control inalterado del 3C principal: tolerancia solo por redondeo del resultado anunciado
    assert abs(serie.fuerza_total_n.max()-14070.987476941267)<1e-3
    assert abs(serie.torque_resistente_nm.max()-88.92396579145439)<1e-3
    return serie,hoyos


def historial_resultantes(s: pd.DataFrame) -> pd.DataFrame:
    """Eje global x hacia R1, y a +90 grados, z vertical (positivo arriba).

    Rodillo 1 local radial +x; tangencial local +y.
    Rodillo 2 radial -x; tangencial local -y.
    Fuerzas normales rodillos SOBRE matriz = -Fz. Resultantes M = r x F:
    Mx = -sum(y_i F_i); My = sum(x_i F_i).
    La fuerza tangencial aproximada se obtiene como +/-mu F_i: su resultante
    no es el torque exacto 3C, que usa cada radio de perforación.
    """
    t = s[['paso','tiempo_s','angulo_grados']].copy()
    f1 = s.fuerza_rodillo_1_n.to_numpy(); f2=s.fuerza_rodillo_2_n.to_numpy()
    x1=s.resultante_radial_r1_m.to_numpy(); x2=-s.resultante_radial_r2_m.to_numpy()
    y1=s.resultante_tangencial_r1_m.to_numpy(); y2=-s.resultante_tangencial_r2_m.to_numpy()
    t['F1_N']=f1; t['F2_N']=f2
    t['Fz_normal_N']=f1+f2
    t['Mx_normales_Nm']=-y1*f1-y2*f2
    t['My_normales_Nm']=x1*f1+x2*f2
    t['M_flexion_normales_Nm']=np.hypot(t.Mx_normales_Nm,t.My_normales_Nm)
    t['T_resistente_3C_Nm']=s.torque_resistente_nm.to_numpy()
    t['F_tangencial_neta_aprox_y_N']=.1*(f1-f2)
    t['P_resistente_W']=s.potencia_resistente_w.to_numpy()
    assert np.allclose(t.Fz_normal_N,s.fuerza_total_n)
    return t


def geometria_perforada(hoyos: pd.DataFrame) -> dict:
    centros = hoyos[['x_mm','y_mm']].to_numpy()/1000
    radio = np.linalg.norm(centros,axis=1)
    delta=centros[:,None,:]-centros[None,:,:]
    dd=np.linalg.norm(delta,axis=2)
    np.fill_diagonal(dd, np.inf)
    paso_min = dd.min()
    area_total=math.pi*RADIO_MATRIZ_M**2
    area_central=math.pi*RADIO_AGUJERO_CENTRAL_M**2
    area_perfs=len(centros)*math.pi*RADIO_PERFORACION_M**2
    area_neta=area_total-area_central-area_perfs  # omite chavetero y mayor área superficial del avellanado
    return {
        'perforaciones':len(centros),'espesor_m':ESPESOR_MATRIZ_M,
        'radio_exterior_m':RADIO_MATRIZ_M,
        'radio_central_m':RADIO_AGUJERO_CENTRAL_M,
        'radio_centros_min_m':float(radio.min()),'radio_centros_max_m':float(radio.max()),
        'paso_min_entre_centros_m':float(paso_min),
        'ligamento_min_entre_agujeros_6mm_m':float(paso_min-2*RADIO_PERFORACION_M),
        'ligamento_min_bocas_9mm_m':float(paso_min-2*RADIO_AVELLANADO_M),
        'margen_exterior_boca_9mm_m':float(RADIO_MATRIZ_M-radio.max()-RADIO_AVELLANADO_M),
        'margen_centro_boca_9mm_m':float(radio.min()-RADIO_AGUJERO_CENTRAL_M-RADIO_AVELLANADO_M),
        'area_bruta_m2':area_total,'area_neta_simplificada_m2':area_neta,
        'porcentaje_huecos_pasantes_area':100*(area_central+area_perfs)/area_total,
        'masa_cilindrica_simplificada_kg':area_neta*ESPESOR_MATRIZ_M*DENSIDAD_ACERO_REFERENCIA_KG_M3,
        'advertencia': 'Masa y área sin chavetero ni avellanados; no son resistencia neta bajo flexión'
    }


def tensiones_nominales_de_eje(s: pd.DataFrame, diametros_mm=(35,40,45,50)) -> pd.DataFrame:
    """Sólo superposición axial + torsión en barra MACIZA lisa.

    Envoltura paramétrica superior si ambos esfuerzos alcanzan una misma sección;
    no prueba que fuerza axial atraviese esa sección ni combina momentos de flexión.
    """
    out=[]
    F=s.Fz_normal_N.to_numpy();T=s.T_resistente_3C_Nm.to_numpy();M=s.M_flexion_normales_Nm.to_numpy()
    for dmm in diametros_mm:
        d=dmm/1000; area=math.pi*d*d/4; J=math.pi*d**4/32
        sigma=F/area; tau=16*T/(math.pi*d**3)
        vm=np.sqrt(sigma**2+3*tau**2)
        # HIPOTESIS OPCIONAL: TODO el par flector de normales pasa por esta sección.
        # El momento interno REAL podría ser diferente: dependen apoyos y rigidez.
        sigma_flexion=32*M/(math.pi*d**3)
        vm_con_flexion=np.sqrt((sigma+sigma_flexion)**2+3*tau**2)
        ixf=int(np.argmax(vm_con_flexion))
        ix=int(np.argmax(vm)); ismax=int(np.argmax(sigma)); itmax=int(np.argmax(tau))
        row={'diametro_mm':dmm, 'sigma_axial_max_MPa':float(sigma[ismax]/1e6),
             'tau_torsion_max_MPa':float(tau[itmax]/1e6),
             'sigma_VM_max_sin_flexion_MPa':float(vm[ix]/1e6),
             'VM_si_todo_M_transmitido_MPa':float(vm_con_flexion[ixf]/1e6),
             'angulo_VM_condicional_deg':float(s.angulo_grados.iloc[ixf]),
             'sigma_flexion_max_MPa':float(sigma_flexion.max()/1e6),
             'angulo_VM_critico_deg':float(s.angulo_grados.iloc[ix]),
             'F_en_instante_VM_N':float(F[ix]), 'T_en_instante_VM_Nm':float(T[ix]),
             'giro_por_metro_rad_m_en_Tmax':float(T.max()/(79e9*J)),
             'leyenda':'eje sólido liso; sin flexión, chaveteros, fatiga o apoyos'}
        for nombre,sy,url in MATERIALES_EJE:
            key=('1045' if '1045' in nombre else '4140')
            row['n_nominal_'+key]=float(sy/vm[ix])
            row['n_hipotesis_todo_M_'+key]=float(sy/vm_con_flexion[ixf])
        out.append(row)
    return pd.DataFrame(out)


def _cargas_agujeros_criticas(proyecto:Path, s:pd.DataFrame, agujeros:pd.DataFrame, paso:int) -> pd.DataFrame:
    """Mismas funciones de 3C; reconstrucción para UN paso (postproceso, sin mutaciones)."""
    sys.path.insert(0,str(proyecto))
    from cinematica import rotar
    from modelos.superposicion import coordenadas_locales
    from estructural.acoplamiento import _contacto_rodillo
    coords=agujeros[['x_mm','y_mm']].to_numpy(float)/1000
    rotated=rotar(coords,2*math.pi*paso/1440)
    radii=np.linalg.norm(coords,axis=1)
    row=s.loc[s.paso==paso].iloc[0]
    records=[]
    for j,alfa in ((1,0.0),(2,math.pi)):
        loc=coordenadas_locales(rotated,alfa)
        contacto=_contacto_rodillo(loc, radii,float(row[f'holgura_centro_r{j}_m']),
                                  float(row[f'inclinacion_r{j}_rad']),j,64)
        for k,area in enumerate(contacto.areas_m2):
            if area<=0: continue
            records.append({'paso':paso,'angulo_grados':float(row.angulo_grados),'rodillo':j,
                            'id_agujero':int(agujeros.id.iloc[k]),
                            'x_global_m':rotated[k,0],'y_global_m':rotated[k,1],
                            'fuerza_normal_N':44e6*area,
                            'centroide_radial_m':contacto.centroides_r_m[k],
                            'centroide_tangencial_m':contacto.centroides_t_m[k]})
        # No re-simular 3C: la diferencia relativa proviene del redondeo en la
        # salida acoplada final de los desplazamientos.
        if not np.isclose(contacto.fuerza_n,float(row[f'fuerza_rodillo_{j}_n']),rtol=1e-5,atol=0.2):
            raise RuntimeError(f'No se pudo reconstruir el contacto 3C paso {paso} rodillo {j}: '
                               f'{contacto.fuerza_n} vs {row[f"fuerza_rodillo_{j}_n"]}')
    return pd.DataFrame(records)


def figura_series(t:pd.DataFrame, out:Path)->None:
    fig,axs=plt.subplots(3,1,figsize=(10.5,8.7),sharex=True,layout='constrained')
    x=t.angulo_grados
    axs[0].plot(x,t.F1_N/1000,label='Rodillo 1',linewidth=1.1)
    axs[0].plot(x,t.F2_N/1000,label='Rodillo 2',linewidth=1.1)
    axs[0].plot(x,t.Fz_normal_N/1000,label='Total',linewidth=1.5)
    axs[0].set_ylabel('Fuerza normal [kN]');axs[0].legend(ncol=3)
    axs[1].plot(x,t.Mx_normales_Nm,label=r'$M_x$')
    axs[1].plot(x,t.My_normales_Nm,label=r'$M_y$')
    axs[1].plot(x,t.M_flexion_normales_Nm,label=r'$|M|$',linewidth=2)
    axs[1].set_ylabel('Momentos de carga normal [N·m]');axs[1].legend(ncol=3)
    axs[2].plot(x,t.T_resistente_3C_Nm,label='Torque 3C')
    axs[2].set_ylabel('Torque [N·m]');axs[2].set_xlabel('Ángulo matriz [°]')
    for ax in axs: ax.grid(alpha=.2)
    fig.savefig(out/'historial_cargas_y_momentos.png',dpi=180);plt.close(fig)


def figura_mapa(agujeros:pd.DataFrame,carga:pd.DataFrame,angulo:float,out:Path,nombre:str)->None:
    base=agujeros[['x_mm','y_mm']].to_numpy()
    ang=math.radians(angulo)
    rot=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang), math.cos(ang)]])
    xy=base@rot.T
    fig,ax=plt.subplots(figsize=(7.6,7),layout='constrained')
    ax.add_patch(Circle((0,0),100,fill=False,color='black',linewidth=1.7))
    ax.add_patch(Circle((0,0),25,fill=False,color='black',linewidth=1.5))
    for x,y in xy:ax.add_patch(Circle((x,y),3,fill=False,ec='#aaaaaa',lw=.65))
    if len(carga):
        aa=carga
        cmax=max(aa.fuerza_normal_N.max(),1)
        for _,r in aa.iterrows():
            xx=r.x_global_m*1000;yy=r.y_global_m*1000
            ax.add_patch(Circle((xx,yy),3,facecolor=plt.cm.Greys(.2+.8*r.fuerza_normal_N/cmax),
                                edgecolor='black',lw=.55))
        # Agujeros originales en rotación mostrados en otra orientación se dibujan
        # solo para contexto; la posición de contactos sí refleja theta.
    ax.set(xlim=(-105,105),ylim=(-105,105),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    ax.set_title(f'Distribución de fuerza por perforación, ángulo {angulo:.2f}°\n'
                 'TONO = fuerza 3C reconstruida (no tensión estructural)')
    ax.grid(alpha=.1)
    fig.savefig(out/nombre,dpi=170);plt.close(fig)


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--proyecto',type=Path,required=True)
    cli.add_argument('--salida',type=Path,required=True)
    opt=cli.parse_args()
    out=opt.salida;out.mkdir(parents=True,exist_ok=True)
    s,agujeros=_leer(opt.proyecto)
    t=historial_resultantes(s)
    topo=geometria_perforada(agujeros)
    tn=tensiones_nominales_de_eje(t)
    assert abs(t.Fz_normal_N.max()-s.fuerza_total_n.max())<1e-7
    assert abs(t.T_resistente_3C_Nm.max()-s.torque_resistente_nm.max())<1e-7
    t.to_csv(out/'series_resultantes_matriz_eje.csv',index=False)
    tn.to_csv(out/'secciones_eje_nominales.csv',index=False)
    (out/'geometria_perforada.json').write_text(json.dumps(topo,ensure_ascii=False,indent=2),encoding='utf-8')
    casos={'max_fuerza_total':int(t.Fz_normal_N.idxmax()),
           'max_torque':int(t.T_resistente_3C_Nm.idxmax()),
           'max_momento_normales':int(t.M_flexion_normales_Nm.idxmax()),
           'max_VM_eje_d35':int(t.angulo_grados.sub(tn.iloc[0].angulo_VM_critico_deg).abs().idxmin())}
    extremos=[];repartos=[]
    for nombre,idx in casos.items():
        fila=t.iloc[idx]
        extremos.append({'evento':nombre, **fila.to_dict()})
        h=_cargas_agujeros_criticas(opt.proyecto,s,agujeros,int(fila.paso))
        h['evento']=nombre;repartos.append(h)
        if nombre in ('max_fuerza_total','max_momento_normales'):
            figura_mapa(agujeros,h,fila.angulo_grados,out,f'mapa_{nombre}.png')
    pd.DataFrame(extremos).to_csv(out/'casos_criticos_correlacionados.csv',index=False)
    pd.concat(repartos,ignore_index=True).to_csv(out/'fuerzas_por_agujero_casos_criticos.csv',index=False)
    figura_series(t,out)
    with (out/'informe_resultados.md').open('w',encoding='utf-8') as f:
        f.write('# Etapa 4A — matriz perforada y árbol principal (premodelo)\n\n')
        f.write('No modifica la etapa 3C. No es FEA: sin identificación verificada del apoyo axial, unión y cargas laterales, '+
                'las tensiones de flexión de la matriz y deformaciones estructurales no están identificadas.\n\n')
        f.write('## Geometría derivada del CAD y CSV\n\n')
        for k,v in topo.items(): f.write(f'- {k}: {v}\n')
        f.write('\n## Historial simultáneo: extremos\n\n')
        for nombre,idx in casos.items():
            r=t.iloc[idx]
            f.write(f'- **{nombre}**: paso {int(r.paso)}, ángulo {r.angulo_grados:.2f}°; '
                    f'Fz={r.Fz_normal_N/1000:.3f} kN, T={r.T_resistente_3C_Nm:.3f} N·m, '
                    f' Mx={r.Mx_normales_Nm:.3f} N·m, My={r.My_normales_Nm:.3f} N·m, '
                    f'|M|={r.M_flexion_normales_Nm:.3f} N·m\n')
        f.write('\n## Eje: tensiones nominales por diámetro hipotético\n\n')
        f.write('```text\n'+tn.to_string(index=False)+'\n```\n')
        f.write('\n\nLa columna que añade flexión es una hipótesis de transferencia del MOMENTO EXTERNO completo a la misma sección, sin apoyos ni fuerzas de correa; NO es un esfuerzo interno resuelto por equilibrio de árbol.\n')
        f.write('\nNOTA: la sección real y transmisión de empuje axial no están determinadas. '
                'Sin presión sobre asiento, cargas de correa, diagrama de momentos/rodamientos, ni Kt/Kf '
                'no puede obtenerse el factor de seguridad final del árbol.\n')
        f.write('\n## Matriz: pendientes para FEM sólido / placa\n\n')
        f.write('1. Definir si carga normal va a tope axial, brida, pernos o rodamiento de empuje.\n')
        f.write('2. Definir contacto matriz--eje: ajuste, chaveta y retención axial; restringir solo GDL reales.\n')
        f.write('3. Considerar avellanados Ø9, agujeros Ø6, espesor 36 mm, hueco Ø50 y chavetero.\n')
        f.write('4. Mallar 3D con refinamiento de radios y puentes; aplicar cargas por agujero en pasos '+
                '3C correlacionados; verificar convergencia de desplazamientos y tensiones lejos de singularidades.\n')
        f.write('5. Verificar fluencia/fatiga, deformación de superficie, contacto de cubo, reacción axial y torsión en chaveta.\n')
        f.write('\nFUENTES MATERIALES CONDICIONALES: '+str(MATERIALES_EJE)+'\n')
    print((out/'informe_resultados.md').read_text(encoding='utf-8')[:6000])

if __name__=='__main__':main()
