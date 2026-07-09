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
# L796 PART 2: NEUROPATHIC-PAIN RECEPTOR MANIPULATIONS
# ============================================================
# Compares NORMAL vs NEUROPATHIC synaptic/passive parameters on the SAME
# fixed, already-validated L796 single-cell active model used in Part 1
# (scripts/14_L796_ligand_gated_receptors.py). Only synaptic weights and
# ECl are changed between conditions; the active conductance model itself
# is untouched.
#
# Manipulations (each tagged exact/range/model-derived/assumption; see
# literature_targets/06_receptor_target_values.csv):
#   - AMPA + NMDA conductance increase (central sensitization;
#     Latremoliere & Woolf 2009 J Pain 10:895-926) -- direction cited,
#     magnitude ASSUMPTION.
#   - GABA-A + glycine conductance decrease (disinhibition;
#     Coull JA et al 2003 Nature 424:938-942) -- direction cited,
#     magnitude ASSUMPTION.
#   - ECl depolarizing shift -70 -> -55 mV (KCC2 loss; Coull 2003) --
#     direction cited (literature-supported), magnitude ASSUMPTION
#     (task-suggested example value).
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
RESULTS_DIR = m.RESULTS_DIR
PLOTS_DIR = m.PLOTS_DIR
REPORTS_DIR = m.REPORTS_DIR

with open(RESULTS_DIR / "L796_receptor_calibration.json") as f:
    CALIB = json.load(f)

# -----------------------------
# Background ("tonic") synaptic drive
# -----------------------------
# A repeating 10 Hz train of AMPA+NMDA (excitatory) and GABA-A+Glycine
# (inhibitory) synaptic events throughout the 1 s current-clamp step,
# representing ongoing convergent synaptic input from primary afferents
# and local inhibitory interneurons. The scale (1.5x each receptor's
# Part-1 unitary weight) is chosen (MODEL-DERIVED, by direct scan) so the
# NORMAL condition's rheobase falls in a physiologically reasonable
# range (~50 pA, consistent with Part 1's phasic-input demonstrations)
# without spontaneous firing at 0 pA -- it is NOT a literature value.
BACKGROUND_FREQ_HZ = 10.0
BACKGROUND_BASE_SCALE = 1.5  # MODEL-DERIVED (tuned so NORMAL has a non-trivial rheobase)

# -----------------------------
# Neuropathic manipulations
# -----------------------------
NEUROPATHIC_AMPA_NMDA_MULTIPLIER = 1.5   # ASSUMPTION (direction: Latremoliere & Woolf 2009)
NEUROPATHIC_GABA_GLY_MULTIPLIER = 0.5    # ASSUMPTION (direction: Coull et al 2003)
NEUROPATHIC_ECL_MV = -55.0               # ASSUMPTION magnitude (direction: Coull et al 2003)
NORMAL_ECL_MV = CALIB["ecl_control_mV"]  # -70.0, EXACT (matches Part 1 control condition)

CONDITIONS = {
    "NORMAL": {
        "exc_scale": BACKGROUND_BASE_SCALE,
        "inh_scale": BACKGROUND_BASE_SCALE,
        "ecl_mV": NORMAL_ECL_MV,
    },
    "NEUROPATHIC": {
        "exc_scale": BACKGROUND_BASE_SCALE * NEUROPATHIC_AMPA_NMDA_MULTIPLIER,
        "inh_scale": BACKGROUND_BASE_SCALE * NEUROPATHIC_GABA_GLY_MULTIPLIER,
        "ecl_mV": NEUROPATHIC_ECL_MV,
    },
}

FI_CURRENTS_PA = list(range(0, 141, 10))  # 0-140 pA per task spec

