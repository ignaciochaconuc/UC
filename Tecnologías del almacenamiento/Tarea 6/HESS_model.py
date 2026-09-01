"""
HESS_model.py — Módulo base para sistema HESS PEMEL-PEMFC (ESTUDIANTES)
========================================================================
Proporciona las estructuras de datos, el modelo de tanques y la gestión
de estado. NO incluye la electroquímica (Nernst, sobrepotenciales, Faraday)
ni los pasos de carga/descarga completos — eso debe programarlo el estudiante.

Lo que SÍ incluye este módulo:
  - Constantes físicas (F, R, LHV, masas molares)
  - Dataclasses: StackParams, TankParams, HESSDesign, HESSState
  - Física de tanques (gas ideal, presión↔moles, SoC, dimensionamiento)
  - Gestión de estado (inicialización, límites, inventario)
  - Paso en reposo (idle_step) con fugas
  - Ejemplo mínimo de uso

Lo que DEBE programar el estudiante:
  - Voltaje reversible de Nernst
  - Voltaje de celda con sobrepotenciales (activación, óhmico, concentración)
  - Resolución de densidad de corriente para potencia objetivo (bisección)
  - Tasas de producción/consumo de H2/O2 (Faraday)
  - Eficiencias en base LHV
  - Pasos completos de carga (PEMEL) y descarga (PEMFC)
  - Loop económico, despacho, LCOS, VPN

Unidades: potencia en MW, energía en MWh, presión en bar, T en K,
cantidad de sustancia en mol, tiempo en s.
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Dict, Tuple
import math
import numpy as np

# ===================================================================
# CONSTANTES FÍSICAS
# ===================================================================
F = 96485.33212          # C/mol_e-
R = 8.314462618          # J/mol·K
P0_BAR = 1.0             # bar, presión de referencia para Nernst
M_H2 = 2.01588e-3        # kg/mol
M_O2 = 31.998e-3         # kg/mol
LHV_H2_MJ_KG = 120.0     # MJ/kg
LHV_H2_J_MOL = LHV_H2_MJ_KG * 1e6 * M_H2
V_LHV = LHV_H2_J_MOL / (2.0 * F)   # voltaje equivalente LHV ≈ 1.25 V

# ===================================================================
# PARÁMETROS DE DISEÑO (Dataclasses)
# ===================================================================
@dataclass
class StackParams:
    """Parámetros electroquímicos y geométricos de un stack PEM."""
    p_stack_nom_MW: float = 1.0
    n_cells: int = 200
    area_cm2: float = 5000.0
    T_K: float = 353.15
    j_min_A_cm2: float = 0.05
    j_max_A_cm2: float = 2.0
    j0_A_cm2: float = 1e-3         # densidad de corriente de intercambio
    asr_ohm_cm2: float = 0.18      # resistencia óhmica de área [Ω·cm²]
    a_act_V: float = 0.045         # coeficiente de activación [V]
    b_conc_V: float = 0.030        # coeficiente de concentración [V]
    faraday_eff: float = 0.99      # eficiencia faradaica
    aux_fraction: float = 0.03     # fracción de auxiliares
    min_plr: float = 0.10          # PLR mínimo
    lambda_h2: float = 1.15        # exceso estequiométrico H2
    lambda_o2: float = 2.00        # exceso estequiométrico O2
    ideal_recirculation: bool = True

@dataclass
class TankParams:
    """Parámetros de tanques ideales isotérmicos."""
    T_K: float = 298.15
    p_h2_min_bar: float = 20.0
    p_h2_max_bar: float = 350.0
    p_o2_min_bar: float = 5.0
    p_o2_max_bar: float = 100.0
    leakage_fraction_per_h: float = 0.0
    V_h2_m3: float | None = None
    V_o2_m3: float | None = None

@dataclass
class HESSDesign:
    """Diseño completo de la planta HESS."""
    x_MW: float = 100.0
    storage_hours: float = 12.0
    n_pemel: int | None = None
    n_pemfc: int | None = None
    pemel: StackParams = field(default_factory=StackParams)
    pemfc: StackParams = field(default_factory=lambda: StackParams(
        p_stack_nom_MW=1.0, n_cells=200, area_cm2=5000.0,
        T_K=353.15, j_min_A_cm2=0.05, j_max_A_cm2=1.5,
        j0_A_cm2=5e-4, asr_ohm_cm2=0.16, a_act_V=0.055,
        b_conc_V=0.040, faraday_eff=0.995, aux_fraction=0.04,
        min_plr=0.10, lambda_h2=1.15, lambda_o2=2.00,
        ideal_recirculation=True))
    tanks: TankParams = field(default_factory=TankParams)
    eta_acdc: float = 0.97
    eta_dcac: float = 0.97
    compressor_kWh_per_kg_H2: float = 2.0

@dataclass
class HESSState:
    """Estado dinámico del HESS."""
    n_H2_mol: float
    n_O2_mol: float
    hour: int = 0

# ===================================================================
# FÍSICA DE TANQUES (Gas Ideal Isotérmico)
# ===================================================================
def moles_from_pressure(p_bar: float, V_m3: float, T_K: float) -> float:
    return p_bar * 1e5 * V_m3 / (R * T_K)

def pressure_from_moles(n_mol: float, V_m3: float, T_K: float) -> float:
    return n_mol * R * T_K / max(V_m3, 1e-12) / 1e5

def size_tanks_from_storage_hours(design: HESSDesign, eta_fc_guess: float = 0.50) -> HESSDesign:
    """Dimensiona tanques H2/O2 a partir de horas de almacenamiento."""
    tanks = design.tanks
    if tanks.V_h2_m3 is not None and tanks.V_o2_m3 is not None:
        return design
    E_out_MWh = design.x_MW * design.storage_hours
    h2_energy_kWh_kg = LHV_H2_MJ_KG / 3.6
    m_h2_usable_kg = E_out_MWh * 1000.0 / max(h2_energy_kWh_kg * eta_fc_guess, 1e-12)
    n_h2_usable_mol = m_h2_usable_kg / M_H2
    n_o2_usable_mol = 0.5 * n_h2_usable_mol
    dp_h2_Pa = (tanks.p_h2_max_bar - tanks.p_h2_min_bar) * 1e5
    dp_o2_Pa = (tanks.p_o2_max_bar - tanks.p_o2_min_bar) * 1e5
    V_h2_m3 = n_h2_usable_mol * R * tanks.T_K / max(dp_h2_Pa, 1e-12)
    V_o2_m3 = n_o2_usable_mol * R * tanks.T_K / max(dp_o2_Pa, 1e-12)
    new_tanks = replace(tanks, V_h2_m3=V_h2_m3, V_o2_m3=V_o2_m3)
    return replace(design, tanks=new_tanks)

def tank_limits(design: HESSDesign) -> Dict[str, float]:
    tanks = design.tanks
    if tanks.V_h2_m3 is None or tanks.V_o2_m3 is None:
        raise ValueError("Primero dimensione los tanques con size_tanks_from_storage_hours.")
    return {
        "n_H2_min_mol": moles_from_pressure(tanks.p_h2_min_bar, tanks.V_h2_m3, tanks.T_K),
        "n_H2_max_mol": moles_from_pressure(tanks.p_h2_max_bar, tanks.V_h2_m3, tanks.T_K),
        "n_O2_min_mol": moles_from_pressure(tanks.p_o2_min_bar, tanks.V_o2_m3, tanks.T_K),
        "n_O2_max_mol": moles_from_pressure(tanks.p_o2_max_bar, tanks.V_o2_m3, tanks.T_K),
    }

def initial_state_from_soc(design: HESSDesign, soc0: float = 0.50) -> HESSState:
    lim = tank_limits(design)
    soc = min(max(soc0, 0.0), 1.0)
    n_H2 = lim["n_H2_min_mol"] + soc*(lim["n_H2_max_mol"] - lim["n_H2_min_mol"])
    n_O2 = lim["n_O2_min_mol"] + soc*(lim["n_O2_max_mol"] - lim["n_O2_min_mol"])
    return HESSState(n_H2_mol=n_H2, n_O2_mol=n_O2, hour=0)

def tank_pressures(design: HESSDesign, state: HESSState) -> Tuple[float, float]:
    tanks = design.tanks
    if tanks.V_h2_m3 is None or tanks.V_o2_m3 is None:
        raise ValueError("Primero dimensione los tanques.")
    p_h2 = pressure_from_moles(state.n_H2_mol, tanks.V_h2_m3, tanks.T_K)
    p_o2 = pressure_from_moles(state.n_O2_mol, tanks.V_o2_m3, tanks.T_K)
    return p_h2, p_o2

def tank_soc(design: HESSDesign, state: HESSState) -> Tuple[float, float]:
    lim = tank_limits(design)
    soc_h2 = (state.n_H2_mol - lim["n_H2_min_mol"]) / max(lim["n_H2_max_mol"] - lim["n_H2_min_mol"], 1e-12)
    soc_o2 = (state.n_O2_mol - lim["n_O2_min_mol"]) / max(lim["n_O2_max_mol"] - lim["n_O2_min_mol"], 1e-12)
    return min(max(soc_h2, 0.0), 1.0), min(max(soc_o2, 0.0), 1.0)

def clip_state_to_tank_limits(design: HESSDesign, state: HESSState) -> HESSState:
    lim = tank_limits(design)
    return HESSState(
        n_H2_mol=min(max(state.n_H2_mol, lim["n_H2_min_mol"]), lim["n_H2_max_mol"]),
        n_O2_mol=min(max(state.n_O2_mol, lim["n_O2_min_mol"]), lim["n_O2_max_mol"]),
        hour=state.hour)

def available_inventory(design: HESSDesign, state: HESSState) -> Tuple[float, float]:
    lim = tank_limits(design)
    return (max(state.n_H2_mol - lim["n_H2_min_mol"], 0.0),
            max(state.n_O2_mol - lim["n_O2_min_mol"], 0.0))

def free_capacity(design: HESSDesign, state: HESSState) -> Tuple[float, float]:
    lim = tank_limits(design)
    return (max(lim["n_H2_max_mol"] - state.n_H2_mol, 0.0),
            max(lim["n_O2_max_mol"] - state.n_O2_mol, 0.0))

# ===================================================================
# PASO EN REPOSO (con fugas)
# ===================================================================
def idle_step(state: HESSState, design: HESSDesign, dt_s: float = 3600.0) -> Tuple[HESSState, Dict]:
    lim = tank_limits(design)
    leak_h2 = design.tanks.leakage_fraction_per_h * max(state.n_H2_mol - lim["n_H2_min_mol"], 0.0) * (dt_s/3600.0)
    leak_o2 = design.tanks.leakage_fraction_per_h * max(state.n_O2_mol - lim["n_O2_min_mol"], 0.0) * (dt_s/3600.0)
    new_state = HESSState(
        n_H2_mol=state.n_H2_mol - leak_h2,
        n_O2_mol=state.n_O2_mol - leak_o2,
        hour=state.hour + 1)
    new_state = clip_state_to_tank_limits(design, new_state)
    soc_h2, soc_o2 = tank_soc(design, new_state)
    p_h2, p_o2 = tank_pressures(design, new_state)
    return new_state, {"mode": "idle", "p_H2_bar": p_h2, "p_O2_bar": p_o2,
                        "soc_H2": soc_h2, "soc_O2": soc_o2}

# ===================================================================
# ELECTROQUÍMICA PEM + PASOS COMPLETOS DE CARGA/DESCARGA
# Pegar dentro de HESS_model.py después de idle_step(...)
# ===================================================================

def reversible_voltage_E0(T_K: float) -> float:
    """
    Potencial reversible estándar aproximado para la reacción H2/O2 [V].

    Se usa una corrección lineal simple con temperatura alrededor de 298.15 K.
    """
    return 1.229 - 8.45e-4 * (T_K - 298.15)


def nernst_voltage(T_K: float, p_H2_bar: float, p_O2_bar: float) -> float:
    """
    Voltaje reversible simplificado de Nernst [V/celda].

    E_rev = E0(T) + (RT/2F) ln(p_H2 * p_O2^(1/2))
    Las presiones se usan adimensionalizadas respecto a 1 bar.
    """
    p_h2 = max(p_H2_bar / P0_BAR, 1e-12)
    p_o2 = max(p_O2_bar / P0_BAR, 1e-12)

    return (
        reversible_voltage_E0(T_K)
        + (R * T_K / (2.0 * F)) * math.log(p_h2 * math.sqrt(p_o2))
    )


def pem_overpotentials(j_A_cm2: float, stack: StackParams) -> Dict[str, float]:
    """
    Calcula sobrepotenciales empíricos PEM [V/celda].

    Incluye:
    - activación
    - óhmico
    - concentración
    """
    j = max(j_A_cm2, 1e-12)
    j0 = max(stack.j0_A_cm2, 1e-12)

    eta_act = stack.a_act_V * math.log(max(j / j0, 1.0))
    eta_ohm = stack.asr_ohm_cm2 * j

    # Se usa j_max como proxy de corriente límite.
    j_lim = max(1.05 * stack.j_max_A_cm2, j * 1.001)
    ratio = min(j / j_lim, 0.999999)
    eta_conc = -stack.b_conc_V * math.log(max(1.0 - ratio, 1e-12))

    return {
        "eta_act_V": eta_act,
        "eta_ohm_V": eta_ohm,
        "eta_conc_V": eta_conc,
        "eta_total_V": eta_act + eta_ohm + eta_conc,
    }


def pem_cell_voltage(
    mode: str,
    stack: StackParams,
    j_A_cm2: float,
    p_H2_bar: float,
    p_O2_bar: float
) -> Dict[str, float]:
    """
    Calcula voltaje de celda PEMEL o PEMFC [V/celda].

    PEMEL:
        V_cell = E_rev + pérdidas

    PEMFC:
        V_cell = E_rev - pérdidas
    """
    E_rev = nernst_voltage(stack.T_K, p_H2_bar, p_O2_bar)
    losses = pem_overpotentials(j_A_cm2, stack)
    eta_total = losses["eta_total_V"]

    if mode.lower() in ["pemel", "el", "electrolyzer", "electrolizador"]:
        V_cell = E_rev + eta_total

    elif mode.lower() in ["pemfc", "fc", "fuelcell", "celda"]:
        V_cell = max(E_rev - eta_total, 0.05)

    else:
        raise ValueError("mode debe ser 'pemel' o 'pemfc'.")

    return {
        "E_rev_V": E_rev,
        "V_cell_V": V_cell,
        **losses,
    }


def stack_dc_power_MW(
    mode: str,
    stack: StackParams,
    j_A_cm2: float,
    p_H2_bar: float,
    p_O2_bar: float
) -> Dict[str, float]:
    """
    Calcula la potencia DC de un stack a una densidad de corriente dada.
    """
    volt = pem_cell_voltage(mode, stack, j_A_cm2, p_H2_bar, p_O2_bar)

    I_A = j_A_cm2 * stack.area_cm2
    V_stack = stack.n_cells * volt["V_cell_V"]
    P_stack_dc_MW = V_stack * I_A / 1e6

    return {
        **volt,
        "I_A": I_A,
        "V_stack_V": V_stack,
        "P_stack_dc_MW": P_stack_dc_MW,
    }


def faraday_rates_mol_s(
    mode: str,
    stack: StackParams,
    j_A_cm2: float,
    n_active: int
) -> Tuple[float, float]:
    """
    Calcula tasas molares de H2 y O2 [mol/s] para todos los stacks activos.

    PEMEL:
        producción de H2 y O2

    PEMFC:
        consumo de H2 y O2
    """
    I_A = j_A_cm2 * stack.area_cm2

    if mode.lower() in ["pemel", "el", "electrolyzer", "electrolizador"]:
        n_H2 = (
            n_active
            * stack.n_cells
            * I_A
            / (2.0 * F)
            * stack.faraday_eff
        )

    elif mode.lower() in ["pemfc", "fc", "fuelcell", "celda"]:
        n_H2 = (
            n_active
            * stack.n_cells
            * I_A
            / (2.0 * F * max(stack.faraday_eff, 1e-12))
        )

    else:
        raise ValueError("mode debe ser 'pemel' o 'pemfc'.")

    n_O2 = 0.5 * n_H2
    return n_H2, n_O2


def installed_stacks(design: HESSDesign, kind: str) -> int:
    """
    Entrega el número instalado de stacks PEMEL o PEMFC.
    """
    if kind.lower() == "pemel":
        if design.n_pemel is not None:
            return int(design.n_pemel)

        return int(math.ceil(
            design.x_MW / max(design.pemel.p_stack_nom_MW, 1e-12)
        ))

    if kind.lower() == "pemfc":
        if design.n_pemfc is not None:
            return int(design.n_pemfc)

        return int(math.ceil(
            design.x_MW / max(design.pemfc.p_stack_nom_MW, 1e-12)
        ))

    raise ValueError("kind debe ser 'pemel' o 'pemfc'.")


def active_stacks_for_command(
    P_cmd_MW: float,
    design: HESSDesign,
    kind: str
) -> int:
    """
    Implementa:

        n_active = min(N, ceil(|P_cmd| / P_stack_nom))
    """
    P = abs(P_cmd_MW)

    if P <= 0:
        return 0

    if kind.lower() == "pemel":
        stack = design.pemel

    elif kind.lower() == "pemfc":
        stack = design.pemfc

    else:
        raise ValueError("kind debe ser 'pemel' o 'pemfc'.")

    N = installed_stacks(design, kind)

    return int(min(
        N,
        max(1, math.ceil(P / max(stack.p_stack_nom_MW, 1e-12)))
    ))


def pemel_grid_power_from_j(
    j_A_cm2: float,
    design: HESSDesign,
    n_active: int,
    p_H2_bar: float,
    p_O2_bar: float
) -> Dict[str, float]:
    """
    Calcula la potencia AC comprada por el PEMEL para una densidad j dada.
    """
    stack = design.pemel

    sp = stack_dc_power_MW(
        "pemel",
        stack,
        j_A_cm2,
        p_H2_bar,
        p_O2_bar
    )

    P_dc_total_MW = n_active * sp["P_stack_dc_MW"]

    n_H2_s, n_O2_s = faraday_rates_mol_s(
        "pemel",
        stack,
        j_A_cm2,
        n_active
    )

    m_H2_kg_h = n_H2_s * M_H2 * 3600.0

    P_comp_MW = (
        m_H2_kg_h
        * design.compressor_kWh_per_kg_H2
        / 1000.0
    )

    P_aux_MW = stack.aux_fraction * P_dc_total_MW

    P_grid_MW = (
        P_dc_total_MW / max(design.eta_acdc, 1e-12)
        + P_aux_MW
        + P_comp_MW
    )

    P_H2_LHV_MW = n_H2_s * LHV_H2_J_MOL / 1e6
    eta_lhv = P_H2_LHV_MW / max(P_grid_MW, 1e-12)

    return {
        **sp,
        "P_dc_total_MW": P_dc_total_MW,
        "P_aux_MW": P_aux_MW,
        "P_comp_MW": P_comp_MW,
        "P_grid_MW_abs": P_grid_MW,
        "n_H2_mol_s": n_H2_s,
        "n_O2_mol_s": n_O2_s,
        "P_H2_LHV_MW": P_H2_LHV_MW,
        "eta_el_lhv": eta_lhv,
    }


def pemfc_grid_power_from_j(
    j_A_cm2: float,
    design: HESSDesign,
    n_active: int,
    p_H2_bar: float,
    p_O2_bar: float
) -> Dict[str, float]:
    """
    Calcula la potencia AC neta exportada por la PEMFC para una densidad j dada.
    """
    stack = design.pemfc

    sp = stack_dc_power_MW(
        "pemfc",
        stack,
        j_A_cm2,
        p_H2_bar,
        p_O2_bar
    )

    P_dc_total_MW = n_active * sp["P_stack_dc_MW"]
    P_aux_MW = stack.aux_fraction * P_dc_total_MW
    P_dc_net_MW = max(P_dc_total_MW - P_aux_MW, 0.0)

    P_grid_MW = P_dc_net_MW * design.eta_dcac

    n_H2_s, n_O2_s = faraday_rates_mol_s(
        "pemfc",
        stack,
        j_A_cm2,
        n_active
    )

    P_H2_LHV_MW = n_H2_s * LHV_H2_J_MOL / 1e6
    eta_lhv = P_grid_MW / max(P_H2_LHV_MW, 1e-12)

    return {
        **sp,
        "P_dc_total_MW": P_dc_total_MW,
        "P_aux_MW": P_aux_MW,
        "P_dc_net_MW": P_dc_net_MW,
        "P_grid_MW_abs": P_grid_MW,
        "n_H2_mol_s": n_H2_s,
        "n_O2_mol_s": n_O2_s,
        "P_H2_LHV_MW": P_H2_LHV_MW,
        "eta_fc_lhv": eta_lhv,
    }


def solve_j_for_power(
    mode: str,
    design: HESSDesign,
    n_active: int,
    P_target_MW: float,
    p_H2_bar: float,
    p_O2_bar: float,
    tol_MW: float = 1e-5,
    max_iter: int = 80
) -> Tuple[float | None, Dict]:
    """
    Resuelve por bisección la densidad de corriente necesaria para una potencia AC objetivo.
    """
    if P_target_MW <= 0 or n_active <= 0:
        return None, {"status": "zero_power"}

    if mode.lower() == "pemel":
        stack = design.pemel
        power_fun = lambda j: pemel_grid_power_from_j(
            j, design, n_active, p_H2_bar, p_O2_bar
        )

    elif mode.lower() == "pemfc":
        stack = design.pemfc
        power_fun = lambda j: pemfc_grid_power_from_j(
            j, design, n_active, p_H2_bar, p_O2_bar
        )

    else:
        raise ValueError("mode debe ser 'pemel' o 'pemfc'.")

    j_lo = stack.j_min_A_cm2
    j_hi = stack.j_max_A_cm2

    out_lo = power_fun(j_lo)
    out_hi = power_fun(j_hi)

    P_lo = out_lo["P_grid_MW_abs"]
    P_hi = out_hi["P_grid_MW_abs"]

    if P_target_MW < P_lo:
        return None, {
            **out_lo,
            "status": "below_min_plr",
            "P_min_MW": P_lo,
            "P_max_MW": P_hi,
        }

    if P_target_MW >= P_hi:
        return j_hi, {
            **out_hi,
            "status": "above_max_power",
            "P_min_MW": P_lo,
            "P_max_MW": P_hi,
        }

    out_mid = out_hi

    for _ in range(max_iter):
        j_mid = 0.5 * (j_lo + j_hi)
        out_mid = power_fun(j_mid)
        P_mid = out_mid["P_grid_MW_abs"]

        if abs(P_mid - P_target_MW) <= tol_MW:
            return j_mid, {
                **out_mid,
                "status": "ok",
                "P_min_MW": P_lo,
                "P_max_MW": P_hi,
            }

        if P_mid < P_target_MW:
            j_lo = j_mid
        else:
            j_hi = j_mid

    return j_mid, {
        **out_mid,
        "status": "ok",
        "P_min_MW": P_lo,
        "P_max_MW": P_hi,
    }


def adjust_j_and_stacks_for_material_limit(
    j_A_cm2: float,
    n_active: int,
    factor: float,
    stack: StackParams
) -> Tuple[float, int]:
    """
    Reduce j y, si hace falta, reduce stacks para no violar j_min.
    """
    factor = min(max(factor, 0.0), 1.0)

    if factor <= 1e-12 or n_active <= 0:
        return 0.0, 0

    total_j_equiv = n_active * j_A_cm2 * factor
    j_try = total_j_equiv / n_active

    if j_try >= stack.j_min_A_cm2:
        return j_try, n_active

    n_new = int(math.floor(
        total_j_equiv / max(stack.j_min_A_cm2, 1e-12)
    ))

    if n_new < 1:
        return 0.0, 0

    j_new = total_j_equiv / n_new
    j_new = min(max(j_new, stack.j_min_A_cm2), stack.j_max_A_cm2)

    return j_new, n_new


def apply_leakage_and_clip(
    state: HESSState,
    design: HESSDesign,
    dt_s: float
) -> HESSState:
    """
    Aplica fugas horarias y recorta el estado a los límites de tanque.
    """
    lim = tank_limits(design)

    leak_h2 = (
        design.tanks.leakage_fraction_per_h
        * max(state.n_H2_mol - lim["n_H2_min_mol"], 0.0)
        * (dt_s / 3600.0)
    )

    leak_o2 = (
        design.tanks.leakage_fraction_per_h
        * max(state.n_O2_mol - lim["n_O2_min_mol"], 0.0)
        * (dt_s / 3600.0)
    )

    leaked = HESSState(
        n_H2_mol=state.n_H2_mol - leak_h2,
        n_O2_mol=state.n_O2_mol - leak_o2,
        hour=state.hour,
    )

    return clip_state_to_tank_limits(design, leaked)


def charge_step(
    state: HESSState,
    design: HESSDesign,
    P_cmd_MW: float,
    dt_s: float = 3600.0
) -> Tuple[HESSState, Dict]:
    """
    Paso completo de carga:

    electricidad AC -> PEMEL -> producción H2/O2 -> tanques.
    """
    dt_h = dt_s / 3600.0

    P_cmd_MW = min(abs(P_cmd_MW), design.x_MW)

    p_H2, p_O2 = tank_pressures(design, state)

    n_active = active_stacks_for_command(
        P_cmd_MW,
        design,
        "pemel"
    )

    j, out = solve_j_for_power(
        "pemel",
        design,
        n_active,
        P_cmd_MW,
        p_H2,
        p_O2
    )

    if j is None:
        new_state, idle_out = idle_step(state, design, dt_s)

        idle_out.update({
            "mode": "charge_block_below_min_plr",
            "P_grid_MW": 0.0,
            "E_comprada_MWh": 0.0,
            "E_vendida_MWh": 0.0,
            "n_active": 0,
            "j_A_cm2": 0.0,
            "constraint": out.get("status"),
        })

        return new_state, idle_out

    n_H2_prod_req = out["n_H2_mol_s"] * dt_s
    n_O2_prod_req = out["n_O2_mol_s"] * dt_s

    cap_H2, cap_O2 = free_capacity(design, state)

    factor = min(
        1.0,
        cap_H2 / max(n_H2_prod_req, 1e-12),
        cap_O2 / max(n_O2_prod_req, 1e-12)
    )

    constraint = out.get("status", "ok")

    if factor < 1.0:
        j, n_active = adjust_j_and_stacks_for_material_limit(
            j,
            n_active,
            factor,
            design.pemel
        )

        constraint = "tank_capacity_limited"

        if n_active == 0:
            new_state, idle_out = idle_step(state, design, dt_s)

            idle_out.update({
                "mode": "charge_block_tank_full",
                "P_grid_MW": 0.0,
                "E_comprada_MWh": 0.0,
                "E_vendida_MWh": 0.0,
                "n_active": 0,
                "j_A_cm2": 0.0,
                "constraint": constraint,
            })

            return new_state, idle_out

        out = pemel_grid_power_from_j(
            j,
            design,
            n_active,
            p_H2,
            p_O2
        )

    n_H2_prod = out["n_H2_mol_s"] * dt_s
    n_O2_prod = out["n_O2_mol_s"] * dt_s

    raw_state = HESSState(
        n_H2_mol=state.n_H2_mol + n_H2_prod,
        n_O2_mol=state.n_O2_mol + n_O2_prod,
        hour=state.hour + 1,
    )

    new_state = apply_leakage_and_clip(raw_state, design, dt_s)

    soc_H2, soc_O2 = tank_soc(design, new_state)
    p_H2_new, p_O2_new = tank_pressures(design, new_state)

    E_comprada = out["P_grid_MW_abs"] * dt_h

    return new_state, {
        "mode": "charge",
        "constraint": constraint,
        "P_grid_MW": -out["P_grid_MW_abs"],
        "P_grid_MW_abs": out["P_grid_MW_abs"],
        "E_comprada_MWh": E_comprada,
        "E_vendida_MWh": 0.0,
        "n_active": n_active,
        "j_A_cm2": j,
        "V_cell_V": out["V_cell_V"],
        "E_rev_V": out["E_rev_V"],
        "eta_act_V": out["eta_act_V"],
        "eta_ohm_V": out["eta_ohm_V"],
        "eta_conc_V": out["eta_conc_V"],
        "eta_el_lhv": out["eta_el_lhv"],
        "P_dc_total_MW": out["P_dc_total_MW"],
        "P_aux_MW": out["P_aux_MW"],
        "P_comp_MW": out["P_comp_MW"],
        "n_H2_prod_mol": n_H2_prod,
        "n_O2_prod_mol": n_O2_prod,
        "n_H2_cons_mol": 0.0,
        "n_O2_cons_mol": 0.0,
        "soc_H2": soc_H2,
        "soc_O2": soc_O2,
        "p_H2_bar": p_H2_new,
        "p_O2_bar": p_O2_new,
    }


def discharge_step(
    state: HESSState,
    design: HESSDesign,
    P_cmd_MW: float,
    dt_s: float = 3600.0
) -> Tuple[HESSState, Dict]:
    """
    Paso completo de descarga:

    tanques H2/O2 -> PEMFC -> electricidad AC neta.
    """
    dt_h = dt_s / 3600.0

    P_cmd_MW = min(abs(P_cmd_MW), design.x_MW)

    p_H2, p_O2 = tank_pressures(design, state)

    n_active = active_stacks_for_command(
        P_cmd_MW,
        design,
        "pemfc"
    )

    j, out = solve_j_for_power(
        "pemfc",
        design,
        n_active,
        P_cmd_MW,
        p_H2,
        p_O2
    )

    if j is None:
        new_state, idle_out = idle_step(state, design, dt_s)

        idle_out.update({
            "mode": "discharge_block_below_min_plr",
            "P_grid_MW": 0.0,
            "E_comprada_MWh": 0.0,
            "E_vendida_MWh": 0.0,
            "n_active": 0,
            "j_A_cm2": 0.0,
            "constraint": out.get("status"),
        })

        return new_state, idle_out

    n_H2_req = out["n_H2_mol_s"] * dt_s
    n_O2_req = out["n_O2_mol_s"] * dt_s

    avail_H2, avail_O2 = available_inventory(design, state)

    factor = min(
        1.0,
        avail_H2 / max(n_H2_req, 1e-12),
        avail_O2 / max(n_O2_req, 1e-12)
    )

    constraint = out.get("status", "ok")

    if factor < 1.0:
        j, n_active = adjust_j_and_stacks_for_material_limit(
            j,
            n_active,
            factor,
            design.pemfc
        )

        constraint = "inventory_limited"

        if n_active == 0:
            new_state, idle_out = idle_step(state, design, dt_s)

            idle_out.update({
                "mode": "discharge_block_empty_tank",
                "P_grid_MW": 0.0,
                "E_comprada_MWh": 0.0,
                "E_vendida_MWh": 0.0,
                "n_active": 0,
                "j_A_cm2": 0.0,
                "constraint": constraint,
            })

            return new_state, idle_out

        out = pemfc_grid_power_from_j(
            j,
            design,
            n_active,
            p_H2,
            p_O2
        )

    n_H2_cons = out["n_H2_mol_s"] * dt_s
    n_O2_cons = out["n_O2_mol_s"] * dt_s

    raw_state = HESSState(
        n_H2_mol=state.n_H2_mol - n_H2_cons,
        n_O2_mol=state.n_O2_mol - n_O2_cons,
        hour=state.hour + 1,
    )

    new_state = apply_leakage_and_clip(raw_state, design, dt_s)

    soc_H2, soc_O2 = tank_soc(design, new_state)
    p_H2_new, p_O2_new = tank_pressures(design, new_state)

    E_vendida = out["P_grid_MW_abs"] * dt_h

    return new_state, {
        "mode": "discharge",
        "constraint": constraint,
        "P_grid_MW": out["P_grid_MW_abs"],
        "P_grid_MW_abs": out["P_grid_MW_abs"],
        "E_comprada_MWh": 0.0,
        "E_vendida_MWh": E_vendida,
        "n_active": n_active,
        "j_A_cm2": j,
        "V_cell_V": out["V_cell_V"],
        "E_rev_V": out["E_rev_V"],
        "eta_act_V": out["eta_act_V"],
        "eta_ohm_V": out["eta_ohm_V"],
        "eta_conc_V": out["eta_conc_V"],
        "eta_fc_lhv": out["eta_fc_lhv"],
        "P_dc_total_MW": out["P_dc_total_MW"],
        "P_aux_MW": out["P_aux_MW"],
        "P_comp_MW": 0.0,
        "n_H2_prod_mol": 0.0,
        "n_O2_prod_mol": 0.0,
        "n_H2_cons_mol": n_H2_cons,
        "n_O2_cons_mol": n_O2_cons,
        "soc_H2": soc_H2,
        "soc_O2": soc_O2,
        "p_H2_bar": p_H2_new,
        "p_O2_bar": p_O2_new,
    }


def stack_capacity_report(design: HESSDesign) -> Dict[str, float]:
    """
    Chequeo rápido de potencia máxima con los parámetros electroquímicos actuales.
    Sirve para verificar si los stacks instalados realmente alcanzan 100 MW.
    """
    design = size_tanks_from_storage_hours(design)

    state = initial_state_from_soc(design, soc0=0.50)
    p_H2, p_O2 = tank_pressures(design, state)

    n_el = installed_stacks(design, "pemel")
    n_fc = installed_stacks(design, "pemfc")

    el = pemel_grid_power_from_j(
        design.pemel.j_max_A_cm2,
        design,
        n_el,
        p_H2,
        p_O2
    )

    fc = pemfc_grid_power_from_j(
        design.pemfc.j_max_A_cm2,
        design,
        n_fc,
        p_H2,
        p_O2
    )

    return {
        "n_pemel": n_el,
        "n_pemfc": n_fc,
        "P_pemel_max_grid_MW": el["P_grid_MW_abs"],
        "P_pemfc_max_grid_MW": fc["P_grid_MW_abs"],
        "eta_el_lhv_at_jmax": el["eta_el_lhv"],
        "eta_fc_lhv_at_jmax": fc["eta_fc_lhv"],
    }


# ===================================================================
# EJEMPLO MÍNIMO (smoke test)
# ===================================================================
#def example_dispatch_24h():
    #"""Ejemplo mínimo que demuestra cómo usar el módulo (sin electroquímica real).
    #El estudiante debe reemplazar esto con su propio modelo completo."""
    #design = HESSDesign(x_MW=100.0, storage_hours=12.0)
    #design.n_pemel = 100; design.n_pemfc = 100
    #design = size_tanks_from_storage_hours(design, eta_fc_guess=0.50)
    #state = initial_state_from_soc(design, soc0=0.45)
#
    #print("=== Smoke test HESS_model.py ===")
    #print(f"Tanques: V_H2={design.tanks.V_h2_m3:.0f} m3, V_O2={design.tanks.V_o2_m3:.0f} m3")
    #lim = tank_limits(design)
    #m_h2 = (lim['n_H2_max_mol']-lim['n_H2_min_mol'])*M_H2
    #print(f"Masa H2 usable: {m_h2:.0f} kg, p_max={design.tanks.p_h2_max_bar} bar")
#
    ## Simular 24h sólo con idle (demuestra que el módulo carga)
    #for h in range(24):
        #state, out = idle_step(state, design)
    #soc_h2, soc_o2 = tank_soc(design, state)
    #print(f"24h idle: SoC H2={soc_h2:.3f}, SoC O2={soc_o2:.3f}")
    #print("El módulo base funciona. Ahora programe la electroquímica.")
    #return design, state
#
#if __name__ == "__main__":
    #example_dispatch_24h()
