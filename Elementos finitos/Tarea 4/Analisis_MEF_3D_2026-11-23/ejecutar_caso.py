"""Resuelve y postprocesa secuencialmente una malla ya preparada.
python ejecutar_caso.py 2.0 6
"""
import argparse
import json
from inspeccionar import ROOT
from resolver import main as solve
from postprocesar import main as post

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('t',type=float); parser.add_argument('h',type=float); args=parser.parse_args()
    solve(args.t,args.h)
    post(args.t,args.h,render=False)
    result=json.loads((ROOT/f'componentes_t{args.t:.1f}_h{args.h:g}'/'resultados.json').read_text())
    if not result['equilibrium_passed'] or not result['boundary_conditions_passed']: raise RuntimeError('Physical verification failed')
