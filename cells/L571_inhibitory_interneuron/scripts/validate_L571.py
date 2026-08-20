#!/usr/bin/env python3
"""Validate final L571-LCN candidates at 23 C and 35 C and generate outputs."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from l571_model import (
    ROOT,
    L571Cell,
    Trace,
    action_potential_metrics,
    firing_metrics,
    load_config,
    passive_metrics,
    run_step,
    save_json,
)


def parse_args() -> argparse.Namespace:
    """Parse validation options.

    Returns:
        Parsed command-line namespace.

    Example:
        ``args = parse_args()``
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--temperature",
        choices=("23", "35", "all"),
        default="all",
        help="Candidate temperature(s) to validate.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a reduced F-I set and skip sensitivity/convergence diagnostics.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned workflow without importing NEURON.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate comparison/report from existing 23C and 35C metrics.",
    )
    return parser.parse_args()


def representative_trace(*, traces: dict[float, Trace], current_na: float) -> Trace:
    """Select a trace keyed by a floating-point current value.

    Args:
        traces: Current-to-trace mapping.
        current_na: Requested current.

    Returns:
        Closest available trace.

    Example:
        ``trace = representative_trace(traces=traces, current_na=0.1)``
    """

    key = min(traces, key=lambda candidate: abs(candidate - current_na))
    return traces[key]


def zero_current_rmp(*, trace: Trace) -> float:
    """Measure steady voltage over the final 100 ms of a zero-current trace.

    Args:
        trace: Zero-current recording.

    Returns:
        Mean somatic voltage in millivolts.

    Example:
        ``rmp = zero_current_rmp(trace=trace)``
    """

    mask = trace.time_ms >= trace.time_ms[-1] - 100.0
    return float(np.mean(trace.soma_mv[mask]))


def pathology_metrics(*, traces: dict[float, Trace], config: dict[str, Any]) -> dict[str, Any]:
    """Classify spontaneous firing, gap/burst signatures, block, and plateaus.

    Args:
        traces: F-I current-to-trace mapping.
        config: Model configuration.

    Returns:
        Conservative rule-based pathology flags.

    Example:
        ``flags = pathology_metrics(traces=traces, config=config)``
    """

    zero = representative_trace(traces=traces, current_na=0.0)
    strong = representative_trace(
        traces=traces,
        current_na=config["protocols"]["strong_current_na"],
    )
    zero_firing = firing_metrics(trace=zero, config=config)
    strong_firing = firing_metrics(trace=strong, config=config)
    intervals = np.diff(np.asarray(strong_firing["spike_times_relative_ms"], dtype=float))
    gap = bool(len(intervals) >= 3 and intervals[0] > 1.5 * np.median(intervals[1:]))
    burst = bool(
        len(intervals) >= 3
        and np.min(intervals) < 10.0
        and np.max(intervals) > 3.0 * max(np.min(intervals), 1e-9)
    )
    delay = config["simulation"]["stim_delay_ms"]
    duration = config["simulation"]["stim_duration_ms"]
    post_mask = strong.time_ms >= delay + duration + 100.0
    pre_mask = (strong.time_ms >= delay - 100.0) & (strong.time_ms < delay)
    post_delta = float(np.mean(strong.soma_mv[post_mask]) - np.mean(strong.soma_mv[pre_mask]))
    block = bool(
        strong_firing["spike_count"] > 0
        and strong_firing["tonic_persistence_fraction"] < 0.5
    )
    return {
        "spontaneous_firing": zero_firing["spike_count"] > 0,
        "spontaneous_rate_hz_during_500_ms_window": zero_firing["firing_rate_hz"],
        "gap_signature_at_strong_current": gap,
        "burst_signature_at_strong_current": burst,
        "depolarization_block_at_strong_current": block,
        "abnormal_post_stimulus_plateau": abs(post_delta) > 10.0,
        "post_stimulus_recovery_delta_mv": post_delta,
    }


