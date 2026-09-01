"""Funciones reutilizables para simular un caso HESS.

Este archivo reemplaza el loop monolítico de ``perfil.py`` por una función
que puede llamarse desde el caso base o desde el análisis paramétrico.

Debe estar en la misma carpeta que ``HESS_model.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from HESS_model import (
    HESSDesign,
    charge_step,
    discharge_step,
    idle_step,
    initial_state_from_soc,
    size_tanks_from_storage_hours,
    stack_capacity_report,
    tank_pressures,
    tank_soc,
)

COLUMNAS_REQUERIDAS = {"timestamp", "precio_usd_mwh", "P_cmd_MW"}


def cargar_perfil(ruta_csv: str | Path) -> pd.DataFrame:
    """Carga y valida el perfil horario de precios y potencia comandada."""
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el perfil de despacho: {ruta}")

    df = pd.read_csv(ruta)
    faltantes = COLUMNAS_REQUERIDAS.difference(df.columns)
    if faltantes:
        raise ValueError(
            "El perfil no contiene las columnas requeridas: "
            + ", ".join(sorted(faltantes))
        )

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df["precio_usd_mwh"] = pd.to_numeric(df["precio_usd_mwh"], errors="raise")
    df["P_cmd_MW"] = pd.to_numeric(df["P_cmd_MW"], errors="raise")
    df = df.sort_values("timestamp").reset_index(drop=True)

    if df.empty:
        raise ValueError("El perfil de despacho está vacío.")

    return df


def crear_diseno(
    storage_hours: float,
    n_pemfc: int,
    *,
    n_pemel: int = 100,
    x_MW: float = 100.0,
    p_stack_pemfc_MW: float = 0.70,
    eta_fc_guess: float = 0.50,
) -> HESSDesign:
    """Crea y dimensiona un diseño HESS para una combinación paramétrica."""
    if storage_hours <= 0:
        raise ValueError("storage_hours debe ser mayor que cero.")
    if n_pemfc <= 0 or n_pemel <= 0:
        raise ValueError("El número de stacks debe ser mayor que cero.")

    design = HESSDesign(
        x_MW=float(x_MW),
        storage_hours=float(storage_hours),
    )
    design.n_pemel = int(n_pemel)
    design.n_pemfc = int(n_pemfc)
    design.pemfc.p_stack_nom_MW = float(p_stack_pemfc_MW)

    return size_tanks_from_storage_hours(
        design,
        eta_fc_guess=float(eta_fc_guess),
    )


def _media_segura(serie: pd.Series) -> float:
    valores = pd.to_numeric(serie, errors="coerce").dropna()
    return float(valores.mean()) if not valores.empty else float("nan")


def simular_caso(
    df_perfil: pd.DataFrame,
    storage_hours: float,
    n_pemfc: int,
    *,
    n_pemel: int = 100,
    x_MW: float = 100.0,
    p_stack_pemfc_MW: float = 0.70,
    eta_fc_guess: float = 0.50,
    soc0: float = 0.50,
    dt_s: float = 3600.0,
    retornar_horario: bool = False,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    """Simula las 1464 horas de un diseño HESS.

    Parameters
    ----------
    df_perfil:
        DataFrame con ``timestamp``, ``precio_usd_mwh`` y ``P_cmd_MW``.
    storage_hours:
        Horas de almacenamiento utilizadas para dimensionar los tanques.
    n_pemfc:
        Número total de stacks PEMFC instalados.
    retornar_horario:
        Si es ``True``, además del resumen retorna el perfil horario completo.

    Returns
    -------
    resumen, df_horario
        ``df_horario`` es ``None`` cuando ``retornar_horario=False``.
    """
    faltantes = COLUMNAS_REQUERIDAS.difference(df_perfil.columns)
    if faltantes:
        raise ValueError(
            "El perfil no contiene las columnas requeridas: "
            + ", ".join(sorted(faltantes))
        )

    if not 0.0 <= soc0 <= 1.0:
        raise ValueError("soc0 debe estar entre 0 y 1.")
    if dt_s <= 0:
        raise ValueError("dt_s debe ser mayor que cero.")

    df = df_perfil.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values("timestamp").reset_index(drop=True)

    design = crear_diseno(
        storage_hours=storage_hours,
        n_pemfc=n_pemfc,
        n_pemel=n_pemel,
        x_MW=x_MW,
        p_stack_pemfc_MW=p_stack_pemfc_MW,
        eta_fc_guess=eta_fc_guess,
    )
    state = initial_state_from_soc(design, soc0=soc0)

    resultados: list[dict[str, Any]] = []

    for row in df.itertuples(index=False):
        timestamp = row.timestamp
        precio = float(row.precio_usd_mwh)
        P_cmd_MW = float(row.P_cmd_MW)

        if P_cmd_MW < 0.0:
            state, out = charge_step(
                state=state,
                design=design,
                P_cmd_MW=abs(P_cmd_MW),
                dt_s=dt_s,
            )
        elif P_cmd_MW > 0.0:
            state, out = discharge_step(
                state=state,
                design=design,
                P_cmd_MW=P_cmd_MW,
                dt_s=dt_s,
            )
        else:
            state, out = idle_step(
                state=state,
                design=design,
                dt_s=dt_s,
            )
            out["P_grid_MW"] = 0.0
            out["E_comprada_MWh"] = 0.0
            out["E_vendida_MWh"] = 0.0

        soc_h2, soc_o2 = tank_soc(design, state)
        p_h2, p_o2 = tank_pressures(design, state)

        E_comprada = float(out.get("E_comprada_MWh", 0.0))
        E_vendida = float(out.get("E_vendida_MWh", 0.0))
        costo = E_comprada * precio
        ingreso = E_vendida * precio

        resultados.append(
            {
                "timestamp": timestamp,
                "precio_usd_mwh": precio,
                "P_cmd_MW": P_cmd_MW,
                "modo": out.get("mode", "desconocido"),
                "constraint": out.get("constraint", "sin_restriccion"),
                "P_real_MW": float(out.get("P_grid_MW", 0.0)),
                "E_comprada_MWh": E_comprada,
                "E_vendida_MWh": E_vendida,
                "costo_USD": costo,
                "ingreso_USD": ingreso,
                "flujo_USD": ingreso - costo,
                "soc_H2": soc_h2,
                "soc_O2": soc_o2,
                "p_H2_bar": p_h2,
                "p_O2_bar": p_o2,
                "n_H2_mol": state.n_H2_mol,
                "n_O2_mol": state.n_O2_mol,
                "n_active": int(out.get("n_active", 0)),
                "j_A_cm2": float(out.get("j_A_cm2", 0.0)),
                "V_cell_V": out.get("V_cell_V", np.nan),
                "E_rev_V": out.get("E_rev_V", np.nan),
                "eta_el_lhv": out.get("eta_el_lhv", np.nan),
                "eta_fc_lhv": out.get("eta_fc_lhv", np.nan),
                "P_dc_total_MW": out.get("P_dc_total_MW", 0.0),
                "P_aux_MW": out.get("P_aux_MW", 0.0),
                "P_comp_MW": out.get("P_comp_MW", 0.0),
                "n_H2_prod_mol": out.get("n_H2_prod_mol", 0.0),
                "n_H2_cons_mol": out.get("n_H2_cons_mol", 0.0),
                "n_O2_prod_mol": out.get("n_O2_prod_mol", 0.0),
                "n_O2_cons_mol": out.get("n_O2_cons_mol", 0.0),
            }
        )

    df_horario = pd.DataFrame(resultados)
    E_comprada_total = float(df_horario["E_comprada_MWh"].sum())
    E_vendida_total = float(df_horario["E_vendida_MWh"].sum())
    socf = float(df_horario["soc_H2"].iloc[-1])
    delta_soc = socf - float(soc0)

    descarga = df_horario["P_cmd_MW"] > 0
    carga = df_horario["P_cmd_MW"] < 0
    constraints = df_horario["constraint"].fillna("sin_restriccion")
    modos = df_horario["modo"].fillna("desconocido")

    limitaciones_materiales = {
        "inventory_limited",
        "tank_capacity_limited",
    }
    modos_sin_operacion = {
        "discharge_block_empty_tank",
        "charge_block_tank_full",
    }

    capacity = stack_capacity_report(design)

    resumen: dict[str, Any] = {
        "storage_hours": float(storage_hours),
        "n_pemfc": int(n_pemfc),
        "n_pemel": int(n_pemel),
        "x_MW": float(x_MW),
        "soc_inicial": float(soc0),
        "soc_final": socf,
        "delta_soc": delta_soc,
        "abs_delta_soc": abs(delta_soc),
        "ciclico_tol_1pct": bool(abs(delta_soc) <= 0.01),
        "horas_simuladas": int(len(df_horario)),
        "E_comprada_MWh": E_comprada_total,
        "E_vendida_MWh": E_vendida_total,
        "RTE": (
            E_vendida_total / E_comprada_total
            if E_comprada_total > 0.0
            else np.nan
        ),
        "costo_total_USD": float(df_horario["costo_USD"].sum()),
        "ingreso_total_USD": float(df_horario["ingreso_USD"].sum()),
        "margen_total_USD": float(df_horario["flujo_USD"].sum()),
        "soc_H2_min": float(df_horario["soc_H2"].min()),
        "soc_H2_max": float(df_horario["soc_H2"].max()),
        "soc_O2_min": float(df_horario["soc_O2"].min()),
        "soc_O2_max": float(df_horario["soc_O2"].max()),
        "p_H2_min_bar": float(df_horario["p_H2_bar"].min()),
        "p_H2_max_bar": float(df_horario["p_H2_bar"].max()),
        "p_O2_min_bar": float(df_horario["p_O2_bar"].min()),
        "p_O2_max_bar": float(df_horario["p_O2_bar"].max()),
        "P_descarga_real_prom_MW": _media_segura(
            df_horario.loc[descarga, "P_real_MW"]
        ),
        "P_descarga_real_max_MW": float(
            df_horario.loc[descarga, "P_real_MW"].max()
        ) if descarga.any() else np.nan,
        "P_carga_real_prom_MW": _media_segura(
            -df_horario.loc[carga, "P_real_MW"]
        ),
        "eta_el_lhv_prom": _media_segura(
            df_horario.loc[carga, "eta_el_lhv"]
        ),
        "eta_fc_lhv_prom": _media_segura(
            df_horario.loc[descarga, "eta_fc_lhv"]
        ),
        "n_active_descarga_prom": _media_segura(
            df_horario.loc[descarga, "n_active"]
        ),
        "n_active_descarga_max": int(
            df_horario.loc[descarga, "n_active"].max()
        ) if descarga.any() else 0,
        "horas_above_max_power": int((constraints == "above_max_power").sum()),
        "horas_inventory_limited": int((constraints == "inventory_limited").sum()),
        "horas_tank_capacity_limited": int(
            (constraints == "tank_capacity_limited").sum()
        ),
        "horas_tanque_vacio": int(
            (modos == "discharge_block_empty_tank").sum()
        ),
        "horas_tanque_lleno": int(
            (modos == "charge_block_tank_full").sum()
        ),
        "sin_limites_materiales": bool(
            (~constraints.isin(limitaciones_materiales)).all()
            and (~modos.isin(modos_sin_operacion)).all()
        ),
        "V_H2_m3": float(design.tanks.V_h2_m3),
        "V_O2_m3": float(design.tanks.V_o2_m3),
        "P_pemel_max_grid_MW": float(capacity["P_pemel_max_grid_MW"]),
        "P_pemfc_max_grid_MW": float(capacity["P_pemfc_max_grid_MW"]),
    }
    resumen["factible_operacional"] = bool(
        resumen["ciclico_tol_1pct"] and resumen["sin_limites_materiales"]
    )

    if retornar_horario:
        return resumen, df_horario
    return resumen, None


def simular_caso_desde_csv(
    ruta_csv: str | Path,
    storage_hours: float,
    n_pemfc: int,
    **kwargs: Any,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    """Atajo para cargar el perfil y simular un caso."""
    df = cargar_perfil(ruta_csv)
    return simular_caso(
        df,
        storage_hours=storage_hours,
        n_pemfc=n_pemfc,
        **kwargs,
    )
