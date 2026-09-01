"""Ejecuta el caso base usando la función común de simulación."""

from pathlib import Path
import pandas as pd

from simulacion_hess import cargar_perfil, simular_caso

BASE_DIR = Path(__file__).resolve().parent
PERFIL = BASE_DIR / "perfil_despacho_completo_preliminar (3).csv"


def main() -> None:
    df = cargar_perfil(PERFIL)
    resumen, horario = simular_caso(
        df_perfil=df,
        storage_hours=18,
        n_pemfc=150,
        n_pemel=100,
        p_stack_pemfc_MW=0.70,
        soc0=0.50,
        retornar_horario=True,
    )

    pd.DataFrame([resumen]).to_csv(
        BASE_DIR / "resumen_HESS_caso_base_reorganizado.csv",
        index=False,
    )
    if horario is not None:
        horario.to_csv(
            BASE_DIR / "perfil_horario_HESS_caso_base_reorganizado.csv",
            index=False,
        )

    print(pd.Series(resumen).to_string())


if __name__ == "__main__":
    main()