# EPSP-to-spike conversion test: reuses Part 1's exact phasic excitatory
# train (2x unitary AMPA+NMDA weight, 50 Hz, 5 pulses) and population-scale
# (15x unitary) GABA-A+Glycine shunting input from the Part-1 shunting demo,
# now scaled per NORMAL/NEUROPATHIC condition.
EPSP_TRAIN_MULTIPLIER = 2.0     # matches Part 1 section1b_summation
SHUNT_INHIBITION_MULTIPLIER = 15.0  # matches Part 1 section2_inhibitory


# ============================================================
# MODEL SETUP
# ============================================================

def build_model_and_locations():
    soma, ais, groups, first_order_dend = m.build_validated_model()
    locs = m.pick_dendrite_locations(soma, groups)
    return soma, ais, groups, first_order_dend, locs


def build_background_drive(sec, exc_scale, inh_scale, ecl_mV, freq=BACKGROUND_FREQ_HZ, tstop=1000.0):
    """Repeating tonic AMPA+NMDA+GABA-A+Glycine drive at a single dendritic
    location. Returns a dict holding every created object so the caller can
    keep a reference alive for the duration of the simulation (NEURON does
    not keep point-process/NetStim objects alive on its own once their
    Python wrapper is garbage collected, even if a NetCon still refers to
    them -- see the _ACTIVE_NETCONS comment in script 14)."""
    interval = 1000.0 / freq
    number = int(tstop / interval)

    ampa = h.AMPA_DynSyn(sec(0.5))
    ampa.tau_rise, ampa.tau_decay, ampa.e = m.AMPA_TAU_RISE, m.AMPA_TAU_DECAY, m.AMPA_E
    nmda = h.NMDA_DynSyn(sec(0.5))
    nmda.tau_rise, nmda.tau_decay, nmda.e = m.NMDA_TAU_RISE, m.NMDA_TAU_DECAY, m.NMDA_E
    gaba = h.GABAa_DynSyn(sec(0.5))
    gaba.tau_rise, gaba.tau_decay, gaba.e = m.GABAA_TAU_RISE, m.GABAA_TAU_DECAY, ecl_mV
    gly = h.Glycine_DynSyn(sec(0.5))
    gly.tau_rise, gly.tau_decay, gly.e = m.GLY_TAU_RISE, m.GLY_TAU_DECAY, ecl_mV

    ns = m.make_netstim(start=0.0, number=number, interval=interval)

    w_ampa = CALIB["w_ampa_unitary_uS"] * exc_scale
    w_nmda = w_ampa * CALIB["w_nmda_ratio"]
    w_gaba = CALIB["w_gaba_uS"] * inh_scale
    w_gly = CALIB["w_gly_uS"] * inh_scale

    ncs = [
        m.new_netcon(ns, ampa, w_ampa),
        m.new_netcon(ns, nmda, w_nmda),
        m.new_netcon(ns, gaba, w_gaba),
        m.new_netcon(ns, gly, w_gly),
    ]
    return {"ampa": ampa, "nmda": nmda, "gaba": gaba, "gly": gly, "ns": ns, "ncs": ncs,
            "w_ampa": w_ampa, "w_nmda": w_nmda, "w_gaba": w_gaba, "w_gly": w_gly}


# ============================================================
# F-I / RHEOBASE / EXCITABILITY INDEX
# ============================================================

def run_fi_sweep(soma, sec, condition_params, currents_pA=FI_CURRENTS_PA, tstop=1000.0):
    spike_counts = {}
    for pA in currents_pA:
        m.reset_stimuli()
        _keepalive = build_background_drive(sec, condition_params["exc_scale"],
                                             condition_params["inh_scale"],
                                             condition_params["ecl_mV"], tstop=tstop)
        stim = h.IClamp(soma(0.5))
        stim.delay = 0.0
        stim.dur = tstop
        stim.amp = pA / 1000.0
        t, v = m.run_sim(tstop, record_secs={"soma": (soma, 0.5)})
        spikes = mod.count_spikes(t, v["soma"], threshold=mod.SPIKE_THRESHOLD)
        spike_counts[pA] = len(spikes)

    rheobase = None
    for pA in currents_pA:
        if spike_counts[pA] >= 1:
            rheobase = pA
            break

    excitability_index = sum(spike_counts.values())
    return spike_counts, rheobase, excitability_index


