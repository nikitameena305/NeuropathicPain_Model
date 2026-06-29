from neuron import h
import math
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# =========================
# USER SETTINGS
# =========================

SWC_FILE = "L796-ALT-PN.CNG.swc"

# Experimental target from Luz et al. 2014 projection neuron population.
TARGET_RMP_MV = -72.8
TARGET_RIN_GOHM = 0.77

# Current-clamp protocol from paper:
# RIN measured using 500 ms hyperpolarizing pulse of -10 pA to -20 pA.
STIM_AMP_NA = -0.01      # -10 pA
STIM_DELAY_MS = 100.0
STIM_DUR_MS = 500.0
TSTOP_MS = 800.0
DT_MS = 0.025            # small stable time step

# Passive starting parameters
CM_UF_CM2 = 1.0
RA_OHM_CM = 200.0        # start with 200; later you can test 150–250 sensitivity
E_PAS_MV = TARGET_RMP_MV

# Search range for g_pas in S/cm2
GPAS_LOW = 1e-8
GPAS_HIGH = 1e-4

# Acceptable closeness
TOL_RIN_GOHM = 0.005     # 0.005 GOhm = 5 MOhm


# =========================
# MORPHOLOGY IMPORT
# =========================

def import_swc_to_neuron(swc_file):
    """
    Import SWC morphology into NEURON using Import3D.
    This creates NEURON sections from the SWC file.
    """
    h.load_file("stdlib.hoc")
    h.load_file("stdrun.hoc")
    h.load_file("import3d.hoc")

    cell = h.Import3d_SWC_read()
    cell.input(swc_file)

    imprt = h.Import3d_GUI(cell, 0)
    imprt.instantiate(None)

    sections = list(h.allsec())
    if len(sections) == 0:
        raise RuntimeError("No sections were created from SWC.")

    return sections


def find_soma_section():
    """
    Find soma section. NEURON section names after Import3D usually include 'soma'.
    If not found, choose first section.
    """
    allsecs = list(h.allsec())
    soma_candidates = [sec for sec in allsecs if "soma" in sec.name().lower()]

    if soma_candidates:
        return soma_candidates[0]

    print("[WARNING] No section named soma found. Using first section as soma.")
    return allsecs[0]


def get_section_groups():
    """
    Group sections by name/type for reporting.
    Import3D names often include soma, axon, dend, apic.
    """
    groups = {
        "soma": [],
        "axon": [],
        "dend": [],
        "apic": [],
        "other": [],
    }

    for sec in h.allsec():
        name = sec.name().lower()
        if "soma" in name:
            groups["soma"].append(sec)
        elif "axon" in name:
            groups["axon"].append(sec)
        elif "apic" in name:
            groups["apic"].append(sec)
        elif "dend" in name:
            groups["dend"].append(sec)
        else:
            groups["other"].append(sec)

    return groups


# =========================
# GEOMETRY AND PASSIVE SETUP
# =========================

def fix_tiny_diameters(min_diam_um=0.2):
    """
    Optional but useful: very tiny diameters can cause numerical/cable issues.
    Previous Luz modelling used minimum 0.2 um due to light microscopy resolution.
    """
    changed = 0
    for sec in h.allsec():
        for seg in sec:
            if seg.diam < min_diam_um:
                seg.diam = min_diam_um
                changed += 1
    return changed


def set_nseg_dlambda(freq=100, d_lambda=0.1):
    """
    d_lambda spatial discretization.
    This gives enough segments for cable accuracy.
    """
    for sec in h.allsec():
        sec.nseg = int((sec.L / (d_lambda * h.lambda_f(freq, sec=sec)) + 0.9) / 2) * 2 + 1
        if sec.nseg < 1:
            sec.nseg = 1


def insert_passive(g_pas):
    """
    Insert passive membrane everywhere.
    """
    for sec in h.allsec():
        sec.Ra = RA_OHM_CM
        sec.cm = CM_UF_CM2
        sec.insert("pas")
        for seg in sec:
            seg.pas.g = g_pas
            seg.pas.e = E_PAS_MV


def total_area_um2():
    """
    NEURON area after morphology import and segmentation.
    h.area(x, sec=sec) returns um2.
    """
    area = 0.0
    by_group = {k: 0.0 for k in ["soma", "axon", "dend", "apic", "other"]}
    groups = get_section_groups()

    for group_name, secs in groups.items():
        for sec in secs:
            for seg in sec:
                a = h.area(seg.x, sec=sec)
                area += a
                by_group[group_name] += a

    return area, by_group


# =========================
# SIMULATION
# =========================

