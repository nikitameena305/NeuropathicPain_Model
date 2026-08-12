from neuron import h
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

Path("figures").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

h.load_file("stdrun.hoc")
h.celsius = 37
h.dt = 0.025
h.tstop = 120
h.v_init = -65

soma = h.Section(name="fallback_DRG_soma")
soma.L = 30
soma.diam = 30
soma.nseg = 1
soma.Ra = 100
soma.cm = 1

soma.insert("hh")
for seg in soma:
    seg.hh.gnabar = 0.12
    seg.hh.gkbar = 0.036
    seg.hh.gl = 0.0003
    seg.hh.el = -65

stim = h.IClamp(soma(0.5))
stim.delay = 20
stim.dur = 2
stim.amp = 1.0

t_vec = h.Vector().record(h._ref_t)
v_vec = h.Vector().record(soma(0.5)._ref_v)

h.finitialize(h.v_init)
h.continuerun(h.tstop)

t = np.array(t_vec.to_python())
v = np.array(v_vec.to_python())

rmp = float(np.mean(v[t < 10]))
peak = float(v.max())

# threshold estimate: first time dV/dt exceeds 10 mV/ms
dvdt = np.gradient(v, t)
idx = np.where(dvdt > 10)[0]
threshold = float(v[idx[0]]) if len(idx) else float("nan")
threshold_time = float(t[idx[0]]) if len(idx) else float("nan")

metrics = pd.DataFrame([{
    "model": "fallback_simplified_DRG_HH_not_validated_2018004",
    "RMP_mV": rmp,
    "threshold_mV_dvdt10": threshold,
    "threshold_time_ms": threshold_time,
    "peak_mV": peak,
    "stim_amp_nA": stim.amp
}])

metrics.to_csv("results/modeldb2018004_AP_parameters_PENDING_fallback.csv", index=False)

plt.figure(figsize=(8,5))
plt.plot(t, v)
plt.axvspan(stim.delay, stim.delay + stim.dur, alpha=0.2)
plt.axhline(threshold, linestyle="--", label=f"threshold ≈ {threshold:.2f} mV")
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (mV)")
plt.title("Fallback DRG AP Parameter Extraction")
plt.legend()
plt.tight_layout()
plt.savefig("figures/modeldb2018004_AP_parameters_PENDING_fallback.png", dpi=300)

print(metrics.to_string(index=False))
print("Saved fallback AP metrics and figure.")