def status_table(*, metrics: dict[str, Any], temperature_c: float) -> list[dict[str, Any]]:
    """Classify results against evidence without inventing missing targets.

    Args:
        metrics: Validation metric mapping.
        temperature_c: Simulation temperature.

    Returns:
        Feature/source/result/status/confidence rows.

    Example:
        ``rows = status_table(metrics=metrics, temperature_c=23)``
    """

    direct = temperature_c == 23.0
    active = metrics["active_passive"]
    ap = metrics["action_potential"]
    representative = metrics["representative_firing"]
    pathology = metrics["pathology"]
    rin_status = "PASS" if direct and 800 <= active["rin_mohm"] <= 1000 else "PLAUSIBLE"
    rmp_status = "PASS" if direct and -71.5 <= metrics["rmp_mv"] <= -66.7 else "PLAUSIBLE"
    tonic_status = "PASS" if direct and representative["spike_count"] >= 3 and representative["tonic_persistence_fraction"] >= 0.75 else "PLAUSIBLE"
    if representative["spike_count"] < 3 or representative["tonic_persistence_fraction"] < 0.75:
        tonic_status = "FAIL"
    rows = [
        {
            "feature": "RMP",
            "target_source": "Luz 2014 tonic rat LCN population: -69.1 ± 1.2 mV",
            "result": metrics["rmp_mv"],
            "status": rmp_status,
            "confidence": "B population-level" if direct else "D translated/no 35 C target",
        },
        {
            "feature": "Rin",
            "target_source": "Szücs 2013 rat LCN population: 0.9 ± 0.1 GΩ",
            "result": active["rin_mohm"],
            "status": rin_status,
            "confidence": "B population-level" if direct else "D translated/no 35 C target",
        },
        {
            "feature": "Membrane tau",
            "target_source": "No exact L571 or LCN target in audited sources",
            "result": active["tau_ms_monoexponential"],
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "Rheobase",
            "target_source": "No exact L571 target",
            "result": metrics["rheobase_na"],
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "AP threshold",
            "target_source": "No exact L571 waveform target",
            "result": ap.get("threshold_mv_dvdt_20_v_s"),
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "AP peak",
            "target_source": "No exact L571 waveform target",
            "result": ap.get("peak_mv"),
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "AP half-width",
            "target_source": "No exact L571 waveform target",
            "result": ap.get("half_width_ms"),
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "AHP",
            "target_source": "No exact L571 waveform target",
            "result": ap.get("ahp_min_mv"),
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "D unknown",
        },
        {
            "feature": "Tonic persistence",
            "target_source": "Luz 2014 rat LCN population; regular discharge during 500 ms pulse",
            "result": representative["tonic_persistence_fraction"],
            "status": tonic_status,
            "confidence": "B population-level" if direct else "D translated plausibility",
        },
        {
            "feature": "Spontaneous firing",
            "target_source": "Luz 2014: 40/85 LCNs rhythmic; exact L571 class unknown",
            "result": pathology["spontaneous_firing"],
            "status": "PLAUSIBLE",
            "confidence": "B population-level; D individual unknown",
        },
        {
            "feature": "AIS-to-soma timing",
            "target_source": "No experiment; reconstructed proximal axon is an AIS proxy",
            "result": ap.get("ais_to_soma_crossing_delay_ms"),
            "status": "NO EXPERIMENTAL TARGET",
            "confidence": "C model-derived",
        },
    ]
    return rows


def mechanism_kinetics(*, cell: L571Cell) -> dict[str, Any]:
    """Read mechanism time constants at -40 mV after temperature initialization.

    Args:
        cell: Active model instance.

    Returns:
        Sodium and potassium kinetic values and temperature parameters.

    Example:
        ``audit = mechanism_kinetics(cell=cell)``
    """

    h = cell.h
    h.celsius = cell.config["temperature_c"]
    h.finitialize(-40.0)
    segment = cell.soma[0](0.5)
    return {
        "test_voltage_mv": -40.0,
        "celsius": float(h.celsius),
        "na": {
            "tau_m_ms": float(segment.l571_na.tau_m),
            "tau_h_ms": float(segment.l571_na.tau_h),
            "tadj": float(segment.l571_na.tadj),
            "q10": float(segment.l571_na.q10),
            "tref_c": float(segment.l571_na.tref),
        },
        "kdr": {
            "tau_n_ms": float(segment.l571_kdr.tau_n),
            "tau_h_ms": float(segment.l571_kdr.tau_h),
            "tadj": float(segment.l571_kdr.tadj),
            "q10": float(segment.l571_kdr.q10),
            "tref_c": float(segment.l571_kdr.tref),
        },
        "table_statements": "none in adapted mechanisms; rates recompute from h.celsius at initialization and every state update",
    }


