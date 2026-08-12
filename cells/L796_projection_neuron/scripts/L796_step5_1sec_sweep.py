import os
import csv
import json
import math
import random
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# STEP 5: ACTIVE CONDUCTANCE TUNING FOR L796
# ============================================================
# This script refines the active conductance scales around the
# best Step 4 candidate.
#
# Passive parameters are fixed.
# Active conductance scales are tuned using an objective score.
# ============================================================


HERE = Path(__file__).resolve().parent
os.chdir(HERE)

PROJECT_ROOT = HERE.parent
SWC_FILE = str(PROJECT_ROOT / "morphology" / "L796-ALT-PN.CNG.swc")

# -----------------------------
# Fixed passive model from Step 2
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

TARGET_RMP = -72.8
TARGET_RIN_GOHM = 0.77

# -----------------------------
# Step 4 best active candidate
# -----------------------------
STEP4_BEST = {
    "BNa_scale": 1.25,
    "KDR_scale": 0.50,
    "KCa_scale": 0.50,
    "CaL_scale": 1.00,
    "iNaP_scale": 1.00,
    "CaAN_scale": 1.00,
}

# -----------------------------
# Simulation protocol
# -----------------------------
STIM_DELAY = 100.0
STIM_DUR = 500.0
TSTOP = 900.0
DT = 0.025
SPIKE_THRESHOLD = -20.0

CURRENT_STEPS_NA = [-0.01, 0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12]

# Desired spike-count pattern based on your Step 4 good model
# and tonic-like current-dependent response.
TARGET_SPIKES = {
    0: 0,
    20: 0,
    40: 2,
    60: 4,
    80: 5,
    100: 6,
    120: 6,
}

# -----------------------------
# Search settings
# -----------------------------
RANDOM_SEED = 42
N_RANDOM_CANDIDATES = 250

# If it is too slow, reduce to 100.
# If you want deeper search later, increase to 500 or 1000.

SEARCH_VALUES = {
    "BNa_scale":  [1.05, 1.15, 1.25, 1.35, 1.45],
    "KDR_scale":  [0.35, 0.45, 0.50, 0.55, 0.65],
    "KCa_scale":  [0.25, 0.50, 0.75, 1.00, 1.50],
    "CaL_scale":  [0.50, 0.75, 1.00, 1.25, 1.50],
    "iNaP_scale": [0.50, 0.75, 1.00, 1.25, 1.50],
    "CaAN_scale": [0.50, 0.75, 1.00, 1.25, 1.50],
}

# -----------------------------
# Baseline conductance densities
# Units: S/cm2
# -----------------------------
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
# MORPHOLOGY FUNCTIONS
# ============================================================

def import_morphology():
    h.load_file("stdrun.hoc")
    h.load_file("import3d.hoc")

    reader = h.Import3d_SWC_read()
    reader.input(SWC_FILE)

    importer = h.Import3d_GUI(reader, 0)
    importer.instantiate(None)

    secs = list(h.allsec())
    if not secs:
        raise RuntimeError("No sections imported from SWC.")
    return secs


def find_soma():
    soma_secs = [sec for sec in h.allsec() if "soma" in sec.name().lower()]
    return soma_secs[0] if soma_secs else list(h.allsec())[0]


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
        print("cd /path/to/NeuropathicPain_Model")
        print("./shared/mechanisms/medlock_267056/x86_64/special -python cells/L796_projection_neuron/scripts/L796_step5_1sec_sweep.py")
        raise e


