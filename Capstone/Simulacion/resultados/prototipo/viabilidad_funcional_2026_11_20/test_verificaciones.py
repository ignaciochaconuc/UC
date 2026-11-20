import unittest,json,math,re,ast
from pathlib import Path
import numpy as np
import pandas as pd
from calculos import D,S,conservar,entradas,seccion_arbol,presion_anular
from fem_matriz import tensiones,recuperar_cargas,malla
from skfem import MeshTet


class Verificaciones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a,cls.df=entradas()
        cls.r=json.loads((D/'resumen_integrado.json').read_text(encoding='utf-8'))

    def test_historicos_intactos(self):
        self.assertEqual(conservar(),{'archivos_verificados':832,'alterados':0})

    def test_unico_escenario(self):
        self.assertEqual(len(self.df),1440)
        self.assertTrue((self.df.varilla=='M8x1.25').all())
        self.assertTrue((self.df.capa_m==.004).all())
        self.assertAlmostEqual(self.r['Tmax_nm'],2.780389530933798,places=10)

    def test_axial_torsion_mismo_paso(self):
        ar=seccion_arbol(self.df.fuerza_total_n,self.df.torque_total_nm)
        i=int(np.argmax(ar['sigma_VM_pa']))
        self.assertEqual(int(self.df.paso.iloc[i]),476)
        self.assertAlmostEqual(ar['sigma_VM_pa'][i],13995816.169966592,places=5)

    def test_escalamiento_seccion(self):
        a=seccion_arbol(np.array([918.]),np.array([2.78]),d=.0127)
        b=seccion_arbol(np.array([918.]),np.array([2.78]),d=.0254)
        self.assertAlmostEqual(float(a['sigma_axial_pa'][0]/b['sigma_axial_pa'][0]),4.)
        self.assertAlmostEqual(float(a['tau_torsion_pa'][0]/b['tau_torsion_pa'][0]),8.)
        self.assertAlmostEqual(float(a['acortamiento_m'][0]/b['acortamiento_m'][0]),4.)

    def test_rechazo_entradas(self):
        with self.assertRaises(ValueError):seccion_arbol(np.array([1.]),np.array([1.,2.]))
        with self.assertRaises(ValueError):seccion_arbol(np.array([1.]),np.array([1.]),d=-1.)
        with self.assertRaises(ValueError):presion_anular(918,0,.012,.006)
        with self.assertRaises(ValueError):malla(0)

    def test_contacto_axial_global(self):
        m=self.r['matriz']
        self.assertGreater(m['p_apoyo_min_pa'],0)
        self.assertLess(m['excentricidad_max_m'],m['nucleo_central_m'])
        self.assertAlmostEqual(math.pi*(11.5**2-6.5**2),282.7433388230814,places=7)

    def test_equilibrio_608_y_peso(self):
        b=pd.read_csv(D/'serie_rodamientos.csv.gz')
        sums=b.groupby('paso').F_normal_contacto_n.sum()
        self.assertTrue(np.allclose(sums,self.df.fuerza_total_n,atol=1e-7))
        tabla=pd.read_csv(D/'rodamientos_608.csv')
        for row in tabla.itertuples():
            data=b[b.id==row.id]
            p=(np.mean(data.P_dinamica_n**3))**(1/3)
            self.assertAlmostEqual(p,row.P_equivalente_n,places=7)
            self.assertAlmostEqual(row.S0_referencia,1370/data.Fr_n.max(),places=9)
            self.assertAlmostEqual(row.L10_millones_vueltas_rodillo,(3300/p)**3,places=6)
            self.assertTrue(np.allclose(data.P_dinamica_n,1.2*data.Fr_n))
            self.assertTrue(np.isnan(row.L10h))

    def test_mano_y_par_no_confundir_torsion_eje_transversal(self):
        self.assertAlmostEqual(self.r['Fmanual_ideal_max_n']*.165,self.r['Tmax_nm'],places=12)
        self.assertAlmostEqual(self.r['manivela']['fuerza_tangencial_union_al_arbol_n']*.0127/2,self.r['Tmax_nm'],places=12)
        p=pd.read_csv(D/'accionamiento_y_perdidas.csv')
        self.assertTrue(np.allclose(p.fuerza_mano_n*.165*p.eficiencia_mecanica_hipotetica,self.r['Tmax_nm']))

    def test_fem_patch_afin_y_giro_rigido(self):
        mesh=MeshTet(np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]]).T,np.array([[0,1,2,3]]).T)
        p=mesh.p.T;eps=np.diag([.001,.0002,-.0003]);u=p@eps
        sig,_=tensiones(mesh,u)
        E=200000;nu=.3;mu=E/(2*(1+nu));la=E*nu/((1+nu)*(1-2*nu))
        expected=2*mu*eps+la*np.trace(eps)*np.eye(3)
        self.assertTrue(np.allclose(sig[0],expected))
        rot=np.cross(np.tile([.01,.02,.03],(len(p),1)),p)+np.array([3.,2.,1.])
        _,vm=tensiones(mesh,rot)
        self.assertLess(vm.max(),1e-8)

    def test_cargas_recuperadas_sin_iterar(self):
        holes=pd.read_csv(S/'resultados/prototipo/revision_ensamble_2026_11_19/perforaciones_STEP.csv')
        for paso in self.r['FEM_matriz']['casos_correlacionados']:
            row=self.df[self.df.paso==paso].iloc[0];F,C=recuperar_cargas(row,self.a,holes)
            self.assertAlmostEqual(F.sum(),row.fuerza_total_n,places=4)
            self.assertAlmostEqual(.1*np.dot(F,holes.radio_posicion_mm)/1000,row.torque_total_nm,places=7)

    def test_conservacion_FEM_y_reacciones(self):
        f=pd.read_csv(D/'convergencia_FEM_completa.csv')
        self.assertGreaterEqual(f.h_mm.nunique(),3)
        self.assertLess(f.residuo_relativo.max(),1e-8)
        self.assertLess(f.error_equilibrio_fuerzas_n.max(),1e-4)
        self.assertLess(f.error_equilibrio_momentos_Nmm.max(),1e-3)
        self.assertGreaterEqual(f.reaccion_axial_negativa_n.min(),0.)
        self.assertAlmostEqual(self.r['FEM_matriz']['reaccion_axial_sentido_traccion_suma_max_n'],
                               f[f.h_mm==f.h_mm.min()].reaccion_axial_negativa_n.max(),places=9)
        for row in f.itertuples():
            old=self.df[self.df.paso==row.paso].iloc[0]
            self.assertAlmostEqual(row.fuerza_aplicada_n,old.fuerza_total_n,places=4)
            self.assertAlmostEqual(row.torque_aplicado_Nmm/1000,old.torque_total_nm,places=7)

    def test_ninguna_aprobacion_sin_convergencia(self):
        m=self.r['FEM_matriz']
        if m['convergencia_envolvente_casos']:
            self.assertLessEqual(m['cambio_VM_ultimas'],.05)
            self.assertLessEqual(m['cambio_u_ultimas'],.05)
            self.assertGreater(m['n_304_validado_bajo_hipotesis'],1.)
        else:self.assertIsNone(m['n_304_validado_bajo_hipotesis'])
        self.assertFalse(m['aprobacion_incondicional'])
        self.assertIsNone(self.r['arbol']['factor_seguridad'])
        self.assertIsNone(self.r['manivela']['factor_seguridad'])

    def test_geometria_FEM_contra_volumen_CAD(self):
        v=next(x['volumen_mm3'] for x in self.a['inventario'] if x['id']==8)
        f=pd.read_csv(D/'convergencia_FEM_completa.csv');fine=f[f.h_mm==f.h_mm.min()]
        self.assertLess(abs(fine.volumen_mm3.iloc[0]/v-1),.01)

    def test_centroides_no_fisicos_no_se_silencian(self):
        d=pd.read_csv(D/'cargas_canales_h3_paso476.csv')
        self.assertTrue(d.centroide_individual_legado_fuera_agujero.any())
        self.assertLess(d.error_centroide_mm.max(),1e-4)
        self.assertLess(np.hypot(d.desplazamiento_equivalente_x_mm,d.desplazamiento_equivalente_y_mm).max(),.1)

    def test_no_runner_acoplado(self):
        for name in ['calculos.py','fem_matriz.py']:
            tree=ast.parse((D/name).read_text(encoding='utf-8'))
            self.assertFalse(any(isinstance(x,ast.Attribute) and x.attr=='simular' for x in ast.walk(tree)))
            self.assertNotIn('ModeloAcoplado',(D/name).read_text(encoding='utf-8').replace('nunca ModeloAcoplado',''))

    def test_latex_integrable(self):
        keys=re.findall(r'@\w+\{([^,]+),',(D/'referencias_revision.bib').read_text(encoding='utf-8'))
        self.assertEqual(len(keys),len(set(keys)))
        for name in ['seccion_ingenieria_detalles.tex','anexo_memoria_mecanica.tex','memoria_independiente.tex']:
            text=(D/name).read_text(encoding='utf-8');text=re.sub(r'(?<!\\)%[^\n]*','',text)
            depth=0
            for t in re.findall(r'(?<!\\)[{}]',text):
                depth+=1 if t=='{' else -1;self.assertGreaterEqual(depth,0)
            self.assertEqual(depth,0)
            self.assertCountEqual(re.findall(r'\\begin\{([^}]+)\}',text),re.findall(r'\\end\{([^}]+)\}',text))
            for cs in re.findall(r'\\cite\{([^}]+)\}',text):self.assertTrue(all(c in keys for c in cs.split(',')))
            self.assertNotIn('VALSTRESS',text)


if __name__=='__main__':unittest.main(verbosity=2)
