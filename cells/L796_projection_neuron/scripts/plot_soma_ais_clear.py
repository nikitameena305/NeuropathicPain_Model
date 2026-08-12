import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Usage:
# python scripts/plot_soma_ais_clear.py traces/step5_best_traces/best_I_60pA.dat


if len(sys.argv) < 2:
    print("Use: python scripts/plot_soma_ais_clear.py traces/step5_best_traces/best_I_60pA.dat")
    sys.exit(1)

trace_file = sys.argv[1]

if not os.path.exists(trace_file):
    print(f"File not found: {trace_file}")
    sys.exit(1)


# ---------- robust trace reader ----------
# Works for .dat with header or without header.
raw = pd.read_csv(
    trace_file,
    sep=r"[\s,]+",
    engine="python",
    comment="#",
    header=None
)

num = raw.apply(pd.to_numeric, errors="coerce")
num = num.dropna(how="any")

if num.shape[1] < 3:
    raise ValueError("Need at least 3 columns: time, soma voltage, AIS voltage")

# assume first 3 numeric columns are time, soma, AIS
t = num.iloc[:, 0].to_numpy()
soma = num.iloc[:, 1].to_numpy()
ais = num.iloc[:, 2].to_numpy()

threshold = -20.0

base = os.path.splitext(os.path.basename(trace_file))[0]
out_dir = "figures/step5_final_model"
os.makedirs(out_dir, exist_ok=True)


# ---------- print peak values ----------
print("\nPeak check")
print(f"Max soma voltage = {np.max(soma):.4f} mV")
print(f"Max AIS voltage  = {np.max(ais):.4f} mV")
print(f"AIS - soma peak  = {np.max(ais) - np.max(soma):.4f} mV")


# ---------- 3-panel clear plot ----------
fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

# Panel 1: soma only
ax[0].plot(t, soma, linewidth=2)
ax[0].axhline(threshold, linestyle="--", linewidth=1)
ax[0].set_ylabel("Soma V (mV)")
ax[0].set_title("Soma trace only")
ax[0].grid(True, alpha=0.3)

# Panel 2: AIS only
ax[1].plot(t, ais, linewidth=2)
ax[1].axhline(threshold, linestyle="--", linewidth=1)
ax[1].set_ylabel("AIS V (mV)")
ax[1].set_title("AIS trace only")
ax[1].grid(True, alpha=0.3)

# Panel 3: overlay, but soma drawn on top
ax[2].plot(t, ais, label="AIS", linewidth=1.2, linestyle="--", zorder=1)
ax[2].plot(t, soma, label="soma", linewidth=2.5, zorder=2)
ax[2].axhline(threshold, linestyle="--", linewidth=1, label="-20 mV threshold")
ax[2].set_xlabel("Time (ms)")
ax[2].set_ylabel("Voltage (mV)")
ax[2].set_title("Overlay: soma drawn on top of AIS")
ax[2].legend()
ax[2].grid(True, alpha=0.3)

plt.tight_layout()

out_png = os.path.join(out_dir, f"{base}_soma_ais_clear_3panel.png")
plt.savefig(out_png, dpi=300)
plt.close()

print(f"\nSaved clear 3-panel figure: {out_png}")


# ---------- first-spike zoom ----------
# Find first soma crossing of -20 mV
cross = np.where((soma[:-1] < threshold) & (soma[1:] >= threshold))[0]

if len(cross) > 0:
    first_cross_time = t[cross[0]]
    zoom_start = first_cross_time - 15
    zoom_end = first_cross_time + 25

    idx = np.where((t >= zoom_start) & (t <= zoom_end))[0]

    plt.figure(figsize=(9, 5))
    plt.plot(t[idx], ais[idx], label="AIS", linewidth=1.2, linestyle="--", zorder=1)
    plt.plot(t[idx], soma[idx], label="soma", linewidth=2.5, zorder=2)
    plt.axhline(threshold, linestyle="--", linewidth=1, label="-20 mV threshold")
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (mV)")
    plt.title("First spike zoom: soma drawn on top")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    out_zoom = os.path.join(out_dir, f"{base}_first_spike_soma_visible_zoom.png")
    plt.savefig(out_zoom, dpi=300)
    plt.close()

    print(f"Saved first-spike zoom figure: {out_zoom}")
else:
    print("No soma spike crossing found for zoom.")
