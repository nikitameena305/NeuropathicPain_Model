from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project1"

DATA = PROJECT / "data"
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"

RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)

json_file = DATA / "baseline_100mN_data.json"
mapping_file = RESULTS / "project1_population_mapping_inferred.csv"

with open(json_file) as f:
    data = json.load(f)

mapping = pd.read_csv(mapping_file)

# ----------------------------
# Flexible spike extraction
# ----------------------------
spike_rows = []

def try_extract_from_dict(d):
    rows = []

    # Case 1: common structure with spike_times and spike_ids
    possible_time_keys = ["spike_times", "spkt", "tvec", "times", "spike_t"]
    possible_id_keys = ["spike_ids", "spkid", "idvec", "gids", "cell_ids", "spike_id"]

    time_key = None
    id_key = None

    for k in possible_time_keys:
        if k in d:
            time_key = k
            break

    for k in possible_id_keys:
        if k in d:
            id_key = k
            break

    if time_key and id_key:
        times = d[time_key]
        ids = d[id_key]
        for t, cid in zip(times, ids):
            rows.append({"time_ms": float(t), "cell_id": int(cid)})
        return rows

    return rows

if isinstance(data, dict):
    spike_rows = try_extract_from_dict(data)

    # Case 2: nested population dictionary
    if not spike_rows:
        for key, value in data.items():
            if isinstance(value, dict):
                rows = try_extract_from_dict(value)
                for r in rows:
                    r["source_key"] = key
                spike_rows.extend(rows)

elif isinstance(data, list):
    # Case 3: list of spike records
    for item in data:
        if isinstance(item, dict):
            possible_t = item.get("time_ms", item.get("t", item.get("time", None)))
            possible_id = item.get("cell_id", item.get("gid", item.get("id", None)))
            if possible_t is not None and possible_id is not None:
                spike_rows.append({"time_ms": float(possible_t), "cell_id": int(possible_id)})

if not spike_rows:
    print("ERROR: Could not automatically extract spikes.")
    print("Your JSON structure is different.")
    print("Run this to inspect:")
    print("python - <<'PY'")
    print("import json; d=json.load(open('project1/data/baseline_100mN_data.json')); print(d.keys() if isinstance(d,dict) else type(d)); print(str(d)[:1000])")
    print("PY")
    raise SystemExit

spikes = pd.DataFrame(spike_rows)

# Merge with population mapping
spikes = spikes.merge(mapping, on="cell_id", how="left")

# Save raw spike table
spikes_out = RESULTS / "baseline_spike_table_mapped.csv"
spikes.to_csv(spikes_out, index=False)

# Estimate simulation duration
duration_ms = spikes["time_ms"].max() - spikes["time_ms"].min()
duration_s = duration_ms / 1000 if duration_ms > 0 else 5.0

# Population firing rates
pop_summary = (
    spikes.groupby(["population", "broad_class"], dropna=False)
    .agg(
        total_spikes=("time_ms", "count"),
        active_cells=("cell_id", "nunique"),
        first_spike_ms=("time_ms", "min"),
        last_spike_ms=("time_ms", "max")
    )
    .reset_index()
)

pop_summary["mean_rate_Hz"] = pop_summary["total_spikes"] / pop_summary["active_cells"] / duration_s

pop_out = RESULTS / "baseline_population_rates.csv"
pop_summary.to_csv(pop_out, index=False)

# Projection output
projection = pop_summary[pop_summary["broad_class"] == "projection"].copy()
projection_out = RESULTS / "baseline_projection_output.csv"
projection.to_csv(projection_out, index=False)

# E/I ratio
exc_spikes = pop_summary.loc[pop_summary["broad_class"].isin(["excitatory_or_interneuron", "projection"]), "total_spikes"].sum()
inh_spikes = pop_summary.loc[pop_summary["broad_class"] == "inhibitory", "total_spikes"].sum()

ei_ratio = exc_spikes / inh_spikes if inh_spikes > 0 else np.nan

summary = pd.DataFrame([{
    "condition": "baseline_100_percent_GABA",
    "duration_s": duration_s,
    "total_spikes": len(spikes),
    "excitatory_plus_projection_spikes": exc_spikes,
    "inhibitory_spikes": inh_spikes,
    "E_I_ratio": ei_ratio,
    "projection_total_spikes": projection["total_spikes"].sum() if len(projection) else 0,
    "projection_mean_rate_Hz": projection["mean_rate_Hz"].mean() if len(projection) else np.nan
}])

summary_out = RESULTS / "baseline_summary_metrics.csv"
summary.to_csv(summary_out, index=False)

# Raster plot
plt.figure(figsize=(12, 6))
plt.scatter(spikes["time_ms"], spikes["cell_id"], s=3)
plt.xlabel("Time (ms)")
plt.ylabel("Cell ID")
plt.title("Baseline SDH Raster Plot: 100% GABA Inhibition")
plt.tight_layout()
plt.savefig(FIGURES / "baseline_raster_100_percent_GABA.png", dpi=300)
plt.close()

# Population firing bar plot
plot_df = pop_summary.sort_values("mean_rate_Hz", ascending=False)

plt.figure(figsize=(12, 6))
plt.bar(plot_df["population"].astype(str), plot_df["mean_rate_Hz"])
plt.xticks(rotation=45, ha="right")
plt.ylabel("Mean firing rate (Hz)")
plt.title("Baseline Population Firing Rates")
plt.tight_layout()
plt.savefig(FIGURES / "baseline_population_firing_rates.png", dpi=300)
plt.close()

print("Saved:")
print(spikes_out)
print(pop_out)
print(projection_out)
print(summary_out)
print(FIGURES / "baseline_raster_100_percent_GABA.png")
print(FIGURES / "baseline_population_firing_rates.png")
print()
print(summary)
