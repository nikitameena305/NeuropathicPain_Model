import math
import csv
import os
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# STEP 3: L796 ACTIVE CONDUCTANCE GRID SEARCH
# Goal:
# Keep fitted passive model fixed.
# Add active conductances.
# Search B_Na, KDR, KCa, CaL combinations.
# Find combinations giving tonic / multi-spike firing.
# ============================================================


HERE = Path(__file__).resolve().parent
os.chdir(HERE)

SWC_FILE = "L796-ALT-PN.CNG.swc"

# Passive values from Step 2
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

# Paper-style current clamp
STIM_DELAY = 100.0
STIM_DUR = 500.0
TSTOP = 800.0
DT = 0.025

# Main fitting current.
# 60 pA was used in the paper figure examples for firing classification.
MAIN_CURRENT_NA = 0.06

# Search scales.
# Do not make this too huge first.
BNA_SCALES = [0.75, 1.00, 1.25, 1.50, 2.00]
KDR_SCALES = [0.25, 0.50, 0.75, 1.00, 1.25]
KCA_SCALES = [0.00, 0.50, 1.00, 2.00, 4.00]
CAL_SCALES = [0.50, 1.00, 2.00]

# After ranking, validate top models on these currents.
VALIDATION_CURRENTS_NA = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10]

# Baseline Medlock-like conductance densities.
# Units are S/cm2 for conductance density.
BASE = {
    # AIS
    "AIS_BNa": 3.45,          # 3450 mS/cm2
    "AIS_KDR": 0.076,         # 76 mS/cm2

    # Soma
    "soma_KDR": 0.001075,     # 1.075 mS/cm2
    "soma_iNaP": 0.0001,      # 0.1 mS/cm2
    "soma_CaL": 0.0001,       # 0.1 mS/cm2
    "soma_KCa": 0.0001,       # 0.1 mS/cm2

    # Dendrite
    "dend_KDR": 0.036,        # 36 mS/cm2
    "dend_CaAN": 0.000091,    # 0.091 mS/cm2
    "dend_CaL": 0.00003,      # 0.03 mS/cm2
    "dend_KCa": 0.001,        # 1 mS/cm2
}


# ============================================================
# MORPHOLOGY IMPORT
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
    """
    We create a separate AIS because Medlock's model has a specific AIS compartment.
    The original traced axon remains passive.
    """
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
        print(f"\n[ERROR] Could not insert mechanism {mech} in {sec.name()}")
        print("This usually means MOD mechanisms are not loaded.")
        print("Run this script with:")
        print("cd /path/to/NeuropathicPain_Model")
        print("./shared/mechanisms/medlock_267056/x86_64/special -python cells/L796_projection_neuron/scripts/L796_step3_active_grid_search.py")
        raise e