def robustness_tests(*, cell: L571Cell, config: dict[str, Any]) -> dict[str, Any]:
    """Run conductance, timestep, and initial-voltage robustness checks.

    Args:
        cell: Baseline active cell.
        config: Model configuration.

    Returns:
        Perturbation results.

    Example:
        ``results = robustness_tests(cell=cell, config=config)``
    """

    current = config["protocols"]["representative_current_na"]
    stored = []
    for section in cell.sections:
        for segment in section:
            stored.append((segment, float(segment.l571_na.gnabar), float(segment.l571_kdr.gkbar)))
    conductance_results: list[dict[str, Any]] = []
    for family in ("na", "kdr"):
        for percent in (-10, -5, 0, 5, 10):
            factor = 1.0 + percent / 100.0
            for segment, na_value, k_value in stored:
                segment.l571_na.gnabar = na_value * factor if family == "na" else na_value
                segment.l571_kdr.gkbar = k_value * factor if family == "kdr" else k_value
            trace = run_step(cell, current_na=current)
            firing = firing_metrics(trace=trace, config=config)
            ap = action_potential_metrics(trace=trace, config=config)
            conductance_results.append(
                {
                    "family": family,
                    "percent": percent,
                    "spike_count": firing["spike_count"],
                    "firing_rate_hz": firing["firing_rate_hz"],
                    "tonic_persistence_fraction": firing["tonic_persistence_fraction"],
                    "ap_peak_mv": ap.get("peak_mv"),
                    "ap_half_width_ms": ap.get("half_width_ms"),
                }
            )
    for segment, na_value, k_value in stored:
        segment.l571_na.gnabar = na_value
        segment.l571_kdr.gkbar = k_value

    dt_results = []
    for dt_ms in (0.05, 0.025, 0.0125):
        trace = run_step(cell, current_na=current, dt_ms=dt_ms)
        firing = firing_metrics(trace=trace, config=config)
        ap = action_potential_metrics(trace=trace, config=config)
        dt_results.append(
            {"dt_ms": dt_ms, "spike_count": firing["spike_count"], "ap_peak_mv": ap.get("peak_mv"), "ap_half_width_ms": ap.get("half_width_ms")}
        )

    voltage_results = []
    for voltage in (-80.0, config["simulation"]["v_init_mv"], -60.0):
        trace = run_step(cell, current_na=current, v_init_mv=voltage)
        firing = firing_metrics(trace=trace, config=config)
        voltage_results.append(
            {"v_init_mv": voltage, "spike_count": firing["spike_count"], "tonic_persistence_fraction": firing["tonic_persistence_fraction"]}
        )
    return {
        "conductance": conductance_results,
        "dt": dt_results,
        "initial_voltage": voltage_results,
    }


