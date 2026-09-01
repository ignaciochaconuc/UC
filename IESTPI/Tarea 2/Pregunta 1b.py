import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location

# =========================================================
# 1) Punto de observación
#    Lo estimo como el centro del patio / conjunto
#    Cámbialo si tienes la coordenada exacta del patio o panel
# =========================================================
lat_obs = -33.49997656
lon_obs = -70.61285065
alt_obs = 570  # altura del sitio sobre el nivel del mar aprox.

site = Location(
    latitude=lat_obs,
    longitude=lon_obs,
    tz='America/Santiago',
    altitude=alt_obs,
    name='Patio de Ingeniería'
)

# =========================================================
# 2) Edificios: vértices (lat, lon) y altura [m]
# =========================================================
edificios = {
    "Raúl Devés": {
        "altura": 13,
        "vertices": [
            (-33.499563, -70.613266),
            (-33.499501, -70.612449),
            (-33.499634, -70.612432),
            (-33.499743, -70.613272),
        ],
    },
    "Cai": {
        "altura": 7,
        "vertices": [
            (-33.499831, -70.613499),
            (-33.499799, -70.613042),
            (-33.500165, -70.613005),
            (-33.500202, -70.613459),
        ],
    },
    "Salas A": {
        "altura": 7,
        "vertices": [
            (-33.500241, -70.612636),
            (-33.500220, -70.612284),
            (-33.499721, -70.612340),
            (-33.499750, -70.61269444444444),  # convertido desde DMS
        ],
    },
    "Salas B": {
        "altura": 9,
        "vertices": [
            (-33.500273, -70.613344),
            (-33.500218, -70.612288),
            (-33.500344, -70.612272),
            (-33.500420, -70.613328),
        ],
    },
}

# =========================================================
# 3) Funciones auxiliares
# =========================================================
R = 6371000  # radio terrestre [m]

def azimut_continuo(az):
    """
    Convierte azimut 0-360 a rango [-180, 180]
    para evitar saltos al pasar por el norte.
    """
    az = np.asarray(az)
    return ((az + 180) % 360) - 180

def ll_to_xy(lat, lon, lat0, lon0):
    """
    Proyección local simple:
    x -> este-oeste [m]
    y -> norte-sur [m]
    """
    x = np.radians(lon - lon0) * R * np.cos(np.radians(lat0))
    y = np.radians(lat - lat0) * R
    return x, y

def edificio_a_sombra(vertices, altura, lat0, lon0):
    """
    Convierte un edificio a coordenadas polares del diagrama solar:
    theta -> azimut continuo [rad]
    r     -> 90 - elevación aparente del edificio
    """
    azs = []
    elevs = []

    for lat, lon in vertices:
        x, y = ll_to_xy(lat, lon, lat0, lon0)
        d = np.hypot(x, y)

        # Azimut geográfico:
        # 0° norte, 90° este, 180° sur, 270° oeste
        az = (np.degrees(np.arctan2(x, y)) + 360) % 360
        az = azimut_continuo(az)

        # Elevación aparente del techo del edificio
        elev = np.degrees(np.arctan2(altura, d))

        azs.append(az)
        elevs.append(elev)

    azs = np.array(azs)
    elevs = np.array(elevs)

    # ordenar por azimut para poder dibujar la silueta
    idx = np.argsort(azs)
    azs = azs[idx]
    elevs = elevs[idx]

    theta = np.deg2rad(azs)
    r = 90 - elevs

    return theta, r, azs, elevs

def y_visual(theta, r):
    """
    Estima la posición vertical visual del punto en el gráfico
    para ordenar etiquetas sin que se monten.
    """
    y = (r / 90.0) * np.cos(theta)
    return 0.5 + 0.46 * y

