from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# Project 5:
# AMPA/NMDA contribution after GABA loss
#
# Biological question:
# When inhibition is reduced, does NMDA make SDH projection neuron
# output more persistent?
#
# This is a receptor-level computational sensitivity model:
# - AMPA = fast excitatory drive
# - NMDA = slow/persistent excitatory drive
# - GABA = inhibitory brake
# - Projection neuron output = pain-like SDH output
# ============================================================

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project5"

RESULTS_DIR = PROJECT / "results"
FIGURES_DIR = PROJECT / "figures"
LOGS_DIR = PROJECT / "logs"
NOTES_DIR = PROJECT / "notes"

for d in [RESULTS_DIR, FIGURES_DIR, LOGS_DIR, NOTES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Time settings
# -----------------------------
dt = 1.0          # ms
t_end = 1000.0    # ms
time = np.arange(0, t_end + dt, dt)

# Stimulus window
stim_start = 100.0
stim_end = 400.0

# Late window after stimulus
late_start = stim_end
late_end = 800.0

# Number of projection neurons
n_projection_neurons = 20

# Random seed for reproducibility
rng = np.random.default_rng(42)

# -----------------------------
# Sensory input
# -----------------------------
def stimulus(t):
    """
    Sensory input to dorsal horn.
    Active only from stim_start to stim_end.
    """
    return np.where((t >= stim_start) & (t <= stim_end), 1.0, 0.0)

input_drive = stimulus(time)

# -----------------------------
# Synaptic kernels
# -----------------------------
def exp_kernel(tau_ms, duration_ms=500):
    """
    Create exponential decay kernel.

    AMPA: small tau, fast decay
    NMDA: large tau, slow decay
    """
    k_t = np.arange(0, duration_ms + dt, dt)
    k = np.exp(-k_t / tau_ms)
    k = k / k.sum()
    return k

ampa_kernel = exp_kernel(tau_ms=8, duration_ms=100)
nmda_kernel = exp_kernel(tau_ms=120, duration_ms=600)

def convolve_drive(drive, kernel):
    """
    Convert stimulus input into receptor current.
    """
    out = np.convolve(drive, kernel, mode="full")[:len(drive)]
    if out.max() > 0:
        out = out / out.max()
    return out

ampa_current_base = convolve_drive(input_drive, ampa_kernel)
nmda_current_base = convolve_drive(input_drive, nmda_kernel)

# -----------------------------
# Condition definitions
# -----------------------------
conditions = [
    {
        "condition": "normal_AMPA_NMDA",
        "description": "Normal AMPA/NMDA with normal GABA inhibition",
        "gaba_scale": 1.0,
        "ampa_scale": 1.0,
        "nmda_scale": 1.0,
    },
    {
        "condition": "reduced_GABA",
        "description": "Reduced GABA inhibition with normal AMPA/NMDA",
        "gaba_scale": 0.35,
        "ampa_scale": 1.0,
        "nmda_scale": 1.0,
    },
    {
        "condition": "reduced_GABA_NMDA_block",
        "description": "Reduced GABA inhibition plus NMDA receptor block",
        "gaba_scale": 0.35,
        "ampa_scale": 1.0,
        "nmda_scale": 0.0,
    },
    {
        "condition": "reduced_GABA_AMPA_block",
        "description": "Reduced GABA inhibition plus AMPA receptor block",
        "gaba_scale": 0.35,
        "ampa_scale": 0.0,
        "nmda_scale": 1.0,
    },
]

# -----------------------------
# Projection neuron firing model
# -----------------------------
def simulate_condition(cond):
    """
    Convert receptor currents + inhibition into projection-neuron firing.

    Simple interpretation:
    excitation = AMPA fast current + NMDA slow current
    inhibition = GABA brake
    net drive = excitation - inhibition

    More net drive = more projection neuron spikes.
    """

    ampa = cond["ampa_scale"] * ampa_current_base
    nmda = cond["nmda_scale"] * nmda_current_base

    # Excitatory contribution
    # AMPA is fast and strong during stimulus
    # NMDA is slower and supports late/persistent output
    excitation = 1.1 * ampa + 0.9 * nmda

    # Inhibition is strongest during sensory input but also suppresses network gain
    gaba_inhibition = cond["gaba_scale"] * (0.75 * input_drive + 0.15)

    # Net projection drive
    net_drive = excitation - gaba_inhibition

    # Rectify: projection neurons cannot have negative firing rate
    net_drive = np.maximum(net_drive, 0)

    # Convert drive to firing rate in Hz
    baseline_rate_hz = 1.0
    max_gain_hz = 70.0
    rate_hz = baseline_rate_hz + max_gain_hz * net_drive

    # Generate spikes for projection neuron population
    # Probability per ms = rate / 1000
    spike_probability = rate_hz / 1000.0

    spike_matrix = rng.random((n_projection_neurons, len(time))) < spike_probability

    # Metrics
    total_spikes = int(spike_matrix.sum())

    stim_mask = (time >= stim_start) & (time <= stim_end)
    late_mask = (time > late_start) & (time <= late_end)

    stim_spikes = int(spike_matrix[:, stim_mask].sum())
    late_spikes = int(spike_matrix[:, late_mask].sum())

    stim_duration_s = (stim_end - stim_start) / 1000.0
    late_duration_s = (late_end - late_start) / 1000.0

    stim_rate_hz = stim_spikes / (n_projection_neurons * stim_duration_s)
    late_rate_hz = late_spikes / (n_projection_neurons * late_duration_s)

    persistent_firing_index = late_rate_hz / stim_rate_hz if stim_rate_hz > 0 else 0

    return {
        "condition": cond["condition"],
        "description": cond["description"],
        "gaba_scale": cond["gaba_scale"],
        "ampa_scale": cond["ampa_scale"],
        "nmda_scale": cond["nmda_scale"],
        "total_spike_count": total_spikes,
        "stimulus_window_spikes": stim_spikes,
        "late_window_spikes": late_spikes,
        "stimulus_projection_rate_Hz": stim_rate_hz,
        "late_projection_rate_Hz": late_rate_hz,
        "persistent_firing_index": persistent_firing_index,
        "time_ms": time,
        "ampa_current": ampa,
        "nmda_current": nmda,
        "net_drive": net_drive,
        "rate_hz": rate_hz,
        "spike_matrix": spike_matrix,
    }

all_results = [simulate_condition(c) for c in conditions]

# -----------------------------
# Save summary CSV
# -----------------------------
summary_rows = []
for r in all_results:
    summary_rows.append({
        "condition": r["condition"],
        "description": r["description"],
        "gaba_scale": r["gaba_scale"],
        "ampa_scale": r["ampa_scale"],
        "nmda_scale": r["nmda_scale"],
        "total_spike_count": r["total_spike_count"],
        "stimulus_window_spikes": r["stimulus_window_spikes"],
        "late_window_spikes": r["late_window_spikes"],
        "stimulus_projection_rate_Hz": r["stimulus_projection_rate_Hz"],
        "late_projection_rate_Hz": r["late_projection_rate_Hz"],
        "persistent_firing_index": r["persistent_firing_index"],
    })

summary_df = pd.DataFrame(summary_rows)
summary_csv = RESULTS_DIR / "project5_ampa_nmda_gaba_summary.csv"
summary_df.to_csv(summary_csv, index=False)

# -----------------------------
# Save time-series CSV
# -----------------------------
timeseries_rows = []
for r in all_results:
    temp = pd.DataFrame({
        "time_ms": r["time_ms"],
        "condition": r["condition"],
        "ampa_current": r["ampa_current"],
        "nmda_current": r["nmda_current"],
        "net_drive": r["net_drive"],
        "projection_rate_Hz": r["rate_hz"],
    })
    timeseries_rows.append(temp)

timeseries_df = pd.concat(timeseries_rows, ignore_index=True)
timeseries_csv = RESULTS_DIR / "project5_projection_timeseries.csv"
timeseries_df.to_csv(timeseries_csv, index=False)

# -----------------------------
# Figure 1: receptor currents
# -----------------------------
plt.figure(figsize=(10, 5))
plt.plot(time, ampa_current_base, label="AMPA fast current")
plt.plot(time, nmda_current_base, label="NMDA slow current")
plt.axvspan(stim_start, stim_end, alpha=0.2, label="Stimulus window")
plt.xlabel("Time (ms)")
plt.ylabel("Normalized receptor current")
plt.title("Project 5: AMPA vs NMDA current timing")
plt.legend()
plt.tight_layout()
plt.savefig(FIGURES_DIR / "project5_ampa_vs_nmda_currents.png", dpi=300)
plt.close()

# -----------------------------
# Figure 2: projection neuron rate traces
# -----------------------------
plt.figure(figsize=(10, 5))
for r in all_results:
    plt.plot(r["time_ms"], r["rate_hz"], label=r["condition"])
plt.axvspan(stim_start, stim_end, alpha=0.2, label="Stimulus window")
plt.axvspan(late_start, late_end, alpha=0.1, label="Late window")
plt.xlabel("Time (ms)")
plt.ylabel("Projection neuron firing rate (Hz)")
plt.title("Project 5: Projection neuron activity across receptor conditions")
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(FIGURES_DIR / "project5_projection_rate_traces.png", dpi=300)
plt.close()

# -----------------------------
# Figure 3: total spike count
# -----------------------------
plt.figure(figsize=(9, 5))
plt.bar(summary_df["condition"], summary_df["total_spike_count"])
plt.xticks(rotation=30, ha="right")
plt.ylabel("Total projection neuron spike count")
plt.title("Project 5: Total spike count")
plt.tight_layout()
plt.savefig(FIGURES_DIR / "project5_total_spike_count_barplot.png", dpi=300)
plt.close()

# -----------------------------
# Figure 4: late firing
# -----------------------------
plt.figure(figsize=(9, 5))
plt.bar(summary_df["condition"], summary_df["late_window_spikes"])
plt.xticks(rotation=30, ha="right")
plt.ylabel("Late spikes after stimulus")
plt.title("Project 5: Late firing after stimulus")
plt.tight_layout()
plt.savefig(FIGURES_DIR / "project5_late_spikes_barplot.png", dpi=300)
plt.close()

# -----------------------------
# Figure 5: persistent firing index
# -----------------------------
plt.figure(figsize=(9, 5))
plt.bar(summary_df["condition"], summary_df["persistent_firing_index"])
plt.xticks(rotation=30, ha="right")
plt.ylabel("Late firing / stimulus firing")
plt.title("Project 5: Persistent firing index")
plt.tight_layout()
plt.savefig(FIGURES_DIR / "project5_persistent_firing_index.png", dpi=300)
plt.close()

# -----------------------------
# Save interpretation note
# -----------------------------
note = f"""
# Project 5 Interpretation: AMPA/NMDA contribution after GABA loss

## Biological question

When GABA inhibition is reduced, does NMDA make spinal dorsal horn projection-neuron output more persistent?

## Conditions tested

1. normal_AMPA_NMDA
   - Normal GABA inhibition
   - AMPA and NMDA both active

2. reduced_GABA
   - GABA inhibition reduced
   - AMPA and NMDA both active

3. reduced_GABA_NMDA_block
   - GABA inhibition reduced
   - NMDA blocked
   - AMPA remains active

4. reduced_GABA_AMPA_block
   - GABA inhibition reduced
   - AMPA blocked
   - NMDA remains active

## Main logic

AMPA is fast.
It gives quick excitation during stimulus.

NMDA is slow.
It decays slowly and can support late/persistent firing after the stimulus.

GABA is inhibitory.
It acts like a brake on SDH projection-neuron firing.

## Expected biological interpretation

If reduced_GABA gives high late firing, but reduced_GABA_NMDA_block reduces late firing,
then NMDA contributes to persistent pain-like output.

If reduced_GABA_AMPA_block strongly reduces stimulus-window firing,
then AMPA contributes to fast stimulus-driven activation.

## Important caution

This script is a receptor-level computational sensitivity model.
It separates AMPA and NMDA mathematically to test mechanism.
It is not yet a full biophysical receptor knockout unless the original NEURON/NetPyNE model
has explicit AMPA and NMDA synapse objects that are directly blocked.

## Output files

Summary CSV:
- project5/results/project5_ampa_nmda_gaba_summary.csv

Time-series CSV:
- project5/results/project5_projection_timeseries.csv

Figures:
- project5/figures/project5_ampa_vs_nmda_currents.png
- project5/figures/project5_projection_rate_traces.png
- project5/figures/project5_total_spike_count_barplot.png
- project5/figures/project5_late_spikes_barplot.png
- project5/figures/project5_persistent_firing_index.png
"""

(NOTES_DIR / "project5_interpretation.md").write_text(note)

# -----------------------------
# Print terminal summary
# -----------------------------
print("\\n==============================")
print("PROJECT 5 COMPLETE")
print("==============================")
print(summary_df.to_string(index=False))
print("\\nSaved summary:")
print(summary_csv)
print("\\nSaved time-series:")
print(timeseries_csv)
print("\\nSaved figures in:")
print(FIGURES_DIR)
print("\\nSaved interpretation note:")
print(NOTES_DIR / "project5_interpretation.md")
