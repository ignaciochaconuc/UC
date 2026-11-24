"""Comprueba componentes conectadas y nodos huérfanos en cada sólido mallado."""
import argparse
import json
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from inspeccionar import ROOT

def main(t,h):
    folder=ROOT/f'componentes_t{t:.1f}_h{h:g}'; results=[]
    for i in range(1,17):
        m=np.load(folder/f'solido_{i:02}.npz'); nodes=m['nodes'].astype(np.int64); ec=m['elements'].astype(np.int64)
        lookup=np.full(int(nodes.max())+1,-1,dtype=np.int64); lookup[nodes]=np.arange(len(nodes)); ec=lookup[ec]
        used=np.unique(ec); orphans=len(nodes)-len(used)
        a=np.repeat(ec[:,0],9); b=ec[:,1:].reshape(-1)
        graph=csr_matrix((np.ones(len(a),dtype=np.int8),(a,b)),shape=(len(nodes),len(nodes)))
        count,labels=connected_components(graph,directed=False)
        row=dict(solid=i,nodes=len(nodes),orphan_nodes=orphans,connected_components=count)
        results.append(row)
    result=dict(solids=results,passed=all(r['orphan_nodes']==0 and r['connected_components']==1 for r in results))
    (folder/'conectividad.json').write_text(json.dumps(result,indent=2)); print(folder.name,result['passed'])
    if not result['passed']: print(json.dumps(result,indent=2)); raise RuntimeError('Mesh connectivity failed')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('t',type=float); p.add_argument('h',type=float); a=p.parse_args(); main(a.t,a.h)
