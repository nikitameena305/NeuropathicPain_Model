import os
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# 06: ACTIVE VALIDATION FOR L796 (current / baseline model)
# ============================================================
# Builds the current active L796 model exactly as produced by
# Step 5 tuning (soma: KDR/iNaP/iCaL/iKCa; dendrites:
# KDR/iCaAN/iCaL/iKCa; artificial AIS: B_Na/KDR -- NOTE the soma
# itself has NO fast Na channel in this baseline model). Runs a
# current-clamp step protocol, extracts somatic AP features and
# rheobase, and compares against literature targets.
# ============================================================


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
os.chdir(PROJECT_ROOT)

SWC_FILE = str(PROJECT_ROOT / "morphology" / "L796-ALT-PN.CNG.swc")
TARGETS_FILE = PROJECT_ROOT / "literature_targets" / "L796_literature_targets.json"

OUT_DIR = PROJECT_ROOT / "validation" / "active"
TRACE_DIR = PROJECT_ROOT / "traces" / "active_baseline"

# -----------------------------
# Fixed passive parameters (Step 2)
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

# -----------------------------
# Current best-tuned active scales (Step 5) -- baseline model,
# soma has NO fast Na channel (B_Na lives only in the artificial AIS).
# -----------------------------
BASELINE_PARAMS = {
    "BNa_scale": 1.45,
    "KDR_scale": 0.50,
    "KCa_scale": 0.25,
    "CaL_scale": 1.25,
    "iNaP_scale": 1.00,
    "CaAN_scale": 1.25,
}

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

# -----------------------------
# Simulation protocol
# -----------------------------
STIM_DELAY = 100.0
STIM_DUR = 500.0
TSTOP = 900.0
DT = 0.025
SPIKE_THRESHOLD = -20.0  # coarse spike-screen for spike counting
DVDT_THRESHOLD = 10.0    # mV/ms, AP-onset criterion for amplitude/width

CURRENT_STEPS_NA = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
RHEOBASE_SWEEP_PA = list(range(0, 105, 5))  # fine 5 pA sweep, 0-100 pA


