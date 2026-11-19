"""Funciones EP2 como única fuente matemática; ningún runner se ejecuta.

El proyecto original permanece de solo lectura. Sus valores globales no se
usan para elegir la máquina nueva: los argumentos de cada función se pasan
explícitamente. Evitar ejecutar suites de distintos proyectos en un proceso.
"""
from pathlib import Path
import sys

EP2=Path(__file__).resolve().parents[2]/'Simulación_peletizadora'
if str(EP2) not in sys.path:sys.path.insert(0,str(EP2))
from modelos.superposicion import interseccion_disco_rectangulo, coordenadas_locales
from modelos.torque import contribuciones_torque_nm, potencia_resistente_w
from estructural.viga_eb import SistemaViga
from estructural.config_eje import SegmentoEje
from estructural.cargas_eje import repartir_entre_rodamientos
from estructural.rodamientos import carga_dinamica_equivalente, vida_l10_millones, vida_l10_horas, factor_estatico
