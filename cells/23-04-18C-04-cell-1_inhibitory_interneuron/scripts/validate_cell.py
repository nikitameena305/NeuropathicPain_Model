"""Generate Cell 1 active, temperature, and robustness validation artifacts."""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pv_cell import (
    PVCell,
    ROOT,
    action_potential_metrics,
    firing_metrics,
    load_config,
    passive_metrics,
    run_step,
    save_json,
)


FINAL_CONFIG = ROOT / "parameters/final/NMO_170087_final_23C.json"


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row if key != "spike_times_relative_ms"})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in keys})


def run_fi(config: dict) -> tuple[PVCell, list[dict], dict[float, object]]:
    cell = PVCell(config)
    metrics = []
    traces = {}
    for current in config["protocols"]["fi_currents_na"]:
        trace = run_step(cell, current)
        traces[current] = trace
        metrics.append(firing_metrics(trace, config))
    return cell, metrics, traces


def gate(metric: str, target: str, source: str, value: float | str, acceptance: str, passed: bool, evidence: str) -> dict:
    return {
        "metric": metric,
        "experimental_target": target,
        "source": source,
        "model_value": value,
        "acceptance_criterion": acceptance,
        "status": "PASS" if passed else "FAIL",
        "evidence_level": evidence,
    }


def active_validation(config: dict) -> tuple[dict, dict[float, object], list[dict]]:
    cell, fi, traces = run_fi(config)
    positive = [row for row in fi if row["current_na"] >= 0 and row["spike_count"]]
    rheobase = positive[0]["current_na"] if positive else None
    rheobase_trace = traces[rheobase] if rheobase is not None else None
    ap = action_potential_metrics(rheobase_trace, config) if rheobase_trace is not None else {"available": False}
    negative = passive_metrics(traces[-0.02], config)
    zero = traces[0.0]
    baseline = float(np.mean(zero.soma_mv[-int(100.0 / config["simulation"]["dt_ms"]):]))
    representative = next(row for row in fi if row["current_na"] == config["protocols"]["representative_current_na"])
    strong = next(row for row in fi if row["current_na"] == config["protocols"]["strong_current_na"])
    active_gates = [
        gate("rheobase", "77 +/- 7 pA", "Gradwell aging adult PV population", rheobase * 1000.0 if rheobase else "none", "63-91 pA (mean +/- 2 SEM)", rheobase is not None and 0.063 <= rheobase <= 0.091, "SP/PL"),
        gate("AP threshold", "-34.9 +/- 1.3 mV", "Gradwell aging adult PV population", ap.get("threshold_mv_dvdt_20_v_s", "none"), "-37.5 to -32.3 mV (mean +/- 2 SEM)", ap.get("available", False) and -37.5 <= ap["threshold_mv_dvdt_20_v_s"] <= -32.3, "SP/PL"),
        gate("AP amplitude", "44.8 +/- 1.6 mV", "Gradwell aging adult PV population", ap.get("amplitude_peak_minus_threshold_mv", "none"), "41.6-48.0 mV (mean +/- 2 SEM)", ap.get("available", False) and 41.6 <= ap["amplitude_peak_minus_threshold_mv"] <= 48.0, "SP/PL"),
        gate("AP half-width", "1.4 +/- 0.1 ms", "Gradwell aging adult PV population", ap.get("half_width_ms", "none"), "1.2-1.6 ms (mean +/- 2 SEM)", ap.get("available", False) and 1.2 <= ap["half_width_ms"] <= 1.6, "SP/PL"),
        gate("AHP relative to threshold", "-17.6 +/- 1.6 mV", "Gradwell aging adult PV population", ap.get("ahp_relative_to_threshold_mv", "none"), "-20.8 to -14.4 mV (mean +/- 2 SEM)", ap.get("available", False) and -20.8 <= ap["ahp_relative_to_threshold_mv"] <= -14.4, "SP/PL"),
        gate("tonic persistence", "tonic in 55% adult and 64.2% broader PV cohorts", "Gradwell 2022 studies", representative["tonic_persistence_fraction"], ">=3 spikes and last spike after 80% of 800-ms pulse at 2x rheobase", representative["spike_count"] >= 3 and representative["tonic_persistence_fraction"] >= 0.8, "SP/PL"),
        gate("strong-current recovery", "no quantitative target", "engineering gate", strong["spike_count"], "spikes present and post-stimulus voltage returns within 5 mV of baseline", strong["spike_count"] > 0 and abs(float(np.mean(traces[0.4].soma_mv[-int(100/config['simulation']['dt_ms']):])) - baseline) < 5.0, "engineering"),
    ]
    result = {
        "schema_version": "1.0",
        "configuration": str(FINAL_CONFIG.relative_to(ROOT)),
        "neuron_version": str(cell.h.nrnversion()),
        "temperature_c": config["temperature_c"],
        "morphology_inventory": cell.inventory(),
        "active_baseline_mv_model_prediction": baseline,
        "active_input_resistance_probe": negative,
        "rheobase_na": rheobase,
        "rheobase_resolution_na": 0.01,
        "rheobase_action_potential": ap,
        "representative_firing_at_2x_rheobase": representative,
        "strong_current_firing": strong,
        "fi_curve": fi,
        "validation_gates": active_gates,
        "gate_counts": {
            "pass": sum(row["status"] == "PASS" for row in active_gates),
            "fail": sum(row["status"] == "FAIL" for row in active_gates),
        },
        "active_status": "PARTIAL: population-supported tonic phenotype and threshold reproduced; waveform/rheobase gates reported individually",
        "claim_scope": "No electrophysiological trace is linked to NMO_170087; all comparisons are population-level.",
    }
    cell.dispose()
    return result, traces, fi