def insert_active_mechanisms(ais):
    groups = section_groups()

    # Soma mechanisms
    for sec in groups["soma"]:
        for mech in ["KDR", "iNaP", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ena = 55
        sec.ek = -90

    # Dendritic mechanisms
    dend_sections = groups["dend"] + groups["apic"]
    for sec in dend_sections:
        for mech in ["KDR", "iCaAN", "iCaL", "iKCa", "CaIntraCellDyn"]:
            safe_insert(sec, mech)
        sec.ek = -90

    # AIS mechanisms
    safe_insert(ais, "B_Na")
    safe_insert(ais, "KDR")
    ais.ena = 55
    ais.ek = -90

    # Original axon remains passive.
    # This avoids spreading AIS sodium conductance across the entire axonal arbor.


def set_active_conductances(ais, bna_scale, kdr_scale, kca_scale, cal_scale):
    groups = section_groups()

    # Soma
    for sec in groups["soma"]:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["soma_KDR"] * kdr_scale
        if h.ismembrane("iNaP", sec=sec):
            sec.gnabar_iNaP = BASE["soma_iNaP"]
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["soma_CaL"] * cal_scale
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["soma_KCa"] * kca_scale

    # Dendrites
    dend_sections = groups["dend"] + groups["apic"]
    for sec in dend_sections:
        if h.ismembrane("KDR", sec=sec):
            sec.gkbar_KDR = BASE["dend_KDR"] * kdr_scale
        if h.ismembrane("iCaAN", sec=sec):
            sec.gbar_iCaAN = BASE["dend_CaAN"]
        if h.ismembrane("iCaL", sec=sec):
            sec.pcabar_iCaL = BASE["dend_CaL"] * cal_scale
        if h.ismembrane("iKCa", sec=sec):
            sec.gbar_iKCa = BASE["dend_KCa"] * kca_scale

    # AIS
    if h.ismembrane("B_Na", sec=ais):
        ais.gnabar_B_Na = BASE["AIS_BNa"] * bna_scale
    if h.ismembrane("KDR", sec=ais):
        ais.gkbar_KDR = BASE["AIS_KDR"] * kdr_scale


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def count_spikes(t, v, threshold=-20.0, refractory_ms=2.0):
    """
    Spike count by upward threshold crossings.
    """
    spike_times = []
    last_spike_time = -1e9

    for i in range(1, len(v)):
        if v[i - 1] < threshold and v[i] >= threshold:
            if t[i] - last_spike_time >= refractory_ms:
                spike_times.append(t[i])
                last_spike_time = t[i]

    return spike_times


def run_sim(soma, ais, current_na, bna_scale, kdr_scale, kca_scale, cal_scale, save_trace=False, tag="trace"):
    set_active_conductances(ais, bna_scale, kdr_scale, kca_scale, cal_scale)

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

    ais_spike_times = count_spikes(t[stim_mask], ais_v[stim_mask], threshold=-20.0)
    soma_spike_times = count_spikes(t[stim_mask], soma_v[stim_mask], threshold=-20.0)

    features = {
        "current_nA": current_na,
        "BNa_scale": bna_scale,
        "KDR_scale": kdr_scale,
        "KCa_scale": kca_scale,
        "CaL_scale": cal_scale,
        "rest_soma_mV": float(np.mean(soma_v[base_mask])),
        "rest_AIS_mV": float(np.mean(ais_v[base_mask])),
        "max_soma_mV": float(np.max(soma_v[stim_mask])),
        "max_AIS_mV": float(np.max(ais_v[stim_mask])),
        "min_soma_mV": float(np.min(soma_v[stim_mask])),
        "min_AIS_mV": float(np.min(ais_v[stim_mask])),
        "plateau_soma_mV": float(np.mean(soma_v[late_mask])),
        "plateau_AIS_mV": float(np.mean(ais_v[late_mask])),
        "recovery_soma_mV": float(np.mean(soma_v[rec_mask])),
        "recovery_AIS_mV": float(np.mean(ais_v[rec_mask])),
        "AIS_spike_count": len(ais_spike_times),
        "soma_spike_count": len(soma_spike_times),
        "AIS_first_latency_ms": float(ais_spike_times[0] - STIM_DELAY) if ais_spike_times else math.nan,
    }

    if save_trace:
        dat_name = f"{tag}.dat"
        with open(dat_name, "w") as f:
            f.write("time_ms soma_mV ais_mV\n")
            for ti, sv, av in zip(t, soma_v, ais_v):
                f.write(f"{ti:.6f} {sv:.6f} {av:.6f}\n")

        png_name = f"{tag}.png"
        plt.figure(figsize=(10, 5))
        plt.plot(t, soma_v, label="soma")
        plt.plot(t, ais_v, label="AIS")
        plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15, label="current injection")
        plt.axhline(-20, linestyle="--", linewidth=1, label="-20 mV spike screen")
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (mV)")
        plt.title(
            f"L796 active: I={current_na*1000:.0f} pA, "
            f"BNa={bna_scale} KDR={kdr_scale} KCa={kca_scale} CaL={cal_scale}"
        )
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(png_name, dpi=250)
        plt.close()

    return features


def score_candidate(rest_features, main_features):
    """
    Higher score = more useful candidate for tonic PN model.
    """
    score = 0.0

    # Must not spontaneously spike at 0 current.
    if rest_features["AIS_spike_count"] == 0 and rest_features["max_AIS_mV"] < -20:
        score += 50
    else:
        score -= 200

    # Rest should stay close to -72.8 mV.
    score -= abs(rest_features["rest_soma_mV"] - E_PAS) * 5

    # Main target: repetitive firing during 60 pA.
    spike_count = main_features["AIS_spike_count"]

    if spike_count >= 3:
        score += 150
    elif spike_count == 2:
        score += 80
    elif spike_count == 1:
        score += 20
    else:
        score -= 50

    # AP should cross 0 mV if true spike.
    if main_features["max_AIS_mV"] > 0:
        score += 30
    else:
        score -= 30

    # Prefer not being stuck in very depolarized plateau if only one spike.
    if spike_count <= 1 and main_features["plateau_AIS_mV"] > -45:
        score -= 30

    # Recovery after pulse should trend back toward rest.
    score -= abs(main_features["recovery_soma_mV"] - E_PAS) * 2

    # Latency should not be extremely delayed.
    lat = main_features["AIS_first_latency_ms"]
    if not math.isnan(lat):
        if lat < 100:
            score += 10
        else:
            score -= 10

    return score


