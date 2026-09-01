from CoolProp.CoolProp import PropsSI
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("DHC_E_MIQ4AY.csv", skiprows=41, sep=",")
df.columns = df.columns.str.strip()
df["Fecha/Hora"] = pd.to_datetime(df["Fecha/Hora"])

df = df[["Fecha/Hora", "ghi", "temp"]]

df_invierno = df[
    (df["Fecha/Hora"] >= "2016-6-01 00:00:00") &
    (df["Fecha/Hora"] <  "2016-09-01 00:00:00")
].copy()


df_invierno = df_invierno.sort_values("Fecha/Hora").reset_index(drop=True)


T_final = 45 + 273.15          # K
P = 101325                     # Pa
rho = PropsSI('D', 'T', T_final, 'P', P, 'Water')   # kg/m3
cp  = PropsSI('C', 'T', T_final, 'P', P, 'Water')   # J/kgK

T_red = 12 + 273.15            # K
V_tank = 405 * 10**-3          # m3
m = V_tank * rho               # kg

E_max = m * cp * (T_final - T_red)   # J
E_i = 0                            # partir vacío

A = 8                        # m2
eta = 0.5
h_convec = 3                  # W/m2K
A_e = (120*45 + 45*75*2 + 120*75) / 10**4   # m2, una cara apoyada


resultados = []


for i in range(len(df_invierno)):

    fecha_hora = df_invierno.iloc[i]["Fecha/Hora"]
    rad = df_invierno.iloc[i]["ghi"]                      # W/m2
    T_ambiente = df_invierno.iloc[i]["temp"] + 273.15    # K

    # Temperatura equivalente del estanque al inicio de la hora
    T_actual = T_red + E_i / (m * cp)

    # Pérdidas de la hora
    Q_p = h_convec * A_e * (T_actual - T_ambiente) * 3600   # J
    Q_p = max(Q_p, 0)

    # Energía disponible luego de pérdidas
    E_post_perdidas = max(0, E_i - Q_p)

    # Hora del día
    hora_dia = fecha_hora.hour

    # Demanda horaria (solo 8:00 y 20:00)
    if hora_dia == 8 or hora_dia == 20:
        m_punto = 5 * 10**-3 * rho   # kg/min  (5 L/min)
        delta_T = T_final - T_red
        t = 20                       # min
        Q_d = m_punto * cp * delta_T * t
    else:
        Q_d = 0

    # Parte de la demanda cubierta por el estanque solar
    Q_solar_demanda = min(E_post_perdidas, Q_d)

    # Parte cubierta por auxiliar
    Q_aux = Q_d - Q_solar_demanda

    # Energía remanente tras atender demanda
    E_post_demanda = E_post_perdidas - Q_solar_demanda

    # Captación solar de la hora
    Q_s_pot = rad * A * eta * 3600   # J

    # Nueva energía en el estanque tras captar
    E_post_captacion = min(E_post_demanda + Q_s_pot, E_max)

    # Solar útil realmente almacenado
    Q_s_util = E_post_captacion - E_post_demanda

    # Solar desperdiciado por saturación
    Q_s_desperdiciada = max(0, Q_s_pot - Q_s_util)

    # Actualizar estado del estanque
    E_i = E_post_captacion


    resultados.append({
        "Fecha/Hora": fecha_hora,
        "fecha": fecha_hora.date(),
        "hora_dia": hora_dia,
        "ghi": rad,
        "T_amb_C": T_ambiente - 273.15,
        "T_actual_C": T_actual - 273.15,
        "Q_p_J": Q_p,
        "Q_d_J": Q_d,
        "Q_s_pot_J": Q_s_pot,
        "Q_s_util_J": Q_s_util,
        "Q_s_desperdiciada_J": Q_s_desperdiciada,
        "Q_solar_demanda_J": Q_solar_demanda,
        "Q_aux_J": Q_aux,
        "E_J": E_i
    })

df_resultados = pd.DataFrame(resultados)


df_resultados["Q_s_util_kWh"] = df_resultados["Q_s_util_J"] / 3.6e6
df_resultados["Q_d_kWh"] = df_resultados["Q_d_J"] / 3.6e6
df_resultados["Q_aux_kWh"] = df_resultados["Q_aux_J"] / 3.6e6
df_resultados["Q_solar_demanda_kWh"] = df_resultados["Q_solar_demanda_J"] / 3.6e6
df_resultados["Q_s_desperdiciada_kWh"] = df_resultados["Q_s_desperdiciada_J"] / 3.6e6
df_resultados["Q_p_kWh"] = df_resultados["Q_p_J"] / 3.6e6
df_resultados["E_kWh"] = df_resultados["E_J"] / 3.6e6
df_resultados["Q_s_pot_kWh"] = df_resultados["Q_s_pot_J"] / 3.6e6


df_ultimo_dia = df_resultados[df_resultados["fecha"] == df_resultados["fecha"].max()].copy().reset_index(drop=True)

Q_demanda_dia = df_ultimo_dia["Q_d_J"].sum()
Q_solar_demanda_dia = df_ultimo_dia["Q_solar_demanda_J"].sum()
Q_aux_dia = df_ultimo_dia["Q_aux_J"].sum()
Q_s_util_dia = df_ultimo_dia["Q_s_util_J"].sum()
Q_s_desperdiciada_dia = df_ultimo_dia["Q_s_desperdiciada_J"].sum()

fraccion_solar_dia = Q_solar_demanda_dia / Q_demanda_dia if Q_demanda_dia > 0 else 0

print(f"Demanda total último día: {Q_demanda_dia/3.6e6:.2f} kWh")
print(f"Cubierta por solar último día: {Q_solar_demanda_dia/3.6e6:.2f} kWh")
print(f"Cubierta por auxiliar último día: {Q_aux_dia/3.6e6:.2f} kWh")
print(f"Solar útil almacenado último día: {Q_s_util_dia/3.6e6:.2f} kWh")
print(f"Solar desperdiciado último día: {Q_s_desperdiciada_dia/3.6e6:.2f} kWh")
print(f"Fracción solar último día: {fraccion_solar_dia:.2%}")

print(df_ultimo_dia)

plt.figure(figsize=(10,5))
plt.plot(df_ultimo_dia["hora_dia"], df_ultimo_dia["Q_s_pot_kWh"], marker="o", label="Captación solar potencial")
plt.plot(df_ultimo_dia["hora_dia"], df_ultimo_dia["Q_d_kWh"], marker="o", label="Demanda ACS")
plt.xlabel("Hora del día")
plt.ylabel("Energía [kWh/h]")
plt.title("Desfase entre captación solar y demanda - último día")
plt.xticks(range(24))
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

plt.figure(figsize=(10,5))
plt.plot(df_ultimo_dia["hora_dia"], df_ultimo_dia["T_actual_C"], marker="o", label="Temperatura equivalente del estanque")
plt.axhline(45, linestyle="--", label="Temperatura de uso")
plt.bar(df_ultimo_dia["hora_dia"], df_ultimo_dia["Q_aux_kWh"], alpha=0.4, label="Apoyo auxiliar [kWh]")
plt.xlabel("Hora del día")
plt.ylabel("Temperatura [°C] / Energía auxiliar [kWh]")
plt.title("Estado del estanque y uso de respaldo - último día")
plt.xticks(range(24))
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()