def nseg_convergence(*, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare passive and active metrics across coarser/baseline/finer nseg.

    Args:
        config: Baseline model configuration.

    Returns:
        Convergence rows.

    Example:
        ``rows = nseg_convergence(config=config)``
    """

    rows = []
    baseline_scale = float(config["discretization"]["nseg_scale"])
    for relative_factor in (0.5, 1.0, 2.0):
        scale = baseline_scale * relative_factor
        candidate = copy.deepcopy(config)
        candidate["discretization"]["nseg_scale"] = scale
        cell = L571Cell(config=candidate)
        rin_trace = run_step(cell, current_na=candidate["protocols"]["rin_current_na"])
        ap_trace = run_step(cell, current_na=candidate["protocols"]["representative_current_na"])
        passive = passive_metrics(trace=rin_trace, config=candidate)
        ap = action_potential_metrics(trace=ap_trace, config=candidate)
        rows.append(
            {
                "relative_factor": relative_factor,
                "nseg_scale": scale,
                "nseg_total": cell.summary()["nseg_total"],
                "rin_mohm": passive["rin_mohm"],
                "ap_peak_mv": ap.get("peak_mv"),
                "ap_half_width_ms": ap.get("half_width_ms"),
            }
        )
        cell.dispose()
    return rows


def save_trace_archive(*, traces: dict[str, Trace], path: Path) -> None:
    """Save selected traces as a compressed NumPy archive.

    Args:
        traces: Named traces.
        path: NPZ output path.

    Returns:
        None.

    Example:
        ``save_trace_archive(traces={'ap': trace}, path=Path('traces.npz'))``
    """

    arrays: dict[str, np.ndarray] = {}
    for name, trace in traces.items():
        arrays[f"{name}_time_ms"] = trace.time_ms
        arrays[f"{name}_soma_mv"] = trace.soma_mv
        arrays[f"{name}_ais_mv"] = trace.ais_mv
        arrays[f"{name}_dendrite_mv"] = trace.dendrite_mv
        arrays[f"{name}_current_na"] = np.asarray([trace.current_na])
    np.savez_compressed(path, **arrays)


def write_fi_csv(*, rows: list[dict[str, Any]], path: Path) -> None:
    """Write machine-readable F-I metrics to CSV.

    Args:
        rows: Firing metric rows.
        path: CSV output path.

    Returns:
        None.

    Example:
        ``write_fi_csv(rows=fi_rows, path=Path('fi.csv'))``
    """

    keys = [key for key in rows[0] if key != "spike_times_relative_ms"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in keys})


def plot_outputs(
    *,
    label: str,
    config: dict[str, Any],
    traces: dict[float, Trace],
    passive_trace: Trace,
    fi_rows: list[dict[str, Any]],
    robustness: dict[str, Any] | None,
) -> None:
    """Generate requested per-temperature validation figures.

    Args:
        label: Temperature directory label.
        config: Model configuration.
        traces: F-I recordings.
        passive_trace: Passive-only hyperpolarizing trace.
        fi_rows: F-I metric rows.
        robustness: Optional robustness output.

    Returns:
        None.

    Example:
        ``plot_outputs(label='23C', config=config, traces=traces, passive_trace=trace, fi_rows=rows, robustness=None)``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = ROOT / "figures" / label
    out.mkdir(parents=True, exist_ok=True)
    representative = representative_trace(
        traces=traces,
        current_na=config["protocols"]["representative_current_na"],
    )
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.plot(passive_trace.time_ms, passive_trace.soma_mv, color="#1f77b4")
    axis.set(xlabel="Time (ms)", ylabel="Soma Vm (mV)", title=f"L571 passive response at {label}")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(out / "passive_response.png", dpi=200)
    plt.close(figure)

    delay = config["simulation"]["stim_delay_ms"]
    mask = (representative.time_ms >= delay - 10) & (representative.time_ms <= delay + 100)
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.plot(representative.time_ms[mask] - delay, representative.soma_mv[mask], color="#1f77b4")
    axis.set(xlabel="Time from stimulus (ms)", ylabel="Soma Vm (mV)", title=f"L571 action potentials at {label}")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(out / "action_potential.png", dpi=200)
    plt.close(figure)

    first_spike = firing_metrics(trace=representative, config=config)["first_spike_latency_ms"]
    center = delay + (first_spike if first_spike is not None else 50.0)
    mask = (representative.time_ms >= center - 4) & (representative.time_ms <= center + 6)
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.plot(representative.time_ms[mask] - center, representative.ais_mv[mask], label="AIS proxy (~20 µm)", color="#d62728")
    axis.plot(representative.time_ms[mask] - center, representative.soma_mv[mask], label="soma", color="#1f77b4")
    axis.plot(representative.time_ms[mask] - center, representative.dendrite_mv[mask], label="proximal dendrite", color="#2ca02c")
    axis.set(xlabel="Time around soma crossing (ms)", ylabel="Vm (mV)", title=f"AP initiation timing at {label}")
    axis.legend()
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(out / "ais_vs_soma.png", dpi=200)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 6))
    selected = sorted(set((0.0, 0.02, 0.04, config["protocols"]["representative_current_na"], config["protocols"]["strong_current_na"])))
    offset = 0.0
    for current in selected:
        trace = representative_trace(traces=traces, current_na=current)
        axis.plot(trace.time_ms, trace.soma_mv + offset, label=f"{trace.current_na:g} nA")
        offset += 35.0
    axis.set(xlabel="Time (ms)", ylabel="Soma Vm + offset (mV)", title=f"L571 current-step family at {label}")
    axis.legend(ncol=2)
    axis.grid(alpha=0.15)
    figure.tight_layout()
    figure.savefig(out / "current_step_traces.png", dpi=200)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot([row["current_na"] for row in fi_rows], [row["firing_rate_hz"] for row in fi_rows], marker="o")
    axis.set(xlabel="Injected current (nA)", ylabel="Firing rate (Hz)", title=f"L571 F-I curve at {label}")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(out / "fi_curve.png", dpi=200)
    plt.close(figure)

    if robustness:
        figure, axis = plt.subplots(figsize=(8, 4))
        for family, color in (("na", "#1f77b4"), ("kdr", "#d62728")):
            rows = [row for row in robustness["conductance"] if row["family"] == family]
            axis.plot([row["percent"] for row in rows], [row["firing_rate_hz"] for row in rows], marker="o", label=family, color=color)
        axis.set(xlabel="Conductance perturbation (%)", ylabel="Firing rate at representative current (Hz)", title=f"L571 conductance sensitivity at {label}")
        axis.legend()
        axis.grid(alpha=0.2)
        figure.tight_layout()
        figure.savefig(out / "sensitivity.png", dpi=200)
        plt.close(figure)


