"""Comprobaciones mínimas que no ejecutan/modifican modelos previos."""
from pathlib import Path
import math
import pandas as pd
b=Path(__file__).resolve().parent
s=pd.read_csv(b/'fuentes'/'series_resultantes_matriz_eje_4A.csv')
a=pd.read_csv(b/'resultados'/'verificaciones_nominales_eje.csv')
c=pd.read_csv(b/'resultados'/'instantes_criticos_correlacionados.csv')
assert len(s)==1440
assert math.isclose(s.Fz_normal_N.max()/1000,14.070987,rel_tol=1e-6)
assert math.isclose(s.T_resistente_3C_Nm.mean(),77.623586,rel_tol=1e-6)
assert math.isclose(s.M_flexion_normales_Nm.max(),153.801516,rel_tol=1e-6)
assert math.isclose(c.loc[c.caso=='M_normal_max','angulo_grados'].iloc[0],269.25)
assert math.isclose(a.loc[a.d_mm==50,'von_mises_axial_torsion_max_MPa'].iloc[0],9.5258,rel_tol=1e-4)
print('OK — 5 validaciones, sin alterar fuentes.')
