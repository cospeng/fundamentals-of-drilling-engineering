"""drilleng -- SI-first helpers for drilling engineering calculations.

Every function here takes and returns SI units (Pa, m, kg/m3, N) unless its
name says otherwise. Field units (ppg, psi, lbf, ft, gal) appear only in the
conversion helpers at the top, so that textbook examples can be reproduced
without letting mixed-unit magic numbers leak into the physics.

The physics are derived in the notebooks; this module only holds the
implementations that passed the self-test at the bottom.

    uv run drilleng.py
"""

from __future__ import annotations

import math

# Standard gravity. In field units this same constant is expressed as
# 1.0 lbf/lbm, which is where the familiar 0.05195 comes from -- see
# 01-drilling-systems.md for the derivation.
G = 9.80665  # m/s2

# ---------------------------------------------------------------------------
# Field unit -> SI conversions
# ---------------------------------------------------------------------------

LB_PER_GAL = 0.45359237 / 0.003785411784  # kg/m3 per ppg
PSI = 6894.757293168361  # Pa per psi
LBF = 4.4482216152605  # N per lbf
FOOT = 0.3048  # m per ft
GAL = 0.003785411784  # m3 per gal


def ppg_to_kgm3(x):
    return x * LB_PER_GAL


def kgm3_to_ppg(x):
    return x / LB_PER_GAL


def psi_to_pa(x):
    return x * PSI


def pa_to_psi(x):
    return x / PSI


def lbf_to_n(x):
    return x * LBF


def ft_to_m(x):
    return x * FOOT


def gal_to_m3(x):
    return x * GAL


def field_hydrostatic_coefficient():
    """The textbook '0.05195' psi/(ppg*ft) coefficient, derived from units only.

    p = rho*g*z with g written as 1.0 lbf/lbm. Converting rho in lbm/gal and z
    in ft to lbf/in2 needs 12 in/ft divided by 231 in3/gal -- and nothing else.
    """
    return 12.0 / 231.0


def mpa_per_gcc_m():
    """The '0.00981' MPa/(g/cc * m) coefficient, derived from units only."""
    return 1.0e3 * G * 1.0 / 1.0e6  # 1000 kg/m3 * g * 1 m -> Pa -> MPa


# ---------------------------------------------------------------------------
# Pressure
# ---------------------------------------------------------------------------


def hydrostatic_pressure(rho_kgm3, tvd_m):
    """p = rho*g*z for a single fluid column."""
    return rho_kgm3 * G * tvd_m


def overburden_pressure(tvd_m, rho_kgm3):
    """Vertical (overburden) stress by trapezoidal integration of a density log.

    tvd_m : increasing depths [m]
    rho_kgm3 : bulk density, scalar or one value per depth [kg/m3]
    returns: total vertical stress [Pa] at each depth, zero at the surface
    """
    z = [float(v) for v in tvd_m]
    rho = _as_profile(rho_kgm3, len(z))
    out = [0.0] * len(z)
    for i in range(1, len(z)):
        out[i] = out[i - 1] + 0.5 * (rho[i] + rho[i - 1]) * G * (z[i] - z[i - 1])
    return out


def pore_pressure_from_coeff(coeff, tvd_m, rho_ref_kgm3=1000.0):
    """p_p = coeff * rho_ref * g * z.

    `coeff` is the pore pressure coefficient of the formation (1.0 = normal
    fresh-water gradient). `rho_ref` is the reference fluid density; the usual
    drilling convention uses fresh water (1000 kg/m3) so that coeff reads
    directly as an equivalent density in g/cc.
    """
    return coeff * rho_ref_kgm3 * G * tvd_m


def equivalent_density(pressure_pa, tvd_m, unit="gcc"):
    """Convert an absolute pressure to an equivalent circulating density.

    unit='gcc' -> g/cm3, unit='kgm3' -> kg/m3.
    """
    if tvd_m <= 0:
        raise ValueError("equivalent density is undefined at surface (tvd <= 0)")
    rho = pressure_pa / (G * tvd_m)
    return rho / 1000.0 if unit == "gcc" else rho


# ---------------------------------------------------------------------------
# Geomechanics / wellbore stability (vertical well)
# ---------------------------------------------------------------------------


def min_horizontal_stress(sv_pa, pp_pa, poisson, biot=1.0):
    """Uniaxial-strain (Eaton) estimate of the least horizontal stress.

    sigma_h = nu/(1-nu) * (sigma_v - alpha*p_p) + alpha*p_p
    """
    return poisson / (1.0 - poisson) * (sv_pa - biot * pp_pa) + biot * pp_pa


