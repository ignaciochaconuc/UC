from pathlib import Path
import sys,json,math,copy,hashlib
import numpy as np,pandas as pd
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
D=Path(__file__).resolve().parent;S=D.parents[2];sys.path.insert(0,str(S))
from peletizadora.ensamble import leer_ensamble,propiedades,transformar,frontera_muestreada
from peletizadora.cad import extraer

def guardar(n,x): (D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
def main():
 e=json.loads((D/'entrada_identificada.json').read_text(encoding='utf-8'))
 raw=D/e['copia_inmutable_en_revision'] if e.get('copia_inmutable_en_revision') else Path(e['archivo_proporcionado'])
 hojas,meta=leer_ensamble(raw);sh={i['id']:s for s,i in hojas};inv=[propiedades(s,i) for s,i in hojas]
 guardar('inventario_nuevo.json',{'meta':meta,'inventario':inv})
 matriz=next(p for p in inv if p['caras_por_tipo'].get('GeomAbs_Cylinder',0)>100)
 ref,dim,holes,_,_=extraer(S/'geometrias/Matriz_prototipo.stp')
 M=np.array(matriz['transformacion_acumulada']);local=transformar(sh[matriz['id']],np.linalg.inv(M))
 fronteras=[frontera_muestreada(local,ref),frontera_muestreada(ref,local)]
 B=np.eye(4);B[:3,:3]=dim['sistema_local']['base_filas_x_y_z_en_CAD'];B[:3,3]=-B[:3,:3]@np.array(dim['sistema_local']['origen_CAD_mm'])
 T=B@np.linalg.inv(M)
 cyl=[c for c in matriz['cilindros'] if abs(c['radio_mm']-3)<1e-5 and abs(c['largo_mm']-10)<1e-5]
 xy=np.array([(T@np.r_[c['centro_eje_mm'],1])[:2] for c in cyl]);hr=np.array([[h['x_mm'],h['y_mm']] for h in holes])
 error=cKDTree(hr).query(xy)[0].max()
 if len(cyl)!=102 or error>1e-5 or any(f['no_sobre_frontera'] for f in fronteras):raise ValueError('La matriz cambió, reconstruir geometría antes de simular')
 shaft=next(p for p in inv if len(p['cilindros'])==1 and abs(p['cilindros'][0]['radio_mm']-4)<1e-5 and p['cilindros'][0]['largo_mm']>100)
 ux=np.array(shaft['cilindros'][0]['eje']);ux*=np.sign(ux[0]);uy=np.array([0.,1.,0.]);uz=np.cross(ux,uy);Q=np.array([ux,uy,uz])
 origin=np.array(shaft['cilindros'][0]['centro_eje_mm']);origin[1]=0
 H=np.eye(4);H[:3,:3]=Q;H[:3,3]=-Q@origin
 transformed=[]
 for p in inv:
  q=propiedades(transformar(sh[p['id']],H),{k:p[k] for k in ['id','nombre_instancia','nombre_definicion','transformacion_acumulada']});transformed.append(q)
 Ti=H@np.linalg.inv(T)
 point=lambda p:(np.linalg.inv(Ti)@np.r_[p,1])[:3]
 rods=[]
 for p in transformed:
  c=max(p['cilindros'],key=lambda z:z['radio_mm'],default=None)
  if c and abs(c['radio_mm']-26)<1e-5 and abs(c['largo_mm']-30)<1e-5:
   z=point(c['centro_eje_mm']);phi=math.atan2(z[1],z[0]);p['clasificacion']='rodillo'
   rods.append(dict(solido_id=p['id'],centro_CAD_mm=c['centro_eje_mm'],centro_local_matriz_mm=z.tolist(),eje_CAD=c['eje'],diametro_mm=52.,ancho_mm=30.,radio_posicion_mm=float(np.linalg.norm(z[:2])),angulo_rad=phi,separacion_envolvente_matriz_mm=abs(z[2])-26))
 bearings=[]
 for p in transformed:
  if any(abs(c['radio_mm']-11)<1e-5 and abs(c['largo_mm']-6.4)<1e-5 for c in p['cilindros']) and any(abs(c['radio_mm']-4)<1e-5 for c in p['cilindros']):
   c=next(c for c in p['cilindros'] if abs(c['radio_mm']-11)<1e-5);bearings.append(dict(solido_id=p['id'],centro_CAD_mm=c['centro_eje_mm'],diametro_interior_mm=8.,diametro_exterior_mm=22.,ancho_envolvente_mm=7.))
 principal=next(p for p in transformed if len(p['cilindros'])==1 and abs(p['cilindros'][0]['radio_mm']-6.35)<1e-5)
 chamber=next(p for p in transformed if sum(abs(c['radio_mm']-4)<1e-5 and abs(c['eje'][0])>.99 for c in p['cilindros'])==2)
 supports=[c for c in chamber['cilindros'] if abs(c['radio_mm']-4)<1e-5 and abs(c['eje'][0])>.99]
 anal=dict(meta=meta,inventario=transformed,matriz_id=matriz['id'],rodillos=rods,rodamientos=bearings,eje_transversal=transformed[shaft['id']-1],arbol_principal=principal,taladros_soporte_transversal=supports,correspondencia_matriz={'local_matriz_a_ensamble':Ti.tolist()},matriz_verificada={'error_centros_mm':error,'fronteras':fronteras,'L_D':10/6},marco_solver_a_CAD=np.linalg.inv(H).tolist(),marco_CAD_a_solver=H.tolist(),matriz_local_a_CAD=np.linalg.inv(T).tolist())
 guardar('ensamble_solver.json',anal);pd.DataFrame(holes).to_csv(D/'perforaciones.csv',index=False)
 # Todos los sólidos: asociación por medidas invariantes, no solamente nombres.
 old=json.loads((S/'resultados/prototipo/revision_ensamble_2026_11_19/ensamble_auditado.json').read_text(encoding='utf-8'))['inventario']
 def cost(x,y):
  v=abs(math.log(x['volumen_mm3']/y['volumen_mm3']));cx=sorted((round(c['radio_mm'],3),round(c['largo_mm'],3)) for c in x['cilindros']);cy=sorted((round(c['radio_mm'],3),round(c['largo_mm'],3)) for c in y['cilindros'])
  return v+(0 if cx==cy else .2)+.05*abs(sum(x['caras_por_tipo'].values())-sum(y['caras_por_tipo'].values()))
 C=np.array([[cost(x,y) for y in inv] for x in old]);ii,jj=linear_sum_assignment(C);rows=[];used=set()
 for i,j in zip(ii,jj):
  if C[i,j]>1:continue
  x,y=old[i],inv[j];used.add(j);rows.append(dict(id_anterior=x['id'],id_nuevo=y['id'],nombre_anterior=x['nombre_instancia'],nombre_nuevo=y['nombre_instancia'],volumen_anterior_mm3=x['volumen_mm3'],volumen_nuevo_mm3=y['volumen_mm3'],variacion_volumen_pct=100*(y['volumen_mm3']/x['volumen_mm3']-1),estado='Geometría invariante equivalente' if C[i,j]<1e-6 else 'Modificado/asociación para revisión',costo_asociacion=C[i,j]))
 for j,y in enumerate(inv):
  if j not in used:rows.append(dict(id_anterior=None,id_nuevo=y['id'],nombre_anterior=None,nombre_nuevo=y['nombre_instancia'],volumen_anterior_mm3=None,volumen_nuevo_mm3=y['volumen_mm3'],variacion_volumen_pct=None,estado='Nuevo/no asociado unívocamente',costo_asociacion=None))
 pd.DataFrame(rows).to_csv(D/'comparacion_todos_solidos.csv',index=False)
 guardar('comparacion_geometria_matriz.json',anal['matriz_verificada'])
 print(json.dumps({k:anal[k] for k in ['rodillos','rodamientos','taladros_soporte_transversal','matriz_verificada']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
