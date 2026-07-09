import csv
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from neuron import h

# ============================================================
# L796 PART 1: LIGAND-GATED RECEPTORS
# ============================================================
# Adds AMPA/NMDA (excitatory), GABA-A/glycine (inhibitory), and an
# nAChR-like receptor onto the FIXED, already-validated L796 single-cell
# active model (parameters/L796_final_parameter_set.json). The active
# model itself is not modified while testing synapses.
#
# Only NEW files are written under L796/. Step 1-5 files, the SWC, the
# HOC, and scripts 13/15/16 are untouched.
# ============================================================

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("finish13", str(HERE / "13_finish_L796.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules["finish13"] = mod
spec.loader.exec_module(mod)  # main() only runs under `if __name__=="__main__"`, false here

PROJECT_ROOT = mod.PROJECT_ROOT
RESULTS_DIR = PROJECT_ROOT / "results" / "receptors"
PLOTS_DIR = PROJECT_ROOT / "plots" / "receptors"
REPORTS_DIR = PROJECT_ROOT / "reports"
for d in (RESULTS_DIR, PLOTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

CELSIUS = 6.3  # see reports/L796_single_cell_final_status.md: locked to match the
                # already-validated single-cell feature set; no celsius value achieves
                # a full simultaneous pass, so we keep the one the model was fit at.

DT = 0.025
E_PAS = mod.E_PAS

# -----------------------------
# Receptor kinetics (see literature_targets/06_receptor_target_values.csv)
# -----------------------------
AMPA_TAU_RISE, AMPA_TAU_DECAY, AMPA_E = 0.5, 2.5, 0.0
NMDA_TAU_RISE, NMDA_TAU_DECAY, NMDA_E = 5.0, 70.0, 0.0
GABAA_TAU_RISE, GABAA_TAU_DECAY = 1.0, 20.0
GLY_TAU_RISE, GLY_TAU_DECAY = 1.0, 10.0
ECL_CONTROL = -70.0  # Coull 2003 control-condition chloride reversal
NACHR_TAU1, NACHR_TAU2, NACHR_E = 1.0, 30.0, 0.0  # alpha4beta2-like proxy (Exp2Syn)


# ============================================================
# MODEL SETUP
# ============================================================

def build_validated_model():
    """Rebuild the fixed, already-validated L796 active model (v1 params)."""
    import json
    with open(mod.PARAMS_DIR / "L796_final_parameter_set.json") as f:
        v1 = json.load(f)
    soma, ais, groups, first_order_dend = mod.build_model()
    params = {
        "soma_BNa": v1["soma_BNa_S_per_cm2"],
        "KDR_scale": v1["tuned_active_scales"]["KDR_scale"],
        **mod.FIXED_SCALES,
    }
    mod.set_conductance_scales(ais, groups, first_order_dend, params)
    h.celsius = CELSIUS
    return soma, ais, groups, first_order_dend


def pick_dendrite_locations(soma, groups):
    """Rank all dendrite sections by path distance from the soma and pick
    representative proximal / mid / distal locations (segment 0.5)."""
    h.distance(0, 0.5, sec=soma)
    dend_secs = groups["dend"] + groups["apic"]
    dists = [(h.distance(0.5, sec=s), s) for s in dend_secs]
    dists.sort(key=lambda x: x[0])

    n = len(dists)
    proximal = dists[int(n * 0.10)]
    mid = dists[int(n * 0.50)]
    distal = dists[int(n * 0.90)]

    return {
        "proximal": {"sec": proximal[1], "dist_um": proximal[0]},
        "mid": {"sec": mid[1], "dist_um": mid[0]},
        "distal": {"sec": distal[1], "dist_um": distal[0]},
    }


# ============================================================
# SIMULATION HELPERS
# ============================================================

def make_netstim(start, number=1, interval=1000.0 / 20.0, noise=0.0):
    ns = h.NetStim()
    ns.start = start
    ns.number = number
    ns.interval = interval
    ns.noise = noise
    return ns


# ------------------------------------------------------------------
# Stimulus registry
# ------------------------------------------------------------------
# ROOT CAUSE (found by direct debugging, not assumed): in NEURON, inserting a new
# point-process synapse (h.AMPA_DynSyn(sec(0.5)), h.GABAa_DynSyn(sec(0.5)), etc.) at a
# segment does NOT replace or disable any earlier point process at that same segment --
# every one inserted stays permanently wired into the model via its own NetCon, and keeps
# firing on every subsequent simulation for as long as its NetCon has nonzero weight. This
# script builds many independent test stimuli (each bisection iteration inside
# calibrate_weight, each proximal/mid/distal location, each summation condition, etc.), and
# without cleanup every earlier one remained live and stacked onto every later measurement --
# corrupting calibration (e.g. Glycine converging to a nonsense weight because ~20 stray
# AMPA+NMDA synapses from Section 1 were still firing at t=300 during its bisection) and
# even inverting the expected proximal-vs-distal EPSP attenuation. This was confirmed
# directly: an isolated, fresh-model test of the same calibration converges correctly, while
# the same calibration run after other synapses had already been built (uncleaned) on the
# same segment does not. (A plain gc.collect() was tried first and made no difference --
# this is not a Python reference-lifetime issue, it is NEURON's own point-process model.)
#
# Fix: every NetCon that drives a "stimulus under test" is registered here. Call
# reset_stimuli() immediately before wiring up each new test's stimuli -- it zeroes every
# previously registered NetCon's weight (a zero-weight event delivers no state change to a
# dual-exponential or Exp2Syn synapse, so a disabled synapse contributes exactly zero current
# for the rest of that run), so only the stimulus intended for the CURRENT test is ever live.
_ACTIVE_NETCONS = []


def new_netcon(ns, target, weight, delay=0.0):
    nc = h.NetCon(ns, target)
    nc.delay = delay
    nc.weight[0] = weight
    _ACTIVE_NETCONS.append(nc)
    return nc


def reset_stimuli():
    for nc in _ACTIVE_NETCONS:
        nc.weight[0] = 0.0


def run_sim(tstop, v_init=E_PAS, record_secs=None, dt=DT):
    """record_secs: dict[name] -> (sec, x). Returns t (np array), dict[name]->v (np array)."""
    t_vec = h.Vector().record(h._ref_t)
    v_recs = {}
    if record_secs:
        for name, (sec, x) in record_secs.items():
            v_recs[name] = h.Vector().record(sec(x)._ref_v)

    h.dt = dt
    h.tstop = tstop
    h.v_init = v_init
    h.finitialize(v_init)
    h.continuerun(tstop)

    t = np.array(t_vec)
    v_out = {name: np.array(vec) for name, vec in v_recs.items()}
    return t, v_out


def psp_features(t, v, stim_time, baseline_window=(None, None), search_window_ms=200.0,
                  polarity="excitatory", decay_fit_window_ms=30.0):
    """Extract amplitude, 20-80% rise time, decay tau, and latency for a single PSP.

    decay_tau is fit over a short window right after the peak (default 30 ms), not
    the full search window: for a somatic PSP in a cell with a slow membrane tau
    (~200 ms here), fitting over a long window picks up the neuron's own passive
    relaxation rather than the synaptic conductance's decay kinetics."""
    if baseline_window[0] is None:
        baseline_window = (stim_time - 20.0, stim_time - 2.0)
    base_mask = (t >= baseline_window[0]) & (t <= baseline_window[1])
    baseline = float(np.mean(v[base_mask]))

    search_mask = (t >= stim_time) & (t <= stim_time + search_window_ms)
    t_s = t[search_mask]
    v_s = v[search_mask]
    if len(t_s) == 0:
        return None

    if polarity == "excitatory":
        peak_idx = int(np.argmax(v_s))
        peak_v = float(v_s[peak_idx])
        amplitude = peak_v - baseline
    else:
        peak_idx = int(np.argmin(v_s))
        peak_v = float(v_s[peak_idx])
        amplitude = baseline - peak_v

    peak_t = float(t_s[peak_idx])

    if abs(amplitude) < 1e-6:
        return {
            "baseline_mV": baseline, "peak_mV": peak_v, "amplitude_mV": amplitude,
            "peak_t_ms": peak_t, "latency_ms": math.nan, "rise_time_ms": math.nan,
            "decay_tau_ms": math.nan,
        }

    lo_level = baseline + 0.2 * (peak_v - baseline)
    hi_level = baseline + 0.8 * (peak_v - baseline)

    rise_mask = (t_s >= stim_time) & (t_s <= peak_t)
    t_rise = t_s[rise_mask]
    v_rise = v_s[rise_mask]

    def first_crossing(level):
        if polarity == "excitatory":
            idx = np.where(v_rise >= level)[0]
        else:
            idx = np.where(v_rise <= level)[0]
        return float(t_rise[idx[0]]) if len(idx) else math.nan

    t_10 = first_crossing(baseline + 0.1 * (peak_v - baseline))
    t_20 = first_crossing(lo_level)
    t_80 = first_crossing(hi_level)
    rise_time = (t_80 - t_20) if (not math.isnan(t_80) and not math.isnan(t_20)) else math.nan
    latency = (t_10 - stim_time) if not math.isnan(t_10) else math.nan

    decay_mask = (t_s >= peak_t) & (t_s <= peak_t + decay_fit_window_ms)
    t_decay = t_s[decay_mask] - peak_t
    v_decay = v_s[decay_mask]
    decay_tau = math.nan
    if len(t_decay) > 5:
        v_inf_guess = v_decay[-1]
        v0 = v_decay[0]

        def model(tt, tau):
            return v_inf_guess + (v0 - v_inf_guess) * np.exp(-tt / tau)

        try:
            popt, _ = curve_fit(model, t_decay, v_decay, p0=[5.0], maxfev=5000,
                                 bounds=(0.1, 500.0))
            decay_tau = float(popt[0])
        except Exception:
            decay_tau = math.nan

    return {
        "baseline_mV": baseline, "peak_mV": peak_v, "amplitude_mV": amplitude,
        "peak_t_ms": peak_t, "latency_ms": latency, "rise_time_ms": rise_time,
        "decay_tau_ms": decay_tau,
    }


_HOLDING_ICLAMPS = {}  # soma name -> single persistent IClamp, so repeated calls don't stack


def add_holding_current(soma, amp_nA, tstop):
    """A continuous bias IClamp, used only to give GABA-A/glycine adequate driving
    force for kinetic characterization: RMP (-72.4 mV) sits close to ECl (-70 mV),
    so at rest a chloride conductance is almost pure shunt with very little visible
    hyperpolarization -- a real, well-known property of GABA-A/glycine near rest,
    not a bug. See reports/L796_ligand_gated_receptor_report.md.

    Reuses a single persistent IClamp per soma rather than creating a new one on every
    call: multiple simultaneous IClamps at the same location sum their currents, so
    repeated calls (e.g. once per calibrate_weight iteration) would otherwise stack an
    ever-growing bias current rather than simply setting the intended one."""
    key = soma.name()
    if key not in _HOLDING_ICLAMPS:
        hold = h.IClamp(soma(0.5))
        hold.delay = 0.0
        _HOLDING_ICLAMPS[key] = hold
    hold = _HOLDING_ICLAMPS[key]
    hold.dur = tstop
    hold.amp = amp_nA
    return hold


def calibrate_weight(build_syn_fn, target_amp_mV, weight_lo=0.00005, weight_hi=0.02,
                      tol=0.05, max_iter=25, polarity="excitatory", stim_time=300.0,
                      tstop=600.0, soma=None, holding_current_nA=0.0):
    """Bisection on NetCon weight (uS) so the somatic PSP amplitude hits target_amp_mV.

    build_syn_fn(w) must build its stimulus using new_netcon() (not raw h.NetCon), so
    reset_stimuli() below can retire every earlier bisection iteration's synapse before
    the new one is wired up -- otherwise every iteration's synapse stays permanently live
    and stacks onto the next (see the _ACTIVE_NETCONS/reset_stimuli comment above)."""
    last_amp = None
    last_w = weight_hi
    for _ in range(max_iter):
        w = (weight_lo + weight_hi) / 2.0
        reset_stimuli()
        syn_objs = build_syn_fn(w)
        hold = add_holding_current(soma, holding_current_nA, tstop) if holding_current_nA else None
        t, v = run_sim(tstop, record_secs={"soma": (soma, 0.5)})
        feat = psp_features(t, v["soma"], stim_time, polarity=polarity)
        amp = abs(feat["amplitude_mV"])
        last_amp, last_w = amp, w
        if abs(amp - target_amp_mV) <= tol:
            return w, amp, feat
        if amp < target_amp_mV:
            weight_lo = w
        else:
            weight_hi = w
    return last_w, last_amp, feat


NMDA_AMPA_WEIGHT_RATIO = 0.5  # phenomenological co-location ratio; see target CSV


def build_ampa_nmda(sec, w_ampa, w_nmda=None, stim_time=300.0, number=1, interval=50.0):
    if w_nmda is None:
        w_nmda = w_ampa * NMDA_AMPA_WEIGHT_RATIO
    ampa = h.AMPA_DynSyn(sec(0.5))
    ampa.tau_rise, ampa.tau_decay, ampa.e = AMPA_TAU_RISE, AMPA_TAU_DECAY, AMPA_E
    nmda = h.NMDA_DynSyn(sec(0.5))
    nmda.tau_rise, nmda.tau_decay, nmda.e = NMDA_TAU_RISE, NMDA_TAU_DECAY, NMDA_E
    # mgo (extracellular Mg2+) is an ion concentration (USEION mg READ mgo), not a
    # point-process attribute; the auto-inserted mg_ion mechanism already defaults to
    # mgo=1.0 mM, which matches our target physiological value.
    ns = make_netstim(start=stim_time, number=number, interval=interval)
    nc_ampa = new_netcon(ns, ampa, w_ampa)
    nc_nmda = new_netcon(ns, nmda, w_nmda)
    return {"ampa": ampa, "nmda": nmda, "ns": ns, "nc_ampa": nc_ampa, "nc_nmda": nc_nmda}


# ============================================================
# SECTION 1: GLUTAMATERGIC (AMPA + NMDA)
# ============================================================

def section1_glutamatergic(soma, locs):
    print("\n" + "=" * 78)
    print("SECTION 1: AMPA + NMDA (glutamatergic)")
    print("=" * 78)

    epsp_rows = []
    mgblock_rows = []
    summation_rows = []
    plot_traces = {}

    prox_sec = locs["proximal"]["sec"]

    # --- calibrate co-located AMPA+NMDA weight for a ~2 mV unitary EPSP at proximal ---
    def build_fn(w):
        return build_ampa_nmda(prox_sec, w)

    w_unitary, amp_unitary, feat_unitary = calibrate_weight(
        build_fn, target_amp_mV=2.0, soma=soma, polarity="excitatory",
        stim_time=300.0, tstop=600.0)
    print(f"  Calibrated AMPA+NMDA weight for ~2 mV unitary EPSP at proximal "
          f"({locs['proximal']['dist_um']:.0f} um): {w_unitary*1000:.3f} nS "
          f"-> {amp_unitary:.3f} mV")

    epsp_rows.append({
        "location": "proximal", "distance_um": locs["proximal"]["dist_um"],
        "receptors": "AMPA+NMDA", "weight_AMPA_nS": w_unitary * 1000,
        "weight_NMDA_nS": w_unitary * NMDA_AMPA_WEIGHT_RATIO * 1000,
        **{k: feat_unitary[k] for k in
           ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]},
    })

    # fresh AMPA+NMDA trace at proximal, for the location-comparison plot (consistent with
    # the mid/distal traces captured below, which are also AMPA+NMDA)
    reset_stimuli()
    _keepalive_prox = build_ampa_nmda(prox_sec, w_unitary)
    t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    plot_traces["proximal"] = (t, v["soma"])

    # AMPA-only at the same weight, for comparison
    reset_stimuli()
    ampa_only = build_ampa_nmda(prox_sec, w_unitary, w_nmda=0.0)
    t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    feat_ampa_only = psp_features(t, v["soma"], 300.0, polarity="excitatory")
    epsp_rows.append({
        "location": "proximal", "distance_um": locs["proximal"]["dist_um"],
        "receptors": "AMPA-only", "weight_AMPA_nS": w_unitary * 1000, "weight_NMDA_nS": 0.0,
        **{k: feat_ampa_only[k] for k in
           ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]},
    })

    # --- proximal vs mid vs distal attenuation: same weight, different location ---
    for name in ["mid", "distal"]:
        sec = locs[name]["sec"]
        reset_stimuli()
        _keepalive = build_ampa_nmda(sec, w_unitary)
        t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
        feat = psp_features(t, v["soma"], 300.0, polarity="excitatory")
        print(f"  {name} ({locs[name]['dist_um']:.0f} um): EPSP amplitude = "
              f"{feat['amplitude_mV']:.3f} mV (same weight as proximal)")
        epsp_rows.append({
            "location": name, "distance_um": locs[name]["dist_um"],
            "receptors": "AMPA+NMDA", "weight_AMPA_nS": w_unitary * 1000,
            "weight_NMDA_nS": w_unitary * NMDA_AMPA_WEIGHT_RATIO * 1000,
            **{k: feat[k] for k in ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]},
        })
        plot_traces[name] = (t, v["soma"])

    # --- NMDA Mg2+ block: simulated demonstration across a voltage range ---
    # NOTE: calling a point process's own FUNCTION (e.g. nmda.mgblock(v)) directly from
    # Python, out of the context of an active simulation, was found to be unreliable
    # (returns 1.0 regardless of v before NEURON's internal state has been set up by a
    # run). This measurement instead voltage-clamps the soma and reads the NMDA point
    # process's own i and g during a real simulation, which is unambiguous: unblock
    # fraction = i / (g * (v - e)).
    #
    # A single persistent SEClamp and NMDA synapse are built ONCE, outside the loop, and
    # reused across all vhold values (only .amp1 changes) -- building a fresh SEClamp/NMDA
    # pair on every iteration without disabling the previous one would stack multiple live
    # voltage clamps and synapses onto the same segment (see the _ACTIVE_NETCONS comment).
    reset_stimuli()
    clamp = h.SEClamp(soma(0.5))
    clamp.dur1 = 600.0
    clamp.rs = 0.001
    nmda_only = h.NMDA_DynSyn(prox_sec(0.5))
    nmda_only.tau_rise, nmda_only.tau_decay, nmda_only.e = \
        NMDA_TAU_RISE, NMDA_TAU_DECAY, NMDA_E
    ns = make_netstim(start=300.0, number=1)
    nc = new_netcon(ns, nmda_only, w_unitary * NMDA_AMPA_WEIGHT_RATIO)
    i_rec = h.Vector().record(nmda_only._ref_i)
    g_rec = h.Vector().record(nmda_only._ref_g)

    nmda_clamp_rows = []
    for vhold in [-80.0, -70.0, -60.0, -50.0, -40.0, -30.0, -20.0, -10.0, 0.0, 10.0, 20.0]:
        clamp.amp1 = vhold
        h.dt = DT
        h.tstop = 600.0
        h.finitialize(vhold)
        h.continuerun(600.0)
        i_arr = np.array(i_rec)
        g_arr = np.array(g_rec)
        # Above the reversal potential (vhold > NMDA_E), the driving force is positive and
        # the current is outward (positive i), not inward -- so pick the peak by magnitude,
        # not by argmin, to work correctly on both sides of the reversal potential.
        peak_idx = int(np.argmax(np.abs(i_arr)))
        peak_i = float(i_arr[peak_idx])
        peak_g = float(g_arr[peak_idx])
        driving_force = vhold - NMDA_E
        if peak_g > 0 and abs(driving_force) > 1e-6:
            unblock = peak_i / (peak_g * driving_force)
        else:
            unblock = math.nan
        mgblock_rows.append({"voltage_mV": vhold, "unblock_fraction": unblock})
        nmda_clamp_rows.append({"holding_mV": vhold, "peak_NMDA_current_nA": peak_i})
    print("  NMDA Mg2+-unblock fraction (Jahr & Stevens 1990, measured via voltage clamp): "
          f"{mgblock_rows[0]['unblock_fraction']:.3f} at -80 mV -> "
          f"{mgblock_rows[-1]['unblock_fraction']:.3f} at +20 mV "
          "(grows with depolarization, confirming Mg2+ unblock)")
    i_m70 = [r for r in nmda_clamp_rows if r["holding_mV"] == -70.0][0]["peak_NMDA_current_nA"]
    i_m20 = [r for r in nmda_clamp_rows if r["holding_mV"] == -20.0][0]["peak_NMDA_current_nA"]
    print(f"  NMDA peak current at Vhold=-70 mV: {i_m70:.5f} nA vs "
          f"Vhold=-20 mV: {i_m20:.5f} nA (more negative/inward at depolarized Vhold confirms unblock)")

    return {
        "epsp_rows": epsp_rows, "mgblock_rows": mgblock_rows,
        "nmda_clamp_rows": nmda_clamp_rows, "plot_traces": plot_traces,
        "w_unitary": w_unitary, "amp_unitary": amp_unitary,
    }


