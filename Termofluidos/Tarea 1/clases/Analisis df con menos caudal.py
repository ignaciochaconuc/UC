import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================================================
# 1) LEER Y PREPARAR BASE
# =========================================================
archivo = "df_final_v2.xlsx"
df = pd.read_excel(archivo)

df["time"] = pd.to_datetime(df["time"])
df["hora"] = df["time"].dt.hour
df["dia"] = df["time"].dt.day
df["dow"] = df["time"].dt.dayofweek   # lunes=0 ... domingo=6

# =========================================================
# 2) FILTRO HORARIO METRO
#    Aproximación para datos horarios:
#    Lun-Vie : 06 a 22
#    Sábado  : 07 a 22
#    Domingo : 08 a 22
# =========================================================
cond_luv = (df["dow"].between(0, 4)) & (df["hora"].between(6, 22))
cond_sat = (df["dow"] == 5) & (df["hora"].between(7, 22))
cond_dom = (df["dow"] == 6) & (df["hora"].between(8, 22))

df_op = df[cond_luv | cond_sat | cond_dom].copy()

# =========================================================
# 3) VARIABLES ÚTILES
# =========================================================
df_op["dT_enfriamiento"] = df_op["T_metro"] - df_op["T_2"]

# Agua evaporada
df_op["m_agua_evaporada"] = (df_op["m_punto_red"] - df_op["m_agua_restante"]).clip(lower=0)

# Agua no evaporada
df_op["m_agua_no_evaporada"] = df_op["m_agua_restante"].clip(lower=0)

# Porcentaje no evaporado
df_op["pct_no_evaporada"] = np.where(
    df_op["m_punto_red"] > 0,
    100 * df_op["m_agua_no_evaporada"] / df_op["m_punto_red"],
    np.nan
)

# =========================================================
# 4) ESTADÍSTICOS POR HORA
# =========================================================
stats_hora = df_op.groupby("hora").agg(
    T2_mean=("T_2", "mean"),
    T2_p25=("T_2", lambda x: x.quantile(0.25)),
    T2_p75=("T_2", lambda x: x.quantile(0.75)),
    Tmetro_mean=("T_metro", "mean"),
    Tamb_mean=("temp_ambiente", "mean"),
    agua_evap_mean=("m_agua_evaporada", "mean"),
    pct_no_evap_mean=("pct_no_evaporada", "mean")
).reset_index()

T2_promedio_global = df_op["T_2"].mean()

# =========================================================
# 5) GRÁFICO 1:
#    PERFIL DE TEMPERATURAS
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

plt.axhline(
    T2_promedio_global,
    linestyle="--",
    linewidth=1.5,
    label=f"T2 promedio global = {T2_promedio_global:.2f} °C"
)

plt.xticks(stats_hora["hora"])
plt.xlabel("Hora del día")
plt.ylabel("Temperatura [°C]")
plt.title("Perfil horario de temperaturas en horario operativo de Metro")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# =========================================================
# 6) GRÁFICO 2:
#    HEATMAP DE T2
# =========================================================
tabla_T2 = df_op.pivot_table(index="dia", columns="hora", values="T_2")

plt.figure(figsize=(12, 7))
im = plt.imshow(tabla_T2.values, aspect="auto", origin="lower")

plt.colorbar(im, label="T2 [°C]")
plt.xticks(ticks=np.arange(len(tabla_T2.columns)), labels=tabla_T2.columns)
plt.yticks(ticks=np.arange(len(tabla_T2.index)), labels=tabla_T2.index)

plt.xlabel("Hora del día")
plt.ylabel("Día de febrero")
plt.title("Heatmap de T2 en horario operativo de Metro")
plt.tight_layout()
plt.show()

# =========================================================
# 7) GRÁFICO 3:
#    AGUA EVAPORADA PROMEDIO POR HORA
# =========================================================
plt.figure(figsize=(10, 6))

plt.bar(stats_hora["hora"], stats_hora["agua_evap_mean"], width=0.8)

plt.xticks(stats_hora["hora"])
plt.xlabel("Hora del día")
plt.ylabel("Agua evaporada promedio [kg/s]")
plt.title("Agua evaporada promedio por hora en horario operativo")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.show()

# =========================================================
# 8) GRÁFICO 4:
#    PORCENTAJE DE AGUA NO EVAPORADA
# =========================================================
plt.figure(figsize=(10, 6))

plt.bar(stats_hora["hora"], stats_hora["pct_no_evap_mean"], width=0.8)

plt.xticks(stats_hora["hora"])
plt.xlabel("Hora del día")
plt.ylabel("Agua no evaporada [% del caudal total]")
plt.title("Porcentaje de agua no evaporada por hora en horario operativo")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.show()