import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.home() / "NeuropathicPain_Model"
OUTDIR = ROOT / "deliverables" / "week1"
OUTDIR.mkdir(parents=True, exist_ok=True)

if len(sys.argv) < 2:
    print("Usage: python python/11_extract_AP_parameters_from_trace.py path/to/trace.csv")
    sys.exit(1)

trace_path = Path(sys.argv[1])

df = pd.read_csv(trace_path)

# Guess time and voltage columns
cols = {c.lower(): c for c in df.columns}

time_col = None
volt_col = None

for c in df.columns:
    lc = c.lower()
    if lc in ["t", "time", "time_ms", "ms"] or "time" in lc:
        time_col = c
    if lc in ["v", "voltage", "voltage_mv", "v_mV".lower()] or "volt" in lc or lc == "v":
        volt_col = c

if time_col is None:
    time_col = df.columns[0]
if volt_col is None:
    volt_col = df.columns[1]

t = df[time_col].to_numpy(dtype=float)
v = df[volt_col].to_numpy(dtype=float)

# RMP: mean of first 5% of trace
n_base = max(5, int(0.05 * len(v)))
rmp = float(np.mean(v[:n_base]))

peak = float(np.max(v))
peak_time = float(t[np.argmax(v)])

# Threshold: point before AP where dV/dt rises strongly
dvdt = np.gradient(v, t)
candidate = np.where((dvdt > 10) & (v > rmp + 5))[0]

if len(candidate) > 0:
    th_idx = int(candidate[0])
else:
    # fallback: maximum dvdt before peak
    pre_peak = np.where(t <= peak_time)[0]
    th_idx = int(pre_peak[np.argmax(dvdt[pre_peak])])

threshold = float(v[th_idx])
threshold_time = float(t[th_idx])

out_csv = OUTDIR / "modeldb2018004_AP_parameters.csv"
out_fig = OUTDIR / "modeldb2018004_AP_trace_with_parameters.png"

out = pd.DataFrame([{
    "source_trace": str(trace_path),
    "time_column": time_col,
    "voltage_column": volt_col,
    "RMP_mV": rmp,
    "threshold_mV": threshold,
    "threshold_time_ms": threshold_time,
    "peak_mV": peak,
    "peak_time_ms": peak_time,
    "method_note": "Threshold estimated from dV/dt > 10 mV/ms or max dV/dt fallback"
}])

out.to_csv(out_csv, index=False)

plt.figure(figsize=(10, 5))
plt.plot(t, v, linewidth=1.5)
plt.axhline(rmp, linestyle="--", linewidth=1, label=f"RMP {rmp:.2f} mV")
plt.scatter([threshold_time], [threshold], s=50, label=f"Threshold {threshold:.2f} mV")
plt.scatter([peak_time], [peak], s=50, label=f"Peak {peak:.2f} mV")
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (mV)")
plt.title("ModelDB 2018004 AP parameters from voltage trace")
plt.legend()
plt.tight_layout()
plt.savefig(out_fig, dpi=300)
plt.close()

print("AP parameters:")
print(out.to_string(index=False))
print("\nCreated:")
print(out_csv)
print(out_fig)
