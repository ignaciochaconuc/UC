import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =========================================================
# 1) Leer y preparar base
# =========================================================
archivo = "df_final_v2.xlsx"
df = pd.read_excel(archivo)

df["time"] = pd.to_datetime(df["time"])
df["fecha"] = pd.to_datetime(df["fecha"])
df["hora"] = df["hora"].astype(int)
df["dia"] = df["time"].dt.day

# Variables útiles
df["dT_enfriamiento"] = df["T_metro"] - df["T_2"]

# Agua efectivamente evaporada
# Se asume que m_punto_red y m_agua_restante están en las mismas unidades
df["m_agua_evaporada"] = (df["m_punto_red"] - df["m_agua_restante"]).clip(lower=0)

# Humedad relativa en %
if df["phi_1"].max() <= 1.5:
    df["phi_1_pct"] = df["phi_1"] * 100
else:
    df["phi_1_pct"] = df["phi_1"]

if df["phi_2"].max() <= 1.5:
    df["phi_2_pct"] = df["phi_2"] * 100
else:
    df["phi_2_pct"] = df["phi_2"]


# =========================================================
# 2) Estadísticos por hora
# =========================================================
stats_hora = df.groupby("hora").agg(
    T2_mean=("T_2", "mean"),
    T2_p25=("T_2", lambda x: x.quantile(0.25)),
    T2_p75=("T_2", lambda x: x.quantile(0.75)),
    Tmetro_mean=("T_metro", "mean"),
    Tamb_mean=("temp_ambiente", "mean"),
    dT_mean=("dT_enfriamiento", "mean"),
    dT_p25=("dT_enfriamiento", lambda x: x.quantile(0.25)),
    dT_p75=("dT_enfriamiento", lambda x: x.quantile(0.75)),
    agua_evap_mean=("m_agua_evaporada", "mean")
).reset_index()


# =========================================================
# 3) Gráfico 1:
#    Perfil horario de temperaturas
# =========================================================
plt.figure(figsize=(10, 6))

plt.plot(stats_hora["hora"], stats_hora["Tamb_mean"], marker="o", label="T ambiente promedio")
plt.plot(stats_hora["hora"], stats_hora["Tmetro_mean"], marker="o", label="T metro promedio")
plt.plot(stats_hora["hora"], stats_hora["T2_mean"], marker="o", linewidth=2, label="T2 promedio")

plt.fill_between(
    stats_hora["hora"],
    stats_hora["T2_p25"],
    stats_hora["T2_p75"],
    alpha=0.2,
    label="Rango intercuartílico T2"
)

plt.xticks(range(0, 24))
plt.xlabel("Hora del día")
plt.ylabel("Temperatura [°C]")
plt.title("Perfil horario de temperaturas")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


# =========================================================
# 4) Gráfico 2:
#    Heatmap día-hora de T2
# =========================================================
tabla_T2 = df.pivot_table(index="dia", columns="hora", values="T_2")

plt.figure(figsize=(12, 7))
im = plt.imshow(tabla_T2.values, aspect="auto", origin="lower")

plt.colorbar(im, label="T2 [°C]")
plt.xticks(ticks=np.arange(24), labels=np.arange(24))
plt.yticks(ticks=np.arange(len(tabla_T2.index)), labels=tabla_T2.index)

plt.xlabel("Hora del día")
plt.ylabel("Día de febrero")
plt.title("Heatmap de T2 por día y hora")
plt.tight_layout()
plt.show()


# =========================================================
# 5) Gráfico 3:
#    Enfriamiento logrado: dT = T_metro - T2
# =========================================================
plt.figure(figsize=(10, 6))

plt.plot(stats_hora["hora"], stats_hora["dT_mean"], marker="o", linewidth=2, label="ΔT promedio")
plt.fill_between(
    stats_hora["hora"],
    stats_hora["dT_p25"],
    stats_hora["dT_p75"],
    alpha=0.2,
    label="Rango intercuartílico ΔT"
)

plt.xticks(range(0, 24))
plt.xlabel("Hora del día")
plt.ylabel("ΔT = T_metro - T2 [°C]")
plt.title("Enfriamiento evaporativo logrado por hora")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


# =========================================================
# 6) Gráfico 4:
#    Agua evaporada promedio por hora
# =========================================================
plt.figure(figsize=(10, 6))

plt.bar(stats_hora["hora"], stats_hora["agua_evap_mean"], width=0.8)
plt.xticks(range(0, 24))
plt.xlabel("Hora del día")
plt.ylabel("Agua evaporada promedio [kg/s]")
plt.title("Agua evaporada promedio por hora")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.show()



# Agua evaporada
df["m_agua_evaporada"] = (df["m_punto_red"] - df["m_agua_restante"]).clip(lower=0)

# Agua no evaporada
df["m_agua_no_evaporada"] = df["m_agua_restante"].clip(lower=0)

# Fracción no evaporada
df["fraccion_no_evaporada"] = df["m_agua_no_evaporada"] / df["m_punto_red"]

# =========================================================
# 3) Promedios por hora
# =========================================================
stats_agua = df.groupby("hora").agg(
    agua_in=("m_punto_red", "mean"),
    agua_evap=("m_agua_evaporada", "mean"),
    agua_no_evap=("m_agua_no_evaporada", "mean"),
    frac_no_evap=("fraccion_no_evaporada", "mean")
).reset_index()

plt.bar(stats_agua["hora"], stats_agua["frac_no_evap"] * 100)

plt.xticks(range(24))
plt.xlabel("Hora del día")
plt.ylabel("Agua no evaporada [% del caudal total]")
plt.title("Porcentaje de agua no evaporada por hora")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.show()