#!/usr/bin/env python3
"""Run the reproducible 35°C NMO_109005 eTrC-like single-cell model."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_PARAMETERS = PACKAGE_ROOT / "parameters" / "eTrC_NMO109005_final_35C.json"
MECHANISM_DIRECTORY = PACKAGE_ROOT / "mechanisms"
_MECHANISMS_LOADED = False


def ensure_mechanisms(*, compile_if_missing: bool = True) -> Path:
    """Compile, if needed, and load the package-local NMODL mechanisms.

    Args:
        compile_if_missing: Permit a local ``nrnivmodl`` build.

    Returns:
        Path to the loaded mechanism library.
    """

    global _MECHANISMS_LOADED
    candidates = [
        MECHANISM_DIRECTORY / "x86_64" / "libnrnmech.so",
        MECHANISM_DIRECTORY / "aarch64" / "libnrnmech.so",
        MECHANISM_DIRECTORY / "arm64" / "libnrnmech.so",
        MECHANISM_DIRECTORY / "nrnmech.dll",
    ]
    library = next((path for path in candidates if path.exists()), None)
    if library is None:
        if not compile_if_missing:
            raise FileNotFoundError(f"No compiled mechanism library under {MECHANISM_DIRECTORY}")
        executable = shutil.which("nrnivmodl")
        sibling = Path(sys.executable).resolve().parent / "nrnivmodl"
        if executable is None and sibling.exists():
            executable = str(sibling)
        if executable is None:
            raise RuntimeError("nrnivmodl was not found; activate a NEURON environment and retry")
        subprocess.run([executable], cwd=MECHANISM_DIRECTORY, check=True)
        library = next((path for path in candidates if path.exists()), None)
        if library is None:
            raise RuntimeError("nrnivmodl completed but no mechanism library was found")
    if not _MECHANISMS_LOADED:
        from neuron import h

        h.nrn_load_dll(str(library.resolve()))
        _MECHANISMS_LOADED = True
    return library


def load_parameters(path: Path = DEFAULT_PARAMETERS) -> dict[str, Any]:
    """Load and minimally validate the final configuration."""

    parameters = json.loads(path.read_text(encoding="utf-8"))
    required = {"morphology", "temperature_C", "passive", "active_domain", "active_mechanisms", "current_protocol"}
    missing = sorted(required - parameters.keys())
    if missing:
        raise ValueError(f"Missing required parameter blocks: {missing}")
    return parameters


def morphology_path(parameters: dict[str, Any]) -> Path:
    """Resolve the configured morphology without relying on the launch directory."""

    configured = Path(parameters["morphology"]["path"])
    if configured.is_absolute() and configured.exists():
        return configured
    repo_candidate = REPOSITORY_ROOT / configured
    package_candidate = PACKAGE_ROOT / "morphology" / configured.name
    for candidate in (repo_candidate, package_candidate):
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Configured morphology not found: {configured}")


def _mechanism_record(parameters: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one named active-mechanism configuration."""

    for record in parameters["active_mechanisms"]:
        if record["mechanism"] == name:
            return record
    raise KeyError(f"Final mechanism {name!r} is absent from the parameter file")


