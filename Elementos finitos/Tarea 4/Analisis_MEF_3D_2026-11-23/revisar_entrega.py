"""Auditoría final de archivos reales, controles físicos y límites de texto PDF."""
import hashlib
import json
import numpy as np
import pymupdf
from inspeccionar import ROOT,SOURCE
from verificar_pasadores import main as check_pins

cases=[(2.,8),(2.,7),(2.,6),(2.5,8),(2.5,6),(3.,8),(3.,6)]
records=[]
for t,h in cases:
    folder=ROOT/f'componentes_t{t:.1f}_h{h}'
    if not (folder/'equivalencia_pasadores.json').exists(): check_pins(t,h)
    q=json.loads((folder/'resumen.json').read_text()); r=json.loads((folder/'resultados.json').read_text()); run=json.loads((folder/'ejecucion.json').read_text())
    info=json.loads((folder/'modelo_resumen.json').read_text()); stability=json.loads((folder/'estabilidad.json').read_text())
    log=(folder/'calculix.log').read_text(errors='replace')
    row=dict(t_mm=t,h_mm=h,physical_checks=bool(r['equilibrium_passed'] and r['boundary_conditions_passed']),solver_completed=run['returncode']==0 and 'Job finished' in log,
             no_solver_errors_or_warnings=not any(s in log.upper() for s in ['ERROR','WARNING']),
             mesh_counts_consistent=sum(v['nodes'] for v in q)==r['nodes'] and sum(v['elements'] for v in q)==r['elements'],
             positive_Jacobians=all(v['minDetJac']>0 and v['status']=='valid' for v in q),
             rigid_body_ranks=stability['rank_bonded_only']==90 and stability['rank_with_supports']==96,
             affine_contact_patch=info['max_affine_patch_error_mm']<1e-7)
    for name in ['volumen_malla','conectividad','equivalencia_pasadores']:
        row[name]=json.loads((folder/f'{name}.json').read_text())['passed']
    assert all(v for k,v in row.items() if k not in ['t_mm','h_mm']),row
    records.append(row)
config=json.loads((ROOT/'configuracion.json').read_text(encoding='utf-8'))
reference_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
original_hash=hashlib.sha256((ROOT.parent/'Ensamblaje 2.stp').read_bytes()).hexdigest()
assert reference_hash==original_hash==config['sha256']
doc=pymupdf.open(ROOT/'informe_MEF_cuadro.pdf'); issues=[]; alltext=''
for i,page in enumerate(doc):
    alltext+=page.get_text()
    for block in page.get_text('dict')['blocks']:
        if block['type']==0:
            x0,y0,x1,y1=block['bbox']
            if x0<0 or y0<0 or x1>page.rect.width+.5 or y1>page.rect.height+.5: issues.append(dict(page=i+1,bbox=block['bbox']))
assert not issues,issues
assert 'np.float64' not in alltext
assert 'no estabilizados' in ' '.join(alltext.split())
assert len(doc)>=13
result=dict(passed=True,pdf_pages=len(doc),pdf_sha256=hashlib.sha256((ROOT/'informe_MEF_cuadro.pdf').read_bytes()).hexdigest(),out_of_page_text_blocks=issues,source_unchanged=True,case_controls=records,
            stress_convergence=False,scope='Controles mecánicos y calidad de entrega aprobados; máximos de tensión NO demostrados convergidos.')
(ROOT/'revision_pdf.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
for i in [0,4,len(doc)-2]: doc[i].get_pixmap(matrix=pymupdf.Matrix(1.15,1.15)).save(str(ROOT/f'revision_pagina_{i+1:02}.png'))
print(json.dumps(result,indent=2,ensure_ascii=False))
