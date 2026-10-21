"""DCL simbólicos. Cargas de 3C; no representa apoyos inventados."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
p=Path(__file__).parent/'resultados'
fig,axs=plt.subplots(1,2,figsize=(12,6.7),layout='constrained')
for ax in axs:
 ax.set_aspect('equal');ax.set_xlim(-4.5,4.5);ax.set_ylim(-4.8,5.1);ax.axis('off')

def arrow(ax,x,y,dx,dy,label,tx=0,ty=0):
 ax.annotate('',xy=(x+dx,y+dy),xytext=(x,y),arrowprops=dict(arrowstyle='->',lw=1.8,color='black'))
 ax.text(x+dx+tx,y+dy+ty,label,fontsize=12)

ax=axs[0];ax.set_title('A. MATRIZ AISLADA (CORTE CONCEPTUAL)',fontsize=12,pad=15)
ax.add_patch(Rectangle((-3.4,-.5),6.8,1.0,facecolor='white',edgecolor='black',linewidth=1.5,hatch='///'))
ax.add_patch(Rectangle((-.55,-.5),1.1,1,facecolor='white',edgecolor='black',linewidth=1.2))
ax.plot([0,0],[-2.7,3.8],'k--',linewidth=.7)
arrow(ax,-2.3,2.5,0,-1.95,r'$F_1$',.14,.10)
arrow(ax,2.3,2.5,0,-1.95,r'$F_2$',.14,.10)
arrow(ax,0,-2.2,0,1.55,r'$R_z\;(?\;\mathrm{acople})$',.2,-.15)
ax.text(0,-3.3,'Momento de normales = resultante',ha='center',fontsize=10)
ax.text(0,-3.75,r'$M_x,\;M_y$ por excentricidad',ha='center',fontsize=12)
ax.text(0,1.1,'Reacciones y transmisión axial\npendientes de definir en la unión',ha='center',fontsize=10)
ax.annotate('Par de transmisión',xy=(1.1,-.05),xytext=(1.3,-2.4),arrowprops=dict(arrowstyle='->',lw=1),fontsize=10)

ax=axs[1];ax.set_title('B. ÁRBOL VERTICAL AISLADO (ESQUEMA)',fontsize=12,pad=15)
ax.add_patch(Rectangle((-.6,-2.85),1.2,5.9,facecolor='white',edgecolor='black',linewidth=1.4))
ax.plot([0,0],[-4,4.5],'k--',linewidth=.8)
ax.add_patch(Rectangle((-1.1,3.1),2.2,.35,fill=False,edgecolor='black',linewidth=1.3))
arrow(ax,0,4.55,0,-1.0,r'$F_z$',.2,-.12)
arrow(ax,-.6,-3.7,-1.9,0,r'$T_1$',-.5,.2)
arrow(ax,-.6,-4.2,-1.9,0,r'$T_2$',-.5,.2)
ax.text(0,-4.55,'Correas en dirección horizontal (simbolizado)',ha='center',fontsize=9)
ax.text(1.0,2.1,r'$M_x,\, M_y,\, T$',fontsize=13)
ax.text(1.0,1.45,'Interfaz matriz–árbol',fontsize=10)
ax.text(1.0,-.55,'Apoyos axial/radiales',fontsize=10)
ax.text(1.0,-.96,'y distancias: pendientes',fontsize=10)
ax.annotate('',xy=(.5,-1.8),xytext=(1.2,-.98),arrowprops=dict(arrowstyle='->',lw=1))
fig.suptitle('DCL DE TRANSFERENCIA DE CARGAS — NO FIJA APOYOS NO DOCUMENTADOS',fontsize=13)
fig.savefig(p/'dcl_provisionales_matriz_arbol.png',dpi=180,bbox_inches='tight')
plt.close(fig)
