"""DCL preliminares diagramáticos sin cotas ni posiciones ficticias de rodamientos."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Arc
O=Path(__file__).resolve().parent/'resultados'; O.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,ax=plt.subplots(1,3,figsize=(14,5))
for a in ax:
 a.set_xlim(0,10);a.set_ylim(0,10);a.set_aspect('equal');a.axis('off')
 for sp in a.spines.values(): sp.set_visible(False)
def arrow(a,x,y,dx,dy,label,lx=None,ly=None):
 a.arrow(x,y,dx,dy,head_width=.22,head_length=.32,width=.025,length_includes_head=True,color='black')
 a.text(x+dx if lx is None else lx,y+dy if ly is None else ly,label,fontsize=10)
# Disco sobre apoyo condicional
A=ax[0];A.text(0.15,9.4,'1. MATRIZ AISLADA',weight='bold')
A.add_patch(Rectangle((1.2,4.4),7.6,.8,fill=False,lw=2,hatch='///'))
A.plot([5,5],[3.4,6.4],'k--',lw=.8)
arrow(A,2.6,7.7,0,-2.55,r'$N_1$',2.2,7.8)
arrow(A,7.4,7.7,0,-2.55,r'$N_2$',7.4,7.8)
A.add_patch(Rectangle((4.3,3.6),1.4,.8,fill=False,lw=1.5))
arrow(A,5,2.3,0,1.25,r'$R_z$ (solo si hay apoyo)',5.5,2.25)
A.text(1.3,1.1,'El resalte NO es empotramiento.',fontsize=8)
# Arbol con matriz y polea; apoyos no localizados
B=ax[1];B.text(.15,9.4,'2. ÁRBOL VERTICAL (cargas)',weight='bold')
B.add_patch(Rectangle((3.9,2.15),1.25,5.7,fill=False,lw=1.8))
B.add_patch(Rectangle((1.4,7.1),6.2,.5,fill=False,lw=2,hatch='///'))
B.add_patch(Rectangle((2.9,1.8),3.3,.33,fill=False,lw=2))
arrow(B,4.52,8.75,0,-1.03,r'$F_z$',5,8.4)
arrow(B,4.52,6.9,2.7,0,r'$F_{t,net}$',7.2,7.18)
arrow(B,6.2,2,-3.0,0,r'$F_{correa}$',0.2,1.6)
B.text(.5,4.6,'Apoyos A y B:\nposición y tipo\npor confirmar',fontsize=8)
B.text(4.75,5.05,r'$M_x,\,M_y,\,T$',fontsize=11)
# polea tensiones paralelas colineales en dirección, par por diferencia
C=ax[2];C.text(.15,9.4,'3. POLEA / CORREAS',weight='bold')
C.add_patch(Rectangle((4.2,3.1),1.5,4.5,fill=False,hatch='///',lw=2))
C.add_patch(Rectangle((2.7,5),4.5,.45,fill=False,lw=1.5))
C.plot([1,8],[5.22,5.22],'k--',alpha=.3)
arrow(C,4.2,7,-3,0,r'$T_1$',.4,7.35)
arrow(C,4.2,3.75,-3,0,r'$T_2$',.4,3.4)
C.text(3.4,1.5,'Dos ramales aproximadamente\nparalelos y hacia el motor',ha='center',fontsize=9)
fig.suptitle('DCL DE REFERENCIA · SOLO FUERZAS Y VÍNCULOS CONFIRMABLES',fontsize=13,weight='bold')
fig.tight_layout(rect=(0,.04,1,.93))
fig.savefig(O/'dcl_parametrico.png',dpi=170,facecolor='white')
fig.savefig(O/'dcl_parametrico.svg',facecolor='white')
plt.close(fig)
