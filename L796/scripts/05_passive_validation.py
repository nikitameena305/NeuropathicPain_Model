import os
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from neuron import h


# ============================================================
# 05: PASSIVE VALIDATION FOR L796
# ============================================================
# Builds the passive-only L796 model (soma + dendrites + the
# artificial AIS, all with the `pas` mechanism only, no active
# conductances) and injects a small hyperpolarizing current step
# to measure resting membrane potential (RMP) and input
# resistance (Rin). Compares both against literature targets and
# writes a PASS/FAIL CSV/markdown table.
# ============================================================


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
os.chdir(PROJECT_ROOT)

SWC_FILE = str(PROJECT_ROOT / "morphology" / "L796-ALT-PN.CNG.swc")
TARGETS_FILE = PROJECT_ROOT / "literature_targets" / "L796_literature_targets.json"

OUT_DIR = PROJECT_ROOT / "validation" / "passive"
TRACE_DIR = PROJECT_ROOT / "traces" / "passive"

# -----------------------------
# Fixed passive parameters (Step 2)
# -----------------------------
E_PAS = -72.8
G_PAS = 3.7855152493e-06
CM = 1.0
RA = 200.0

# -----------------------------
# Simulation protocol
# -----------------------------
STIM_DELAY = 100.0
STIM_DUR = 500.0
TSTOP = 900.0
DT = 0.025
RIN_STEP_NA = -0.01  # -10 pA hyperpolarizing pulse


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


# ============================================================
# SIMULATION
# ============================================================

def run_rin_step(soma):
    stim = h.IClamp(soma(0.5))
    stim.delay = STIM_DELAY
    stim.dur = STIM_DUR
    stim.amp = RIN_STEP_NA

    t_vec = h.Vector().record(h._ref_t)
    soma_vec = h.Vector().record(soma(0.5)._ref_v)

    h.dt = DT
    h.tstop = TSTOP
    h.v_init = E_PAS

    h.finitialize(E_PAS)
    h.continuerun(TSTOP)

    t = np.array(t_vec)
    v = np.array(soma_vec)

    base_mask = (t >= 50) & (t < 95)
    late_mask = (t >= 550) & (t < 595)

    v_base = float(np.mean(v[base_mask]))
    v_steady = float(np.mean(v[late_mask]))
    delta_v = v_steady - v_base
    rin_gohm = abs(delta_v / RIN_STEP_NA) / 1000.0

    return t, v, v_base, v_steady, delta_v, rin_gohm


# ============================================================
# MAIN
# ============================================================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    targets = json.loads(TARGETS_FILE.read_text())["passive"]

    print("05 passive validation: importing morphology...")
    import_morphology()
    changed = fix_tiny_diameters(0.2)
    set_nseg_dlambda()

    soma = find_soma()
    insert_passive_everywhere()
    create_artificial_ais(soma)

    print(f"Soma section: {soma.name()}")
    print(f"Diameters corrected below 0.2 um: {changed}")
    print(f"Injecting {RIN_STEP_NA * 1000:.1f} pA step for {STIM_DUR} ms...")

    t, v, v_base, v_steady, delta_v, rin_gohm = run_rin_step(soma)

    rmp_target = targets["RMP_mV"]["target"]
    rmp_tol = targets["RMP_mV"]["tolerance"]
    rin_target = targets["Rin_GOhm"]["target"]
    rin_tol = targets["Rin_GOhm"]["tolerance"]

    rmp_pass = abs(v_base - rmp_target) <= rmp_tol
    rin_pass = abs(rin_gohm - rin_target) <= rin_tol

    rows = [
        {
            "feature": "RMP_mV",
            "model_value": round(v_base, 4),
            "target": rmp_target,
            "tolerance": rmp_tol,
            "source": targets["RMP_mV"]["source"],
            "result": "PASS" if rmp_pass else "FAIL",
        },
        {
            "feature": "Rin_GOhm",
            "model_value": round(rin_gohm, 4),
            "target": rin_target,
            "tolerance": rin_tol,
            "source": targets["Rin_GOhm"]["source"],
            "result": "PASS" if rin_pass else "FAIL",
        },
    ]

    csv_path = OUT_DIR / "L796_passive_validation.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    try:
        import pandas as pd
        md_path = OUT_DIR / "L796_passive_validation.md"
        pd.DataFrame(rows).to_markdown(md_path, index=False)
    except ImportError:
        pass

    # Trace plot / raw trace
    dat_path = TRACE_DIR / "L796_passive_Rin_step.dat"
    with open(dat_path, "w") as f:
        f.write("time_ms soma_mV\n")
        for ti, vi in zip(t, v):
            f.write(f"{ti:.6f} {vi:.6f}\n")

    plt.figure(figsize=(9, 5))
    plt.plot(t, v, label="soma")
    plt.axvspan(STIM_DELAY, STIM_DELAY + STIM_DUR, alpha=0.15, label=f"{RIN_STEP_NA*1000:.0f} pA step")
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (mV)")
    plt.title("L796 passive validation: RMP / Rin step")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(TRACE_DIR / "L796_passive_Rin_step.png", dpi=250)
    plt.close()

    print("\nPassive validation results:")
    for row in rows:
        print(f"  {row['feature']}: model={row['model_value']} target={row['target']} "
              f"+/-{row['tolerance']} -> {row['result']}")
    print(f"\nSaved: {csv_path}")


if __name__ == "__main__":
    main()
