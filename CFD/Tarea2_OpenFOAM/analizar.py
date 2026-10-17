#!/usr/bin/env python3
"""Estadísticas temporales ponderadas; elimina tiempos duplicados de reinicios."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'resultados'; OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'figure.dpi':150})

def load(re):
    files=sorted((ROOT/f'Re{re}/postProcessing/forceCoeffs').glob('*/forceCoeffs.dat'),key=lambda p:float(p.parent.name))
    if not files:
        return np.atleast_2d(np.loadtxt(OUT/f'coeficientes_Re{re}.csv', delimiter=',', skiprows=1))
    a=np.concatenate([np.atleast_2d(np.loadtxt(p)) for p in files])
    # Mantener el último registro cuando un reinicio repite un tiempo.
    _,idx=np.unique(a[:,0][::-1],return_index=True)
    a=a[len(a)-1-idx];return a[np.argsort(a[:,0])]

def window(a,lo,hi):
    ts=np.r_[lo,a[(a[:,0]>lo)&(a[:,0]<hi),0],hi]
    return np.column_stack([ts]+[np.interp(ts,a[:,0],a[:,i]) for i in range(1,a.shape[1])])

def stats(a,lo,hi):
    b=window(a,lo,hi);t=b[:,0];cd=b[:,2];cl=b[:,3]
    avg=lambda y:float(np.trapz(y,t)/(hi-lo))
    cm=avg(cl)
    rms=avg((cl-cm)**2)**0.5
    v=cl-cm
    ix=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    crossings=t[ix]-v[ix]*(t[ix+1]-t[ix])/(v[ix+1]-v[ix])
    periods=np.diff(crossings)
    f=float(1/np.mean(periods)) if len(periods)>1 else None
    # FFT uniforme, con ventana Hann; corroboración independiente de cruces.
    tu=np.arange(lo,hi,0.02);vu=np.interp(tu,t,cl);vu-=np.mean(vu)
    ff=np.fft.rfftfreq(len(tu),0.02)
    power=abs(np.fft.rfft(vu*np.hanning(len(vu))))**2
    fi=int(np.argmax(power[1:])+1)
    return dict(Cd_medio=avg(cd),Cl_medio=cm,Cl_rms=rms,
                frecuencia_Hz=f,St=2*f if f else None,
                ciclos_completos=len(periods),periodo_s=1/f if f else None,
                frecuencia_FFT_Hz=float(ff[fi]))

rows=[];details={}
fig,axs=plt.subplots(4,2,figsize=(12,10),sharex=True)
for row,re in enumerate([100,1000,10000,100000]):
    a=load(re);s=stats(a,200,400);w1=stats(a,200,300);w2=stats(a,300,400)
    s.update(Re=re,modelo='Laminar 2D' if re<10000 else 'URANS SST 2D',
             cambio_Cd_pct=100*abs(w2['Cd_medio']-w1['Cd_medio'])/abs(w1['Cd_medio']),
             cambio_Clrms_pct=100*abs(w2['Cl_rms']-w1['Cl_rms'])/w1['Cl_rms'])
    rows.append(s);details[re]={'global_200_400':s,'ventana_200_300':w1,'ventana_300_400':w2}
    for col,(idx,label) in enumerate([(2,'Cd'),(3,'Cl')]):
        ax=axs[row,col];ax.plot(a[::4,0],a[::4,idx],lw=.65)
        ax.axvspan(200,400,color='green',alpha=.09)
        ax.set_ylabel(f'Re={re}\n{label}');ax.grid(alpha=.25)
        if idx==2:ax.set_ylim(bottom=0,top=max(2.5,1.3*s['Cd_medio']))
    fig2,ax2=plt.subplots(2,1,figsize=(10,5),sharex=True)
    b=window(a,300,400)
    for ax,idx,label in zip(ax2,[2,3],['Cd','Cl']):
        ax.plot(b[:,0],b[:,idx],lw=1);ax.set_ylabel(label);ax.grid(alpha=.3)
    ax2[-1].set_xlabel('Tiempo [s]');fig2.suptitle(f'Re={re} — últimos 100 s')
    fig2.tight_layout();fig2.savefig(OUT/f'fuerzas_Re{re}.png');plt.close(fig2)
    np.savetxt(OUT/f'coeficientes_Re{re}.csv',a,delimiter=',',header='t,Cm,Cd,Cl,Cl_frente,Cl_atras',comments='')
axs[-1,0].set_xlabel('Tiempo [s]');axs[-1,1].set_xlabel('Tiempo [s]')
fig.suptitle('Evolución de fuerzas — intervalo de análisis sombreado: 200–400 s')
fig.tight_layout();fig.savefig(OUT/'fuerzas_comparacion.png');plt.close(fig)
with (OUT/'resumen.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
(OUT/'estadisticas.json').write_text(json.dumps(details,indent=2))
lines=['# Resultados de las cuatro simulaciones\n',
'Estadísticas ponderadas por tiempo entre 200 y 400 s (paso adaptativo). La frecuencia se calcula con cruces ascendentes de Cl respecto de su media; se contrasta con FFT sobre una señal interpolada uniformemente.\n',
'| Re | Modelo | Cd medio | Cl medio | Cl RMS | f [Hz] | St | Cambio Cd [%] | Cambio Cl RMS [%] |',
'|---:|---|---:|---:|---:|---:|---:|---:|---:|']
for s in rows:
    lines.append(f"| {s['Re']} | {s['modelo']} | {s['Cd_medio']:.5f} | {s['Cl_medio']:.5f} | {s['Cl_rms']:.5f} | {s['frecuencia_Hz']:.5f} | {s['St']:.4f} | {s['cambio_Cd_pct']:.3f} | {s['cambio_Clrms_pct']:.3f} |")
lines+=['\nLos cambios comparan ventanas 200–300 y 300–400 s; no son estimaciones del error físico ni pruebas de independencia de malla. La media de Cl puede no ser exactamente cero por usar ventanas con ciclos incompletos.',
'\nRe1000 es laminar 2D: no resuelve la transición tridimensional real. Los casos SST son URANS 2D y no resuelven las estructuras turbulentas 3D. El cilindro está confinado en un canal con D/H=0.1, paredes no deslizantes y entrada uniforme; no comparar directamente con un cilindro no confinado.',
'\nLa menor Cd obtenida a Re100000 no demuestra una crisis de arrastre: revisar sensibilidad a SST, malla y tratamiento de pared antes de atribuirle un mecanismo físico.',
'\nPendientes: sensibilidad espacial y temporal, y+ desarrollado, balance de caudal y longitud de recirculación del campo medio. Las imágenes instantáneas no representan el campo medio.']
(OUT/'RESUMEN.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[:9]))

# Comprobaciones del campo final, si ya se ejecutó foamPostProcess.
checks=[]
for re in [100,1000,10000,100000]:
    rates=[]
    for patch in ['inlet','outlet']:
        p=ROOT/f'Re{re}/postProcessing/patchFlowRate(patch={patch})/400/surfaceFieldValue.dat'
        if p.exists():rates.append(float(np.atleast_2d(np.loadtxt(p))[-1,1]))
    if len(rates)==2:
        checks.append(f'- Re={re}: caudales orientados de entrada/salida {rates[0]:.10g} / {rates[1]:.10g} m³/s; desequilibrio relativo {abs(sum(rates))/abs(rates[0]):.3e} (a la precisión de salida).')
checks+=['\n## y+ a t=400 s\n','| Re | Superficie | Mínimo | Máximo | Promedio |','|---:|---|---:|---:|---:|']
import re as regex
for re in [10000,100000]:
    p=ROOT/f'Re{re}/log.yPlus'
    if p.exists():
        for patch,lo,hi,avg in regex.findall(r'patch (\w+) y\+ : min = ([\d.eE+-]+), max = ([\d.eE+-]+), average = ([\d.eE+-]+)',p.read_text()):
            checks.append(f'| {re} | {patch} | {float(lo):.3f} | {float(hi):.3f} | {float(avg):.3f} |')
checks+=['\nEstos y+ son instantáneos. El cilindro a Re100000 alcanza y+≈18: comprobar sensibilidad del tratamiento de pared y de las capas antes de presentar sus fuerzas como validadas.']
with (OUT/'RESUMEN.md').open('a') as f:f.write('\n## Balance de caudal a t=400 s\n\n'+'\n'.join(checks)+'\n')
