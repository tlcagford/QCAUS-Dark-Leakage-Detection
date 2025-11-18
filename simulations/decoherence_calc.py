"""
simulations_decoherence_calc.py

Runnable toy-model script for sensitivity sweeps.
"""
from math import pi
import numpy as np
from scipy.linalg import expm
import matplotlib.pyplot as plt
import argparse

# Physical constants (SI)
eV_to_J = 1.602176634e-19
hbar_si = 1.054571817e-34
c = 3e8

def decoherence_rate_from_params(g, m_ev, Q, eta, background_noise):
    """
    Phenomenological mapping to an effective decoherence rate (1/s).
    This function is intentionally transparent so you can replace it with a more realistic model.
    Inputs:
      - g : effective coupling proxy (unitless, >0)
      - m_ev : dark particle mass in eV
      - Q : cavity quality factor (dimensionless)
      - eta : detector efficiency (0..1)
      - background_noise : noise spectral proxy (>=0)
    Output:
      - gamma: decoherence rate in 1/s
    """
    omega_d = (m_ev * eV_to_J) / hbar_si  # rad/s
    gamma0 = 1e3
    gamma = gamma0 * (omega_d / (1 + Q)) * (1.0 / (1 + g)) * (1.0 / max(1e-6, eta)) * (1 + background_noise)
    return gamma

def sweep_and_plot():
    g_vals = np.logspace(-6, 2, 25)
    m_vals = [1e-22, 1e-20, 1e-18]
    Q = 1e4
    eta = 0.2
    background_noise = 1.0

    plt.figure()
    for m in m_vals:
        gammas = [decoherence_rate_from_params(g, m, Q, eta, background_noise) for g in g_vals]
        plt.loglog(g_vals, gammas, label=f"m={m:.0e} eV")
    plt.xlabel('effective coupling proxy g (unitless)')
    plt.ylabel('effective decoherence rate gamma (1/s)')
    plt.title('Toy decoherence rate vs coupling (varying mass)')
    plt.grid(True, which='both', ls=':')
    plt.legend()
    plt.tight_layout()
    plt.show()

    distances = np.linspace(1e2, 1e7, 50)
    g_choice = 1e-2
    m_choice = 1e-22
    gamma = decoherence_rate_from_params(g_choice, m_choice, Q, eta, background_noise)
    t_prop = distances / c
    P = 1.0 - np.exp(-gamma * t_prop)
    plt.figure()
    plt.loglog(distances, P)
    plt.xlabel('distance (m)')
    plt.ylabel('decoherence probability P')
    plt.title('Toy decoherence probability vs distance')
    plt.grid(True, which='both', ls=':')
    plt.tight_layout()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Toy decoherence simulator for photon<->dark mixing')
    parser.add_argument('--plot', action='store_true', help='run example plots')
    args = parser.parse_args()
    if args.plot:
        sweep_and_plot()

if __name__ == '__main__':
    main()