# ============================================================
# EPSP-TO-SPIKE CONVERSION (extends Part 1's shunting demonstration)
# ============================================================

def run_epsp_to_spike_test(soma, sec, condition_params, with_inhibition):
    m.reset_stimuli()
    w_ampa = CALIB["w_ampa_train_uS"] * condition_params["exc_scale"] / BACKGROUND_BASE_SCALE
    w_nmda = w_ampa * CALIB["w_nmda_ratio"]
    _keepalive_exc = m.build_ampa_nmda(sec, w_ampa, w_nmda=w_nmda, stim_time=300.0,
                                        number=5, interval=1000.0 / 50.0)
    _keepalive_inh = None
    if with_inhibition:
        w_gaba = CALIB["w_gaba_uS"] * SHUNT_INHIBITION_MULTIPLIER * \
            (condition_params["inh_scale"] / BACKGROUND_BASE_SCALE)
        w_gly = CALIB["w_gly_uS"] * SHUNT_INHIBITION_MULTIPLIER * \
            (condition_params["inh_scale"] / BACKGROUND_BASE_SCALE)
        gaba = h.GABAa_DynSyn(sec(0.5))
        gaba.tau_rise, gaba.tau_decay, gaba.e = m.GABAA_TAU_RISE, m.GABAA_TAU_DECAY, condition_params["ecl_mV"]
        gly = h.Glycine_DynSyn(sec(0.5))
        gly.tau_rise, gly.tau_decay, gly.e = m.GLY_TAU_RISE, m.GLY_TAU_DECAY, condition_params["ecl_mV"]
        ns = m.make_netstim(start=300.0, number=1)
        nc1 = m.new_netcon(ns, gaba, w_gaba)
        nc2 = m.new_netcon(ns, gly, w_gly)
        _keepalive_inh = (gaba, gly, ns, nc1, nc2)

    t, v = m.run_sim(600.0, record_secs={"soma": (soma, 0.5)})
    v_soma = v["soma"]
    post_mask = t >= 300.0
    peak_v = float(np.max(v_soma[post_mask]))
    spikes = mod.count_spikes(t[post_mask], v_soma[post_mask], threshold=mod.SPIKE_THRESHOLD)
    return peak_v, len(spikes) > 0, t, v_soma


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