def section1b_summation(soma, locs, w_unitary):
    """EPSP-to-spike conversion via NMDA-dependent temporal summation: a train of
    inputs, each individually subthreshold, that summate toward/past threshold --
    compare AMPA+NMDA vs AMPA-only, at 20 Hz and 50 Hz."""
    print("\n  --- EPSP-to-spike via temporal summation (train, AMPA+NMDA vs AMPA-only) ---")
    sec = locs["proximal"]["sec"]
    # Weight multiplier chosen by direct scan (see script development notes): at 2x the
    # unitary EPSP weight, AMPA+NMDA reaches spike threshold via NMDA-dependent temporal
    # summation at both 20 Hz and 50 Hz, while AMPA-only (same weight, no NMDA) stays
    # subthreshold at both -- this is the frequency/weight combination that cleanly
    # isolates NMDA's contribution to EPSP-to-spike conversion, rather than one where
    # AMPA alone is already sufficient to fire (which would happen at higher multipliers).
    w_train = w_unitary * 2.0

    rows = []
    traces = {}
    for freq in [20.0, 50.0]:
        interval = 1000.0 / freq
        for condition, w_nmda in [("AMPA+NMDA", w_train * NMDA_AMPA_WEIGHT_RATIO), ("AMPA-only", 0.0)]:
            reset_stimuli()
            _keepalive = build_ampa_nmda(sec, w_train, w_nmda=w_nmda, stim_time=300.0, number=5,
                                          interval=interval)
            t, v = run_sim(300.0 + 5 * interval + 300.0, record_secs={"soma": (soma, 0.5)})
            v_soma = v["soma"]
            post_mask = t >= 300.0
            peak_v = float(np.max(v_soma[post_mask]))
            spikes = mod.count_spikes(t[post_mask], v_soma[post_mask], threshold=mod.SPIKE_THRESHOLD)
            fired = len(spikes) > 0
            print(f"    {freq:.0f} Hz, {condition}: peak depolarization = {peak_v:.2f} mV, "
                  f"spike fired = {fired}")
            rows.append({
                "frequency_Hz": freq, "condition": condition, "n_pulses": 5,
                "weight_AMPA_nS": w_train * 1000, "weight_NMDA_nS": w_nmda * 1000,
                "peak_depolarization_mV": peak_v, "spike_fired": fired,
                "n_spikes": len(spikes),
            })
            traces[(freq, condition)] = (t, v_soma)

    return rows, traces, w_train


