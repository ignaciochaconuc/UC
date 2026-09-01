import pandas as pd
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.HumidAirProp import HAPropsSI

df = pd.read_excel(r"C:\UC\Termofluidos\Tarea 1\Datos meteorológicos Febrero 2026 Pudahuel.xlsx")

df["time"] = pd.to_datetime(df["time"])

T_red = 15                  # °C
V_punto_aire = 8100 * 1.699 / 3600 # m3/s
V_punto_red = 1.5 / 60      # L/s

datos = []

def estado_posible(P, w, h):
    P_v = P * w / (0.621945 + w)

    if P_v >= P:
        return False, np.nan, np.nan

    T_sat = CP.PropsSI('T', 'P', P_v, 'Q', 1, 'Water')  # K
    h_sat = HAPropsSI('H', 'T', T_sat, 'P', P, 'R', 1)

    return h >= h_sat, T_sat, h_sat

def evaporacion_completa(T_metro, T_red, m_punto_aire, P, h_1, w_1, phi_1, h_agua_entrada, m_punto_red):
    tol = 1e-6

    if phi_1 >= 1 - tol:
        w_2 = w_1
        h_2 = h_1
        T_2 = T_metro
        phi_2 = 1
        m_agua_restante = m_punto_red
        estado = "Aire saturado, no evapora agua"
        return [w_2, h_2, T_2, phi_2, m_agua_restante, estado]

    seguir = True
    caudal_saturacion = m_punto_red
    m_agua_restante = 0
    w_2 = np.nan
    h_2 = np.nan
    T_2 = np.nan
    phi_2 = np.nan
    estado = "No calculado"

    while seguir:
        w_2_ten = (m_punto_aire * w_1 + caudal_saturacion) / m_punto_aire
        h_2_ten = (m_punto_aire * h_1 + caudal_saturacion * h_agua_entrada) / m_punto_aire

        posible, _, _ = estado_posible(P, w_2_ten, h_2_ten)

        if posible:
            T_2_ten = HAPropsSI('T', 'P', P, 'W', w_2_ten, 'H', h_2_ten) - 273.15
            w_2_sat = HAPropsSI('W', 'T', T_2_ten + 273.15, 'P', P, 'R', 1)

            if w_2_ten <= w_2_sat:
                w_2 = w_2_ten
                h_2 = h_2_ten
                T_2 = T_2_ten
                phi_2 = HAPropsSI('R', 'T', T_2 + 273.15, 'P', P, 'W', w_2)

                if abs(caudal_saturacion - m_punto_red) < 1e-12:
                    estado = "Completamente evaporado"
                else:
                    m_agua_restante = m_punto_red - caudal_saturacion
                    estado = "Sobra agua"

                    # Tope físico: si sobra agua, T2 no puede quedar bajo T_red
                    if T_2 < T_red:
                        T_2 = T_red
                        phi_2 = 1
                        w_2 = HAPropsSI('W', 'T', T_2 + 273.15, 'P', P, 'R', 1)
                        h_2 = HAPropsSI('H', 'T', T_2 + 273.15, 'P', P, 'R', 1)

                        m_agua_evaporada = m_punto_aire * (w_2 - w_1)
                        m_agua_restante = m_punto_red - m_agua_evaporada

                seguir = False
            else:
                caudal_saturacion -= m_punto_red * 0.001

        else:
            if caudal_saturacion <= 0:
                w_2 = w_1
                h_2 = h_1
                T_2 = T_metro
                phi_2 = phi_1
                m_agua_restante = m_punto_red
                estado = "No evapora agua"
                seguir = False
            else:
                caudal_saturacion -= m_punto_red * 0.001

    return [w_2, h_2, T_2, phi_2, m_agua_restante, estado]

for i in range(len(df)):
    time = df.loc[i, "time"]
    fecha = time.date()
    hora = time.hour

    temp = df.loc[i, "temp"]
    phi_1 = df.loc[i, "rhum"] / 100
    P = df.loc[i, "pres"] * 100
    T_metro = 5 + temp

    densidad_agua = CP.PropsSI('D', 'T', T_red + 273.15, 'P', P, 'Water')
    m_punto_red = V_punto_red * densidad_agua / 1000

    v_1 = HAPropsSI('V', 'T', T_metro + 273.15, 'P', P, 'R', phi_1)
    m_punto_aire = V_punto_aire / v_1
    h_1 = HAPropsSI('H', 'T', T_metro + 273.15, 'P', P, 'R', phi_1)
    w_1 = HAPropsSI('W', 'T', T_metro + 273.15, 'P', P, 'R', phi_1)

    h_agua_entrada = CP.PropsSI('H', 'P', P, 'T', T_red + 273.15, 'Water')

    w_2, h_2, T_2, phi_2, m_agua_restante, estado = evaporacion_completa(
    T_metro=T_metro,
    T_red=T_red,
    m_punto_aire=m_punto_aire,
    P=P,
    h_1=h_1,
    w_1=w_1,
    phi_1=phi_1,
    h_agua_entrada=h_agua_entrada,
    m_punto_red=m_punto_red
)

    datos.append([
        time, fecha, hora,
        temp, T_metro, P, phi_1,
        m_punto_aire, m_punto_red,
        h_1, w_1,
        h_agua_entrada,
        w_2, h_2, T_2, phi_2,
        m_agua_restante, estado
    ])

df_final = pd.DataFrame(datos, columns=[
    "time", "fecha", "hora",
    "temp_ambiente", "T_metro", "P", "phi_1",
    "m_punto_aire", "m_punto_red",
    "h_1", "w_1",
    "h_agua_entrada",
    "w_2", "h_2", "T_2", "phi_2",
    "m_agua_restante", "estado",
])

print(df_final.head())

df_final.to_excel(r"C:\UC\Termofluidos\Tarea 1\df_final_v2.xlsx", index=False)