def plot_fi_curve(fi_data, path):
    plt.figure(figsize=(8, 5))
    colors = {"NORMAL": "tab:blue", "NEUROPATHIC": "tab:red"}
    for cond, (spike_counts, rheobase, excitability) in fi_data.items():
        currents = sorted(spike_counts.keys())
        counts = [spike_counts[c] for c in currents]
        plt.plot(currents, counts, marker="o", label=f"{cond} (rheobase={rheobase} pA)",
                 color=colors.get(cond))
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Spike count during 1 s step (with tonic synaptic background)")
    plt.title("L796 F-I curve: NORMAL vs NEUROPATHIC")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_excitability_bar(fi_data, path):
    conds = list(fi_data.keys())
    values = [fi_data[c][2] for c in conds]
    colors = ["tab:blue" if c == "NORMAL" else "tab:red" for c in conds]
    plt.figure(figsize=(6, 5))
    plt.bar(conds, values, color=colors)
    for i, v in enumerate(values):
        plt.text(i, v + max(values) * 0.02, str(v), ha="center")
    plt.ylabel(f"Excitability index (sum of spikes, {FI_CURRENTS_PA[0]}-{FI_CURRENTS_PA[-1]} pA)")
    plt.title("L796 excitability index: NORMAL vs NEUROPATHIC")
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_epsp_conversion(traces, path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, cond in zip(axes, ["NORMAL", "NEUROPATHIC"]):
        for label in ["alone", "with_inhibition"]:
            t, v = traces[(cond, label)]
            mask = (t >= 280) & (t <= 600)
            ax.plot(t[mask], v[mask], label=label.replace("_", " "))
        ax.axhline(mod.SPIKE_THRESHOLD, linestyle="--", linewidth=1, color="k", alpha=0.5)
        ax.set_title(cond)
        ax.set_xlabel("Time (ms)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Somatic voltage (mV)")
    plt.suptitle("EPSP-to-spike conversion: excitatory train + inhibition, NORMAL vs NEUROPATHIC")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


# ============================================================
# REPORT APPEND / TERMINAL SUMMARY
# ============================================================

def fmt(v, nd=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:.{nd}f}"


def append_report(fi_data, epsp_results):
    report_path = REPORTS_DIR / "L796_ligand_gated_receptor_report.md"
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Part 2: Neuropathic-Pain Receptor Manipulations")
    lines.append("")
    lines.append(
        "NORMAL vs NEUROPATHIC synaptic parameters were compared on the SAME fixed, "
        "already-validated L796 active model used in Part 1. Only synaptic weights and ECl "
        "were changed; the active conductance model itself was not touched."
    )
    lines.append("")
    lines.append("## Manipulations")
    lines.append("")
    lines.append("| manipulation | value | tag | source |")
    lines.append("|---|---|---|---|")
    lines.append(f"| AMPA + NMDA conductance | x{NEUROPATHIC_AMPA_NMDA_MULTIPLIER:g} | "
                 "ASSUMPTION (direction cited, magnitude assumed) | "
                 "Latremoliere & Woolf 2009 J Pain 10:895-926 (central sensitization) |")
    lines.append(f"| GABA-A + glycine conductance | x{NEUROPATHIC_GABA_GLY_MULTIPLIER:g} | "
                 "ASSUMPTION (direction cited, magnitude assumed) | "
                 "Coull JA et al 2003 Nature 424:938-942 (disinhibition) |")
    lines.append(f"| ECl | {NORMAL_ECL_MV:g} -> {NEUROPATHIC_ECL_MV:g} mV | "
                 "ASSUMPTION magnitude (direction literature-supported) | "
                 "Coull JA et al 2003 Nature 424:938-942 (KCC2 loss) |")
    lines.append(
        f"| Background tonic synaptic drive scale | x{BACKGROUND_BASE_SCALE:g} "
        "(NORMAL baseline, both exc and inh) | MODEL-DERIVED "
        "(tuned so NORMAL has a non-trivial, non-zero rheobase; not a literature value) | "
        "This study (direct parameter scan) |"
    )
    lines.append("")
    lines.append(
        f"Background drive: a repeating {BACKGROUND_FREQ_HZ:g} Hz train of AMPA+NMDA and "
        "GABA-A+Glycine events at the proximal dendrite throughout each 1 s current-clamp "
        "step, representing ongoing convergent synaptic input. Without this tonic background, "
        "a bare current-clamp sweep cannot show any NORMAL-vs-NEUROPATHIC difference at all, "
        "since none of the manipulated parameters (synaptic weights, ECl) affect an "
        "unstimulated synapse -- this was confirmed directly during script development."
    )
    lines.append("")

    lines.append("## Rheobase, F-I curve, and excitability index")
    lines.append("")
    lines.append("| condition | rheobase (pA) | excitability index (sum of spikes, "
                 f"{FI_CURRENTS_PA[0]}-{FI_CURRENTS_PA[-1]} pA) |")
    lines.append("|---|---|---|")
    for cond, (spike_counts, rheobase, excitability) in fi_data.items():
        lines.append(f"| {cond} | {rheobase if rheobase is not None else 'no spikes in range'} | "
                     f"{excitability} |")
    lines.append("")

    rheo_normal = fi_data["NORMAL"][1]
    rheo_neuro = fi_data["NEUROPATHIC"][1]
    exc_normal = fi_data["NORMAL"][2]
    exc_neuro = fi_data["NEUROPATHIC"][2]
    rheobase_lowered = (rheo_neuro is not None and rheo_normal is not None and rheo_neuro < rheo_normal)
    firing_raised = exc_neuro > exc_normal
    lines.append(
        f"Rheobase: {'LOWERED' if rheobase_lowered else 'not lowered'} under NEUROPATHIC "
        f"({fmt(rheo_normal,0)} pA -> {fmt(rheo_neuro,0)} pA). "
        f"Excitability index: {'RAISED' if firing_raised else 'not raised'} under NEUROPATHIC "
        f"({exc_normal} -> {exc_neuro})."
    )
    lines.append("")
    lines.append("Figures: `plots/receptors/L796_normal_vs_neuropathic_FI.png`, "
                 "`plots/receptors/L796_excitability_index.png`.")
    lines.append("")

    lines.append("## EPSP-to-spike conversion (excitatory train + inhibition)")
    lines.append("")
    lines.append(
        "Reuses Part 1's exact phasic excitatory train (2x unitary AMPA+NMDA weight, 50 Hz, "
        "5 pulses) and population-scale (15x unitary) GABA-A+Glycine shunting input -- which "
        "was shown in Part 1 to BLOCK the train under normal/control synaptic weights -- now "
        "scaled per NORMAL/NEUROPATHIC condition:"
    )
    lines.append("")
    lines.append("| condition | excitatory train alone fires? | + inhibition fires? |")
    lines.append("|---|---|---|")
    for cond in ["NORMAL", "NEUROPATHIC"]:
        alone_fired = epsp_results[(cond, "alone")]["fired"]
        inhib_fired = epsp_results[(cond, "with_inhibition")]["fired"]
        lines.append(f"| {cond} | {alone_fired} | {inhib_fired} |")
    lines.append("")
    lines.append("Figure: `plots/receptors/L796_EPSP_to_spike_conversion.png`.")
    lines.append("")

    lines.append("## Part 2 limitations")
    lines.append("")
    lines.append(
        "- The tonic background synaptic drive (10 Hz, both exc and inh) and its "
        f"{BACKGROUND_BASE_SCALE:g}x baseline scale are a modeling device to make the "
        "synaptic manipulations visible in a somatic current-clamp F-I/rheobase readout -- "
        "they are not fit to any measured spontaneous synaptic activity rate in L796 or the "
        "dorsal horn."
    )
    lines.append(
        "- The AMPA/NMDA and GABA-A/glycine conductance-change magnitudes (1.5x and 0.5x) and "
        f"the ECl shift magnitude ({NORMAL_ECL_MV:g} to {NEUROPATHIC_ECL_MV:g} mV) are "
        "assumptions within the literature-cited direction of change, not fitted to a specific "
        "reported fold-change or mV value from Latremoliere & Woolf 2009 or Coull et al 2003."
    )
    lines.append(
        "- Optional additional nAChR/P2X/5-HT3 drive under the neuropathic condition was not "
        "added; P2X and 5-HT3 remain unimplemented (no vetted mechanism), and nAChR was left "
        "out of this specific comparison to keep the manipulation set directly tied to the two "
        "cited papers."
    )
    lines.append(
        "- This is a single-neuron demonstration; it does not model the network-level "
        "microglia-BDNF-KCC2 signaling cascade that produces the ECl shift in vivo (Coull et "
        "al 2003), only its downstream electrophysiological consequence."
    )
    lines.append("")

    report_path.write_text(existing + "\n".join(lines), encoding="utf-8")
    print(f"\nAppended Part 2 section to: {report_path}")


def print_terminal_summary(fi_data, epsp_results):
    print("\n" + "=" * 78)
    print("L796 PART 2 SUMMARY: NEUROPATHIC-PAIN MANIPULATIONS")
    print("=" * 78)
    rheo_normal = fi_data["NORMAL"][1]
    rheo_neuro = fi_data["NEUROPATHIC"][1]
    exc_normal = fi_data["NORMAL"][2]
    exc_neuro = fi_data["NEUROPATHIC"][2]
    print(f"Rheobase: NORMAL={rheo_normal} pA -> NEUROPATHIC={rheo_neuro} pA")
    print(f"Excitability index (0-140 pA): NORMAL={exc_normal} -> NEUROPATHIC={exc_neuro}")
    rheobase_lowered = (rheo_neuro is not None and rheo_normal is not None and rheo_neuro < rheo_normal)
    firing_raised = exc_neuro > exc_normal
    print(f"Rheobase lowered under neuropathic: {rheobase_lowered}")
    print(f"Firing raised under neuropathic: {firing_raised}")
    for cond in ["NORMAL", "NEUROPATHIC"]:
        alone = epsp_results[(cond, "alone")]["fired"]
        inhib = epsp_results[(cond, "with_inhibition")]["fired"]
        print(f"EPSP-to-spike ({cond}): train alone fires={alone}, train+inhibition fires={inhib}")
    print("=" * 78)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Building the fixed, already-validated L796 single-cell active model...")
    soma, ais, groups, first_order_dend, locs = build_model_and_locations()
    sec = locs["proximal"]["sec"]

    print("\n" + "=" * 78)
    print("RHEOBASE / F-I / EXCITABILITY INDEX: NORMAL vs NEUROPATHIC")
    print("=" * 78)

    fi_data = {}
    fi_rows = []
    for cond_name, params in CONDITIONS.items():
        print(f"\n  --- {cond_name} (exc_scale={params['exc_scale']:.2f}, "
              f"inh_scale={params['inh_scale']:.2f}, ECl={params['ecl_mV']:g} mV) ---")
        spike_counts, rheobase, excitability = run_fi_sweep(soma, sec, params)
        fi_data[cond_name] = (spike_counts, rheobase, excitability)
        print(f"    rheobase = {rheobase} pA, excitability index = {excitability}")
        for pA in FI_CURRENTS_PA:
            fi_rows.append({"condition": cond_name, "current_pA": pA,
                             "spike_count": spike_counts[pA]})

    print("\n" + "=" * 78)
    print("EPSP-TO-SPIKE CONVERSION: NORMAL vs NEUROPATHIC")
    print("=" * 78)

    epsp_results = {}
    epsp_traces = {}
    epsp_rows = []
    for cond_name, params in CONDITIONS.items():
        for label, with_inhibition in [("alone", False), ("with_inhibition", True)]:
            peak_v, fired, t, v_soma = run_epsp_to_spike_test(soma, sec, params, with_inhibition)
            epsp_results[(cond_name, label)] = {"peak_mV": peak_v, "fired": fired}
            epsp_traces[(cond_name, label)] = (t, v_soma)
            print(f"  {cond_name} {label}: peak={peak_v:.2f} mV, fired={fired}")
            epsp_rows.append({"condition": cond_name, "test": label,
                               "peak_mV": peak_v, "fired": fired})

    # --- save CSVs ---
    save_csv(fi_rows, RESULTS_DIR / "L796_normal_vs_neuropathic_FI.csv")
    excitability_rows = [{"condition": c, "rheobase_pA": fi_data[c][1],
                           "excitability_index": fi_data[c][2]} for c in CONDITIONS]
    save_csv(excitability_rows, RESULTS_DIR / "L796_excitability_index.csv")
    save_csv(epsp_rows, RESULTS_DIR / "L796_EPSP_to_spike_conversion.csv")

    # --- save plots ---
    plot_fi_curve(fi_data, PLOTS_DIR / "L796_normal_vs_neuropathic_FI.png")
    plot_excitability_bar(fi_data, PLOTS_DIR / "L796_excitability_index.png")
    plot_epsp_conversion(epsp_traces, PLOTS_DIR / "L796_EPSP_to_spike_conversion.png")

    append_report(fi_data, epsp_results)
    print_terminal_summary(fi_data, epsp_results)

    return fi_data, epsp_results


if __name__ == "__main__":
    main()
