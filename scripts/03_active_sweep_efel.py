from neuron import h
from pathlib import Path
import numpy as np
import pandas as pd
import efel

MORPH_FILE = "morphologies/L360.swc"
OUT = Path("results/active/active_sweep_efel.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

h.load_file("stdrun.hoc")
h.load_file("import3d.hoc")

def load_mechanisms():
    try:
        h.nrn_load_dll("mechanisms/x86_64/.libs/libnrnmech.so")
        print("Loaded compiled MOD mechanisms.")
    except Exception as e:
        print("Could not load external MOD library. Continuing with built-in mechanisms if available.")
        print(e)

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

    # Start simple: active only in soma.
    # Later you can move Na/K to AIS.
    soma.insert("hh")
    for seg in soma:
        seg.hh.gnabar = gnabar
        seg.hh.gkbar = gkbar
        seg.hh.gl = 0.000003
        seg.hh.el = -65

    return soma

def run_sim(g_pas, gnabar, gkbar, amp):
    soma = setup_cell(g_pas, gnabar, gkbar)

    stim = h.IClamp(soma(0.5))
    stim.delay = 500
    stim.dur = 500
    stim.amp = amp

    v = h.Vector().record(soma(0.5)._ref_v)
    t = h.Vector().record(h._ref_t)

    h.v_init = -65
    h.tstop = 1500
    h.dt = 0.025
    h.finitialize(h.v_init)
    h.continuerun(h.tstop)

    t = np.array(t)
    v = np.array(v)

    trace = {
        "T": t,
        "V": v,
        "stim_start": [500],
        "stim_end": [1000]
    }

    features = efel.getFeatureValues(
        [trace],
        [
            "Spikecount",
            "AP_amplitude",
            "AP_width",
            "voltage_base",
            "mean_frequency"
        ]
    )[0]

    def get_mean(name):
        value = features.get(name, None)
        if value is None or len(value) == 0:
            return np.nan
        return float(np.mean(value))

    return {
        "g_pas": g_pas,
        "gnabar": gnabar,
        "gkbar": gkbar,
        "amp_nA": amp,
        "spikecount": get_mean("Spikecount"),
        "AP_amplitude_mV": get_mean("AP_amplitude"),
        "AP_width_ms": get_mean("AP_width"),
        "voltage_base_mV": get_mean("voltage_base"),
        "mean_frequency_Hz": get_mean("mean_frequency"),
        "vmax_mV": float(np.max(v)),
        "vend_mV": float(v[-1])
    }

load_mechanisms()

g_pas = 3e-6

gnabar_values = [0.02, 0.05, 0.08, 0.12, 0.2]
gkbar_values = [0.005, 0.01, 0.02, 0.04, 0.08]
amps = [0.02, 0.05, 0.1, 0.15, 0.2]

rows = []

for gnabar in gnabar_values:
    for gkbar in gkbar_values:
        for amp in amps:
            try:
                row = run_sim(g_pas, gnabar, gkbar, amp)
                rows.append(row)
                print(
                    f"gna={gnabar} gk={gkbar} amp={amp} "
                    f"spikes={row['spikecount']} freq={row['mean_frequency_Hz']}"
                )
            except Exception as e:
                print("FAILED:", gnabar, gkbar, amp, e)

df = pd.DataFrame(rows)

# Simple biological filter
df["good_candidate"] = (
    (df["spikecount"] >= 1) &
    (df["spikecount"] <= 30) &
    (df["AP_amplitude_mV"] >= 50) &
    (df["AP_width_ms"] >= 0.5) &
    (df["AP_width_ms"] <= 5.0) &
    (df["vend_mV"] < -50)
)

df.to_csv(OUT, index=False)

print("\nTop candidates:")
print(df[df["good_candidate"]].head(10).to_string(index=False))
print(f"\nSaved: {OUT}")
