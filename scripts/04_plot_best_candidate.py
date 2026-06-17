from neuron import h
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MORPH_FILE = "morphologies/L360.swc"
CSV = "results/active/active_sweep_efel.csv"
FIG = Path("figures/best_candidate_trace.png")
FIG.parent.mkdir(parents=True, exist_ok=True)

h.load_file("stdrun.hoc")
h.load_file("import3d.hoc")

def load_swc(path):
    h("forall delete_section()")
    cell = h.Import3d_SWC_read()
    cell.input(path)
    i3d = h.Import3d_GUI(cell, 0)
    i3d.instantiate(None)
    return list(h.allsec())

def get_soma():
    for sec in h.allsec():
        if "soma" in sec.name().lower():
            return sec
    return list(h.allsec())[0]

def setup_cell(g_pas, gnabar, gkbar):
    sections = load_swc(MORPH_FILE)

    for sec in sections:
        sec.Ra = 150
        sec.cm = 1
        sec.insert("pas")
        for seg in sec:
            seg.pas.g = g_pas
            seg.pas.e = -65

    soma = get_soma()
    soma.insert("hh")

    for seg in soma:
        seg.hh.gnabar = gnabar
        seg.hh.gkbar = gkbar
        seg.hh.gl = 0.000003
        seg.hh.el = -65

    return soma

df = pd.read_csv(CSV)
good = df[df["good_candidate"] == True]

if len(good) == 0:
    raise RuntimeError("No good candidate found. Expand sweep ranges.")

row = good.iloc[0]

soma = setup_cell(row["g_pas"], row["gnabar"], row["gkbar"])

stim = h.IClamp(soma(0.5))
stim.delay = 500
stim.dur = 500
stim.amp = row["amp_nA"]

v = h.Vector().record(soma(0.5)._ref_v)
t = h.Vector().record(h._ref_t)

h.v_init = -65
h.tstop = 1500
h.dt = 0.025
h.finitialize(h.v_init)
h.continuerun(h.tstop)

plt.figure(figsize=(8, 4))
plt.plot(np.array(t), np.array(v))
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (mV)")
plt.title("Best candidate voltage trace")
plt.tight_layout()
plt.savefig(FIG, dpi=300)

print("Best candidate:")
print(row.to_string())
print(f"\nSaved figure: {FIG}")
