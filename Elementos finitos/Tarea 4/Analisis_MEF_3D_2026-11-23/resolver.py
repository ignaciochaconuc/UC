"""Audita estabilidad por cuerpos rígidos y ejecuta CalculiX con registro.
Uso: python resolver.py 2.0 6
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
import numpy as np
from inspeccionar import ROOT

def verify(folder):
    info=json.loads((folder/'modelo_resumen.json').read_text(encoding='utf-8'))
    m=np.load(folder/'modelo.npz'); xyz=m['xyz']
    counts=[len(np.load(folder/f'solido_{i:02}.npz')['nodes']) for i in range(1,17)]
    ends=np.cumsum(counts)
    rbt=[]; equations=[]
    lines=iter((folder/'modelo.inp').open())
    for line in lines:
        if line.strip().upper()!='*EQUATION': continue
        n=int(next(lines)); terms=[]
        while len(terms)<n:
            values=next(lines).strip().split(',')
            for j in range(0,len(values),3): terms.append((int(values[j]),int(values[j+1])-1,float(values[j+2])))
        row=np.zeros(96)
        for node,dof,coef in terms:
            if node>len(xyz): continue # all auxiliary DOFs are fixed to zero
            body=int(np.searchsorted(ends,node,side='left'))
            p=xyz[node-1]/1000.
            unit=np.eye(3)[dof]
            row[6*body:6*body+3]+=coef*unit
            row[6*body+3:6*body+6]+=coef*np.cross(p,unit)
        rbt.append(row)
    c=np.array(rbt)
    singular=np.linalg.svd(c,compute_uv=False)
    tie_singular=np.linalg.svd(c[:3*info['tied_nodes']],compute_uv=False)
    rank=int(np.sum(singular>singular[0]*1e-8)); tie_rank=int(np.sum(tie_singular>tie_singular[0]*1e-8))
    result=dict(rigid_body_unknowns=96,rank_with_supports=rank,rank_bonded_only=tie_rank,
                singular_values_with_supports=singular.tolist(),singular_values_bonded_only=tie_singular.tolist())
    (folder/'estabilidad.json').write_text(json.dumps(result,indent=2))
    if rank!=96 or tie_rank!=90: raise RuntimeError(f'Unexpected rigid-body rank: supports {rank}, contacts {tie_rank}')
    print('Rigid-body stability verified: contacts rank90/96; supported rank96/96',flush=True)

def main(t,h,serial=True,linear_solver='pardiso'):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'; verify(folder)
    deck=folder/'modelo.inp'; content=deck.read_text()
    content=content.replace('*STATIC,SOLVER=ITERATIVE CHOLESKY\n','*STATIC\n')
    content=content.replace('*STATIC,SOLVER=PASTIX\n','*STATIC\n')
    content=content.replace('*STATIC,SOLVER=PARDISO\n','*STATIC\n')
    if linear_solver=='iterative': content=content.replace('*STATIC\n','*STATIC,SOLVER=ITERATIVE CHOLESKY\n')
    if linear_solver=='pastix': content=content.replace('*STATIC\n','*STATIC,SOLVER=PASTIX\n')
    if linear_solver=='pardiso': content=content.replace('*STATIC\n','*STATIC,SOLVER=PARDISO\n')
    deck.write_text(content,encoding='ascii')
    official=list((ROOT/'herramientas').rglob('ccx_i4_static.exe'))
    exe=official[0] if serial and official else next((ROOT/'herramientas').rglob('ccx.exe' if serial else 'ccx_MT.exe'))
    if linear_solver=='pardiso': exe=next((ROOT/'herramientas'/'oficial_2.24').rglob('ccx_i4.exe'))
    env=os.environ.copy(); env['OMP_NUM_THREADS']='4'; env['CCX_NPROC_EQUATION_SOLVER']='4'; env['CCX_NPROC_RESULTS']='4'
    env['GFORTRAN_UNBUFFERED_ALL']='y'
    env['OPENBLAS_NUM_THREADS']='4'; env['MKL_NUM_THREADS']='4'; env['PASTIX_THREAD_NBR']='4'
    env['PATH']=str(ROOT/'herramientas'/'mkl_runtime')+os.pathsep+env['PATH']
    started=time.time()
    with (folder/'calculix.log').open('w') as log:
        proc=subprocess.run([str(exe),'-i','modelo'],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
    record=dict(returncode=proc.returncode,elapsed_seconds=time.time()-started,solver=str(exe),linear_solver=linear_solver)
    (folder/'ejecucion.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)
    if proc.returncode!=0 or 'Job finished' not in (folder/'calculix.log').read_text(errors='replace'):
        raise RuntimeError(f'CalculiX did not finish successfully: {proc.returncode}')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float)
    g=p.add_mutually_exclusive_group(); g.add_argument('--serial',action='store_true'); g.add_argument('--multithread',action='store_true')
    p.add_argument('--solver',choices=['pardiso','pastix','iterative','direct'],default='pardiso')
    a=p.parse_args(); main(a.t,a.h,not a.multithread,a.solver)
