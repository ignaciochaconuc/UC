import unittest,json,math,re,ast
from pathlib import Path
import numpy as np,pandas as pd
from simular_final import entradas
from componentes_final import conservar,D,S
from contacto_corregido import interseccion_disco_huella_variable,longitud_contacto_desde_holgura
from peletizadora.legado import coordenadas_locales

class Revision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a,cls.c,cls.h=entradas();cls.df=pd.read_csv(D/'serie_3C_definitiva.csv')

    def test_integridad(self):
        self.assertEqual(conservar()['alterados'],0)
        self.assertEqual(conservar()['archivos_historicos'],891)

    def test_geometria_cobertura_completa(self):
        g=json.loads((D/'dictamen_geometrico.json').read_text(encoding='utf-8'))
        self.assertEqual(g['antiguos_cubiertos'],39);self.assertEqual(g['nuevos_cubiertos'],67)
        self.assertTrue(g['matriz_identica']);self.assertTrue(g['alojamientos_608_corregidos'])
        self.assertEqual(len(self.h),102)

    def test_marco_ortonormal(self):
        H=np.array(self.a['marco_CAD_a_solver']);R=H[:3,:3]
        self.assertTrue(np.allclose(R@R.T,np.eye(3),atol=1e-12))
        self.assertAlmostEqual(np.linalg.det(R),1.,places=12)
        self.assertTrue(np.allclose(H@np.array(self.a['marco_solver_a_CAD']),np.eye(4),atol=1e-10))

    def test_nucleo_M8_y_escenario(self):
        self.assertEqual(len(self.c['varillas']),1)
        v=self.c['varillas'][0]
        self.assertEqual(v['nombre'],'M8x1.25');self.assertEqual(v['nucleo_referencia_m'],.006466)
        self.assertEqual(self.c['capas_m'],[.004])
        self.assertAlmostEqual(self.c['presion_pa']/1e6,2.25867,places=5)

    def test_convergencia_1440_y_equilibrio(self):
        d=self.df
        self.assertEqual(len(d),1440);self.assertTrue(d.convergio.all())
        self.assertLess(d.residuo_final_holgura_m.max(),1e-9)
        self.assertLess(d.cambio_final_fuerza_relativo.max(),1e-5)
        self.assertLess(d.residuo_equilibrio_fuerzas_n.max(),1e-6)
        self.assertLess(d.residuo_equilibrio_momentos_nm.max(),1e-6)
        self.assertTrue(np.allclose(d.fuerza_r1_n+d.fuerza_r2_n,d.fuerza_total_n))
        self.assertTrue(np.allclose(d.torque_r1_nm+d.torque_r2_nm,d.torque_total_nm))

    def test_no_coincidencia_forzada_maximos(self):
        d=self.df
        self.assertNotEqual(int(d.paso[d.fuerza_total_n.idxmax()]),int(d.paso[d.torque_total_nm.idxmax()]))
        self.assertGreater(abs(d.fuerza_total_n.max()-917.9962632879824),1e-3)

    def test_medio_disco_analitico(self):
        R=.003;Drod=.052;lc=.006;prof=(Drod-math.sqrt(Drod**2-4*lc**2))/2
        A,cr,ct=interseccion_disco_huella_variable(np.array([[.03,.003]]),R,(.02,.04),.004-prof,0,.03,Drod,.004,256)
        self.assertAlmostEqual(A[0]/(math.pi*R*R),.5,places=6)
        self.assertAlmostEqual(cr[0],.03,places=8)
        self.assertAlmostEqual(ct[0],.003-4*R/(3*math.pi),places=8)

    def test_centroides_todos_estados_dentro_region_y_fuerzas(self):
        xy=self.h[['x_mm','y_mm']].to_numpy()/1000;radios=np.linalg.norm(xy,axis=1)
        for row in self.df.itertuples(index=False):
            theta=math.radians(row.angulo_grados);co=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
            fs=0.;ts=0.
            for j,rod in enumerate(self.a['rodillos'],1):
                loc=coordenadas_locales(xy@co.T,rod['angulo_rad']);rc=rod['radio_posicion_mm']/1000
                g=getattr(row,f'holgura_r{j}_centro_m');slope=getattr(row,f'inclinacion_radial_r{j}_rad')
                area,cr,ct=interseccion_disco_huella_variable(loc,.003,(rc-.015,rc+.015),g,slope,rc,.052,.004,64)
                pos=area>1e-15;cc=np.c_[cr[pos],ct[pos]]
                self.assertTrue(np.all(np.linalg.norm(cc-loc[pos],axis=1)<=.003+1e-10))
                self.assertTrue(np.all((cr[pos]>=rc-.015-1e-10)&(cr[pos]<=rc+.015+1e-10)))
                lim=longitud_contacto_desde_holgura(g+slope*(cr[pos]-rc),.052,.004)/2
                self.assertTrue(np.all(abs(ct[pos])<=lim+1e-10))
                f=area*self.c['presion_pa'];fs+=f.sum();ts+=.1*np.dot(f,radios)
            self.assertAlmostEqual(fs,row.fuerza_total_n,places=4)
            self.assertAlmostEqual(ts,row.torque_total_nm,places=7)

    def test_contacto_nulo_y_simetria(self):
        loc=np.array([[.03,0],[.03,.004],[.03,-.004],[.08,.08]])
        A,r,t=interseccion_disco_huella_variable(loc,.003,(.015,.045),.0005,0,.03,.052,.004,128)
        self.assertAlmostEqual(A[1],A[2],places=12);self.assertAlmostEqual(t[1],-t[2],places=12)
        self.assertEqual(A[-1],0);self.assertTrue(np.isnan(t[-1]))

    def test_608_montaje_cargas_y_vida(self):
        m=pd.read_csv(D/'montaje_608_verificado.csv');self.assertEqual(len(m),4)
        self.assertTrue((m.asiento_diam_mm==22).all());self.assertGreater(m.margen_cilindro_activo_mm.min(),-1e-8)
        b=pd.read_csv(D/'rodamientos_608.csv');h=pd.read_csv(D/'cargas_608.csv.gz')
        for row in b.itertuples():
            v=h[h.id==row.id]
            self.assertAlmostEqual(row.Peq_n,np.mean(v.P_n**3)**(1/3),places=7)
            self.assertAlmostEqual(row.L10_millones_rev,(3300/row.Peq_n)**3,places=6)
            self.assertAlmostEqual(row.S0,1370/row.Frmax_n,places=10)
        self.assertGreater(b.S0.min(),1)

    def test_arbol_manivela_y_no_propiedades_inventadas(self):
        r=json.loads((D/'resumen_componentes.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(r['arbol']['L_m'],.235)
        self.assertAlmostEqual(r['manivela']['radio_m'],.165)
        self.assertIsNone(r['arbol']['grado']);self.assertIsNone(r['arbol']['factor_seguridad'])
        self.assertIsNone(r['apoyo_principal']['C0_n'])
        self.assertAlmostEqual(r['matriz']['area_apoyo_m2']*1e6,math.pi*(9.525**2-6.5**2),places=8)

    def test_FEM_nuevo_y_conservacion(self):
        f=pd.read_csv(D/'convergencia_FEM.csv')
        componentes=pd.read_csv(D/'serie_componentes.csv').set_index('paso')
        self.assertGreaterEqual(f.h_mm.nunique(),3)
        self.assertLess(f.residuo_relativo.max(),1e-8)
        self.assertLess(f.error_equilibrio_fuerzas_n.max(),1e-4)
        self.assertLess(f.error_equilibrio_momentos_Nmm.max(),1e-3)
        for r in f.itertuples():
            row=self.df[self.df.paso==r.paso].iloc[0]
            self.assertAlmostEqual(r.fuerza_aplicada_n,row.fuerza_total_n,places=4)
            self.assertAlmostEqual(r.torque_aplicado_Nmm/1000,row.torque_total_nm,places=7)
            self.assertAlmostEqual(r.momento_normal_aplicado_Nmm,componentes.loc[r.paso,'M_normales_nm']*1000,delta=1e-5)

    def test_FEM_patch_y_frontera_real(self):
        from fem_final import tensiones
        from skfem import MeshTet
        mesh=MeshTet(np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]]).T,np.array([[0,1,2,3]]).T)
        eps=np.diag([.001,.0002,-.0003]);u=mesh.p.T@eps
        sig,_=tensiones(mesh,u);E=200000;nu=.3;mu=E/(2*(1+nu));la=E*nu/((1+nu)*(1-2*nu))
        self.assertTrue(np.allclose(sig[0],2*mu*eps+la*np.trace(eps)*np.eye(3)))
        with np.load(D/'fem_h3_paso636.npz') as z:
            p=z['p'];u=z['u'];bottom=abs(p[:,1]-26)<1e-6;r=np.hypot(p[:,0],p[:,2])
            fixed=bottom&(r<=9.525+1e-6);outer=bottom&(r>9.525+1e-6)
            self.assertTrue(np.all(u[fixed]==0));self.assertGreater(np.linalg.norm(u[outer],axis=1).max(),1e-8)

    def test_validacion_numerica_y_aprobacion_condicionada(self):
        v=pd.read_csv(D/'validacion_numerica_3C.csv');self.assertTrue(v.todos_convergieron.all())
        self.assertLess(v.error_F_abs_n.max(),.1);self.assertLess(v.error_g_abs_m.max(),5e-9)
        r=json.loads((D/'resumen_final.json').read_text(encoding='utf-8'))['FEM']
        self.assertFalse(r['aprobacion_incondicional'])
        if r['convergencia_envolvente']:
            self.assertLessEqual(r['cambio_VM_rel'],.05);self.assertLessEqual(r['cambio_u_rel'],.05)
        else:self.assertIn('No cerrado',r['estado'])

    def test_latex_y_citas(self):
        bib=(D/'referencias_revision.bib').read_text(encoding='utf-8');keys=re.findall(r'@\w+\{([^,]+),',bib)
        self.assertEqual(len(keys),len(set(keys)))
        for p in D.glob('*.tex'):
            t=p.read_text(encoding='utf-8');t=re.sub(r'(?<!\\)%[^\n]*','',t);depth=0
            for c in re.findall(r'(?<!\\)[{}]',t):
                depth+=1 if c=='{' else -1;self.assertGreaterEqual(depth,0)
            self.assertEqual(depth,0)
            for group in re.findall(r'\\cite\{([^}]+)\}',t):self.assertTrue(all(k in keys for k in group.split(',')))
            self.assertCountEqual(re.findall(r'\\begin\{([^}]+)\}',t),re.findall(r'\\end\{([^}]+)\}',t))
        an=(D/'anexos_A3_A8.tex').read_text(encoding='utf-8')
        for i in range(3,9):self.assertIn(f'anexo_A{i}',an)

if __name__=='__main__':unittest.main(verbosity=2)