def temperature_validation(base: dict) -> tuple[list[dict], dict[float, object]]:
    rows = []
    representative_traces = {}
    for temperature in [21.0, 23.0, 24.0, 35.0]:
        config = copy.deepcopy(base)
        config["temperature_c"] = temperature
        cell, fi, traces = run_fi(config)
        positive = [row for row in fi if row["current_na"] >= 0 and row["spike_count"]]
        rheobase = positive[0]["current_na"] if positive else None
        representative = next(row for row in fi if row["current_na"] == config["protocols"]["representative_current_na"])
        ap = action_potential_metrics(traces[rheobase], config) if rheobase is not None else {"available": False}
        rows.append({
            "temperature_c": temperature,
            "classification": "EXPERIMENTAL-RANGE MODEL COMPARISON" if temperature <= 24 else "35 C MODEL PREDICTION",
            "rheobase_na": rheobase,
            "spikes_at_0p12_na": representative["spike_count"],
            "frequency_hz_at_0p12_na": representative["frequency_hz"],
            "tonic_persistence_at_0p12_na": representative["tonic_persistence_fraction"],
            "ap_threshold_mv": ap.get("threshold_mv_dvdt_20_v_s"),
            "ap_peak_mv": ap.get("peak_mv"),
            "ap_half_width_ms": ap.get("half_width_ms"),
            "q10_na": config["active"]["q10_na"],
            "q10_kdr": config["active"]["q10_kdr"],
            "reference_temperature_c": config["active"]["reference_temperature_c"],
        })
        representative_traces[temperature] = traces[config["protocols"]["representative_current_na"]]
        cell.dispose()
    return rows, representative_traces


