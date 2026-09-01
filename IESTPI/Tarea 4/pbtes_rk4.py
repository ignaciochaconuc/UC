"""
Educational PBTES Model (Packed Bed Thermal Energy Storage)
Using the Schumann 1D Two-Phase Model and RK4 Integration.

This script is self-contained. It simulates a charge phase (hot inlet)
and a discharge phase (cold inlet, same flow direction), then visualizes 
the results as a heatmap. It includes environmental heat losses.
"""

import numpy as np
import matplotlib.pyplot as plt
import time

# Attempt to import CoolProp
try:
    import CoolProp.CoolProp as CP
    USE_COOLPROP = True
    print("CoolProp found! Using accurate air properties.")
except ImportError:
    USE_COOLPROP = False
    print("Warning: CoolProp not found. Using ideal gas approximations.")

def get_air_properties(T_C):
    """
    Get Air density [kg/m3] and specific heat (Cp) [J/kgK] at 1 atm.
    T_C: Temperature in Celsius
    """
    if USE_COOLPROP:
        T_K = T_C + 273.15
        rho = CP.PropsSI('D', 'T', T_K, 'P', 101325, 'Air')
        cp = CP.PropsSI('C', 'T', T_K, 'P', 101325, 'Air')
    else:
        T_K = T_C + 273.15
        rho = 101325 / (287.058 * T_K) # Ideal gas law
        cp = 1005.0 + 0.2 * T_C        # Approximate linear relation for air Cp
    return rho, cp

def calculate_hv(rho_f, cp_f, v_interstitial, d_p, eps, mu_f=2e-5, k_f=0.03):
    """
    Calculate the volumetric heat transfer coefficient (h_v) [W/m3K]
    using the Wakao correlation.
    """
    v_superficial = v_interstitial * eps
    Re = rho_f * abs(v_superficial) * d_p / mu_f
    Pr = cp_f * mu_f / k_f
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    h_f = Nu * k_f / d_p
    a_s = 6 * (1 - eps) / d_p
    h_v = h_f * a_s
    return h_v

def pbtes_derivatives(t, y, params):
    """
    Computes the time derivatives for the fluid and solid temperatures.
    Uses a 1st order upwind spatial difference scheme.
    """
    N = params['N']
    dz = params['dz']
    v = params['v']
    T_in = params['T_in']
    T_env = params['T_env']
    
    coeff_f = params['coeff_f']
    coeff_s = params['coeff_s']
    coeff_env = params['coeff_env']
    
    T_f = y[:N]
    T_s = y[N:]
    
    dTf_dt = np.zeros(N)
    v_mag = abs(v)
    
    if v > 0:
        # Flow from z=0 to z=L
        dTf_dt[0] = v_mag * (T_in - T_f[0]) / dz + coeff_f * (T_s[0] - T_f[0])
        dTf_dt[1:] = v_mag * (T_f[:-1] - T_f[1:]) / dz + coeff_f * (T_s[1:] - T_f[1:])
    elif v < 0:
        # Flow from z=L to z=0
        dTf_dt[-1] = v_mag * (T_in - T_f[-1]) / dz + coeff_f * (T_s[-1] - T_f[-1])
        dTf_dt[:-1] = v_mag * (T_f[1:] - T_f[:-1]) / dz + coeff_f * (T_s[:-1] - T_f[:-1])
    else:
        dTf_dt = coeff_f * (T_s - T_f)
        
    # Add heat loss to the environment (applied to fluid equation)
    dTf_dt += coeff_env * (T_env - T_f)
        
    dTs_dt = coeff_s * (T_f - T_s)
    
    return np.concatenate((dTf_dt, dTs_dt))

def rk4_step(f, t, y, dt, params):
    """Standard 4th-Order Runge-Kutta Integrator."""
    k1 = f(t, y, params)
    k2 = f(t + dt/2, y + dt/2 * k1, params)
    k3 = f(t + dt/2, y + dt/2 * k2, params)
    k4 = f(t + dt, y + dt * k3, params)
    return y + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)

