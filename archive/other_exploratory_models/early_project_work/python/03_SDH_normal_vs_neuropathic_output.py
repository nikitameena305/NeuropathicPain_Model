from neuron import h
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

Path("figures").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

def run_sdh(condition):
    h("forall delete_section()")
    h.load_file("stdrun.hoc")

    h.celsius = 37
    h.dt = 0.025
    h.tstop = 600
    h.v_init = -65

    sdh = h.Section(name=f"SDH_projection_{condition}")
    sdh.L = 30
    sdh.diam = 30
    sdh.nseg = 1
    sdh.Ra = 100
    sdh.cm = 1

    # Basic excitable SDH soma
    sdh.insert("hh")
    for seg in sdh:
        seg.hh.gnabar = 0.06
        seg.hh.gkbar = 0.02
        seg.hh.gl = 0.0003
        seg.hh.el = -65

    # DRG-like spike train input
    drg_input = h.NetStim()
    drg_input.start = 100
    drg_input.number = 12
    drg_input.interval = 25
    drg_input.noise = 0

    # Inhibitory interneuron input
    inhib_input = h.NetStim()
    inhib_input.start = 105
    inhib_input.number = 12
    inhib_input.interval = 25
    inhib_input.noise = 0

    # AMPA fast excitation
    ampa = h.Exp2Syn(sdh(0.5))
    ampa.tau1 = 0.1
    ampa.tau2 = 5
    ampa.e = 0

    # NMDA-like slow excitation; simplified without explicit Mg2+ block
    nmda = h.Exp2Syn(sdh(0.5))
    nmda.tau1 = 2
    nmda.tau2 = 100
    nmda.e = 0

    # GABA/glycine-like inhibition
    gaba = h.Exp2Syn(sdh(0.5))
    gaba.tau1 = 0.5
    gaba.tau2 = 15
    gaba.e = -80

    if condition == "normal":
        ampa_w = 0.002
        nmda_w = 0.0005
        gaba_w = 0.0015
    else:
        # neuropathic-like:
        # stronger excitation + weaker inhibition/disinhibition
        ampa_w = 0.004
        nmda_w = 0.0012
        gaba_w = 0.0003

    nc_ampa = h.NetCon(drg_input, ampa)
    nc_ampa.weight[0] = ampa_w
    nc_ampa.delay = 1

    nc_nmda = h.NetCon(drg_input, nmda)
    nc_nmda.weight[0] = nmda_w
    nc_nmda.delay = 1

    nc_gaba = h.NetCon(inhib_input, gaba)
    nc_gaba.weight[0] = gaba_w
    nc_gaba.delay = 1

    t_vec = h.Vector().record(h._ref_t)
    v_vec = h.Vector().record(sdh(0.5)._ref_v)

    spikes = h.Vector()
    detector = h.NetCon(sdh(0.5)._ref_v, None, sec=sdh)
    detector.threshold = 0
    detector.record(spikes)

    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    t = np.array(t_vec.to_python())
    v = np.array(v_vec.to_python())
    sp = np.array(spikes.to_python())

    metrics = {
        "condition": condition,
        "AMPA_weight": ampa_w,
        "NMDA_weight": nmda_w,
        "GABA_weight": gaba_w,
        "baseline_mV": float(v[0]),
        "peak_mV": float(v.max()),
        "voltage_change_mV": float(v.max() - v[0]),
        "spike_count": int(len(sp)),
        "afterdischarge_mean_400_600ms": float(np.mean(v[(t >= 400) & (t <= 600)]))
    }

    return t, v, metrics

t1, v_normal, m1 = run_sdh("normal")
t2, v_neuro, m2 = run_sdh("neuropathic_like")

pd.DataFrame({
    "time_ms": t1,
    "normal_SDH_mV": v_normal,
    "neuropathic_like_SDH_mV": v_neuro
}).to_csv("results/03_SDH_normal_vs_neuropathic_trace.csv", index=False)

pd.DataFrame([m1, m2]).to_csv("results/03_SDH_normal_vs_neuropathic_metrics.csv", index=False)

plt.figure(figsize=(9,5))
plt.plot(t1, v_normal, label="Normal SDH output")
plt.plot(t2, v_neuro, label="Neuropathic-like SDH output")
plt.axvspan(100, 400, alpha=0.2, label="DRG input train")
plt.xlabel("Time (ms)")
plt.ylabel("SDH voltage (mV)")
plt.title("SDH Output: Normal vs Neuropathic-like")
plt.legend()
plt.tight_layout()
plt.savefig("figures/03_SDH_normal_vs_neuropathic_output.png", dpi=300)

print("DONE: SDH normal vs neuropathic-like output")
print(pd.DataFrame([m1, m2]).to_string(index=False))
print("Figure: figures/03_SDH_normal_vs_neuropathic_output.png")
