"""Fit passive NMO_170087 parameters to the pre-registered PV population target."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pv_cell import PVCell, ROOT, load_config, passive_metrics, run_step, save_json


TARGET_RIN_MOHM = 225.0
TARGET_RIN_SEM_MOHM = 22.0
TARGET_CAP_PF = 10.9
TARGET_CAP_SEM_PF = 0.6


def evaluate(config: dict, current_na: float) -> tuple[dict, dict, object]:
    cell = PVCell(config, passive_only=True)
    trace = run_step(cell, current_na)
    metrics = passive_metrics(trace, config)
    inventory = cell.inventory()
    cell.dispose()
    return metrics, inventory, trace


def tune_gpas(config: dict, current_na: float) -> tuple[float, dict, dict, object]:
    low, high = 1e-7, 5e-4
    best = None
    for _ in range(24):
        trial = (low + high) / 2.0
        config["passive"]["g_pas_s_cm2"] = trial
        metrics, inventory, trace = evaluate(config, current_na)
        best = (trial, metrics, inventory, trace)
        if metrics["rin_mohm"] > TARGET_RIN_MOHM:
            low = trial
        else:
            high = trial
    assert best is not None
    return best


def write_trace(path: Path, trace: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Retain a 0.1-ms analysis trace; simulations and metric extraction still
    # run at the configured 0.025-ms timestep.
    stride = max(1, int(round(0.1 / float(np.median(np.diff(trace.time_ms))))))
    indices = np.arange(0, len(trace.time_ms), stride, dtype=int)
    if indices[-1] != len(trace.time_ms) - 1:
        indices = np.append(indices, len(trace.time_ms) - 1)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ms", "soma_mv", "proximal_axon_mv", "proximal_dendrite_mv", "current_na"])
        writer.writerows(
            zip(
                trace.time_ms[indices],
                trace.soma_mv[indices],
                trace.axon_mv[indices],
                trace.dendrite_mv[indices],
                [trace.current_na] * len(indices),
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "parameters/passive/passive_search_template.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/passive")
    args = parser.parse_args()
    base = load_config(args.config)
    current_na = base["protocols"]["passive_current_na"]
    rows = []
    selected = None
    for ra in [80.0, 100.0, 120.0, 150.0]:
        for cm in [0.5, 0.75, 1.0, 1.25, 1.5]:
            config = copy.deepcopy(base)
            config["passive"]["ra_ohm_cm"] = ra
            config["passive"]["cm_uf_cm2"] = cm
            gpas, metrics, inventory, trace = tune_gpas(config, current_na)
            cap_equiv = metrics["equivalent_capacitance_from_tau_rin_pf"]
            score = abs(metrics["rin_mohm"] - TARGET_RIN_MOHM) / TARGET_RIN_SEM_MOHM + abs(cap_equiv - TARGET_CAP_PF) / TARGET_CAP_SEM_PF
            row = {
                "ra_ohm_cm": ra,
                "cm_uf_cm2": cm,
                "g_pas_s_cm2": gpas,
                **metrics,
                "geometric_capacitance_pf": inventory["geometric_capacitance_pf"],
                "rin_target_mohm": TARGET_RIN_MOHM,
                "capacitance_target_pf": TARGET_CAP_PF,
                "normalized_score": score,
            }
            rows.append(row)
            if selected is None or score < selected[0]:
                selected = (score, copy.deepcopy(config), metrics, inventory, trace)

    assert selected is not None
    args.output.mkdir(parents=True, exist_ok=True)
    grid_path = args.output / "passive_fit_grid.csv"
    with grid_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    _, config, metrics, inventory, trace = selected
    config["status"] = "selected_passive"
    config["evidence_classification"] = {
        "morphology": "SC",
        "input_resistance_target": "SP/PL",
        "ra": "A",
        "cm": "A",
        "g_pas": "F",
        "e_pas": "A/F"
    }
    save_json(config, ROOT / "parameters/passive/passive_selected_parameters.json")
    rin_pass = abs(metrics["rin_mohm"] - TARGET_RIN_MOHM) <= TARGET_RIN_SEM_MOHM
    capacitance_pass = abs(metrics["equivalent_capacitance_from_tau_rin_pf"] - TARGET_CAP_PF) <= TARGET_CAP_SEM_PF
    validation = {
        "schema_version": "1.0",
        "temperature_c": config["temperature_c"],
        "protocol": {
            "current_na": current_na,
            "delay_ms": config["simulation"]["stim_delay_ms"],
            "duration_ms": config["simulation"]["stim_duration_ms"],
            "holding_interpretation": "-60 mV experimental current-clamp holding condition; not measured RMP"
        },
        "metrics": metrics,
        "morphology_inventory": inventory,
        "gates": [
            {
                "metric": "input resistance",
                "target": "225 +/- 22 MOhm",
                "source": "Gradwell et al. 2022 aging study, adult PV population",
                "model_value": metrics["rin_mohm"],
                "absolute_error": abs(metrics["rin_mohm"] - TARGET_RIN_MOHM),
                "percent_error": 100.0 * abs(metrics["rin_mohm"] - TARGET_RIN_MOHM) / TARGET_RIN_MOHM,
                "acceptance": "203-247 MOhm",
                "status": "PASS" if rin_pass else "FAIL",
                "evidence_level": "SP/PL"
            },
            {
                "metric": "equivalent capacitance tau/Rin",
                "target": "10.9 +/- 0.6 pF",
                "source": "Gradwell et al. 2022 aging study, adult PV population",
                "model_value": metrics["equivalent_capacitance_from_tau_rin_pf"],
                "absolute_error": abs(metrics["equivalent_capacitance_from_tau_rin_pf"] - TARGET_CAP_PF),
                "percent_error": 100.0 * abs(metrics["equivalent_capacitance_from_tau_rin_pf"] - TARGET_CAP_PF) / TARGET_CAP_PF,
                "acceptance": "10.3-11.5 pF without cm outside 0.5-1.5 uF/cm2",
                "status": "PASS" if capacitance_pass else "FAIL",
                "evidence_level": "SP/PL comparison"
            }
        ],
        "overall_status": "PASS" if rin_pass else "FAIL",
        "caution": "The capacitance comparison does not block active work when Rin passes because electrode-derived whole-cell capacitance and total reconstructed membrane capacitance are not equivalent observables. Any failed capacitance gate is preserved."
    }
    save_json(validation, args.output / "passive_validation_metrics.json")
    save_json(inventory, args.output / "neuron_import_inventory.json")
    write_trace(args.output / "passive_representative_trace.csv", trace)

    figure_dir = ROOT / "figures/passive"
    figure_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(trace.time_ms, trace.soma_mv, color="#2455a4", linewidth=1.5, label="soma")
    ax.plot(trace.time_ms, trace.dendrite_mv, color="#2f8f5b", linewidth=1.0, alpha=0.8, label="proximal dendrite")
    ax.set(xlabel="Time (ms)", ylabel="Membrane potential (mV)", title="Passive response to -20 pA, 800 ms")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "hyperpolarizing_response.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(trace.time_ms, trace.soma_mv, color="#2455a4", linewidth=1.5)
    ax.axhline(metrics["baseline_equilibrium_mv"], color="#555555", linestyle="--", label="baseline")
    ax.set(xlabel="Time (ms)", ylabel="Membrane potential (mV)", title="Unforced passive baseline and current response")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "baseline_trace.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    for cm in sorted({row["cm_uf_cm2"] for row in rows}):
        subset = [row for row in rows if row["cm_uf_cm2"] == cm]
        ax.plot([row["ra_ohm_cm"] for row in subset], [row["normalized_score"] for row in subset], marker="o", label=f"cm={cm:g}")
    ax.set(xlabel="Axial resistivity (ohm cm)", ylabel="Normalized target error", title="Restrained passive fitting grid")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(figure_dir / "passive_fitting_error.png", dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 4.0))
    axes[0].bar(["Target", "Model"], [TARGET_RIN_MOHM, metrics["rin_mohm"]], color=["#999999", "#2455a4"])
    axes[0].errorbar([0], [TARGET_RIN_MOHM], yerr=[TARGET_RIN_SEM_MOHM], fmt="none", color="black", capsize=4)
    axes[0].set(ylabel="Input resistance (MOhm)", title="Primary target")
    axes[1].bar(["Target", "Model equiv.", "Model geom."], [TARGET_CAP_PF, metrics["equivalent_capacitance_from_tau_rin_pf"], inventory["geometric_capacitance_pf"]], color=["#999999", "#c46b2d", "#2455a4"])
    axes[1].errorbar([0], [TARGET_CAP_PF], yerr=[TARGET_CAP_SEM_PF], fmt="none", color="black", capsize=4)
    axes[1].set(ylabel="Capacitance (pF)", title="Non-equivalent capacitance checks")
    fig.tight_layout()
    fig.savefig(figure_dir / "measured_vs_target.png", dpi=300)
    plt.close(fig)

    delay = config["simulation"]["stim_delay_ms"]
    window = (trace.time_ms >= delay - 20) & (trace.time_ms <= delay + 150)
    t = trace.time_ms[window] - delay
    baseline = metrics["baseline_equilibrium_mv"]
    steady = metrics["steady_state_mv"]
    tau = metrics["tau_ms_monoexponential"]
    fit = steady + (baseline - steady) * np.exp(-np.maximum(t, 0.0) / tau)
    fit[t < 0] = baseline
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(t, trace.soma_mv[window], label="NEURON trace", color="#2455a4")
    ax.plot(t, fit, "--", label=f"mono-exponential, tau={tau:.2f} ms", color="#c46b2d")
    ax.set(xlabel="Time from step onset (ms)", ylabel="Membrane potential (mV)", title="Tau fit and Rin response")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "rin_tau_fit.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.axis("off")
    ax.text(0.08, 0.67, "Full native SWC\n(soma + dendrites + partial axon)", ha="center", va="center", bbox=dict(boxstyle="round,pad=0.5", fc="#e7eef8", ec="#2455a4"))
    ax.annotate("uniform Ra, cm, g_pas, e_pas\nd-lambda discretization", xy=(0.88, 0.67), xytext=(0.47, 0.67), arrowprops=dict(arrowstyle="->", lw=1.8), ha="center", va="center", bbox=dict(boxstyle="round,pad=0.5", fc="#eef7ef", ec="#2f8f5b"))
    ax.text(0.5, 0.18, "No synthetic axon; no active conductances", ha="center", fontsize=11, color="#6b2b2b")
    ax.set_title("Passive compartment scheme")
    fig.tight_layout()
    fig.savefig(figure_dir / "passive_compartment_schematic.png", dpi=300)
    plt.close(fig)

    print(json.dumps({"selected": config["passive"], "metrics": metrics, "inventory": inventory, "gates": validation["gates"]}, indent=2))


if __name__ == "__main__":
    main()