def fracture_pressure(sv_pa, pp_pa, poisson, biot=1.0, tensile_pa=0.0):
    """Fracture initiation pressure of a vertical well.

    Kirsch gives sigma_theta = 3*sigma_h - sigma_H - p_w at the wall; tensile
    failure starts when the effective hoop stress reaches -T. Taking the
    isotropic horizontal stress case (sigma_H = sigma_h) this reduces to
    p_f = sigma_h + T.
    """
    return min_horizontal_stress(sv_pa, pp_pa, poisson, biot) + tensile_pa


def kirsch_hoop_stress(sh_max_pa, sh_min_pa, pw_pa, theta_deg=90.0):
    """Total hoop stress at the borehole wall, theta measured from sigma_H axis.

    sigma_theta = sh_max + sh_min - 2*(sh_max - sh_min)*cos(2*theta) - pw
    theta = 90 deg gives the minimum (breakout-prone) hoop stress:
    sigma_theta = 3*sh_min - sh_max - pw.
    """
    t = math.radians(theta_deg)
    return sh_max_pa + sh_min_pa - 2.0 * (sh_max_pa - sh_min_pa) * math.cos(2.0 * t) - pw_pa


def mohr_coulomb_collapse(sh_max_pa, sh_min_pa, pp_pa, c_pa, phi_deg, biot=1.0):
    """Mud pressure that keeps the wall out of Mohr-Coulomb shear failure.

    Effective stresses at the breakout azimuth (theta = 90 deg from sigma_H):

        sigma_r' = p_w - alpha*p_p
        sigma_t' = 3*sh_max - sh_min - p_w - alpha*p_p

    Setting sigma_t' = sigma_c + N*sigma_r' with N = tan^2(45 + phi/2) and
    sigma_c = 2c*tan(45 + phi/2), and solving for p_w:

        p_c = [3*sh_max - sh_min - sigma_c + alpha*p_p*(N-1)] / (1 + N)

    The result can fall below the pore pressure; that simply means shear
    failure does not control the lower bound of the mud window there and the
    pore pressure does. Do not clamp it -- report it.
    """
    n = math.tan(math.radians(45.0 + phi_deg / 2.0)) ** 2
    sigma_c = 2.0 * c_pa * math.sqrt(n)
    return (3.0 * sh_max_pa - sh_min_pa - sigma_c + biot * pp_pa * (n - 1.0)) / (1.0 + n)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _as_profile(value, length):
    if hasattr(value, "__len__"):
        v = [float(x) for x in value]
        if len(v) != length:
            raise ValueError("density profile length does not match depth grid")
        return v
    return [float(value)] * length


# ---------------------------------------------------------------------------
# self-test: anchored on units and on the closed-form values above
# ---------------------------------------------------------------------------


def _self_test():
    # 1. hydrostatic pressure in SI
    p = hydrostatic_pressure(1000.0, 1000.0)
    assert abs(p - 9.80665e6) < 1.0, p

    # 2. the textbook 0.05195 must fall out of pure unit conversion
    p_si = hydrostatic_pressure(ppg_to_kgm3(10.0), ft_to_m(10000.0))
    p_psi = pa_to_psi(p_si)
    p_book = field_hydrostatic_coefficient() * 10.0 * 10000.0
    assert abs(p_psi - p_book) / p_book < 1e-4, (p_psi, p_book)

    # 3. 0.00981 MPa/(g/cc*m) coefficient
    assert abs(mpa_per_gcc_m() - 0.00980665) < 1e-9

    # 4. least horizontal stress from the uniaxial-strain relation
    sh = min_horizontal_stress(100e6, 45e6, poisson=0.25)
    assert abs(sh - 63.333333e6) < 1e3, sh

    # 5. Mohr-Coulomb collapse, isotropic stress, c=20 MPa, phi=30 deg
    pc = mohr_coulomb_collapse(sh, sh, 45e6, c_pa=20e6, phi_deg=30.0)
    assert abs(pc - 36.847e6) < 1e4, pc

    # 6. equivalent density round-trip
    assert abs(equivalent_density(hydrostatic_pressure(1000.0, 1000.0), 1000.0) - 1.0) < 1e-12

    # 7. pore pressure from coefficient
    assert abs(pore_pressure_from_coeff(1.30, 2000.0) - 1.30 * 1000.0 * G * 2000.0) < 1.0

    # 8. trapezoid with constant density must match the closed form
    z = [0.0, 1000.0, 2000.0]
    po = overburden_pressure(z, 2650.0)
    assert abs(po[-1] - 2650.0 * G * 2000.0) < 1.0, po

    print("drilleng self-test: 8/8 passed")


if __name__ == "__main__":
    _self_test()
