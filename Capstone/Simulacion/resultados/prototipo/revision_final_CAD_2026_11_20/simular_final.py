from auditar import D,S,guardar
import sys,json,math
import numpy as np,pandas as pd
sys.path.insert(0,str(S))
from peletizadora.acoplado_prototipo import ModeloAcoplado as ModeloEP2,resumir_acoplado
from peletizadora.legado import repartir_entre_rodamientos
from contacto_corregido import interseccion_disco_huella_variable
class ModeloFinal(ModeloEP2):
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


def entradas():
 a=json.loads((D/'ensamble_solver.json').read_text(encoding='utf-8'))
 c=json.loads((S/'configuraciones/acoplado_m8.json').read_text(encoding='utf-8'));c['capas_m']=[.004];c['varillas']=[c['varillas'][1]]
 h=pd.read_csv(D/'perforaciones.csv');return a,c,h

def main():
 a,c,h=entradas();m=ModeloFinal(a,h,c,c['varillas'][0]);df,hist=m.simular(.004)
 df.to_csv(D/'serie_3C_definitiva.csv',index=False);hist.to_csv(D/'iteraciones.csv.gz',index=False,compression='gzip')
 r=resumir_acoplado(df);guardar('resumen_3C.json',r);guardar('parametros_3C.json',c)
 print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
