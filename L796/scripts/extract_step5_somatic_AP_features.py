import os
import re
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


TRACE_DIR = "traces/step5_best_traces"
OUT_DIR = "results/ap_features"
FIG_DIR = "figures/ap_features"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


def parse_current_pa(filename):
    """
    Handles:
    best_I_-10pA.dat
    best_I_0pA.dat
    best_I_60pA.dat
    """
    base = os.path.basename(filename)
    m = re.search(r"I_(-?\d+)pA", base)
    if m:
        return int(m.group(1))
    return np.nan


def read_dat_trace(path):
    """
    Robustly reads your .dat traces.
    Assumes first 3 numeric columns are:
    time_ms, soma_v, ais_v
    """
    raw = pd.read_csv(
        path,
        sep=r"[\s,]+",
        engine="python",
        comment="#",
        header=None
    )

    num = raw.apply(pd.to_numeric, errors="coerce")
    num = num.dropna(how="any")

    if num.shape[1] < 3:
        raise ValueError(f"{path} has fewer than 3 numeric columns")

    df = pd.DataFrame({
        "time_ms": num.iloc[:, 0].to_numpy(),
        "soma_v": num.iloc[:, 1].to_numpy(),
        "ais_v": num.iloc[:, 2].to_numpy(),
    })

    return df


def upward_crossings(t, v, threshold=-20.0):
    idx = np.where((v[:-1] < threshold) & (v[1:] >= threshold))[0] + 1
    return idx


def interp_cross_time(t1, t2, v1, v2, level):
    if v2 == v1:
        return t2
    return t1 + ((level - v1) / (v2 - v1)) * (t2 - t1)


def estimate_threshold(t, v, cross_idx, dvdt_cutoff=10.0):
    """
    Estimate AP threshold from dV/dt crossing.
    Searches 5 ms before -20 mV crossing.
    If not found, uses voltage at -20 mV crossing.
    """
    dt = np.median(np.diff(t))
    dvdt = np.gradient(v, t)  # mV/ms

    t_cross = t[cross_idx]
    win = np.where((t >= t_cross - 5.0) & (t <= t_cross))[0]

    candidates = win[dvdt[win] >= dvdt_cutoff]
    if len(candidates) > 0:
        i = candidates[0]
        return t[i], v[i], dvdt[i]

    return t_cross, v[cross_idx], dvdt[cross_idx]


def width_at_level(t, v, peak_idx, level):
    """
    Width around a spike at a voltage level.
    Finds left and right crossings around peak.
    """
    # left crossing: below to above level before peak
    left = None
    for i in range(peak_idx, 0, -1):
        if v[i - 1] < level <= v[i]:
            left = interp_cross_time(t[i - 1], t[i], v[i - 1], v[i], level)
            break

    # right crossing: above to below level after peak
    right = None
    for i in range(peak_idx, len(v) - 1):
        if v[i] >= level > v[i + 1]:
            right = interp_cross_time(t[i], t[i + 1], v[i], v[i + 1], level)
            break

    if left is None or right is None:
        return np.nan

    return right - left