# ============================================================
# MORPHOLOGY / MODEL HELPERS (same conventions as Step 5 template)
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
    groups = {"soma": [], "axon": [], "dend": [], "apic": [], "other": []}
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
        print("./external/SDHmodel/x86_64/special -python L796/scripts/06_active_validation.py")
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

    for sec in groups["soma"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["soma_KDR"] * kdr
        if h.ismembrane("iNaP", sec=sec):
            sec.gnabar_iNaP = BASE["soma_iNaP"] * inap
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["soma_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["soma_KCa"] * kca

    for sec in groups["dend"] + groups["apic"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["dend_KDR"] * kdr
        if h.ismembrane("iCaAN", sec=sec):
            sec.gbar_iCaAN = BASE["dend_CaAN"] * caan
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["dend_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["dend_KCa"] * kca

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


def ap_amplitude_and_width(t, v, spike_time, dvdt_threshold=DVDT_THRESHOLD, window_ms=8.0):
    """Onset-referenced AP amplitude/half-width using a dV/dt threshold criterion."""
    mask = (t >= spike_time - 5.0) & (t <= spike_time + window_ms)
    idx = np.where(mask)[0]
    if len(idx) < 3:
        return None

    tt = t[idx]
    vv = v[idx]
    dvdt = np.gradient(vv, tt)

    peak_local = int(np.argmax(vv))
    peak_v = float(vv[peak_local])
    peak_t = float(tt[peak_local])

    onset_local = None
    for j in range(1, peak_local + 1):
        if dvdt[j] >= dvdt_threshold:
            onset_local = j
            break
    if onset_local is None:
        return None

    onset_v = float(vv[onset_local])
    amplitude = peak_v - onset_v

    half_level = onset_v + amplitude / 2.0

    left = None
    for j in range(onset_local, peak_local + 1):
        if vv[j] >= half_level:
            left = j
            break

    right = None
    for j in range(peak_local, len(vv)):
        if vv[j] < half_level:
            right = j
            break

    half_width = None
    if left is not None and right is not None and right > left:
        half_width = float(tt[right] - tt[left])

    return {
        "peak_mV": peak_v,
        "peak_time_ms": peak_t,
        "onset_mV": onset_v,
        "amplitude_mV": amplitude,
        "overshoot_mV": peak_v,
        "half_width_ms": half_width,
    }


def classify_firing_pattern(spike_times, stim_delay=STIM_DELAY, stim_dur=STIM_DUR):
    if len(spike_times) == 0:
        return "silent"
    first_latency = spike_times[0] - stim_delay
    if len(spike_times) == 1:
        return "single"

    isis = np.diff(spike_times)
    cv = float(np.std(isis) / np.mean(isis)) if np.mean(isis) != 0 else math.nan

    if first_latency > 0.15 * stim_dur:
        return "delayed"
    if len(spike_times) >= 3 and not math.isnan(cv) and cv < 0.5:
        return "tonic"
    return "phasic"


def run_sim(soma, ais, current_na, params, save_trace=False, prefix="trace"):
    set_conductance_scales(ais, params)

    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY
    stim.dur = STIM_DUR
    stim.amp = current_na

    t_vec = h.Vector().record(h._ref_t)
    soma_vec = h.Vector().record(soma(0.5)._ref_v)

    h.dt = DT
    h.tstop = TSTOP
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(TSTOP)

    t = np.array(t_vec)
    v = np.array(soma_vec)

    stim_mask = (t >= STIM_DELAY) & (t <= STIM_DELAY + STIM_DUR)
    spikes = count_spikes(t[stim_mask], v[stim_mask])

    if save_trace:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        dat = TRACE_DIR / f"{prefix}.dat"
        with open(dat, "w") as f:
            f.write("time_ms soma_mV\n")
            for ti, vi in zip(t, v):
                f.write(f"{ti:.6f} {vi:.6f}\n")

        plt.figure(figsize=(9, 5))
        plt.plot(t, v)
        plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15)
        plt.xlabel("Time (ms)")
        plt.ylabel("Soma voltage (mV)")
        plt.title(f"L796 active validation baseline: I={int(round(current_na*1000))} pA")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(TRACE_DIR / f"{prefix}.png", dpi=200)
        plt.close()

    return t, v, spikes


def find_rheobase(soma, ais, params):
    for pA in RHEOBASE_SWEEP_PA:
        _, _, spikes = run_sim(soma, ais, pA / 1000.0, params)
        if len(spikes) >= 1:
            return pA
    return None


# ============================================================
# MAIN
# ============================================================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = json.loads(TARGETS_FILE.read_text())["active"]

    print("06 active validation: importing morphology...")
    import_morphology()
    fix_tiny_diameters(0.2)
    set_nseg_dlambda()

    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    insert_active_mechanisms(ais)

    print(f"Soma section: {soma.name()}")
    print("Finding rheobase (5 pA sweep, 0-100 pA)...")
    rheobase_pA = find_rheobase(soma, ais, BASELINE_PARAMS)
    print(f"  Rheobase = {rheobase_pA} pA")

    print("Running characterization current steps...")
    ap_features = None
    firing_pattern = "silent"
    char_current_pA = None

    for pA_na in CURRENT_STEPS_NA:
        pA = int(round(pA_na * 1000))
        t, v, spikes = run_sim(soma, ais, pA_na, BASELINE_PARAMS,
                                save_trace=True, prefix=f"baseline_I_{pA}pA")

        if ap_features is None and len(spikes) >= 1:
            feat = ap_amplitude_and_width(t, v, spikes[0])
            if feat is not None:
                ap_features = feat
                char_current_pA = pA
                firing_pattern = classify_firing_pattern(spikes)

    if ap_features is None:
        ap_features = {
            "peak_mV": math.nan, "onset_mV": math.nan,
            "amplitude_mV": math.nan, "overshoot_mV": math.nan,
            "half_width_ms": math.nan,
        }

    def in_range(val, lo, hi):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return False
        return lo <= val <= hi

    rows = [
        {
            "feature": "AP_amplitude_mV",
            "model_value": round(ap_features["amplitude_mV"], 4) if ap_features["amplitude_mV"] is not None and not math.isnan(ap_features["amplitude_mV"]) else "NaN",
            "target_min": targets["AP_amplitude_mV"]["min"],
            "target_max": targets["AP_amplitude_mV"]["max"],
            "source": targets["AP_amplitude_mV"]["source"],
            "result": "PASS" if in_range(ap_features["amplitude_mV"], targets["AP_amplitude_mV"]["min"], targets["AP_amplitude_mV"]["max"]) else "FAIL",
        },
        {
            "feature": "AP_half_width_ms",
            "model_value": round(ap_features["half_width_ms"], 4) if ap_features["half_width_ms"] is not None and not (isinstance(ap_features["half_width_ms"], float) and math.isnan(ap_features["half_width_ms"])) else "NaN",
            "target_min": targets["AP_half_width_ms"]["min"],
            "target_max": targets["AP_half_width_ms"]["max"],
            "source": targets["AP_half_width_ms"]["source"],
            "result": "PASS" if in_range(ap_features["half_width_ms"], targets["AP_half_width_ms"]["min"], targets["AP_half_width_ms"]["max"]) else "FAIL",
        },
        {
            "feature": "AP_overshoot_mV",
            "model_value": round(ap_features["overshoot_mV"], 4) if not math.isnan(ap_features["overshoot_mV"]) else "NaN",
            "target_min": targets["AP_overshoot_mV"]["min"],
            "target_max": targets["AP_overshoot_mV"]["max"],
            "source": targets["AP_overshoot_mV"]["source"],
            "result": "PASS" if in_range(ap_features["overshoot_mV"], targets["AP_overshoot_mV"]["min"], targets["AP_overshoot_mV"]["max"]) else "FAIL",
        },
        {
            "feature": "rheobase_pA",
            "model_value": rheobase_pA if rheobase_pA is not None else "NaN",
            "target_min": targets["rheobase_pA"]["min"],
            "target_max": targets["rheobase_pA"]["max"],
            "source": targets["rheobase_pA"]["source"],
            "result": "PASS" if rheobase_pA is not None and targets["rheobase_pA"]["min"] <= rheobase_pA <= targets["rheobase_pA"]["max"] else "FAIL",
        },
        {
            "feature": "firing_pattern",
            "model_value": firing_pattern,
            "target_min": "/".join(targets["firing_pattern"]["allowed"]),
            "target_max": "",
            "source": targets["firing_pattern"]["source"],
            "result": "PASS" if firing_pattern in targets["firing_pattern"]["allowed"] else "FAIL",
        },
    ]

    csv_path = OUT_DIR / "L796_active_validation.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    try:
        import pandas as pd
        md_path = OUT_DIR / "L796_active_validation.md"
        pd.DataFrame(rows).to_markdown(md_path, index=False)
    except ImportError:
        pass

    print(f"\nCharacterization current: {char_current_pA} pA")
    print("\nActive validation results (baseline model, no somatic B_Na):")
    for row in rows:
        print(f"  {row['feature']}: model={row['model_value']} "
              f"target=[{row['target_min']}, {row['target_max']}] -> {row['result']}")
    print(f"\nSaved: {csv_path}")


if __name__ == "__main__":
    main()
