import pandas as pd
import matplotlib.pyplot as plt
import os

RUTA_CSV = "perfil_horario_HESS_final_8h_106stacks.csv"
CARPETA_SALIDA = "graficos_HESS_final"

os.makedirs(CARPETA_SALIDA, exist_ok=True)

df = pd.read_csv(RUTA_CSV)
df["timestamp"] = pd.to_datetime(df["timestamp"])



M_H2 = 2.01588e-3   # kg/mol
df["inventario_H2_kg"] = df["n_H2_mol"] * M_H2

plt.figure(figsize=(14, 5))
plt.step(
    df["timestamp"],
    df["m_H2_prod_kg"],
    where="mid",
    label="Producción H2 [kg/h]"
)
plt.step(
    df["timestamp"],
    df["m_H2_cons_kg"],
    where="mid",
    label="Consumo H2 [kg/h]"
)
plt.xlabel("Tiempo")
plt.ylabel("Hidrógeno [kg/h]")
plt.title("Producción y consumo horario de H2")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "01_produccion_consumo_H2.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


plt.figure(figsize=(14, 5))
plt.plot(df["timestamp"], df["inventario_H2_kg"])
plt.xlabel("Tiempo")
plt.ylabel("Inventario de H2 [kg]")
plt.title("Inventario de H2 almacenado")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "02_inventario_H2.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


plt.figure(figsize=(14, 5))
plt.plot(df["timestamp"], df["soc_H2"], label="SoC H2")
plt.plot(df["timestamp"], df["soc_O2"], label="SoC O2")
plt.xlabel("Tiempo")
plt.ylabel("SoC [-]")
plt.title("Evolución del estado de carga de los tanques")
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "03_soc_tanques.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()

plt.figure(figsize=(14, 5))
plt.plot(df["timestamp"], df["p_H2_bar"], label="Presión H2 [bar]")
plt.plot(df["timestamp"], df["p_O2_bar"], label="Presión O2 [bar]")
plt.xlabel("Tiempo")
plt.ylabel("Presión [bar]")
plt.title("Evolución de la presión en los tanques")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "04_presiones_tanques.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


plt.figure(figsize=(14, 5))
plt.step(df["timestamp"], df["n_active"], where="mid")
plt.xlabel("Tiempo")
plt.ylabel("Número de stacks activos")
plt.title("Stacks activos en la operación del HESS")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "05_stacks_activos.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()

plt.figure(figsize=(14, 5))
plt.plot(df["timestamp"], df["j_A_cm2"])
plt.xlabel("Tiempo")
plt.ylabel("Densidad de corriente [A/cm²]")
plt.title("Evolución de la densidad de corriente")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "06_densidad_corriente.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()

# Parte economica

factor_anual = 365 / 61
vida_util = 20
inflacion = 0.03
tasa_descuento = 0.07

potencia_kW = 100000
capacidad_kWh = 800000

costo_tanques = 72.8 * capacidad_kWh
costo_conversion = 79.4 * capacidad_kWh
costo_desarrollo = 50 * capacidad_kWh
costo_epc = 27.52 * capacidad_kWh
costo_integracion = 16.3 * capacidad_kWh
costo_equipos_electricos = 123 * potencia_kW
costo_control = 1.06 * potencia_kW

energia_comprada_anual = df["E_comprada_MWh"].sum() * factor_anual
energia_vendida_anual = df["E_vendida_MWh"].sum() * factor_anual

costo_energia_anual = df["costo_USD"].sum() * factor_anual
ingreso_anual = df["ingreso_USD"].sum() * factor_anual

capex_total = (costo_tanques + costo_conversion + costo_desarrollo + costo_epc + costo_integracion + costo_equipos_electricos + costo_control)

opex_fijo_anual = 14.3 * potencia_kW
opex_variable_usd_kwh = 0.0005125
opex_variable_anual = ( opex_variable_usd_kwh * energia_vendida_anual * 1000)
opex_anual = opex_fijo_anual + opex_variable_anual

vpn = -capex_total
costos_descontados = capex_total
energia_descontada = 0

resultados = []

for año in range(1, vida_util + 1):

    factor_inflacion = (1 + inflacion) ** (año - 1)
    factor_descuento = (1 + tasa_descuento) ** año

    ingreso = ingreso_anual * factor_inflacion
    costo_energia = costo_energia_anual * factor_inflacion
    opex = opex_anual * factor_inflacion

    flujo = ingreso - costo_energia - opex

    vpn += flujo / factor_descuento

    costos_descontados += (
        costo_energia + opex
    ) / factor_descuento

    energia_descontada += (
        energia_vendida_anual
        / factor_descuento
    )

    resultados.append({
        "Año": año,
        "Ingreso_USD": ingreso,
        "Costo_energia_USD": costo_energia,
        "OPEX_USD": opex,
        "Flujo_neto_USD": flujo,
        "Flujo_descontado_USD": flujo / factor_descuento
    })

lcos = costos_descontados / energia_descontada
rte = energia_vendida_anual / energia_comprada_anual

print("CAPEX total:", capex_total)
print("OPEX fijo anual:", opex_fijo_anual)
print("OPEX variable anual:", opex_variable_anual)
print("Energia comprada anual:", energia_comprada_anual)
print("Energia vendida anual:", energia_vendida_anual)
print("RTE", rte * 100)
print("LCOS:", lcos)
print("VPN:", vpn)