def validate_one(*, config_path: Path, quick: bool) -> dict[str, Any]:
    """Run all requested validation protocols for one temperature.

    Args:
        config_path: Final candidate configuration.
        quick: Whether to skip expensive robustness tests.

    Returns:
        Complete validation metrics.

    Example:
        ``metrics = validate_one(config_path=path, quick=False)``
    """

    config = load_config(path=config_path)
    label = f"{int(config['temperature_c'])}C"
    result_dir = ROOT / "results" / label
    result_dir.mkdir(parents=True, exist_ok=True)

    passive_cell = L571Cell(config=config, passive_only=True)
    passive_trace = run_step(passive_cell, current_na=config["protocols"]["rin_current_na"])
    passive_only = passive_metrics(trace=passive_trace, config=config)
    passive_summary = passive_cell.summary()
    passive_cell.dispose()

    cell = L571Cell(config=config)
    currents = config["protocols"]["fi_currents_na"]
    if quick:
        currents = [0.0, 0.02, 0.035, 0.04, 0.05, 0.10, 0.30]
    traces: dict[float, Trace] = {}
    fi_rows = []
    for current in currents:
        trace = run_step(cell, current_na=float(current))
        traces[float(current)] = trace
        fi_rows.append(firing_metrics(trace=trace, config=config))
    rin_trace = run_step(cell, current_na=config["protocols"]["rin_current_na"])
    active_passive = passive_metrics(trace=rin_trace, config=config)
    zero_trace = representative_trace(traces=traces, current_na=0.0)
    rmp = zero_current_rmp(trace=zero_trace)
    firing_rows = [row for row in fi_rows if row["spike_count"] > 0]
    rheobase = min((row["current_na"] for row in firing_rows), default=None)
    representative = representative_trace(
        traces=traces,
        current_na=config["protocols"]["representative_current_na"],
    )
    waveform = action_potential_metrics(trace=representative, config=config)
    representative_firing = firing_metrics(trace=representative, config=config)
    pathology = pathology_metrics(traces=traces, config=config)
    kinetics = mechanism_kinetics(cell=cell)
    robustness = None if quick else robustness_tests(cell=cell, config=config)
    cell_summary = cell.summary()
    cell.dispose()
    nseg = None if quick else nseg_convergence(config=config)
    metrics: dict[str, Any] = {
        "configuration": str(config_path.resolve()),
        "temperature_c": config["temperature_c"],
        "model": cell_summary,
        "passive_only": passive_only,
        "passive_model": passive_summary,
        "active_passive": active_passive,
        "rmp_mv": rmp,
        "rheobase_na": rheobase,
        "representative_current_na": config["protocols"]["representative_current_na"],
        "representative_firing": representative_firing,
        "action_potential": waveform,
        "pathology": pathology,
        "fi_curve": fi_rows,
        "mechanism_temperature_audit": kinetics,
        "robustness": robustness,
        "nseg_convergence": nseg,
    }
    metrics["status_table"] = status_table(metrics=metrics, temperature_c=config["temperature_c"])
    save_json(value=metrics, path=result_dir / "validation_metrics.json")
    write_fi_csv(rows=fi_rows, path=result_dir / "fi_curve.csv")
    save_trace_archive(
        traces={
            "passive": passive_trace,
            "zero": zero_trace,
            "representative": representative,
            "strong": representative_trace(traces=traces, current_na=config["protocols"]["strong_current_na"]),
        },
        path=result_dir / "selected_traces.npz",
    )
    plot_outputs(
        label=label,
        config=config,
        traces=traces,
        passive_trace=passive_trace,
        fi_rows=fi_rows,
        robustness=robustness,
    )
    return metrics