def repartir_etiquetas(y_objetivo, y_min=0.18, y_max=0.82, sep_min=0.035):
    """
    Reparte etiquetas verticalmente para que no se superpongan.
    """
    y = np.array(y_objetivo, dtype=float)

    if len(y) == 0:
        return y

    y[0] = min(y[0], y_max)

    for i in range(1, len(y)):
        y[i] = min(y[i], y[i - 1] - sep_min)

    if y[-1] < y_min:
        y += (y_min - y[-1])

    if y[0] > y_max:
        y -= (y[0] - y_max)

    y[0] = min(y[0], y_max)
    for i in range(1, len(y)):
        y[i] = min(y[i], y[i - 1] - sep_min)

    return y

# =========================================================
# 4) Crear figura polar
# =========================================================
fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={'projection': 'polar'})

ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_rlim(0, 90)

# Escala radial como altura solar
rticks = np.arange(10, 91, 10)
ax.set_rticks(rticks)
ax.set_yticklabels([f"{90-r}°" for r in rticks])
ax.set_rlabel_position(180)

ax.grid(True, alpha=0.3)
ax.set_title("Diagrama de posición solar con sombreado - Patio de Ingeniería", pad=20)

# =========================================================
# 5) Dibujar sombreado de edificios
# =========================================================
for nombre, info in edificios.items():
    theta, r, azs, elevs = edificio_a_sombra(
        info["vertices"], info["altura"], lat_obs, lon_obs
    )

    # Polígono cerrado entre la silueta del edificio y el horizonte
    theta_fill = np.r_[theta[0], theta, theta[-1]]
    r_fill = np.r_[90, r, 90]

    ax.fill(theta_fill, r_fill, alpha=0.25, zorder=1)
    ax.plot(theta, r, lw=1.5, zorder=2)

    # Etiqueta del edificio en el centro angular del obstáculo
    theta_unwrap = np.unwrap(theta)
    theta_c = np.mean(theta_unwrap)
    r_c = np.min(r) + 3

    ax.text(theta_c, r_c, nombre, fontsize=8, ha='center', va='center')

# =========================================================
# 6) Trayectorias solares mensuales
# =========================================================
meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

etiquetas_derecha = []
etiquetas_izquierda = []

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

    ax.plot(theta, r, color="black", lw=1.1, zorder=3)

    if len(solpos) > 0:
        theta_ini, r_ini = theta[0], r[0]
        etiquetas_derecha.append({
            "mes": mes,
            "theta": theta_ini,
            "r": r_ini,
            "y": y_visual(theta_ini, r_ini)
        })

        theta_fin, r_fin = theta[-1], r[-1]
        etiquetas_izquierda.append({
            "mes": mes,
            "theta": theta_fin,
            "r": r_fin,
            "y": y_visual(theta_fin, r_fin)
        })

# =========================================================
# 7) Etiquetas de meses ordenadas
# =========================================================
etiquetas_derecha = sorted(etiquetas_derecha, key=lambda d: -d["y"])
etiquetas_izquierda = sorted(etiquetas_izquierda, key=lambda d: -d["y"])

y_der = repartir_etiquetas([d["y"] for d in etiquetas_derecha],
                           y_min=0.18, y_max=0.82, sep_min=0.035)
y_izq = repartir_etiquetas([d["y"] for d in etiquetas_izquierda],
                           y_min=0.18, y_max=0.82, sep_min=0.035)

for d, y_txt in zip(etiquetas_derecha, y_der):
    ax.annotate(
        d["mes"],
        xy=(d["theta"], d["r"]),
        xycoords='data',
        xytext=(1.04, y_txt),
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

for d, y_txt in zip(etiquetas_izquierda, y_izq):
    ax.annotate(
        d["mes"],
        xy=(d["theta"], d["r"]),
        xycoords='data',
        xytext=(-0.04, y_txt),
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

# =========================================================
# 8) Cardinales
# =========================================================
ax.text(np.deg2rad(0),   92, "N", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(90),  92, "E", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(180), 92, "S", ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(np.deg2rad(270), 92, "O", ha="center", va="center", fontsize=12, fontweight="bold")

plt.tight_layout()
plt.show()