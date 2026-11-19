"""Puente de lectura a funciones comerciales; nunca modifica sus parámetros."""
from pathlib import Path
import sys

COMERCIAL=Path(__file__).resolve().parents[1]/'Simulación_peletizadora'
if str(COMERCIAL) not in sys.path:
    sys.path.insert(0,str(COMERCIAL))

from modelos.superposicion import interseccion_disco_rectangulo, coordenadas_locales
from modelos.torque import contribuciones_torque_nm, potencia_resistente_w
from estructural.viga_eb import SistemaViga
from estructural.config_eje import SegmentoEje
from estructural.cargas_eje import repartir_entre_rodamientos
from estructural.rodamientos import carga_dinamica_equivalente, vida_l10_millones, vida_l10_horas, factor_estatico, velocidad_rodillo_rpm
from config import PARAMETROS as PARAMETROS_COMERCIAL
