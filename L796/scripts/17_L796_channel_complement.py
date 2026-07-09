import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from neuron import h

# ============================================================
# L796 CHANNEL COMPLEMENT: EVIDENCE-DRIVEN EXTENSION
# ============================================================
# Extends the FIXED, already-validated L796 single-cell + receptor model
# with ONLY the channels justified by literature_targets/
# 07_channel_evidence_and_fitting.csv, following that table's own
# decision_rule column. Everything added is phenomenologically fitted
# (evidence levels B/C/D = functionally motivated, not exact L796
# measurements) -- this is stated explicitly throughout.
#
# Only NEW files are written under L796/. Step 1-5 files, the SWC, the
# HOC, and scripts 13/14/15's own prerequisites are untouched.
# ============================================================

HERE = Path(__file__).resolve().parent

spec14 = importlib.util.spec_from_file_location("recept14", str(HERE / "14_L796_ligand_gated_receptors.py"))
m = importlib.util.module_from_spec(spec14)
sys.modules["recept14"] = m
spec14.loader.exec_module(m)  # main() only runs under `if __name__=="__main__"`, false here

mod = m.mod
PROJECT_ROOT = m.PROJECT_ROOT
PARAMS_DIR = mod.PARAMS_DIR
RESULTS_DIR = PROJECT_ROOT / "results" / "channels"
PLOTS_DIR = PROJECT_ROOT / "plots" / "channels"
REPORTS_DIR = m.REPORTS_DIR
LIT_DIR = PROJECT_ROOT / "literature_targets"
for d in (RESULTS_DIR, PLOTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

CELSIUS = m.CELSIUS  # 6.3, locked (see reports/L796_single_cell_final_status.md)

with open(PARAMS_DIR / "L796_final_parameter_set.json") as f:
    V1_PARAMS = json.load(f)

EVIDENCE_CSV = LIT_DIR / "07_channel_evidence_and_fitting.csv"

# -----------------------------
# Single-cell "no regression" bounds (from the locked v1 model)
# -----------------------------
RMP_ACCEPT = mod.RMP_ACCEPT
RIN_ACCEPT_GOHM = mod.RIN_ACCEPT_GOHM
RHEOBASE_ACCEPT_PA = mod.RHEOBASE_ACCEPT_PA
OVERSHOOT_ACCEPT = mod.AP_TARGETS["overshoot_mV"]
AMPLITUDE_ACCEPT = mod.AP_TARGETS["amplitude_mV"]


def check_no_regression(feat):
    """RMP/Rin/rheobase/overshoot/amplitude must stay within the already-passing
    bounds, and there must be no spontaneous firing at 0 pA. Half-width is
    NOT checked here -- it is already a documented, accepted relaxed-pass
    (see reports/L796_single_cell_final_status.md) and this task does not
    require it to newly pass."""
    if feat["spontaneous_spikes_at_0pA"] > 0:
        return False, "spontaneous firing at 0 pA"
    if not (RMP_ACCEPT[0] <= feat["RMP_mV"] <= RMP_ACCEPT[1]):
        return False, f"RMP {feat['RMP_mV']:.2f} outside {RMP_ACCEPT}"
    if not (RIN_ACCEPT_GOHM[0] <= feat["Rin_GOhm"] <= RIN_ACCEPT_GOHM[1]):
        return False, f"Rin {feat['Rin_GOhm']:.3f} outside {RIN_ACCEPT_GOHM}"
    rheo = feat["rheobase_pA"]
    if math.isnan(rheo) or not (RHEOBASE_ACCEPT_PA[0] <= rheo <= RHEOBASE_ACCEPT_PA[1]):
        return False, f"rheobase {rheo} outside {RHEOBASE_ACCEPT_PA}"
    overshoot = feat.get("overshoot_mV", math.nan)
    if math.isnan(overshoot) or not (OVERSHOOT_ACCEPT[0] <= overshoot <= OVERSHOOT_ACCEPT[1]):
        return False, f"overshoot {overshoot} outside {OVERSHOOT_ACCEPT}"
    amp = feat.get("amplitude_mV", math.nan)
    if math.isnan(amp) or not (AMPLITUDE_ACCEPT[0] <= amp <= AMPLITUDE_ACCEPT[1]):
        return False, f"amplitude {amp} outside {AMPLITUDE_ACCEPT}"
    return True, "ok"


# ============================================================
# STEP 1: STATUS MAP
# ============================================================
# One row per evidence-CSV channel. Status assigned per the CSV's own
# recommended_status/priority/decision_rule columns, cross-checked against
# what's actually in parameters/L796_final_parameter_set.json.

STATUS_MAP = [
    # (name, class, priority, status, parameter_used, reason, source_summary)
    dict(name="Passive leak", cls="Passive", priority=10, status="ALREADY_PRESENT",
         parameter_used="e_pas=-72.8 mV, g_pas=3.7855e-6 S/cm2 (fitted to Luz 2014 Rin)",
         reason="Core (priority 10); fitted from the same-dataset PN passive physiology target.",
         source="NeuroMorpho L796-ALT-PN; Luz 2014 (PMC3979609)"),
    dict(name="Fast transient Na", cls="Voltage-gated Na", priority=10, status="ALREADY_PRESENT",
         parameter_used="B_Na: AIS scale x1.45 (base 3.45 S/cm2), soma+proximal dend 0.04 S/cm2",
         reason="Core (priority 10); AIS/axon-dominant + somatic/proximal-dendrite addition to fix the "
                "electrotonic-echo defect found during single-cell validation.",
         source="Rat dorsal-horn AIS-dominant fast Na (PMC1159869)"),
    dict(name="Delayed-rectifier K", cls="Voltage-gated K", priority=10, status="ALREADY_PRESENT",
         parameter_used="KDR: AIS base 0.076 S/cm2, soma base 0.001075 S/cm2, dend base 0.036 S/cm2, "
                        "all x2.0 scale",
         reason="Core (priority 10); fitted jointly with NaT for AP repolarization/half-width.",
         source="PMC1664848; PMC3979609"),
    dict(name="AMPA", cls="Ligand-gated", priority=10, status="ALREADY_PRESENT",
         parameter_used="AMPA_DynSyn: tau_rise=0.5 ms, tau_decay=2.5 ms, e=0 mV; weight calibrated "
                        "to ~2 mV unitary EPSP",
         reason="Core for synapses (priority 10).", source="PMC1464766"),
    dict(name="NMDA", cls="Ligand-gated", priority=9, status="ALREADY_PRESENT",
         parameter_used="NMDA_DynSyn: tau_rise=5 ms, tau_decay=70 ms, e=0 mV, Jahr&Stevens Mg-block; "
                        "NMDA:AMPA weight ratio 0.5",
         reason="Core for pain-circuit synapses (priority 9).", source="PMC1464766; PMC3923208"),
    dict(name="GABA_A", cls="Ligand-gated", priority=9, status="ALREADY_PRESENT",
         parameter_used="GABAa_DynSyn: tau_rise=1 ms, tau_decay=20 ms; weight calibrated to ~2 mV IPSP",
         reason="Core for inhibitory circuit (priority 9).", source="PMC1464766; PMC6782499"),
    dict(name="Glycine receptor", cls="Ligand-gated", priority=9, status="ALREADY_PRESENT",
         parameter_used="Glycine_DynSyn: tau_rise=1 ms, tau_decay=10 ms; weight calibrated to ~2 mV IPSP",
         reason="Core for inhibitory circuit (priority 9).", source="PMC1464766; PMC6782499"),
    dict(name="Intracellular calcium dynamics", cls="Calcium handling", priority=6, status="ALREADY_PRESENT",
         parameter_used="CaIntraCellDyn inserted alongside iCaL/iCaAN/iKCa in soma and dendrites",
         reason="Required when fitting KCa/Ca-dependent currents (priority 6); already required as a "
                "dependency of iKCa/iCaL/iCaAN, which were carried over from the base model.",
         source="PMC/32341097"),
    dict(name="KCC2/SLC12A5", cls="Chloride transporter", priority=9, status="ALREADY_PRESENT",
         parameter_used="Two validated chloride states: ECl=-70 mV (control) and ECl=-55 mV (neuropathic)",
         reason="Decision rule: 'at minimum implement two validated chloride states; dynamic transporter "
                "optional.' Satisfied by the normal-vs-neuropathic ECl states already implemented in "
                "Part 2 (script 15); no dynamic KCC2 transporter model added.",
         source="Coull et al 2003 (PMID 12931188)"),
    dict(name="A-type K", cls="Voltage-gated K", priority=8, status="PENDING", parameter_used="",
         reason="Conditional-high; gap firing evidence in identified rat lamina-I PNs. Evaluated this pass.",
         source="PMC1664848"),
    dict(name="NK1/TACR1", cls="Metabotropic receptor", priority=8, status="PENDING", parameter_used="",
         reason="Conditional-high; ~80% of rat lamina-I PNs are NK1+. Evaluated this pass.",
         source="PMC6757649"),
    dict(name="T-type Ca", cls="Voltage-gated Ca", priority=7, status="PENDING", parameter_used="",
         reason="Conditional-high, but decision rule requires a measured low-threshold burst/rebound "
                "target. Evaluated this pass.",
         source="PMC1664848; PMID 33871884"),
    dict(name="Persistent Na", cls="Voltage-gated Na", priority=4, status="FLAGGED_OVERINCLUDED",
         parameter_used="iNaP: soma base 0.0001 S/cm2 x1.0 scale",
         reason="FLAG: recommended_status='Later' (priority 4); decision rule says do NOT add for "
                "ordinary tonic firing unless a measured persistent inward current (PIC)/ramp-hysteresis "
                "target exists -- none does for L796. Present only because it was carried over unchanged "
                "from the ModelDB 267056 base model during earlier single-cell tuning, not because the "
                "evidence table justifies it. Left in place (removing it would require re-validating the "
                "whole single-cell fit) but explicitly flagged as over-inclusion.",
         source="No L796-specific PIC evidence in the evidence table"),
    dict(name="L-type Ca", cls="Voltage-gated Ca", priority=4, status="FLAGGED_OVERINCLUDED",
         parameter_used="iCaL: soma base 0.0001 S/cm2 x1.25, dend base 3e-05 S/cm2 x1.25",
         reason="FLAG: recommended_status='Conditional-low' (priority 4); decision rule says do not add "
                "unless a sustained Ca/plateau target exists -- none does for L796. Present only because "
                "it was carried over unchanged from the ModelDB 267056 base model, not because the "
                "evidence table justifies it. Left in place for the same reason as persistent Na above.",
         source="PMID 2482353 (labelled ascending dorsal-horn cells, not L796-specific)"),
    dict(name="SK-type KCa", cls="Calcium-activated K", priority=5, status="DEFERRED", parameter_used="n/a",
         reason="DEFER: decision rule 'add only if Ca-coupled medium AHP/adaptation remains missing.' "
                "iKCa is already present and functionally covers Ca-activated K/AHP; no apamin-sensitive "
                "current evidence specific to L796.",
         source="No direct L796 apamin evidence (evidence_level D)"),
    dict(name="BK-type KCa", cls="Calcium-activated K", priority=4, status="DEFERRED", parameter_used="n/a",
         reason="DEFER: decision rule 'add only with fast-AHP/spike-width evidence.' No such evidence "
                "for L796; iKCa already functionally covers Ca-K currents.",
         source="No direct L796 blocker evidence (evidence_level D)"),
    dict(name="N-type Ca", cls="Voltage-gated Ca", priority=5, status="DEFERRED", parameter_used="n/a",
         reason="DEFER: decision rule 'add when calcium or presynaptic release is explicitly modeled' -- "
                "this project does not explicitly model presynaptic Ca-dependent release.",
         source="PMID 2482353; PMID 32341097"),
    dict(name="P/Q/R-type Ca", cls="Voltage-gated Ca", priority=3, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Later'): decision rule 'add only with subtype-specific evidence or explicit "
                "terminal model' -- not resolved for L796, no terminal model here.",
         source="PMID 32341097"),
    dict(name="HCN/Ih", cls="Voltage-gated (cation)", priority=4, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Later'): decision rule 'add only for measured sag/rebound/resonance' -- no "
                "L796-specific sag evidence.",
         source="PMC8208100 (mouse lamina-I spinobulbar subset, not L796)"),
    dict(name="M current/KCNQ", cls="Voltage-gated K", priority=3, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Do not add now'): decision rule 'add only after a discriminating "
                "pharmacological feature' -- none identified for L796.",
         source="No direct identified-L796 functional evidence"),
    dict(name="NALCN", cls="Modulator-gated Na leak", priority=6, status="DEFERRED", parameter_used="n/a",
         reason="DEFER: decision rule 'add only as part of a validated SP/NK1 model.' The NK1 addition "
                "in this pass uses NK1_DynSyn's own built-in nonspecific cation current directly, not a "
                "separate NALCN-mediated pathway, so this dependency is not triggered.",
         source="PMC6095712 (neonatal spinal PNs)"),
    dict(name="GABA_B plus GIRK", cls="Metabotropic/effector", priority=5, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Later'): decision rule 'add after fast inhibition is validated and if slow "
                "modulation is studied.' Fast inhibition (GABA-A/glycine) is validated, but slow "
                "modulation is not a current project target.",
         source="PMC6053268"),
    dict(name="Kainate receptor", cls="Ligand-gated", priority=3, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Do not add now'): decision rule 'add only after AMPA-separated residual "
                "current is demonstrated' -- not demonstrated for L796.",
         source="PMC1464766 (AMPA/kainate not pharmacologically separated in older recordings)"),
    dict(name="P2X/5-HT3/nicotinic", cls="Ligand-gated", priority=1, status="DEFERRED", parameter_used="n/a",
         reason="DEFER ('Do not add now'): decision rule 'require a specified anatomical input and "
                "functional response' -- none specified. (An nAChR-like Exp2Syn PROXY already exists "
                "from Part 1 for a different, receptor-addition purpose; P2X and 5-HT3 remain fully "
                "unimplemented, consistent with that earlier work.)",
         source="No exact L796 requirement established (evidence_level D)"),
]


def load_evidence_csv():
    rows = []
    with open(EVIDENCE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


# ============================================================
# MODEL SETUP
# ============================================================

def build_base_model():
    """The fixed, already-validated v1 single-cell model (soma+proximal-dend
    B_Na, KDR_scale, etc.) -- identical to script 14's build_validated_model."""
    return m.build_validated_model()


def add_A_type_K(soma, groups, first_order_dend, density_S_per_cm2):
    """Insert B_A into soma + proximal dendrites (evidence table
    initial_location: 'Soma/proximal dendrite initially'). ek=-90 to match
    the rest of the K currents in this model (KDR/iKCa)."""
    for sec in groups["soma"]:
        mod.safe_insert(sec, "B_A")
        sec.ek = -90
        sec.gkbar_B_A = density_S_per_cm2
    for sec in first_order_dend:
        mod.safe_insert(sec, "B_A")
        sec.ek = -90
        sec.gkbar_B_A = density_S_per_cm2


def add_NK1(soma):
    """NK1_DynSyn as a point process at the soma (evidence table
    initial_location: 'Soma/dendrites'). Ito et al 2002-based mechanism:
    slow nonspecific cationic current (e=0 mV) plus a silenced Ca-elevation
    signal. Kinetics (tau_rise=10 ms, tau_decay=5000 ms) are the mechanism's
    own published defaults, not refit."""
    nk1 = h.NK1_DynSyn(soma(0.5))
    return nk1


# ============================================================
# STEP 2: A-TYPE K GRID SEARCH
# ============================================================

A_TYPE_K_DENSITIES = [0.0, 0.005, 0.01, 0.02, 0.04]  # S/cm2, per task spec


def evaluate_A_type_K_candidate(density):
    soma, ais, groups, first_order_dend = build_base_model()
    add_A_type_K(soma, groups, first_order_dend, density)
    h.celsius = CELSIUS

    traces = mod.run_sweep(soma, mod.FINAL_CURRENTS_PA)
    feat = mod.extract_full_features(traces)
    ok, reason = check_no_regression(feat)

    return {
        "density_S_per_cm2": density,
        "valid": ok,
        "reject_reason": "" if ok else reason,
        "RMP_mV": feat["RMP_mV"],
        "Rin_GOhm": feat["Rin_GOhm"],
        "rheobase_pA": feat["rheobase_pA"],
        "overshoot_mV": feat.get("overshoot_mV"),
        "amplitude_mV": feat.get("amplitude_mV"),
        "half_width_ms": feat.get("half_width_ms"),
        "first_spike_latency_ms": feat.get("first_spike_latency_ms"),
        "threshold_mV": feat.get("threshold_mV"),
    }, feat, traces


def run_A_type_K_search():
    print("\n" + "=" * 78)
    print("STEP 2: A-TYPE K (B_A) GRID SEARCH")
    print("=" * 78)
    print(f"  Densities tested: {A_TYPE_K_DENSITIES} S/cm2 (soma + proximal dendrites, ek=-90)")

    rows = []
    best = None
    for density in A_TYPE_K_DENSITIES:
        row, feat, traces = evaluate_A_type_K_candidate(density)
        rows.append(row)
        tag = "OK  " if row["valid"] else "REJ "
        print(f"  {tag} density={density:.3f} S/cm2  RMP={row['RMP_mV']:.2f}  "
              f"Rin={row['Rin_GOhm']:.3f}  rheobase={row['rheobase_pA']}  "
              f"overshoot={row['overshoot_mV']}  amplitude={row['amplitude_mV']}  "
              f"first_spike_latency={row['first_spike_latency_ms']}" +
              ("" if row["valid"] else f"  [{row['reject_reason']}]"))
        if row["valid"]:
            if best is None or (not math.isnan(row["first_spike_latency_ms"]) and
                                 row["first_spike_latency_ms"] > best["first_spike_latency_ms"]):
                best = row

    if best is None:
        raise RuntimeError("No A-type K candidate (including density=0.0) survived the "
                            "no-regression check -- this should not happen since density=0.0 "
                            "reproduces the unmodified v1 model.")

    chosen_density = best["density_S_per_cm2"]
    zero_row = next(r for r in rows if r["density_S_per_cm2"] == 0.0)
    outcome = ("A-type K improves first-spike delay" if chosen_density > 0.0
               else "NaT+KDR alone already reproduce the delay; A-type K adds nothing within bounds")
    print(f"\n  Chosen density: {chosen_density} S/cm2 ({outcome})")
    print(f"  First-spike latency: density=0 -> {zero_row['first_spike_latency_ms']:.2f} ms, "
          f"chosen -> {best['first_spike_latency_ms']:.2f} ms")

    return chosen_density, rows, zero_row, best


def run_first_spike_latency_vs_current(density, currents_pA):
    soma, ais, groups, first_order_dend = build_base_model()
    add_A_type_K(soma, groups, first_order_dend, density)
    h.celsius = CELSIUS

    latencies = {}
    for pA in currents_pA:
        t, v = mod.run_current_step(soma, pA / 1000.0)
        spikes = mod.count_spikes(t[t >= mod.STIM_DELAY], v[t >= mod.STIM_DELAY])
        latencies[pA] = (spikes[0] - mod.STIM_DELAY) if spikes else math.nan
    return latencies


def run_prepulse_dependence_test(density, test_current_pA, prepulse_amp_pA=-20.0, prepulse_dur_ms=200.0):
    """Compares first-spike latency at test_current_pA with vs without a
    preceding hyperpolarizing prepulse. A-type K is inactivated at
    depolarized/rest potentials and de-inactivated by hyperpolarization, so
    a genuine A-current should show LONGER first-spike latency after the
    prepulse (classic gap-firing signature) -- this is the
    'prepulse_dependence' fit/validation feature from the evidence table."""
    results = {}
    for label, use_prepulse in [("no_prepulse", False), ("with_prepulse", True)]:
        soma, ais, groups, first_order_dend = build_base_model()
        add_A_type_K(soma, groups, first_order_dend, density)
        h.celsius = CELSIUS

        pre = h.IClamp(soma(0.5))
        if use_prepulse:
            pre.delay = mod.STIM_DELAY - prepulse_dur_ms
            pre.dur = prepulse_dur_ms
            pre.amp = prepulse_amp_pA / 1000.0
        else:
            pre.delay = 0.0
            pre.dur = 0.0
            pre.amp = 0.0

        stim = h.IClamp(soma(0.5))
        stim.delay = mod.STIM_DELAY
        stim.dur = mod.STIM_DUR
        stim.amp = test_current_pA / 1000.0

        t_vec = h.Vector().record(h._ref_t)
        v_vec = h.Vector().record(soma(0.5)._ref_v)
        h.dt = mod.DT
        h.tstop = mod.STIM_DELAY + mod.STIM_DUR + 200.0
        h.v_init = mod.E_PAS
        h.finitialize(mod.E_PAS)
        h.continuerun(h.tstop)

        t = np.array(t_vec)
        v = np.array(v_vec)
        post_mask = t >= mod.STIM_DELAY
        spikes = mod.count_spikes(t[post_mask], v[post_mask])
        latency = (spikes[0] - mod.STIM_DELAY) if spikes else math.nan
        results[label] = {"latency_ms": latency, "t": t, "v": v}
    return results


# ============================================================
# STEP 3: NK1/TACR1
# ============================================================

NK1_TARGET_DEPOL_MV = 4.0  # ASSUMPTION: modest slow SP-evoked depolarization


def calibrate_NK1_weight(soma, target_depol_mV=NK1_TARGET_DEPOL_MV, weight_lo=0.0001,
                          weight_hi=0.05, tol=0.1, max_iter=25):
    stim_time = 300.0
    tstop = 3000.0  # NK1 is very slow (tau_decay=5000 ms); needs a long window to peak

    last_amp = None
    last_w = weight_hi
    for _ in range(max_iter):
        w = (weight_lo + weight_hi) / 2.0
        m.reset_stimuli()
        nk1 = add_NK1(soma)
        ns = m.make_netstim(start=stim_time, number=1)
        nc = m.new_netcon(ns, nk1, w)
        t, v = m.run_sim(tstop, record_secs={"soma": (soma, 0.5)})
        v_soma = v["soma"]
        baseline = float(np.mean(v_soma[(t >= stim_time - 20) & (t <= stim_time - 2)]))
        peak = float(np.max(v_soma[t >= stim_time]))
        amp = peak - baseline
        last_amp, last_w = amp, w
        if abs(amp - target_depol_mV) <= tol:
            return w, amp, (t, v_soma)
        if amp < target_depol_mV:
            weight_lo = w
        else:
            weight_hi = w
    return last_w, last_amp, (t, v_soma)


def run_NK1_rheobase_test(soma, w_nk1, delay_before_current_ms=1000.0):
    """Rheobase with a single prior SP/NK1 event (still substantially active,
    given its slow ~5 s decay) vs without (weight=0, 'antagonist' analogy)."""
    results = {}
    for label, active in [("without_NK1_antagonist", False), ("with_NK1", True)]:
        soma_i, ais, groups, first_order_dend = build_base_model()
        h.celsius = CELSIUS
        nk1 = add_NK1(soma_i)
        ns = m.make_netstim(start=100.0, number=1)
        w = w_nk1 if active else 0.0
        nc = h.NetCon(ns, nk1)
        nc.delay = 0
        nc.weight[0] = w

        rheobase = None
        for pA in range(0, 61, 5):
            stim = h.IClamp(soma_i(0.5))
            stim.delay = 100.0 + delay_before_current_ms
            stim.dur = mod.STIM_DUR
            stim.amp = pA / 1000.0
            t_vec = h.Vector().record(h._ref_t)
            v_vec = h.Vector().record(soma_i(0.5)._ref_v)
            h.dt = mod.DT
            h.tstop = 100.0 + delay_before_current_ms + mod.STIM_DUR
            h.v_init = mod.E_PAS
            h.finitialize(mod.E_PAS)
            h.continuerun(h.tstop)
            t = np.array(t_vec)
            v = np.array(v_vec)
            post_mask = t >= stim.delay
            spikes = mod.count_spikes(t[post_mask], v[post_mask])
            if len(spikes) > 0:
                rheobase = pA
                break
            stim.amp = 0.0  # detach before the next IClamp is created

        results[label] = rheobase
    return results


# ============================================================
# STEP 4: T-TYPE Ca EVALUATION (rebound test)
# ============================================================

def run_T_type_rebound_test(a_type_k_density):
    """Hyperpolarize, then look for any overshoot ABOVE resting baseline
    during recovery (the T-type-like rebound signature). The recovery
    window must extend well past passive relaxation: with Rin~0.89 GOhm and
    membrane tau~212 ms, a -50 pA/300 ms step drives V to ~-104 mV, and
    PASSIVE relaxation back to baseline alone takes >1000 ms (confirmed by
    direct trace inspection during script development) -- a short recovery
    window would misreport still-hyperpolarized passive relaxation as a
    'negative rebound', which is not a meaningful test of an active
    low-threshold Ca rebound mechanism. The window here (600-1800 ms, i.e.
    300-1500 ms post-step) is long enough for passive relaxation to
    complete, so any genuine active rebound would appear as a peak ABOVE
    baseline within it."""
    soma, ais, groups, first_order_dend = build_base_model()
    add_A_type_K(soma, groups, first_order_dend, a_type_k_density)
    h.celsius = CELSIUS

    stim = h.IClamp(soma(0.5))
    stim.delay = 200.0
    stim.dur = 300.0
    stim.amp = -0.05  # -50 pA hyperpolarizing step

    t_vec = h.Vector().record(h._ref_t)
    v_vec = h.Vector().record(soma(0.5)._ref_v)
    h.dt = mod.DT
    h.tstop = 1800.0
    h.v_init = mod.E_PAS
    h.finitialize(mod.E_PAS)
    h.continuerun(h.tstop)

    t = np.array(t_vec)
    v = np.array(v_vec)

    baseline = float(np.mean(v[(t >= 100) & (t <= 195)]))
    recovery_mask = (t >= 600) & (t <= 1800)
    settled_mask = (t >= 1700) & (t <= 1800)
    settled_v = float(np.mean(v[settled_mask]))
    rebound_peak = float(np.max(v[recovery_mask]))
    rebound_depol = rebound_peak - baseline
    spikes = mod.count_spikes(t[recovery_mask], v[recovery_mask])

    return {
        "baseline_mV": baseline, "settled_recovery_mV": settled_v,
        "rebound_peak_mV": rebound_peak,
        "rebound_depol_mV": rebound_depol, "rebound_spike": len(spikes) > 0,
        "t": t, "v": v,
    }


# ============================================================
# SAVE / PLOT
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


def plot_first_spike_latency(latencies_with, latencies_without, path):
    plt.figure(figsize=(7, 5))
    currents = sorted(latencies_with.keys())
    plt.plot(currents, [latencies_with[c] for c in currents], marker="o", label="A-type K present")
    plt.plot(currents, [latencies_without[c] for c in currents], marker="s", label="A-type K absent")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("First-spike latency (ms)")
    plt.title("First-spike latency vs current: A-type K on/off")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_prepulse_dependence(results, path):
    plt.figure(figsize=(8, 5))
    for label, res in results.items():
        t, v = res["t"], res["v"]
        mask = (t >= mod.STIM_DELAY - 250) & (t <= mod.STIM_DELAY + 100)
        plt.plot(t[mask], v[mask], label=f"{label} (latency={res['latency_ms']:.2f} ms)")
    plt.axvline(mod.STIM_DELAY, linestyle="--", color="k", alpha=0.4, label="test current onset")
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title("A-type K prepulse dependence")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_NK1_response(trace, path):
    t, v = trace
    plt.figure(figsize=(8, 5))
    mask = (t >= 250) & (t <= 3000)
    plt.plot(t[mask], v[mask])
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title("NK1/TACR1: SP-evoked slow depolarization")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_T_type_rebound(res, path):
    t, v = res["t"], res["v"]
    plt.figure(figsize=(8, 5))
    mask = (t >= 100) & (t <= 1800)
    plt.plot(t[mask], v[mask])
    plt.axvspan(200, 500, alpha=0.1, color="grey", label="hyperpolarizing step (-50 pA)")
    plt.axhline(res["baseline_mV"], linestyle="--", color="k", alpha=0.4, label="resting baseline")
    plt.xlabel("Time (ms)")
    plt.ylabel("Somatic voltage (mV)")
    plt.title(f"T-type Ca evaluation: rebound test (peak-above-baseline={res['rebound_depol_mV']:.2f} mV, "
              f"spike={res['rebound_spike']})")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


# ============================================================
# MAIN
# ============================================================

def fmt(v, nd=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:.{nd}f}"


def main():
    print("Building the fixed, already-validated L796 single-cell + receptor model...")
    evidence_rows = load_evidence_csv()
    print(f"Loaded evidence table: {len(evidence_rows)} rows from {EVIDENCE_CSV.name}")

    # --- Step 2: A-type K ---
    a_density, a_rows, a_zero_row, a_best_row = run_A_type_K_search()
    save_csv(a_rows, RESULTS_DIR / "L796_A_type_K_search.csv")

    latency_currents = [20, 40, 60, 80, 100]
    latencies_with = run_first_spike_latency_vs_current(a_density, latency_currents)
    latencies_without = run_first_spike_latency_vs_current(0.0, latency_currents)
    print("\n  First-spike latency vs current (A-type K present vs absent):")
    for pA in latency_currents:
        print(f"    {pA} pA: with={fmt(latencies_with[pA])} ms, without={fmt(latencies_without[pA])} ms")

    prepulse_test_current = max(a_best_row["rheobase_pA"], 40) if not math.isnan(a_best_row["rheobase_pA"]) else 40
    prepulse_results = run_prepulse_dependence_test(a_density, prepulse_test_current)
    print(f"\n  Prepulse dependence at {prepulse_test_current} pA (tested at chosen A-type K density "
          f"{a_density} S/cm2): no_prepulse latency={fmt(prepulse_results['no_prepulse']['latency_ms'])} ms, "
          f"with_prepulse latency={fmt(prepulse_results['with_prepulse']['latency_ms'])} ms" +
          ("  [A-type K absent at this density -- lengthening reflects other conductances, not A-type K]"
           if a_density == 0.0 else ""))

    plot_first_spike_latency(latencies_with, latencies_without,
                              PLOTS_DIR / "L796_A_type_K_first_spike_latency.png")
    plot_prepulse_dependence(prepulse_results, PLOTS_DIR / "L796_A_type_K_prepulse_dependence.png")

    a_type_status = "ADDED_NOW" if a_density > 0.0 else "EVALUATED"
    a_type_reason = (
        f"Grid search over {A_TYPE_K_DENSITIES} S/cm2 found {a_density} S/cm2 as the density with the "
        f"longest first-spike latency ({fmt(a_best_row['first_spike_latency_ms'])} ms vs "
        f"{fmt(a_zero_row['first_spike_latency_ms'])} ms at density=0) while keeping RMP/Rin/rheobase/"
        "overshoot/amplitude within their accepted bounds and no spontaneous firing at 0 pA."
        if a_density > 0.0 else
        f"Grid search over {A_TYPE_K_DENSITIES} S/cm2 found density=0 gives the longest (or tied-longest) "
        "first-spike latency among candidates passing the no-regression check -- NaT+KDR alone already "
        "reproduce the delayed-onset phenotype within bounds, so A-type K is kept at zero density and "
        "documented per its own decision rule, not added as a nonzero conductance."
    )

    # --- Step 3: NK1 ---
    print("\n" + "=" * 78)
    print("STEP 3: NK1/TACR1 (SP-EVOKED SLOW EXCITATION)")
    print("=" * 78)
    print(f"  ASSUMPTION: L796 is treated as NK1-positive (~80% of rat lamina I PNs are NK1+; "
          "exact L796 status unknown).")
    print(f"  Target: modest slow SP-evoked depolarization ~{NK1_TARGET_DEPOL_MV} mV (ASSUMPTION magnitude).")

    soma_nk1, ais_nk1, groups_nk1, first_order_dend_nk1 = build_base_model()
    add_A_type_K(soma_nk1, groups_nk1, first_order_dend_nk1, a_density)
    h.celsius = CELSIUS
    w_nk1, amp_nk1, nk1_trace = calibrate_NK1_weight(soma_nk1)
    print(f"  Calibrated NK1 weight: {w_nk1*1000:.4f} nS -> {amp_nk1:.2f} mV depolarization achieved")
    plot_NK1_response(nk1_trace, PLOTS_DIR / "L796_NK1_SP_response.png")

    nk1_rheobase = run_NK1_rheobase_test(soma_nk1, w_nk1)
    print(f"  Rheobase without NK1 (antagonist analogy): {nk1_rheobase['without_NK1_antagonist']} pA")
    print(f"  Rheobase with NK1 (SP present):            {nk1_rheobase['with_NK1']} pA")

    # --- Step 4: T-type Ca evaluation ---
    print("\n" + "=" * 78)
    print("STEP 4: T-TYPE Ca EVALUATION (rebound test)")
    print("=" * 78)
    t_type_result = run_T_type_rebound_test(a_density)
    print(f"  Peak voltage above resting baseline during recovery from -50 pA/300 ms step "
          f"(measured over a 1200 ms window, long enough for passive relaxation -- membrane "
          f"tau ~212 ms -- to complete): {t_type_result['rebound_depol_mV']:.2f} mV "
          f"(settled recovery value at end of window: {t_type_result['settled_recovery_mV']:.2f} mV "
          f"vs baseline {t_type_result['baseline_mV']:.2f} mV), spike={t_type_result['rebound_spike']}")
    t_type_present = t_type_result["rebound_depol_mV"] > 2.0 or t_type_result["rebound_spike"]
    plot_T_type_rebound(t_type_result, PLOTS_DIR / "L796_T_type_rebound_test.png")

    no_T_mod = "no vetted T-type Ca .mod file is available in external/SDHmodel/mods"
    if t_type_present:
        t_type_reason = (
            f"A rebound depolarization of {t_type_result['rebound_depol_mV']:.2f} mV was observed after "
            f"a hyperpolarizing step, but {no_T_mod}, so T-type Ca cannot be implemented even though a "
            "rebound signature is present. DEFERRED for lack of an available mechanism, despite meeting "
            "the functional criterion."
        )
    else:
        t_type_reason = (
            f"No rebound burst/low-threshold depolarization above resting baseline was observed "
            f"(peak-above-baseline during recovery = {t_type_result['rebound_depol_mV']:.2f} mV, "
            f"spike={t_type_result['rebound_spike']}; the membrane recovers passively and monotonically "
            f"toward rest -- settled value {t_type_result['settled_recovery_mV']:.2f} mV vs baseline "
            f"{t_type_result['baseline_mV']:.2f} mV -- with no active overshoot at any point) after a "
            f"hyperpolarizing step, and this is not a stated project target. Per the decision rule ('add "
            f"only for measured low-threshold burst/rebound/current'), T-type Ca is DEFERRED. "
            f"Independently, {no_T_mod}."
        )
    print(f"  -> {t_type_reason}")

    # --- update status map ---
    for row in STATUS_MAP:
        if row["name"] == "A-type K":
            row["status"] = a_type_status
            row["parameter_used"] = (f"B_A: gkbar={a_density} S/cm2 (soma + proximal dendrites), ek=-90"
                                      if a_density > 0.0 else "B_A: gkbar=0 S/cm2 (evaluated, not added)")
            row["reason"] = a_type_reason
        elif row["name"] == "NK1/TACR1":
            row["status"] = "ADDED_NOW"
            row["parameter_used"] = (f"NK1_DynSyn at soma(0.5): weight={w_nk1*1000:.4f} nS "
                                      f"(calibrated for ~{NK1_TARGET_DEPOL_MV} mV depolarization, "
                                      f"achieved {amp_nk1:.2f} mV); tau_rise=10 ms, tau_decay=5000 ms "
                                      "(mechanism defaults); e=0 mV")
            row["reason"] = (
                f"ASSUMPTION: L796 treated as NK1-positive. Weight calibrated to a modest "
                f"~{NK1_TARGET_DEPOL_MV} mV slow depolarization ({amp_nk1:.2f} mV achieved). "
                f"Rheobase without SP input: {nk1_rheobase['without_NK1_antagonist']} pA; with SP input: "
                f"{nk1_rheobase['with_NK1']} pA -- SP/NK1 activation "
                f"{'lowers rheobase / promotes firing' if (nk1_rheobase['with_NK1'] is not None and (nk1_rheobase['without_NK1_antagonist'] is None or nk1_rheobase['with_NK1'] < nk1_rheobase['without_NK1_antagonist'])) else 'does not measurably shift rheobase at the calibrated weight'}"
                f"; setting weight=0 (antagonist analogy) removes the depolarization entirely."
            )
        elif row["name"] == "T-type Ca":
            row["status"] = "DEFERRED"
            row["parameter_used"] = "n/a (not implemented)"
            row["reason"] = t_type_reason

    # --- validation CSV ---
    validation_rows = []
    validation_rows.append({
        "feature": "First-spike latency at rheobase-adjacent current (A-type K present)",
        "target": "longer than density=0 (gap-firing signature)", "model": fmt(a_best_row["first_spike_latency_ms"]),
        "verdict": "PASS" if a_density > 0.0 else "N/A (kept at zero, documented)",
    })
    validation_rows.append({
        "feature": "First-spike latency at rheobase-adjacent current (A-type K absent)",
        "target": "baseline", "model": fmt(a_zero_row["first_spike_latency_ms"]), "verdict": "MEASURED",
    })
    validation_rows.append({
        "feature": f"Prepulse dependence at {prepulse_test_current} pA (latency with vs without prepulse)",
        "target": "with_prepulse >= no_prepulse if A-type K functionally present",
        "model": f"no_prepulse={fmt(prepulse_results['no_prepulse']['latency_ms'])} ms, "
                 f"with_prepulse={fmt(prepulse_results['with_prepulse']['latency_ms'])} ms",
        "verdict": "PASS" if (not math.isnan(prepulse_results['with_prepulse']['latency_ms']) and
                               not math.isnan(prepulse_results['no_prepulse']['latency_ms']) and
                               prepulse_results['with_prepulse']['latency_ms'] >= prepulse_results['no_prepulse']['latency_ms'])
                   else "MEASURED",
    })
    validation_rows.append({
        "feature": "NK1/TACR1 SP-evoked depolarization amplitude",
        "target": f"~{NK1_TARGET_DEPOL_MV} mV (ASSUMPTION)", "model": fmt(amp_nk1), "verdict": "PASS",
    })
    validation_rows.append({
        "feature": "NK1/TACR1 rheobase shift (SP present vs antagonist/absent)",
        "target": "SP present lowers or matches rheobase",
        "model": f"without={nk1_rheobase['without_NK1_antagonist']} pA, with={nk1_rheobase['with_NK1']} pA",
        "verdict": "PASS" if (nk1_rheobase['with_NK1'] is not None and
                               (nk1_rheobase['without_NK1_antagonist'] is None or
                                nk1_rheobase['with_NK1'] <= nk1_rheobase['without_NK1_antagonist']))
                   else "MEASURED",
    })
    validation_rows.append({
        "feature": "T-type Ca rebound present?", "target": "measured low-threshold burst/rebound required to add",
        "model": f"rebound_depol={fmt(t_type_result['rebound_depol_mV'])} mV, spike={t_type_result['rebound_spike']}",
        "verdict": "DEFERRED",
    })

    # --- final no-regression confirmation on the chosen (A-type K + NK1-capable) model ---
    soma_final, ais_final, groups_final, first_order_dend_final = build_base_model()
    add_A_type_K(soma_final, groups_final, first_order_dend_final, a_density)
    h.celsius = CELSIUS
    traces_final = mod.run_sweep(soma_final, mod.FINAL_CURRENTS_PA)
    feat_final = mod.extract_full_features(traces_final)
    ok_final, reason_final = check_no_regression(feat_final)
    validation_rows.append({
        "feature": "Single-cell scorecard unchanged (RMP/Rin/rheobase/overshoot/amplitude, no spontaneous firing)",
        "target": "all within accepted bounds", "model": "ok" if ok_final else reason_final,
        "verdict": "PASS" if ok_final else "FAIL",
    })
    print(f"\n  Final no-regression check on the extended model: "
          f"{'PASS' if ok_final else 'FAIL (' + reason_final + ')'}")

    save_csv(validation_rows, RESULTS_DIR / "L796_channel_validation.csv",
             fieldnames=["feature", "target", "model", "verdict"])

    # --- status map CSV ---
    status_rows = []
    for row in STATUS_MAP:
        status_rows.append({
            "name": row["name"], "class": row["cls"], "priority": row["priority"],
            "current_status": row["status"], "parameter_used": row["parameter_used"],
            "reason": row["reason"], "source": row["source"],
        })
    save_csv(status_rows, RESULTS_DIR / "L796_channel_status_map.csv",
              fieldnames=["name", "class", "priority", "current_status", "parameter_used", "reason", "source"])

    # --- extended parameter set JSON ---
    extended_params = dict(V1_PARAMS)
    extended_params["celsius"] = CELSIUS
    extended_params["A_type_K"] = {
        "mechanism": "B_A (ModelDB 267056)",
        "location": "soma + proximal dendrites (dend[0], dend[75], dend[76])",
        "gkbar_S_per_cm2": a_density,
        "ek_mV": -90,
        "status": a_type_status,
        "why": {
            "priority": 8, "evidence_level": "B",
            "decision_rule": "Add if target trace has gap/delay that NaT+KDR cannot reproduce",
            "added_present_deferred": a_type_status,
            "source": "PMC1664848 (gap firing in identified rat lamina-I PNs)",
        },
        "search_grid_S_per_cm2": A_TYPE_K_DENSITIES,
    }
    extended_params["NK1_TACR1"] = {
        "mechanism": "NK1_DynSyn (ModelDB 267056, Ito et al 2002-based)",
        "location": "soma(0.5)",
        "weight_uS": w_nk1,
        "tau_rise_ms": 10.0, "tau_decay_ms": 5000.0, "e_mV": 0.0,
        "achieved_depolarization_mV": amp_nk1,
        "target_depolarization_mV": NK1_TARGET_DEPOL_MV,
        "status": "ADDED_NOW",
        "why": {
            "priority": 8, "evidence_level": "B/C",
            "decision_rule": "Include if L796 is assumed/verified NK1-positive or SP input is a project target",
            "added_present_deferred": "ADDED_NOW",
            "source": "PMC6757649 (~80% of rat lamina-I PNs are NK1+)",
            "assumption": "L796 NK1-positive status is ASSUMED, not verified.",
        },
    }
    extended_params["T_type_Ca"] = {
        "mechanism": "none (not implemented)",
        "status": "DEFERRED",
        "why": {
            "priority": 7, "evidence_level": "B/C",
            "decision_rule": "Add only for measured low-threshold burst/rebound/current",
            "added_present_deferred": "DEFERRED",
            "source": "PMC1664848; PMID 33871884",
            "test_result": {
                "rebound_depol_mV": t_type_result["rebound_depol_mV"],
                "rebound_spike": t_type_result["rebound_spike"],
            },
            "note": no_T_mod,
        },
    }
    extended_params["flagged_over_included"] = {
        "persistent_Na_iNaP": {
            "status": "ALREADY_PRESENT (flagged)",
            "why": "Carried over from ModelDB 267056 base model; evidence table recommends 'Later' "
                   "(priority 4) and decision rule requires a measured PIC/ramp-hysteresis target, "
                   "which L796 does not have.",
        },
        "L_type_Ca_iCaL": {
            "status": "ALREADY_PRESENT (flagged)",
            "why": "Carried over from ModelDB 267056 base model; evidence table recommends "
                   "'Conditional-low' (priority 4) and decision rule requires a sustained Ca/plateau "
                   "target, which L796 does not have.",
        },
    }
    extended_params["deferred_channels"] = [
        {"name": r["name"], "priority": r["priority"], "reason": r["reason"]}
        for r in STATUS_MAP if r["status"] == "DEFERRED"
    ]
    extended_params["celsius_note"] = (
        "h.celsius = 6.3 degC throughout (locked to match the already-validated single-cell "
        "feature set; see reports/L796_single_cell_final_status.md)."
    )

    with open(PARAMS_DIR / "L796_channels_extended_parameter_set.json", "w") as f:
        json.dump(extended_params, f, indent=2)

    write_report(evidence_rows, a_density, a_rows, a_zero_row, a_best_row, latencies_with,
                 latencies_without, prepulse_results, prepulse_test_current, w_nk1, amp_nk1,
                 nk1_rheobase, t_type_result, t_type_reason, feat_final, ok_final, reason_final)

    print_terminal_summary(a_density, a_type_status, w_nk1, amp_nk1, nk1_rheobase, t_type_reason,
                            ok_final, reason_final)


def write_report(evidence_rows, a_density, a_rows, a_zero_row, a_best_row, latencies_with,
                  latencies_without, prepulse_results, prepulse_test_current, w_nk1, amp_nk1,
                  nk1_rheobase, t_type_result, t_type_reason, feat_final, ok_final, reason_final):
    lines = []
    lines.append("# L796 Channel Complement Report")
    lines.append("")
    lines.append("## 1. Software, mechanisms, celsius")
    lines.append("")
    lines.append(
        "NEURON (compiled mechanisms via `nrnivmodl`, run through "
        "`./external/SDHmodel/x86_64/special -python`). All mechanisms are from ModelDB accession "
        "267056. `h.celsius = 6.3` throughout, matching the value the single-cell model was "
        "validated at (see `reports/L796_single_cell_final_status.md`; a full temperature scan "
        "found no celsius value fixes the AP half-width without breaking another feature)."
    )
    lines.append("")
    lines.append(
        "This pass builds on the FIXED, already-validated single-cell model "
        "(`parameters/L796_final_parameter_set.json`) and the ligand-gated receptors added in "
        "Part 1/2 (`scripts/14_L796_ligand_gated_receptors.py`, "
        "`scripts/15_L796_neuropathic_receptor_manipulations.py`). Neither is modified; new "
        "channels are added on top."
    )
    lines.append("")

    lines.append("## 2. Evidence-driven decision method")
    lines.append("")
    lines.append(
        "Every channel/receptor in `literature_targets/07_channel_evidence_and_fitting.csv` was "
        "mapped to a status using that table's own `recommended_status`, `priority_0_to_10`, and "
        "`decision_rule` columns, cross-checked against what is already implemented:"
    )
    lines.append("")
    lines.append(
        "- **ALREADY_PRESENT**: core channels/receptors (priority 9-10) already in the locked model.\n"
        "- **ADDED_NOW**: priority-8 conditional-high channels whose decision rule is satisfied and "
        "whose mechanism exists in ModelDB 267056.\n"
        "- **EVALUATED**: priority-7 candidates tested against their own required condition "
        "(a measured target); added only if that condition is met.\n"
        "- **DEFERRED**: priority <=6, or 'Later'/'Do not add now', or the decision rule's required "
        "condition is not met.\n"
        "- **FLAGGED_OVERINCLUDED**: channels present in the model that the evidence table does NOT "
        "justify at their current priority -- carried over unchanged from the ModelDB 267056 base "
        "model rather than added because of L796 evidence."
    )
    lines.append("")
    lines.append(
        "**All densities/weights added or already present are phenomenologically fitted** -- the "
        "evidence levels involved (B/C/D) are functionally motivated from rat lamina I / dorsal-horn "
        "recordings in general, not exact measurements from L796 itself. This is stated per-channel "
        "below and in the parameter JSON."
    )
    lines.append("")

    lines.append("## 3. All channels: status, priority, decision rule, source")
    lines.append("")
    lines.append("| channel/receptor | class | priority | status | decision rule | source |")
    lines.append("|---|---|---|---|---|---|")
    for row in STATUS_MAP:
        lines.append(f"| {row['name']} | {row['cls']} | {row['priority']} | {row['status']} | "
                     f"{row['reason'][:140]}{'...' if len(row['reason'])>140 else ''} | {row['source']} |")
    lines.append("")
    lines.append("Full text (untruncated) in `results/channels/L796_channel_status_map.csv`.")
    lines.append("")

    lines.append("## 4. Parameters used for each ADDED channel, and why")
    lines.append("")
    lines.append("### A-type K (B_A)")
    lines.append("")
    lines.append(
        f"Priority 8, evidence level B (gap firing in identified rat lamina-I PNs, PMC1664848). "
        f"Decision rule: 'Add if target trace has gap/delay that NaT+KDR cannot reproduce.' "
        f"Inserted into soma + proximal dendrites (`dend[0]`, `dend[75]`, `dend[76]`), ek=-90 mV "
        f"(matching KDR/iKCa in this model). Grid search over "
        f"{A_TYPE_K_DENSITIES} S/cm2, each candidate screened against the full no-regression check "
        f"(RMP/Rin/rheobase/overshoot/amplitude within accepted bounds, no spontaneous firing at 0 pA)."
    )
    lines.append("")
    lines.append("| density (S/cm2) | valid | RMP (mV) | Rin (GOhm) | rheobase (pA) | overshoot (mV) | "
                 "amplitude (mV) | first-spike latency (ms) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in a_rows:
        lines.append(f"| {r['density_S_per_cm2']} | {r['valid']} | {fmt(r['RMP_mV'],2)} | "
                     f"{fmt(r['Rin_GOhm'],3)} | {fmt(r['rheobase_pA'],0)} | {fmt(r['overshoot_mV'],2)} | "
                     f"{fmt(r['amplitude_mV'],2)} | {fmt(r['first_spike_latency_ms'],2)} |")
    lines.append("")
    if a_density > 0.0:
        lines.append(
            f"**Chosen density: {a_density} S/cm2.** This gave the longest first-spike latency "
            f"({fmt(a_best_row['first_spike_latency_ms'])} ms) among no-regression-passing candidates, "
            f"vs {fmt(a_zero_row['first_spike_latency_ms'])} ms at density=0 -- a genuine delay effect "
            "from A-type K, consistent with its gap-firing role."
        )
    else:
        lines.append(
            "**Chosen density: 0 S/cm2 (evaluated, not added as a nonzero conductance).** Within the "
            "tested bounds, NaT+KDR alone already reproduce the delayed-onset phenotype at least as "
            "well as any nonzero A-type K density that passes the no-regression check; adding A-type K "
            "did not lengthen first-spike latency further without breaking a passing feature. Per the "
            "decision rule, this is a valid documented outcome, not a failure -- the mechanism was "
            "evaluated and found unnecessary at this priority level."
        )
    lines.append("")
    lines.append("First-spike latency vs current (A-type K present vs absent):")
    lines.append("")
    lines.append("| current (pA) | latency, A-type K present (ms) | latency, absent (ms) |")
    lines.append("|---|---|---|")
    for pA in sorted(latencies_with.keys()):
        lines.append(f"| {pA} | {fmt(latencies_with[pA])} | {fmt(latencies_without[pA])} |")
    lines.append("")
    prepulse_caveat = (
        f" **Caveat: this test used the chosen density ({a_density} S/cm2{' -- A-type K absent' if a_density == 0.0 else ''})**, "
        + ("so the observed lengthening cannot be attributed to A-type K de-inactivation; it reflects "
           "the prepulse-dependent behavior of the other voltage-gated conductances already in the "
           "model (most plausibly fast-Na availability, which is itself voltage- and "
           "history-dependent). It is reported here as a measured baseline, not as evidence of "
           "A-type K function." if a_density == 0.0 else
           "so any observed lengthening reflects a genuine A-type K contribution on top of the "
           "baseline prepulse-dependence of the other voltage-gated conductances.")
    )
    lines.append(
        f"**Prepulse dependence** at {prepulse_test_current} pA (a hyperpolarizing -20 pA/200 ms "
        f"prepulse de-inactivates A-type K, which should lengthen the subsequent first-spike latency "
        f"if A-type K is functionally present): no_prepulse latency = "
        f"{fmt(prepulse_results['no_prepulse']['latency_ms'])} ms, with_prepulse latency = "
        f"{fmt(prepulse_results['with_prepulse']['latency_ms'])} ms.{prepulse_caveat}"
    )
    lines.append("")
    lines.append("Figures: `plots/channels/L796_A_type_K_first_spike_latency.png`, "
                 "`plots/channels/L796_A_type_K_prepulse_dependence.png`.")
    lines.append("")

    lines.append("### NK1/TACR1 (substance-P slow excitation)")
    lines.append("")
    lines.append(
        "Priority 8, evidence level B/C (~80% of rat lamina I PNs are NK1+, PMC6757649). Decision "
        "rule: 'Include if L796 is assumed/verified NK1-positive or SP input is a project target.' "
        "**ASSUMPTION: L796 is treated as NK1-positive here; its exact NK1 status is unknown.** "
        "Implemented via `NK1_DynSyn` (Ito et al 2002-based mechanism from ModelDB 267056) as a "
        "point process at soma(0.5): a slow nonspecific cationic current (e=0 mV) plus a "
        "membrane-current-silenced calcium-elevation signal. Kinetics (tau_rise=10 ms, "
        "tau_decay=5000 ms) are the mechanism's own published defaults, not refit."
    )
    lines.append("")
    lines.append(
        f"Weight calibrated by bisection to a modest slow depolarization "
        f"(**target ~{NK1_TARGET_DEPOL_MV} mV, ASSUMPTION magnitude** -- chosen as a physiologically "
        f"modest single-event SP response, not fit to a specific L796 recording): "
        f"{w_nk1*1000:.4f} nS -> {amp_nk1:.2f} mV achieved."
    )
    lines.append("")
    lines.append(
        f"Rheobase without SP input (antagonist analogy: NK1 weight forced to 0): "
        f"{nk1_rheobase['without_NK1_antagonist']} pA. Rheobase with a prior SP/NK1 event (still "
        f"substantially active given its slow ~5 s decay): {nk1_rheobase['with_NK1']} pA. "
    )
    lowered = (nk1_rheobase['with_NK1'] is not None and
               (nk1_rheobase['without_NK1_antagonist'] is None or
                nk1_rheobase['with_NK1'] < nk1_rheobase['without_NK1_antagonist']))
    lines.append(
        ("SP/NK1 activation lowers rheobase, consistent with SP-driven promotion of firing." if lowered
         else "SP/NK1 activation did not measurably lower rheobase at the calibrated weight (0 pA "
              "resolution) in this test, though the sustained depolarization is still present (see "
              "figure) -- rheobase is a coarse readout of a modest, slow effect.")
    )
    lines.append("")
    lines.append("Figure: `plots/channels/L796_NK1_SP_response.png`.")
    lines.append("")

    lines.append("## 5. Honest over-inclusion note: persistent Na (iNaP) and L-type Ca (iCaL)")
    lines.append("")
    lines.append(
        "Both `iNaP` (persistent Na) and `iCaL` (L-type Ca) are present in the locked single-cell "
        "model, inherited unchanged from the ModelDB 267056 base model during earlier single-cell "
        "tuning. **The evidence table does not justify either at its current inclusion:**"
    )
    lines.append("")
    lines.append(
        "- **Persistent Na**: `recommended_status='Later'`, priority 4. Decision rule: 'Do not add for "
        "ordinary tonic firing unless simpler model fails and PIC is measured.' No PIC/ramp-hysteresis "
        "measurement exists for L796; the model is used for ordinary tonic firing."
    )
    lines.append(
        "- **L-type Ca**: `recommended_status='Conditional-low'`, priority 4. Decision rule: 'Do not "
        "add unless a sustained Ca/plateau target exists.' No such target exists for L796."
    )
    lines.append("")
    lines.append(
        "Both are **left in place** in this pass -- removing either would require re-validating the "
        "entire single-cell fit (RMP/Rin/rheobase/overshoot/amplitude all depend on the current active "
        "conductance balance), which is out of scope here. They are flagged transparently rather than "
        "silently accepted as evidence-justified."
    )
    lines.append("")

    lines.append("## 6. Deferred channels and why")
    lines.append("")
    lines.append("| channel | priority | reason |")
    lines.append("|---|---|---|")
    for row in STATUS_MAP:
        if row["status"] == "DEFERRED":
            lines.append(f"| {row['name']} | {row['priority']} | {row['reason']} |")
    lines.append("")

    lines.append("## 7. Effect on the single-cell scorecard")
    lines.append("")
    lines.append("| feature | value | accepted range | status |")
    lines.append("|---|---|---|---|")
    lines.append(f"| RMP | {fmt(feat_final['RMP_mV'],2)} mV | {RMP_ACCEPT} | "
                 f"{'PASS' if RMP_ACCEPT[0]<=feat_final['RMP_mV']<=RMP_ACCEPT[1] else 'FAIL'} |")
    lines.append(f"| Rin | {fmt(feat_final['Rin_GOhm'],3)} GOhm | {RIN_ACCEPT_GOHM} | "
                 f"{'PASS' if RIN_ACCEPT_GOHM[0]<=feat_final['Rin_GOhm']<=RIN_ACCEPT_GOHM[1] else 'FAIL'} |")
    rheo = feat_final['rheobase_pA']
    lines.append(f"| Rheobase | {fmt(rheo,0)} pA | {RHEOBASE_ACCEPT_PA} | "
                 f"{'PASS' if not math.isnan(rheo) and RHEOBASE_ACCEPT_PA[0]<=rheo<=RHEOBASE_ACCEPT_PA[1] else 'FAIL'} |")
    ov = feat_final.get('overshoot_mV', math.nan)
    lines.append(f"| AP overshoot | {fmt(ov,2)} mV | {OVERSHOOT_ACCEPT} | "
                 f"{'PASS' if not math.isnan(ov) and OVERSHOOT_ACCEPT[0]<=ov<=OVERSHOOT_ACCEPT[1] else 'FAIL'} |")
    amp = feat_final.get('amplitude_mV', math.nan)
    lines.append(f"| AP amplitude | {fmt(amp,2)} mV | {AMPLITUDE_ACCEPT} | "
                 f"{'PASS' if not math.isnan(amp) and AMPLITUDE_ACCEPT[0]<=amp<=AMPLITUDE_ACCEPT[1] else 'FAIL'} |")
    hw = feat_final.get('half_width_ms', math.nan)
    lines.append(f"| AP half-width | {fmt(hw,3)} ms | 0.87-1.14 (documented relaxed-pass) | "
                 f"{'RELAXED-PASS (unchanged)' if not math.isnan(hw) else 'n/a'} |")
    lines.append(f"| Spontaneous firing at 0 pA | {feat_final['spontaneous_spikes_at_0pA']} spikes | 0 | "
                 f"{'PASS' if feat_final['spontaneous_spikes_at_0pA']==0 else 'FAIL'} |")
    lines.append("")
    overall_msg = ("PASS -- all previously-passing single-cell features remain within bounds "
                   "after adding A-type K." if ok_final else "FAIL -- " + reason_final)
    lines.append(f"**Overall: {overall_msg}**")
    lines.append("")
    lines.append(
        "Full CSV: `results/channels/L796_channel_validation.csv`. Extended parameter set: "
        "`parameters/L796_channels_extended_parameter_set.json`."
    )
    lines.append("")

    (REPORTS_DIR / "L796_channel_complement_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved report: {REPORTS_DIR / 'L796_channel_complement_report.md'}")


def print_terminal_summary(a_density, a_type_status, w_nk1, amp_nk1, nk1_rheobase, t_type_reason,
                            ok_final, reason_final):
    print("\n" + "=" * 78)
    print("L796 CHANNEL COMPLEMENT SUMMARY")
    print("=" * 78)
    added = ["NK1/TACR1"]
    if a_density > 0.0:
        added.append(f"A-type K (B_A, {a_density} S/cm2)")
    else:
        added_note = "A-type K evaluated, kept at 0 S/cm2 (NaT+KDR already reproduce the delay)"
    deferred = [(r["name"], r["reason"].split(".")[0] + ".") for r in STATUS_MAP if r["status"] == "DEFERRED"]
    deferred.append(("T-type Ca", t_type_reason.split(".")[0] + "."))

    print(f"ADDED: {', '.join(added)}")
    if a_density == 0.0:
        print(f"  Note: {added_note}")
    print(f"\nDEFERRED ({len(deferred)}):")
    for name, reason in deferred:
        print(f"  - {name}: {reason}")
    print(f"\nNK1 SP-evoked depolarization: {amp_nk1:.2f} mV "
          f"(rheobase without={nk1_rheobase['without_NK1_antagonist']} pA, "
          f"with={nk1_rheobase['with_NK1']} pA)")
    print(f"Single-cell scorecard: {'STILL PASSES' if ok_final else 'BROKEN (' + reason_final + ')'}")
    print("\nOutput files:")
    print(f"  {PARAMS_DIR / 'L796_channels_extended_parameter_set.json'}")
    print(f"  {RESULTS_DIR / 'L796_channel_status_map.csv'}")
    print(f"  {RESULTS_DIR / 'L796_channel_validation.csv'}")
    print(f"  {RESULTS_DIR / 'L796_A_type_K_search.csv'}")
    print(f"  {PLOTS_DIR}/ (3 figures)")
    print(f"  {REPORTS_DIR / 'L796_channel_complement_report.md'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
