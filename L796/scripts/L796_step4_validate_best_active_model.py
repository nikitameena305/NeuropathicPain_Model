import os
import csv
import math
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# STEP 4: VALIDATION OF BEST L796 ACTIVE MODEL
# ============================================================
# This script validates the best active candidate from Step 3.
# It does NOT search randomly again.
# It uses the best parameter set and tests it across currents.
# ============================================================


HERE = Path(__file__).resolve().parent
os.chdir(HERE)

SWC_FILE = "L796-ALT-PN.CNG.swc"

# -----------------------------
# Passive values from Step 2
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

# -----------------------------
# Best active candidate from Step 3
# -----------------------------
BEST_PARAMS = {
    "BNa_scale": 1.25,
    "KDR_scale": 0.50,
    "KCa_scale": 0.50,
    "CaL_scale": 1.00,
}

# -----------------------------
# Simulation protocol
# -----------------------------
STIM_DELAY = 100.0
STIM_DUR = 500.0
TSTOP = 800.0
DT = 0.025

# Validation current steps in nA
# 0.02 nA = 20 pA
CURRENT_STEPS_NA = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12]

# Passive check current
HYPERPOLARIZING_CURRENT_NA = -0.01  # -10 pA

# Spike detection threshold
SPIKE_THRESHOLD_MV = -20.0

# Baseline conductance densities from Medlock-like pNK1 mechanisms.
# Units: S/cm2
BASE = {
    "AIS_BNa": 3.45,
    "AIS_KDR": 0.076,

    "soma_KDR": 0.001075,
    "soma_iNaP": 0.0001,
    "soma_CaL": 0.0001,
    "soma_KCa": 0.0001,

    "dend_KDR": 0.036,
    "dend_CaAN": 0.000091,
    "dend_CaL": 0.00003,
    "dend_KCa": 0.001,
}


# ============================================================
# MORPHOLOGY
# ============================================================

def import_morphology():
    h.load_file("stdrun.hoc")
    h.load_file("import3d.hoc")

    reader = h.Import3d_SWC_read()
    reader.input(SWC_FILE)

    importer = h.Import3d_GUI(reader, 0)
    importer.instantiate(None)

    sections = list(h.allsec())
    if not sections:
        raise RuntimeError("No sections imported from SWC.")

    return sections


def find_soma():
    soma_sections = [sec for sec in h.allsec() if "soma" in sec.name().lower()]
    if soma_sections:
        return soma_sections[0]
    return list(h.allsec())[0]


def section_groups():
    groups = {
        "soma": [],
        "axon": [],
        "dend": [],
        "apic": [],
        "other": [],
    }

    for sec in h.allsec():
        name = sec.name().lower()

        if "artificial_ais" in name:
            continue
        elif "soma" in name:
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


def fix_tiny_diameters(min_diam=0.2):
    changed = 0
    for sec in h.allsec():
        for seg in sec:
            if seg.diam < min_diam:
                seg.diam = min_diam
                changed += 1
    return changed


def set_nseg_dlambda(freq=100, d_lambda=0.1):
    for sec in h.allsec():
        try:
            sec.nseg = int((sec.L / (d_lambda * h.lambda_f(freq, sec=sec)) + 0.9) / 2) * 2 + 1
            if sec.nseg < 1:
                sec.nseg = 1
        except Exception:
            sec.nseg = 1


# ============================================================
# MODEL SETUP
# ============================================================

def insert_passive_everywhere():
    for sec in h.allsec():
        sec.Ra = RA
        sec.cm = CM
        sec.insert("pas")
        for seg in sec:
            seg.pas.g = G_PAS
            seg.pas.e = E_PAS


def create_artificial_ais(soma):
    ais = h.Section(name="artificial_ais")
    ais.L = 9.0
    ais.diam = 1.5
    ais.nseg = 5
    ais.Ra = RA
    ais.cm = CM
    ais.connect(soma(1.0))

    ais.insert("pas")
    for seg in ais:
        seg.pas.g = G_PAS
        seg.pas.e = E_PAS

    return ais


def safe_insert(sec, mech):
    try:
        sec.insert(mech)
    except Exception as e:
        print(f"\nERROR: Could not insert {mech} in {sec.name()}")
        print("Run with compiled mechanisms:")
        print("cd ~/NeuropathicPain_Model")
        print("./external/SDHmodel/x86_64/special -python L796/L796_step4_validate_best_active_model.py")
        raise e


