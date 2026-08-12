import os
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# 07: ADD SOMATIC B_Na AND RE-BALANCE KDR FOR L796
# ============================================================
# The current L796 active model has fast Na channels (B_Na) only
# in the artificial AIS -- the soma itself has KDR/iNaP/iCaL/iKCa
# but no fast Na. That produces a somatic AP that barely
# overshoots 0 mV (~+2.6 mV) with a half-width of ~1.9 ms, both
# literature failures.
#
# This script inserts B_Na into the soma (density grid
# 0.05-0.5 S/cm2), re-balances KDR (scale grid 0.35-0.9) to keep
# repolarization in check, and scores each candidate by
# normalized error against the AP-shape literature targets
# (amplitude, half-width, overshoot, rheobase) -- NOT the old
# spike-count pattern used in Step 5.
#
# Passive parameters and all other active conductance scales
# (iNaP, iCaL, iKCa, iCaAN, AIS B_Na) are kept fixed at the
# current Step 5 best-tuned values.
# ============================================================


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
os.chdir(PROJECT_ROOT)

SWC_FILE = str(PROJECT_ROOT / "morphology" / "L796-ALT-PN.CNG.swc")
TARGETS_FILE = PROJECT_ROOT / "literature_targets" / "L796_literature_targets.json"

OUT_DIR = PROJECT_ROOT / "validation" / "tuning"
TRACE_DIR = PROJECT_ROOT / "traces" / "tuning"

# -----------------------------
# Fixed passive parameters (Step 2) -- NOT tuned here
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

# -----------------------------
# Fixed active scales (Step 5 best), everything except
# soma B_Na density and KDR_scale
# -----------------------------
FIXED_PARAMS = {
    "BNa_scale": 1.45,   # AIS B_Na, unchanged
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

BASELINE_KDR_SCALE = 0.50  # Step 5 best, used for the "before" model

# -----------------------------
# Grid search settings
# -----------------------------
SOMA_BNA_GRID = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]  # S/cm2, absolute density
# KDR_SCALE_GRID originally 0.35-0.9; every top candidate from that pass sat at
# the 0.9 edge (half-width kept improving with higher KDR), so the grid was
# widened up to 1.5 to see whether half-width can converge nearer 1 ms.
KDR_SCALE_GRID = [0.35, 0.45, 0.55, 0.65, 0.75, 0.90, 1.05, 1.20, 1.35, 1.50]

# -----------------------------
# Fast protocol for grid search (AP shape + rheobase only)
# -----------------------------
FAST_STIM_DELAY = 20.0
FAST_STIM_DUR = 150.0
FAST_TSTOP = 180.0
DT = 0.025
SPIKE_THRESHOLD = -20.0
DVDT_THRESHOLD = 10.0

COARSE_RHEOBASE_STEPS_PA = list(range(0, 105, 10))
FINE_RHEOBASE_STEPS_PA = list(range(0, 102, 2))

# -----------------------------
# Full protocol for before/after characterization
# (same timing as the Step 5 template / 06_active_validation.py)
# -----------------------------
FULL_STIM_DELAY = 100.0
FULL_STIM_DUR = 500.0
FULL_TSTOP = 900.0


# ============================================================
# MORPHOLOGY / MODEL HELPERS
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
        print("./shared/mechanisms/medlock_267056/x86_64/special -python cells/L796_projection_neuron/scripts/07_tuning.py")
        raise e


def insert_active_mechanisms(ais):
    """Same as the Step 5 template, PLUS B_Na inserted into the soma."""
    groups = section_groups()

    for sec in groups["soma"]:
        for mech in ["KDR", "iNaP", "iCaL", "iKCa", "CaIntraCellDyn", "B_Na"]:
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
    """params must contain: BNa_scale (AIS), KDR_scale, KCa_scale, CaL_scale,
    iNaP_scale, CaAN_scale, soma_BNa_density (absolute S/cm2, 0.0 = no somatic Na)."""
    groups = section_groups()

    bna_ais = params["BNa_scale"]
    kdr = params["KDR_scale"]
    kca = params["KCa_scale"]
    cal = params["CaL_scale"]
    inap = params["iNaP_scale"]
    caan = params["CaAN_scale"]
    soma_bna = params["soma_BNa_density"]

    for sec in groups["soma"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["soma_KDR"] * kdr
        if h.ismembrane("iNaP", sec=sec):
            sec.gnabar_iNaP = BASE["soma_iNaP"] * inap
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["soma_CaL"] * cal
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["soma_KCa"] * kca
        if h.ismembrane("B_Na", sec=sec):
            sec.gnabar_B_Na = soma_bna

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
        ais.gnabar_B_Na = BASE["AIS_BNa"] * bna_ais
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
    mask = (t >= spike_time - 5.0) & (t <= spike_time + window_ms)
    idx = np.where(mask)[0]
    if len(idx) < 3:
        return None

    tt = t[idx]
    vv = v[idx]
    dvdt = np.gradient(vv, tt)

    peak_local = int(np.argmax(vv))
    peak_v = float(vv[peak_local])

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
        "onset_mV": onset_v,
        "amplitude_mV": amplitude,
        "overshoot_mV": peak_v,
        "half_width_ms": half_width,
    }


