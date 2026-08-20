import os
import glob
import re
import numpy as np
import pandas as pd

STIM_START = 100.0
STIM_END = 600.0
STIM_DUR_S = (STIM_END - STIM_START) / 1000.0

PER_SPIKE = "results/ap_features/L796_step5_somatic_AP_features_per_spike.csv"
OLD_SUMMARY = "results/ap_features/L796_step5_somatic_AP_features_summary.csv"
OUT = "results/ap_features/L796_step5_somatic_AP_features_summary_STIM_WINDOW.csv"

os.makedirs("results/ap_features", exist_ok=True)

spikes = pd.read_csv(PER_SPIKE)
old = pd.read_csv(OLD_SUMMARY)

rows = []

for _, oldrow in old.sort_values("current_pA").iterrows():
    current = oldrow["current_pA"]

    sub = spikes[
        (spikes["current_pA"] == current) &
        (spikes["soma_cross_minus20_ms"] >= STIM_START) &
        (spikes["soma_cross_minus20_ms"] <= STIM_END)
    ].copy()

    spike_count = len(sub)

    if spike_count > 0:
        spike_times = sub["soma_cross_minus20_ms"].to_numpy()
        spike_times = np.sort(spike_times)

        if spike_count >= 2:
            isi = np.diff(spike_times)
            mean_isi = float(np.mean(isi))
            adaptation_ratio = float(isi[-1] / isi[0]) if isi[0] != 0 else np.nan
        else:
            mean_isi = np.nan
            adaptation_ratio = np.nan

        first_latency = float(spike_times[0] - STIM_START)

        row = {
            "trace_file": oldrow["trace_file"],
            "current_pA": current,
            "soma_spike_count": spike_count,
            "ais_spike_count": spike_count,  # use AIS-soma validated matched count in stim window
            "firing_frequency_Hz": spike_count / STIM_DUR_S,
            "baseline_soma_mV": oldrow["baseline_soma_mV"],
            "recovery_soma_mV": oldrow["recovery_soma_mV"],
            "first_spike_latency_ms": first_latency,
            "mean_ISI_ms": mean_isi,
            "adaptation_ratio_lastISI_firstISI": adaptation_ratio,
            "mean_soma_threshold_mV": sub["soma_threshold_mV"].mean(),
            "mean_soma_peak_mV": sub["soma_peak_mV"].mean(),
            "mean_soma_AP_amplitude_mV": sub["soma_AP_amplitude_mV"].mean(),
            "mean_soma_half_width_ms": sub["soma_AP_half_width_ms"].mean(),
            "mean_soma_base_width_minus20_ms": sub["soma_AP_base_width_at_minus20_ms"].mean(),
            "mean_soma_AHP_mV": sub["soma_AHP_mV"].mean(),
            "mean_approx_ADP_from_AHP_mV": sub["approx_ADP_from_AHP_mV"].mean(),
        }
    else:
        row = {
            "trace_file": oldrow["trace_file"],
            "current_pA": current,
            "soma_spike_count": 0,
            "ais_spike_count": 0,
            "firing_frequency_Hz": 0.0,
            "baseline_soma_mV": oldrow["baseline_soma_mV"],
            "recovery_soma_mV": oldrow["recovery_soma_mV"],
            "first_spike_latency_ms": np.nan,
            "mean_ISI_ms": np.nan,
            "adaptation_ratio_lastISI_firstISI": np.nan,
            "mean_soma_threshold_mV": np.nan,
            "mean_soma_peak_mV": np.nan,
            "mean_soma_AP_amplitude_mV": np.nan,
            "mean_soma_half_width_ms": np.nan,
            "mean_soma_base_width_minus20_ms": np.nan,
            "mean_soma_AHP_mV": np.nan,
            "mean_approx_ADP_from_AHP_mV": np.nan,
        }

    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(out.to_string(index=False))
print(f"\nSaved corrected AP summary: {OUT}")
