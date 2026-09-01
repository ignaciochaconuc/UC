import pandas as pd
import matplotlib.pyplot as plt
import numpy as np



df_hist = pd.read_csv("DHC_PVSYST_E_5OUW1S.csv", sep=";", skiprows=10)

df_hist = df_hist.iloc[1:].copy()

for col in df_hist.columns:
    df_hist[col] = pd.to_numeric(df_hist[col], errors="coerce")


df_hist["datetime"] = pd.to_datetime({
    "year": df_hist["YEAR"],
    "month": df_hist["MONTH"],
    "day": df_hist["DAY"],
    "hour": df_hist["HOUR"],
    "minute": df_hist["MINUTE"]
})

df_2015 = df_hist[df_hist["YEAR"] == 2015].copy()


df_tmy = pd.read_csv("DHTMY_E_O4IQ3Q.csv", skiprows=41)

df_tmy = df_tmy.rename(columns={"Fecha/Hora": "datetime"})


df_tmy["datetime"] = pd.to_datetime(df_tmy["datetime"])

for col in df_tmy.columns:
    if col != "datetime":
        df_tmy[col] = pd.to_numeric(df_tmy[col], errors="coerce")


df_tmy = df_tmy.rename(columns={
    "ghi": "GHI",
    "difh": "DHI",
    "dni": "DNI",
    "temp": "TAMB"
})


df_2015["doy"] = df_2015["datetime"].dt.dayofyear
df_2015["month"] = df_2015["datetime"].dt.month
df_2015["day"] = df_2015["datetime"].dt.day
df_2015["hour"] = df_2015["datetime"].dt.hour

df_tmy["doy"] = df_tmy["datetime"].dt.dayofyear
df_tmy["month"] = df_tmy["datetime"].dt.month
df_tmy["day"] = df_tmy["datetime"].dt.day
df_tmy["hour"] = df_tmy["datetime"].dt.hour


hist = df_2015.copy()
tmy = df_tmy.copy()


hist = hist[~((hist["month"] == 2) & (hist["day"] == 29))].copy()
tmy  = tmy[~((tmy["month"] == 2) & (tmy["day"] == 29))].copy()


temp_hist_daily = hist.groupby("doy")["TAMB"].mean()
temp_tmy_daily  = tmy.groupby("doy")["TAMB"].mean()

plt.figure(figsize=(12,5))
plt.plot(temp_hist_daily.index, temp_hist_daily.values, label="Año 2015")
plt.plot(temp_tmy_daily.index, temp_tmy_daily.values, label="TMY")
plt.xlabel("Día del año")
plt.ylabel("Temperatura [°C]")
plt.title("Temperatura media diaria")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


ghi_hist_daily = hist.groupby("doy")["GHI"].sum()
ghi_tmy_daily  = tmy.groupby("doy")["GHI"].sum()

dni_hist_daily = hist.groupby("doy")["DNI"].sum()
dni_tmy_daily  = tmy.groupby("doy")["DNI"].sum()

dhi_hist_daily = hist.groupby("doy")["DHI"].sum()
dhi_tmy_daily  = tmy.groupby("doy")["DHI"].sum()



plt.figure(figsize=(12,5))
plt.plot(ghi_hist_daily.index, ghi_hist_daily.values, label="2015")
plt.plot(ghi_tmy_daily.index, ghi_tmy_daily.values, label="TMY")
plt.xlabel("Día del año")
plt.ylabel("kWh/m²·día")
plt.title("GHI diaria")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


plt.figure(figsize=(12,5))
plt.plot(dni_hist_daily.index, dni_hist_daily.values, label="2015")
plt.plot(dni_tmy_daily.index, dni_tmy_daily.values, label="TMY")
plt.xlabel("Día del año")
plt.ylabel("kWh/m²·día")
plt.title("DNI diaria")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


plt.figure(figsize=(12,5))
plt.plot(dhi_hist_daily.index, dhi_hist_daily.values, label="2015")
plt.plot(dhi_tmy_daily.index, dhi_tmy_daily.values, label="TMY")
plt.xlabel("Día del año")
plt.ylabel("kWh/m²·día")
plt.title("DHI diaria")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()


cols_merge = ["month", "day", "hour"]

merge_rad = pd.merge(
    hist[cols_merge + ["doy", "GHI", "DNI"]],
    tmy[cols_merge + ["GHI", "DNI"]],
    on=cols_merge,
    suffixes=("_2015", "_TMY")
)


merge_rad["diff_GHI"] = merge_rad["GHI_TMY"] - merge_rad["GHI_2015"]
merge_rad["diff_DNI"] = merge_rad["DNI_TMY"] - merge_rad["DNI_2015"]


heat_ghi = merge_rad.pivot_table(index="hour", columns="doy", values="diff_GHI")
heat_dni = merge_rad.pivot_table(index="hour", columns="doy", values="diff_DNI")


vmax_ghi = np.nanmax(np.abs(heat_ghi.values))
vmax_dni = np.nanmax(np.abs(heat_dni.values))

# Heatmap GHI
plt.figure(figsize=(14,5))
plt.imshow(
    heat_ghi.values,
    aspect="auto",
    origin="lower",
    cmap="coolwarm",
    vmin=-vmax_ghi,
    vmax=vmax_ghi,
    extent=[1, 365, heat_ghi.index.min(), heat_ghi.index.max()]
)
plt.colorbar(label="ΔGHI = TMY - 2015 [W/m²]")
plt.xlabel("Día del año")
plt.ylabel("Hora del día")
plt.title("Heat map de diferencia de radiación global horizontal (GHI)")
plt.tight_layout()
plt.show()


plt.figure(figsize=(14,5))
plt.imshow(
    heat_dni.values,
    aspect="auto",
    origin="lower",
    cmap="coolwarm",
    vmin=-vmax_dni,
    vmax=vmax_dni,
    extent=[1, 365, heat_dni.index.min(), heat_dni.index.max()]
)
plt.colorbar(label="ΔDNI = TMY - 2015 [W/m²]")
plt.xlabel("Día del año")
plt.ylabel("Hora del día")
plt.title("Heat map de diferencia de radiación directa normal (DNI)")
plt.tight_layout()
plt.show()