def insert_active_mechanisms(ais):
    groups = section_groups()

    # Soma active mechanisms
    for sec in groups["soma"]:
        for mech in ["KDR", "iNaP", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ena = 55
        sec.ek = -90

    # Dendritic active mechanisms
    for sec in groups["dend"] + groups["apic"]:
        for mech in ["KDR", "iCaAN", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ek = -90

    # AIS active mechanisms
    safe_insert(ais, "B_Na")
    safe_insert(ais, "KDR")
    ais.ena = 55
    ais.ek = -90


def set_best_conductances(ais):
    bna = BEST_PARAMS["BNa_scale"]
    kdr = BEST_PARAMS["KDR_scale"]
    kca = BEST_PARAMS["KCa_scale"]
    cal = BEST_PARAMS["CaL_scale"]

    groups = section_groups()

    # Soma
    for sec in groups["soma"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["soma_KDR"] * kdr
        if h.ismembrane("iNaP", sec=sec):
            sec.gnabar_iNaP = BASE["soma_iNaP"]
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["soma_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["soma_KCa"] * kca

    # Dendrites
    for sec in groups["dend"] + groups["apic"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["dend_KDR"] * kdr
        if h.ismembrane("iCaAN", sec=sec):
            sec.gbar_iCaAN = BASE["dend_CaAN"]
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["dend_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["dend_KCa"] * kca

    # AIS
    if h.ismembrane("B_Na", sec=ais):
        ais.gnabar_B_Na = BASE["AIS_BNa"] * bna
    if h.ismembrane("KDR", sec=ais):
        ais.gkbar_KDR = BASE["AIS_KDR"] * kdr


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def count_spikes(t, v, threshold=SPIKE_THRESHOLD_MV, refractory_ms=2.0):
    spike_times = []
    last = -1e9

    for i in range(1, len(v)):
        if v[i - 1] < threshold and v[i] >= threshold:
            if t[i] - last >= refractory_ms:
                spike_times.append(t[i])
                last = t[i]

    return spike_times


def spike_peaks(t, v, spike_times, window_ms=6.0):
    peaks = []
    for st in spike_times:
        mask = (t >= st) & (t <= st + window_ms)
        if np.any(mask):
            peaks.append(float(np.max(v[mask])))
    return peaks


def spike_widths_at_threshold(t, v, spike_times, threshold=SPIKE_THRESHOLD_MV):
    """
    Approximate width at -20 mV threshold.
    This is not true half-width; it is a simple threshold-width metric.
    """
    widths = []

    for st in spike_times:
        # Find index nearest spike start
        start_idx = int(np.argmin(np.abs(t - st)))

        # Find downward crossing after peak/start
        end_idx = None
        for j in range(start_idx + 1, len(v)):
            if v[j - 1] >= threshold and v[j] < threshold:
                end_idx = j
                break

        if end_idx is not None:
            widths.append(float(t[end_idx] - t[start_idx]))

    return widths


def run_current_clamp(soma, ais, current_na, save_trace=False, prefix="trace"):
    set_best_conductances(ais)

    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY
    stim.dur = STIM_DUR
    stim.amp = current_na

    t_vec = h.Vector().record(h._ref_t)
    soma_v_vec = h.Vector().record(soma(0.5)._ref_v)
    ais_v_vec = h.Vector().record(ais(0.5)._ref_v)

    h.dt = DT
    h.tstop = TSTOP
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(TSTOP)

    t = np.array(t_vec)
    soma_v = np.array(soma_v_vec)
    ais_v = np.array(ais_v_vec)

    stim_mask = (t >= STIM_DELAY) & (t <= STIM_DELAY + STIM_DUR)
    base_mask = (t >= 50) & (t < 95)
    late_mask = (t >= 550) & (t < 595)
    rec_mask = (t >= 750) & (t < 795)

    soma_spikes_abs = count_spikes(t[stim_mask], soma_v[stim_mask])
    ais_spikes_abs = count_spikes(t[stim_mask], ais_v[stim_mask])

    soma_peaks = spike_peaks(t, soma_v, soma_spikes_abs)
    ais_peaks = spike_peaks(t, ais_v, ais_spikes_abs)

    soma_widths = spike_widths_at_threshold(t, soma_v, soma_spikes_abs)
    ais_widths = spike_widths_at_threshold(t, ais_v, ais_spikes_abs)

    ais_isis = np.diff(ais_spikes_abs) if len(ais_spikes_abs) >= 2 else np.array([])

    features = {
        "current_pA": current_na * 1000.0,
        "current_nA": current_na,

        "rest_soma_mV": float(np.mean(soma_v[base_mask])),
        "rest_AIS_mV": float(np.mean(ais_v[base_mask])),

        "max_soma_mV": float(np.max(soma_v[stim_mask])),
        "max_AIS_mV": float(np.max(ais_v[stim_mask])),

        "min_soma_mV": float(np.min(soma_v[stim_mask])),
        "min_AIS_mV": float(np.min(ais_v[stim_mask])),

        "plateau_soma_mV_550_595": float(np.mean(soma_v[late_mask])),
        "plateau_AIS_mV_550_595": float(np.mean(ais_v[late_mask])),

        "recovery_soma_mV_750_795": float(np.mean(soma_v[rec_mask])),
        "recovery_AIS_mV_750_795": float(np.mean(ais_v[rec_mask])),

        "soma_spike_count": len(soma_spikes_abs),
        "AIS_spike_count": len(ais_spikes_abs),

        "AIS_first_spike_latency_ms": float(ais_spikes_abs[0] - STIM_DELAY) if ais_spikes_abs else math.nan,
        "soma_first_spike_latency_ms": float(soma_spikes_abs[0] - STIM_DELAY) if soma_spikes_abs else math.nan,

        "AIS_mean_peak_mV": float(np.mean(ais_peaks)) if ais_peaks else math.nan,
        "soma_mean_peak_mV": float(np.mean(soma_peaks)) if soma_peaks else math.nan,

        "AIS_mean_width_at_minus20_ms": float(np.mean(ais_widths)) if ais_widths else math.nan,
        "soma_mean_width_at_minus20_ms": float(np.mean(soma_widths)) if soma_widths else math.nan,

        "AIS_mean_ISI_ms": float(np.mean(ais_isis)) if len(ais_isis) > 0 else math.nan,
        "AIS_first_ISI_ms": float(ais_isis[0]) if len(ais_isis) > 0 else math.nan,
        "AIS_last_ISI_ms": float(ais_isis[-1]) if len(ais_isis) > 0 else math.nan,
        "AIS_adaptation_ratio_lastISI_firstISI": float(ais_isis[-1] / ais_isis[0]) if len(ais_isis) >= 2 and ais_isis[0] != 0 else math.nan,

        "firing_frequency_Hz": len(ais_spikes_abs) / (STIM_DUR / 1000.0),
    }

    if save_trace:
        trace_dir = Path("L796_step4_traces")
        trace_dir.mkdir(exist_ok=True)

        dat_path = trace_dir / f"{prefix}.dat"
        with open(dat_path, "w") as f:
            f.write("time_ms soma_mV AIS_mV\n")
            for ti, sv, av in zip(t, soma_v, ais_v):
                f.write(f"{ti:.6f} {sv:.6f} {av:.6f}\n")

        png_path = trace_dir / f"{prefix}.png"
        plt.figure(figsize=(10, 5))
        plt.plot(t, soma_v, label="soma")
        plt.plot(t, ais_v, label="AIS")
        plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15, label="current injection")
        plt.axhline(SPIKE_THRESHOLD_MV, linestyle="--", linewidth=1, label="-20 mV spike screen")
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (mV)")
        plt.title(f"L796 best active validation: I={current_na*1000:.0f} pA")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(png_path, dpi=250)
        plt.close()

    return t, soma_v, ais_v, features


def compute_rin_active_model(soma, ais):
    t, soma_v, ais_v, features = run_current_clamp(
        soma, ais,
        HYPERPOLARIZING_CURRENT_NA,
        save_trace=True,
        prefix="Rin_check_minus10pA"
    )

    base_mask = (t >= 50) & (t < 95)
    steady_mask = (t >= 550) & (t < 595)

    v_base = float(np.mean(soma_v[base_mask]))
    v_steady = float(np.mean(soma_v[steady_mask]))
    delta_v = v_steady - v_base

    rin_mohm = abs(delta_v / HYPERPOLARIZING_CURRENT_NA)
    rin_gohm = rin_mohm / 1000.0

    return {
        "current_pA": HYPERPOLARIZING_CURRENT_NA * 1000.0,
        "baseline_soma_mV": v_base,
        "steady_soma_mV": v_steady,
        "delta_v_mV": delta_v,
        "Rin_GOhm": rin_gohm,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("Step 4: validating selected L796 active model...")

    import_morphology()
    changed = fix_tiny_diameters(0.2)
    set_nseg_dlambda()

    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    insert_active_mechanisms(ais)
    set_best_conductances(ais)

    print(f"Soma section: {soma.name()}")
    print(f"Artificial AIS: {ais.name()}")
    print(f"Diameters corrected below 0.2 um: {changed}")
    print("Best active parameters:")
    for k, v in BEST_PARAMS.items():
        print(f"  {k}: {v}")

    # Save final parameter set
    final_params = {
        "passive": {
            "e_pas_mV": E_PAS,
            "g_pas_S_per_cm2": G_PAS,
            "cm_uF_per_cm2": CM,
            "Ra_ohm_cm": RA,
        },
        "best_active_scales": BEST_PARAMS,
        "base_conductance_densities_S_per_cm2": BASE,
        "protocol": {
            "stim_delay_ms": STIM_DELAY,
            "stim_duration_ms": STIM_DUR,
            "tstop_ms": TSTOP,
            "dt_ms": DT,
            "spike_threshold_mV": SPIKE_THRESHOLD_MV,
        },
    }

    with open("L796_step4_final_parameter_set.json", "w") as f:
        json.dump(final_params, f, indent=2)

    # 1. Passive/Rin check after active channel insertion
    rin_info = compute_rin_active_model(soma, ais)

    with open("L796_step4_Rin_check.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        for k, v in rin_info.items():
            unit = "GOhm" if "Rin" in k else ("mV" if "mV" in k or "delta" in k else "pA")
            writer.writerow([k, v, unit])

    # 2. Current sweep validation
    all_features = []
    all_traces = {}

    for cur in CURRENT_STEPS_NA:
        prefix = f"I_{int(cur*1000):03d}pA"
        t, soma_v, ais_v, feat = run_current_clamp(
            soma, ais,
            cur,
            save_trace=True,
            prefix=prefix
        )
        all_features.append(feat)
        all_traces[cur] = (t, soma_v, ais_v)

    # Save feature table
    feature_fields = list(all_features[0].keys())
    with open("L796_step4_current_sweep_features.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=feature_fields)
        writer.writeheader()
        for row in all_features:
            writer.writerow(row)

    # F-I curve
    plt.figure(figsize=(8, 5))
    plt.plot(
        [f["current_pA"] for f in all_features],
        [f["AIS_spike_count"] for f in all_features],
        marker="o",
        label="AIS"
    )
    plt.plot(
        [f["current_pA"] for f in all_features],
        [f["soma_spike_count"] for f in all_features],
        marker="s",
        label="soma"
    )
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Spike count during 500 ms")
    plt.title("L796 validated active model: F-I curve")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_step4_FI_curve.png", dpi=250)
    plt.close()

    # Firing frequency curve
    plt.figure(figsize=(8, 5))
    plt.plot(
        [f["current_pA"] for f in all_features],
        [f["firing_frequency_Hz"] for f in all_features],
        marker="o"
    )
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Firing frequency (Hz)")
    plt.title("L796 validated active model: firing frequency")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("L796_step4_frequency_curve.png", dpi=250)
    plt.close()

    # AIS overlay traces
    plt.figure(figsize=(10, 6))
    for cur, (t, soma_v, ais_v) in all_traces.items():
        plt.plot(t, ais_v, label=f"{cur*1000:.0f} pA")
    plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.12, label="current injection")
    plt.axhline(SPIKE_THRESHOLD_MV, linestyle="--", linewidth=1, label="-20 mV spike screen")
    plt.xlabel("Time (ms)")
    plt.ylabel("AIS voltage (mV)")
    plt.title("L796 validated active model: AIS current-step traces")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_step4_AIS_current_traces_overlay.png", dpi=250)
    plt.close()

    # Soma overlay traces
    plt.figure(figsize=(10, 6))
    for cur, (t, soma_v, ais_v) in all_traces.items():
        plt.plot(t, soma_v, label=f"{cur*1000:.0f} pA")
    plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.12, label="current injection")
    plt.axhline(SPIKE_THRESHOLD_MV, linestyle="--", linewidth=1, label="-20 mV spike screen")
    plt.xlabel("Time (ms)")
    plt.ylabel("Soma voltage (mV)")
    plt.title("L796 validated active model: soma current-step traces")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_step4_soma_current_traces_overlay.png", dpi=250)
    plt.close()

    # Final report
    rows_by_current = {round(f["current_pA"]): f for f in all_features}
    main60 = rows_by_current.get(60, None)
    rest0 = rows_by_current.get(0, None)

    report = []
    report.append("L796 STEP 4 VALIDATED ACTIVE MODEL REPORT")
    report.append("=" * 55)
    report.append("")
    report.append("Purpose:")
    report.append("Validate the best active conductance candidate selected from Step 3.")
    report.append("")
    report.append("Fixed passive parameters:")
    report.append(f"  e_pas = {E_PAS} mV")
    report.append(f"  g_pas = {G_PAS:.10e} S/cm2")
    report.append(f"  cm = {CM} uF/cm2")
    report.append(f"  Ra = {RA} ohm-cm")
    report.append("")
    report.append("Selected active conductance scales:")
    for k, v in BEST_PARAMS.items():
        report.append(f"  {k} = {v}")
    report.append("")
    report.append("Rin check with active mechanisms inserted:")
    report.append(f"  Current = {rin_info['current_pA']:.1f} pA")
    report.append(f"  Baseline soma voltage = {rin_info['baseline_soma_mV']:.4f} mV")
    report.append(f"  Steady soma voltage = {rin_info['steady_soma_mV']:.4f} mV")
    report.append(f"  Delta V = {rin_info['delta_v_mV']:.4f} mV")
    report.append(f"  Rin = {rin_info['Rin_GOhm']:.4f} GOhm")
    report.append("")
    report.append("Current sweep summary:")
    for f in all_features:
        report.append(
            f"  {f['current_pA']:.0f} pA: "
            f"AIS spikes={f['AIS_spike_count']}, "
            f"soma spikes={f['soma_spike_count']}, "
            f"max AIS={f['max_AIS_mV']:.2f} mV, "
            f"recovery soma={f['recovery_soma_mV_750_795']:.2f} mV"
        )
    report.append("")

    if rest0 is not None:
        if rest0["AIS_spike_count"] == 0:
            report.append("[OK] No spontaneous AIS firing at 0 pA.")
        else:
            report.append("[WARNING] Spontaneous firing occurred at 0 pA.")

    if main60 is not None:
        if main60["AIS_spike_count"] >= 3:
            report.append("[OK] Repetitive AIS firing was present at 60 pA.")
        else:
            report.append("[WARNING] Weak or absent repetitive firing at 60 pA.")

        report.append(
            f"At 60 pA, the model produced {main60['AIS_spike_count']} AIS spikes "
            f"and {main60['soma_spike_count']} soma spikes."
        )

    report.append("")
    report.append("Interpretation:")
    report.append(
        "The selected active parameter set was validated across multiple current steps. "
        "The model should be considered an exploratory tuned active L796 projection-neuron model, "
        "because the L796 experimental paper provides firing-pattern targets but does not provide exact "
        "active conductance-density values."
    )

    Path("L796_step4_validated_active_model_report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\nStep 4 validation finished.")
    print("Saved:")
    print("  L796_step4_final_parameter_set.json")
    print("  L796_step4_Rin_check.csv")
    print("  L796_step4_current_sweep_features.csv")
    print("  L796_step4_FI_curve.png")
    print("  L796_step4_frequency_curve.png")
    print("  L796_step4_AIS_current_traces_overlay.png")
    print("  L796_step4_soma_current_traces_overlay.png")
    print("  L796_step4_traces/")
    print("  L796_step4_validated_active_model_report.txt")


if __name__ == "__main__":
    main()
