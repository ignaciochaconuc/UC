"""Contrastes de discretización e inicio independiente: solo M8 y4mm."""
from simular_final import *

def main():
    a,c,h=entradas();base=pd.read_csv(D/'serie_3C_definitiva.csv');rows=[]
    for nombre,orden,divisiones in [('cuadratura128',128,80),('malla160',64,160)]:
        m=ModeloFinal(a,h,c,c['varillas'][0],divisiones=divisiones)
        d,_=m.simular(.004,pasos=32,orden=orden,inicial_cero=True)
        ref=base.set_index('paso').loc[d.paso]
        rows.append(dict(contraste=nombre,estados=32,todos_convergieron=bool(d.convergio.all()),
            error_F_abs_n=float(max(abs(d.fuerza_total_n.to_numpy()-ref.fuerza_total_n.to_numpy()))),
            error_T_abs_nm=float(max(abs(d.torque_total_nm.to_numpy()-ref.torque_total_nm.to_numpy()))),
            error_g_abs_m=float(max(max(abs(d[f'holgura_r{j}_centro_m'].to_numpy()-ref[f'holgura_r{j}_centro_m'].to_numpy())) for j in [1,2]))))
    pd.DataFrame(rows).to_csv(D/'validacion_numerica_3C.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':main()
