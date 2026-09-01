import pandas as pd

from HESS_model import (
    HESSDesign,
    size_tanks_from_storage_hours,
    initial_state_from_soc,
    idle_step,
    tank_soc,
    tank_pressures,
    charge_step,
    discharge_step,
    M_H2,
    M_O2
)


RUTA_PERFIL = "perfil_despacho_completo_preliminar (3).csv"

df = pd.read_csv(RUTA_PERFIL)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)



HORAS_ALMACENAMIENTO = 8
N_STACKS_PEMEL = 100
N_STACKS_PEMFC = 106

SOC_INICIAL = 0.50
TOLERANCIA_SOC = 0.01      
DT_S = 3600.0



design = HESSDesign(
    x_MW=100.0,
    storage_hours=HORAS_ALMACENAMIENTO
)

design.n_pemel = N_STACKS_PEMEL
design.n_pemfc = N_STACKS_PEMFC

# Se mantiene el valor utilizado en el análisis paramétrico
design.pemfc.p_stack_nom_MW = 0.70

# Dimensionamiento de tanques
design = size_tanks_from_storage_hours(
    design,
    eta_fc_guess=0.50
)

# Estado inicial
state = initial_state_from_soc(
    design,
    soc0=SOC_INICIAL
)



resultados = []

for _, row in df.iterrows():

    timestamp = row["timestamp"]
    precio = row["precio_usd_mwh"]
    P_cmd_MW = row["P_cmd_MW"]


    if P_cmd_MW < 0:

        state, out = charge_step(
            state=state,
            design=design,
            P_cmd_MW=abs(P_cmd_MW),
            dt_s=DT_S
        )

    elif P_cmd_MW > 0:

        state, out = discharge_step(
            state=state,
            design=design,
            P_cmd_MW=P_cmd_MW,
            dt_s=DT_S
        )

    else:

        state, out = idle_step(
            state=state,
            design=design,
            dt_s=DT_S
        )

        out["P_grid_MW"] = 0.0
        out["E_comprada_MWh"] = 0.0
        out["E_vendida_MWh"] = 0.0


    soc_h2, soc_o2 = tank_soc(design, state)
    p_h2, p_o2 = tank_pressures(design, state)


    E_comprada = out.get("E_comprada_MWh", 0.0)
    E_vendida = out.get("E_vendida_MWh", 0.0)

    costo_USD = E_comprada * precio
    ingreso_USD = E_vendida * precio

    n_H2_prod_mol = out.get("n_H2_prod_mol", 0.0)
    n_H2_cons_mol = out.get("n_H2_cons_mol", 0.0)

    n_O2_prod_mol = out.get("n_O2_prod_mol", 0.0)
    n_O2_cons_mol = out.get("n_O2_cons_mol", 0.0)

    resultados.append({

        # Tiempo y operación
        "timestamp": timestamp,
        "precio_usd_mwh": precio,
        "P_cmd_MW": P_cmd_MW,
        "modo": out.get("mode", "desconocido"),
        "constraint": out.get(
            "constraint",
            "sin_restriccion"
        ),

        # Potencia y energía
        "P_real_MW": out.get("P_grid_MW", 0.0),
        "P_dc_total_MW": out.get("P_dc_total_MW", 0.0),
        "P_aux_MW": out.get("P_aux_MW", 0.0),
        "P_comp_MW": out.get("P_comp_MW", 0.0),

        "E_comprada_MWh": E_comprada,
        "E_vendida_MWh": E_vendida,

        # Resultados económicos
        "costo_USD": costo_USD,
        "ingreso_USD": ingreso_USD,
        "flujo_USD": ingreso_USD - costo_USD,

        # Estado de tanques
        "soc_H2": soc_h2,
        "soc_O2": soc_o2,
        "p_H2_bar": p_h2,
        "p_O2_bar": p_o2,

        "n_H2_mol": state.n_H2_mol,
        "n_O2_mol": state.n_O2_mol,

        # Producción de especies
        "n_H2_prod_mol": n_H2_prod_mol,
        "n_H2_cons_mol": n_H2_cons_mol,
        "n_O2_prod_mol": n_O2_prod_mol,
        "n_O2_cons_mol": n_O2_cons_mol,

        "m_H2_prod_kg": n_H2_prod_mol * M_H2,
        "m_H2_cons_kg": n_H2_cons_mol * M_H2,
        "m_O2_prod_kg": n_O2_prod_mol * M_O2,
        "m_O2_cons_kg": n_O2_cons_mol * M_O2,

        # Electroquímica
        "n_active": out.get("n_active", 0),
        "j_A_cm2": out.get("j_A_cm2", 0.0),
        "V_cell_V": out.get("V_cell_V", None),
        "E_rev_V": out.get("E_rev_V", None),
        "eta_el_lhv": out.get("eta_el_lhv", None),
        "eta_fc_lhv": out.get("eta_fc_lhv", None)
    })


