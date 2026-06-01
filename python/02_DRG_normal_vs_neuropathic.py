from neuron import h
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

Path("figures").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

def run_drg(condition):
    h("forall delete_section()")
    h.load_file("stdrun.hoc")

    h.celsius = 37
    h.dt = 0.025
    h.tstop = 300
    h.v_init = -65

    soma = h.Section(name=f"DRG_soma_{condition}")
    soma.L = 30
    soma.diam = 30
    soma.nseg = 1
    soma.Ra = 100
    soma.cm = 1

    axon = h.Section(name=f"DRG_axon_{condition}")
    axon.L = 1000
    axon.diam = 1.0
    axon.nseg = 21
    axon.Ra = 100
    axon.cm = 1
    axon.connect(soma(1))

    for sec in [soma, axon]:
        sec.insert("hh")
        for seg in sec:
            if condition == "normal":
                seg.hh.gnabar = 0.12
                seg.hh.gkbar = 0.036
            else:
                # neuropathic-like: more Na+ accelerator, less K+ brake
                seg.hh.gnabar = 0.17
                seg.hh.gkbar = 0.025
            seg.hh.gl = 0.0003
            seg.hh.el = -65

    # weak stimulus: should be small/harmless-like
    stim = h.IClamp(soma(0.5))
    stim.delay = 50
    stim.dur = 150
    stim.amp = 0.08

    t_vec = h.Vector().record(h._ref_t)
    v_vec = h.Vector().record(soma(0.5)._ref_v)

    spike_times = h.Vector()
    nc = h.NetCon(soma(0.5)._ref_v, None, sec=soma)
    nc.threshold = 0
    nc.record(spike_times)

    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    t = np.array(t_vec.to_python())
    v = np.array(v_vec.to_python())
    spikes = np.array(spike_times.to_python())

    metrics = {
        "condition": condition,
        "stimulus_nA": stim.amp,
        "RMP_mV": float(v[0]),
        "peak_mV": float(v.max()),
        "spike_count": int(len(spikes)),
        "first_spike_ms": float(spikes[0]) if len(spikes) else np.nan
    }

    return t, v, metrics

t1, v_normal, m1 = run_drg("normal")
t2, v_neuro, m2 = run_drg("neuropathic_like")

pd.DataFrame({
    "time_ms": t1,
    "normal_DRG_mV": v_normal,
    "neuropathic_like_DRG_mV": v_neuro
}).to_csv("results/02_DRG_normal_vs_neuropathic_trace.csv", index=False)

pd.DataFrame([m1, m2]).to_csv("results/02_DRG_normal_vs_neuropathic_metrics.csv", index=False)

plt.figure(figsize=(9,5))
plt.plot(t1, v_normal, label="Normal DRG")
plt.plot(t2, v_neuro, label="Neuropathic-like DRG")
plt.axvspan(50, 200, alpha=0.2, label="same weak stimulus")
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (mV)")
plt.title("DRG Hyperexcitability: Normal vs Neuropathic-like")
plt.legend()
plt.tight_layout()
plt.savefig("figures/02_DRG_normal_vs_neuropathic.png", dpi=300)

print("DONE: DRG normal vs neuropathic-like simulation")
print(pd.DataFrame([m1, m2]).to_string(index=False))
print("Figure: figures/02_DRG_normal_vs_neuropathic.png")