def extract_trace_features(path):
    current_pa = parse_current_pa(path)
    df = read_dat_trace(path)

    t = df["time_ms"].to_numpy()
    soma = df["soma_v"].to_numpy()
    ais = df["ais_v"].to_numpy()

    stim_start = 100.0
    stim_end = 600.0

    baseline_idx = np.where(t < stim_start)[0]
    recovery_idx = np.where((t >= stim_end + 150.0) & (t <= stim_end + 200.0))[0]

    baseline_v = float(np.mean(soma[baseline_idx])) if len(baseline_idx) else np.nan
    recovery_v = float(np.mean(soma[recovery_idx])) if len(recovery_idx) else np.nan

    soma_cross = upward_crossings(t, soma, threshold=-20.0)
    ais_cross = upward_crossings(t, ais, threshold=-20.0)

    rows = []

    for spike_no, cross_idx in enumerate(soma_cross, start=1):
        cross_t = t[cross_idx]

        # peak within 6 ms after threshold crossing
        peak_win = np.where((t >= cross_t) & (t <= cross_t + 6.0))[0]
        if len(peak_win) == 0:
            continue

        peak_idx = peak_win[np.argmax(soma[peak_win])]
        peak_t = t[peak_idx]
        peak_v = soma[peak_idx]

        th_t, th_v, th_dvdt = estimate_threshold(t, soma, cross_idx)

        amplitude = peak_v - th_v
        half_level = th_v + amplitude / 2.0

        half_width = width_at_level(t, soma, peak_idx, half_level)
        base_width_minus20 = width_at_level(t, soma, peak_idx, -20.0)

        # AHP: minimum 2-30 ms after peak, but stop before next spike if needed
        if spike_no < len(soma_cross):
            next_cross_t = t[soma_cross[spike_no]]
            ahp_end = min(peak_t + 30.0, next_cross_t - 2.0)
        else:
            ahp_end = peak_t + 30.0

        ahp_win = np.where((t >= peak_t + 2.0) & (t <= ahp_end))[0]
        if len(ahp_win):
            ahp_v = float(np.min(soma[ahp_win]))
            ahp_t = float(t[ahp_win[np.argmin(soma[ahp_win])]])
        else:
            ahp_v = np.nan
            ahp_t = np.nan

        # ADP approximation: maximum after AHP up to next spike or 40 ms
        if not np.isnan(ahp_t):
            adp_end = peak_t + 40.0
            if spike_no < len(soma_cross):
                adp_end = min(adp_end, t[soma_cross[spike_no]] - 2.0)

            adp_win = np.where((t >= ahp_t) & (t <= adp_end))[0]
            if len(adp_win):
                adp_peak_v = float(np.max(soma[adp_win]))
                adp_amp_from_ahp = adp_peak_v - ahp_v
            else:
                adp_peak_v = np.nan
                adp_amp_from_ahp = np.nan
        else:
            adp_peak_v = np.nan
            adp_amp_from_ahp = np.nan

        rows.append({
            "trace_file": os.path.basename(path),
            "current_pA": current_pa,
            "spike_no": spike_no,
            "baseline_soma_mV": baseline_v,
            "recovery_soma_mV": recovery_v,
            "soma_cross_minus20_ms": cross_t,
            "soma_threshold_time_ms": th_t,
            "soma_threshold_mV": th_v,
            "threshold_dvdt_mV_per_ms": th_dvdt,
            "soma_peak_time_ms": peak_t,
            "soma_peak_mV": peak_v,
            "soma_AP_amplitude_mV": amplitude,
            "soma_AP_half_width_ms": half_width,
            "soma_AP_base_width_at_minus20_ms": base_width_minus20,
            "soma_AHP_mV": ahp_v,
            "soma_AHP_time_ms": ahp_t,
            "approx_ADP_peak_mV": adp_peak_v,
            "approx_ADP_from_AHP_mV": adp_amp_from_ahp,
            "first_spike_latency_ms": cross_t - stim_start if spike_no == 1 else np.nan,
        })

    spike_rows = pd.DataFrame(rows)

    # per-trace summary
    spike_count = len(soma_cross)
    firing_freq_hz = spike_count / ((stim_end - stim_start) / 1000.0)

    if len(soma_cross) >= 2:
        spike_times = t[soma_cross]
        isi = np.diff(spike_times)
        mean_isi = float(np.mean(isi))
        adaptation_ratio = float(isi[-1] / isi[0]) if isi[0] != 0 else np.nan
    else:
        mean_isi = np.nan
        adaptation_ratio = np.nan

    summary = {
        "trace_file": os.path.basename(path),
        "current_pA": current_pa,
        "soma_spike_count": spike_count,
        "ais_spike_count": len(ais_cross),
        "firing_frequency_Hz": firing_freq_hz,
        "baseline_soma_mV": baseline_v,
        "recovery_soma_mV": recovery_v,
        "first_spike_latency_ms": spike_rows["first_spike_latency_ms"].dropna().iloc[0] if len(spike_rows) and spike_rows["first_spike_latency_ms"].notna().any() else np.nan,
        "mean_ISI_ms": mean_isi,
        "adaptation_ratio_lastISI_firstISI": adaptation_ratio,
        "mean_soma_threshold_mV": spike_rows["soma_threshold_mV"].mean() if len(spike_rows) else np.nan,
        "mean_soma_peak_mV": spike_rows["soma_peak_mV"].mean() if len(spike_rows) else np.nan,
        "mean_soma_AP_amplitude_mV": spike_rows["soma_AP_amplitude_mV"].mean() if len(spike_rows) else np.nan,
        "mean_soma_half_width_ms": spike_rows["soma_AP_half_width_ms"].mean() if len(spike_rows) else np.nan,
        "mean_soma_base_width_minus20_ms": spike_rows["soma_AP_base_width_at_minus20_ms"].mean() if len(spike_rows) else np.nan,
        "mean_soma_AHP_mV": spike_rows["soma_AHP_mV"].mean() if len(spike_rows) else np.nan,
        "mean_approx_ADP_from_AHP_mV": spike_rows["approx_ADP_from_AHP_mV"].mean() if len(spike_rows) else np.nan,
    }

    return df, spike_rows, summary


def main():
    trace_paths = sorted(
        glob.glob(os.path.join(TRACE_DIR, "best_I_*pA.dat")),
        key=parse_current_pa
    )

    if not trace_paths:
        raise FileNotFoundError(f"No .dat files found in {TRACE_DIR}")

    all_spikes = []
    summaries = []

    for path in trace_paths:
        print(f"Processing: {path}")
        df, spike_rows, summary = extract_trace_features(path)

        if len(spike_rows):
            all_spikes.append(spike_rows)
        summaries.append(summary)

    all_spikes_df = pd.concat(all_spikes, ignore_index=True) if all_spikes else pd.DataFrame()
    summary_df = pd.DataFrame(summaries).sort_values("current_pA")

    all_spikes_csv = os.path.join(OUT_DIR, "L796_step5_somatic_AP_features_per_spike.csv")
    summary_csv = os.path.join(OUT_DIR, "L796_step5_somatic_AP_features_summary.csv")

    all_spikes_df.to_csv(all_spikes_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)

    print(f"\nSaved per-spike features: {all_spikes_csv}")
    print(f"Saved summary features:   {summary_csv}")

    # F-I curve from extracted features
    plt.figure(figsize=(7, 5))
    plt.plot(summary_df["current_pA"], summary_df["soma_spike_count"], marker="o")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Somatic spike count during 500 ms")
    plt.title("L796 Step 5 somatic F-I curve")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "L796_step5_somatic_FI_curve_from_features.png"), dpi=300)
    plt.close()

    # latency curve
    plt.figure(figsize=(7, 5))
    plt.plot(summary_df["current_pA"], summary_df["first_spike_latency_ms"], marker="o")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("First-spike latency (ms)")
    plt.title("L796 Step 5 first-spike latency")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "L796_step5_first_spike_latency.png"), dpi=300)
    plt.close()

    # AP peak curve
    plt.figure(figsize=(7, 5))
    plt.plot(summary_df["current_pA"], summary_df["mean_soma_peak_mV"], marker="o")
    plt.xlabel("Injected current (pA)")
    plt.ylabel("Mean somatic AP peak (mV)")
    plt.title("L796 Step 5 somatic AP peak")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "L796_step5_somatic_AP_peak.png"), dpi=300)
    plt.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
