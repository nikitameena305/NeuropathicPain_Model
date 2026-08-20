"""Fit staged Na/KDR/IAr/Ih candidates for the NMO_260150 model."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from ecr_model import (
    ECRCell,
    analyse_trace,
    ensure_mechanisms,
    neuron_available,
    run_iclamp,
    run_subthreshold_voltage_clamp,
    write_json,
)


TARGETS = {
    "rmp_mV": {"mean": -59.0, "sd": 8.2, "n": 31},
    "rheobase_pA": {"mean": 26.9, "sd": 20.5, "n": 26},
    "ap_threshold_mV_dvdt_10": {"mean": -35.3, "sd": 5.4, "n": 26},
    "first_spike_latency_ms": {"mean": 321.8, "sd": 235.8, "n": 26},
    "ap_base_width_ms_threshold_to_downstroke": {"mean": 1.4, "sd": 0.5, "n": 26},
    "ap_height_mV_peak_minus_threshold": {"mean": 64.8, "sd": 10.2, "n": 26},
    "ahp_mV_trough_minus_threshold": {"mean": -28.42, "sd": 5.2, "n": 26},
    "IAr_model_current_pA": {"mean": 165.7, "sd": 80.3, "n": 10},
    "Ih_model_current_pA": {"mean": -10.9, "sd": 5.0, "n": 11},
}


def stage1_candidates() -> list[dict[str, dict[str, float]]]:
    """Return nine Na/KDR regional-density candidates.

    Args:
        None.

    Returns:
        Active mechanism mappings.

    Example:
        ``candidates = stage1_candidates()``
    """

    candidates = []
    for g_na in (0.08, 0.12, 0.16):
        for g_kdr in (0.12, 0.20, 0.30):
            candidates.append(
                {
                    "B_Na": {"soma": g_na, "dendrite": 0.04*g_na, "ais": 0.0},
                    "B_DR": {"soma": g_kdr, "dendrite": 0.10*g_kdr, "ais": 0.0},
                }
            )
    return candidates


def active_score(metrics: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    """Score a current-clamp batch against broad population constraints.

    Args:
        metrics: Per-current measurement rows.

    Returns:
        Lower-is-better score and selection summary.

    Example:
        ``score, summary = active_score(rows)``
    """

    zero = next(row for row in metrics if row["amplitude_nA"] == 0.0)
    spiking = [row for row in metrics if row["amplitude_nA"] > 0.0 and row["spike_count"] > 0]
    if not spiking:
        return 1e6, {"reason": "no evoked action potential"}
    rheobase_row = min(spiking, key=lambda row: row["amplitude_nA"])
    values = {
        "rmp_mV": zero["rmp_mV"],
        "rheobase_pA": 1000.0*rheobase_row["amplitude_nA"],
        "ap_threshold_mV_dvdt_10": rheobase_row["ap_threshold_mV_dvdt_10"],
        "first_spike_latency_ms": rheobase_row["first_spike_latency_ms"],
        "ap_base_width_ms_threshold_to_downstroke": rheobase_row["ap_base_width_ms_threshold_to_downstroke"],
        "ap_height_mV_peak_minus_threshold": rheobase_row["ap_height_mV_peak_minus_threshold"],
        "ahp_mV_trough_minus_threshold": rheobase_row["ahp_mV_trough_minus_threshold"],
    }
    score = 0.0
    z_scores: dict[str, float | None] = {}
    for name, value in values.items():
        if value is None:
            score += 25.0
            z_scores[name] = None
            continue
        target = TARGETS[name]
        z_value = (float(value) - target["mean"])/target["sd"]
        z_scores[name] = z_value
        score += z_value*z_value
    phenotype_penalty = {"delayed": 0.0, "tonic": 0.2, "transient": 0.3, "single": 0.5}.get(
        rheobase_row["firing_class"],
        1.0,
    )
    score += phenotype_penalty
    if zero["spontaneous_spike_count_before_step"] or zero["spike_count"]:
        score += 100.0
    if any(row["depolarization_block"] for row in metrics):
        score += 100.0
    return score, {
        "rheobase_test_resolution_pA": 1000.0*rheobase_row["amplitude_nA"],
        "rheobase_row": rheobase_row,
        "z_scores": z_scores,
        "phenotype_penalty": phenotype_penalty,
    }


def evaluate_configuration(
    h: Any,
    *,
    swc_path: Path,
    passive: dict[str, float],
    active: dict[str, dict[str, float]],
    current_steps_nA: list[float],
    temperature_C: float,
) -> tuple[dict[str, Any], dict[float, dict[str, list[float]]]]:
    """Evaluate one active configuration at fixed current steps.

    Args:
        h: NEURON hoc interface.
        swc_path: Standardized SWC path.
        passive: Passive parameters.
        active: Active mechanism densities.
        current_steps_nA: Current steps to run.
        temperature_C: Simulation temperature.

    Returns:
        Evaluation summary and raw traces keyed by current.

    Example:
        ``summary, traces = evaluate_configuration(h, swc_path=swc, ...)``
    """

    h.celsius = temperature_C
    cell = ECRCell(h, morphology_path=swc_path, passive=passive, active=active)
    rows: list[dict[str, Any]] = []
    traces: dict[float, dict[str, list[float]]] = {}
    for amplitude in current_steps_nA:
        trace = run_iclamp(
            h,
            cell=cell,
            amplitude_nA=amplitude,
            delay_ms=300.0,
            duration_ms=1000.0,
            tstop_ms=1500.0,
            v_init_mV=float(passive["e_pas_mV"]),
            record_currents=True,
        )
        traces[amplitude] = trace
        rows.append(analyse_trace(trace, amplitude_nA=amplitude, delay_ms=300.0, duration_ms=1000.0))
    score, selection = active_score(rows)
    summary = {
        "active": active,
        "passive": passive,
        "temperature_C": temperature_C,
        "score_z2_plus_gates": score,
        "selection": selection,
        "per_current": rows,
        "inventory": cell.inventory(),
    }
    cell.delete()
    return summary, traces


def channel_diagnostics(
    h: Any,
    *,
    swc_path: Path,
    passive: dict[str, float],
    active: dict[str, dict[str, float]],
    temperature_C: float,
) -> tuple[dict[str, float], dict[str, list[float]]]:
    """Measure isolated model IAr and Ih with the paper's voltage protocol.

    Args:
        h: NEURON hoc interface.
        swc_path: Standardized SWC path.
        passive: Passive parameters.
        active: Active mechanism densities.
        temperature_C: Simulation temperature.

    Returns:
        Scalar channel metrics and protocol traces.

    Example:
        ``metrics, trace = channel_diagnostics(h, swc_path=swc, ...)``
    """

    h.celsius = temperature_C
    cell = ECRCell(h, morphology_path=swc_path, passive=passive, active=active)
    trace = run_subthreshold_voltage_clamp(h, cell=cell)
    ia_values = [
        value for time, value in zip(trace["time_ms"], trace["IAr_model_current_pA"]) if 1200.0 <= time <= 1400.0
    ]
    ih_values = [
        value for time, value in zip(trace["time_ms"], trace["Ih_model_current_pA"]) if 1000.0 <= time <= 1200.0
    ]
    metrics = {
        "IAr_model_current_pA": max(ia_values) if ia_values else 0.0,
        "Ih_model_current_pA": sum(ih_values)/len(ih_values) if ih_values else 0.0,
    }
    cell.delete()
    return metrics, trace


def write_trace_csv(
    *,
    output_path: Path,
    traces: dict[float, dict[str, list[float]]],
) -> None:
    """Write representative current-clamp traces in long-form CSV.

    Args:
        output_path: Destination CSV path.
        traces: Trace mappings keyed by current amplitude.

    Returns:
        None.

    Example:
        ``write_trace_csv(output_path=path, traces=traces)``
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["current_pA", "time_ms", "voltage_mV"])
        for amplitude, trace in sorted(traces.items()):
            for time, voltage in zip(trace["time_ms"][::4], trace["voltage_mV"][::4]):
                writer.writerow([f"{1000.0*amplitude:.3f}", f"{time:.6f}", f"{voltage:.6f}"])