def run_passive_sim(g_pas, save_trace=False, trace_prefix="trace"):
    """
    Run passive current-clamp simulation and calculate Rin.

    Rin = deltaV / I
    deltaV in mV
    I in nA
    Rin in MOhm because mV/nA = MOhm
    """
    insert_passive(g_pas)

    soma = find_soma_section()

    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY_MS
    stim.dur = STIM_DUR_MS
    stim.amp = STIM_AMP_NA

    t_vec = h.Vector().record(h._ref_t)
    v_vec = h.Vector().record(soma(0.5)._ref_v)

    h.dt = DT_MS
    h.tstop = TSTOP_MS
    h.v_init = TARGET_RMP_MV

    h.finitialize(TARGET_RMP_MV)
    h.continuerun(TSTOP_MS)

    t = np.array(t_vec)
    v = np.array(v_vec)

    baseline_mask = (t >= 50) & (t < 95)
    steady_mask = (t >= 550) & (t < 595)
    recovery_mask = (t >= 750) & (t < 795)

    v_base = float(np.mean(v[baseline_mask]))
    v_steady = float(np.mean(v[steady_mask]))
    v_recovery = float(np.mean(v[recovery_mask]))

    delta_v = v_steady - v_base  # negative for hyperpolarizing pulse
    rin_mohm = abs(delta_v / STIM_AMP_NA)  # mV/nA = MOhm
    rin_gohm = rin_mohm / 1000.0

    if save_trace:
        with open(f"{trace_prefix}.dat", "w") as f:
            for ti, vi in zip(t, v):
                f.write(f"{ti:.6f}\t{vi:.6f}\n")

        plt.figure(figsize=(9, 5))
        plt.plot(t, v)
        plt.axvspan(STIM_DELAY_MS, STIM_DELAY_MS + STIM_DUR_MS, alpha=0.15, label="current injection")
        plt.xlabel("Time (ms)")
        plt.ylabel("Soma voltage (mV)")
        plt.title(f"L796 passive fit: g_pas={g_pas:.3e} S/cm², Rin={rin_gohm:.3f} GΩ")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{trace_prefix}.png", dpi=250)
        plt.close()

    return {
        "g_pas": g_pas,
        "v_base_mV": v_base,
        "v_steady_mV": v_steady,
        "v_recovery_mV": v_recovery,
        "delta_v_mV": delta_v,
        "rin_MOhm": rin_mohm,
        "rin_GOhm": rin_gohm,
        "error_GOhm": rin_gohm - TARGET_RIN_GOHM,
    }


# =========================
# FITTING
# =========================

def fit_gpas_binary_search():
    """
    g_pas up -> leak stronger -> Rin lower.
    g_pas down -> leak weaker -> Rin higher.
    Binary search finds g_pas that matches target Rin.
    """
    low = GPAS_LOW
    high = GPAS_HIGH

    history = []

    for i in range(60):
        mid = math.sqrt(low * high)  # log-space midpoint
        result = run_passive_sim(mid, save_trace=False)
        history.append((i, result))

        rin = result["rin_GOhm"]

        if abs(rin - TARGET_RIN_GOHM) < TOL_RIN_GOHM:
            return mid, result, history

        if rin > TARGET_RIN_GOHM:
            # Rin too high means leak too low. Increase g_pas.
            low = mid
        else:
            # Rin too low means leak too high. Decrease g_pas.
            high = mid

    return mid, result, history


