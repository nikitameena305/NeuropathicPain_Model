import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -------------------------------------------------------
# Usage:
# python scripts/check_ais_vs_soma.py traces/step5_best_traces/best_I_60pA.dat
# -------------------------------------------------------


def read_trace_file(path):
    """
    Reads .dat or .csv trace file.
    Expected columns can be:
    time soma AIS
    or time soma_v ais_v
    or no header: time soma AIS
    """

    # First try reading with header
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = None

    # If header reading failed or gave only 1 column, try whitespace
    if df is None or df.shape[1] < 2:
        try:
            df = pd.read_csv(path, delim_whitespace=True)
        except Exception:
            df = None

    # If still bad, read as no header whitespace file
    if df is None or df.shape[1] < 2:
        df = pd.read_csv(path, delim_whitespace=True, header=None)

    # If first row became column names but columns are numeric-looking, okay.
    # If no header, assign names.
    if all(isinstance(c, int) for c in df.columns):
        if df.shape[1] >= 3:
            df = df.iloc[:, :3]
            df.columns = ["time_ms", "soma_v", "ais_v"]
        else:
            raise ValueError("File has fewer than 3 columns. Need time, soma, AIS.")

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Auto-detect columns
    time_col = None
    soma_col = None
    ais_col = None

    for col in df.columns:
        c = col.lower()
        if time_col is None and ("time" in c or c in ["t", "ms"]):
            time_col = col
        if soma_col is None and "soma" in c:
            soma_col = col
        if ais_col is None and ("ais" in c or "axon" in c):
            ais_col = col

    # Fallback if no proper names
    if time_col is None or soma_col is None or ais_col is None:
        if df.shape[1] >= 3:
            time_col = df.columns[0]
            soma_col = df.columns[1]
            ais_col = df.columns[2]
        else:
            raise ValueError("Could not detect time/soma/AIS columns.")

    out = pd.DataFrame({
        "time_ms": pd.to_numeric(df[time_col], errors="coerce"),
        "soma_v": pd.to_numeric(df[soma_col], errors="coerce"),
        "ais_v": pd.to_numeric(df[ais_col], errors="coerce"),
    })

    out = out.dropna().reset_index(drop=True)
    return out


def crossing_times(time, voltage, threshold=-20.0):
    """
    Detect upward threshold crossings with linear interpolation.
    """
    times = []
    indices = []

    for i in range(1, len(voltage)):
        if voltage[i - 1] < threshold <= voltage[i]:
            t1, t2 = time[i - 1], time[i]
            v1, v2 = voltage[i - 1], voltage[i]

            if v2 != v1:
                frac = (threshold - v1) / (v2 - v1)
                cross_t = t1 + frac * (t2 - t1)
            else:
                cross_t = t2

            times.append(cross_t)
            indices.append(i)

    return np.array(times), np.array(indices)


def spike_peaks(time, voltage, cross_indices, window_ms=5.0):
    """
    For each threshold crossing, find peak within next few ms.
    """
    peaks = []
    peak_times = []

    for idx in cross_indices:
        t_start = time[idx]
        t_end = t_start + window_ms

        win = np.where((time >= t_start) & (time <= t_end))[0]

        if len(win) == 0:
            peaks.append(np.nan)
            peak_times.append(np.nan)
            continue

        local_idx = win[np.argmax(voltage[win])]
        peaks.append(voltage[local_idx])
        peak_times.append(time[local_idx])

    return np.array(peaks), np.array(peak_times)


