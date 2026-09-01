import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results.csv")

df.columns = ["timestamp", "P_solar", "Q_aux_only", "Q_aux"]


df["fecha"] = pd.to_datetime("2024 " + df["timestamp"], format="%Y %b %d, %I:%M %p")


Q_aux_only_anual = df["Q_aux_only"].sum()      # [kWh] demanda sin solar
Q_aux_anual      = df["Q_aux"].sum()           # [kWh] auxiliar consumida con solar
E_solar_anual    = Q_aux_only_anual - Q_aux_anual   # [kWh] energía solar ahorrada

frac_solar = (Q_aux_only_anual - Q_aux_anual) / Q_aux_only_anual

print("=" * 60)
print("C.1  CASO BASE  (A = 800 m²)")
print("=" * 60)
print(f"Energía demanda sin solar (Q_aux_only) : {Q_aux_only_anual:,.0f} kWh/año")
print(f"Energía auxiliar consumida (Q_aux)     : {Q_aux_anual:,.0f} kWh/año")
print(f"Energía solar anual ahorrada           : {E_solar_anual:,.0f} kWh/año")
print(f"FRACCIÓN SOLAR ANUAL                    : {frac_solar*100:.2f} %")
print()

verano   = df[(df["fecha"] >= "2024-01-01") & (df["fecha"] < "2024-01-08")]
invierno = df[(df["fecha"] >= "2024-07-01") & (df["fecha"] < "2024-07-08")]

fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

for ax, datos, titulo in [
    (axes[0], verano,   "Semana típica de VERANO (enero)"),
    (axes[1], invierno, "Semana típica de INVIERNO (julio)"),
]:
    horas = np.arange(len(datos))
    ax.plot(horas, datos["P_solar"],    label="Potencia solar entregada", color="#E8A33D", lw=1.8)
    ax.plot(horas, datos["Q_aux_only"], label="Demanda del proceso",       color="#3D6FE8", lw=1.8, ls="--")
    ax.set_title(titulo)
    ax.set_xlabel("Hora de la semana")
    ax.set_xticks(np.arange(0, 169, 24))
    ax.grid(alpha=0.3)

axes[0].set_ylabel("Potencia [kW]")
axes[0].legend(loc="upper right")
fig.suptitle("Potencia solar entregada vs. demanda del proceso", fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig("fig_semanas.png", dpi=150, bbox_inches="tight")
print("Guardado: fig_semanas.png")
print()

par = pd.read_csv("parametrico-results.csv", header=None, index_col=0)

# Localizar las filas de interés por su etiqueta
fila_area = [i for i in par.index if "Collector area" in str(i)][0]
fila_fs   = [i for i in par.index if "Solar fraction" in str(i)][0]

areas = par.loc[fila_area].astype(float).values        # [m²]
fs    = par.loc[fila_fs].astype(float).values * 100.0  # [%]

orden = np.argsort(areas)
areas, fs = areas[orden], fs[orden]

def area_para_fraccion(objetivo, areas, fs):
    if objetivo > fs.max():
        return None
    return float(np.interp(objetivo, fs, areas))

print("=" * 60)
print("C.2  ANÁLISIS PARAMÉTRICO")
print("=" * 60)
print(f"Rango de área evaluado: {areas.min():.0f} – {areas.max():.0f} m²")
print(f"Fracción solar máxima alcanzada: {fs.max():.1f} % (a {areas[np.argmax(fs)]:.0f} m²)")
print()
for objetivo in [30, 50, 70]:
    a = area_para_fraccion(objetivo, areas, fs)
    if a is None:
        print(f"  FS = {objetivo}% : NO alcanzable en el rango evaluado")
    else:
        print(f"  FS = {objetivo}% : ~{a:,.0f} m²")
print()

fig2, ax = plt.subplots(figsize=(9, 6))
ax.plot(areas, fs, "o-", color="#E8A33D", lw=2, ms=5, label="Fracción Solar Anual")

for objetivo, color in [(30, "#888"), (50, "#888"), (70, "#888")]:
    a = area_para_fraccion(objetivo, areas, fs)
    if a is not None:
        ax.axhline(objetivo, color=color, ls=":", lw=1)
        ax.axvline(a, color=color, ls=":", lw=1)
        ax.annotate(f"{objetivo}% ≈ {a:.0f} m²",
                    xy=(a, objetivo), xytext=(a + 80, objetivo - 5),
                    fontsize=9, color="#444")

ax.set_xlabel("Área de colectores [m²]")
ax.set_ylabel("Fracción Solar Anual [%]")
ax.set_title("Fracción Solar Anual vs. Área de colectores", fontweight="bold")
ax.grid(alpha=0.3)
ax.legend()
fig2.tight_layout()
fig2.savefig("fig_parametrico.png", dpi=150, bbox_inches="tight")
print("Guardado: fig_parametrico.png")
