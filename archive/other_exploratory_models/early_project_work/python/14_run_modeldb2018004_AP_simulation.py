import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from neuron import h

ROOT = Path(".").resolve()
MODEL_DIR = ROOT / "modeldb" / "2018004"
OUTDIR = ROOT / "deliverables" / "week1"
LOGDIR = ROOT / "logs"

OUTDIR.mkdir(parents=True, exist_ok=True)
LOGDIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MODEL_DIR))

# Load NEURON standard run system
h.load_file("stdrun.hoc")

# Load compiled ModelDB mechanisms
try:
    h.nrn_load_dll(str(MODEL_DIR / "x86_64" / "libnrnmech.so"))
    print("Loaded compiled mechanisms.")
except Exception as e:
    print("Mechanism load warning:", e)

from pseudounipolar_neuron_class import pseudounipolar_neuron

# Important compatibility fix:
# Older model code uses pandas DataFrame.append(), removed in pandas 2.x
if not hasattr(pd.DataFrame, "append"):
    def _append(self, other=None, ignore_index=False, **kwargs):
        return pd.concat([self, pd.DataFrame([other])], ignore_index=ignore_index)
    pd.DataFrame.append = _append
    print("Patched pandas DataFrame.append compatibility.")

print("Creating pseudounipolar neuron...")
cell = pseudounipolar_neuron(
    centralFiberD=5.7,
    peripheralFiberD=7.3,
    neckFiberD=7.3,
    numNodes_p=20,
    numNodes_c=20,
    somaSize=80
)

print("Neuron created.")
print("Number of sections in sectionDF:", len(cell.sectionDF))

# Find soma section from sectionDF
soma_rows = cell.sectionDF[cell.sectionDF["sectionType"] == "soma"]
if len(soma_rows) == 0:
    raise RuntimeError("No soma section found in sectionDF.")

soma = soma_rows.iloc[0]["object"]

# Inject current at soma
stim = h.IClamp(soma(0.5))
stim.delay = 5.0      # ms
stim.dur = 1.0        # ms
stim.amp = 2.0        # nA; strong enough to try AP

# Record voltage
t_vec = h.Vector().record(h._ref_t)
v_vec = h.Vector().record(soma(0.5)._ref_v)

h.dt = 0.025
h.tstop = 40.0
h.finitialize(-80)
h.run()

t = np.array(t_vec)
v = np.array(v_vec)

trace_csv = OUTDIR / "modeldb2018004_soma_voltage_trace.csv"
trace_fig = OUTDIR / "modeldb2018004_soma_voltage_trace.png"
section_csv = OUTDIR / "modeldb2018004_section_summary.csv"

pd.DataFrame({
    "time_ms": t,
    "voltage_mV": v
}).to_csv(trace_csv, index=False)

# Save section summary without object column
section_summary = cell.sectionDF.drop(columns=["object"]).copy()
section_summary.to_csv(section_csv, index=False)

plt.figure(figsize=(10, 5))
plt.plot(t, v, linewidth=1.5)
plt.xlabel("Time (ms)")
plt.ylabel("Soma voltage (mV)")
plt.title("ModelDB 2018004 pseudounipolar neuron soma voltage trace")
plt.tight_layout()
plt.savefig(trace_fig, dpi=300)
plt.close()

print("\nCreated:")
print(trace_csv)
print(trace_fig)
print(section_csv)

print("\nVoltage check:")
print("min_mV =", float(np.min(v)))
print("max_mV =", float(np.max(v)))
print("start_mV =", float(v[0]))
print("end_mV =", float(v[-1]))

print("\nSection types:")
print(cell.sectionDF["sectionType"].value_counts().to_string())