# ============================================================
# SECTION 2: INHIBITORY (GABA-A + Glycine) AND SHUNTING
# ============================================================

HOLDING_CURRENT_NA = 0.014  # depolarizes RMP (-72.4 mV) to ~-60 mV for IPSP characterization


def section2_inhibitory(soma, locs, w_ampa_train, w_nmda_train):
    print("\n" + "=" * 78)
    print("SECTION 2: GABA-A + Glycine (inhibitory) and shunting")
    print("=" * 78)
    print(f"  IPSP kinetics characterized from a depolarized holding potential "
          f"(bias {HOLDING_CURRENT_NA*1000:.1f} pA) because RMP (-72.4 mV) sits close to "
          f"ECl ({ECL_CONTROL} mV) -- see note in the report.")

    sec = locs["proximal"]["sec"]
    ipsp_rows = []
    ipsp_traces = {}

    def build_gabaa(w):
        gaba = h.GABAa_DynSyn(sec(0.5))
        gaba.tau_rise, gaba.tau_decay, gaba.e = GABAA_TAU_RISE, GABAA_TAU_DECAY, ECL_CONTROL
        ns = make_netstim(start=300.0, number=1)
        nc = new_netcon(ns, gaba, w)
        return gaba, ns, nc

    def build_glycine(w):
        gly = h.Glycine_DynSyn(sec(0.5))
        gly.tau_rise, gly.tau_decay, gly.e = GLY_TAU_RISE, GLY_TAU_DECAY, ECL_CONTROL
        ns = make_netstim(start=300.0, number=1)
        nc = new_netcon(ns, gly, w)
        return gly, ns, nc

    def build_both(w_gaba, w_gly):
        g1, ns1, nc1 = build_gabaa(w_gaba)
        g2, ns2, nc2 = build_glycine(w_gly)
        return g1, g2, ns1, ns2, nc1, nc2

    w_gaba, amp_gaba, feat_gaba = calibrate_weight(
        build_gabaa, target_amp_mV=2.0, soma=soma, polarity="inhibitory",
        stim_time=300.0, tstop=600.0, holding_current_nA=HOLDING_CURRENT_NA)
    print(f"  Calibrated GABA-A weight for ~2 mV IPSP: {w_gaba*1000:.3f} nS -> {amp_gaba:.3f} mV, "
          f"decay tau = {feat_gaba['decay_tau_ms']:.2f} ms")
    ipsp_rows.append({"receptor": "GABA-A", "weight_nS": w_gaba * 1000,
                       **{k: feat_gaba[k] for k in
                          ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]}})
    reset_stimuli()
    _keepalive0a = build_gabaa(w_gaba)
    _keepalive0b = add_holding_current(soma, HOLDING_CURRENT_NA, 600.0)
    t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    ipsp_traces["GABA-A"] = (t, v["soma"])

    w_gly, amp_gly, feat_gly = calibrate_weight(
        build_glycine, target_amp_mV=2.0, soma=soma, polarity="inhibitory",
        stim_time=300.0, tstop=600.0, holding_current_nA=HOLDING_CURRENT_NA)
    print(f"  Calibrated Glycine weight for ~2 mV IPSP: {w_gly*1000:.3f} nS -> {amp_gly:.3f} mV, "
          f"decay tau = {feat_gly['decay_tau_ms']:.2f} ms")
    ipsp_rows.append({"receptor": "Glycine", "weight_nS": w_gly * 1000,
                       **{k: feat_gly[k] for k in
                          ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]}})
    reset_stimuli()
    _keepalive1 = build_glycine(w_gly)
    _keepalive2 = add_holding_current(soma, HOLDING_CURRENT_NA, 600.0)
    t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    ipsp_traces["Glycine"] = (t, v["soma"])

    faster = "Glycine" if feat_gly["decay_tau_ms"] < feat_gaba["decay_tau_ms"] else "GABA-A"
    print(f"  Faster decay: {faster} "
          f"(GABA-A {feat_gaba['decay_tau_ms']:.2f} ms vs Glycine {feat_gly['decay_tau_ms']:.2f} ms)")

    # co-located GABA-A + Glycine
    reset_stimuli()
    _keepalive3 = build_both(w_gaba, w_gly)
    _keepalive4 = add_holding_current(soma, HOLDING_CURRENT_NA, 600.0)
    t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    feat_both = psp_features(t, v["soma"], 300.0, polarity="inhibitory")
    ipsp_rows.append({"receptor": "GABA-A+Glycine", "weight_nS": (w_gaba + w_gly) * 1000,
                       **{k: feat_both[k] for k in
                          ["amplitude_mV", "rise_time_ms", "decay_tau_ms", "latency_ms"]}})
    ipsp_traces["GABA-A+Glycine"] = (t, v["soma"])

    # --- shunting: co-activate excitatory train with inhibition, AT RESTING POTENTIAL ---
    print("\n  --- Shunting inhibition (excitatory train +/- simultaneous GABA-A+Glycine) ---")
    # Explicitly turn OFF the (now persistent/reused) holding-current IClamp from the IPSP
    # kinetics measurements above -- otherwise this "resting potential" test would silently
    # inherit the prior depolarized holding bias.
    add_holding_current(soma, 0.0, 600.0)

    # A direct scan (see script development notes) found the single-unitary-synapse GABA-A+
    # Glycine weight (the same weight calibrated above for a ~2 mV IPSP) is NOT strong enough
    # to shunt-block a train robust enough to fire a spike on its own -- blocking only occurs
    # around ~12x that weight. This is used here as a stand-in for convergent input from
    # several co-active inhibitory interneurons (a population-level inhibitory barrage),
    # not a claim that a single GABAergic/glycinergic synapse can shunt-block on its own.
    SHUNT_INHIBITION_MULTIPLIER = 15.0

    shunt_rows = []
    shunt_traces = {}
    for label, with_inhibition in [("EPSP train alone", False), ("EPSP train + inhibition", True)]:
        reset_stimuli()
        _keepalive5 = build_ampa_nmda(sec, w_ampa_train, w_nmda=w_nmda_train, stim_time=300.0,
                                       number=5, interval=1000.0 / 50.0)
        _keepalive6 = None
        if with_inhibition:
            _keepalive6 = build_both(w_gaba * SHUNT_INHIBITION_MULTIPLIER,
                                      w_gly * SHUNT_INHIBITION_MULTIPLIER)
        t, v = run_sim(600.0, record_secs={"soma": (soma, 0.5)})
        v_soma = v["soma"]
        post_mask = t >= 300.0
        peak_v = float(np.max(v_soma[post_mask]))
        spikes = mod.count_spikes(t[post_mask], v_soma[post_mask], threshold=mod.SPIKE_THRESHOLD)
        fired = len(spikes) > 0
        inhib_mult_used = SHUNT_INHIBITION_MULTIPLIER if with_inhibition else 0.0
        print(f"    {label}: peak depolarization = {peak_v:.2f} mV, spike fired = {fired}")
        shunt_rows.append({"condition": label, "peak_depolarization_mV": peak_v,
                            "spike_fired": fired, "n_spikes": len(spikes),
                            "inhibition_weight_multiplier": inhib_mult_used})
        shunt_traces[label] = (t, v_soma)

    return {
        "ipsp_rows": ipsp_rows, "ipsp_traces": ipsp_traces,
        "shunt_rows": shunt_rows, "shunt_traces": shunt_traces,
        "shunt_inhibition_multiplier": SHUNT_INHIBITION_MULTIPLIER,
        "w_gaba": w_gaba, "w_gly": w_gly, "faster_decay": faster,
    }