def build_cell(
    parameters: dict[str, Any],
    *,
    d_lambda: float | None = None,
    sodium_scale: float = 1.0,
    potassium_scale: float = 1.0,
) -> Any:
    """Instantiate the unchanged morphology and apply the final conductances."""

    from neuron import h

    sys.path.insert(0, str(SCRIPT_DIR))
    from fit_passive import ETrCMorphology

    h("forall delete_section()")
    discretization = dict(parameters["discretization"])
    if d_lambda is not None:
        discretization["d_lambda"] = float(d_lambda)
    cell = ETrCMorphology(
        morphology_path=morphology_path(parameters),
        passive=dict(parameters["passive"]),
        discretization=discretization,
    )
    max_length = float(parameters["active_domain"]["proximal_axon_max_segment_length_um"])
    for section in cell.axon_sections:
        required = max(1, math.ceil(float(section.L) / max_length))
        section.nseg = required if required % 2 else required + 1
    h.distance(0.0, 0.5, sec=cell.soma_sections[0])
    cutoff = float(parameters["active_domain"]["proximal_axon_cutoff_um"])
    proximal_sections = [
        section
        for section in cell.axon_sections
        if min(float(h.distance(segment.x, sec=section)) for segment in section) <= cutoff
    ]
    sodium = _mechanism_record(parameters, "B_Na")
    potassium = _mechanism_record(parameters, "B_DR")
    for section in cell.soma_sections + proximal_sections:
        section.insert("B_Na")
        section.insert("B_DR")
    h.usetable_B_Na = int(sodium["parameters"].get("usetable", 0))
    h.usetable_B_DR = int(potassium["parameters"].get("usetable", 0))
    for section in cell.soma_sections:
        for segment in section:
            segment.gnabar_B_Na = float(sodium["distribution"]["soma_gnabar_S_cm2"]) * sodium_scale
            segment.gkbar_B_DR = float(potassium["distribution"]["soma_gkbar_S_cm2"]) * potassium_scale
            segment.tau_factor_B_Na = float(sodium["parameters"]["tau_factor"])
            segment.alpha_shift_B_Na = float(sodium["parameters"]["alpha_shift_mV"])
            segment.beta_shift_B_Na = float(sodium["parameters"]["beta_shift_mV"])
            segment.ena = float(sodium["parameters"]["ena_mV"])
            segment.ek = float(potassium["parameters"]["ek_mV"])
    active_segment_count = 0
    for section in proximal_sections:
        for segment in section:
            in_domain = float(h.distance(segment.x, sec=section)) <= cutoff
            segment.gnabar_B_Na = (
                float(sodium["distribution"]["proximal_native_axon_gnabar_S_cm2"]) * sodium_scale if in_domain else 0.0
            )
            segment.gkbar_B_DR = (
                float(potassium["distribution"]["proximal_native_axon_gkbar_S_cm2"]) * potassium_scale if in_domain else 0.0
            )
            segment.tau_factor_B_Na = float(sodium["parameters"]["tau_factor"])
            segment.alpha_shift_B_Na = float(sodium["parameters"]["alpha_shift_mV"])
            segment.beta_shift_B_Na = float(sodium["parameters"]["beta_shift_mV"])
            segment.ena = float(sodium["parameters"]["ena_mV"])
            segment.ek = float(potassium["parameters"]["ek_mV"])
            active_segment_count += int(in_domain)
    cell.proximal_active_sections = proximal_sections
    cell.proximal_active_segment_count = active_segment_count
    return cell


def detect_spikes(times: np.ndarray, voltages: np.ndarray, *, start_ms: float, stop_ms: float) -> np.ndarray:
    """Return upward -20 mV threshold crossings in a selected interval."""

    crossing = np.where((voltages[:-1] < -20.0) & (voltages[1:] >= -20.0))[0] + 1
    return times[crossing[(times[crossing] >= start_ms) & (times[crossing] <= stop_ms)]]


def _window_mean(times: np.ndarray, values: np.ndarray, start_ms: float, stop_ms: float) -> float:
    """Return a mean over a non-empty time window."""

    mask = (times >= start_ms) & (times <= stop_ms)
    if not np.any(mask):
        raise ValueError(f"No samples in window {start_ms}-{stop_ms} ms")
    return float(np.mean(values[mask]))


def classify_trace(
    *,
    current_pA: float,
    rheobase_hint_pA: float,
    spike_times_ms: Sequence[float],
    late_voltage_mV: float,
    recovery_pass: bool,
) -> str:
    """Automatically classify a 1-s primary current step."""

    relative = [time - 500.0 for time in spike_times_ms]
    if not relative:
        return "reluctant" if current_pA >= 2.0 * rheobase_hint_pA else "silent"
    if (relative[-1] < 700.0 and late_voltage_mV > -40.0) or not recovery_pass:
        return "depolarization block"
    if len(relative) == 1:
        return "single-spike"
    if relative[0] > 100.0:
        return "delayed"
    if not any(time > 100.0 for time in relative):
        return "transient"
    return "tonic"


