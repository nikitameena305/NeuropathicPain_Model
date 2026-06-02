#!/usr/bin/env python3

"""
Project 2: DRG Hyperexcitability + SDH Disinhibition Combined Model

This script uses ModelDB 267056 spike output and reconstructs population
identity using known population order and population sizes.

Why manual mapping?
The saved 100mN_data.json contains spike times and spike cell IDs, but in this
export the population labels are not stored in the usual NetPyNE places.
So we map GIDs by population order and known cell counts from the model.

Outputs:
- project2/results/project2_baseline_population_rates.csv
- project2/results/project2_condition_summary.csv
- project2/figures/project2_projection_output_barplot.png
- project2/figures/project2_relative_output_index.png
- project2/logs/project2_run_log.txt
"""

import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path.home() / "NeuropathicPain_Model"

INPUT_JSON_CANDIDATES = [
    ROOT / "modeldb" / "267056" / "data" / "100mN_data.json",
    ROOT / "data" / "100mN_data.json",
]

OUT_DIR = ROOT / "project2"
RESULTS_DIR = OUT_DIR / "results"
FIGURES_DIR = OUT_DIR / "figures"
LOGS_DIR = OUT_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def find_input_json():
    for path in INPUT_JSON_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find 100mN_data.json.")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_sim_duration_seconds(data):
    """
    Your previous ModelDB 267056 run summary was 5 seconds.
    If duration is stored in simConfig, use that. Otherwise fallback to 5 sec.
    """
    sim_config = data.get("simConfig", {})
    duration_ms = sim_config.get("duration", None)

    if duration_ms is not None:
        return float(duration_ms) / 1000.0

    return 5.0


def manual_modeldb267056_gid_to_population():
    """
    Reconstruct GID to population mapping.

    Known population sizes from ModelDB 267056 / previous run summary:

    Ab_SAI: 10
    Ab_SAII: 10
    Ad: 20
    C_PEP: 40
    C_NP: 80
    PKC: 75
    VGLUT3: 10
    PV: 15
    DOR: 15
    TrC: 5
    DYN: 10
    SOM: 15
    CR: 100
    ISLET: 4
    NK1: 9

    Total = 418 if all listed exactly.
    But active cells may be fewer because not all neurons spike.
    That is okay.

    Important:
    This maps population identity by sequential GID order.
    """
    population_sizes = [
        ("Ab_SAI", 10),
        ("Ab_SAII", 10),
        ("Ad", 20),
        ("C_PEP", 40),
        ("C_NP", 80),
        ("PKC", 75),
        ("VGLUT3", 10),
        ("PV", 15),
        ("DOR", 15),
        ("TrC", 5),
        ("DYN", 10),
        ("SOM", 15),
        ("CR", 100),
        ("ISLET", 4),
        ("NK1", 9),
    ]

    gid_to_pop = {}
    gid = 0

    for pop_name, n_cells in population_sizes:
        for _ in range(n_cells):
            gid_to_pop[gid] = pop_name
            gid += 1

    return gid_to_pop, population_sizes


def extract_population_rates(data):
    sim_data = data.get("simData", {})

    spkt = sim_data.get("spkt", [])
    spkid = sim_data.get("spkid", [])

    if len(spkt) == 0 or len(spkid) == 0:
        raise ValueError("No spike data found in simData['spkt'] or simData['spkid'].")

    duration_s = get_sim_duration_seconds(data)
    gid_to_pop, population_sizes = manual_modeldb267056_gid_to_population()

    spike_counts = {}
    for gid in spkid:
        gid_int = int(gid)
        spike_counts[gid_int] = spike_counts.get(gid_int, 0) + 1

    rows = []

    for gid, pop in gid_to_pop.items():
        rows.append(
            {
                "gid": gid,
                "population": pop,
                "spikes": spike_counts.get(gid, 0),
            }
        )

    df_cells = pd.DataFrame(rows)

    df_pop = (
        df_cells.groupby("population")
        .agg(
            n_cells=("gid", "count"),
            active_cells=("spikes", lambda x: int((x > 0).sum())),
            total_spikes=("spikes", "sum"),
        )
        .reset_index()
    )

    df_pop["mean_rate_Hz"] = df_pop["total_spikes"] / df_pop["n_cells"] / duration_s
    df_pop["active_cell_fraction"] = df_pop["active_cells"] / df_pop["n_cells"]

    return df_pop, df_cells, duration_s, population_sizes


def safe_mean_rate(df_pop, population_names):
    selected = df_pop[df_pop["population"].isin(population_names)]

    if selected.empty:
        return 0.0

    total_cells = selected["n_cells"].sum()

    weighted_mean = (
        selected["mean_rate_Hz"] * selected["n_cells"]
    ).sum() / total_cells

    return float(weighted_mean)


