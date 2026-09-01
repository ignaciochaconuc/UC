import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location

site = Location(
    latitude=-33.5,
    longitude=-70.612,
    tz='America/Santiago',
    altitude=570,
    name='Santiago'
)

def azimut_continuo(az):
    az = np.asarray(az)
    return ((az + 180) % 360) - 180   # N=0, E positivo, O negativo

def y_visual(theta, r):
    """
    Posición vertical aproximada en el gráfico polar, en fracción de ejes.
    0 = abajo, 1 = arriba
    """
    y = (r / 90.0) * np.cos(theta)   # coordenada vertical en el círculo
    return 0.5 + 0.46 * y

def repartir_etiquetas(y_objetivo, y_min=0.18, y_max=0.82, sep_min=0.032):
    """
    Reparte etiquetas verticalmente para que no se monten.
    Recibe y_objetivo ya ordenado de arriba hacia abajo.
    """
    y = np.array(y_objetivo, dtype=float)

    if len(y) == 0:
        return y

    # limitar arriba
    y[0] = min(y[0], y_max)

    # pasada hacia abajo imponiendo separación mínima
    for i in range(1, len(y)):
        y[i] = min(y[i], y[i-1] - sep_min)

    # si la última cae muy abajo, subir todas
    if y[-1] < y_min:
        y += (y_min - y[-1])

    # si la primera queda muy arriba, bajar todas
    if y[0] > y_max:
        y -= (y[0] - y_max)

    # una segunda pasada por seguridad
    y[0] = min(y[0], y_max)
    for i in range(1, len(y)):
        y[i] = min(y[i], y[i-1] - sep_min)

    return y

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})

ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_rlim(0, 90)

# Ticks radiales
rticks = np.arange(10, 91, 10)
ax.set_rticks(rticks)
ax.set_yticklabels([f"{90-r}°" for r in rticks])
ax.set_rlabel_position(180)

ax.grid(True, alpha=0.3)
ax.set_title("Diagrama de posición solar - Santiago", pad=20)

meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

# Guardaremos aquí las posiciones de etiquetas
etiquetas_derecha = []   # amanecer
etiquetas_izquierda = [] # atardecer

for m, mes in enumerate(meses, start=1):
    fecha = f"2025-{m:02d}-21"
    times = pd.date_range(
        start=f"{fecha} 00:00",
        end=f"{fecha} 23:59",
        freq="5min",
        tz=site.tz
    )

    solpos = site.get_solarposition(times)
    solpos = solpos[solpos["apparent_elevation"] > 0].copy()

    az = azimut_continuo(solpos["azimuth"].values)
    theta = np.deg2rad(az)
    r = 90 - solpos["apparent_elevation"].values

    ax.plot(theta, r, color="black", lw=1)

    if len(solpos) > 0:
        # Inicio de la trayectoria (amanecer, lado derecho)
        theta_ini, r_ini = theta[0], r[0]
        etiquetas_derecha.append({
            "mes": mes,
            "theta": theta_ini,
            "r": r_ini,
            "y": y_visual(theta_ini, r_ini)
        })

        # Fin de la trayectoria (atardecer, lado izquierdo)
        theta_fin, r_fin = theta[-1], r[-1]
        etiquetas_izquierda.append({
            "mes": mes,
            "theta": theta_fin,
            "r": r_fin,
            "y": y_visual(theta_fin, r_fin)
        })

# Ordenar de arriba hacia abajo
etiquetas_derecha = sorted(etiquetas_derecha, key=lambda d: -d["y"])
etiquetas_izquierda = sorted(etiquetas_izquierda, key=lambda d: -d["y"])

# Repartir posiciones verticales para que no se monten
y_der = repartir_etiquetas([d["y"] for d in etiquetas_derecha],
                           y_min=0.18, y_max=0.82, sep_min=0.035)
y_izq = repartir_etiquetas([d["y"] for d in etiquetas_izquierda],
                           y_min=0.18, y_max=0.82, sep_min=0.035)

# Dibujar etiquetas derechas
for d, y_txt in zip(etiquetas_derecha, y_der):
    ax.annotate(
        d["mes"],
        xy=(d["theta"], d["r"]),
        xycoords='data',
        xytext=(1.03, y_txt),
        textcoords='axes fraction',
        ha='left',
        va='center',
        fontsize=8,
        clip_on=False,
        arrowprops=dict(
            arrowstyle='-',
            lw=0.6,
            color='0.35',
            shrinkA=0,
            shrinkB=0
        )
    )

# Dibujar etiquetas izquierdas
for d, y_txt in zip(etiquetas_izquierda, y_izq):
    ax.annotate(
        d["mes"],
        xy=(d["theta"], d["r"]),
        xycoords='data',
        xytext=(-0.03, y_txt),
        textcoords='axes fraction',
        ha='right',
        va='center',
        fontsize=8,
        clip_on=False,
        arrowprops=dict(
            arrowstyle='-',
            lw=0.6,
            color='0.35',
            shrinkA=0,
            shrinkB=0
        )
    )

# Cardinales
ax.text(np.deg2rad(0),   92, "N", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(90),  92, "E", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(180), 92, "S", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(270), 92, "O", ha="center", va="center", fontsize=12, fontweight="bold")

plt.tight_layout()
plt.show()