def run_current_step(
    cell: Any,
    parameters: dict[str, Any],
    *,
    current_pA: float,
    temperature_C: float | None = None,
    dt_ms: float | None = None,
    record_currents: bool = False,
) -> dict[str, Any]:
    """Run the standard held 1-s step followed by a recovery test pulse."""

    from neuron import h

    protocol = parameters["current_protocol"]
    temperature = float(parameters["temperature_C"] if temperature_C is None else temperature_C)
    dt = float(parameters["discretization"]["dt_ms"] if dt_ms is None else dt_ms)
    delay = float(protocol["primary_delay_ms"])
    duration = float(protocol["primary_duration_ms"])
    step_end = delay + duration
    test_delay = float(protocol["recovery_test_delay_ms"])
    test_end = test_delay + float(protocol["recovery_test_duration_ms"])
    stop = float(protocol["stop_ms"])
    h.cvode.active(0)
    h.celsius = temperature
    h.dt = dt
    h.steps_per_ms = 1.0 / dt
    holding = h.IClamp(cell.soma_sections[0](0.5))
    holding.delay = 0.0
    holding.dur = stop + dt
    holding.amp = float(protocol["holding_current_pA"]) / 1000.0
    primary = h.IClamp(cell.soma_sections[0](0.5))
    primary.delay = delay
    primary.dur = duration
    primary.amp = float(current_pA) / 1000.0
    test = h.IClamp(cell.soma_sections[0](0.5))
    test.delay = test_delay
    test.dur = float(protocol["recovery_test_duration_ms"])
    test.amp = float(protocol["recovery_test_current_pA"]) / 1000.0
    time_vector = h.Vector().record(h._ref_t)
    soma = cell.soma_sections[0](0.5)
    voltage_vector = h.Vector().record(soma._ref_v)
    ina_vector = h.Vector().record(soma._ref_ina_B_Na) if record_currents else None
    ikdr_vector = h.Vector().record(soma._ref_ik_B_DR) if record_currents else None
    h.finitialize(float(protocol["holding_target_mV"]))
    h.continuerun(stop)
    # Copy out of NEURON-owned vector memory.  A bare np.asarray view can be
    # overwritten when a later protocol reuses the released hoc allocation.
    times = np.asarray(time_vector, dtype=float).copy()
    voltages = np.asarray(voltage_vector, dtype=float).copy()
    primary_spikes = detect_spikes(times, voltages, start_ms=delay, stop_ms=step_end)
    test_spikes = detect_spikes(times, voltages, start_ms=test_delay, stop_ms=test_end)
    pre_voltage = _window_mean(times, voltages, delay - 50.0, delay - 5.0)
    late_voltage = _window_mean(times, voltages, step_end - 100.0, step_end - 5.0)
    recovery_voltage = _window_mean(times, voltages, test_delay - 80.0, test_delay - 20.0)
    recovery_voltage_pass = abs(recovery_voltage - pre_voltage) <= 3.0
    recovery_pass = recovery_voltage_pass and len(test_spikes) > 0
    metrics = {
        "current_pA": float(current_pA),
        "temperature_C": temperature,
        "dt_ms": dt,
        "pre_step_voltage_mV": pre_voltage,
        "spike_count": int(len(primary_spikes)),
        "first_spike_latency_ms": float(primary_spikes[0] - delay) if len(primary_spikes) else None,
        "last_spike_time_from_onset_ms": float(primary_spikes[-1] - delay) if len(primary_spikes) else None,
        "spikes_first_100_ms": int(np.sum(primary_spikes <= delay + 100.0)),
        "spikes_after_100_ms": int(np.sum(primary_spikes > delay + 100.0)),
        "firing_frequency_Hz": float(len(primary_spikes) / (duration / 1000.0)),
        "late_step_voltage_mV": late_voltage,
        "peak_voltage_mV": float(np.max(voltages[(times >= delay) & (times <= step_end)])),
        "recovery_voltage_mV": recovery_voltage,
        "recovery_voltage_pass": recovery_voltage_pass,
        "recovery_test_spike_count": int(len(test_spikes)),
        "recovery_pass": recovery_pass,
    }
    metrics["classification"] = classify_trace(
        current_pA=float(current_pA),
        rheobase_hint_pA=float(parameters["biological_targets"]["rheobase_pA"]["mean"]),
        spike_times_ms=primary_spikes,
        late_voltage_mV=late_voltage,
        recovery_pass=recovery_pass,
    )
    result: dict[str, Any] = {"metrics": metrics, "time_ms": times, "voltage_mV": voltages}
    if record_currents:
        result["ina_mA_cm2"] = np.asarray(ina_vector, dtype=float).copy()
        result["ikdr_mA_cm2"] = np.asarray(ikdr_vector, dtype=float).copy()
    return result


