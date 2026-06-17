from neuron import h
from pathlib import Path
import numpy as np
import pandas as pd

MORPH_FILE = "morphologies/L360.swc"
OUT = Path("results/passive/passive_sweep.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

h.load_file("stdrun.hoc")
h.load_file("import3d.hoc")

def load_swc(path):
    h("forall delete_section()")
    cell = h.Import3d_SWC_read()
    cell.input(path)
    i3d = h.Import3d_GUI(cell, 0)
    i3d.instantiate(None)
    return list(h.allsec())

def setup_passive(sections, g_pas):
    for sec in sections:
        sec.Ra = 150
        sec.cm = 1
        sec.insert("pas")
        for seg in sec:
            seg.pas.g = g_pas
            seg.pas.e = -65

def get_soma():
    for sec in h.allsec():
        if "soma" in sec.name().lower():
            return sec
    return list(h.allsec())[0]

def measure_rin(g_pas):
    sections = load_swc(MORPH_FILE)
    setup_passive(sections, g_pas)

    soma = get_soma()

    stim = h.IClamp(soma(0.5))
    stim.delay = 500
    stim.dur = 500
    stim.amp = -0.02  # nA = -20 pA

    v = h.Vector().record(soma(0.5)._ref_v)
    t = h.Vector().record(h._ref_t)

    h.v_init = -65
    h.tstop = 1500
    h.dt = 0.05
    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    v = np.array(v)
    t = np.array(t)

    baseline = np.mean(v[(t > 400) & (t < 490)])
    steady = np.mean(v[(t > 900) & (t < 990)])

    dv_mV = steady - baseline
    rin_MOhm = abs(dv_mV / stim.amp)  # mV/nA = MOhm

    return baseline, steady, rin_MOhm

g_values = [1e-6, 1.5e-6, 2e-6, 2.5e-6, 3e-6, 3.5e-6, 4e-6, 5e-6, 6e-6]

rows = []
for g in g_values:
    baseline, steady, rin = measure_rin(g)
    rows.append({
        "g_pas": g,
        "baseline_mV": baseline,
        "steady_mV": steady,
        "Rin_MOhm": rin
    })
    print(f"g_pas={g:.2e} Rin={rin:.2f} MOhm")

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(f"\nSaved: {OUT}")
