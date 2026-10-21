import hashlib
import json
from pathlib import Path
import pytest
from auditoria_6a import RAIZ, inventario, ejecutar


def test_inventario_trazable_y_evidencia():
    filas=inventario()
    assert len(filas)==16 and len({r['id'] for r in filas})==16
    assert all(all(v for v in r.values()) for r in filas)
    assert all((RAIZ/f).is_file() for r in filas for f in r['fuentes'])
    tuerca=next(r for r in filas if r['id']=='C05')
    assert 'NO axial' in tuerca['acciones']
    assert 'no confirmadas' in tuerca['evidencia']
    assert '1,6mm' in next(r for r in filas if r['id']=='C03')['geometria_disponible']


def test_ejecucion_no_simula_y_conserva(tmp_path):
    r=ejecutar(tmp_path)
    assert not r['fem_ejecutado'] and not r['cad_modificado']
    assert r['nuevos_factores_seguridad'] is None
    h=json.loads((tmp_path/'trazabilidad_sha256.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==v for f,v in h.items())
    c=r['hallazgo_consistencia']
    assert c['estados_serie_actual']==1440
    assert c['maximo_serie_3c_n']==pytest.approx(c['maximo_copia4c_n'])
    assert (tmp_path/'camino_cargas_y_alcance_6b.md').is_file()
    with pytest.raises(ValueError):
        ejecutar(RAIZ/'Transmision/resultados')