df_final = pd.DataFrame(resultados)


E_comprada_total = df_final["E_comprada_MWh"].sum()
E_vendida_total = df_final["E_vendida_MWh"].sum()

if E_comprada_total > 0:
    RTE = E_vendida_total / E_comprada_total
else:
    RTE = float("nan")

soc_final = df_final["soc_H2"].iloc[-1]
delta_soc = soc_final - SOC_INICIAL

es_ciclico = abs(delta_soc) <= TOLERANCIA_SOC

horas_descarga = df_final["P_real_MW"] > 0

if horas_descarga.any():
    P_descarga_prom = df_final.loc[
        horas_descarga,
        "P_real_MW"
    ].mean()

    P_descarga_max = df_final.loc[
        horas_descarga,
        "P_real_MW"
    ].max()
else:
    P_descarga_prom = 0.0
    P_descarga_max = 0.0


resumen_final = pd.DataFrame([{

    "storage_hours": HORAS_ALMACENAMIENTO,
    "n_pemel": N_STACKS_PEMEL,
    "n_pemfc": N_STACKS_PEMFC,

    "V_H2_m3": design.tanks.V_h2_m3,
    "V_O2_m3": design.tanks.V_o2_m3,

    "E_comprada_MWh": E_comprada_total,
    "E_vendida_MWh": E_vendida_total,
    "RTE": RTE,
    "RTE_pct": 100 * RTE,

    "costo_total_USD": df_final["costo_USD"].sum(),
    "ingreso_total_USD": df_final["ingreso_USD"].sum(),
    "margen_total_USD": df_final["flujo_USD"].sum(),

    "soc_inicial": SOC_INICIAL,
    "soc_final": soc_final,
    "delta_soc": delta_soc,
    "error_soc_pct": abs(delta_soc) * 100,
    "caso_ciclico_1pct": es_ciclico,

    "soc_H2_min": df_final["soc_H2"].min(),
    "soc_H2_max": df_final["soc_H2"].max(),

    "p_H2_min_bar": df_final["p_H2_bar"].min(),
    "p_H2_max_bar": df_final["p_H2_bar"].max(),

    "P_descarga_prom_MW": P_descarga_prom,
    "P_descarga_max_MW": P_descarga_max,

    "H2_producido_total_kg":
        df_final["m_H2_prod_kg"].sum(),

    "H2_consumido_total_kg":
        df_final["m_H2_cons_kg"].sum(),

    "O2_producido_total_kg":
        df_final["m_O2_prod_kg"].sum(),

    "O2_consumido_total_kg":
        df_final["m_O2_cons_kg"].sum(),

    "horas_limitadas_inventario": (
        df_final["constraint"] == "inventory_limited"
    ).sum(),

    "horas_limitadas_tanque": (
        df_final["constraint"] == "tank_capacity_limited"
    ).sum(),

    "horas_sobre_potencia_maxima": (
        df_final["constraint"] == "above_max_power"
    ).sum()
}])


df_final.to_csv(
    "perfil_horario_HESS_final_8h_106stacks.csv",
    index=False
)

resumen_final.to_csv(
    "resumen_HESS_final_8h_106stacks.csv",
    index=False
)


pd.set_option(
    "display.float_format",
    "{:,.4f}".format
)

print("\n========================================")
print("CASO FINAL HESS")
print("8 horas - 106 stacks PEMFC")
print("========================================")

print(resumen_final.T)

print("\nCondición cíclica:")
print(f"SoC inicial       = {SOC_INICIAL:.6f}")
print(f"SoC final         = {soc_final:.6f}")
print(f"Diferencia SoC    = {delta_soc:.6f}")
print(f"Error absoluto    = {abs(delta_soc) * 100:.4f} %")

if es_ciclico:
    print("Resultado: CASO CÍCLICO")
else:
    print("Resultado: CASO NO CÍCLICO")