def plot_comparison(*, results: dict[str, dict[str, Any]]) -> None:
    """Generate side-by-side 23 C versus 35 C summary plots.

    Args:
        results: Temperature-label validation results.

    Returns:
        None.

    Example:
        ``plot_comparison(results=results)``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [label for label in ("23C", "35C") if label in results]
    if len(labels) < 2:
        return
    figure, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for label in labels:
        rows = results[label]["fi_curve"]
        axes[0].plot([row["current_na"] for row in rows], [row["firing_rate_hz"] for row in rows], marker="o", label=label)
    axes[0].set(xlabel="Injected current (nA)", ylabel="Firing rate (Hz)", title="F-I comparison")
    axes[0].legend()
    axes[0].grid(alpha=0.2)
    features = ("RMP", "Rin/10", "AP peak", "AP width×10")
    values = {}
    for label in labels:
        result = results[label]
        values[label] = [
            result["rmp_mv"],
            result["active_passive"]["rin_mohm"] / 10.0,
            result["action_potential"].get("peak_mv"),
            (result["action_potential"].get("half_width_ms") or 0.0) * 10.0,
        ]
    x = np.arange(len(features))
    width = 0.35
    for index, label in enumerate(labels):
        axes[1].bar(x + (index - 0.5) * width, values[label], width=width, label=label)
    axes[1].set_xticks(x, features)
    axes[1].set_title("Selected metrics (scaled where labelled)")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.2)
    figure.suptitle("L571-LCN 23 C versus 35 C")
    figure.savefig(ROOT / "figures" / "23C_vs_35C_comparison.png", dpi=200)
    plt.close(figure)


def write_final_report(*, results: dict[str, dict[str, Any]]) -> None:
    """Write the final evidence-aware validation report.

    Args:
        results: Completed temperature validations.

    Returns:
        None.

    Example:
        ``write_final_report(results=results)``
    """

    if "23C" not in results or "35C" not in results:
        return
    result23 = results["23C"]
    result35 = results["35C"]
    rows23 = {row["feature"]: row for row in result23["status_table"]}
    rows35 = {row["feature"]: row for row in result35["status_table"]}
    feature_order = [row["feature"] for row in result23["status_table"]]
    lines = [
        "# L571-LCN final validation",
        "",
        "## Scope and identity",
        "",
        "**CONFIRMED:** rat; lumbar spinal cord; lamina I; local-circuit interneuron; VGAT-positive/GABAergic reconstructed example; multipolar; soma, dendrites, and axon reconstructed.",
        "",
        "**POPULATION-LEVEL CONSTRAINT:** tonic firing is common/predominant among non-rhythmic rat lamina-I LCNs; population Rin is approximately 0.9 ± 0.1 GΩ.",
        "",
        "**UNKNOWN:** exact individual L571 firing class, rheobase, AP waveform parameters, membrane tau, and behaviour at 35 C.",
        "",
        "The 23 C candidate is constrained against experiments performed at 22–24 C. The 35 C candidate sets `h.celsius = 35` before initialization but deliberately retains Q10=1 for the selected active mechanisms because the executed Medlock source does not apply a correction and no L571-specific correction is available. It is therefore a conservative temperature-labelled translation with a major biological limitation, not direct 35 C validation.",
        "",
        "## Results",
        "",
        "| Feature | Target/source | 23 C result | 35 C result | Status | Confidence |",
        "|---|---|---:|---:|---|---|",
    ]
    for feature in feature_order:
        row23 = rows23[feature]
        row35 = rows35[feature]
        result_23 = row23["result"]
        result_35 = row35["result"]
        status = row23["status"] if row23["status"] != "NO EXPERIMENTAL TARGET" else row35["status"]
        confidence = row23["confidence"]
        lines.append(
            f"| {feature} | {row23['target_source']} | {result_23} | {result_35} | {status} | {confidence} |"
        )
    lines.extend(
        [
            "",
            "## Phenotype and numerical checks",
            "",
            f"- 23 C rheobase on the tested 5 pA grid: {result23['rheobase_na']} nA; representative firing at 0.1 nA: {result23['representative_firing']['spike_count']} spikes, persistence {result23['representative_firing']['tonic_persistence_fraction']:.3f}.",
            f"- 35 C rheobase on the same grid: {result35['rheobase_na']} nA; representative firing at 0.1 nA: {result35['representative_firing']['spike_count']} spikes, persistence {result35['representative_firing']['tonic_persistence_fraction']:.3f}.",
            f"- Pathology flags at 23 C: {result23['pathology']}.",
            f"- Pathology flags at 35 C: {result35['pathology']}.",
            "- Full nseg, dt, initial-voltage, and ±5/±10% Na/K perturbation results are stored in each temperature's `validation_metrics.json`.",
            "",
            "## Decision",
            "",
            "**READY WITH BIOLOGICAL LIMITATIONS**",
            "",
            "The 23 C model is population-constrained rather than L571-electrophysiology-specific. The 35 C model is suitable as a clearly labelled exploratory translation, but its active-channel temperature dependence remains unresolved and must not be presented as experimentally validated.",
        ]
    )
    (ROOT / "reports" / "L571_final_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Run selected validations and generate machine-readable and visual outputs.

    Returns:
        Process status code.

    Example:
        ``raise SystemExit(main())``
    """

    args = parse_args()
    selected = {
        "23C": ROOT / "parameters" / "L571_final_23C.json",
        "35C": ROOT / "parameters" / "L571_final_35C.json",
    }
    if args.temperature != "all":
        selected = {f"{args.temperature}C": selected[f"{args.temperature}C"]}
    if args.dry_run:
        print(json.dumps({"configs": {key: str(value) for key, value in selected.items()}, "quick": args.quick}, indent=2))
        return 0
    if args.report_only:
        results = {
            label: json.loads((ROOT / "results" / label / "validation_metrics.json").read_text(encoding="utf-8"))
            for label in ("23C", "35C")
        }
        plot_comparison(results=results)
        write_final_report(results=results)
        print(json.dumps({"status": "REPORT REGENERATED"}, indent=2))
        return 0
    results = {
        label: validate_one(config_path=path, quick=args.quick)
        for label, path in selected.items()
    }
    plot_comparison(results=results)
    write_final_report(results=results)
    print(
        json.dumps(
            {
                "status": "READY WITH BIOLOGICAL LIMITATIONS" if len(results) == 2 else "COMPLETE",
                "outputs": {label: str(ROOT / "results" / label / "validation_metrics.json") for label in results},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