def classify_firing_pattern(spike_times, stim_delay, stim_dur):
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


def run_sim(soma, ais, current_na, params, stim_delay, stim_dur, tstop):
    set_conductance_scales(ais, params)

    stim = h.IClamp(soma(0.5))
    stim.delay = stim_delay
    stim.dur = stim_dur
    stim.amp = current_na

    t_vec = h.Vector().record(h._ref_t)
    soma_vec = h.Vector().record(soma(0.5)._ref_v)

    h.dt = DT
    h.tstop = tstop
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(tstop)

    t = np.array(t_vec)
    v = np.array(soma_vec)

    stim_mask = (t >= stim_delay) & (t <= stim_delay + stim_dur)
    spikes = count_spikes(t[stim_mask], v[stim_mask])

    return t, v, spikes


def find_rheobase(soma, ais, params, steps_pA, stim_delay, stim_dur, tstop):
    for pA in steps_pA:
        _, _, spikes = run_sim(soma, ais, pA / 1000.0, params, stim_delay, stim_dur, tstop)
        if len(spikes) >= 1:
            return pA
    return None


def characterize(soma, ais, params, fast=True):
    """Find rheobase and AP-shape features for a given parameter set."""
    if fast:
        steps = COARSE_RHEOBASE_STEPS_PA
        delay, dur, tstop = FAST_STIM_DELAY, FAST_STIM_DUR, FAST_TSTOP
    else:
        steps = FINE_RHEOBASE_STEPS_PA
        delay, dur, tstop = FAST_STIM_DELAY, FAST_STIM_DUR, FAST_TSTOP

    rheobase_pA = find_rheobase(soma, ais, params, steps, delay, dur, tstop)

    if rheobase_pA is None:
        return {
            "rheobase_pA": None, "amplitude_mV": math.nan, "half_width_ms": math.nan,
            "overshoot_mV": math.nan, "firing_pattern": "silent",
        }

    t, v, spikes = run_sim(soma, ais, rheobase_pA / 1000.0, params, delay, dur, tstop)
    feat = ap_amplitude_and_width(t, v, spikes[0]) if spikes else None
    if feat is None:
        feat = {"amplitude_mV": math.nan, "half_width_ms": math.nan, "overshoot_mV": math.nan}

    return {
        "rheobase_pA": rheobase_pA,
        "amplitude_mV": feat["amplitude_mV"],
        "half_width_ms": feat["half_width_ms"],
        "overshoot_mV": feat["overshoot_mV"],
        "firing_pattern": None,  # filled in by full characterization only
    }