def insert_active_mechanisms(ais):
    groups = section_groups()

    for sec in groups["soma"]:
        for mech in ["KDR", "iNaP", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ena = 55
        sec.ek = -90

    for sec in groups["dend"] + groups["apic"]:
        for mech in ["KDR", "iCaAN", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ek = -90

    safe_insert(ais, "B_Na")
    safe_insert(ais, "KDR")
    ais.ena = 55
    ais.ek = -90


def set_conductance_scales(ais, params):
    groups = section_groups()

    bna = params["BNa_scale"]
    kdr = params["KDR_scale"]
    kca = params["KCa_scale"]
    cal = params["CaL_scale"]
    inap = params["iNaP_scale"]
    caan = params["CaAN_scale"]

    # Soma
    for sec in groups["soma"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["soma_KDR"] * kdr
        if h.ismembrane("iNaP", sec=sec):
            sec.gnabar_iNaP = BASE["soma_iNaP"] * inap
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["soma_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["soma_KCa"] * kca

    # Dendrites
    for sec in groups["dend"] + groups["apic"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["dend_KDR"] * kdr
        if h.ismembrane("iCaAN", sec=sec):
            sec.gbar_iCaAN = BASE["dend_CaAN"] * caan
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

def count_spikes(t, v, threshold=SPIKE_THRESHOLD, refractory_ms=2.0):
    spike_times = []
    last_time = -1e9

    for i in range(1, len(v)):
        if v[i - 1] < threshold and v[i] >= threshold:
            if t[i] - last_time >= refractory_ms:
                spike_times.append(float(t[i]))
                last_time = float(t[i])

    return spike_times


def spike_peaks_and_widths(t, v, spike_times):
    peaks = []
    widths = []

    for st in spike_times:
        peak_mask = (t >= st) & (t <= st + 8.0)
        idx = np.where(peak_mask)[0]
        if len(idx) == 0:
            continue

        peak_idx = idx[np.argmax(v[idx])]
        peak_v = float(v[peak_idx])
        peaks.append(peak_v)

        half_level = (SPIKE_THRESHOLD + peak_v) / 2.0

        left = None
        for j in range(max(1, peak_idx - 200), peak_idx + 1):
            if v[j - 1] < half_level and v[j] >= half_level:
                left = j
                break

        right = None
        for j in range(peak_idx + 1, min(len(v), peak_idx + 800)):
            if v[j - 1] >= half_level and v[j] < half_level:
                right = j
                break

        if left is not None and right is not None:
            widths.append(float(t[right] - t[left]))

    return peaks, widths


def run_sim(soma, ais, current_na, params, save_trace=False, prefix="trace"):
    set_conductance_scales(ais, params)

    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY
    stim.dur = STIM_DUR
    stim.amp = current_na

    t_vec = h.Vector().record(h._ref_t)
    soma_vec = h.Vector().record(soma(0.5)._ref_v)
    ais_vec = h.Vector().record(ais(0.5)._ref_v)

    h.dt = DT
    h.tstop = TSTOP
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(TSTOP)

    t = np.array(t_vec)
    soma_v = np.array(soma_vec)
    ais_v = np.array(ais_vec)

    base_mask = (t >= 50) & (t < 95)
    stim_mask = (t >= STIM_DELAY) & (t <= STIM_DELAY + STIM_DUR)
    late_mask = (t >= 550) & (t < 595)
    recovery_mask = (t >= 800) & (t < 895)

    soma_spikes = count_spikes(t[stim_mask], soma_v[stim_mask])
    ais_spikes = count_spikes(t[stim_mask], ais_v[stim_mask])

    soma_peaks, soma_widths = spike_peaks_and_widths(t, soma_v, soma_spikes)
    ais_peaks, ais_widths = spike_peaks_and_widths(t, ais_v, ais_spikes)

    ais_isis = np.diff(ais_spikes) if len(ais_spikes) >= 2 else np.array([])

    current_pA = int(round(current_na * 1000))

    if current_na < 0:
        # RIN from -10 pA pulse
        v_base = float(np.mean(soma_v[base_mask]))
        v_steady = float(np.mean(soma_v[late_mask]))
        delta_v = v_steady - v_base
        rin_gohm = abs(delta_v / current_na) / 1000.0
    else:
        rin_gohm = math.nan
        delta_v = math.nan

    feat = {
        "current_pA": current_pA,
        "current_nA": current_na,

        "soma_RMP_mV": float(np.mean(soma_v[base_mask])),
        "AIS_RMP_mV": float(np.mean(ais_v[base_mask])),

        "soma_spike_count": len(soma_spikes),
        "AIS_spike_count": len(ais_spikes),

        "AIS_frequency_Hz": len(ais_spikes) / (STIM_DUR / 1000.0),
        "soma_frequency_Hz": len(soma_spikes) / (STIM_DUR / 1000.0),

        "AIS_first_latency_ms": float(ais_spikes[0] - STIM_DELAY) if ais_spikes else math.nan,
        "soma_first_latency_ms": float(soma_spikes[0] - STIM_DELAY) if soma_spikes else math.nan,

        "AIS_AP_peak_mV": float(np.mean(ais_peaks)) if ais_peaks else math.nan,
        "soma_AP_peak_mV": float(np.mean(soma_peaks)) if soma_peaks else math.nan,

        "AIS_AP_width_ms": float(np.mean(ais_widths)) if ais_widths else math.nan,
        "soma_AP_width_ms": float(np.mean(soma_widths)) if soma_widths else math.nan,

        "AIS_mean_ISI_ms": float(np.mean(ais_isis)) if len(ais_isis) > 0 else math.nan,
        "AIS_first_ISI_ms": float(ais_isis[0]) if len(ais_isis) > 0 else math.nan,
        "AIS_last_ISI_ms": float(ais_isis[-1]) if len(ais_isis) > 0 else math.nan,
        "AIS_adaptation_ratio": float(ais_isis[-1] / ais_isis[0]) if len(ais_isis) >= 2 and ais_isis[0] != 0 else math.nan,
        "AIS_ISI_CV": float(np.std(ais_isis) / np.mean(ais_isis)) if len(ais_isis) >= 2 and np.mean(ais_isis) != 0 else math.nan,

        "max_soma_mV": float(np.max(soma_v[stim_mask])),
        "max_AIS_mV": float(np.max(ais_v[stim_mask])),
        "plateau_soma_mV": float(np.mean(soma_v[late_mask])),
        "plateau_AIS_mV": float(np.mean(ais_v[late_mask])),
        "recovery_soma_mV": float(np.mean(soma_v[recovery_mask])),
        "recovery_AIS_mV": float(np.mean(ais_v[recovery_mask])),

        "RIN_GOhm": rin_gohm,
        "RIN_deltaV_mV": delta_v,
    }

    if save_trace:
        outdir = Path("L796_step5_best_traces")
        outdir.mkdir(exist_ok=True)

        dat = outdir / f"{prefix}.dat"
        with open(dat, "w") as f:
            f.write("time_ms soma_mV AIS_mV\n")
            for ti, sv, av in zip(t, soma_v, ais_v):
                f.write(f"{ti:.6f} {sv:.6f} {av:.6f}\n")

        png = outdir / f"{prefix}.png"
        plt.figure(figsize=(10, 5))
        plt.plot(t, soma_v, label="soma")
        plt.plot(t, ais_v, label="AIS")
        plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15, label="current injection")
        plt.axhline(SPIKE_THRESHOLD, linestyle="--", linewidth=1, label="-20 mV spike screen")
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (mV)")
        plt.title(f"L796 Step 5 tuned model: I={current_pA} pA")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(png, dpi=250)
        plt.close()

    return feat


# ============================================================
# SCORING FUNCTION
# ============================================================

def score_candidate(features_by_current):
    """
    Higher score = better tuned active model.

    We reward:
    - stable rest at 0 pA
    - RIN near 0.77 GOhm
    - target spike counts
    - monotonic F-I curve
    - good AP peaks
    - recovery near rest
    - regular tonic-like ISI
    """
    score = 0.0

    # RIN check from -10 pA
    neg = features_by_current.get(-10)
    if neg:
        rin = neg["RIN_GOhm"]
        score -= abs(rin - TARGET_RIN_GOHM) * 250.0

    # 0 pA stability
    rest = features_by_current.get(0)
    if rest:
        if rest["AIS_spike_count"] == 0 and rest["soma_spike_count"] == 0:
            score += 250.0
        else:
            score -= 1000.0

        score -= abs(rest["soma_RMP_mV"] - TARGET_RMP) * 15.0

        if rest["max_AIS_mV"] > SPIKE_THRESHOLD:
            score -= 500.0

    # Target spike counts
    spike_sequence = []

    for pA, target in TARGET_SPIKES.items():
        feat = features_by_current.get(pA)
        if not feat:
            continue

        actual = feat["AIS_spike_count"]
        spike_sequence.append(actual)

        score -= abs(actual - target) * 60.0

        if actual == target:
            score += 35.0

        # For spiking responses, AP peak should cross 0 mV.
        if target > 0:
            if feat["max_AIS_mV"] > 0:
                score += 20.0
            else:
                score -= 80.0

            if feat["max_soma_mV"] > -5:
                score += 15.0
            else:
                score -= 40.0

        # Recovery should approach rest. Penalize poor recovery.
        # We use 800-895 ms window because TSTOP is 900 ms.
        if pA in [40, 60, 80, 100, 120]:
            score -= abs(feat["recovery_soma_mV"] - TARGET_RMP) * 8.0

    # Monotonic F-I curve
    currents = [0, 20, 40, 60, 80, 100, 120]
    spikes = [features_by_current[c]["AIS_spike_count"] for c in currents if c in features_by_current]

    for a, b in zip(spikes[:-1], spikes[1:]):
        if b < a:
            score -= 200.0
        elif b > a:
            score += 10.0

    # Tonic regularity at 60 pA
    f60 = features_by_current.get(60)
    if f60 and f60["AIS_spike_count"] >= 3:
        ar = f60["AIS_adaptation_ratio"]
        cv = f60["AIS_ISI_CV"]

        if not math.isnan(ar):
            score -= abs(ar - 1.0) * 50.0
            if 0.75 <= ar <= 1.35:
                score += 40.0

        if not math.isnan(cv):
            score -= cv * 80.0
            if cv < 0.25:
                score += 40.0

        lat = f60["AIS_first_latency_ms"]
        if not math.isnan(lat):
            if 40 <= lat <= 140:
                score += 20.0
            else:
                score -= 20.0

    return score


# ============================================================
# CANDIDATE GENERATION
# ============================================================

def make_random_candidates():
    random.seed(RANDOM_SEED)

    candidates = []
    seen = set()

    # Always include Step 4 best model
    candidates.append(STEP4_BEST.copy())
    seen.add(tuple(STEP4_BEST[k] for k in SEARCH_VALUES.keys()))

    while len(candidates) < N_RANDOM_CANDIDATES:
        p = {k: random.choice(vs) for k, vs in SEARCH_VALUES.items()}
        key = tuple(p[k] for k in SEARCH_VALUES.keys())
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    return candidates


# ============================================================
# MAIN
# ============================================================

def main():
    print("Step 5: importing morphology and building active model...")

    import_morphology()
    changed = fix_tiny_diameters(0.2)
    set_nseg_dlambda()

    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    insert_active_mechanisms(ais)

    print(f"Soma section: {soma.name()}")
    print(f"Artificial AIS: {ais.name()}")
    print(f"Diameters corrected below 0.2 um: {changed}")
    print(f"Random candidates to test: {N_RANDOM_CANDIDATES}")
    print("Starting tuning search...")

    candidates = make_random_candidates()
    results = []

    for i, params in enumerate(candidates, start=1):
        if i % 25 == 0:
            print(f"  Tested {i}/{len(candidates)} candidates...")

        features_by_current = {}

        for cur in CURRENT_STEPS_NA:
            feat = run_sim(soma, ais, cur, params, save_trace=False)
            features_by_current[feat["current_pA"]] = feat

        score = score_candidate(features_by_current)

        row = {
            "score": score,
            **params,
        }

        # Store summary features for important currents.
        for pA in [0, 20, 40, 60, 80, 100, 120]:
            feat = features_by_current.get(pA)
            if feat:
                prefix = f"I{pA}"
                row[f"{prefix}_AIS_spikes"] = feat["AIS_spike_count"]
                row[f"{prefix}_soma_spikes"] = feat["soma_spike_count"]
                row[f"{prefix}_max_AIS_mV"] = feat["max_AIS_mV"]
                row[f"{prefix}_max_soma_mV"] = feat["max_soma_mV"]
                row[f"{prefix}_recovery_soma_mV"] = feat["recovery_soma_mV"]
                row[f"{prefix}_AIS_latency_ms"] = feat["AIS_first_latency_ms"]
                row[f"{prefix}_AIS_AP_peak_mV"] = feat["AIS_AP_peak_mV"]
                row[f"{prefix}_AIS_AP_width_ms"] = feat["AIS_AP_width_ms"]
                row[f"{prefix}_AIS_adaptation_ratio"] = feat["AIS_adaptation_ratio"]
                row[f"{prefix}_AIS_ISI_CV"] = feat["AIS_ISI_CV"]
                row[f"{prefix}_RIN_GOhm"] = feat["RIN_GOhm"]

        results.append((row, features_by_current))

    results_sorted = sorted(results, key=lambda x: x[0]["score"], reverse=True)
    best_row, best_features = results_sorted[0]
    best_params = {k: best_row[k] for k in SEARCH_VALUES.keys()}

    # Save all candidate summary
    all_rows = [r for r, f in results_sorted]
    all_fieldnames = sorted(set().union(*[row.keys() for row in all_rows]))

    with open("L796_step5_all_tuning_candidates.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    with open("L796_step5_top20_tuned_candidates.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        for row in all_rows[:20]:
            writer.writerow(row)

    # Save best full features table
    full_feature_rows = []
    for pA in sorted(best_features.keys()):
        row = {
            "current_pA": pA,
            **best_features[pA],
        }
        full_feature_rows.append(row)

    feature_fieldnames = sorted(set().union(*[row.keys() for row in full_feature_rows]))
    with open("L796_step5_best_model_features.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=feature_fieldnames)
        writer.writeheader()
        for row in full_feature_rows:
            writer.writerow(row)

    # Save best parameter set
    final_params = {
        "passive_fixed": {
            "e_pas_mV": E_PAS,
            "g_pas_S_per_cm2": G_PAS,
            "cm_uF_per_cm2": CM,
            "Ra_ohm_cm": RA,
        },
        "tuned_active_scales": best_params,
        "base_conductance_densities_S_per_cm2": BASE,
        "search_values": SEARCH_VALUES,
        "target_spikes": TARGET_SPIKES,
        "best_score": best_row["score"],
    }

    with open("L796_step5_best_tuned_parameter_set.json", "w") as f:
        json.dump(final_params, f, indent=2)

    # Save traces for best model
    for cur in CURRENT_STEPS_NA:
        pA = int(round(cur * 1000))
        run_sim(soma, ais, cur, best_params, save_trace=True, prefix=f"best_I_{pA}pA")

    # Plot F-I curve for best model
    positive_currents = [p for p in sorted(best_features.keys()) if p >= 0]
    ais_counts = [best_features[p]["AIS_spike_count"] for p in positive_currents]
    soma_counts = [best_features[p]["soma_spike_count"] for p in positive_currents]
    freq = [best_features[p]["AIS_frequency_Hz"] for p in positive_currents]

    plt.figure(figsize=(8, 5))
    plt.plot(positive_currents, ais_counts, marker="o", label="AIS")
    plt.plot(positive_currents, soma_counts, marker="s", label="soma")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Spike count during 500 ms")
    plt.title("L796 Step 5 tuned model: F-I curve")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_step5_tuned_FI_curve.png", dpi=250)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(positive_currents, freq, marker="o")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Mean firing frequency (Hz)")
    plt.title("L796 Step 5 tuned model: mean firing frequency")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("L796_step5_tuned_frequency_curve.png", dpi=250)
    plt.close()

    # Overlay AIS traces for best model
    plt.figure(figsize=(10, 6))
    for cur in CURRENT_STEPS_NA:
        if cur < 0:
            continue
        pA = int(round(cur * 1000))
        trace_path = Path("L796_step5_best_traces") / f"best_I_{pA}pA.dat"
        data = np.loadtxt(trace_path, skiprows=1)
        t = data[:, 0]
        ais_v = data[:, 2]
        plt.plot(t, ais_v, label=f"{pA} pA")
    plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15, label="current injection")
    plt.axhline(SPIKE_THRESHOLD, linestyle="--", linewidth=1, label="-20 mV spike screen")
    plt.xlabel("Time (ms)")
    plt.ylabel("AIS voltage (mV)")
    plt.title("L796 Step 5 tuned model: AIS traces")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_step5_tuned_AIS_trace_overlay.png", dpi=250)
    plt.close()

    # Report
    report = []
    report.append("L796 STEP 5 ACTIVE CONDUCTANCE TUNING REPORT")
    report.append("=" * 60)
    report.append("")
    report.append("Purpose:")
    report.append("Refine active conductance scales around the Step 4 best candidate.")
    report.append("")
    report.append("Passive parameters were kept fixed:")
    report.append(f"  e_pas = {E_PAS} mV")
    report.append(f"  g_pas = {G_PAS:.10e} S/cm2")
    report.append(f"  cm = {CM} uF/cm2")
    report.append(f"  Ra = {RA} ohm-cm")
    report.append("")
    report.append("Best tuned active scales:")
    for k, v in best_params.items():
        report.append(f"  {k} = {v}")
    report.append("")
    report.append(f"Best score = {best_row['score']:.4f}")
    report.append("")
    report.append("Best model current-step summary:")
    for pA in sorted(best_features.keys()):
        feat = best_features[pA]
        if pA == -10:
            report.append(
                f"  -10 pA: RIN = {feat['RIN_GOhm']:.4f} GOhm, "
                f"deltaV = {feat['RIN_deltaV_mV']:.4f} mV"
            )
        else:
            report.append(
                f"  {pA} pA: AIS spikes={feat['AIS_spike_count']}, "
                f"soma spikes={feat['soma_spike_count']}, "
                f"freq={feat['AIS_frequency_Hz']:.2f} Hz, "
                f"AIS peak={feat['max_AIS_mV']:.2f} mV, "
                f"latency={feat['AIS_first_latency_ms']:.2f} ms, "
                f"recovery soma={feat['recovery_soma_mV']:.2f} mV, "
                f"adaptation={feat['AIS_adaptation_ratio']}"
            )
    report.append("")
    report.append("Interpretation:")
    report.append(
        "The tuned model should be selected only if it improves recovery, stability, and "
        "feature targets compared with Step 4. Because the L796 experimental paper does not "
        "provide exact conductance densities, this remains an exploratory feature-tuned active model."
    )

    Path("L796_step5_tuning_report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\nStep 5 tuning finished.")
    print("Best tuned active scales:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"Best score: {best_row['score']:.4f}")
    print("\nSaved:")
    print("  L796_step5_all_tuning_candidates.csv")
    print("  L796_step5_top20_tuned_candidates.csv")
    print("  L796_step5_best_model_features.csv")
    print("  L796_step5_best_tuned_parameter_set.json")
    print("  L796_step5_tuned_FI_curve.png")
    print("  L796_step5_tuned_frequency_curve.png")
    print("  L796_step5_tuned_AIS_trace_overlay.png")
    print("  L796_step5_best_traces/")
    print("  L796_step5_tuning_report.txt")


if __name__ == "__main__":
    main()
