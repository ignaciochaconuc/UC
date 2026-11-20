"""Pruebas de la memoria; no se importa ni ejecuta ningún modelo anterior."""
import ast
import csv
import json
import math
import re
import unittest
from pathlib import Path

from reproducir_memoria import (D, S, leer_base, factor_estatico,
                                convertir_kt, verificar_historicos)


class MemoriaKt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((D/'resumen.json').read_text(encoding='utf-8'))

    def test_conservacion_812_archivos(self):
        self.assertEqual(verificar_historicos(), {'archivos_verificados':812,'alterados':0})

    def test_escenario_unico_y_estados(self):
        rows,c,v,m = leer_base()
        self.assertEqual(len(rows),1440)
        self.assertEqual(m['clase'],'8.8')
        self.assertEqual(v['nucleo_referencia_m'],.006466)
        self.assertAlmostEqual(c['presion_pa']/1e6,2.25867,places=5)

    def test_flexion_momento_correlacionado(self):
        r=self.r
        sigma=32*r['momento_resultante_correspondiente_nm']/(math.pi*r['diamenor_referencia_m']**3)
        self.assertAlmostEqual(sigma/r['sigma_nominal_raiz_pa'],1.,places=12)
        self.assertAlmostEqual(r['I_raiz_m4'],math.pi*.006466**4/64,places=20)

    def test_bases_iguales_y_sin_doble_conteo(self):
        r=self.r
        for kt in [1.,1.5,2.5,3.]:
            kg=convertir_kt(kt,.006466,.008)
            self.assertAlmostEqual(kg*r['sigma_nominal_base_mayor_pa']/
                                   (kt*r['sigma_nominal_raiz_pa']),1.,places=12)
        self.assertAlmostEqual(r['conversion_Kt_mayor_sobre_Kt_raiz'],1.8939253634,places=9)

    def test_unidades_y_umbral(self):
        r=self.r;k=r['Kt_raiz_umbral_inicio_fluencia_flexion']
        self.assertAlmostEqual(factor_estatico(640e6,r['sigma_nominal_raiz_pa'],k),1.,places=12)
        self.assertAlmostEqual(factor_estatico(640,r['sigma_nominal_raiz_pa']/1e6,1.5),
                               factor_estatico(640e6,r['sigma_nominal_raiz_pa'],1.5),places=12)

    def test_entradas_invalidas(self):
        for k in [0.,-.1,.5,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):factor_estatico(640e6,315e6,k)
        with self.assertRaises(ValueError):convertir_kt(1.5,.008,.006466)
        with self.assertRaises(ValueError):factor_estatico(-640e6,315e6,1.5)

    def test_casos_no_mezclados(self):
        with (D/'casos_correlacionados.csv').open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        cases={r['maximo_de']:r for r in rows}
        self.assertEqual(cases['sigma_nominal_max_pa']['paso'],'541')
        self.assertEqual(cases['fuerza_total_n']['paso'],'476')
        self.assertEqual(cases['flecha_max_m']['paso'],'301')
        self.assertLess(float(cases['sigma_nominal_max_pa']['torque_total_nm']),
                        float(cases['torque_total_nm']['torque_total_nm']))

    def test_no_aprobacion_o_kt_seleccionado(self):
        r=self.r
        for k in ['Kt_raiz_seleccionado','Kf_seleccionado',
                  'factor_seguridad_estatico_definitivo','factor_seguridad_fatiga_definitivo']:
            self.assertIsNone(r[k])
        self.assertIs(r['aprobado'],False)
        with (D/'sensibilidad_Kt_sin_seleccion.csv').open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        self.assertTrue(all(r['rango_fisico_validado']=='False' and r['aprobacion']=='False' for r in rows))
        self.assertLess(float(rows[-1]['n_y_condicional']),1.)

    def test_no_importa_simuladores(self):
        tree=ast.parse((D/'reproducir_memoria.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                self.assertFalse('acoplado' in (node.module or '') or 'peletizadora' in (node.module or ''))
            if isinstance(node,ast.Import):
                self.assertTrue(all('acoplado' not in n.name and 'peletizadora' not in n.name for n in node.names))

    def test_main_solo_configuracion_elegida(self):
        t=(D/'seccion_principal_M8_88_h4.tex').read_text(encoding='utf-8')
        self.assertIn('8.8 candidata',t)
        self.assertIn('4 mm',t)
        for otro in ['M6','10.9','capa de 1 mm','capa de 2 mm']:
            self.assertNotIn(otro,t)

    def test_tabla_latex_coincide_con_calculo_sin_redondear(self):
        text=(D/'anexo_justificacion_Kt_M8.tex').read_text(encoding='utf-8')
        table=re.findall(r'^([\d,]+) & ([\d,]+) & ([\d,]+) &',text,re.M)
        self.assertEqual(len(table),5)
        for kt,sigma,n in table:
            k=float(kt.replace(',','.'))
            self.assertAlmostEqual(float(sigma.replace(',','.')),k*self.r['sigma_nominal_raiz_pa']/1e6,delta=.006)
            self.assertAlmostEqual(float(n.replace(',','.')),factor_estatico(640e6,self.r['sigma_nominal_raiz_pa'],k),delta=.0006)

    def test_latex_llaves_citas_y_bibliografia(self):
        bib=(D/'referencias_Kt.bib').read_text(encoding='utf-8')+'\n'+(S/'fisica/referencias_resistencia_m8.bib').read_text(encoding='utf-8')
        keys=re.findall(r'@\w+\{([^,]+),',bib)
        self.assertEqual(len(keys),len(set(keys)))
        for name in ['seccion_principal_M8_88_h4.tex','anexo_justificacion_Kt_M8.tex','memoria_Kt_M8.tex']:
            text=(D/name).read_text(encoding='utf-8')
            text=re.sub(r'(?<!\\)%[^\n]*','',text)
            depth=0
            for token in re.findall(r'(?<!\\)[{}]',text):
                depth += 1 if token=='{' else -1
                self.assertGreaterEqual(depth,0)
            self.assertEqual(depth,0)
            self.assertCountEqual(re.findall(r'\\begin\{([^}]+)\}',text),re.findall(r'\\end\{([^}]+)\}',text))
            for group in re.findall(r'\\cite\{([^}]+)\}',text):
                self.assertTrue(all(k in keys for k in group.split(',')))


if __name__=='__main__':
    unittest.main(verbosity=2)
