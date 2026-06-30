import glob
import os
import re
import pandas as pd
from pandas.errors import EmptyDataError

IN_DIR = "results/step5_final_model"
OUT_DIR = "validation/ais_soma"

STIM_START = 100.0
STIM_END = 600.0

os.makedirs(OUT_DIR, exist_ok=True)

def parse_current_from_name(name):
    m = re.search(r"I_(-?\d+)pA", name)
    if m:
        return int(m.group(1))
    return None

files = sorted(glob.glob(f"{IN_DIR}/*_ais_vs_soma_check.csv"))
rows = []
skipped = []

for f in files:
    base = os.path.basename(f)
    current = parse_current_from_name(base)

    if os.path.getsize(f) == 0:
        skipped.append((base, "empty file"))
        continue

    try:
        df = pd.read_csv(f)
    except EmptyDataError:
        skipped.append((base, "EmptyDataError"))
        continue

    if len(df) == 0:
        skipped.append((base, "no spikes"))
        continue

    required_cols = [
        "soma_cross_-20mV_ms",
        "ais_cross_-20mV_ms",
        "AIS_leads_soma_by_ms",
        "AIS_minus_soma_peak_mV",
        "soma_peak_mV",
        "ais_peak_mV"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        skipped.append((base, f"missing columns: {missing}"))
        continue

    # IMPORTANT: keep only spikes during stimulus window
    df_stim = df[
        (df["soma_cross_-20mV_ms"] >= STIM_START) &
        (df["soma_cross_-20mV_ms"] <= STIM_END)
    ].copy()

    if len(df_stim) == 0:
        skipped.append((base, "no spikes inside stimulus window"))
        continue

    rows.append({
        "current_pA": current,
        "file": base,
        "stim_window_ms": f"{STIM_START}-{STIM_END}",
        "n_spikes_in_stim_window": len(df_stim),
        "mean_AIS_lead_ms": df_stim["AIS_leads_soma_by_ms"].mean(),
        "mean_AIS_minus_soma_peak_mV": df_stim["AIS_minus_soma_peak_mV"].mean(),
        "max_soma_peak_mV": df_stim["soma_peak_mV"].max(),
        "max_AIS_peak_mV": df_stim["ais_peak_mV"].max(),
    })

out = pd.DataFrame(rows)

if len(out) > 0:
    out = out.sort_values("current_pA")
    out_path = f"{OUT_DIR}/L796_step5_AIS_soma_summary_STIM_WINDOW.csv"
    out.to_csv(out_path, index=False)

    print("\nAIS-SOMA SUMMARY DURING STIMULUS WINDOW")
    print(out.to_string(index=False))
    print(f"\nSaved: {out_path}")
else:
    print("No valid AIS-soma CSV files found.")

if skipped:
    print("\nSkipped files:")
    for name, reason in skipped:
        print(f"- {name}: {reason}")
