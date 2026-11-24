"""Lee únicamente salidas reales de CalculiX; verifica reacciones y restricciones."""
import argparse
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from inspeccionar import ROOT

FLOAT=re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?')

def vm(s):
    return np.sqrt(.5*((s[...,0]-s[...,1])**2+(s[...,1]-s[...,2])**2+(s[...,2]-s[...,0])**2)+3*np.sum(s[...,3:6]**2,axis=-1))

def parse_dat(path,n):
    u=np.full((n,3),np.nan); reactions={}; vmax=-1.; vmax_id=None; mode=None
    for line in path.open(errors='replace'):
        low=line.lower()
        if 'displacements (' in low: mode='u'; continue
        if 'forces (' in low: mode='r'; continue
        if 'stresses (' in low: mode='s'; continue
        if not line.strip(): continue
        tokens=line.split()
        try: vals=[float(x.replace('D','E')) for x in tokens]
        except ValueError: continue
        if mode=='u' and len(vals)==4 and 1<=int(vals[0])<=n: u[int(vals[0])-1]=vals[1:]
        elif mode=='r' and len(vals)==4: reactions[int(vals[0])]=vals[1:]
        elif mode=='s' and len(vals)==8:
            stress=float(vm(np.array(vals[2:])))
            if stress>vmax: vmax=stress; vmax_id=(int(vals[0]),int(vals[1]))
    if not np.all(np.isfinite(u)) or vmax<0: raise RuntimeError('Incomplete DAT output')
    return u,reactions,vmax,vmax_id

def parse_frd(path,n):
    stress=np.full((n,6),np.nan); mode=None
    for line in path.open(errors='replace'):
        if line.startswith(' -4'):
            mode='s' if 'STRESS' in line else None
        elif line.startswith(' -3'): mode=None
        elif mode=='s' and line.startswith(' -1'):
            node=int(line[3:13])
            # Windows build writes three-digit exponents with adjacent fields.
            vals=re.findall(r'[-+]?\d\.\d{5}[EeDd][-+]\d{2,3}',line[13:])
            if len(vals)!=6: raise RuntimeError(f'Unexpected FRD stress record: {line!r}')
            if 1<=node<=n: stress[node-1]=[float(v.replace('D','E')) for v in vals]
    if not np.all(np.isfinite(stress)): raise RuntimeError('Incomplete FRD stress output')
    return stress

def render_fields(folder,t,common_limits=None):
    model=np.load(folder/'modelo.npz'); xyz=model['xyz']
    fields=np.load(folder/'campos.npz'); vnodal=fields['von_mises']; unorm=np.linalg.norm(fields['displacement'],axis=1)
    tris=[]; offset=0
    for i in range(1,17):
        local=np.load(folder/f'solido_{i:02}.npz'); conv={int(n):k+offset for k,n in enumerate(local['nodes'])}
        for face in json.loads((folder/f'solido_{i:02}_superficies.json').read_text()):
            for tri in face['triangles']:
                ns=[conv[k] for k in tri]
                for sub in [(0,3,5),(3,1,4),(5,4,2),(3,4,5)]: tris.append([ns[k] for k in sub])
        offset+=len(local['nodes'])
    tris=np.array(tris); tris=tris[np.argsort(xyz[tris,2].mean(axis=1))[::-1]]
    for name,field,unit,title in [('von_mises',vnodal,'MPa (extrapolado/promediado nodal)','Tensión de von Mises'),('desplazamiento',unorm,'mm','Desplazamiento total')]:
        maximum=float(field.max()); limit=maximum if common_limits is None else common_limits[name]
        fig,ax=plt.subplots(figsize=(12,8))
        collection=ax.tripcolor(xyz[:,0],xyz[:,1],tris,field,shading='gouraud',cmap='turbo',vmin=0,vmax=limit,rasterized=True)
        ax.set_aspect('equal'); ax.set(xlabel='X [mm]',ylabel='Y [mm]',title=f't = {t:g} mm · {title}\nProyección XY desde Z negativo; geometría sin deformar')
        ax.title.set_fontsize(14); ax.xaxis.label.set_fontsize(13); ax.yaxis.label.set_fontsize(13); ax.tick_params(labelsize=12)
        point=xyz[int(np.argmax(field))]; ax.plot(point[0],point[1],'kx',markersize=7)
        nodal_offset=(-150,55) if name=='von_mises' and point[1]<0 else (10,18)
        ax.annotate(f'Máx. nodal: {maximum:.5g}',point[:2],xytext=nodal_offset,textcoords='offset points',fontsize=10,arrowprops=dict(arrowstyle='-',color='black',linewidth=.7),bbox=dict(facecolor='white',alpha=.85,edgecolor='.6'))
        if name=='von_mises':
            result=json.loads((folder/'resultados.json').read_text()); gp=result['max_stress_element_centroid_mm']
            ax.plot(gp[0],gp[1],'k*',markersize=9)
            ax.annotate(f"Elemento del máx. de integración: {result['von_mises_max_integration_MPa']:.5g} MPa",gp[:2],xytext=(15,22 if gp[1]<0 else -35),textcoords='offset points',fontsize=8,bbox=dict(facecolor='white',alpha=.85,edgecolor='.6'))
        bar=fig.colorbar(collection,ax=ax,label=unit,shrink=.75); bar.ax.yaxis.label.set_fontsize(12); bar.ax.tick_params(labelsize=12)
        fig.tight_layout(); fig.savefig(folder/f'{name}.png',dpi=180); plt.close(fig)