def full_characterize(soma, ais, params, prefix):
    """Fine rheobase + full-duration run for accurate AP shape and firing pattern.
    Used for the final before/after report only (not the grid search)."""
    rheobase_pA = find_rheobase(soma, ais, params, FINE_RHEOBASE_STEPS_PA,
                                 FAST_STIM_DELAY, FAST_STIM_DUR, FAST_TSTOP)
    if rheobase_pA is None:
        return {
            "rheobase_pA": None, "amplitude_mV": math.nan, "half_width_ms": math.nan,
            "overshoot_mV": math.nan, "firing_pattern": "silent",
        }

    t, v, spikes = run_sim(soma, ais, rheobase_pA / 1000.0, params,
                            FULL_STIM_DELAY, FULL_STIM_DUR, FULL_TSTOP)
    feat = ap_amplitude_and_width(t, v, spikes[0]) if spikes else None
    if feat is None:
        feat = {"amplitude_mV": math.nan, "half_width_ms": math.nan, "overshoot_mV": math.nan}

    pattern = classify_firing_pattern(spikes, FULL_STIM_DELAY, FULL_STIM_DUR)

    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    dat = TRACE_DIR / f"{prefix}_I_{rheobase_pA}pA.dat"
    with open(dat, "w") as f:
        f.write("time_ms soma_mV\n")
        for ti, vi in zip(t, v):
            f.write(f"{ti:.6f} {vi:.6f}\n")

    plt.figure(figsize=(9, 5))
    plt.plot(t, v)
    plt.axvspan(FULL_STIM_DELAY, FULL_STIM_DELAY + FULL_STIM_DUR, alpha=0.15)
    plt.xlabel("Time (ms)")
    plt.ylabel("Soma voltage (mV)")
    plt.title(f"{prefix}: I={rheobase_pA} pA (rheobase)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(TRACE_DIR / f"{prefix}_I_{rheobase_pA}pA.png", dpi=200)
    plt.close()

    return {
        "rheobase_pA": rheobase_pA,
        "amplitude_mV": feat["amplitude_mV"],
        "half_width_ms": feat["half_width_ms"],
        "overshoot_mV": feat["overshoot_mV"],
        "firing_pattern": pattern,
        "n_spikes": len(spikes),
    }


# ============================================================
# SCORING
# ============================================================

def normalized_error(value, lo, hi, big_penalty=10.0):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return big_penalty
    rng = hi - lo
    if lo <= value <= hi:
        return 0.0
    if value < lo:
        return (lo - value) / rng
    return (value - hi) / rng


def score_features(feat, targets):
    e_amp = normalized_error(feat["amplitude_mV"], targets["AP_amplitude_mV"]["min"], targets["AP_amplitude_mV"]["max"])
    e_hw = normalized_error(feat["half_width_ms"], targets["AP_half_width_ms"]["min"], targets["AP_half_width_ms"]["max"])
    e_over = normalized_error(feat["overshoot_mV"], targets["AP_overshoot_mV"]["min"], targets["AP_overshoot_mV"]["max"])
    e_rheo = normalized_error(feat["rheobase_pA"], targets["rheobase_pA"]["min"], targets["rheobase_pA"]["max"])
    total = e_amp + e_hw + e_over + e_rheo
    return total, {"err_amplitude": e_amp, "err_half_width": e_hw, "err_overshoot": e_over, "err_rheobase": e_rheo}


# ============================================================
# MAIN
# ============================================================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = json.loads(TARGETS_FILE.read_text())["active"]

    print("07 tuning: importing morphology...")
    import_morphology()
    fix_tiny_diameters(0.2)
    set_nseg_dlambda()

    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    insert_active_mechanisms(ais)

    print(f"Soma section: {soma.name()}")
    print(f"Grid: {len(SOMA_BNA_GRID)} soma B_Na densities x {len(KDR_SCALE_GRID)} KDR scales "
          f"= {len(SOMA_BNA_GRID) * len(KDR_SCALE_GRID)} candidates")

    results = []
    for soma_bna in SOMA_BNA_GRID:
        for kdr_scale in KDR_SCALE_GRID:
            params = dict(FIXED_PARAMS)
            params["KDR_scale"] = kdr_scale
            params["soma_BNa_density"] = soma_bna

            feat = characterize(soma, ais, params, fast=True)
            score, err = score_features(feat, targets)

            row = {
                "soma_BNa_density_S_per_cm2": soma_bna,
                "KDR_scale": kdr_scale,
                "score": score,
                **feat,
                **err,
            }
            results.append(row)

    results_sorted = sorted(results, key=lambda r: r["score"])

    all_fieldnames = sorted(set().union(*[r.keys() for r in results_sorted]))
    with open(OUT_DIR / "L796_tuning_all_candidates.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        for row in results_sorted:
            writer.writerow(row)

    best = results_sorted[0]
    best_params = {
        **FIXED_PARAMS,
        "KDR_scale": best["KDR_scale"],
        "soma_BNa_density": best["soma_BNa_density_S_per_cm2"],
    }

    print("\nBest grid candidate (fast protocol):")
    print(f"  soma B_Na density = {best['soma_BNa_density_S_per_cm2']} S/cm2")
    print(f"  KDR_scale = {best['KDR_scale']}")
    print(f"  score = {best['score']:.4f}")

    # -----------------------------
    # Full before/after characterization
    # -----------------------------
    print("\nRunning full-protocol characterization: BEFORE (no somatic B_Na)...")
    before_params = dict(FIXED_PARAMS)
    before_params["KDR_scale"] = BASELINE_KDR_SCALE
    before_params["soma_BNa_density"] = 0.0
    before_feat = full_characterize(soma, ais, before_params, prefix="before_no_somatic_BNa")

    print("Running full-protocol characterization: AFTER (tuned somatic B_Na)...")
    after_feat = full_characterize(soma, ais, best_params, prefix="after_tuned_somatic_BNa")

    before_score, before_err = score_features(before_feat, targets)
    after_score, after_err = score_features(after_feat, targets)

    def pass_fail(feat):
        checks = {
            "AP_amplitude_mV": targets["AP_amplitude_mV"]["min"] <= feat["amplitude_mV"] <= targets["AP_amplitude_mV"]["max"] if not math.isnan(feat["amplitude_mV"]) else False,
            "AP_half_width_ms": targets["AP_half_width_ms"]["min"] <= feat["half_width_ms"] <= targets["AP_half_width_ms"]["max"] if feat["half_width_ms"] is not None and not (isinstance(feat["half_width_ms"], float) and math.isnan(feat["half_width_ms"])) else False,
            "AP_overshoot_mV": targets["AP_overshoot_mV"]["min"] <= feat["overshoot_mV"] <= targets["AP_overshoot_mV"]["max"] if not math.isnan(feat["overshoot_mV"]) else False,
            "rheobase_pA": feat["rheobase_pA"] is not None and targets["rheobase_pA"]["min"] <= feat["rheobase_pA"] <= targets["rheobase_pA"]["max"],
            "firing_pattern": feat["firing_pattern"] in targets["firing_pattern"]["allowed"],
        }
        return checks

    before_pf = pass_fail(before_feat)
    after_pf = pass_fail(after_feat)

    before_after_rows = []
    for key, label in [
        ("amplitude_mV", "AP_amplitude_mV"),
        ("half_width_ms", "AP_half_width_ms"),
        ("overshoot_mV", "AP_overshoot_mV"),
        ("rheobase_pA", "rheobase_pA"),
        ("firing_pattern", "firing_pattern"),
    ]:
        before_after_rows.append({
            "feature": label,
            "before": before_feat[key],
            "before_PASS": before_pf[label],
            "after": after_feat[key],
            "after_PASS": after_pf[label],
        })

    with open(OUT_DIR / "L796_before_after_comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["feature", "before", "before_PASS", "after", "after_PASS"])
        writer.writeheader()
        for row in before_after_rows:
            writer.writerow(row)

    try:
        import pandas as pd
        pd.DataFrame(before_after_rows).to_markdown(OUT_DIR / "L796_before_after_comparison.md", index=False)
    except ImportError:
        pass

    final_params = {
        "passive_fixed": {
            "e_pas_mV": E_PAS,
            "g_pas_S_per_cm2": G_PAS,
            "cm_uF_per_cm2": CM,
            "Ra_ohm_cm": RA,
        },
        "fixed_active_scales": FIXED_PARAMS,
        "best_soma_BNa_density_S_per_cm2": best["soma_BNa_density_S_per_cm2"],
        "best_KDR_scale": best["KDR_scale"],
        "base_conductance_densities_S_per_cm2": BASE,
        "grid": {
            "soma_BNa_density_S_per_cm2": SOMA_BNA_GRID,
            "KDR_scale": KDR_SCALE_GRID,
        },
        "best_score_fast_protocol": best["score"],
        "before_after": {
            "before_no_somatic_BNa": before_feat,
            "after_tuned_somatic_BNa": after_feat,
            "before_score": before_score,
            "after_score": after_score,
        },
    }

    with open(OUT_DIR / "L796_best_tuned_parameter_set.json", "w") as f:
        json.dump(final_params, f, indent=2)

    print("\n" + "=" * 60)
    print("BEFORE (no somatic B_Na) vs AFTER (tuned somatic B_Na)")
    print("=" * 60)
    for row in before_after_rows:
        print(f"  {row['feature']}: before={row['before']} (PASS={row['before_PASS']})  "
              f"-> after={row['after']} (PASS={row['after_PASS']})")

    print(f"\nSaved:")
    print(f"  {OUT_DIR / 'L796_tuning_all_candidates.csv'}")
    print(f"  {OUT_DIR / 'L796_before_after_comparison.csv'}")
    print(f"  {OUT_DIR / 'L796_best_tuned_parameter_set.json'}")
    print(f"  {TRACE_DIR}/ (before/after traces)")


if __name__ == "__main__":
    main()
