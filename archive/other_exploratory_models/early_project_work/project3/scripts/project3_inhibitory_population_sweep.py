from pathlib import Path
import subprocess
import shutil
import json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.home() / "NeuropathicPain_Model"
MODEL_DIR = ROOT / "modeldb" / "267056"
NETPARAMS = MODEL_DIR / "netParams_mechanical.py"
INIT_SCRIPT = MODEL_DIR / "init_mechanical.py"

OUT_RAW = ROOT / "project3" / "results" / "raw"
OUT_SUMMARY = ROOT / "project3" / "results" / "summary"
OUT_FIG = ROOT / "project3" / "figures"
OUT_LOG = ROOT / "project3" / "logs"

for p in [OUT_RAW, OUT_SUMMARY, OUT_FIG, OUT_LOG]:
    p.mkdir(parents=True, exist_ok=True)

ORIGINAL_TEXT = NETPARAMS.read_text()

CASES = {
    "baseline_normal_inhibition": {
        "GABA_SCALE": "1.0",
        "PV_SCALE": "1.0",
        "DYN_SCALE": "1.0",
        "ISLET_SCALE": "1.0",
        "description": "Normal inhibition"
    },
    "all_inhibition_reduced": {
        "GABA_SCALE": "0.3",
        "PV_SCALE": "0.3",
        "DYN_SCALE": "0.3",
        "ISLET_SCALE": "0.3",
        "description": "All inhibition reduced"
    },
    "only_PV_inhibition_reduced": {
        "GABA_SCALE": "1.0",
        "PV_SCALE": "0.3",
        "DYN_SCALE": "1.0",
        "ISLET_SCALE": "1.0",
        "description": "Only PV inhibition reduced"
    },
    "only_DYN_inhibition_reduced": {
        "GABA_SCALE": "1.0",
        "PV_SCALE": "1.0",
        "DYN_SCALE": "0.3",
        "ISLET_SCALE": "1.0",
        "description": "Only DYN inhibition reduced"
    },
    "only_ISLET_inhibition_reduced": {
        "GABA_SCALE": "1.0",
        "PV_SCALE": "1.0",
        "DYN_SCALE": "1.0",
        "ISLET_SCALE": "0.3",
        "description": "Only ISLET inhibition reduced"
    }
}


def patch_netparams():
    txt = ORIGINAL_TEXT

    # Safety: remove accidental old bad import if present.
    txt = txt.replace("import os, sim", "from netpyne import specs, sim")

    old = "GABA_SCALE = getattr(cfg, 'GABA_SCALE', 1.0)"
    new = """GABA_SCALE = float(__import__('os').environ.get('GABA_SCALE', getattr(cfg, 'GABA_SCALE', 1.0)))
PV_SCALE = float(__import__('os').environ.get('PV_SCALE', 1.0))
DYN_SCALE = float(__import__('os').environ.get('DYN_SCALE', 1.0))
ISLET_SCALE = float(__import__('os').environ.get('ISLET_SCALE', 1.0))"""

    if old not in txt:
        raise RuntimeError("Could not find original GABA_SCALE line. Check netParams_mechanical.py.")

    txt = txt.replace(old, new)

    replacements = [
        ("cfg.PV_GABA * GABA_SCALE", "cfg.PV_GABA * GABA_SCALE * PV_SCALE"),
        ("cfg.PV_GLY * GABA_SCALE", "cfg.PV_GLY * GABA_SCALE * PV_SCALE"),
        ("cfg.DYN_GABA * GABA_SCALE", "cfg.DYN_GABA * GABA_SCALE * DYN_SCALE"),
        ("cfg.DYN_GLY * GABA_SCALE", "cfg.DYN_GLY * GABA_SCALE * DYN_SCALE"),
        ("cfg.ISLET_GABA * GABA_SCALE", "cfg.ISLET_GABA * GABA_SCALE * ISLET_SCALE"),
        ("cfg.ISLET_GLY * GABA_SCALE", "cfg.ISLET_GLY * GABA_SCALE * ISLET_SCALE"),
    ]

    for old, new in replacements:
        txt = txt.replace(old, new)

    NETPARAMS.write_text(txt)


def restore_netparams():
    NETPARAMS.write_text(ORIGINAL_TEXT)


def extract_spikes(json_path):
    data = json.load(open(json_path))
    simData = data.get("simData", {})
    net = data.get("net", {})

    spkt = simData.get("spkt", [])
    spkid = simData.get("spkid", [])

    gid_to_pop = {}
    cells = net.get("cells", [])

    if isinstance(cells, list):
        for cell in cells:
            gid = cell.get("gid", None)
            tags = cell.get("tags", {})
            pop = tags.get("pop", "unknown")
            if gid is not None:
                gid_to_pop[int(gid)] = pop

    rows = []
    for t, gid in zip(spkt, spkid):
        gid = int(gid)
        rows.append({
            "time_ms": float(t),
            "gid": gid,
            "population": gid_to_pop.get(gid, "unknown")
        })

    return pd.DataFrame(rows), len(spkt), len(spkid)


def summarize_spikes(df, case_name, duration_ms=5000):
    duration_s = duration_ms / 1000

    if df.empty:
        return pd.DataFrame([{
            "case": case_name,
            "population": "empty_spike_data",
            "n_cells": 0,
            "total_spikes": 0,
            "mean_rate_Hz": 0
        }])

    summary = (
        df.groupby("population")
        .agg(
            total_spikes=("time_ms", "count"),
            n_cells=("gid", "nunique")
        )
        .reset_index()
    )

    summary["mean_rate_Hz"] = summary["total_spikes"] / summary["n_cells"] / duration_s
    summary["case"] = case_name

    return summary[["case", "population", "n_cells", "total_spikes", "mean_rate_Hz"]]


