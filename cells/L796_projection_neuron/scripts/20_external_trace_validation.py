from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

MODEL_TRACE = Path("results/final_model_v2/final_traces_v2/v2_I_40pA.dat")
EXP_TRACE = Path("literature_targets/digitized_experimental_AP.csv")

OUTDIR = Path("results/external_validation")
FIGDIR = Path("figures/external_validation")
OUTDIR.mkdir(parents=True, exist_ok=True)
FIGDIR.mkdir(parents=True, exist_ok=True)

def read_trace(path):
    df = pd.read_csv(path)
    cols = [c.lower() for c in df.columns]

    tcol = None
    vcol = None

    for c in df.columns:
        lc = c.lower()
        if "time" in lc or lc in ["t", "t_ms"]:
            tcol = c
        if "soma" in lc or "volt" in lc or lc in ["v", "v_m", "voltage_mV".lower()]:
            vcol = c

    if tcol is None:
        tcol = df.columns[0]
    if vcol is None:
        vcol = df.columns[1]

    t = df[tcol].astype(float).to_numpy()
    v = df[vcol].astype(float).to_numpy()
    return t, v

def first_ap_features(t, v):
    dt = np.median(np.diff(t))
    dvdt = np.gradient(v, dt)

    # threshold: first point with dV/dt >= 10 mV/ms and voltage > -60 mV
    candidates = np.where((dvdt >= 10) & (v > -60))[0]
    if len(candidates) == 0:
        return None

    ith = candidates[0]
    t_th = t[ith]
    v_th = v[ith]

    # peak within 15 ms after threshold
    win = np.where((t >= t_th) & (t <= t_th + 15))[0]
    ipk = win[np.argmax(v[win])]
    t_pk = t[ipk]
    v_pk = v[ipk]

    amp = v_pk - v_th
    half_v = v_th + amp / 2

    # half-width crossings
    left = np.where((t >= t_th - 2) & (t <= t_pk) & (v >= half_v))[0]
    right = np.where((t >= t_pk) & (t <= t_pk + 10) & (v <= half_v))[0]

    if len(left) > 0 and len(right) > 0:
        hw = t[right[0]] - t[left[0]]
    else:
        hw = np.nan

    return {
        "threshold_time_ms": t_th,
        "threshold_mV": v_th,
        "peak_time_ms": t_pk,
        "peak_mV": v_pk,
        "amplitude_mV": amp,
        "half_width_ms": hw,
    }

def align_to_threshold(t, v, feat):
    return t - feat["threshold_time_ms"], v - feat["threshold_mV"]

tm, vm = read_trace(MODEL_TRACE)
te, ve = read_trace(EXP_TRACE)

fm = first_ap_features(tm, vm)
fe = first_ap_features(te, ve)

if fm is None:
    raise RuntimeError("No AP detected in model trace.")
if fe is None:
    raise RuntimeError("No AP detected in experimental trace.")

tm_a, vm_a = align_to_threshold(tm, vm, fm)
te_a, ve_a = align_to_threshold(te, ve, fe)

# Compare shape over -2 to +8 ms around threshold
grid = np.linspace(-2, 8, 1000)
model_interp = np.interp(grid, tm_a, vm_a)
exp_interp = np.interp(grid, te_a, ve_a)
rmse = float(np.sqrt(np.mean((model_interp - exp_interp) ** 2)))

summary = pd.DataFrame([
    {"source": "model", **fm},
    {"source": "experiment", **fe},
])
summary["shape_RMSE_mV_threshold_aligned"] = rmse
summary.to_csv(OUTDIR / "external_AP_trace_validation_summary.csv", index=False)

plt.figure(figsize=(8, 5))
plt.plot(tm_a, vm_a, label="Model AP, threshold-aligned")
plt.plot(te_a, ve_a, label="Experimental AP, threshold-aligned")
plt.xlim(-5, 20)
plt.xlabel("Time from AP threshold (ms)")
plt.ylabel("Voltage relative to threshold (mV)")
plt.title(f"External AP trace validation; RMSE={rmse:.2f} mV")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIGDIR / "external_AP_trace_overlay.png", dpi=200)

print(summary.to_string(index=False))
print("Saved:")
print(OUTDIR / "external_AP_trace_validation_summary.csv")
print(FIGDIR / "external_AP_trace_overlay.png")
