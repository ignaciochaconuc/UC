#!/usr/bin/env python3
"""Exporta un SVG de la sección real de la malla, sin dependencias externas."""
from pathlib import Path
import re
r=Path(__file__).resolve().parent
m=r/'mesh2d/constant/polyMesh'
points=[tuple(map(float,x.split())) for x in re.findall(r'^\(([-+0-9.eE ]+)\)$',(m/'points').read_text(),re.M)]
faces=[list(map(int,x.split())) for x in re.findall(r'^\d+\(([0-9 ]+)\)$',(m/'faces').read_text(),re.M)]
b=(m/'boundary').read_text()
f=re.search(r'front\s*\{(.*?)\}',b,re.S)[1]
start=int(re.search(r'startFace\s+(\d+)',f)[1]); count=int(re.search(r'nFaces\s+(\d+)',f)[1])
polys=[]
for face in faces[start:start+count]:
 xy=[points[i][:2] for i in face]
 if any(2<=x<=18 and 5<=y<=15 for x,y in xy):
  polys.append('<polygon points="'+' '.join(f'{x:.6f},{20-y:.6f}' for x,y in xy)+'"/>')
s='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="1.8 4.8 16.4 10.4" width="1200" height="760">
<rect x="1.8" y="4.8" width="16.4" height="10.4" fill="white"/>
<g fill="none" stroke="#304a60" stroke-width="0.009">'''+''.join(polys)+'''</g>
<circle cx="6" cy="10" r="1" fill="#ccc" stroke="#222" stroke-width="0.02"/>
</svg>'''
(r/'malla_cilindro.svg').write_text(s)
print('Vista de la malla exportada a malla_cilindro.svg')
