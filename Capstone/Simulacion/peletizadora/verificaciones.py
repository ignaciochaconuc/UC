"""Adaptadores generales: solo ejecutar con datos explícitos de la máquina.

No incorporan posiciones, diámetros ni grados del prototipo retirado.
"""
import math
from types import SimpleNamespace
import numpy as np
from scipy.sparse.linalg import splu
from .nucleo import positivo
from .legado import SistemaViga, SegmentoEje, carga_dinamica_equivalente, vida_l10_millones, vida_l10_horas, factor_estatico


def presion_canal(PN0_pa,mu_pared,nu_LR,L_activa_m,diametro_m):
    """Stelte etal.2011, ecuaciones1–2; no calibrada por defecto."""
    for nombre,v in locals().copy().items():positivo(v,nombre)
    exponente=4*mu_pared*nu_LR*L_activa_m/diametro_m
    if exponente>700:raise ValueError('Fuera del dominio numérico')
    return PN0_pa/nu_LR*math.expm1(exponente)


def resolver_viga(nodos_m,segmentos,E_pa,cargas_n,restricciones,fuente):
    if not fuente:raise ValueError('Falta fuente para apoyos/propiedades')
    positivo(E_pa,'E')
    piezas=tuple(SegmentoEje(**s) for s in segmentos)
    sistema=SistemaViga(np.asarray(nodos_m),SimpleNamespace(segmentos=piezas,modulo_young_pa=E_pa))
    restricciones=np.array(restricciones,dtype=int)
    if len(np.unique(restricciones))!=len(restricciones) or np.any(restricciones<0) or np.any(restricciones>=sistema.numero_gdl):
        raise ValueError('Restricciones inválidas')
    sistema.restringidos=restricciones
    sistema.libres=np.setdiff1d(np.arange(sistema.numero_gdl),restricciones)
    sistema._factor=splu(sistema.K[sistema.libres][:,sistema.libres].tocsc())
    return sistema,sistema.resolver(np.asarray(cargas_n,dtype=float))


def vida_bolas(cargas_radiales_n,C_n,C0_n,rpm,Fa_n,fuente_fabricante):
    if not fuente_fabricante or Fa_n is None:
        raise ValueError('Identificar fabricante y condición axial; no asumirFa0')
    if Fa_n!=0:raise ValueError('Carga combinada requiereX,Y,e de la variante real')
    for k,v in [('C',C_n),('C0',C0_n),('rpm',rpm)]:positivo(v,k)
    Peq=carga_dinamica_equivalente(cargas_radiales_n)
    L10=vida_l10_millones(C_n,Peq)
    return dict(Peq_n=Peq,L10_millones=L10,L10h=vida_l10_horas(L10,rpm),
                S0=factor_estatico(C0_n,float(np.max(cargas_radiales_n))),fuente=fuente_fabricante,
                limite='Vida básica de referencia; no aprobación del montaje')


def balance_potencia(potencia_motor_w,eficiencia_mecanica,potencia_max_w,potencia_media_w):
    # Reutilizar cálculo de5A/B, adaptando unidades sin duplicar ecuación.
    from pathlib import Path
    import sys
    transmision=Path(__file__).resolve().parents[2]/'Transmision'
    if str(transmision) not in sys.path:sys.path.insert(0,str(transmision))
    from transmision.calculos import balance_motor
    r=balance_motor(potencia_motor_w/1000,eficiencia_mecanica,potencia_max_w/1000,potencia_media_w/1000)
    return dict(potencia_disponible_w=r['potencia_disponible_kw']*1000,margen_maximo_w=r['margen_maximo_kw']*1000,
        cubre_maximo=r['cubre_maximo_3c'],eficiencia_minima_maximo=r['eficiencia_minima_maximo'],
        nota='Eficiencia mecánica explícita; no eficiencia eléctrica ni capacidad de correas')
