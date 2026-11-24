"""Informe PDF y tablas/gráficos, exclusivamente desde resultados aceptados."""
import csv
import argparse
import subprocess
import sys
import json
import textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from inspeccionar import ROOT
from postprocesar import render_fields

def read_result(t,h):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'
    r=json.loads((folder/'resultados.json').read_text(encoding='utf-8'))
    if not r['equilibrium_passed'] or not r['boundary_conditions_passed'] or r['status'].startswith('REJECTED'):
        raise RuntimeError(f'Result rejected: {folder}')
    return r

def save_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def text_page(pdf,title,paragraphs):
    fig=plt.figure(figsize=(8.27,11.69)); fig.text(.09,.94,title,fontsize=18,weight='bold',va='top')
    y=.885
    for paragraph in paragraphs:
        wrapped='\n'.join(textwrap.fill(line,88) if line else '' for line in paragraph.split('\n'))
        height=(wrapped.count('\n')+1)*.019+.025
        if y-height<.065:
            fig.text(.09,.035,'MEF sólido 3D · 23-11-2026 · procedimiento reproducible',fontsize=8,color='.4')
            pdf.savefig(fig); plt.close(fig)
            fig=plt.figure(figsize=(8.27,11.69)); fig.text(.09,.94,title+' (continuación)',fontsize=16,weight='bold',va='top'); y=.885
        fig.text(.09,y,wrapped,fontsize=10.5,va='top',linespacing=1.5)
        y-=height
    fig.text(.09,.035,'MEF sólido 3D · 23-11-2026 · datos y código reproducibles en la carpeta del análisis',fontsize=8,color='.4')
    pdf.savefig(fig); plt.close(fig)

def image_page(pdf,title,paths):
    images=[plt.imread(path) for path in paths]; ratios=[im.shape[0]/im.shape[1] for im in images]
    fig,axes=plt.subplots(len(paths),1,figsize=(8.27,11.69),gridspec_kw={'height_ratios':ratios}); axes=np.atleast_1d(axes)
    for ax,im in zip(axes,images): ax.imshow(im); ax.axis('off')
    fig.suptitle(title,fontsize=16); fig.tight_layout(rect=(0,.02,1,.95)); pdf.savefig(fig); plt.close(fig)