def main():
    input_json = find_input_json()
    data = load_json(input_json)

    df_pop, df_cells, duration_s, population_sizes = extract_population_rates(data)

    # Biological population groups
    drg_input_pops = [
        "Ab_SAI",
        "Ab_SAII",
        "Ad",
        "C_PEP",
        "C_NP",
    ]

    projection_pops = [
        "NK1",
        "PKC",
        "DOR",
        "TrC",
    ]

    inhibitory_pops = [
        "PV",
        "DYN",
        "ISLET",
    ]

    baseline_drg_rate = safe_mean_rate(df_pop, drg_input_pops)
    baseline_projection_rate = safe_mean_rate(df_pop, projection_pops)
    baseline_inhibitory_rate = safe_mean_rate(df_pop, inhibitory_pops)

    if baseline_projection_rate == 0:
        raise ValueError(
            "Baseline projection rate is zero. Check projection population mapping."
        )

    conditions = [
        {
            "condition": "C1_normal_DRG_normal_GABA",
            "DRG_state": "normal",
            "GABA_state": "normal",
            "DRG_SCALE": 1.0,
            "GABA_SCALE": 1.0,
        },
        {
            "condition": "C2_hyper_DRG_normal_GABA",
            "DRG_state": "hyperexcitable",
            "GABA_state": "normal",
            "DRG_SCALE": 1.5,
            "GABA_SCALE": 1.0,
        },
        {
            "condition": "C3_normal_DRG_reduced_GABA",
            "DRG_state": "normal",
            "GABA_state": "reduced",
            "DRG_SCALE": 1.0,
            "GABA_SCALE": 0.5,
        },
        {
            "condition": "C4_hyper_DRG_reduced_GABA",
            "DRG_state": "hyperexcitable",
            "GABA_state": "reduced",
            "DRG_SCALE": 1.5,
            "GABA_SCALE": 0.5,
        },
    ]

    rows = []

    for c in conditions:
        drg_scale = c["DRG_SCALE"]
        gaba_scale = c["GABA_SCALE"]

        central_disinhibition_gain = 1.0 / gaba_scale

        predicted_projection_rate = (
            baseline_projection_rate
            * drg_scale
            * central_disinhibition_gain
        )

        relative_output_index = predicted_projection_rate / baseline_projection_rate

        rows.append(
            {
                "condition": c["condition"],
                "DRG_state": c["DRG_state"],
                "GABA_state": c["GABA_state"],
                "DRG_SCALE": drg_scale,
                "GABA_SCALE": gaba_scale,
                "central_disinhibition_gain": central_disinhibition_gain,
                "baseline_DRG_input_rate_Hz": baseline_drg_rate,
                "baseline_inhibitory_rate_Hz": baseline_inhibitory_rate,
                "baseline_projection_rate_Hz": baseline_projection_rate,
                "predicted_projection_rate_Hz": predicted_projection_rate,
                "relative_output_index_vs_C1": relative_output_index,
            }
        )

    df_conditions = pd.DataFrame(rows)

    # Save outputs
    pop_csv = RESULTS_DIR / "project2_baseline_population_rates.csv"
    df_pop.to_csv(pop_csv, index=False)

    cell_csv = RESULTS_DIR / "project2_gid_population_spike_counts.csv"
    df_cells.to_csv(cell_csv, index=False)

    condition_csv = RESULTS_DIR / "project2_condition_summary.csv"
    df_conditions.to_csv(condition_csv, index=False)

    # Plot 1: projection output
    plt.figure(figsize=(10, 6))
    plt.bar(
        df_conditions["condition"],
        df_conditions["predicted_projection_rate_Hz"],
    )
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("Predicted SDH projection output rate (Hz)")
    plt.title("Project 2: DRG Hyperexcitability + SDH Disinhibition")
    plt.tight_layout()

    fig_path = FIGURES_DIR / "project2_projection_output_barplot.png"
    plt.savefig(fig_path, dpi=300)
    plt.close()

    # Plot 2: relative output
    plt.figure(figsize=(10, 6))
    plt.bar(
        df_conditions["condition"],
        df_conditions["relative_output_index_vs_C1"],
    )
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("Relative output index vs C1")
    plt.title("Relative Pain Output Index")
    plt.tight_layout()

    fig2_path = FIGURES_DIR / "project2_relative_output_index.png"
    plt.savefig(fig2_path, dpi=300)
    plt.close()

    # Log
    log_path = LOGS_DIR / "project2_run_log.txt"
    with open(log_path, "w") as f:
        f.write("Project 2 run completed successfully.\n")
        f.write(f"Input JSON: {input_json}\n")
        f.write(f"Simulation duration used: {duration_s} seconds\n")
        f.write("\nManual population sizes used:\n")
        for pop_name, n_cells in population_sizes:
            f.write(f"{pop_name}: {n_cells}\n")
        f.write(f"\nBaseline DRG input rate: {baseline_drg_rate:.4f} Hz\n")
        f.write(f"Baseline inhibitory rate: {baseline_inhibitory_rate:.4f} Hz\n")
        f.write(f"Baseline projection rate: {baseline_projection_rate:.4f} Hz\n")
        f.write(f"Saved population rates: {pop_csv}\n")
        f.write(f"Saved cell-level counts: {cell_csv}\n")
        f.write(f"Saved condition summary: {condition_csv}\n")
        f.write(f"Saved figure 1: {fig_path}\n")
        f.write(f"Saved figure 2: {fig2_path}\n")

    print("\n✅ Project 2 completed successfully!")
    print(f"Input JSON used: {input_json}")
    print(f"Population rates saved to: {pop_csv}")
    print(f"Cell-level spike counts saved to: {cell_csv}")
    print(f"Condition summary saved to: {condition_csv}")
    print(f"Figure saved to: {fig_path}")
    print(f"Relative figure saved to: {fig2_path}")
    print(f"Log saved to: {log_path}")

    print("\nBaseline population rates:")
    print(df_pop.to_string(index=False))

    print("\nCondition summary:")
    print(df_conditions.to_string(index=False))


if __name__ == "__main__":
    main()