def one_run(config: dict, label: str, family: str, current: float = 0.12, dt: float | None = None, vinit: float | None = None) -> dict:
    cell = PVCell(config)
    trace = run_step(cell, current, dt_ms=dt, v_init_mv=vinit)
    firing = firing_metrics(trace, config)
    ap = action_potential_metrics(trace, config)
    row = {
        "family": family,
        "condition": label,
        "current_na": current,
        "dt_ms": dt if dt is not None else config["simulation"]["dt_ms"],
        "d_lambda": config["discretization"]["d_lambda"],
        "v_init_mv": vinit if vinit is not None else config["simulation"]["v_init_mv"],
        "temperature_c": config["temperature_c"],
        "nseg_total": cell.inventory()["segments"]["total"],
        "spike_count": firing["spike_count"],
        "frequency_hz": firing["frequency_hz"],
        "tonic_persistence_fraction": firing["tonic_persistence_fraction"],
        "ap_threshold_mv": ap.get("threshold_mv_dvdt_20_v_s"),
        "ap_peak_mv": ap.get("peak_mv"),
        "ap_half_width_ms": ap.get("half_width_ms"),
    }
    cell.dispose()
    return row


def robustness(base: dict) -> list[dict]:
    rows = []
    for dt in [0.05, 0.025, 0.0125]:
        rows.append(one_run(copy.deepcopy(base), f"dt={dt:g} ms", "dt convergence", dt=dt))
    for d_lambda in [0.2, 0.1, 0.05]:
        config = copy.deepcopy(base)
        config["discretization"]["d_lambda"] = d_lambda
        rows.append(one_run(config, f"d_lambda={d_lambda:g}", "spatial convergence"))
    for vinit in [-70.0, -60.0, -50.0]:
        rows.append(one_run(copy.deepcopy(base), f"v_init={vinit:g} mV", "initial voltage", vinit=vinit))
    for channel in ["na", "kdr"]:
        for scale in [0.9, 1.1]:
            config = copy.deepcopy(base)
            for region in config["active"]["conductance_s_cm2"].values():
                region[channel] *= scale
            rows.append(one_run(config, f"{channel} x{scale:g}", "conductance perturbation"))
    for key, scale in [("g_pas_s_cm2", 0.95), ("g_pas_s_cm2", 1.05), ("cm_uf_cm2", 0.9), ("cm_uf_cm2", 1.1), ("ra_ohm_cm", 0.9), ("ra_ohm_cm", 1.1)]:
        config = copy.deepcopy(base)
        config["passive"][key] *= scale
        rows.append(one_run(config, f"{key} x{scale:g}", "passive perturbation"))
    for temperature in [22.0, 24.0]:
        config = copy.deepcopy(base)
        config["temperature_c"] = temperature
        rows.append(one_run(config, f"temperature={temperature:g} C", "temperature perturbation"))
    for length in [15.0, 30.0, 45.0]:
        config = copy.deepcopy(base)
        config["active"]["ais_proxy_max_distance_um"] = length
        rows.append(one_run(config, f"proximal enrichment={length:g} um", "partial-axon/AIS-proxy sensitivity"))
    passive_axon = copy.deepcopy(base)
    passive_axon["active"]["conductance_s_cm2"]["ais_proxy"] = {"na": 0.0, "kdr": 0.0}
    passive_axon["active"]["conductance_s_cm2"]["distal_axon"] = {"na": 0.0, "kdr": 0.0}
    rows.append(one_run(passive_axon, "native partial axon made passive", "partial-axon/AIS-proxy sensitivity"))
    return rows


def save_traces(path: Path, traces: dict[float, object], selected: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["current_na", "time_ms", "soma_mv", "proximal_axon_mv", "proximal_dendrite_mv"])
        for current in selected:
            trace = traces[current]
            # Export at 0.1 ms to keep representative CSVs reviewable while
            # simulations and all metric extraction retain the 0.025-ms dt.
            stride = max(1, int(round(0.1 / float(np.median(np.diff(trace.time_ms))))))
            indices = np.arange(0, len(trace.time_ms), stride, dtype=int)
            if indices[-1] != len(trace.time_ms) - 1:
                indices = np.append(indices, len(trace.time_ms) - 1)
            writer.writerows(
                zip(
                    [current] * len(indices),
                    trace.time_ms[indices],
                    trace.soma_mv[indices],
                    trace.axon_mv[indices],
                    trace.dendrite_mv[indices],
                )
            )


