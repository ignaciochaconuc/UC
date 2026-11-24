"""Extrae runtimes Intel desde wheels descargados, sólo dentro de esta carpeta.
python -m pip download mkl==2026.2.1 intel-openmp==2026.2.0 tbb==2023.2.0 --no-deps --dest herramientas
python instalar_mkl.py
"""
import hashlib
import json
import zipfile
from inspeccionar import ROOT

target=ROOT/'herramientas'/'mkl_runtime'; target.mkdir(exist_ok=True)
manifest=[]
for wheel in (ROOT/'herramientas').glob('*.whl'):
    entries=[]
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.lower().endswith('.dll'):
                name=member.replace('\\','/').split('/')[-1]
                dest=target/name; data=archive.read(member)
                if dest.exists() and dest.read_bytes()!=data: raise RuntimeError('DLL name conflict')
                dest.write_bytes(data); entries.append(name)
    manifest.append(dict(wheel=wheel.name,sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),dlls=entries))
(target/'procedencia.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2))
