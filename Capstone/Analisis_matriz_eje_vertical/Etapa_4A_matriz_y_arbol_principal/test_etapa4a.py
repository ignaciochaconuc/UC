"""Checks independientes de la salida de 4A, no modifica etapas anteriores."""
from pathlib import Path
import numpy as np
import pandas as pd
r=Path(__file__).parent/'resultados'
s=pd.read_csv(r/'series_resultantes_matriz_eje.csv')
c=pd.read_csv(r/'casos_criticos_correlacionados.csv')
a=pd.read_csv(r/'fuerzas_por_agujero_casos_criticos.csv')
e=pd.read_csv(r/'secciones_eje_nominales.csv')
assert len(s)==1440
assert abs(s.Fz_normal_N.max()-14070.987476941267)<1e-3
assert abs(s.T_resistente_3C_Nm.max()-88.92396579145439)<1e-3
assert abs(s.Fz_normal_N.mean()-12398.878745636162)<1e-3
assert abs(s.M_flexion_normales_Nm.max()-153.802)<.05
assert abs(c.loc[c.evento=='max_momento_normales','Fz_normal_N'].item()-12864)<1
for evento,x in a.groupby('evento'):
    corr=c.loc[c.evento==evento].iloc[0]
    assert abs(x.fuerza_normal_N.sum()-corr.Fz_normal_N)<1.0
assert not e.isna().any().any()
print('VALIDACIÓN 4A: historial, correlación y reconstrucción por perforación OK')
