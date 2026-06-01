import json
import os
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path.home() / "NeuropathicPain_Model"
OUTDIR = ROOT / "deliverables" / "week1"
OUTDIR.mkdir(parents=True, exist_ok=True)

SEARCH_DIRS = [
    ROOT / "results" / "modeldb_267056",
    ROOT / "modeldb" / "267056",
    ROOT / "external" / "SDHmodel",
]

def find_json_files():
    files = []
    for d in SEARCH_DIRS:
        if d.exists():
            files.extend(d.rglob("*.json"))
    return sorted(files, key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)

def load_json(path):
    with open(path, "r", errors="ignore") as f:
        return json.load(f)

def get_nested(d, keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def extract_netpyne_spikes(data):
    # Most NetPyNE outputs store spikes here:
    simdata = data.get("simData", {}) if isinstance(data, dict) else {}

    spkt = simdata.get("spkt", None)
    spkid = simdata.get("spkid", None)

    if spkt is None or spkid is None:
        # Some files may store directly at top level
        spkt = data.get("spkt", None) if isinstance(data, dict) else None
        spkid = data.get("spkid", None) if isinstance(data, dict) else None

    if spkt is None or spkid is None:
        raise ValueError("Could not find NetPyNE spike arrays spkt/spkid in JSON.")

    spkt = np.array(spkt, dtype=float)
    spkid = np.array(spkid, dtype=int)

    if len(spkt) != len(spkid):
        raise ValueError("spkt and spkid lengths do not match.")

    return spkt, spkid

def extract_gid_to_pop(data):
    gid_to_pop = {}

    net = data.get("net", {}) if isinstance(data, dict) else {}
    cells = net.get("cells", None)

    if isinstance(cells, list):
        for cell in cells:
            try:
                gid = int(cell.get("gid"))
                tags = cell.get("tags", {})
                pop = tags.get("pop", "unknown")
                gid_to_pop[gid] = pop
            except Exception:
                pass

    elif isinstance(cells, dict):
        for gid_key, cell in cells.items():
            try:
                gid = int(gid_key)
                tags = cell.get("tags", {})
                pop = tags.get("pop", "unknown")
                gid_to_pop[gid] = pop
            except Exception:
                pass

    # Alternative NetPyNE style
    pops = net.get("pops", {})
    if not gid_to_pop and isinstance(pops, dict):
        # Cannot always reconstruct gid mapping, but keep placeholder
        pass

    return gid_to_pop

def compute_rates(spkt, spkid, gid_to_pop):
    if len(spkt) == 0:
        raise ValueError("No spikes found.")

    duration_ms = float(np.max(spkt) - np.min(spkt))
    if duration_ms <= 0:
        duration_ms = float(np.max(spkt))

    duration_s = duration_ms / 1000.0

    rows = []
    all_gids = sorted(set(spkid.tolist()))

    for gid in all_gids:
        pop = gid_to_pop.get(gid, "unknown")
        nspikes = int(np.sum(spkid == gid))
        rate_hz = nspikes / duration_s if duration_s > 0 else math.nan
        rows.append({
            "gid": gid,
            "population": pop,
            "spike_count": nspikes,
            "duration_ms": duration_ms,
            "firing_rate_Hz": rate_hz,
        })

    cell_df = pd.DataFrame(rows)

    pop_df = (
        cell_df.groupby("population", dropna=False)
        .agg(
            n_cells=("gid", "count"),
            total_spikes=("spike_count", "sum"),
            mean_rate_Hz=("firing_rate_Hz", "mean"),
            median_rate_Hz=("firing_rate_Hz", "median"),
            max_rate_Hz=("firing_rate_Hz", "max"),
        )
        .reset_index()
        .sort_values("mean_rate_Hz", ascending=False)
    )

    return cell_df, pop_df, duration_ms

def plot_raster(spkt, spkid, gid_to_pop, json_name):
    # Focus useful populations: GABA/inhibitory and TrC/eTrC if labels exist
    labels = [gid_to_pop.get(int(g), "unknown") for g in spkid]
    labels_arr = np.array(labels)

    keywords = ["GABA", "gaba", "Gly", "gly", "PV", "DYN", "islet", "TrC", "eTrC", "TC", "tonic"]
    mask = np.zeros(len(spkt), dtype=bool)

    for kw in keywords:
        mask |= np.char.find(labels_arr.astype(str), kw) >= 0

    # If no matching labels, plot first 5000 spikes
    if mask.sum() < 5:
        mask = np.ones(len(spkt), dtype=bool)

    idx = np.where(mask)[0]
    if len(idx) > 5000:
        idx = idx[:5000]

    plt.figure(figsize=(12, 6))
    plt.scatter(spkt[idx], spkid[idx], s=3)
    plt.xlabel("Time (ms)")
    plt.ylabel("Cell ID")
    plt.title(f"ModelDB 267056 SDH tonic firing / raster\nSource: {json_name}")
    plt.tight_layout()

    fig_path = OUTDIR / "modeldb267056_tonic_firing.png"
    plt.savefig(fig_path, dpi=300)
    plt.close()
    return fig_path

def main():
    json_files = find_json_files()
    if not json_files:
        raise FileNotFoundError("No JSON files found for ModelDB 267056. Run the model first or locate output JSON.")

    print("JSON candidates:")
    for p in json_files[:10]:
        print(" -", p)

    # use largest json file first
    json_path = json_files[0]
    print(f"\nUsing JSON file: {json_path}")

    data = load_json(json_path)
    spkt, spkid = extract_netpyne_spikes(data)
    gid_to_pop = extract_gid_to_pop(data)

    cell_df, pop_df, duration_ms = compute_rates(spkt, spkid, gid_to_pop)

    cell_csv = OUTDIR / "modeldb267056_cell_rates.csv"
    pop_csv = OUTDIR / "modeldb267056_population_rates.csv"
    summary_txt = OUTDIR / "modeldb267056_summary.txt"

    cell_df.to_csv(cell_csv, index=False)
    pop_df.to_csv(pop_csv, index=False)

    fig_path = plot_raster(spkt, spkid, gid_to_pop, json_path.name)

    # Try to identify eTrC/TrC and GABA-related populations
    pop_names = pop_df["population"].astype(str)
    etrc_df = pop_df[pop_names.str.contains("eTrC|TrC|tonic", case=False, regex=True)]
    gaba_df = pop_df[pop_names.str.contains("GABA|PV|DYN|islet|inhib|gly", case=False, regex=True)]

    with open(summary_txt, "w") as f:
        f.write("ModelDB 267056 Week 1 extraction summary\n")
        f.write("=========================================\n")
        f.write(f"Source JSON: {json_path}\n")
        f.write(f"Total spikes: {len(spkt)}\n")
        f.write(f"Unique spiking cells: {len(set(spkid.tolist()))}\n")
        f.write(f"Duration analysed: {duration_ms:.3f} ms\n\n")

        f.write("Top population firing rates:\n")
        f.write(pop_df.head(20).to_string(index=False))
        f.write("\n\n")

        f.write("Possible eTrC/TrC populations:\n")
        if len(etrc_df):
            f.write("\n" + etrc_df.to_string(index=False))
        else:
            f.write("\nNo eTrC/TrC-labelled population detected automatically.")
        f.write("\n\n")

        f.write("Possible GABA/inhibitory populations for Group 3 focus:\n")
        if len(gaba_df):
            f.write("\n" + gaba_df.to_string(index=False))
        else:
            f.write("\nNo GABA/inhibitory-labelled population detected automatically.")
        f.write("\n\n")

        f.write("Stimulus current pA: not automatically extracted from JSON; check model config/readme if required.\n")
        f.write("Match to Medlock Fig. 3: write Y/N after visual comparison with paper/model documentation.\n")

    print("\nDONE.")
    print("Created:")
    print(" ", cell_csv)
    print(" ", pop_csv)
    print(" ", summary_txt)
    print(" ", fig_path)
    print("\nTop population rates:")
    print(pop_df.head(20).to_string(index=False))

if __name__ == "__main__":
    main()