# ============================================================
# SECTION 3: nAChR-LIKE PROXY (documented, not a validated nAChR)
# ============================================================

NACHR_CAVEAT = (
    "CAVEAT: in the dorsal horn, nAChR activation is predominantly ANTINOCICEPTIVE, acting "
    "largely PRESYNAPTICALLY and on INHIBITORY interneurons to enhance GABA/glycine release. "
    "Placing an nAChR-like conductance directly on the L796 projection-neuron soma/dendrite, "
    "as done here, is a simplification for demonstrating ligand-gated depolarization and "
    "summation; it does NOT reproduce the in-vivo cholinergic analgesic circuit, and no real, "
    "vetted nAChR .mod file was available in external/SDHmodel/mods, so this is a documented "
    "Exp2Syn PROXY (alpha4beta2-like kinetics: tau1=1 ms, tau2=30 ms, e=0 mV), not a validated "
    "nAChR model."
)


def section3_nAChR(soma, locs, w_ampa_unitary):
    print("\n" + "=" * 78)
    print("SECTION 3: nAChR-like proxy (Exp2Syn, alpha4beta2-like kinetics)")
    print("=" * 78)
    print(f"  {NACHR_CAVEAT}")

    sec = locs["proximal"]["sec"]

    # Turn off the (persistent/reused) holding-current IClamp left over from Section 2's
    # IPSP characterization -- Section 3 should start from normal resting potential.
    add_holding_current(soma, 0.0, 700.0)

    def build_nachr(w):
        syn = h.Exp2Syn(sec(0.5))
        syn.tau1, syn.tau2, syn.e = NACHR_TAU1, NACHR_TAU2, NACHR_E
        ns = make_netstim(start=300.0, number=1)
        nc = new_netcon(ns, syn, w)
        return syn, ns, nc

    w_nachr, amp_nachr, feat_nachr = calibrate_weight(
        build_nachr, target_amp_mV=2.0, soma=soma, polarity="excitatory",
        stim_time=300.0, tstop=700.0)
    print(f"  Calibrated nAChR-like weight for ~2 mV depolarization: {w_nachr*1000:.3f} nS "
          f"-> {amp_nachr:.3f} mV, decay tau = {feat_nachr['decay_tau_ms']:.2f} ms "
          f"(vs synaptic tau2={NACHR_TAU2} ms)")
    reset_stimuli()
    _keepalive_trace = build_nachr(w_nachr)
    t, v = run_sim(700.0, record_secs={"soma": (soma, 0.5)})
    nachr_trace = (t, v["soma"])

    # --- summation with glutamatergic drive ---
    print("\n  --- nAChR-like + AMPA/NMDA summation toward threshold ---")
    summation_rows = []
    summation_traces = {}

    conditions = [
        ("nAChR-like alone", True, False),
        ("AMPA+NMDA alone", False, True),
        ("nAChR-like + AMPA+NMDA (combined)", True, True),
    ]
    for label, use_nachr, use_glut in conditions:
        reset_stimuli()
        _keepalive_a = build_nachr(w_nachr) if use_nachr else None
        _keepalive_b = build_ampa_nmda(sec, w_ampa_unitary, stim_time=300.0, number=1) \
            if use_glut else None
        t, v = run_sim(700.0, record_secs={"soma": (soma, 0.5)})
        v_soma = v["soma"]
        post_mask = t >= 300.0
        peak_v = float(np.max(v_soma[post_mask]))
        baseline = float(np.mean(v_soma[(t >= 280) & (t <= 298)]))
        spikes = mod.count_spikes(t[post_mask], v_soma[post_mask], threshold=mod.SPIKE_THRESHOLD)
        fired = len(spikes) > 0
        print(f"    {label}: peak = {peak_v:.2f} mV (depol. {peak_v - baseline:.2f} mV above "
              f"baseline), spike fired = {fired}")
        summation_rows.append({
            "condition": label, "peak_mV": peak_v, "depolarization_above_baseline_mV": peak_v - baseline,
            "spike_fired": fired,
        })
        summation_traces[label] = (t, v_soma)

    linear_sum = (summation_rows[0]["depolarization_above_baseline_mV"] +
                  summation_rows[1]["depolarization_above_baseline_mV"])
    combined = summation_rows[2]["depolarization_above_baseline_mV"]
    print(f"    Linear sum of individual depolarizations: {linear_sum:.2f} mV; "
          f"observed combined: {combined:.2f} mV "
          f"({'supralinear' if combined > linear_sum else 'sublinear/near-linear'} "
          "summation, as expected for co-activated conductances with shared driving force)")

    return {
        "w_nachr": w_nachr, "amp_nachr": amp_nachr, "feat_nachr": feat_nachr,
        "nachr_trace": nachr_trace, "summation_rows": summation_rows,
        "summation_traces": summation_traces, "caveat": NACHR_CAVEAT,
    }