def measure_active_rest_and_rin(cell: Any, parameters: dict[str, Any], *, temperature_C: float, dt_ms: float) -> dict[str, float]:
    """Measure natural active-model RMP and Rin with a -1 pA, 500-ms step."""

    from neuron import h

    h.cvode.active(0)
    h.celsius = float(temperature_C)
    h.dt = float(dt_ms)
    h.steps_per_ms = 1.0 / h.dt
    clamp = h.IClamp(cell.soma_sections[0](0.5))
    clamp.delay = 500.0
    clamp.dur = 500.0
    clamp.amp = -0.001
    times_vector = h.Vector().record(h._ref_t)
    voltage_vector = h.Vector().record(cell.soma_sections[0](0.5)._ref_v)
    h.finitialize(float(parameters["passive"]["e_pas_mV"]))
    h.continuerun(1200.0)
    times = np.asarray(times_vector, dtype=float)
    voltages = np.asarray(voltage_vector, dtype=float)
    rest = _window_mean(times, voltages, 450.0, 495.0)
    steady = _window_mean(times, voltages, 950.0, 995.0)
    return {"rmp_mV": rest, "rin_MOhm": (steady - rest) / -0.001, "test_current_pA": -1.0}


def run_series(
    parameters: dict[str, Any],
    *,
    temperature_C: float | None = None,
    dt_ms: float | None = None,
    d_lambda: float | None = None,
    sodium_scale: float = 1.0,
    potassium_scale: float = 1.0,
    currents_pA: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Build one cell and execute a concise current series."""

    cell = build_cell(
        parameters,
        d_lambda=d_lambda,
        sodium_scale=sodium_scale,
        potassium_scale=potassium_scale,
    )
    temperature = float(parameters["temperature_C"] if temperature_C is None else temperature_C)
    dt = float(parameters["discretization"]["dt_ms"] if dt_ms is None else dt_ms)
    currents = list(parameters["current_protocol"]["current_series_pA"] if currents_pA is None else currents_pA)
    traces = [run_current_step(cell, parameters, current_pA=current, temperature_C=temperature, dt_ms=dt) for current in currents]
    spiking = [trace for trace in traces if trace["metrics"]["spike_count"] > 0]
    rheobase = min((trace["metrics"]["current_pA"] for trace in spiking), default=None)
    rheobase_trace = next((trace for trace in traces if trace["metrics"]["current_pA"] == rheobase), None)
    rest = measure_active_rest_and_rin(cell, parameters, temperature_C=temperature, dt_ms=dt)
    return {
        "cell": cell,
        "traces": traces,
        "metrics": [trace["metrics"] for trace in traces],
        "rheobase_pA": rheobase,
        "rheobase_trace": rheobase_trace,
        "active_rest": rest,
        "temperature_C": temperature,
        "dt_ms": dt,
        "d_lambda": float(parameters["discretization"]["d_lambda"] if d_lambda is None else d_lambda),
    }


def _write_fi_curve(path: Path, metrics: Sequence[dict[str, Any]]) -> None:
    """Write concise per-current firing metrics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(metrics[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(metrics)


def _write_representative_traces(path: Path, traces: dict[str, dict[str, Any]]) -> None:
    """Write 0.1-ms-decimated Vm, INa, and IKDR for selected conditions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["condition", "current_pA", "time_ms", "voltage_mV", "ina_mA_cm2", "ikdr_mA_cm2"])
        for label, trace in traces.items():
            stride = max(1, round(0.1 / float(trace["metrics"]["dt_ms"])))
            for index in range(0, len(trace["time_ms"]), stride):
                writer.writerow(
                    [
                        label,
                        trace["metrics"]["current_pA"],
                        f"{trace['time_ms'][index]:.4f}",
                        f"{trace['voltage_mV'][index]:.6f}",
                        f"{trace['ina_mA_cm2'][index]:.9g}",
                        f"{trace['ikdr_mA_cm2'][index]:.9g}",
                    ]
                )


def _write_figures(
    *,
    series: dict[str, Any],
    representative: dict[str, dict[str, Any]],
    active_path: Path,
    firing_path: Path,
) -> None:
    """Create the final active-trace and firing-validation figures."""

    import matplotlib.pyplot as plt

    colors = {"subthreshold": "#64748b", "rheobase": "#0f766e", "two_x": "#2563eb", "strong": "#dc2626"}
    figure, axes = plt.subplots(2, 2, figsize=(12.5, 7.2), sharex=True, sharey=True, constrained_layout=True)
    for axis, (label, trace) in zip(axes.flat, representative.items()):
        axis.plot(trace["time_ms"], trace["voltage_mV"], color=colors[label], linewidth=0.9)
        axis.axvspan(500.0, 1500.0, color="#cbd5e1", alpha=0.25)
        axis.set_title(f"{label.replace('_', ' ').title()}: {trace['metrics']['current_pA']:.1f} pA — {trace['metrics']['classification']}")
        axis.set_xlabel("Time (ms)")
        axis.set_ylabel("Somatic Vm (mV)")
        axis.set_xlim(350.0, 1850.0)
    figure.suptitle("NMO_109005 final 35°C current-clamp traces", fontsize=14, fontweight="bold")
    active_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(active_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    metrics = series["metrics"]
    currents = [item["current_pA"] for item in metrics]
    counts = [item["spike_count"] for item in metrics]
    latencies = [np.nan if item["first_spike_latency_ms"] is None else item["first_spike_latency_ms"] for item in metrics]
    late = [item["late_step_voltage_mV"] for item in metrics]
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 7.0), constrained_layout=True)
    axes[0, 0].plot(currents, counts, marker="o", color="#0f766e")
    axes[0, 0].set(title="F–I relation", xlabel="Injected current (pA)", ylabel="Spikes in 1 s")
    axes[0, 1].plot(currents, latencies, marker="o", color="#d97706")
    axes[0, 1].axhspan(137.1 - 12.4, 137.1 + 12.4, color="#fde68a", alpha=0.6, label="GRP mean ±2 SEM")
    axes[0, 1].set(title="First-spike latency", xlabel="Injected current (pA)", ylabel="Latency (ms)")
    axes[0, 1].legend(frameon=False)
    axes[1, 0].plot(currents, late, marker="o", color="#2563eb")
    axes[1, 0].axhline(-40.0, color="#dc2626", linestyle="--", linewidth=1.0, label="block screen")
    axes[1, 0].set(title="Late-step voltage", xlabel="Injected current (pA)", ylabel="Vm (mV)")
    axes[1, 0].legend(frameon=False)
    classification_order = [item["classification"] for item in metrics]
    axes[1, 1].axis("off")
    rows = [[f"{current:.1f}", str(count), classification] for current, count, classification in zip(currents, counts, classification_order)]
    table = axes[1, 1].table(cellText=rows, colLabels=["pA", "spikes", "class"], loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.25)
    axes[1, 1].set_title("Automatic classifications")
    figure.suptitle("NMO_109005 35°C firing validation", fontsize=14, fontweight="bold")
    firing_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(firing_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def generate_final_outputs(parameters: dict[str, Any]) -> dict[str, Any]:
    """Run the final model and write all outputs reproducible from one command."""

    results_directory = PACKAGE_ROOT / "results"
    figures_directory = PACKAGE_ROOT / "figures"
    series = run_series(parameters)
    rheobase = series["rheobase_pA"]
    if rheobase is None:
        raise RuntimeError("Final current series did not elicit any action potential")
    rheobase_metrics = series["rheobase_trace"]["metrics"]
    selected_currents = {
        "subthreshold": max(current for current in parameters["current_protocol"]["current_series_pA"] if current < rheobase),
        "rheobase": rheobase,
        "two_x": min(parameters["current_protocol"]["current_series_pA"], key=lambda value: abs(value - 2.0 * rheobase)),
        "strong": max(parameters["current_protocol"]["current_series_pA"]),
    }
    representative = {
        label: run_current_step(
            series["cell"],
            parameters,
            current_pA=current,
            temperature_C=float(parameters["temperature_C"]),
            dt_ms=float(parameters["discretization"]["dt_ms"]),
            record_currents=True,
        )
        for label, current in selected_currents.items()
    }
    _write_fi_curve(results_directory / "FI_curve.csv", series["metrics"])
    _write_representative_traces(results_directory / "representative_traces.csv", representative)
    _write_figures(
        series=series,
        representative=representative,
        active_path=figures_directory / "active_traces.png",
        firing_path=figures_directory / "firing_validation.png",
    )
    targets = parameters["biological_targets"]
    acceptance = {
        "rheobase_within_population_mean_plus_minus_2SEM": abs(rheobase - float(targets["rheobase_pA"]["mean"])) <= 2.0 * float(targets["rheobase_pA"]["sem"]),
        "latency_within_population_mean_plus_minus_2SEM": abs(float(rheobase_metrics["first_spike_latency_ms"]) - float(targets["first_spike_latency_ms"]["mean"])) <= 2.0 * float(targets["first_spike_latency_ms"]["sem"]),
        "phenotype_transient_or_single": rheobase_metrics["classification"] in {"transient", "single-spike"},
        "not_depolarization_block": all(item["classification"] != "depolarization block" for item in series["metrics"]),
        "recovery_pass": bool(rheobase_metrics["recovery_pass"]),
    }
    validation = {
        "model": parameters["model_name"],
        "claim": parameters["temperature_claim"],
        "temperature_C": parameters["temperature_C"],
        "mechanism_library": str(next(path for path in [MECHANISM_DIRECTORY / "x86_64" / "libnrnmech.so", MECHANISM_DIRECTORY / "aarch64" / "libnrnmech.so", MECHANISM_DIRECTORY / "arm64" / "libnrnmech.so", MECHANISM_DIRECTORY / "nrnmech.dll"] if path.exists()).relative_to(PACKAGE_ROOT)),
        "active_domain": parameters["active_domain"],
        "proximal_active_section_count": len(series["cell"].proximal_active_sections),
        "proximal_active_segment_count": series["cell"].proximal_active_segment_count,
        "active_rest": series["active_rest"],
        "rheobase_pA": rheobase,
        "first_spike_latency_ms": rheobase_metrics["first_spike_latency_ms"],
        "rheobase_classification": rheobase_metrics["classification"],
        "rheobase_metrics": rheobase_metrics,
        "current_series": series["metrics"],
        "acceptance": acceptance,
        "overall_target_status": "PARTIAL" if acceptance["rheobase_within_population_mean_plus_minus_2SEM"] and acceptance["phenotype_transient_or_single"] and acceptance["not_depolarization_block"] and acceptance["recovery_pass"] else "FAIL",
        "model_status": parameters["model_status"],
        "network_ready": parameters["network_ready"],
        "known_failures": [
            "first-spike latency is substantially shorter than the GRP population target",
            "active-model input resistance is lower than the GRP population target",
            "morphology-derived capacitance is much larger than the whole-cell population value",
            "B_Na and B_DR kinetics are effectively temperature-independent despite celsius/tadj variables in their source",
        ],
    }
    results_directory.mkdir(parents=True, exist_ok=True)
    (results_directory / "temperature_35C_validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return validation


def build_parser() -> argparse.ArgumentParser:
    """Create the final runner command-line parser."""

    parser = argparse.ArgumentParser(description="Run the final 35°C NMO_109005 eTrC-like model.")
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS, help="Final parameter JSON.")
    parser.add_argument("--no-compile", action="store_true", help="Fail instead of compiling absent mechanisms.")
    parser.add_argument("--dry-run", action="store_true", help="Validate paths and print the planned outputs without importing NEURON.")
    return parser


def main() -> int:
    """Execute the final model and return zero when engineering checks complete."""

    args = build_parser().parse_args()
    parameters = load_parameters(args.parameters)
    planned = {
        "repository_root": str(REPOSITORY_ROOT),
        "package_root": str(PACKAGE_ROOT),
        "morphology": str(morphology_path(parameters)),
        "temperature_C": parameters["temperature_C"],
        "outputs": [
            "results/FI_curve.csv",
            "results/representative_traces.csv",
            "results/temperature_35C_validation.json",
            "figures/active_traces.png",
            "figures/firing_validation.png",
        ],
    }
    if args.dry_run:
        print(json.dumps(planned, indent=2))
        return 0
    library = ensure_mechanisms(compile_if_missing=not args.no_compile)
    validation = generate_final_outputs(parameters)
    print(
        json.dumps(
            {
                "mechanism_library": str(library),
                "rheobase_pA": validation["rheobase_pA"],
                "first_spike_latency_ms": validation["first_spike_latency_ms"],
                "classification": validation["rheobase_classification"],
                "depolarization_block": not validation["acceptance"]["not_depolarization_block"],
                "recovery_pass": validation["acceptance"]["recovery_pass"],
                "overall_target_status": validation["overall_target_status"],
                "model_status": validation["model_status"],
                "network_ready": validation["network_ready"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