def main():
    if len(sys.argv) < 2:
        print("\nUse like this:")
        print("python scripts/check_ais_vs_soma.py traces/step5_best_traces/best_I_60pA.dat\n")
        sys.exit(1)

    trace_path = sys.argv[1]

    if not os.path.exists(trace_path):
        print(f"File not found: {trace_path}")
        sys.exit(1)

    df = read_trace_file(trace_path)

    t = df["time_ms"].to_numpy()
    soma = df["soma_v"].to_numpy()
    ais = df["ais_v"].to_numpy()

    threshold = -20.0

    soma_cross_t, soma_cross_i = crossing_times(t, soma, threshold)
    ais_cross_t, ais_cross_i = crossing_times(t, ais, threshold)

    soma_peaks, soma_peak_times = spike_peaks(t, soma, soma_cross_i)
    ais_peaks, ais_peak_times = spike_peaks(t, ais, ais_cross_i)

    n = min(len(soma_cross_t), len(ais_cross_t))

    print("\n==============================")
    print("AIS vs SOMA CHECK")
    print("==============================")
    print(f"Trace file: {trace_path}")
    print(f"Soma spikes detected: {len(soma_cross_t)}")
    print(f"AIS spikes detected : {len(ais_cross_t)}")

    print("\nGlobal peak check:")
    print(f"Max soma voltage = {np.max(soma):.4f} mV")
    print(f"Max AIS voltage  = {np.max(ais):.4f} mV")
    print(f"AIS - soma peak  = {np.max(ais) - np.max(soma):.4f} mV")

    rows = []

    for i in range(n):
        ais_lead = soma_cross_t[i] - ais_cross_t[i]
        peak_diff = ais_peaks[i] - soma_peaks[i]

        rows.append({
            "spike_no": i + 1,
            "soma_cross_-20mV_ms": soma_cross_t[i],
            "ais_cross_-20mV_ms": ais_cross_t[i],
            "AIS_leads_soma_by_ms": ais_lead,
            "soma_peak_mV": soma_peaks[i],
            "ais_peak_mV": ais_peaks[i],
            "AIS_minus_soma_peak_mV": peak_diff,
            "soma_peak_time_ms": soma_peak_times[i],
            "ais_peak_time_ms": ais_peak_times[i],
        })

    result = pd.DataFrame(rows)

    if len(result) > 0:
        print("\nPer-spike comparison:")
        print(result.to_string(index=False))

        print("\nSummary:")
        print(f"Mean AIS lead over soma = {result['AIS_leads_soma_by_ms'].mean():.5f} ms")
        print(f"Mean AIS-soma peak difference = {result['AIS_minus_soma_peak_mV'].mean():.5f} mV")

        if result["AIS_leads_soma_by_ms"].mean() > 0:
            print("Timing result: AIS crosses -20 mV BEFORE soma.")
        elif result["AIS_leads_soma_by_ms"].mean() < 0:
            print("Timing result: Soma crosses -20 mV BEFORE AIS.")
        else:
            print("Timing result: AIS and soma cross at same time.")

        if result["AIS_minus_soma_peak_mV"].mean() > 0:
            print("Peak result: AIS spike peak is higher than soma.")
        elif result["AIS_minus_soma_peak_mV"].mean() < 0:
            print("Peak result: Soma spike peak is higher than AIS.")
        else:
            print("Peak result: AIS and soma peaks are same.")

    else:
        print("\nNo spikes detected using -20 mV threshold.")

    # Save output
    base = os.path.splitext(os.path.basename(trace_path))[0]

    out_dir = "results/step5_final_model"
    fig_dir = "figures/step5_final_model"

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(fig_dir, exist_ok=True)

    out_csv = os.path.join(out_dir, f"{base}_ais_vs_soma_check.csv")
if len(result) > 0:
    result.to_csv(out_csv, index=False)
else:
    empty_result = pd.DataFrame(columns=[
        "spike_no",
        "soma_cross_-20mV_ms",
        "ais_cross_-20mV_ms",
        "AIS_leads_soma_by_ms",
        "soma_peak_mV",
        "ais_peak_mV",
        "AIS_minus_soma_peak_mV",
        "soma_peak_time_ms",
        "ais_peak_time_ms"
    ])
    empty_result.to_csv(out_csv, index=False)
    # Full trace figure
    out_png = os.path.join(fig_dir, f"{base}_ais_vs_soma_check.png")

    plt.figure(figsize=(11, 5))
    plt.plot(t, soma, label="soma", linewidth=2)
    plt.plot(t, ais, label="AIS", linewidth=1.2, linestyle="--")
    plt.axhline(threshold, linestyle=":", label="-20 mV threshold")
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (mV)")
    plt.title(f"AIS vs soma comparison: {base}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()

    # Zoom figure around first spike
    if len(soma_cross_t) > 0:
        zoom_start = soma_cross_t[0] - 10
        zoom_end = soma_cross_t[0] + 20

        zoom = np.where((t >= zoom_start) & (t <= zoom_end))[0]

        out_zoom_png = os.path.join(fig_dir, f"{base}_first_spike_zoom.png")

        plt.figure(figsize=(8, 5))
        plt.plot(t[zoom], soma[zoom], label="soma", linewidth=2)
        plt.plot(t[zoom], ais[zoom], label="AIS", linewidth=1.2, linestyle="--")
        plt.axhline(threshold, linestyle=":", label="-20 mV threshold")
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (mV)")
        plt.title(f"First spike zoom: {base}")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_zoom_png, dpi=300)
        plt.close()

        print(f"\nSaved zoom figure: {out_zoom_png}")

    print(f"\nSaved CSV: {out_csv}")
    print(f"Saved figure: {out_png}")


if __name__ == "__main__":
    main()