def main():
    print("Importing morphology...")
    import_swc_to_neuron(SWC_FILE)

    print("Fixing geometry...")
    changed = fix_tiny_diameters(min_diam_um=0.2)
    set_nseg_dlambda(freq=100, d_lambda=0.1)

    area, area_by_group = total_area_um2()

    print(f"Imported sections: {len(list(h.allsec()))}")
    print(f"Segments with diameter corrected to 0.2 um: {changed}")
    print(f"Total NEURON membrane area: {area:.2f} um2")
    print("Area by group:")
    for k, v in area_by_group.items():
        print(f"  {k}: {v:.2f} um2")

    # Formula estimate for starting interpretation
    area_cm2 = area * 1e-8
    target_rin_ohm = TARGET_RIN_GOHM * 1e9
    gpas_formula = (1.0 / target_rin_ohm) / area_cm2

    print("\nFormula-based starting estimate:")
    print(f"  g_pas ≈ {gpas_formula:.4e} S/cm2")
    print("Now doing simulation-based fitting...")

    best_gpas, best_result, history = fit_gpas_binary_search()

    print("\nBEST PASSIVE FIT")
    print("=" * 40)
    print(f"Target RMP: {TARGET_RMP_MV:.2f} mV")
    print(f"Target Rin: {TARGET_RIN_GOHM:.3f} GOhm")
    print(f"Best g_pas: {best_gpas:.6e} S/cm2")
    print(f"Simulated Rin: {best_result['rin_GOhm']:.4f} GOhm")
    print(f"Baseline V: {best_result['v_base_mV']:.4f} mV")
    print(f"Steady V: {best_result['v_steady_mV']:.4f} mV")
    print(f"Delta V: {best_result['delta_v_mV']:.4f} mV")
    print(f"Recovery V: {best_result['v_recovery_mV']:.4f} mV")

    # Save final trace
    final = run_passive_sim(best_gpas, save_trace=True, trace_prefix="L796_passive_best_fit")

    # Save history CSV
    with open("L796_passive_gpas_fit_history.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "iteration", "g_pas_S_per_cm2", "rin_GOhm",
            "target_RIN_GOhm", "error_GOhm",
            "v_base_mV", "v_steady_mV", "delta_v_mV"
        ])
        for i, r in history:
            writer.writerow([
                i,
                f"{r['g_pas']:.10e}",
                f"{r['rin_GOhm']:.6f}",
                f"{TARGET_RIN_GOHM:.6f}",
                f"{r['error_GOhm']:.6f}",
                f"{r['v_base_mV']:.6f}",
                f"{r['v_steady_mV']:.6f}",
                f"{r['delta_v_mV']:.6f}",
            ])

    # Save final summary CSV
    with open("L796_passive_best_fit_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["target_RMP", TARGET_RMP_MV, "mV"])
        writer.writerow(["target_RIN", TARGET_RIN_GOHM, "GOhm"])
        writer.writerow(["stim_amp", STIM_AMP_NA, "nA"])
        writer.writerow(["stim_delay", STIM_DELAY_MS, "ms"])
        writer.writerow(["stim_duration", STIM_DUR_MS, "ms"])
        writer.writerow(["cm", CM_UF_CM2, "uF/cm2"])
        writer.writerow(["Ra", RA_OHM_CM, "ohm-cm"])
        writer.writerow(["e_pas", E_PAS_MV, "mV"])
        writer.writerow(["total_area_NEURON", f"{area:.4f}", "um2"])
        writer.writerow(["formula_gpas_estimate", f"{gpas_formula:.10e}", "S/cm2"])
        writer.writerow(["best_gpas", f"{best_gpas:.10e}", "S/cm2"])
        writer.writerow(["simulated_RIN", f"{best_result['rin_GOhm']:.6f}", "GOhm"])
        writer.writerow(["baseline_voltage", f"{best_result['v_base_mV']:.6f}", "mV"])
        writer.writerow(["steady_voltage", f"{best_result['v_steady_mV']:.6f}", "mV"])
        writer.writerow(["delta_voltage", f"{best_result['delta_v_mV']:.6f}", "mV"])
        writer.writerow(["recovery_voltage", f"{best_result['v_recovery_mV']:.6f}", "mV"])

    # Save report text
    report = f"""
L796 PASSIVE FIT REPORT
=======================

Purpose:
Fit passive leak conductance g_pas so that the L796 morphology reproduces the experimental
projection-neuron input resistance reported in Luz et al. 2014.

Experimental target:
RMP target = {TARGET_RMP_MV:.2f} mV
RIN target = {TARGET_RIN_GOHM:.3f} GOhm

Protocol:
Soma current clamp
Current amplitude = {STIM_AMP_NA:.3f} nA
Current delay = {STIM_DELAY_MS:.1f} ms
Current duration = {STIM_DUR_MS:.1f} ms
Simulation end = {TSTOP_MS:.1f} ms

Passive parameters:
cm = {CM_UF_CM2:.3f} uF/cm2
Ra = {RA_OHM_CM:.3f} ohm-cm
e_pas = {E_PAS_MV:.3f} mV
fitted g_pas = {best_gpas:.10e} S/cm2

Morphology:
Total NEURON membrane area = {area:.3f} um2
Formula-based g_pas estimate = {gpas_formula:.10e} S/cm2

Simulation output:
Baseline soma voltage = {best_result['v_base_mV']:.4f} mV
Steady soma voltage during pulse = {best_result['v_steady_mV']:.4f} mV
Voltage deflection = {best_result['delta_v_mV']:.4f} mV
Simulated input resistance = {best_result['rin_GOhm']:.4f} GOhm
Recovery voltage = {best_result['v_recovery_mV']:.4f} mV

Interpretation:
The fitted g_pas value was selected by simulation-based passive fitting, not by formula alone.
The formula estimate was used only as a starting reference because branched morphology and axial
resistance affect the input resistance measured at the soma.
""".strip()

    Path("L796_passive_fit_report.txt").write_text(report, encoding="utf-8")

    print("\nSaved:")
    print("  L796_passive_best_fit.dat")
    print("  L796_passive_best_fit.png")
    print("  L796_passive_best_fit_summary.csv")
    print("  L796_passive_gpas_fit_history.csv")
    print("  L796_passive_fit_report.txt")


if __name__ == "__main__":
    main()
