"""Acercamientos de la superficie del sólido 7 con campos nodales calculados."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inspeccionar import ROOT

fig,axes=plt.subplots(3,1,figsize=(8,10.5))
window=np.array([-148.7,-323.4])
limit=max(json.loads((ROOT/f'componentes_t{t:.1f}_h6'/'resultados.json').read_text())['von_mises_max_nodal_MPa'] for t in [2.,2.5,3.])
for ax,t in zip(axes,[2.,2.5,3.]):
    folder=ROOT/f'componentes_t{t:.1f}_h6'; m=np.load(folder/'solido_07.npz'); xyz=m['xyz']; ids=m['nodes']; conv={int(n):k for k,n in enumerate(ids)}
    offset=sum(len(np.load(folder/f'solido_{i:02}.npz')['nodes']) for i in range(1,7))
    values=np.load(folder/'campos.npz')['von_mises'][offset:offset+len(ids)]
    result=json.loads((folder/'resultados.json').read_text()); center=np.array(result['max_stress_element_centroid_mm']); tris=[]
    for face in json.loads((folder/'solido_07_superficies.json').read_text()):
        for raw in face['triangles']:
            ns=[conv[n] for n in raw]
            for sub in [(0,3,5),(3,1,4),(5,4,2),(3,4,5)]: tris.append([ns[k] for k in sub])
    tris=np.array(tris); means=xyz[tris].mean(axis=1)
    keep=np.linalg.norm(means[:,:2]-window,axis=1)<3.5
    tris=tris[keep]; tris=tris[np.argsort(xyz[tris,2].mean(axis=1))[::-1]]
    im=ax.tripcolor(xyz[:,0],xyz[:,1],tris,values,shading='gouraud',cmap='turbo',vmin=0,vmax=limit)
    ax.triplot(xyz[:,0],xyz[:,1],tris,color='.2',linewidth=.25,alpha=.5)
    ax.plot(center[0],center[1],'k*',markersize=8)
    p=np.array(result['max_nodal_stress_position_mm'])
    ax.scatter(p[0],p[1],c=[result['von_mises_max_nodal_MPa']],cmap='turbo',vmin=0,vmax=limit,s=40,edgecolors='black',linewidths=.7,zorder=10)
    ax.set(xlim=(window[0]-2.2,window[0]+2.2),ylim=(window[1]-1.6,window[1]+1.6),xlabel='X global [mm]',ylabel='Y global [mm]',title=f't={t:g} mm · vaina derecha (sólido 7)\nEstrella: elemento crítico; círculo: nodo de máximo nodal')
    ax.title.set_fontsize(11)
    ax.set_aspect('equal'); fig.colorbar(im,ax=ax,label='von Mises nodal [MPa]',shrink=.8)
fig.suptitle('Unión vaina–pedalier: campos reales y discretización\nProyección de superficies; aristas superpuestas. No prueba convergencia.',fontsize=11)
fig.tight_layout(rect=(0,0,1,.94)); fig.savefig(ROOT/'detalle_union_critica.png',dpi=180); plt.close(fig)