def write_firing_figure(
    *,
    output_path: Path,
    traces: dict[float, dict[str, list[float]]],
    rheobase_nA: float,
) -> None:
    """Render four original current-clamp traces using Figure 9 logic.

    Args:
        output_path: Destination PNG.
        traces: Exact 5 pA-step traces.
        rheobase_nA: Tested rheobase.

    Returns:
        None.

    Example:
        ``write_firing_figure(output_path=path, traces=traces, rheobase_nA=0.015)``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    requested = (0.0, rheobase_nA, min(0.025, max(traces)), max(traces))
    selected = []
    for amplitude in requested:
        closest = min(traces, key=lambda value: abs(value - amplitude))
        if closest not in selected:
            selected.append(closest)
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), sharex=True, sharey=True, constrained_layout=True)
    colours = ("#4b5563", "#7c3aed", "#2563eb", "#dc2626")
    for axis, amplitude, colour in zip(axes.flat, selected, colours):
        trace = traces[amplitude]
        axis.plot(trace["time_ms"], trace["voltage_mV"], color=colour, linewidth=0.9)
        axis.axvspan(300, 1300, color=colour, alpha=0.08)
        axis.set_title(f"{1000.0*amplitude:.0f} pA")
        axis.set(xlabel="Time (ms)", ylabel="Soma Vm (mV)")
    figure.suptitle("NMO_260150 active responses - operational room-temperature reference")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, facecolor="white")
    plt.close(figure)


def write_metrics_figure(
    *,
    output_path: Path,
    metrics: list[dict[str, Any]],
    traces: dict[float, dict[str, list[float]]],
    rheobase_nA: float,
) -> None:
    """Render F-I, latency, first-AP, and target-deviation panels.

    Args:
        output_path: Destination PNG.
        metrics: Exact current-scan metrics.
        traces: Exact current-scan traces.
        rheobase_nA: Tested rheobase.

    Returns:
        None.

    Example:
        ``write_metrics_figure(output_path=path, metrics=rows, traces=traces, rheobase_nA=0.015)``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
    currents = [1000.0*row["amplitude_nA"] for row in metrics]
    axes[0, 0].plot(currents, [row["spike_count"] for row in metrics], "o-", color="#2563eb")
    axes[0, 0].set(title="F-I / spike-count curve", xlabel="Current (pA)", ylabel="Spikes in 1 s")
    latency_rows = [row for row in metrics if row["first_spike_latency_ms"] is not None]
    axes[0, 1].plot(
        [1000.0*row["amplitude_nA"] for row in latency_rows],
        [row["first_spike_latency_ms"] for row in latency_rows],
        "o-",
        color="#7c3aed",
    )
    axes[0, 1].axhspan(
        TARGETS["first_spike_latency_ms"]["mean"] - TARGETS["first_spike_latency_ms"]["sd"],
        TARGETS["first_spike_latency_ms"]["mean"] + TARGETS["first_spike_latency_ms"]["sd"],
        color="#ede9fe",
        alpha=0.8,
    )
    axes[0, 1].set(title="First-spike latency", xlabel="Current (pA)", ylabel="Latency (ms)")
    rheobase_trace = traces[rheobase_nA]
    rheobase_row = next(row for row in metrics if row["amplitude_nA"] == rheobase_nA)
    first_time = rheobase_row["threshold_time_ms"] or 300.0
    indices = [
        index for index, time in enumerate(rheobase_trace["time_ms"]) if first_time - 5.0 <= time <= first_time + 15.0
    ]
    axes[1, 0].plot(
        [rheobase_trace["time_ms"][index] - first_time for index in indices],
        [rheobase_trace["voltage_mV"][index] for index in indices],
        color="#dc2626",
    )
    axes[1, 0].axhline(TARGETS["ap_threshold_mV_dvdt_10"]["mean"], color="#111827", linestyle="--", linewidth=0.8)
    axes[1, 0].set(title="First AP at tested rheobase", xlabel="Time from threshold (ms)", ylabel="Vm (mV)")
    metric_names = (
        "rheobase_pA",
        "ap_threshold_mV_dvdt_10",
        "first_spike_latency_ms",
        "ap_base_width_ms_threshold_to_downstroke",
        "ap_height_mV_peak_minus_threshold",
        "ahp_mV_trough_minus_threshold",
    )
    values = {
        "rheobase_pA": 1000.0*rheobase_nA,
        **{name: rheobase_row[name] for name in metric_names if name != "rheobase_pA"},
    }
    z_scores = [(values[name] - TARGETS[name]["mean"])/TARGETS[name]["sd"] for name in metric_names]
    labels = ("Rheo", "Threshold", "Latency", "Base width", "Height", "AHP")
    axes[1, 1].bar(labels, z_scores, color="#0f766e")
    axes[1, 1].axhspan(-1, 1, color="#dcfce7", alpha=0.7)
    axes[1, 1].axhline(0, color="#111827", linewidth=0.8)
    axes[1, 1].tick_params(axis="x", rotation=25)
    axes[1, 1].set(title="Rheobase-metric deviation", ylabel="Z score")
    figure.suptitle("NMO_260150 active validation against NPFF-targeted population")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, facecolor="white")
    plt.close(figure)


