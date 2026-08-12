import re
import math
from pathlib import Path

import numpy as np
import pandas as pd


TRACE_DIR = Path("L796_step4_traces")
STIM_START = 100.0
STIM_END = 600.0
STIM_DUR_SEC = 0.5
SPIKE_THRESHOLD = -20.0

RIN_CURRENT_NA = -0.01   # -10 pA


def read_trace(path):
    df = pd.read_csv(path, sep=r"\s+", comment="#")
    # Expected columns: time_ms soma_mV AIS_mV
    return df["time_ms"].values, df["soma_mV"].values, df["AIS_mV"].values


def current_from_filename(path):
    # I_060pA.dat -> 60
    m = re.search(r"I_(\d+)pA\.dat", path.name)
    if not m:
        return None
    return int(m.group(1))


def upward_crossings(t, v, threshold=SPIKE_THRESHOLD):
    stim_mask = (t >= STIM_START) & (t <= STIM_END)
    idx = np.where(stim_mask)[0]

    spike_indices = []
    last_t = -1e9
    refractory_ms = 2.0

    for k in idx[1:]:
        if v[k - 1] < threshold and v[k] >= threshold:
            if t[k] - last_t >= refractory_ms:
                spike_indices.append(k)
                last_t = t[k]

    return spike_indices


def spike_peak_and_widths(t, v, spike_indices):
    peaks = []
    widths = []

    for cross_idx in spike_indices:
        # Look 8 ms after threshold crossing for AP peak
        peak_window = np.where((t >= t[cross_idx]) & (t <= t[cross_idx] + 8.0))[0]
        if len(peak_window) == 0:
            continue

        local_peak_idx = peak_window[np.argmax(v[peak_window])]
        peak_v = float(v[local_peak_idx])
        peaks.append(peak_v)

        # Approximate AP half-width:
        # half-height between -20 mV spike-screen threshold and AP peak
        half_level = (SPIKE_THRESHOLD + peak_v) / 2.0

        # Find upward crossing of half-level before peak
        left_idx = None
        for j in range(cross_idx, local_peak_idx + 1):
            if v[j - 1] < half_level and v[j] >= half_level:
                left_idx = j
                break

        # Find downward crossing of half-level after peak
        right_idx = None
        search_end_time = t[local_peak_idx] + 20.0
        after_peak = np.where((t >= t[local_peak_idx]) & (t <= search_end_time))[0]
        for j in after_peak[1:]:
            if v[j - 1] >= half_level and v[j] < half_level:
                right_idx = j
                break

        if left_idx is not None and right_idx is not None:
            widths.append(float(t[right_idx] - t[left_idx]))

    return peaks, widths


def extract_features_for_signal(t, v, label):
    base_mask = (t >= 50) & (t < 95)
    stim_mask = (t >= STIM_START) & (t <= STIM_END)

    spike_indices = upward_crossings(t, v)
    spike_times = [float(t[i]) for i in spike_indices]

    peaks, widths = spike_peak_and_widths(t, v, spike_indices)

    isis = np.diff(spike_times) if len(spike_times) >= 2 else np.array([])

    out = {
        f"{label}_RMP_mV": float(np.mean(v[base_mask])),
        f"{label}_spike_count": len(spike_times),
        f"{label}_firing_frequency_Hz": len(spike_times) / STIM_DUR_SEC,
        f"{label}_first_spike_latency_ms": float(spike_times[0] - STIM_START) if spike_times else math.nan,
        f"{label}_AP_peak_mV": float(np.mean(peaks)) if peaks else math.nan,
        f"{label}_AP_width_halfheight_ms": float(np.mean(widths)) if widths else math.nan,
        f"{label}_first_ISI_ms": float(isis[0]) if len(isis) > 0 else math.nan,
        f"{label}_last_ISI_ms": float(isis[-1]) if len(isis) > 0 else math.nan,
        f"{label}_mean_ISI_ms": float(np.mean(isis)) if len(isis) > 0 else math.nan,
        f"{label}_adaptation_ratio_lastISI_firstISI": float(isis[-1] / isis[0]) if len(isis) >= 2 and isis[0] != 0 else math.nan,
        f"{label}_max_voltage_mV": float(np.max(v[stim_mask])),
        f"{label}_min_voltage_mV": float(np.min(v[stim_mask])),
    }

    return out


def compute_rin():
    rin_file = TRACE_DIR / "Rin_check_minus10pA.dat"
    if not rin_file.exists():
        return math.nan, math.nan, math.nan

    t, soma_v, ais_v = read_trace(rin_file)

    base_mask = (t >= 50) & (t < 95)
    steady_mask = (t >= 550) & (t < 595)

    v_base = float(np.mean(soma_v[base_mask]))
    v_steady = float(np.mean(soma_v[steady_mask]))
    delta_v = v_steady - v_base

    # mV / nA = MOhm
    rin_MOhm = abs(delta_v / RIN_CURRENT_NA)
    rin_GOhm = rin_MOhm / 1000.0

    return rin_GOhm, v_base, delta_v


def main():
    trace_files = sorted(TRACE_DIR.glob("I_*pA.dat"), key=lambda p: current_from_filename(p))

    if not trace_files:
        raise FileNotFoundError("No I_*pA.dat files found in L796_step4_traces/")

    rin_GOhm, rin_base_mV, rin_delta_mV = compute_rin()

    rows = []

    for path in trace_files:
        current_pA = current_from_filename(path)
        t, soma_v, ais_v = read_trace(path)

        row = {
            "current_pA": current_pA,
            "RIN_GOhm_from_minus10pA": rin_GOhm,
            "RIN_baseline_mV": rin_base_mV,
            "RIN_deltaV_mV": rin_delta_mV,
        }

        row.update(extract_features_for_signal(t, soma_v, "soma"))
        row.update(extract_features_for_signal(t, ais_v, "AIS"))

        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("current_pA")

    df.to_csv("L796_step4_final_ephys_features.csv", index=False)

    # Make short report table: most important values
    keep_cols = [
        "current_pA",
        "soma_RMP_mV",
        "AIS_RMP_mV",
        "RIN_GOhm_from_minus10pA",
        "soma_spike_count",
        "AIS_spike_count",
        "AIS_firing_frequency_Hz",
        "AIS_first_spike_latency_ms",
        "AIS_AP_peak_mV",
        "AIS_AP_width_halfheight_ms",
        "AIS_adaptation_ratio_lastISI_firstISI",
        "soma_AP_peak_mV",
        "soma_AP_width_halfheight_ms",
    ]

    short = df[keep_cols].copy()
    short.to_csv("L796_step4_report_ready_features.csv", index=False)

    # Markdown table for direct report copy
    md = []
    md.append("# L796 Step 4 Final Electrophysiological Features\n")
    md.append(f"RIN from -10 pA validation pulse: **{rin_GOhm:.4f} GΩ**\n")
    md.append("AP width is estimated as half-height width between the -20 mV spike-screen threshold and AP peak.\n")
    md.append(short.to_markdown(index=False, floatfmt=".4f"))

    Path("L796_step4_report_ready_features.md").write_text("\n".join(md), encoding="utf-8")

    print("\nSaved:")
    print("  L796_step4_final_ephys_features.csv")
    print("  L796_step4_report_ready_features.csv")
    print("  L796_step4_report_ready_features.md")
    print("\nReport-ready table:\n")
    print(short.to_string(index=False))


if __name__ == "__main__":
    main()
