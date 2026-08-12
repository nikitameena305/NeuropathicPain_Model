from neuron import h
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

Path("figures").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

h.load_file("stdrun.hoc")
h.celsius = 37
h.dt = 0.025
h.tstop = 120
h.v_init = -65

# -------------------------
# Ball-and-stick neuron
# soma = ball
# dendrite = stick
# -------------------------
soma = h.Section(name="soma")
soma.L = 30
soma.diam = 30
soma.nseg = 1
soma.Ra = 100
soma.cm = 1

dend = h.Section(name="dend")
dend.L = 300
dend.diam = 1
dend.nseg = 11
dend.Ra = 100
dend.cm = 1
dend.connect(soma(1))

# Active soma: HH creates AP
soma.insert("hh")
for seg in soma:
    seg.hh.gnabar = 0.12
    seg.hh.gkbar = 0.036
    seg.hh.gl = 0.0003
    seg.hh.el = -65

# Passive dendrite
dend.insert("pas")
for seg in dend:
    seg.pas.g = 0.0001
    seg.pas.e = -65

# Current injection
stim = h.IClamp(soma(0.5))
stim.delay = 20
stim.dur = 40
stim.amp = 0.35

# Record
t_vec = h.Vector().record(h._ref_t)
v_vec = h.Vector().record(soma(0.5)._ref_v)

h.finitialize(h.v_init)
h.continuerun(h.tstop)

t = np.array(t_vec)
v = np.array(v_vec)

# Estimate AP parameters
baseline = float(v[0])
peak = float(v.max())
threshold_index = np.where(v > -20)[0]
threshold_time = float(t[threshold_index[0]]) if len(threshold_index) else np.nan

np.savetxt(
    "results/ball_stick_ap_trace.csv",
    np.column_stack([t, v]),
    delimiter=",",
    header="time_ms,voltage_mV",
    comments=""
)

with open("results/ball_stick_ap_metrics.txt", "w") as f:
    f.write(f"Baseline/RMP approx: {baseline:.2f} mV\n")
    f.write(f"Peak voltage: {peak:.2f} mV\n")
    f.write(f"Approx threshold crossing time > -20 mV: {threshold_time:.2f} ms\n")
    f.write("Stimulus current: 0.35 nA\n")

plt.figure(figsize=(8,5))
plt.plot(t, v)
plt.axvspan(stim.delay, stim.delay + stim.dur, alpha=0.2, label="IClamp stimulus")
plt.xlabel("Time (ms)")
plt.ylabel("Soma voltage (mV)")
plt.title("NEURON Ball-and-Stick Demo: Clear Action Potential")
plt.legend()
plt.tight_layout()
plt.savefig("figures/01_ball_stick_AP_demo.png", dpi=300)

print("DONE: AP spike generated")
print("Figure: figures/01_ball_stick_AP_demo.png")
print("Metrics: results/ball_stick_ap_metrics.txt")
print(open("results/ball_stick_ap_metrics.txt").read())
