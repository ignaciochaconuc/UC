import pandas as pd

df = pd.read_csv("perfil_despacho_completo_preliminar (3).csv")

df["timestamp"] = pd.to_datetime(df["timestamp"])


# ===============Loop Principal===============================

from HESS_model import (
    HESSDesign,
    size_tanks_from_storage_hours,
    initial_state_from_soc,
    idle_step,
    tank_soc,
    tank_pressures,
    charge_step,
    discharge_step,
    stack_capacity_report
)

# =========================
# Diseño base
# =========================

design = HESSDesign(
    x_MW=100.0,
    storage_hours=18.0
)

design.n_pemel = 100

# Aumentamos capacidad modular de la PEMFC
design.n_pemfc = 150
design.pemfc.p_stack_nom_MW = 0.70

design = size_tanks_from_storage_hours(
    design,
    eta_fc_guess=0.50
)

state = initial_state_from_soc(
    design,
    soc0=0.50
)

dt_s = 3600.0

# =========================
# Simulación horaria
# =========================

resultados = []

for i, row in df.iterrows():

    timestamp = row["timestamp"]
    precio = row["precio_usd_mwh"]
    P_cmd_MW = row["P_cmd_MW"]

    if P_cmd_MW < 0:
        state, out = charge_step(
            state=state,
            design=design,
            P_cmd_MW=abs(P_cmd_MW),
            dt_s=dt_s
        )

    elif P_cmd_MW > 0:
        state, out = discharge_step(
            state=state,
            design=design,
            P_cmd_MW=P_cmd_MW,
            dt_s=dt_s
        )

    else:
        state, out = idle_step(
            state=state,
            design=design,
            dt_s=dt_s
        )

        out["P_grid_MW"] = 0.0
        out["E_comprada_MWh"] = 0.0
        out["E_vendida_MWh"] = 0.0

    soc_h2, soc_o2 = tank_soc(design, state)
    p_h2, p_o2 = tank_pressures(design, state)

    costo_USD = out.get("E_comprada_MWh", 0.0) * precio
    ingreso_USD = out.get("E_vendida_MWh", 0.0) * precio

    resultados.append({
        "timestamp": timestamp,
        "precio_usd_mwh": precio,
        "P_cmd_MW": P_cmd_MW,
        "modo": out.get("mode", "desconocido"),
        "constraint": out.get("constraint", "sin_restriccion"),
        "P_real_MW": out.get("P_grid_MW", 0.0),
        "E_comprada_MWh": out.get("E_comprada_MWh", 0.0),
        "E_vendida_MWh": out.get("E_vendida_MWh", 0.0),
        "costo_USD": costo_USD,
        "ingreso_USD": ingreso_USD,
        "flujo_USD": ingreso_USD - costo_USD,
        "soc_H2": soc_h2,
        "soc_O2": soc_o2,
        "p_H2_bar": p_h2,
        "p_O2_bar": p_o2,
        "n_H2_mol": state.n_H2_mol,
        "n_O2_mol": state.n_O2_mol,
        "n_active": out.get("n_active", 0),
        "j_A_cm2": out.get("j_A_cm2", 0.0),
        "V_cell_V": out.get("V_cell_V", None),
        "E_rev_V": out.get("E_rev_V", None),
        "eta_el_lhv": out.get("eta_el_lhv", None),
        "eta_fc_lhv": out.get("eta_fc_lhv", None),
    })

df_hess = pd.DataFrame(resultados)

print("Filas en df_hess:", len(df_hess))
print(df_hess["modo"].value_counts())
print(df_hess["P_cmd_MW"].value_counts())


pd.set_option("display.float_format", "{:,.2f}".format)

resumen_hess = {
    "E_comprada_MWh": df_hess["E_comprada_MWh"].sum(),
    "E_vendida_MWh": df_hess["E_vendida_MWh"].sum(),
    "RTE_preliminar": df_hess["E_vendida_MWh"].sum() / df_hess["E_comprada_MWh"].sum(),
    "costo_total_USD": df_hess["costo_USD"].sum(),
    "ingreso_total_USD": df_hess["ingreso_USD"].sum(),
    "margen_total_USD": df_hess["flujo_USD"].sum(),
    "soc_H2_min": df_hess["soc_H2"].min(),
    "soc_H2_max": df_hess["soc_H2"].max(),
    "soc_O2_min": df_hess["soc_O2"].min(),
    "soc_O2_max": df_hess["soc_O2"].max(),
    "p_H2_min_bar": df_hess["p_H2_bar"].min(),
    "p_H2_max_bar": df_hess["p_H2_bar"].max(),
    "p_O2_min_bar": df_hess["p_O2_bar"].min(),
    "p_O2_max_bar": df_hess["p_O2_bar"].max()
}