def get_projection_output(summary):
    wanted = ["NK1", "TrC", "PKC"]
    out = summary[summary["population"].isin(wanted)].copy()

    if out.empty:
        return summary.copy()

    return out


all_summaries = []
all_projection = []
debug_rows = []

try:
    patch_netparams()

    # Fast check before long simulation.
    check = subprocess.run(
        ["python", "-m", "py_compile", str(NETPARAMS)],
        cwd=str(MODEL_DIR),
        capture_output=True,
        text=True
    )

    if check.returncode != 0:
        print("Patched netParams failed compile:")
        print(check.stderr)
        raise SystemExit(1)

    print("Patch compile check passed.")

    for case_name, params in CASES.items():
        print("\n==============================")
        print(f"Running case: {case_name}")
        print(f"Description: {params['description']}")
        print(f"GABA={params['GABA_SCALE']} PV={params['PV_SCALE']} DYN={params['DYN_SCALE']} ISLET={params['ISLET_SCALE']}")
        print("==============================")

        env = __import__("os").environ.copy()
        env["GABA_SCALE"] = params["GABA_SCALE"]
        env["PV_SCALE"] = params["PV_SCALE"]
        env["DYN_SCALE"] = params["DYN_SCALE"]
        env["ISLET_SCALE"] = params["ISLET_SCALE"]

        log_file = OUT_LOG / f"{case_name}.log"

        with open(log_file, "w") as log:
            run = subprocess.run(
                ["python", str(INIT_SCRIPT)],
                cwd=str(MODEL_DIR),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT
            )

        if run.returncode != 0:
            print(f"FAILED: {case_name}")
            debug_rows.append({
                "case": case_name,
                "status": "failed_run",
                "log_file": str(log_file),
                "json_path": "",
                "n_spkt": "",
                "n_spkid": ""
            })
            continue

        json_path = MODEL_DIR / "data" / "100mN_data.json"

        if not json_path.exists():
            print(f"FAILED: JSON missing for {case_name}")
            debug_rows.append({
                "case": case_name,
                "status": "json_missing",
                "log_file": str(log_file),
                "json_path": str(json_path),
                "n_spkt": "",
                "n_spkid": ""
            })
            continue

        case_json = OUT_RAW / f"{case_name}.json"
        shutil.copy(json_path, case_json)

        df_spikes, n_spkt, n_spkid = extract_spikes(case_json)
        df_spikes.to_csv(OUT_SUMMARY / f"{case_name}_spikes.csv", index=False)

        summary = summarize_spikes(df_spikes, case_name)
        summary["description"] = params["description"]
        summary["GABA_SCALE"] = params["GABA_SCALE"]
        summary["PV_SCALE"] = params["PV_SCALE"]
        summary["DYN_SCALE"] = params["DYN_SCALE"]
        summary["ISLET_SCALE"] = params["ISLET_SCALE"]

        summary.to_csv(OUT_SUMMARY / f"{case_name}_population_summary.csv", index=False)

        projection = get_projection_output(summary)
        projection.to_csv(OUT_SUMMARY / f"{case_name}_projection_output.csv", index=False)

        all_summaries.append(summary)
        all_projection.append(projection)

        debug_rows.append({
            "case": case_name,
            "status": "success",
            "log_file": str(log_file),
            "json_path": str(json_path),
            "n_spkt": n_spkt,
            "n_spkid": n_spkid
        })

    pd.DataFrame(debug_rows).to_csv(OUT_SUMMARY / "project3_debug_run_status.csv", index=False)

    if not all_summaries:
        print("\nNO SUCCESSFUL CASES.")
        raise SystemExit(1)

    combined = pd.concat(all_summaries, ignore_index=True)
    combined.to_csv(OUT_SUMMARY / "project3_population_summary.csv", index=False)

    projection_all = pd.concat(all_projection, ignore_index=True)
    projection_all.to_csv(OUT_SUMMARY / "project3_projection_output_summary.csv", index=False)

    pivot = projection_all.pivot_table(
        index="case",
        columns="population",
        values="mean_rate_Hz",
        aggfunc="mean"
    )

    ax = pivot.plot(kind="bar", figsize=(12, 6))
    ax.set_ylabel("Mean firing rate (Hz)")
    ax.set_xlabel("Condition")
    ax.set_title("Project 3: PV vs DYN vs ISLET inhibition loss")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "project3_projection_output_barplot.png", dpi=300)
    plt.close()

    rel = projection_all.copy()
    baseline = rel[rel["case"] == "baseline_normal_inhibition"][["population", "mean_rate_Hz"]]
    baseline = baseline.rename(columns={"mean_rate_Hz": "baseline_rate_Hz"})

    rel = rel.merge(baseline, on="population", how="left")
    rel["relative_output_vs_baseline"] = rel["mean_rate_Hz"] / rel["baseline_rate_Hz"]
    rel.to_csv(OUT_SUMMARY / "project3_relative_output_vs_baseline.csv", index=False)

    ax = rel.pivot_table(
        index="case",
        columns="population",
        values="relative_output_vs_baseline",
        aggfunc="mean"
    ).plot(kind="bar", figsize=(12, 6))

    ax.axhline(1.0, linestyle="--")
    ax.set_ylabel("Relative output vs baseline")
    ax.set_xlabel("Condition")
    ax.set_title("Project 3: Relative output after population-specific inhibition loss")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "project3_relative_output_vs_baseline.png", dpi=300)
    plt.close()

    print("\nDONE: Project 3 completed.")
    print("Saved summary CSVs and figures.")

finally:
    restore_netparams()
    print("Restored original netParams_mechanical.py")