# ============================================================
# MAIN GRID SEARCH
# ============================================================

def main():
    print("Step 3: importing L796 morphology...")
    import_morphology()

    changed = fix_tiny_diameters(0.2)
    set_nseg_dlambda(freq=100, d_lambda=0.1)

    soma = find_soma()
    insert_passive_everywhere()
    ais = create_artificial_ais(soma)
    insert_active_mechanisms(ais)

    print(f"Imported sections: {len(list(h.allsec()))}")
    print(f"Soma section: {soma.name()}")
    print(f"Artificial AIS added: {ais.name()}")
    print(f"Diameters corrected below 0.2 um: {changed}")
    print("Starting active conductance grid search...")

    results = []
    total = len(BNA_SCALES) * len(KDR_SCALES) * len(KCA_SCALES) * len(CAL_SCALES)
    counter = 0

    for bna in BNA_SCALES:
        for kdr in KDR_SCALES:
            for kca in KCA_SCALES:
                for cal in CAL_SCALES:
                    counter += 1
                    if counter % 25 == 0:
                        print(f"  {counter}/{total} combinations tested...")

                    rest = run_sim(soma, ais, 0.00, bna, kdr, kca, cal, save_trace=False)
                    mainf = run_sim(soma, ais, MAIN_CURRENT_NA, bna, kdr, kca, cal, save_trace=False)

                    score = score_candidate(rest, mainf)

                    row = dict(mainf)
                    row["rest_0nA_AIS_spike_count"] = rest["AIS_spike_count"]
                    row["rest_0nA_max_AIS_mV"] = rest["max_AIS_mV"]
                    row["score"] = score
                    results.append(row)

    # Sort best first
    results_sorted = sorted(results, key=lambda r: r["score"], reverse=True)

    fieldnames = [
        "score",
        "current_nA",
        "BNa_scale", "KDR_scale", "KCa_scale", "CaL_scale",
        "rest_0nA_AIS_spike_count", "rest_0nA_max_AIS_mV",
        "rest_soma_mV", "rest_AIS_mV",
        "max_soma_mV", "max_AIS_mV",
        "plateau_soma_mV", "plateau_AIS_mV",
        "recovery_soma_mV", "recovery_AIS_mV",
        "AIS_spike_count", "soma_spike_count",
        "AIS_first_latency_ms",
        "min_soma_mV", "min_AIS_mV",
    ]

    with open("L796_active_grid_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results_sorted:
            writer.writerow(r)

    with open("L796_active_grid_top20.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results_sorted[:20]:
            writer.writerow(r)

    multispike = [r for r in results_sorted if r["AIS_spike_count"] >= 2]

    with open("L796_active_multispike_candidates.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in multispike:
            writer.writerow(r)

    print("\nGrid search finished.")
    print(f"Total combinations: {len(results_sorted)}")
    print(f"Multi-spike candidates: {len(multispike)}")

    if results_sorted:
        best = results_sorted[0]
        print("\nBest candidate:")
        for k in ["score", "BNa_scale", "KDR_scale", "KCa_scale", "CaL_scale",
                  "AIS_spike_count", "max_AIS_mV", "plateau_AIS_mV",
                  "recovery_soma_mV", "AIS_first_latency_ms"]:
            print(f"  {k}: {best[k]}")

    # Plot score distribution
    plt.figure(figsize=(8, 5))
    plt.hist([r["score"] for r in results_sorted], bins=30)
    plt.xlabel("Score")
    plt.ylabel("Number of models")
    plt.title("L796 active grid search score distribution")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("L796_active_score_distribution.png", dpi=250)
    plt.close()

    # Plot spike count distribution
    counts = defaultdict(int)
    for r in results_sorted:
        counts[int(r["AIS_spike_count"])] += 1

    plt.figure(figsize=(8, 5))
    xs = sorted(counts.keys())
    ys = [counts[x] for x in xs]
    plt.bar([str(x) for x in xs], ys)
    plt.xlabel("AIS spike count at 60 pA")
    plt.ylabel("Number of models")
    plt.title("L796 active grid: spike-count distribution")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("L796_active_spike_count_distribution.png", dpi=250)
    plt.close()

    # Save traces of top 5
    Path("L796_active_top_traces").mkdir(exist_ok=True)
    for i, r in enumerate(results_sorted[:5], start=1):
        tag = (
            f"L796_active_top_traces/top{i}_"
            f"BNa{r['BNa_scale']}_KDR{r['KDR_scale']}_KCa{r['KCa_scale']}_CaL{r['CaL_scale']}"
        ).replace(".", "p")
        run_sim(
            soma, ais, MAIN_CURRENT_NA,
            r["BNa_scale"], r["KDR_scale"], r["KCa_scale"], r["CaL_scale"],
            save_trace=True,
            tag=tag
        )

    # Validate top 3 over multiple currents
    validation_rows = []
    for rank, r in enumerate(results_sorted[:3], start=1):
        for cur in VALIDATION_CURRENTS_NA:
            vf = run_sim(
                soma, ais, cur,
                r["BNa_scale"], r["KDR_scale"], r["KCa_scale"], r["CaL_scale"],
                save_trace=False
            )
            vf["rank"] = rank
            validation_rows.append(vf)

    val_fields = ["rank"] + fieldnames[1:-3]
    with open("L796_active_top3_validation_FI.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=val_fields)
        writer.writeheader()
        for r in validation_rows:
            writer.writerow({k: r.get(k, "") for k in val_fields})

    # F-I curve for top 3
    plt.figure(figsize=(8, 5))
    for rank in [1, 2, 3]:
        rows = [r for r in validation_rows if r["rank"] == rank]
        rows = sorted(rows, key=lambda x: x["current_nA"])
        plt.plot(
            [r["current_nA"] * 1000 for r in rows],
            [r["AIS_spike_count"] for r in rows],
            marker="o",
            label=f"Top {rank}"
        )

    plt.xlabel("Injected current (pA)")
    plt.ylabel("AIS spike count")
    plt.title("L796 active top candidates: F-I validation")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("L796_active_top3_FI_validation.png", dpi=250)
    plt.close()

    # Save report
    report = f"""
L796 STEP 3 ACTIVE GRID SEARCH REPORT
=====================================

Purpose:
To add active conductances to the passively fitted L796 morphology and search for conductance combinations
that produce projection-neuron-like tonic/repetitive firing.

Fixed passive values:
e_pas = {E_PAS} mV
g_pas = {G_PAS:.10e} S/cm2
cm = {CM} uF/cm2
Ra = {RA} ohm-cm

Active mechanisms used:
B_Na in artificial AIS
KDR in dendrite, soma, and AIS
iNaP in soma
iCaL in dendrite and soma
iCaAN in dendrite
iKCa in dendrite and soma
CaIntraCellDyn in dendrite and soma

Why artificial AIS:
Medlock-style active mechanisms use a separate AIS compartment. The original traced axon was kept passive
to avoid spreading AIS sodium conductance across the full axonal arbor.

Main current tested:
{MAIN_CURRENT_NA*1000:.1f} pA for {STIM_DUR:.1f} ms

Grid tested:
B_Na scales = {BNA_SCALES}
KDR scales = {KDR_SCALES}
KCa scales = {KCA_SCALES}
CaL scales = {CAL_SCALES}

Total combinations tested = {len(results_sorted)}
Multi-spike candidates = {len(multispike)}

Best candidate:
{results_sorted[0] if results_sorted else "No results"}

Interpretation:
This is an exploratory active conductance search. The L796 paper gives experimental firing-pattern targets,
but does not give complete active conductance densities. Therefore, active conductances were searched/tuned
rather than copied as exact L796 biological values.
""".strip()

    Path("L796_step3_active_grid_report.txt").write_text(report, encoding="utf-8")

    print("\nSaved output files:")
    print("  L796_active_grid_summary.csv")
    print("  L796_active_grid_top20.csv")
    print("  L796_active_multispike_candidates.csv")
    print("  L796_active_score_distribution.png")
    print("  L796_active_spike_count_distribution.png")
    print("  L796_active_top3_validation_FI.csv")
    print("  L796_active_top3_FI_validation.png")
    print("  L796_active_top_traces/")
    print("  L796_step3_active_grid_report.txt")


if __name__ == "__main__":
    main()