resumen_hess = pd.DataFrame([resumen_hess])

print(resumen_hess.T)


df_hess.to_csv("perfil_horario_final_HESS.csv", index=False)
resumen_hess.to_csv("resumen_HESS_caso_base.csv", index=False)

soc0= 0.50
socf = df_hess["soc_H2"].iloc[-1]

print("SoC inicial:", soc0)
print("SoC final:", socf)
print("Diferencia:", socf - soc0)

# gráficos--------------------------------------------------

import matplotlib.pyplot as plt


# Asegurarse de que timestamp sea datetime
df_hess["timestamp"] = pd.to_datetime(df_hess["timestamp"])

# Opcional: ordenar por tiempo
df_hess = df_hess.sort_values("timestamp").reset_index(drop=True)

# grafico precio y despacho
plt.figure(figsize=(14,6))

ax1 = plt.gca()
ax1.plot(df_hess["timestamp"], df_hess["precio_usd_mwh"], label="Precio energía [USD/MWh]")
ax1.set_xlabel("Tiempo")
ax1.set_ylabel("Precio [USD/MWh]")

ax2 = ax1.twinx()
ax2.step(df_hess["timestamp"], df_hess["P_cmd_MW"], where="mid", label="P_cmd [MW]")
ax2.step(df_hess["timestamp"], df_hess["P_real_MW"], where="mid", label="P_real [MW]")
ax2.set_ylabel("Potencia [MW]")

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

plt.title("Precio de energía y perfil de despacho HESS")
plt.tight_layout()
plt.savefig("grafico_precio_y_despacho.png", dpi=300, bbox_inches="tight")
plt.show()

# SoC de h2 Y O2 ------------------------------------------------

plt.figure(figsize=(14,5))
plt.plot(df_hess["timestamp"], df_hess["soc_H2"], label="SoC H2")
plt.plot(df_hess["timestamp"], df_hess["soc_O2"], label="SoC O2")
plt.xlabel("Tiempo")
plt.ylabel("SoC [-]")
plt.title("Evolución del estado de carga de los tanques")
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafico_soc_tanques.png", dpi=300, bbox_inches="tight")
plt.show()

# Gráfico de presiones de H2 y O2 ------------------------------------------------

plt.figure(figsize=(14,5))
plt.plot(df_hess["timestamp"], df_hess["p_H2_bar"], label="Presión H2 [bar]")
plt.plot(df_hess["timestamp"], df_hess["p_O2_bar"], label="Presión O2 [bar]")
plt.xlabel("Tiempo")
plt.ylabel("Presión [bar]")
plt.title("Evolución de la presión en los tanques")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafico_presion_tanques.png", dpi=300, bbox_inches="tight")
plt.show()

# flujo económico -acumulado-----------------------------------------------
df_hess["flujo_acumulado_USD"] = df_hess["flujo_USD"].cumsum()

plt.figure(figsize=(14,5))
plt.plot(df_hess["timestamp"], df_hess["flujo_acumulado_USD"])
plt.xlabel("Tiempo")
plt.ylabel("Flujo acumulado [USD]")
plt.title("Flujo económico acumulado del caso base")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafico_flujo_acumulado.png", dpi=300, bbox_inches="tight")
plt.show()


#energía comprada y vendida por hora----------------------------

plt.figure(figsize=(14,5))
plt.step(df_hess["timestamp"], df_hess["E_comprada_MWh"], where="mid", label="E comprada [MWh]")
plt.step(df_hess["timestamp"], df_hess["E_vendida_MWh"], where="mid", label="E vendida [MWh]")
plt.xlabel("Tiempo")
plt.ylabel("Energía por hora [MWh]")
plt.title("Energía comprada y vendida por hora")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafico_energia_horaria.png", dpi=300, bbox_inches="tight")
plt.show()


