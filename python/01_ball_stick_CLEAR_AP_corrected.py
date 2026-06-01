from neuron import h
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Output folders
fig_dir = Path("figures")
res_dir = Path("results")
log_dir = Path("logs")
fig_dir.mkdir(exist_ok=True)
res_dir.mkdir(exist_ok=True)
log_dir.mkdir(exist_ok=True)

# NEURON setup
h.load_file("stdrun.hoc")

# -----------------------------
# 1. Create ball-and-stick cell
# -----------------------------
soma = h.Section(name="soma")
dend = h.Section(name="dend")

# Soma: active spike-generating region
soma.L = 20      # um
soma.diam = 20   # um
soma.Ra = 100
soma.cm = 1

# Dendrite: passive cable/stick
dend.L = 200
dend.diam = 1
dend.Ra = 100
dend.cm = 1
dend.connect(soma(1))

# -----------------------------
# 2. Insert mechanisms
# -----------------------------
# HH channel gives Na+, K+, leak currents and can generate AP
soma.insert("hh")

# Passive dendrite only spreads current
dend.insert("pas")
for seg in dend:
    seg.pas.g = 0.0001
    seg.pas.e = -65

# -----------------------------
# 3. Current clamp stimulation
# -----------------------------
stim = h.IClamp(soma(0.5))
stim.delay = 20     # ms
stim.dur = 2        # ms, short pulse
stim.amp = 0.8      # nA, strong enough to cross threshold

# -----------------------------
# 4. Record voltage and time
# -----------------------------
t = h.Vector().record(h._ref_t)
v = h.Vector().record(soma(0.5)._ref_v)

# -----------------------------
# 5. Run simulation
# -----------------------------
h.dt = 0.025
h.tstop = 80
h.finitialize(-65)
h.run()

t_np = np.array(t)
v_np = np.array(v)

# -----------------------------
# 6. Extract AP parameters
# -----------------------------
rmp = float(np.mean(v_np[t_np < 20]))
peak_v = float(np.max(v_np))
peak_t = float(t_np[np.argmax(v_np)])

# Threshold estimate: first point where voltage crosses -20 mV
crossings = np.where(v_np > -20)[0]
if len(crossings) > 0:
    threshold_index = int(crossings[0])
    threshold_v = float(v_np[threshold_index])
    threshold_t = float(t_np[threshold_index])
    ap_generated = "YES"
else:
    threshold_v = np.nan
    threshold_t = np.nan
    ap_generated = "NO"

# Save trace
trace_df = pd.DataFrame({
    "time_ms": t_np,
    "soma_voltage_mV": v_np
})
trace_df.to_csv(res_dir / "01_ball_stick_CLEAR_AP_trace.csv", index=False)

# Save metrics
metrics_df = pd.DataFrame([{
    "model": "Ball-and-stick HH soma + passive dendrite",
    "stim_delay_ms": stim.delay,
    "stim_duration_ms": stim.dur,
    "stim_amplitude_nA": stim.amp,
    "initial_voltage_mV": -65,
    "estimated_RMP_mV": rmp,
    "AP_generated": ap_generated,
    "threshold_estimate_mV": threshold_v,
    "threshold_time_ms": threshold_t,
    "peak_voltage_mV": peak_v,
    "peak_time_ms": peak_t
}])
metrics_df.to_csv(res_dir / "01_ball_stick_CLEAR_AP_metrics.csv", index=False)

# -----------------------------
# 7. Plot clear AP
# -----------------------------
plt.figure(figsize=(9, 5))
plt.plot(t_np, v_np, linewidth=2, label="Soma voltage")

# Stimulus shading
plt.axvspan(stim.delay, stim.delay + stim.dur, alpha=0.2, label="IClamp stimulus")

# Threshold and peak markers
if ap_generated == "YES":
    plt.scatter([threshold_t], [threshold_v], s=50, label=f"Threshold crossing ~{threshold_v:.1f} mV")
plt.scatter([peak_t], [peak_v], s=50, label=f"AP peak {peak_v:.1f} mV")

plt.axhline(0, linestyle="--", linewidth=1, label="0 mV reference")
plt.xlabel("Time (ms)")
plt.ylabel("Soma voltage (mV)")
plt.title("NEURON Ball-and-Stick Demo: Clear Action Potential")
plt.legend()
plt.tight_layout()
plt.savefig(fig_dir / "01_ball_stick_CLEAR_AP_corrected.png", dpi=300)
plt.close()

# Save log
with open(log_dir / "01_ball_stick_CLEAR_AP_corrected.log", "w") as f:
    f.write("Corrected ball-and-stick AP simulation\n")
    f.write("=====================================\n")
    f.write("Soma mechanism: hh\n")
    f.write("Dendrite mechanism: passive\n")
    f.write(f"IClamp delay: {stim.delay} ms\n")
    f.write(f"IClamp duration: {stim.dur} ms\n")
    f.write(f"IClamp amplitude: {stim.amp} nA\n")
    f.write(f"AP generated: {ap_generated}\n")
    f.write(f"RMP: {rmp:.3f} mV\n")
    f.write(f"Peak voltage: {peak_v:.3f} mV\n")
    f.write(f"Peak time: {peak_t:.3f} ms\n")
    f.write(f"Threshold estimate: {threshold_v} mV at {threshold_t} ms\n")

print("DONE: corrected clear AP figure generated.")
print(metrics_df.to_string(index=False))
print("Figure: figures/01_ball_stick_CLEAR_AP_corrected.png")
print("Trace: results/01_ball_stick_CLEAR_AP_trace.csv")
print("Metrics: results/01_ball_stick_CLEAR_AP_metrics.csv")