def run_phase(y0, t_start, phase_name, v_interstitial, T_in, t_total, params):
    print(f"\n--- Starting {phase_name} Phase ---")
    rho_f, cp_f = get_air_properties(T_in)
    hv = calculate_hv(rho_f, cp_f, v_interstitial, params['d_p'], params['eps'])
    
    coeff_f = hv / (params['eps'] * rho_f * cp_f)
    coeff_s = hv / ((1 - params['eps']) * params['rho_s'] * params['cp_s'])
    
    # Heat loss coefficient
    # a_wall = 4 / D_tank. h_vol_loss = U_loss * a_wall
    h_vol_loss = params['U_loss'] * (4.0 / params['D_tank'])
    coeff_env = h_vol_loss / (params['eps'] * rho_f * cp_f)
    
    params['v'] = v_interstitial
    params['T_in'] = T_in
    params['coeff_f'] = coeff_f
    params['coeff_s'] = coeff_s
    params['coeff_env'] = coeff_env
    
    dt_cfl = params['dz'] / abs(v_interstitial) if v_interstitial != 0 else 1e6
    dt_ht = 1.0 / coeff_f
    dt = min(dt_cfl * 0.5, dt_ht * 0.5)
    
    t_steps = int(t_total / dt)
    dt = t_total / t_steps 
    
    print(f"Calculated stable dt: {dt:.3f} s")
    print(f"Total steps to simulate: {t_steps}")
    
    # Save about 100 points per phase for a smooth heatmap
    save_interval = max(1, t_steps // 100)
    history_Tf, history_Ts, history_t = [], [], []
    
    y = y0.copy()
    t = t_start
    N = params['N']
    
    start_time = time.time()
    
    for step in range(t_steps):
        if step % save_interval == 0:
            history_Tf.append(y[:N].copy())
            history_Ts.append(y[N:].copy())
            history_t.append(t)
            
        y = rk4_step(pbtes_derivatives, t, y, dt, params)
        t += dt
        
    history_Tf.append(y[:N].copy())
    history_Ts.append(y[N:].copy())
    history_t.append(t)
    
    print(f"Phase completed in {time.time() - start_time:.2f} seconds.")
    
    return y, t, np.array(history_Tf), np.array(history_Ts), np.array(history_t)

def plot_heatmap(z, t_array, Ts_matrix, T_charge, t_charge_end):
    """
    Plots a heatmap of the Solid Temperature over Time and space.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Convert time to hours
    T_hours = t_array / 3600.0
    Z_mesh, T_mesh = np.meshgrid(z, T_hours)
    
    # Plot heatmap
    c = ax.pcolormesh(T_mesh, Z_mesh, Ts_matrix, cmap='inferno', shading='auto', 
                      vmin=Ts_matrix.min(), vmax=T_charge)
    
    # Add a vertical line to denote switch from charge to discharge
    ax.axvline(x=t_charge_end / 3600.0, color='white', linestyle='--', linewidth=2, label='Phase Switch')
    
    cbar = fig.colorbar(c, ax=ax)
    cbar.set_label('Solid Temperature [°C]')
    
    ax.set_title('PBTES Solid Temperature Evolution (Charge & Discharge)')
    ax.set_xlabel('Time [hours]')
    ax.set_ylabel('Axial Position z [m]')
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig('pbtes_heatmap.png', dpi=300)
    print("\nHeatmap saved as 'pbtes_heatmap.png'")
    plt.show()

if __name__ == "__main__":
    # ---------------------------------------------------------
    # 1. System Parameters setup
    # ---------------------------------------------------------
    L = 5.0                # Tank length [m]
    N_nodes = 50           # Number of spatial nodes
    
    params = {
        'N': N_nodes,
        'dz': L / N_nodes,
        'eps': 0.4,        # Bed porosity [-]
        'd_p': 0.05,       # Particle diameter [m]
        'rho_s': 2500,     # Solid density [kg/m3] (e.g., basalt rock)
        'cp_s': 850,       # Solid specific heat [J/kgK]
        'D_tank': 2.0,     # Tank diameter [m]
        'U_loss': 1.5,     # Overall heat loss coefficient [W/m2K]
        'T_env': 20.0      # Ambient Environment temperature [°C]
    }
    
    z_grid = np.linspace(params['dz']/2, L - params['dz']/2, N_nodes)
    
    # ---------------------------------------------------------
    # 2. Operating Conditions
    # ---------------------------------------------------------
    v_superficial = 0.50                 # Superficial velocity [m/s] (10x faster)
    v_interstitial = v_superficial / params['eps']
    
    T_ambient = 20.0                     # Ambient / Initial / Discharge Inlet temp
    T_charge = 300.0                     # Hot air for charging
    
    duration_charge = 4.0 * 3600         # 4 hours of charging
    duration_discharge = 4.0 * 3600      # 4 hours of discharging
    
    # ---------------------------------------------------------
    # 3. Execution
    # ---------------------------------------------------------
    # Initial state vector: all at ambient temperature
    y_init = np.full(2 * N_nodes, T_ambient)
    
    # Charge Phase
    y_end_charge, t_mid, hist_Tf_c, hist_Ts_c, hist_t_c = run_phase(
        y0=y_init, 
        t_start=0.0,
        phase_name="Charge",
        v_interstitial=v_interstitial, 
        T_in=T_charge,
        t_total=duration_charge,
        params=params
    )
    
    # Discharge Phase (Same flow direction, ambient inlet)
    y_end_discharge, t_end, hist_Tf_d, hist_Ts_d, hist_t_d = run_phase(
        y0=y_end_charge, 
        t_start=t_mid,
        phase_name="Discharge",
        v_interstitial=v_interstitial, 
        T_in=T_ambient,
        t_total=duration_discharge,
        params=params
    )
    
    # Concatenate results
    t_all = np.concatenate((hist_t_c, hist_t_d))
    Ts_all = np.vstack((hist_Ts_c, hist_Ts_d))
    
    # Plot Heatmap
    plot_heatmap(z_grid, t_all, Ts_all, T_charge, duration_charge)
