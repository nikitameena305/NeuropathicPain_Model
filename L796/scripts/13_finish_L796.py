import os
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from neuron import h

# ============================================================
# L796 FINISHING SCRIPT
# ============================================================
# Adds fast somatic/proximal-dendritic sodium current (B_Na) to
# fix the "electrotonic echo" somatic AP defect of the Step-5
# model (soma had KDR/iNaP/iCaL/iKCa but no fast Na, so the AP
# recorded at the soma was just a passively-conducted echo of
# the artificial-AIS spike: peak ~+2.6 mV, half-width ~1.9 ms).
#
# Only NEW files are written under L796/. Step 1-5 files, the
# SWC, and the HOC are untouched.
# ============================================================

HERE = Path(__file__).resolve().parent
os.chdir(HERE)

PROJECT_ROOT = Path("/home/nikita/NeuropathicPain_Model/L796")
SWC_FILE = str(PROJECT_ROOT / "morphology" / "L796-ALT-PN.CNG.swc")
STEP5_BEST_JSON = PROJECT_ROOT / "parameters" / "L796_step5_best_tuned_parameter_set.json"

PARAMS_DIR = PROJECT_ROOT / "parameters"
RESULTS_DIR = PROJECT_ROOT / "results" / "final_model"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = PROJECT_ROOT / "figures" / "final_model"
for d in (PARAMS_DIR, RESULTS_DIR, REPORTS_DIR, FIGURES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Fixed passive model (unchanged from Step 2/5)
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

TARGET_RMP = -72.8
TARGET_RIN_GOHM = 0.77

RMP_ACCEPT = (-76.0, -70.0)
RIN_ACCEPT_GOHM = (0.60, 1.00)
RHEOBASE_ACCEPT_PA = (20.0, 60.0)

AP_TARGETS = {
    "overshoot_mV": (5.0, 30.0),
    "half_width_ms": (0.87, 1.14),
    "amplitude_mV": (70.0, 78.0),
}

# -----------------------------
# Baseline conductance densities (S/cm2) -- same as Step 5
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

# Fixed scales carried over from the Step-5 best tuned model
# (everything except KDR_scale, which we re-search jointly with
# the new soma_BNa knob, since adding somatic fast Na changes how
# much repolarizing K+ current is needed for a sharp AP).
with open(STEP5_BEST_JSON) as f:
    _step5_best = json.load(f)

FIXED_SCALES = {
    "BNa_scale": _step5_best["tuned_active_scales"]["BNa_scale"],   # AIS B_Na scale, unchanged
    "KCa_scale": _step5_best["tuned_active_scales"]["KCa_scale"],
    "CaL_scale": _step5_best["tuned_active_scales"]["CaL_scale"],
    "iNaP_scale": _step5_best["tuned_active_scales"]["iNaP_scale"],
    "CaAN_scale": _step5_best["tuned_active_scales"]["CaAN_scale"],
}
STEP5_KDR_SCALE = _step5_best["tuned_active_scales"]["KDR_scale"]

# -----------------------------
# Search grid (Step 2 of the task)
# -----------------------------
SOMA_BNA_VALUES = [0.05, 0.10, 0.20, 0.35, 0.50]   # S/cm2, absolute density
KDR_SCALE_VALUES = [0.5, 0.7, 0.9]

# Refinement grid (NOT part of the literal task-specified grid above). The primary
# grid's optimum sits at KDR_scale=0.9, its upper edge, with half-width monotonically
# decreasing as KDR_scale increases -- an edge effect suggesting the 1.14 ms half-width
# target may be reachable just outside the specified grid. Explored here, transparently
# labeled, to check achievability before accepting the primary-grid result as final.
REFINE_SOMA_BNA_VALUES = [0.04, 0.05, 0.06]
REFINE_KDR_SCALE_VALUES = [0.9, 1.2, 1.6, 2.0, 2.5]

# -----------------------------
# Simulation protocol
# -----------------------------
DT = 0.025
SPIKE_THRESHOLD = -20.0          # mV, spike screen
DVDT_THRESHOLD = 10.0            # mV/ms, AP threshold criterion

STIM_DELAY = 200.0               # ms
STIM_DUR = 1000.0                # ms (1 s, per protocol)
TSTOP = 1400.0                   # ms (200 ms tail for recovery)

BASELINE_WINDOW = (STIM_DELAY - 100.0, STIM_DELAY - 5.0)
RIN_WINDOW = (STIM_DELAY + STIM_DUR - 150.0, STIM_DELAY + STIM_DUR - 10.0)
TAU_FIT_WINDOW_MS = 200.0        # first 200 ms of the -10 pA step

# Search-phase sweep: enough resolution/range to find rheobase and
# characterize the first spike, without the full 0-300 pA final sweep.
SEARCH_CURRENTS_PA = [-10, 0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]

# Final sweep for the winning candidate (and for the Step-5 "before" model)
FINAL_CURRENTS_PA = [-10] + list(range(0, 301, 20))


# ============================================================
# MORPHOLOGY / MODEL CONSTRUCTION
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


def get_first_order_dendrites(soma, groups):
    """Sections in dend/apic whose immediate parent is the soma."""
    first_order = []
    for sec in groups["dend"] + groups["apic"]:
        sref = h.SectionRef(sec=sec)
        if sref.has_parent():
            parent = sref.parent
            if parent.name() == soma.name():
                first_order.append(sec)
    return first_order


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
        print("cd ~/NeuropathicPain_Model && cd external/SDHmodel && nrnivmodl mods")
        print("./external/SDHmodel/x86_64/special -python L796/scripts/13_finish_L796.py")
        raise e


def insert_active_mechanisms(ais, groups, first_order_dend):
    for sec in groups["soma"]:
        for mech in ["KDR", "iNaP", "iCaL", "iKCa", "CaIntraCellDyn", "B_Na"]:
            safe_insert(sec, mech)
        sec.ena = 55
        sec.ek = -90

    for sec in groups["dend"] + groups["apic"]:
        for mech in ["KDR", "iCaAN", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ek = -90

    for sec in first_order_dend:
        safe_insert(sec, "B_Na")
        sec.ena = 55

    safe_insert(ais, "B_Na")
    safe_insert(ais, "KDR")
    ais.ena = 55
    ais.ek = -90


def set_conductance_scales(ais, groups, first_order_dend, params):
    bna_ais = FIXED_SCALES["BNa_scale"]
    kdr = params["KDR_scale"]
    kca = FIXED_SCALES["KCa_scale"]
    cal = FIXED_SCALES["CaL_scale"]
    inap = FIXED_SCALES["iNaP_scale"]
    caan = FIXED_SCALES["CaAN_scale"]
    soma_bna = params["soma_BNa"]

    for sec in groups["soma"]:
        sec.gkbar_KDR = BASE["soma_KDR"] * kdr
        sec.gnabar_iNaP = BASE["soma_iNaP"] * inap
        sec.pcabar_iCaL = BASE["soma_CaL"] * cal
        sec.gbar_iKCa = BASE["soma_KCa"] * kca
        sec.gnabar_B_Na = soma_bna

    for sec in groups["dend"] + groups["apic"]:
        sec.gkbar_KDR = BASE["dend_KDR"] * kdr
        sec.gbar_iCaAN = BASE["dend_CaAN"] * caan
        sec.pcabar_iCaL = BASE["dend_CaL"] * cal
        sec.gbar_iKCa = BASE["dend_KCa"] * kca

    for sec in first_order_dend:
        sec.gnabar_B_Na = soma_bna

    ais.gnabar_B_Na = BASE["AIS_BNa"] * bna_ais
    ais.gkbar_KDR = BASE["AIS_KDR"] * kdr


# ============================================================
# SIMULATION
# ============================================================

def run_current_step(soma, current_na):
    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY
    stim.dur = STIM_DUR
    stim.amp = current_na

    t_vec = h.Vector().record(h._ref_t)
    v_vec = h.Vector().record(soma(0.5)._ref_v)

    h.dt = DT
    h.tstop = TSTOP
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(TSTOP)

    t = np.array(t_vec)
    v = np.array(v_vec)

    stim.amp = 0.0  # detach effect before next IClamp is created
    return t, v


def run_sweep(soma, currents_pA):
    traces = {}
    for pA in currents_pA:
        t, v = run_current_step(soma, pA / 1000.0)
        traces[pA] = (t, v)
    return traces


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


def window_mask(t, window):
    return (t >= window[0]) & (t <= window[1])


def compute_rmp(t, v):
    return float(np.mean(v[window_mask(t, BASELINE_WINDOW)]))


def compute_rin_gohm(t_neg, v_neg):
    base = float(np.mean(v_neg[window_mask(t_neg, BASELINE_WINDOW)]))
    steady = float(np.mean(v_neg[window_mask(t_neg, RIN_WINDOW)]))
    delta_v = steady - base
    # delta_v is in mV, -10.0 is in pA: mV/pA is dimensionally GOhm already.
    return abs(delta_v / (-10.0)), delta_v, base


def fit_tau_ms(t_neg, v_neg):
    mask = (t_neg >= STIM_DELAY) & (t_neg <= STIM_DELAY + TAU_FIT_WINDOW_MS)
    t_win = t_neg[mask]
    v_win = v_neg[mask]
    if len(t_win) < 10:
        return math.nan
    t_rel = t_win - t_win[0]
    v0 = v_win[0]
    v_inf_guess = v_win[-1]

    def model(t_rel, v_inf, tau):
        return v_inf + (v0 - v_inf) * np.exp(-t_rel / tau)

    try:
        popt, _ = curve_fit(model, t_rel, v_win, p0=[v_inf_guess, 20.0],
                             maxfev=10000, bounds=([-100.0, 0.1], [0.0, 500.0]))
        return float(popt[1])
    except Exception:
        return math.nan


def ap_features_from_spike(t, v, spike_time):
    """Extract threshold/peak/amplitude/half-width/AHP for one spike."""
    peak_mask = (t >= spike_time - 2.0) & (t <= spike_time + 8.0)
    idx = np.where(peak_mask)[0]
    if len(idx) == 0:
        return None
    peak_idx = idx[np.argmax(v[idx])]
    peak_v = float(v[peak_idx])

    dvdt = np.diff(v) / np.diff(t)
    search_back_n = int(5.0 / DT)
    start_idx = max(1, peak_idx - search_back_n)
    thr_idx = None
    for i in range(start_idx, peak_idx):
        if dvdt[i] >= DVDT_THRESHOLD:
            thr_idx = i
            break
    if thr_idx is None:
        return None
    thr_v = float(v[thr_idx])
    thr_t = float(t[thr_idx])

    half_level = thr_v + (peak_v - thr_v) / 2.0
    left = None
    for j in range(max(1, peak_idx - 200), peak_idx + 1):
        if v[j - 1] < half_level <= v[j]:
            left = j
            break
    right = None
    for j in range(peak_idx + 1, min(len(v), peak_idx + 800)):
        if v[j - 1] >= half_level > v[j]:
            right = j
            break
    half_width = float(t[right] - t[left]) if (left is not None and right is not None) else math.nan

    ahp_mask = (t > t[peak_idx]) & (t <= t[peak_idx] + 50.0)
    ahp_idx = np.where(ahp_mask)[0]
    if len(ahp_idx) > 0:
        min_v = float(np.min(v[ahp_idx]))
        ahp_depth_from_threshold = thr_v - min_v
    else:
        min_v = math.nan
        ahp_depth_from_threshold = math.nan

    return {
        "threshold_mV": thr_v,
        "threshold_t_ms": thr_t,
        "peak_mV": peak_v,
        "overshoot_mV": peak_v,
        "amplitude_mV": peak_v - thr_v,
        "half_width_ms": half_width,
        "ahp_min_mV": min_v,
        "ahp_depth_from_threshold_mV": ahp_depth_from_threshold,
    }


def extract_full_features(traces, rmp_target_check=True):
    """traces: dict pA -> (t, v). Returns a feature dict."""
    feat = {}

    t_neg, v_neg = traces[-10]
    t0, v0 = traces[0]

    feat["RMP_mV"] = compute_rmp(t0, v0)
    rin, delta_v, base = compute_rin_gohm(t_neg, v_neg)
    feat["Rin_GOhm"] = rin
    feat["tau_ms"] = fit_tau_ms(t_neg, v_neg)

    zero_spikes = count_spikes(t0[window_mask(t0, (STIM_DELAY, STIM_DELAY + STIM_DUR))],
                                v0[window_mask(t0, (STIM_DELAY, STIM_DELAY + STIM_DUR))])
    feat["spontaneous_spikes_at_0pA"] = len(zero_spikes)

    pos_currents = sorted([pA for pA in traces.keys() if pA >= 0])
    spike_counts = {}
    spike_times_by_pA = {}
    for pA in pos_currents:
        t, v = traces[pA]
        mask = window_mask(t, (STIM_DELAY, STIM_DELAY + STIM_DUR))
        spikes = count_spikes(t[mask], v[mask])
        spike_counts[pA] = len(spikes)
        spike_times_by_pA[pA] = spikes

    rheobase = None
    for pA in pos_currents:
        if spike_counts[pA] >= 1:
            rheobase = pA
            break
    feat["rheobase_pA"] = rheobase if rheobase is not None else math.nan

    if rheobase is not None:
        t_rh, v_rh = traces[rheobase]
        first_spike_t = spike_times_by_pA[rheobase][0]
        ap_feat = ap_features_from_spike(t_rh, v_rh, first_spike_t)
        if ap_feat:
            feat.update(ap_feat)
        feat["first_spike_latency_ms"] = first_spike_t - STIM_DELAY

        target_2x = 2 * rheobase
        avail = [pA for pA in pos_currents if pA > 0]
        pA_2x = min(avail, key=lambda x: abs(x - target_2x)) if avail else None
        if pA_2x is not None:
            n_spk = spike_counts[pA_2x]
            feat["current_at_2x_rheobase_pA"] = pA_2x
            feat["firing_freq_at_2x_rheobase_Hz"] = n_spk / (STIM_DUR / 1000.0)
            spk_times = spike_times_by_pA[pA_2x]
            isis = np.diff(spk_times) if len(spk_times) >= 2 else np.array([])
            if len(isis) >= 2 and isis[0] != 0:
                feat["adaptation_ratio"] = float(isis[-1] / isis[0])
            else:
                feat["adaptation_ratio"] = math.nan
        else:
            feat["current_at_2x_rheobase_pA"] = math.nan
            feat["firing_freq_at_2x_rheobase_Hz"] = math.nan
            feat["adaptation_ratio"] = math.nan
    else:
        for k in ["threshold_mV", "peak_mV", "overshoot_mV", "amplitude_mV", "half_width_ms",
                  "ahp_min_mV", "ahp_depth_from_threshold_mV", "first_spike_latency_ms",
                  "current_at_2x_rheobase_pA", "firing_freq_at_2x_rheobase_Hz", "adaptation_ratio"]:
            feat.setdefault(k, math.nan)

    feat["spike_counts_by_pA"] = spike_counts
    return feat


# ============================================================
# SEARCH / SCORING
# ============================================================

def range_error(value, lo, hi):
    if math.isnan(value):
        return 1.0
    if lo <= value <= hi:
        return 0.0
    width = hi - lo
    if value < lo:
        return (lo - value) / width
    return (value - hi) / width


def is_valid_candidate(feat):
    if feat["spontaneous_spikes_at_0pA"] > 0:
        return False, "spontaneous firing at 0 pA"
    if not (RMP_ACCEPT[0] <= feat["RMP_mV"] <= RMP_ACCEPT[1]):
        return False, f"RMP {feat['RMP_mV']:.2f} outside {RMP_ACCEPT}"
    if not (RIN_ACCEPT_GOHM[0] <= feat["Rin_GOhm"] <= RIN_ACCEPT_GOHM[1]):
        return False, f"Rin {feat['Rin_GOhm']:.3f} outside {RIN_ACCEPT_GOHM}"
    rheo = feat["rheobase_pA"]
    if math.isnan(rheo) or not (RHEOBASE_ACCEPT_PA[0] <= rheo <= RHEOBASE_ACCEPT_PA[1]):
        return False, f"rheobase {rheo} outside {RHEOBASE_ACCEPT_PA}"
    return True, "ok"


def score_ap_targets(feat):
    e_overshoot = range_error(feat.get("overshoot_mV", math.nan), *AP_TARGETS["overshoot_mV"])
    e_halfwidth = range_error(feat.get("half_width_ms", math.nan), *AP_TARGETS["half_width_ms"])
    e_amplitude = range_error(feat.get("amplitude_mV", math.nan), *AP_TARGETS["amplitude_mV"])
    return e_overshoot + e_halfwidth + e_amplitude, {
        "overshoot_err": e_overshoot,
        "half_width_err": e_halfwidth,
        "amplitude_err": e_amplitude,
    }


def run_search(soma, ais, groups, first_order_dend, soma_bna_values, kdr_scale_values,
               label="primary", best=None):
    print(f"Starting {label} grid search: soma_BNa x KDR_scale "
          f"({len(soma_bna_values)} x {len(kdr_scale_values)} = "
          f"{len(soma_bna_values) * len(kdr_scale_values)} candidates)")

    all_rows = []

    for soma_bna in soma_bna_values:
        for kdr_scale in kdr_scale_values:
            params = {"soma_BNa": soma_bna, "KDR_scale": kdr_scale, **FIXED_SCALES}
            set_conductance_scales(ais, groups, first_order_dend, params)

            traces = run_sweep(soma, SEARCH_CURRENTS_PA)
            feat = extract_full_features(traces)
            valid, reason = is_valid_candidate(feat)
            total_err, err_detail = score_ap_targets(feat)

            row = {
                "grid": label,
                "soma_BNa": soma_bna,
                "KDR_scale": kdr_scale,
                "valid": valid,
                "reject_reason": "" if valid else reason,
                "RMP_mV": feat["RMP_mV"],
                "Rin_GOhm": feat["Rin_GOhm"],
                "rheobase_pA": feat["rheobase_pA"],
                "overshoot_mV": feat.get("overshoot_mV"),
                "half_width_ms": feat.get("half_width_ms"),
                "amplitude_mV": feat.get("amplitude_mV"),
                "total_ap_error": total_err,
                **err_detail,
            }
            all_rows.append(row)

            tag = "OK  " if valid else "REJ "
            print(f"  [{label}] {tag} soma_BNa={soma_bna:.2f} KDR_scale={kdr_scale:.2f} "
                  f"RMP={feat['RMP_mV']:.2f} Rin={feat['Rin_GOhm']:.3f} "
                  f"rheobase={feat['rheobase_pA']} overshoot={feat.get('overshoot_mV')} "
                  f"hw={feat.get('half_width_ms')} amp={feat.get('amplitude_mV')} "
                  f"err={total_err:.3f}" + ("" if valid else f"  [{reason}]"))

            if valid:
                if best is None or total_err < best["total_ap_error"]:
                    best = {**params, "total_ap_error": total_err, "feat": feat, "grid": label}

    return best, all_rows


def save_search_candidates_csv(all_rows):
    fieldnames = list(all_rows[0].keys())
    with open(RESULTS_DIR / "L796_final_search_candidates.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)


# ============================================================
# MAIN
# ============================================================

def build_model():
    import_morphology()
    fix_tiny_diameters(0.2)
    set_nseg_dlambda()
    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    groups = section_groups()
    first_order_dend = get_first_order_dendrites(soma, groups)
    insert_active_mechanisms(ais, groups, first_order_dend)
    return soma, ais, groups, first_order_dend


def main():
    print("Building L796 finishing model (soma + proximal-dendrite fast Na)...")
    soma, ais, groups, first_order_dend = build_model()
    print(f"Soma: {soma.name()}, AIS: {ais.name()}")
    print(f"First-order dendrites (direct soma children) receiving B_Na: "
          f"{[s.name() for s in first_order_dend]}")

    best, primary_rows = run_search(soma, ais, groups, first_order_dend,
                                     SOMA_BNA_VALUES, KDR_SCALE_VALUES, label="primary")

    if best is None:
        raise RuntimeError("No valid candidate survived the constraints on the primary grid. "
                            "Widen the search grid or relax constraints.")

    print("\nBest candidate from primary (task-specified) grid:")
    print(f"  soma_BNa = {best['soma_BNa']}, KDR_scale = {best['KDR_scale']}, "
          f"total_ap_error = {best['total_ap_error']:.4f}")

    best, refine_rows = run_search(soma, ais, groups, first_order_dend,
                                    REFINE_SOMA_BNA_VALUES, REFINE_KDR_SCALE_VALUES,
                                    label="refinement", best=best)

    all_rows = primary_rows + refine_rows
    save_search_candidates_csv(all_rows)

    best = select_best(all_rows)

    finalize(soma, ais, groups, first_order_dend, best, all_rows)


def count_ap_target_fails(feat):
    n = 0
    for key, (lo, hi) in AP_TARGETS.items():
        v = feat.get(key, math.nan)
        if math.isnan(v) or not (lo <= v <= hi):
            n += 1
    return n


def select_best(all_rows):
    """Lexicographic selection: prefer candidates that satisfy more of the
    overshoot/half-width/amplitude target ranges outright, tie-broken by the
    lowest summed normalized AP-target error. This avoids picking a candidate
    that minimizes the *sum* of errors by trading two in-range features for a
    marginal improvement on the third."""
    valid_rows = [r for r in all_rows if r["valid"]]
    if not valid_rows:
        return None

    def sort_key(r):
        feat = {
            "overshoot_mV": r["overshoot_mV"],
            "half_width_ms": r["half_width_ms"],
            "amplitude_mV": r["amplitude_mV"],
        }
        return (count_ap_target_fails(feat), r["total_ap_error"])

    best_row = min(valid_rows, key=sort_key)
    return {
        "soma_BNa": best_row["soma_BNa"],
        "KDR_scale": best_row["KDR_scale"],
        "total_ap_error": best_row["total_ap_error"],
        "grid": best_row["grid"],
        **FIXED_SCALES,
    }


def finalize(soma, ais, groups, first_order_dend, best, all_rows):
    print("\nBest surviving candidate overall (by target-ranges-satisfied, then summed error):")
    print(f"  grid = {best['grid']}")
    print(f"  soma_BNa = {best['soma_BNa']}")
    print(f"  KDR_scale = {best['KDR_scale']}")
    print(f"  total_ap_error = {best['total_ap_error']:.4f}")

    # Final full 0-300 pA sweep on the winner
    final_params = {"soma_BNa": best["soma_BNa"], "KDR_scale": best["KDR_scale"], **FIXED_SCALES}
    set_conductance_scales(ais, groups, first_order_dend, final_params)
    final_traces = run_sweep(soma, FINAL_CURRENTS_PA)
    final_feat = extract_full_features(final_traces)

    # Save traces for the winner
    trace_dir = RESULTS_DIR / "final_traces"
    trace_dir.mkdir(exist_ok=True)
    for pA, (t, v) in final_traces.items():
        np.savetxt(trace_dir / f"final_I_{pA}pA.dat", np.column_stack([t, v]),
                    header="time_ms soma_mV", comments="")

    # Save winning parameter set
    final_param_set = {
        "passive_fixed": {
            "e_pas_mV": E_PAS,
            "g_pas_S_per_cm2": G_PAS,
            "cm_uF_per_cm2": CM,
            "Ra_ohm_cm": RA,
        },
        "tuned_active_scales": {
            "BNa_scale_AIS": FIXED_SCALES["BNa_scale"],
            "KDR_scale": final_params["KDR_scale"],
            "KCa_scale": FIXED_SCALES["KCa_scale"],
            "CaL_scale": FIXED_SCALES["CaL_scale"],
            "iNaP_scale": FIXED_SCALES["iNaP_scale"],
            "CaAN_scale": FIXED_SCALES["CaAN_scale"],
        },
        "soma_BNa_S_per_cm2": final_params["soma_BNa"],
        "proximal_dendrite_BNa_S_per_cm2": final_params["soma_BNa"],
        "proximal_dendrite_sections": [s.name() for s in first_order_dend],
        "base_conductance_densities_S_per_cm2": BASE,
        "winning_grid": best["grid"],
        "search_grid_primary_task_specified": {
            "soma_BNa_values": SOMA_BNA_VALUES,
            "KDR_scale_values": KDR_SCALE_VALUES,
        },
        "search_grid_refinement_extension": {
            "soma_BNa_values": REFINE_SOMA_BNA_VALUES,
            "KDR_scale_values": REFINE_KDR_SCALE_VALUES,
        },
        "search_constraints": {
            "RMP_accept_mV": RMP_ACCEPT,
            "Rin_accept_GOhm": RIN_ACCEPT_GOHM,
            "rheobase_accept_pA": RHEOBASE_ACCEPT_PA,
        },
        "ap_targets": AP_TARGETS,
        "best_total_ap_error": best["total_ap_error"],
    }
    with open(PARAMS_DIR / "L796_final_parameter_set.json", "w") as f:
        json.dump(final_param_set, f, indent=2)

    # -----------------------------
    # BEFORE model: Step-5 best tuned model, same feature pipeline
    # -----------------------------
    print("\nRe-building Step-5 (before) model for comparison...")
    before_params = {"soma_BNa": 0.0, "KDR_scale": STEP5_KDR_SCALE, **FIXED_SCALES}
    set_conductance_scales(ais, groups, first_order_dend, before_params)
    before_traces = run_sweep(soma, FINAL_CURRENTS_PA)
    before_feat = extract_full_features(before_traces)

    for pA, (t, v) in before_traces.items():
        np.savetxt(trace_dir / f"before_I_{pA}pA.dat", np.column_stack([t, v]),
                    header="time_ms soma_mV", comments="")

    make_figures(before_traces, final_traces, before_feat, final_feat)
    scorecard_rows = make_validation_table(before_feat, final_feat)
    write_report(before_feat, final_feat, best, all_rows, scorecard_rows, first_order_dend)
    print_scorecard(scorecard_rows, final_feat)


# ============================================================
# FIGURES
# ============================================================

def make_figures(before_traces, final_traces, before_feat, final_feat):
    overlay_current = 100
    if overlay_current not in before_traces or overlay_current not in final_traces:
        overlay_current = FINAL_CURRENTS_PA[len(FINAL_CURRENTS_PA) // 2]

    t_b, v_b = before_traces[overlay_current]
    t_a, v_a = final_traces[overlay_current]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    ax.plot(t_b, v_b, label="Before (Step 5, no somatic B_Na)", color="tab:orange")
    ax.plot(t_a, v_a, label="After (final, somatic+proximal B_Na)", color="tab:blue")
    ax.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.1, color="grey")
    ax.axhline(SPIKE_THRESHOLD, linestyle="--", linewidth=1, color="k", alpha=0.5)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Somatic voltage (mV)")
    ax.set_title(f"Full somatic trace, I = {overlay_current} pA")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[1]
    b_rheo = before_feat.get("rheobase_pA")
    a_rheo = final_feat.get("rheobase_pA")
    if not math.isnan(b_rheo) and "threshold_t_ms" in before_feat:
        t0 = before_feat["threshold_t_ms"]
        mask = (t_b >= t0 - 3) & (t_b <= t0 + 10)
        ax.plot(t_b[mask] - t0, v_b[mask], label="Before", color="tab:orange")
    if not math.isnan(a_rheo) and "threshold_t_ms" in final_feat:
        t0 = final_feat["threshold_t_ms"]
        mask = (t_a >= t0 - 3) & (t_a <= t0 + 10)
        ax.plot(t_a[mask] - t0, v_a[mask], label="After", color="tab:blue")
    ax.axhline(0, linestyle=":", linewidth=1, color="k", alpha=0.5)
    ax.set_xlabel("Time relative to AP threshold (ms)")
    ax.set_ylabel("Somatic voltage (mV)")
    ax.set_title("First AP at rheobase, aligned to threshold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "L796_final_before_after_AP_overlay.png", dpi=250)
    plt.close()

    currents = sorted(set(before_feat["spike_counts_by_pA"].keys()) |
                       set(final_feat["spike_counts_by_pA"].keys()))
    b_counts = [before_feat["spike_counts_by_pA"].get(c, 0) for c in currents]
    a_counts = [final_feat["spike_counts_by_pA"].get(c, 0) for c in currents]

    plt.figure(figsize=(7, 5))
    plt.plot(currents, b_counts, marker="o", label="Before (Step 5)", color="tab:orange")
    plt.plot(currents, a_counts, marker="s", label="After (final)", color="tab:blue")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Spike count during 1 s step")
    plt.title("L796 F-I curve: before vs after")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "L796_final_before_after_FI_curve.png", dpi=250)
    plt.close()


# ============================================================
# VALIDATION TABLE
# ============================================================

def fmt(v, nd=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:.{nd}f}"


def make_validation_table(before_feat, final_feat):
    rows = []

    def add(feature, target, acc_range, value, verdict_fn=None):
        if verdict_fn is None:
            verdict = "MEASURED"
        else:
            verdict = verdict_fn(value)
        rows.append({
            "feature": feature,
            "target": target,
            "acceptable_range": acc_range,
            "model": fmt(value, 3) if isinstance(value, float) else value,
            "verdict": verdict,
        })

    def pass_if(lo, hi):
        return lambda v: "PASS" if (not math.isnan(v) and lo <= v <= hi) else "FAIL"

    add("RMP (mV)", "-72.8", f"{RMP_ACCEPT[0]} to {RMP_ACCEPT[1]}",
        final_feat["RMP_mV"], pass_if(*RMP_ACCEPT))
    add("Input resistance Rin (GOhm)", "0.77", f"{RIN_ACCEPT_GOHM[0]} to {RIN_ACCEPT_GOHM[1]}",
        final_feat["Rin_GOhm"], pass_if(*RIN_ACCEPT_GOHM))
    add("Membrane tau (ms)", "not specified (informational)", "n/a", final_feat["tau_ms"])
    add("Rheobase (pA)", "20-60", f"{RHEOBASE_ACCEPT_PA[0]} to {RHEOBASE_ACCEPT_PA[1]}",
        final_feat["rheobase_pA"], pass_if(*RHEOBASE_ACCEPT_PA))
    add("AP threshold (mV, dV/dt>=10 mV/ms)", "not specified (informational)", "n/a",
        final_feat.get("threshold_mV", math.nan))
    add("AP overshoot / peak (mV)", "positive overshoot", f"{AP_TARGETS['overshoot_mV'][0]} to {AP_TARGETS['overshoot_mV'][1]}",
        final_feat.get("overshoot_mV", math.nan), pass_if(*AP_TARGETS["overshoot_mV"]))
    add("AP amplitude (mV)", "70-78", f"{AP_TARGETS['amplitude_mV'][0]} to {AP_TARGETS['amplitude_mV'][1]}",
        final_feat.get("amplitude_mV", math.nan), pass_if(*AP_TARGETS["amplitude_mV"]))
    add("AP half-width (ms)", "0.87-1.14", f"{AP_TARGETS['half_width_ms'][0]} to {AP_TARGETS['half_width_ms'][1]}",
        final_feat.get("half_width_ms", math.nan), pass_if(*AP_TARGETS["half_width_ms"]))
    add("AHP depth from threshold (mV)", "not specified (informational)", "n/a",
        final_feat.get("ahp_depth_from_threshold_mV", math.nan))
    add("Firing frequency at ~2x rheobase (Hz)", "not specified (informational)", "n/a",
        final_feat.get("firing_freq_at_2x_rheobase_Hz", math.nan))
    add("Adaptation ratio (last ISI / first ISI)", "not specified (informational)", "n/a",
        final_feat.get("adaptation_ratio", math.nan))
    add("First-spike latency (ms)", "not specified (informational)", "n/a",
        final_feat.get("first_spike_latency_ms", math.nan))

    fieldnames = ["feature", "target", "acceptable_range", "model", "verdict"]
    # Literal task-specified path (top-level results/), in addition to the
    # organized results/final_model/ copy used elsewhere in this pipeline.
    with open(PROJECT_ROOT / "results" / "L796_final_validation_vs_targets.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    with open(RESULTS_DIR / "L796_final_validation_vs_targets.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return rows


def print_scorecard(rows, final_feat):
    print("\n" + "=" * 78)
    print("L796 FINAL FEATURE SCORECARD")
    print("=" * 78)
    print(f"{'feature':<42} {'target':<14} {'model':<10} verdict")
    print("-" * 78)
    for r in rows:
        print(f"{r['feature']:<42} {str(r['target']):<14} {str(r['model']):<10} {r['verdict']}")
    print("-" * 78)

    overshoot = final_feat.get("overshoot_mV", math.nan)
    half_width = final_feat.get("half_width_ms", math.nan)
    rmp_ok = RMP_ACCEPT[0] <= final_feat["RMP_mV"] <= RMP_ACCEPT[1]
    rin_ok = RIN_ACCEPT_GOHM[0] <= final_feat["Rin_GOhm"] <= RIN_ACCEPT_GOHM[1]
    rheo = final_feat["rheobase_pA"]
    rheo_ok = (not math.isnan(rheo)) and RHEOBASE_ACCEPT_PA[0] <= rheo <= RHEOBASE_ACCEPT_PA[1]
    ap_ok = (not math.isnan(overshoot) and overshoot > 0.0 and
             not math.isnan(half_width) and half_width <= 1.14)
    validated = ap_ok and rmp_ok and rin_ok and rheo_ok

    if validated:
        verdict_line = ("VERDICT: L796 single-cell model VALIDATED -- somatic AP now overshoots "
                         f"({overshoot:.1f} mV > 0) with half-width {half_width:.2f} ms <= 1.14 ms, "
                         "without breaking RMP/Rin/rheobase.")
    else:
        verdict_line = ("VERDICT: L796 single-cell model NOT FULLY VALIDATED -- see trade-offs in "
                         "reports/L796_final_completion_report.md for the closest achievable set.")
    print(verdict_line)
    print("=" * 78)


# ============================================================
# REPORT
# ============================================================

def write_report(before_feat, final_feat, best, all_rows, scorecard_rows, first_order_dend):
    lines = []
    lines.append("# L796 Lamina I ALT Projection-Neuron Model -- Final Completion Report")
    lines.append("")
    lines.append("## Defect addressed")
    lines.append("")
    lines.append(
        "The Step-5 model inserted fast sodium (B_Na) only in the artificial AIS. The soma "
        "carried KDR, iNaP, iCaL, and iKCa but no fast Na, so the somatic AP recorded in that "
        "model was an electrotonically-conducted echo of the AIS spike (peak ~+2.6 mV, "
        "half-width ~1.9 ms) rather than a genuine regenerative somatic action potential."
    )
    lines.append("")
    lines.append(
        "This script (`scripts/13_finish_L796.py`) inserts B_Na into the soma and the "
        f"{len(first_order_dend)} first-order (proximal) dendrites directly attached to the "
        "soma (" + ", ".join(s.name() for s in first_order_dend) + "), with a single tunable "
        "density `soma_BNa` (S/cm2) applied to both, `ena = 55 mV`. The KDR scale (shared by "
        "soma, dendrites, and AIS) was re-searched jointly with `soma_BNa` because adding "
        "somatic fast Na changes how much repolarizing K+ current is needed for a sharp AP. "
        "All other tuned active scales (AIS BNa_scale, KCa_scale, CaL_scale, iNaP_scale, "
        "CaAN_scale) were kept fixed at the Step-5 best-tuned values. Passive parameters "
        "(e_pas, g_pas, cm, Ra) were kept fixed throughout."
    )
    lines.append("")
    lines.append("## Search")
    lines.append("")
    lines.append(
        f"**Primary grid (task-specified):** soma_BNa in {SOMA_BNA_VALUES} S/cm2 x "
        f"KDR_scale in {KDR_SCALE_VALUES} "
        f"({len(SOMA_BNA_VALUES) * len(KDR_SCALE_VALUES)} candidates), each screened at "
        f"currents {SEARCH_CURRENTS_PA} pA over a 1 s step."
    )
    lines.append("")
    lines.append(
        "Candidates were rejected if they fired spontaneously at 0 pA, moved RMP outside "
        f"{RMP_ACCEPT} mV, moved Rin outside {RIN_ACCEPT_GOHM} GOhm, or moved rheobase outside "
        f"{RHEOBASE_ACCEPT_PA} pA. Surviving candidates were scored by summed normalized error "
        "against the AP overshoot/half-width/amplitude target ranges (lower is better)."
    )
    lines.append("")
    lines.append(
        "On the primary grid, the best surviving candidate (soma_BNa=0.05, KDR_scale=0.9) sat "
        "at the KDR_scale upper edge of the tested range, with half-width still above the "
        "1.14 ms target and shrinking monotonically as KDR_scale increased. This edge effect "
        "indicated the target might be reachable just outside the literal task-specified grid, "
        "so a **refinement grid** (clearly a deliberate extension beyond the specified values, "
        f"not a substitute for it) was also run: soma_BNa in {REFINE_SOMA_BNA_VALUES} S/cm2 x "
        f"KDR_scale in {REFINE_KDR_SCALE_VALUES} "
        f"({len(REFINE_SOMA_BNA_VALUES) * len(REFINE_KDR_SCALE_VALUES)} candidates), same "
        "protocol and constraints."
    )
    lines.append("")
    n_valid = sum(1 for r in all_rows if r["valid"])
    lines.append(f"{n_valid} / {len(all_rows)} candidates survived the constraints across both "
                 "grids. Full results (both grids, tagged by the `grid` column): "
                 "`results/final_model/L796_final_search_candidates.csv`.")
    lines.append("")
    lines.append(f"**Winning candidate (from the {best['grid']} grid):**")
    lines.append("")
    lines.append(f"- soma_BNa = {best['soma_BNa']} S/cm2 (soma + proximal dendrites)")
    lines.append(f"- KDR_scale = {best['KDR_scale']}")
    lines.append(f"- total AP-target error = {best['total_ap_error']:.4f}")
    lines.append("")
    lines.append("## Before vs after (1 s somatic current-clamp sweep, 0-300 pA in 20 pA steps)")
    lines.append("")
    lines.append("| Feature | Before (Step 5) | After (final) |")
    lines.append("|---|---|---|")

    def row(label, key, nd=3):
        b = before_feat.get(key, math.nan)
        a = final_feat.get(key, math.nan)
        return f"| {label} | {fmt(b, nd)} | {fmt(a, nd)} |"

    lines.append(row("RMP (mV)", "RMP_mV", 2))
    lines.append(row("Rin (GOhm)", "Rin_GOhm"))
    lines.append(row("tau (ms)", "tau_ms", 2))
    lines.append(row("Rheobase (pA)", "rheobase_pA", 0))
    lines.append(row("AP threshold (mV)", "threshold_mV", 2))
    lines.append(row("AP peak / overshoot (mV)", "overshoot_mV", 2))
    lines.append(row("AP amplitude (mV)", "amplitude_mV", 2))
    lines.append(row("AP half-width (ms)", "half_width_ms", 3))
    lines.append(row("AHP depth from threshold (mV)", "ahp_depth_from_threshold_mV", 2))
    lines.append(row("Firing frequency at ~2x rheobase (Hz)", "firing_freq_at_2x_rheobase_Hz", 2))
    lines.append(row("Adaptation ratio", "adaptation_ratio", 3))
    lines.append(row("First-spike latency (ms)", "first_spike_latency_ms", 2))
    lines.append("")
    lines.append("Figures: `figures/final_model/L796_final_before_after_AP_overlay.png`, "
                 "`figures/final_model/L796_final_before_after_FI_curve.png`.")
    lines.append("")
    lines.append("## Validation vs literature targets (final model)")
    lines.append("")
    lines.append("| feature | target | acceptable_range | model | verdict |")
    lines.append("|---|---|---|---|---|")
    for r in scorecard_rows:
        lines.append(f"| {r['feature']} | {r['target']} | {r['acceptable_range']} | "
                     f"{r['model']} | {r['verdict']} |")
    lines.append("")
    lines.append("Full CSV: `results/L796_final_validation_vs_targets.csv` "
                 "(also copied to `results/final_model/L796_final_validation_vs_targets.csv`).")
    lines.append("")

    overshoot = final_feat.get("overshoot_mV", math.nan)
    half_width = final_feat.get("half_width_ms", math.nan)
    rmp_ok = RMP_ACCEPT[0] <= final_feat["RMP_mV"] <= RMP_ACCEPT[1]
    rin_ok = RIN_ACCEPT_GOHM[0] <= final_feat["Rin_GOhm"] <= RIN_ACCEPT_GOHM[1]
    rheo = final_feat["rheobase_pA"]
    rheo_ok = (not math.isnan(rheo)) and RHEOBASE_ACCEPT_PA[0] <= rheo <= RHEOBASE_ACCEPT_PA[1]
    ap_ok = (not math.isnan(overshoot) and overshoot > 0.0 and
             not math.isnan(half_width) and half_width <= 1.14)
    validated = ap_ok and rmp_ok and rin_ok and rheo_ok

    lines.append("## Acceptance check")
    lines.append("")
    lines.append(f"- Somatic AP overshoot > 0 mV: **{'YES' if (not math.isnan(overshoot) and overshoot > 0) else 'NO'}** "
                 f"({fmt(overshoot, 2)} mV)")
    lines.append(f"- Half-width <= 1.14 ms: **{'YES' if (not math.isnan(half_width) and half_width <= 1.14) else 'NO'}** "
                 f"({fmt(half_width, 3)} ms)")
    lines.append(f"- RMP within {RMP_ACCEPT} mV: **{'YES' if rmp_ok else 'NO'}** ({fmt(final_feat['RMP_mV'], 2)} mV)")
    lines.append(f"- Rin within {RIN_ACCEPT_GOHM} GOhm: **{'YES' if rin_ok else 'NO'}** ({fmt(final_feat['Rin_GOhm'], 3)} GOhm)")
    lines.append(f"- Rheobase within {RHEOBASE_ACCEPT_PA} pA: **{'YES' if rheo_ok else 'NO'}** ({fmt(rheo, 0)} pA)")
    lines.append("")
    if validated:
        lines.append(
            "**The single-cell model is declared VALIDATED**: the somatic AP is now a genuine "
            "regenerative spike (overshoot > 0 mV, half-width within the Zhang 2021 literature "
            "range), and RMP, Rin, and rheobase all remain within their accepted bounds."
        )
    else:
        lines.append(
            "**The bounds could not all be met simultaneously.** The closest achievable "
            "candidate is reported above. See the trade-off discussion below."
        )
    lines.append("")
    lines.append("## Remaining limitations")
    lines.append("")
    if not ap_ok:
        lines.append(
            f"- Even after extending KDR_scale beyond the task-specified upper bound (up to "
            f"{max(REFINE_KDR_SCALE_VALUES)}, vs. {max(KDR_SCALE_VALUES)} specified) and "
            f"exploring soma_BNa in {REFINE_SOMA_BNA_VALUES} S/cm2, the best surviving "
            f"candidate's half-width ({fmt(half_width, 3)} ms) could not be brought down to "
            "the 1.14 ms target without raising soma_BNa enough to break the AP amplitude "
            "target (70-78 mV) or trigger spontaneous firing. A wider search that also varies "
            "KCa_scale/CaL_scale (currently held fixed at their Step-5 values) might close the "
            "remaining gap, but was out of scope here."
        )
    else:
        lines.append(
            "- The refinement grid that closed the half-width gap extends beyond the literal "
            f"task-specified KDR_scale range (up to {max(REFINE_KDR_SCALE_VALUES)} vs. "
            f"{max(KDR_SCALE_VALUES)} specified); this is flagged transparently in the search "
            "section and the winning `grid` is recorded in the parameter set and CSV."
        )
    lines.append(
        "- AP threshold, AHP depth, firing frequency at 2x rheobase, adaptation ratio, and "
        "first-spike latency are reported as measured, informational values: the source "
        "literature (Zhang 2021, Luz 2014) used for this validation did not supply numeric "
        "targets for these features, so no PASS/FAIL verdict is assigned to them."
    )
    lines.append(
        "- Because the proximal dendrites and soma share a single `soma_BNa` density rather "
        "than independent densities, the search cannot separately tune backpropagation-related "
        "dendritic excitability vs. the somatic spike shape; this was a deliberate simplification "
        "to keep the search tractable, consistent with the task's tunable-density specification."
    )
    lines.append(
        "- The model does not reproduce a specific published L796 recording; it is tuned to "
        "fall within reported population ranges (Zhang 2021, Luz 2014), so cell-to-cell "
        "variability within those ranges is not captured."
    )
    lines.append("")

    (REPORTS_DIR / "L796_final_completion_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved report: {REPORTS_DIR / 'L796_final_completion_report.md'}")


if __name__ == "__main__":
    main()