def main(t,h,render=True):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'
    log=(folder/'calculix.log').read_text(errors='replace')
    if 'Job finished' not in log and 'JOB FINISHED' not in log: raise RuntimeError('No successful solver completion')
    info=json.loads((folder/'modelo_resumen.json').read_text()); model=np.load(folder/'modelo.npz'); xyz=model['xyz']; ec=model['elements']; n=len(xyz)
    u,rf,smax,loc=parse_dat(folder/'modelo.dat',n); snodal=parse_frd(folder/'modelo.frd',n); vnodal=vm(snodal); unorm=np.linalg.norm(u,axis=1)
    supports=json.loads((folder/'apoyos.json').read_text()); reactions=[]; rsum=np.zeros(3); msum=np.zeros(3); groups={}
    for s in supports:
        if s['dummy'] not in rf: raise RuntimeError('Missing auxiliary reaction')
        force=float(rf[s['dummy']][0])*np.array(s['direction']); moment=np.cross(s['position'],force)
        rsum+=force; msum+=moment
        group=groups.setdefault(str(s['solid']),dict(force_N=[0.,0.,0.],moment_origin_Nmm=[0.,0.,0.]))
        group['force_N']=(np.array(group['force_N'])+force).tolist(); group['moment_origin_Nmm']=(np.array(group['moment_origin_Nmm'])+moment).tolist()
    f=np.array(info['load_resultant_N']); moment=np.array(info['load_moment_Nmm'])
    ferror=rsum+f; merror=msum+moment
    support_error=max(abs(np.dot(u[s['node']-1],s['direction'])) for s in supports)
    inherited=json.loads((folder/'apoyos_heredados.json').read_text())
    inherited_error=max([abs(np.dot(u[s['node']-1],s['direction'])) for s in inherited],default=0.)
    umaxnode=int(np.argmax(unorm))+1; smaxnode=int(np.argmax(vnodal))+1
    result=dict(thickness_mm=t,h_mm=h,nodes=n,elements=len(ec),von_mises_max_integration_MPa=smax,
                max_stress_element=loc[0],max_stress_integration_point=loc[1],max_stress_element_centroid_mm=xyz[ec[loc[0]-1,:4]-1].mean(axis=0).tolist(),
                von_mises_max_nodal_MPa=float(vnodal.max()),max_nodal_stress_position_mm=xyz[smaxnode-1].tolist(),
                displacement_max_mm=float(unorm.max()),max_displacement_node=umaxnode,max_displacement_position_mm=xyz[umaxnode-1].tolist(),
                nominal_yield_safety_factor=276./smax,reference_2mm_54_71MPa_percent_difference=100*(smax/54.71-1) if t==2. else None,
                nominal_yield_safety_factor_nodal=276./float(vnodal.max()),
                nominal_yield_safety_factor_conservative=276./max(smax,float(vnodal.max())),
                reference_2mm_0_4716mm_percent_difference=100*(unorm.max()/.4716-1) if t==2. else None,
                reactions=groups,total_reaction_N=rsum.tolist(),total_reaction_moment_Nmm=msum.tolist(),
                equilibrium_force_residual_N=ferror.tolist(),equilibrium_moment_residual_Nmm=merror.tolist(),
                relative_force_residual=float(np.linalg.norm(ferror)/np.linalg.norm(f)),relative_moment_residual=float(np.linalg.norm(merror)/np.linalg.norm(moment)),
                max_support_constraint_displacement_mm=support_error,
                inherited_head_ring_nodes=len(inherited),max_inherited_radial_displacement_mm=inherited_error,
                status='solver_output_requires_mesh_convergence')
    result['equilibrium_passed']=result['relative_force_residual']<.001 and result['relative_moment_residual']<.001
    result['boundary_conditions_passed']=bool(support_error<1e-6 and inherited_error<1e-5)
    if not result['equilibrium_passed'] or not result['boundary_conditions_passed']:
        result['status']='REJECTED_equilibrium_or_boundary_checks_failed'
    (folder/'resultados.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    np.savez_compressed(folder/'campos.npz',displacement=u,stress=snodal,von_mises=vnodal)
    if render: render_fields(folder,t)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); p.add_argument('--no-render',action='store_true'); a=p.parse_args(); main(a.t,a.h,not a.no_render)