def main(render=True):
    results=[read_result(t,6) for t in [2.,2.5,3.]]
    limits={'von_mises':max(r['von_mises_max_nodal_MPa'] for r in results),'desplazamiento':max(r['displacement_max_mm'] for r in results)}
    if render:
        for r in results: render_fields(ROOT/f"componentes_t{r['thickness_mm']:.1f}_h6",r['thickness_mm'],limits)
    if render or not (ROOT/'detalle_union_critica.png').exists():
        subprocess.run([sys.executable,str(ROOT/'detalle_uniones.py')],check=True)
    meshes=[read_result(2.,h) for h in [8,7,6]]
    pair_sensitivity=[]
    for t in [2.,2.5,3.]:
        coarse=read_result(t,8); fine=read_result(t,6)
        pair_sensitivity.append(dict(espesor_mm=t,elementos_inicial=coarse['elements'],elementos_final=fine['elements'],
                                     VM_GP_inicial_MPa=coarse['von_mises_max_integration_MPa'],VM_GP_final_MPa=fine['von_mises_max_integration_MPa'],
                                     VM_nodal_inicial_MPa=coarse['von_mises_max_nodal_MPa'],VM_nodal_final_MPa=fine['von_mises_max_nodal_MPa'],
                                     u_inicial_mm=coarse['displacement_max_mm'],u_final_mm=fine['displacement_max_mm'],
                                     cambio_u_porcentaje=100*abs(fine['displacement_max_mm']-coarse['displacement_max_mm'])/fine['displacement_max_mm']))
    save_csv(ROOT/'sensibilidad_por_espesor.csv',pair_sensitivity)
    masses={float(r['thickness_mm']):r for r in csv.DictReader((ROOT/'masas_geometricas.csv').open())}
    reaction_rows=[]
    for r in results:
        for solid,values in r['reactions'].items():
            force=values['force_N']; moment=values['moment_origin_Nmm']
            reaction_rows.append(dict(espesor_mm=r['thickness_mm'],solido=int(solid),Fx_N=force[0],Fy_N=force[1],Fz_N=force[2],Mx_origen_Nmm=moment[0],My_origen_Nmm=moment[1],Mz_origen_Nmm=moment[2]))
    save_csv(ROOT/'reacciones.csv',reaction_rows)
    rows=[]
    for r in results:
        mass=masses[r['thickness_mm']]
        rows.append(dict(espesor_mm=r['thickness_mm'],masa_total_kg=float(mass['sum_mass_kg']),masa_tubos_kg=float(mass['tube_mass_kg']),
                         volumen_total_mm3=float(mass['sum_volume_mm3']),von_Mises_GP_MPa=r['von_mises_max_integration_MPa'],
                         von_Mises_nodal_MPa=r['von_mises_max_nodal_MPa'],desplazamiento_max_mm=r['displacement_max_mm'],
                         FS_nominal_conservador=r['nominal_yield_safety_factor_conservative'],nodos=r['nodes'],elementos_C3D10=r['elements'],
                         residuo_relativo_fuerza=r['relative_force_residual'],residuo_relativo_momento=r['relative_moment_residual']))
    save_csv(ROOT/'comparacion_resultados.csv',rows)
    meshrows=[dict(h_max_mm=r['h_mm'],nodos=r['nodes'],elementos=r['elements'],von_Mises_GP_MPa=r['von_mises_max_integration_MPa'],von_Mises_nodal_MPa=r['von_mises_max_nodal_MPa'],desplazamiento_mm=r['displacement_max_mm']) for r in meshes]
    save_csv(ROOT/'sensibilidad_malla.csv',meshrows)
    last,previous=meshes[-1],meshes[-2]
    sensitivity={k:100*abs(last[k]-previous[k])/abs(last[k]) for k in ['von_mises_max_integration_MPa','von_mises_max_nodal_MPa','displacement_max_mm']}
    sensitivity['displacement_within_2_percent']=sensitivity['displacement_max_mm']<2
    sensitivity['both_stress_measures_within_5_percent']=max(sensitivity['von_mises_max_integration_MPa'],sensitivity['von_mises_max_nodal_MPa'])<5
    (ROOT/'sensibilidad_malla.json').write_text(json.dumps(sensitivity,indent=2))
    for row in rows:
        row['estado_maximos_tension']='No certificados como convergidos; ver sensibilidad de malla'
        row['factor_seguridad_estado']='Nominal y dependiente de malla; no constituye aceptación de diseño'
    save_csv(ROOT/'comparacion_resultados.csv',rows)
    x=[r['espesor_mm'] for r in rows]
    fig,axes=plt.subplots(2,2,figsize=(9,7.5)); axes=axes.ravel()
    axes[0].plot(x,[r['von_Mises_GP_MPa'] for r in rows],'o-',label='Puntos de integración')
    axes[0].plot(x,[r['von_Mises_nodal_MPa'] for r in rows],'s--',label='Nodal extrapolado/promediado'); axes[0].set_ylabel('Máximo von Mises [MPa]'); axes[0].legend(fontsize=8)
    axes[1].plot(x,[r['desplazamiento_max_mm'] for r in rows],'o-'); axes[1].set_ylabel('Desplazamiento máximo [mm]')
    axes[2].plot(x,[r['FS_nominal_conservador'] for r in rows],'o-'); axes[2].set_ylabel('Factor nominal: 276 / mayor máximo')
    for ax in axes[:3]: ax.set_xlabel('Espesor [mm]'); ax.set_xticks(x); ax.grid(alpha=.25)
    axes[3].plot([r['masa_total_kg'] for r in rows],[r['desplazamiento_max_mm'] for r in rows],'o-'); axes[3].set(xlabel='Masa total [kg]',ylabel='Desplazamiento máximo [mm]'); axes[3].grid(alpha=.25)
    fig.suptitle('Valores calculados; tensiones y factores nominales dependientes de malla',fontsize=11); fig.tight_layout(); fig.savefig(ROOT/'comparacion_estructural.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(8.5,7.5)); n=[r['elements'] for r in meshes]
    axes[0].plot(n,[r['von_mises_max_integration_MPa'] for r in meshes],'o-',label='Integración'); axes[0].plot(n,[r['von_mises_max_nodal_MPa'] for r in meshes],'s--',label='Nodal'); axes[0].set_ylabel('Máximo von Mises [MPa]'); axes[0].legend()
    axes[1].plot(n,[r['displacement_max_mm'] for r in meshes],'o-'); axes[1].axhline(.4716,color='.4',linestyle=':',label='Inventor: referencia preliminar'); axes[1].set_ylabel('Desplazamiento máximo [mm]'); axes[1].legend()
    for ax in axes: ax.set_xlabel('Número de tetraedros cuadráticos'); ax.grid(alpha=.25)
    fig.suptitle('Sensibilidad de malla: configuración de 2 mm'); fig.tight_layout(); fig.savefig(ROOT/'sensibilidad_malla.png',dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.2)); ax.axis('off')
    headings=['t [mm]','Masa [kg]','VM GP [MPa]','VM nodal [MPa]','u máx [mm]','FS nominal']
    values=[[f"{r['espesor_mm']:.1f}",f"{r['masa_total_kg']:.4f}",f"{r['von_Mises_GP_MPa']:.3f}",f"{r['von_Mises_nodal_MPa']:.3f}",f"{r['desplazamiento_max_mm']:.5f}",f"{r['FS_nominal_conservador']:.3f}"] for r in rows]
    tab=ax.table(cellText=values,colLabels=headings,loc='center',cellLoc='center'); tab.auto_set_font_size(False); tab.set_fontsize(11); tab.scale(1,2)
    ax.set_title('Resultados sólidos 3D; tensiones y factores nominales dependientes de malla'); fig.tight_layout(); fig.savefig(ROOT/'tabla_comparativa.png',dpi=180); plt.close(fig)
    lines=['ANÁLISIS MEF 3D — RESULTADOS CALCULADOS', 'Máximos puntuales de tensión y factores nominales NO certificados como convergidos.', '']
    for r in rows: lines.append(f"t={r['espesor_mm']:.1f} mm: masa={r['masa_total_kg']:.6f} kg; VM_GP={r['von_Mises_GP_MPa']:.6f} MPa; VM_nodal={r['von_Mises_nodal_MPa']:.6f} MPa; u_max={r['desplazamiento_max_mm']:.7f} mm; FS_nominal={r['FS_nominal_conservador']:.5f}.")
    lines.extend(['',f'Sensibilidad últimas dos mallas: {json.dumps(sensitivity,ensure_ascii=False)}',
                  'Equilibrio y residuos de apoyos: aprobados en los tres espesores.',
                  'La convergencia de máximos debe interpretarse con sensibilidad_malla.csv y las limitaciones del informe. No se certifica un espesor óptimo sin criterios admisibles de diseño.'])
    mass_change=100*(rows[-1]['masa_total_kg']/rows[0]['masa_total_kg']-1)
    displacement_change=100*(rows[-1]['desplazamiento_max_mm']/rows[0]['desplazamiento_max_mm']-1)
    lines.append(f'De 2,0 a 3,0 mm: masa {mass_change:+.2f}%; desplazamiento máximo {displacement_change:+.2f}%. Esto no certifica resistencia ni seguridad de diseño.')
    (ROOT/'RESUMEN.txt').write_text('\n'.join(lines),encoding='utf-8')
    with PdfPages(ROOT/'informe_MEF_cuadro.pdf') as pdf:
        text_page(pdf,'Cuadro de bicicleta · MEF sólido 3D',[
            'Resultado principal: masas y desplazamientos globales comparables; máximos puntuales de tensión no estabilizados con el refinamiento. Los factores de seguridad son nominales y dependientes de malla. No se certifica un espesor óptimo.',
            f'Comparación global de 2,0 a 3,0 mm: masa {mass_change:+.2f}% y desplazamiento máximo {displacement_change:+.2f}%. La reducción de desplazamiento se contrasta entre mallas; no se interpreta como una certificación de resistencia.',
            'Comparación de espesores 2,0 / 2,5 / 3,0 mm. Se conservan geometría exterior, posiciones, remates y punteras de la única referencia autorizada.',
            'Referencia: archivo subido Ensamblaje 2.stp, confirmado por el usuario ante la ausencia del nombre Ensamblaje 2(1).stp. La copia exacta es referencia_confirmada.stp; su hash está en configuracion.json. No se usó otro STEP anterior.',
            'Análisis estático lineal con tetraedros cuadráticos C3D10 de CalculiX 2.24 y PARDISO (MKL 2026.2.1). Todos los valores estructurales de este informe se extraen de archivos DAT y FRD reales y pasan los controles de equilibrio y condiciones de borde.',
            'Las masas son integrales geométricas CAD. Las tensiones se informan con dos convenciones: máximo en puntos de integración y máximo nodal extrapolado/promediado. El factor nominal conservador usa 276 MPa dividido por el mayor máximo.',
            'No se prescribe desplazamiento admisible ni un factor mínimo de diseño. Se entregan comparaciones y limitaciones, sin certificar un espesor óptimo.'
        ])
        image_page(pdf,'Geometría identificada y masas',[ROOT/'geometria_identificada.png',ROOT/'comparacion_masas.png'])
        text_page(pdf,'Geometría, material y condiciones',[
            'El STEP contiene 16 sólidos válidos: 12 tubos, dos remates de 5 mm y dos punteras. Espesor medido de los tubos: 2,5 mm. Diámetros exteriores presentes: 21,3; 26,9; 33,7 y 42,4 mm. La tabla completa está en dimensiones_tubos.csv.',
            'Las variantes se construyen cambiando sólo taladros coaxiales, con una envolvente exterior conservada por tubo. Se exige reconstrucción correcta a 2,5 mm. Los auxiliares se reutilizan sin edición y la exportación se comprueba mediante superficies analíticas muestreadas y cajas óptimas.',
            'La fragmentación diagnóstica conservó 16 volúmenes sin etiquetas volumétricas compartidas: no se detectaron interferencias con ese control. Las booleanas coincidentes produjeron diferencias numéricas de volumen de hasta 61,83 mm³ (0,0065%). No se utilizó la geometría fragmentada para el MEF. Las verificaciones detalladas están en auditoria_variantes.json y contactos.csv.',
            'Aluminio 6061-T6 isotrópico: E=68,9 GPa; nu=0,33; densidad=2700 kg/m³; fluencia nominal=276 MPa. Unidades de cálculo: mm, N, MPa y tonne. No se introduce peso propio.',
            'Cargas normales compresivas distribuidas: 600 N en remate de asiento 13 y 100 N en delantero 14. Resultante global: (153,984; -682,519; 0) N. Las áreas y momentos integrados están en modelo_resumen.json.',
            'Última aclaración del usuario: puntera derecha 16 (Z negativo), radial y axial; izquierda 15 (Z positivo), sólo radial. Se usan agujeros interiores R6 mm. Dirección: radial en interiores de tramos 4 y 5. Tangencial libre; axial libre en dirección y puntera izquierda.',
            'Los ejes de agujeros traseros no son paralelos. Se conservan los ejes reales de cada cara; no se introduce un eje común artificial.'
        ])
        text_page(pdf,'Contactos y verificaciones mecánicas',[
            'Se midieron holguras de ~0,05 y ~0,10 mm entre tubos y punteras. El usuario confirmó contacto adherido. No se cerraron mediante desplazamiento de piezas ni se añadieron cordones inventados.',
            'Los vínculos MPC interpolan desplazamientos sobre tetraedros cuadráticos maestros. Se exige partición de unidad y reproducción afín en las posiciones originales; ello conserva traslaciones y rotaciones rígidas infinitesimales y permite transferir momentos a través de la holgura.',
            'Equivalencia de pasador: er·u=0 y, sólo donde corresponde, a·u=0. er es la dirección radial local y a el eje medido del cilindro. Ninguna restricción se sustituye por un empotramiento completo.',
            'El anillo adherido entre tramos de dirección hereda la condición radial del maestro para evitar doble imposición casi redundante. Su residuo radial se controla explícitamente después de resolver, con tolerancia de 1e-5 mm.',
            'Estabilidad: 96 movimientos rígidos de 16 cuerpos; rango 90 con adherencias y 96 con apoyos. Jacobianos positivos y volumen integrado de malla contrastado con CAD. Ensayo de parche independiente: 1 MPa recuperado y error de desplazamiento <5e-12 mm.',
            'Equilibrio: error relativo de fuerzas y momentos <0,1%. Reacciones recuperadas con nodos auxiliares sin elementos para evitar la limitación de RF en nodos físicos sujetos a MPC. Los valores completos están en resultados.json.',
            'Se conservaron intentos rechazados y logs: fallos de mallado global, fusión no aceptada, restricciones redundantes y fallos de solucionadores directos SPOOLES. La ruta final usa mallas independientes y PARDISO. No se modificaron geometría ni cargas para resolver esos problemas.'
        ])
        image_page(pdf,'Comparación de las tres configuraciones',[ROOT/'tabla_comparativa.png',ROOT/'comparacion_estructural.png'])
        reaction_text=['Todas las componentes se expresan en el sistema global del STEP. Los momentos se calculan respecto del origen global; no son momentos locales de un pasador. La tabla completa por sólido de apoyo está en reacciones.csv.']
        for r in results:
            rear_right=np.array(r['reactions']['16']['force_N']); rear_left=np.array(r['reactions']['15']['force_N']); head=np.array(r['reactions']['4']['force_N'])+np.array(r['reactions']['5']['force_N'])
            reaction_text.append(f"t={r['thickness_mm']:.1f} mm. Fuerzas (Fx,Fy,Fz) [N]: derecha {tuple(round(float(v),4) for v in rear_right)}; izquierda {tuple(round(float(v),4) for v in rear_left)}; dirección total {tuple(round(float(v),4) for v in head)}. Error relativo de equilibrio: fuerzas {r['relative_force_residual']:.3e}, momentos {r['relative_moment_residual']:.3e}. Residuo de apoyo {r['max_support_constraint_displacement_mm']:.3e} mm; anillo heredado {r['max_inherited_radial_displacement_mm']:.3e} mm.")
        reaction_text.append('La resultante de cargas es (153,9842; -682,5190; 0) N. El momento de cargas respecto del origen es (-23456,3719; -5292,0287; 79960,0538) N·mm. Las reacciones equilibran ambas magnitudes dentro de la tolerancia establecida.')
        text_page(pdf,'Reacciones y equilibrio global',reaction_text)
        text_page(pdf,'Sensibilidad de malla y referencia Inventor',[
            'Caso de 2 mm, tres discretizaciones: h máximo 8 / 7 / 6 mm, con 16 / 24 / 32 puntos de curvatura por círculo. Refinamiento local de 0,08 mm en una arista problemática del sólido 7. Son mallas no uniformes: h máximo no representa el tamaño en toda la pared. El caso final de 3 mm usa 28 puntos de curvatura por límite de memoria, conservando h máximo=6 mm y toda la geometría.',
            '\n'.join(f"h={r['h_mm']:g} mm: {r['elements']} elementos, {r['nodes']} nodos; VM integración={r['von_mises_max_integration_MPa']:.4f} MPa, VM nodal={r['von_mises_max_nodal_MPa']:.4f} MPa, u={r['displacement_max_mm']:.6f} mm." for r in meshes),
            f"Cambio relativo entre últimas dos mallas: integración {sensitivity['von_mises_max_integration_MPa']:.2f}%; nodal {sensitivity['von_mises_max_nodal_MPa']:.2f}%; desplazamiento {sensitivity['displacement_max_mm']:.2f}%.",
            ('Los máximos satisfacen el criterio operativo de sensibilidad <5% para tensión y <2% para desplazamiento en las últimas dos mallas.' if sensitivity['both_stress_measures_within_5_percent'] and sensitivity['displacement_within_2_percent'] else 'No se demuestra estabilización de todos los máximos con estos criterios. Las comparaciones de tensión y los factores nominales deben considerarse dependientes de malla.'),
            'El máximo de integración se desplaza desde el encuentro de tirantes y tubo de asiento hacia la unión de una vaina con el pedalier. Se comprobó que los tetraedros críticos tienen jacobianos positivos. Pueden contribuir aristas/muescas sin radio y la discretización de contactos no conformes. No se ha aislado una causa única ni demostrado una singularidad analítica; véase diagnostico_maximos.json.',
            f"Inventor: 54,71 MPa y 0,4716 mm, referencia preliminar de otra simulación de tubos nominalmente de 2 mm. Caso actual de 2 mm: VM integración {results[0]['von_mises_max_integration_MPa']:.4f} MPa, VM nodal {results[0]['von_mises_max_nodal_MPa']:.4f} MPa y u={results[0]['displacement_max_mm']:.6f} mm.",
            f"Diferencias numéricas frente a esa referencia: tensión de integración {100*(results[0]['von_mises_max_integration_MPa']/54.71-1):+.2f}%; tensión nodal {100*(results[0]['von_mises_max_nodal_MPa']/54.71-1):+.2f}%; desplazamiento {100*(results[0]['displacement_max_mm']/.4716-1):+.2f}%. No son errores de validación conocidos: la recuperación de tensiones y la malla original no están completamente definidas.",
            'El tamaño medio 0,015 de Inventor es relativo al tamaño del modelo, según Autodesk; no equivale a 0,015 mm. No se conocen todos los ajustes originales por pieza, elementos curvos y adaptación local. Referencia documental completa en README.txt.',
            'La discrepancia se evalúa considerando la convención de tensiones, contactos ideales y mallas distintas. Las imágenes históricas permiten una comparación espacial cualitativa; no hay campos originales de Inventor en formato intercambiable. No se calibró ningún parámetro para forzar coincidencia.'
        ])
        image_page(pdf,'Estudio de sensibilidad',[ROOT/'sensibilidad_malla.png'])
        text_page(pdf,'Control inicial/final en cada espesor',[
            'Se comparó una malla inicial con 16 puntos de curvatura por círculo y h máximo=8 mm frente a la final con h máximo=6 mm. Las finales de 2,0 y 2,5 mm usan 32 puntos de curvatura; la final de 3,0 mm usa 28 por memoria disponible. El refinamiento localizado de la muesca se conserva.',
            *[f"t={r['espesor_mm']:.1f} mm: {r['elementos_inicial']} a {r['elementos_final']} tetraedros; VM integración {r['VM_GP_inicial_MPa']:.3f} a {r['VM_GP_final_MPa']:.3f} MPa; VM nodal {r['VM_nodal_inicial_MPa']:.3f} a {r['VM_nodal_final_MPa']:.3f} MPa; u {r['u_inicial_mm']:.6f} a {r['u_final_mm']:.6f} mm (cambio {r['cambio_u_porcentaje']:.3f}%)." for r in pair_sensitivity],
            'Estos datos separan la estabilidad del desplazamiento global de la sensibilidad de máximos locales. No se impone una tendencia monotónica de tensión con el espesor ni se usa la coincidencia parcial con Inventor para aceptar máximos no convergidos.',
            'La tabla editable es sensibilidad_por_espesor.csv. Para resolver los picos se requiere un estudio localizado adicional que separe efectos de la muesca y de la representación de las uniones; cualquier modificación exterior exige una nueva definición geométrica autorizada.'
        ])
        for r in results:
            folder=ROOT/f"componentes_t{r['thickness_mm']:.1f}_h6"
            image_page(pdf,f"Campos calculados · t={r['thickness_mm']:g} mm",[folder/'von_mises.png',folder/'desplazamiento.png'])
        image_page(pdf,'Detalle de la zona crítica (proyección)',[ROOT/'detalle_union_critica.png'])
        text_page(pdf,'Límites de interpretación y reproducción',[
            'Este análisis evalúa elasticidad lineal con uniones adheridas ideales. No modela cordones de soldadura ni zonas afectadas térmicamente. El factor respecto de 276 MPa corresponde únicamente al material base idealizado.',
            'No se evalúan fatiga, pandeo local o global, impacto ni cargas de uso distintas del caso indicado. El espesor de menor masa no queda certificado como diseño seguro por el solo cumplimiento nominal de fluencia.',
            'Los máximos locales en encuentros de aristas pueden ser sensibles al refinamiento. Los jacobianos y el equilibrio no sustituyen un estudio de convergencia. Tampoco se afirma que todas las paredes tengan un número uniforme de elementos a través de su espesor.',
            'Resultados tabulados: comparacion_resultados.csv y sensibilidad_malla.csv. Localizaciones de máximos y reacciones: resultados.json por caso. La localización del máximo de integración se acompaña del centroide de sus cuatro vértices, no de una coordenada de integración inventada.',
            'Reproducción: README.txt. Código: inspeccionar.py, verificar_geometria.py, generar_variantes.py, auditar_variantes.py, mallar_componentes.py, preparar_modelo.py, resolver.py, postprocesar.py y generar_informe.py.',
            'Documentación primaria: Autodesk Inventor, Pin Constraint (enlace completo en README.txt); manual CalculiX ccx_2.22.pdf en www.dhondt.de; distribución Windows en github.com/calculix/CalculiX-Windows. La versión ejecutada y su procedencia están archivadas.'
        ])
    print(json.dumps(rows,indent=2)); print('PDF generated')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--reuse-fields',action='store_true'); args=parser.parse_args(); main(not args.reuse_fields)