def build_parser() -> argparse.ArgumentParser:
    """Build the active-fit command-line parser.

    Args:
        None.

    Returns:
        Configured parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Run a staged, <500-simulation active fit.")
    parser.add_argument("--dry-run", action="store_true", help="Print the staged search without importing NEURON.")
    return parser


def main() -> int:
    """Run the staged active fit and write reference-condition artifacts.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python fit_active.py``
    """

    args = build_parser().parse_args()
    cell_dir = Path(__file__).resolve().parent.parent
    coarse_steps = [0.0, 0.015, 0.025, 0.060, 0.100]
    plan = {
        "MODEL_1": "pas + B_Na + B_DR; 9 configurations x 5 current steps",
        "MODEL_2": "MODEL_1 + soma-restricted B_A; 4 configurations x 5 steps + 4 voltage protocols",
        "MODEL_3": "MODEL_2 + Ih_Kole; 9 passive/HCN combinations x 5 steps + 9 voltage protocols",
        "final_exact_scan": "0 to 100 pA in 5 pA steps",
        "maximum_scripted_simulations": 150,
        "temperature_C": 23.0,
        "temperature_label": "operational room-temperature proxy; not a reported chamber temperature",
    }
    print(json.dumps(plan, indent=2))
    if args.dry_run or not neuron_available():
        if not neuron_available():
            print("NEURON is unavailable; completed dry-run only.")
        return 0

    import neuron
    from neuron import h

    h.load_file("stdrun.hoc")
    h.dt = 0.025
    h.steps_per_ms = 40.0
    h.cvode_active(0)
    mechanism_library = ensure_mechanisms(h, mechanism_dir=cell_dir / "mechanisms")
    passive_payload = json.loads((cell_dir / "parameters" / "passive_final.json").read_text(encoding="utf-8"))
    passive_base = dict(passive_payload["passive"])
    passive_base["e_pas_mV"] = -61.0
    swc_path = cell_dir / "morphology" / "NMO_260150_100521A-S14_set5_cell11_standardized.CNG.swc"
    simulation_count = 0

    stage1: list[dict[str, Any]] = []
    for active in stage1_candidates():
        summary, _ = evaluate_configuration(
            h,
            swc_path=swc_path,
            passive=passive_base,
            active=active,
            current_steps_nA=coarse_steps,
            temperature_C=23.0,
        )
        stage1.append(summary)
        simulation_count += len(coarse_steps)
    selected_stage1 = min(stage1, key=lambda row: row["score_z2_plus_gates"])

    stage2: list[dict[str, Any]] = []
    for g_a in (0.0025, 0.005, 0.008, 0.012):
        active = json.loads(json.dumps(selected_stage1["active"]))
        active["B_A"] = {"soma": g_a, "dendrite": 0.0, "ais": 0.0}
        summary, _ = evaluate_configuration(
            h,
            swc_path=swc_path,
            passive=passive_base,
            active=active,
            current_steps_nA=coarse_steps,
            temperature_C=23.0,
        )
        diagnostics, _ = channel_diagnostics(
            h,
            swc_path=swc_path,
            passive=passive_base,
            active=active,
            temperature_C=23.0,
        )
        summary["channel_diagnostics"] = diagnostics
        summary["IAr_target_z"] = (
            (diagnostics["IAr_model_current_pA"] - TARGETS["IAr_model_current_pA"]["mean"])
            / TARGETS["IAr_model_current_pA"]["sd"]
        )
        stage2.append(summary)
        simulation_count += len(coarse_steps) + 1
    selected_stage2 = min(stage2, key=lambda row: abs(row["IAr_target_z"]))

    stage3: list[dict[str, Any]] = []
    for g_h in (3e-5, 5.7e-5, 8e-5):
        for e_pas in (-59.0, -61.0, -63.0):
            passive = dict(passive_base)
            passive["e_pas_mV"] = e_pas
            active = json.loads(json.dumps(selected_stage2["active"]))
            active["Ih_Kole"] = {"soma": g_h, "dendrite": g_h, "ais": 0.0}
            summary, _ = evaluate_configuration(
                h,
                swc_path=swc_path,
                passive=passive,
                active=active,
                current_steps_nA=coarse_steps,
                temperature_C=23.0,
            )
            diagnostics, _ = channel_diagnostics(
                h,
                swc_path=swc_path,
                passive=passive,
                active=active,
                temperature_C=23.0,
            )
            ih_z = (
                (diagnostics["Ih_model_current_pA"] - TARGETS["Ih_model_current_pA"]["mean"])
                / TARGETS["Ih_model_current_pA"]["sd"]
            )
            summary["channel_diagnostics"] = diagnostics
            summary["Ih_target_z"] = ih_z
            summary["combined_selection_score"] = summary["score_z2_plus_gates"] + ih_z*ih_z
            stage3.append(summary)
            simulation_count += len(coarse_steps) + 1
    selected = min(stage3, key=lambda row: row["combined_selection_score"])

    exact_steps = [value/1000.0 for value in range(0, 101, 5)]
    final_reference, exact_traces = evaluate_configuration(
        h,
        swc_path=swc_path,
        passive=selected["passive"],
        active=selected["active"],
        current_steps_nA=exact_steps,
        temperature_C=23.0,
    )
    simulation_count += len(exact_steps)
    exact_spiking = [row for row in final_reference["per_current"] if row["amplitude_nA"] > 0 and row["spike_count"]]
    rheobase_nA = min(row["amplitude_nA"] for row in exact_spiking)
    channel_metrics, channel_trace = channel_diagnostics(
        h,
        swc_path=swc_path,
        passive=selected["passive"],
        active=selected["active"],
        temperature_C=23.0,
    )
    simulation_count += 1
    output = {
        "identity": {
            "known": "NPFF-positive excitatory vertical interneuron",
            "unconfirmed": "CR/calretinin identity",
            "mapping": "Medlock eCR-like computational analogue",
        },
        "evidence_category": "NPFFCre-targeted / GRPRFlp-excluded population-level electrophysiology",
        "targets": TARGETS,
        "search_plan": plan,
        "scripted_simulation_count": simulation_count,
        "mechanism_library_runtime_path": str(mechanism_library),
        "stage1_all": sorted(stage1, key=lambda row: row["score_z2_plus_gates"]),
        "stage1_selected": selected_stage1,
        "stage2_all": sorted(stage2, key=lambda row: abs(row["IAr_target_z"])),
        "stage2_selected": selected_stage2,
        "stage3_all": sorted(stage3, key=lambda row: row["combined_selection_score"]),
        "selected_reference_model": final_reference,
        "exact_rheobase_pA_5pA_resolution": 1000.0*rheobase_nA,
        "channel_diagnostics": channel_metrics,
        "interpretation": {
            "IAr": "B_A is a model representation of rapid IA; exact NMO_260150 expression is not known",
            "Ih": "Ih_Kole is a published HCN model candidate; exact NMO_260150 expression is not known",
            "ICaT": "not included because ICa,T was detected in 0/16 tested cells",
            "firing": "tonic/single-at-rheobase outcome retained because forced long delay was not supported by the tested B_A kinetics",
        },
    }
    parameter_payload = {
        "model": "NMO_260150 active native soma+dendrite reference-condition model",
        "status": "reference-condition fitted; 35 C translation pending",
        "temperature_C": 23.0,
        "temperature_evidence": "operational room-temperature proxy, not a reported chamber value",
        "passive": selected["passive"],
        "active": selected["active"],
        "ais": {"enabled": False, "status": "NO RECONSTRUCTED AXON; no model-defined AIS required"},
        "diameter_scale": 1.0,
        "diameter_status": "model-defined standardized radius profile; NeuroMorpho says No Diameter",
        "dt_ms": 0.025,
        "d_lambda": 0.1,
        "frequency_Hz": 100.0,
        "protocol": {"delay_ms": 300.0, "duration_ms": 1000.0, "increment_pA": 5.0},
        "exact_rheobase_pA": 1000.0*rheobase_nA,
        "channel_diagnostics": channel_metrics,
        "evidence_category": "NPFFCre-targeted / GRPRFlp-excluded population",
    }
    write_json(cell_dir / "parameters" / "active_final_23C.json", parameter_payload)
    write_json(cell_dir / "results" / "active_fit_summary.json", output)
    representative = {
        amplitude: trace
        for amplitude, trace in exact_traces.items()
        if amplitude in {0.0, rheobase_nA, 0.025, 0.1}
    }
    write_trace_csv(output_path=cell_dir / "results" / "reference_representative_traces.csv", traces=representative)
    compact_channel_trace = {name: values[::4] for name, values in channel_trace.items()}
    write_json(cell_dir / "results" / "reference_channel_protocol.json", {"metrics": channel_metrics, "trace": compact_channel_trace, "saved_interval_ms": 0.1})
    write_firing_figure(
        output_path=cell_dir / "figures" / "firing_traces.png",
        traces=exact_traces,
        rheobase_nA=rheobase_nA,
    )
    write_metrics_figure(
        output_path=cell_dir / "figures" / "active_metrics.png",
        metrics=final_reference["per_current"],
        traces=exact_traces,
        rheobase_nA=rheobase_nA,
    )
    print(json.dumps({"scripted_simulations": simulation_count, "rheobase_pA": 1000.0*rheobase_nA, "channels": channel_metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