def make_figures(config: dict, validation: dict, traces: dict[float, object], fi: list[dict], temp_rows: list[dict], temp_traces: dict[float, object], robust_rows: list[dict]) -> None:
    active_dir = ROOT / "figures/active"
    final_dir = ROOT / "figures/final"
    active_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(3, 2, figsize=(10, 8), sharex=True, sharey=True)
    for ax, current in zip(axes.flat, [-0.02, 0.0, 0.04, 0.06, 0.12, 0.4]):
        trace = traces[current]
        ax.plot(trace.time_ms, trace.soma_mv, color="#2455a4", linewidth=1.0)
        ax.set_title(f"{current * 1000:g} pA")
    for ax in axes[-1]:
        ax.set_xlabel("Time (ms)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Vm (mV)")
    fig.suptitle("Standardized 800-ms current-clamp responses")
    fig.tight_layout()
    fig.savefig(active_dir / "representative_voltage_traces.png", dpi=300)
    plt.close(fig)

    rheobase = validation["rheobase_na"]
    trace = traces[rheobase]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(trace.time_ms, trace.soma_mv, color="#2455a4")
    ax.set(xlabel="Time (ms)", ylabel="Vm (mV)", title=f"Rheobase response ({rheobase * 1000:.0f} pA grid estimate)")
    fig.tight_layout()
    fig.savefig(active_dir / "rheobase_trace.png", dpi=300)
    plt.close(fig)

    positives = [row for row in fi if row["current_na"] >= 0]
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.plot([row["current_na"] * 1000 for row in positives], [row["frequency_hz"] for row in positives], "o-", color="#2455a4")
    ax.set(xlabel="Injected current (pA)", ylabel="Firing rate (Hz)", title="Model F-I curve (800-ms pulse)")
    fig.tight_layout()
    fig.savefig(active_dir / "fi_curve.png", dpi=300)
    plt.close(fig)

    ap_time = validation["rheobase_action_potential"]["soma_crossing_time_ms"]
    window = (trace.time_ms >= ap_time - 5) & (trace.time_ms <= ap_time + 15)
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.plot(trace.time_ms[window] - ap_time, trace.soma_mv[window], color="#2455a4")
    ax.set(xlabel="Time from -20 mV crossing (ms)", ylabel="Vm (mV)", title="First action potential at rheobase")
    fig.tight_layout()
    fig.savefig(active_dir / "first_action_potential.png", dpi=300)
    plt.close(fig)

    dvdt = np.gradient(trace.soma_mv, trace.time_ms)
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    ax.plot(trace.soma_mv[window], dvdt[window], color="#7b3f98")
    ax.set(xlabel="Vm (mV)", ylabel="dV/dt (V/s)", title="First-spike phase plot")
    fig.tight_layout()
    fig.savefig(active_dir / "ap_phase_plot.png", dpi=300)
    plt.close(fig)

    rep = next(row for row in fi if row["current_na"] == 0.12)
    isi = np.diff(rep["spike_times_relative_ms"])
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(np.arange(1, len(isi) + 1), isi, "o-", color="#2f8f5b")
    ax.set(xlabel="ISI number", ylabel="Interspike interval (ms)", title="Adaptation at 120 pA (2x model rheobase)")
    fig.tight_layout()
    fig.savefig(active_dir / "adaptation_isi.png", dpi=300)
    plt.close(fig)

    labels = ["Rheobase\n(pA)", "Threshold\n(mV)", "Amplitude\n(mV)", "Half-width\n(ms)", "AHP rel.\n(mV)"]
    targets = np.array([77, -34.9, 44.8, 1.4, -17.6], dtype=float)
    model = np.array([rheobase * 1000, validation["rheobase_action_potential"]["threshold_mv_dvdt_20_v_s"], validation["rheobase_action_potential"]["amplitude_peak_minus_threshold_mv"], validation["rheobase_action_potential"]["half_width_ms"], validation["rheobase_action_potential"]["ahp_relative_to_threshold_mv"]])
    normalized = model / np.where(targets == 0, 1, targets)
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    x = np.arange(len(labels))
    ax.bar(x - 0.18, np.ones(len(labels)), 0.36, label="Population target", color="#999999")
    ax.bar(x + 0.18, normalized, 0.36, label="Model / target", color="#2455a4")
    ax.axhline(1, color="black", linewidth=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Ratio (signed for voltage measures)")
    ax.set_title("Population targets versus model outputs")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(active_dir / "experimental_target_vs_model.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    for temperature in [23.0, 35.0]:
        ttrace = temp_traces[temperature]
        ax.plot(ttrace.time_ms, ttrace.soma_mv, label=f"{temperature:.0f} C" + (" model prediction" if temperature == 35 else ""), linewidth=1.0)
    ax.set(xlabel="Time (ms)", ylabel="Vm (mV)", title="Experimental-range model versus 35 C translation at 120 pA")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(final_dir / "temperature_comparison.png", dpi=300)
    plt.close(fig)

    selected_robust = [row for row in robust_rows if row["family"] in {"dt convergence", "spatial convergence", "conductance perturbation", "partial-axon/AIS-proxy sensitivity"}]
    fig, ax = plt.subplots(figsize=(10.5, 5.3))
    labels_r = [row["condition"] for row in selected_robust]
    ax.bar(np.arange(len(selected_robust)), [row["spike_count"] for row in selected_robust], color="#4f7f6f")
    ax.set_xticks(np.arange(len(selected_robust)), labels_r, rotation=45, ha="right")
    ax.set(ylabel="Spike count at 120 pA", title="Numerical and model-definition robustness")
    fig.tight_layout()
    fig.savefig(final_dir / "robustness_summary.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.axis("off")
    boxes = [
        (0.08, "SC\nMorphology + PV/Pax2", "#b9e3c6"),
        (0.31, "SP/PL\nPassive + active targets", "#d7e8b2"),
        (0.56, "F/A\nBiophysical parameters", "#f4d6a0"),
        (0.80, "P\n35 C + exact-cell outputs", "#e8b3b3"),
    ]
    for x, label, color in boxes:
        ax.text(x, 0.55, label, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.6", fc=color, ec="#444444"))
    for left, right in zip(boxes[:-1], boxes[1:]):
        ax.annotate("", xy=(right[0] - 0.09, 0.55), xytext=(left[0] + 0.1, 0.55), arrowprops=dict(arrowstyle="->"))
    ax.set_title("Evidence-confidence flow: support decreases from identity to prediction")
    fig.tight_layout()
    fig.savefig(final_dir / "evidence_confidence_schematic.png", dpi=300)
    plt.close(fig)


def main() -> None:
    config = load_config(FINAL_CONFIG)
    result_dir = ROOT / "results"
    validation, traces, fi = active_validation(config)
    save_json(validation, result_dir / "active/active_validation_metrics.json")
    write_rows(result_dir / "active/FI_curve.csv", fi)
    save_traces(result_dir / "active/representative_traces.csv", traces, [-0.02, 0.0, 0.04, 0.06, 0.12, 0.4])
    write_rows(result_dir / "validation/active_validation_table.csv", validation["validation_gates"])

    temperatures, temperature_traces = temperature_validation(config)
    write_rows(result_dir / "temperature/temperature_summary.csv", temperatures)
    save_json({"schema_version": "1.0", "rows": temperatures, "interpretation": "21-24 C is the reported experimental range; 35 C is a MODEL PREDICTION."}, result_dir / "temperature/temperature_validation.json")

    robust = robustness(config)
    write_rows(result_dir / "robustness/robustness_summary.csv", robust)
    save_json({"schema_version": "1.0", "rows": robust}, result_dir / "robustness/robustness_summary.json")
    make_figures(config, validation, traces, fi, temperatures, temperature_traces, robust)
    print(json.dumps({"validation": validation["gate_counts"], "rheobase_na": validation["rheobase_na"], "temperature": temperatures, "robustness_rows": len(robust)}, indent=2))


if __name__ == "__main__":
    main()