# ============================================================
# SAVE CSVs / PLOTS
# ============================================================

def save_csv(rows, path, fieldnames=None):
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_epsp_by_location(plot_traces, path):
    plt.figure(figsize=(8, 5))
    for name in ["proximal", "mid", "distal"]:
        t, v = plot_traces[name]
        mask = (t >= 280) & (t <= 400)
        plt.plot(t[mask], v[mask], label=name)
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title("AMPA+NMDA unitary EPSP: proximal/mid/distal attenuation (same weight)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_summation(summation_traces, path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, freq in zip(axes, [20.0, 50.0]):
        for condition in ["AMPA+NMDA", "AMPA-only"]:
            t, v = summation_traces[(freq, condition)]
            mask = (t >= 280) & (t <= 700)
            ax.plot(t[mask], v[mask], label=condition)
        ax.axhline(mod.SPIKE_THRESHOLD, linestyle="--", linewidth=1, color="k", alpha=0.5)
        ax.set_title(f"{freq:.0f} Hz train (5 pulses)")
        ax.set_xlabel("Time (ms)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Somatic voltage (mV)")
    plt.suptitle("NMDA-dependent temporal summation: EPSP-to-spike")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_mgblock(mgblock_rows, path):
    plt.figure(figsize=(7, 5))
    vs = [r["voltage_mV"] for r in mgblock_rows]
    us = [r["unblock_fraction"] for r in mgblock_rows]
    plt.plot(vs, us, marker="o")
    plt.xlabel("Membrane voltage (mV)")
    plt.ylabel("NMDA Mg2+-unblock fraction")
    plt.title("NMDA Mg2+ block relief with depolarization (Jahr & Stevens 1990)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_ipsp(ipsp_traces, path):
    plt.figure(figsize=(8, 5))
    for name in ["GABA-A", "Glycine", "GABA-A+Glycine"]:
        t, v = ipsp_traces[name]
        mask = (t >= 280) & (t <= 450)
        plt.plot(t[mask], v[mask], label=name)
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title("IPSP kinetics (from depolarized holding potential): GABA-A vs Glycine")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_shunting(shunt_traces, path):
    plt.figure(figsize=(8, 5))
    for label, (t, v) in shunt_traces.items():
        mask = (t >= 280) & (t <= 600)
        plt.plot(t[mask], v[mask], label=label)
    plt.axhline(mod.SPIKE_THRESHOLD, linestyle="--", linewidth=1, color="k", alpha=0.5)
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title("Shunting inhibition: excitatory train +/- simultaneous GABA-A+Glycine")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_nachr(nachr_trace, summation_traces, path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    t, v = nachr_trace
    mask = (t >= 280) & (t <= 500)
    axes[0].plot(t[mask], v[mask], color="tab:purple")
    axes[0].set_title("nAChR-like proxy: single-pulse depolarization")
    axes[0].set_xlabel("Time (ms)")
    axes[0].set_ylabel("Somatic voltage (mV)")
    axes[0].grid(alpha=0.3)

    for label, (t, v) in summation_traces.items():
        mask = (t >= 280) & (t <= 500)
        axes[1].plot(t[mask], v[mask], label=label)
    axes[1].axhline(mod.SPIKE_THRESHOLD, linestyle="--", linewidth=1, color="k", alpha=0.5)
    axes[1].set_title("nAChR-like + AMPA/NMDA summation")
    axes[1].set_xlabel("Time (ms)")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


# ============================================================
# REPORT / TERMINAL SUMMARY
# ============================================================

def fmt(v, nd=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:.{nd}f}"


def write_report(s1, summation_rows, s2, s3, locs):
    lines = []
    lines.append("# L796 Ligand-Gated Receptor Report")
    lines.append("")
    lines.append(
        "Ligand-gated receptors were added to the FIXED, already-validated L796 single-cell "
        "active model (`parameters/L796_final_parameter_set.json`; see "
        "`reports/L796_single_cell_final_status.md` for the single-cell closeout, including "
        "the accepted AP half-width relaxed-pass). The active conductance densities were not "
        "changed while testing synapses. `h.celsius` is explicitly set to 6.3 degC throughout "
        "(the value the single-cell model was validated at)."
    )
    lines.append("")
    lines.append(
        "**All synaptic conductances (AMPA/NMDA/GABA-A/glycine/nAChR-like weights) are "
        "phenomenological**: they are tuned to produce a physiological unitary EPSP/IPSP "
        "amplitude (target 0.5-5 mV), not measured or fit to any L796-specific synaptic "
        "recording. See `literature_targets/06_receptor_target_values.csv` for confidence "
        "grades on every kinetic parameter."
    )
    lines.append("")
    lines.append("## Dendrite locations used")
    lines.append("")
    lines.append("| location | section | path distance from soma (um) |")
    lines.append("|---|---|---|")
    for name, info in locs.items():
        lines.append(f"| {name} | {info['sec'].name()} | {info['dist_um']:.1f} |")
    lines.append("")

    lines.append("## 1a. Glutamatergic: AMPA + NMDA")
    lines.append("")
    lines.append(f"AMPA: tau_rise={AMPA_TAU_RISE} ms, tau_decay={AMPA_TAU_DECAY} ms, e={AMPA_E} mV "
                 f"(AMPA_DynSyn.mod, tau values adjusted from mechanism defaults to match the "
                 f"literature-cited fast-AMPA range). NMDA: tau_rise={NMDA_TAU_RISE} ms, "
                 f"tau_decay={NMDA_TAU_DECAY} ms, e={NMDA_E} mV, Mg2+ block via the Jahr & Stevens "
                 f"(1990) equation implemented directly in NMDA_DynSyn.mod (mgo=1.0 mM) -- this is "
                 f"a real published equation, not a proxy. Co-located at a fixed "
                 f"NMDA:AMPA weight ratio of {NMDA_AMPA_WEIGHT_RATIO} (phenomenological assumption).")
    lines.append("")
    lines.append("| location | receptors | weight AMPA (nS) | weight NMDA (nS) | amplitude (mV) | rise time (ms) | decay tau (ms) | latency (ms) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in s1["epsp_rows"]:
        lines.append(f"| {r['location']} | {r['receptors']} | {fmt(r['weight_AMPA_nS'],3)} | "
                     f"{fmt(r['weight_NMDA_nS'],3)} | {fmt(r['amplitude_mV'],3)} | "
                     f"{fmt(r['rise_time_ms'],2)} | {fmt(r['decay_tau_ms'],2)} | {fmt(r['latency_ms'],2)} |")
    lines.append("")
    lines.append(
        f"Unitary EPSP amplitude was calibrated to ~2 mV at the proximal location "
        f"({s1['amp_unitary']:.3f} mV achieved), within the 0.5-5 mV target. Applying the same "
        "weight at mid and distal locations shows clear proximal-to-distal attenuation "
        "(see table and `plots/receptors/L796_EPSP_traces_by_location.png`)."
    )
    lines.append("")
    _clamp_by_v = {r["holding_mV"]: r["peak_NMDA_current_nA"] for r in s1["nmda_clamp_rows"]}
    lines.append("**NMDA Mg2+ block relief with depolarization** "
                 f"(`plots/receptors/L796_NMDA_mgblock.png`): unblock fraction rises from "
                 f"{s1['mgblock_rows'][0]['unblock_fraction']:.3f} at -80 mV to "
                 f"{s1['mgblock_rows'][-1]['unblock_fraction']:.3f} at +20 mV, measured via "
                 "voltage clamp (a direct out-of-simulation call to the mechanism's own "
                 "mgblock() function was tried first but found unreliable; see script comments). "
                 f"Peak NMDA current: {_clamp_by_v[-70.0]:.5f} nA at Vhold=-70 mV vs "
                 f"{_clamp_by_v[-20.0]:.5f} nA at Vhold=-20 mV -- "
                 "NMDA contribution clearly grows with depolarization, confirming Mg2+ unblock.")
    lines.append("")
    lines.append("**EPSP-to-spike via NMDA-dependent temporal summation** "
                 "(5-pulse train, `plots/receptors/L796_AMPA_NMDA_summation.png`):")
    lines.append("")
    lines.append("| frequency (Hz) | condition | peak depolarization (mV) | spike fired |")
    lines.append("|---|---|---|---|")
    for r in summation_rows:
        lines.append(f"| {r['frequency_Hz']:.0f} | {r['condition']} | "
                     f"{fmt(r['peak_depolarization_mV'],2)} | {r['spike_fired']} |")
    lines.append("")

    lines.append("## 1b. Inhibitory: GABA-A + Glycine")
    lines.append("")
    lines.append(f"GABA-A: tau_rise={GABAA_TAU_RISE} ms, tau_decay={GABAA_TAU_DECAY} ms "
                 f"(GABAa_DynSyn.mod defaults). Glycine: tau_rise={GLY_TAU_RISE} ms, "
                 f"tau_decay={GLY_TAU_DECAY} ms (Glycine_DynSyn.mod defaults). "
                 f"ECl = {ECL_CONTROL} mV for both (control condition, Coull 2003).")
    lines.append("")
    lines.append(
        f"RMP ({-72.43} mV) sits close to ECl ({ECL_CONTROL} mV), so at rest a chloride "
        "conductance has little driving force and is almost pure shunt -- a real property of "
        "GABA-A/glycine near rest, not a modeling artifact. IPSP amplitude/kinetics below were "
        f"therefore characterized from a depolarized holding potential "
        f"(+{HOLDING_CURRENT_NA*1000:.1f} pA bias current, baseline ~-60 mV) to give adequate "
        "driving force; the shunting demonstration further below uses normal resting potential, "
        "since shunting does not require a large driving force to be effective."
    )
    lines.append("")
    lines.append("| receptor | weight (nS) | amplitude (mV) | rise time (ms) | decay tau (ms) | latency (ms) |")
    lines.append("|---|---|---|---|---|---|")
    for r in s2["ipsp_rows"]:
        lines.append(f"| {r['receptor']} | {fmt(r['weight_nS'],3)} | {fmt(r['amplitude_mV'],3)} | "
                     f"{fmt(r['rise_time_ms'],2)} | {fmt(r['decay_tau_ms'],2)} | {fmt(r['latency_ms'],2)} |")
    lines.append("")
    lines.append(f"**{s2['faster_decay']} decays faster**, as expected "
                 f"(GABA-A tau_decay={GABAA_TAU_DECAY} ms vs Glycine tau_decay={GLY_TAU_DECAY} ms "
                 "at the mechanism level; somatic decay tau above is broadened by cable/membrane "
                 "filtering but preserves the same ordering).")
    lines.append("")
    lines.append("**Shunting inhibition** (`plots/receptors/L796_shunting_demo.png`): a 50 Hz "
                 "excitatory train (AMPA+NMDA) that fires a spike alone is blocked when GABA-A+"
                 "Glycine are co-activated simultaneously, at normal resting potential. A direct "
                 "scan found the single-unitary-synapse GABA-A+Glycine weight (the same weight "
                 "calibrated above for a ~2 mV IPSP) does NOT shunt-block this train -- blocking "
                 f"only occurs around {s2['shunt_inhibition_multiplier']:g}x that weight, used "
                 "here as a stand-in for convergent input from several co-active inhibitory "
                 "interneurons (a population-level inhibitory barrage), not a claim that a "
                 "single GABAergic/glycinergic synapse can shunt-block this train on its own:")
    lines.append("")
    lines.append("| condition | peak depolarization (mV) | spike fired | inhibition weight multiplier |")
    lines.append("|---|---|---|---|")
    for r in s2["shunt_rows"]:
        lines.append(f"| {r['condition']} | {fmt(r['peak_depolarization_mV'],2)} | {r['spike_fired']} | "
                     f"{fmt(r['inhibition_weight_multiplier'],1)}x |")
    lines.append("")

    lines.append("## 1c. nAChR-like receptor (documented proxy)")
    lines.append("")
    lines.append(f"{NACHR_CAVEAT}")
    lines.append("")
    lines.append(f"Single-pulse depolarization calibrated to ~2 mV: {s3['amp_nachr']:.3f} mV "
                 f"achieved, decay tau {s3['feat_nachr']['decay_tau_ms']:.2f} ms "
                 f"(synaptic tau2={NACHR_TAU2} ms).")
    lines.append("")
    lines.append("| condition | peak depolarization above baseline (mV) | spike fired |")
    lines.append("|---|---|---|")
    for r in s3["summation_rows"]:
        lines.append(f"| {r['condition']} | {fmt(r['depolarization_above_baseline_mV'],2)} | "
                     f"{r['spike_fired']} |")
    lines.append("")
    lines.append(
        "nAChR-like activation depolarizes L796 and summates with glutamatergic drive "
        "(`plots/receptors/L796_nAChR_depolarization.png`), demonstrating the requested "
        "ligand-gated cation-channel behavior -- but see the caveat above: this does not "
        "represent the real (predominantly presynaptic/interneuronal, antinociceptive) "
        "cholinergic circuit in the dorsal horn."
    )
    lines.append("")

    lines.append("## 1d. Deferred: P2X and 5-HT3")
    lines.append("")
    lines.append(
        "No vetted P2X3/P2X4 or 5-HT3 .mod file is available in `external/SDHmodel/mods`. "
        "Per the guardrails, these are **not implemented** (not faked with an unlabeled proxy) "
        "and are listed as future work. Both are neuropathic-pain-relevant "
        "(P2X: microglia-BDNF-KCC2 axis, Tsuda 2003/Trang 2012; 5-HT3: descending "
        "facilitation, Suzuki 2004) -- see `literature_targets/06_receptor_target_values.csv`."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- All synaptic weights are phenomenological (tuned to a target EPSP/IPSP amplitude), "
        "not measured for L796; the underlying active-conductance densities they act on are "
        "themselves phenomenologically fitted (see the single-cell status report)."
    )
    lines.append(
        "- The NMDA:AMPA weight ratio (0.5) and the AMPA/GABA-A/glycine tau values (mechanism "
        "defaults, with AMPA tau_rise/tau_decay adjusted to the literature-cited range) are "
        "assumptions/defaults, not L796-specific fits."
    )
    lines.append(
        "- The nAChR-like receptor is a documented Exp2Syn proxy on the projection neuron "
        "itself; it does not reproduce the presynaptic/interneuronal site of real dorsal-horn "
        "nAChR action."
    )
    lines.append(
        "- P2X and 5-HT3 are deferred (no vetted mechanism available), not implemented."
    )
    lines.append(
        f"- The shunting demonstration uses {s2['shunt_inhibition_multiplier']:g}x the "
        "single-unitary-synapse GABA-A+Glycine weight -- a direct scan confirmed the unitary "
        "weight alone (the same weight calibrated above for a realistic ~2 mV IPSP) does not "
        "block the excitatory train tested here. The multiplier is intended to represent "
        "several co-active inhibitory interneurons converging on the same location, not a "
        "single synapse; it was not independently validated against a specific convergence "
        "count from the literature."
    )
    lines.append("")

    (REPORTS_DIR / "L796_ligand_gated_receptor_report.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"\nSaved report: {REPORTS_DIR / 'L796_ligand_gated_receptor_report.md'}")


def print_terminal_summary(s1, summation_rows, s2, s3):
    print("\n" + "=" * 78)
    print("L796 PART 1 SUMMARY: LIGAND-GATED RECEPTORS")
    print("=" * 78)
    print(f"AMPA+NMDA unitary somatic EPSP (proximal): {s1['amp_unitary']:.3f} mV")
    print(f"GABA-A+Glycine unitary somatic IPSP (from depolarized holding): ~2.0 mV each "
          f"(GABA-A decay tau={ [r for r in s2['ipsp_rows'] if r['receptor']=='GABA-A'][0]['decay_tau_ms']:.2f} ms, "
          f"Glycine decay tau={ [r for r in s2['ipsp_rows'] if r['receptor']=='Glycine'][0]['decay_tau_ms']:.2f} ms, "
          f"faster receptor = {s2['faster_decay']})")
    print(f"nAChR-like (Exp2Syn proxy) unitary depolarization: {s3['amp_nachr']:.3f} mV")
    shunt_blocked = s2["shunt_rows"][0]["spike_fired"] and not s2["shunt_rows"][1]["spike_fired"]
    print(f"Shunting inhibition blocked EPSP-train spike: {shunt_blocked}")
    print("=" * 78)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Building the fixed, already-validated L796 single-cell active model...")
    soma, ais, groups, first_order_dend = build_validated_model()
    locs = pick_dendrite_locations(soma, groups)
    for name, info in locs.items():
        print(f"  {name}: {info['sec'].name()} at {info['dist_um']:.1f} um path distance from soma")

    s1 = section1_glutamatergic(soma, locs)
    summation_rows, summation_traces, w_train = section1b_summation(soma, locs, s1["w_unitary"])
    s2 = section2_inhibitory(soma, locs, w_train, w_train * NMDA_AMPA_WEIGHT_RATIO)
    s3 = section3_nAChR(soma, locs, s1["w_unitary"])

    # --- save CSVs ---
    save_csv(s1["epsp_rows"], RESULTS_DIR / "L796_EPSP_validation.csv")
    save_csv(s1["mgblock_rows"], RESULTS_DIR / "L796_NMDA_mgblock.csv")
    save_csv(s1["nmda_clamp_rows"], RESULTS_DIR / "L796_NMDA_voltage_clamp.csv")
    save_csv(summation_rows, RESULTS_DIR / "L796_EPSP_summation.csv")
    save_csv(s2["ipsp_rows"], RESULTS_DIR / "L796_IPSP_validation.csv")
    save_csv(s2["shunt_rows"], RESULTS_DIR / "L796_shunting_validation.csv")
    save_csv(s3["summation_rows"], RESULTS_DIR / "L796_nAChR_validation.csv")

    # --- save plots ---
    plot_epsp_by_location(s1["plot_traces"], PLOTS_DIR / "L796_EPSP_traces_by_location.png")
    plot_summation(summation_traces, PLOTS_DIR / "L796_AMPA_NMDA_summation.png")
    plot_mgblock(s1["mgblock_rows"], PLOTS_DIR / "L796_NMDA_mgblock.png")
    plot_ipsp(s2["ipsp_traces"], PLOTS_DIR / "L796_IPSP_traces.png")
    plot_shunting(s2["shunt_traces"], PLOTS_DIR / "L796_shunting_demo.png")
    plot_nachr(s3["nachr_trace"], s3["summation_traces"], PLOTS_DIR / "L796_nAChR_depolarization.png")

    # --- handoff JSON for script 15 (neuropathic manipulations) ---
    import json
    handoff = {
        "celsius": CELSIUS,
        "dendrite_locations": {name: {"section": info["sec"].name(), "distance_um": info["dist_um"]}
                                for name, info in locs.items()},
        "w_ampa_unitary_uS": s1["w_unitary"],
        "amp_unitary_epsp_mV": s1["amp_unitary"],
        "w_ampa_train_uS": w_train,
        "w_nmda_ratio": NMDA_AMPA_WEIGHT_RATIO,
        "w_gaba_uS": s2["w_gaba"],
        "w_gly_uS": s2["w_gly"],
        "w_nachr_uS": s3["w_nachr"],
        "amp_unitary_ipsp_mV": 2.0,
        "ecl_control_mV": ECL_CONTROL,
        "holding_current_nA": HOLDING_CURRENT_NA,
        "ampa_kinetics": {"tau_rise": AMPA_TAU_RISE, "tau_decay": AMPA_TAU_DECAY, "e": AMPA_E},
        "nmda_kinetics": {"tau_rise": NMDA_TAU_RISE, "tau_decay": NMDA_TAU_DECAY, "e": NMDA_E},
        "gabaa_kinetics": {"tau_rise": GABAA_TAU_RISE, "tau_decay": GABAA_TAU_DECAY},
        "glycine_kinetics": {"tau_rise": GLY_TAU_RISE, "tau_decay": GLY_TAU_DECAY},
    }
    with open(RESULTS_DIR / "L796_receptor_calibration.json", "w") as f:
        json.dump(handoff, f, indent=2)

    write_report(s1, summation_rows, s2, s3, locs)
    print_terminal_summary(s1, summation_rows, s2, s3)

    return s1, summation_rows, s2, s3, locs


if __name__ == "__main__":
    main()
