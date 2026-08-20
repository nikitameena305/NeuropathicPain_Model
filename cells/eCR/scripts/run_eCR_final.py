"""Reproduce and validate the final NMO_260150 eCR-like model at 35 C."""

from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ecr_model import (
    ECRCell,
    IDENTITY_STATEMENT,
    analyse_trace,
    ensure_mechanisms,
    run_iclamp,
    run_subthreshold_voltage_clamp,
    spike_crossings,
    write_json,
)


CELL_DIR = Path(__file__).resolve().parents[1]
MORPHOLOGY = CELL_DIR / "morphology" / "NMO_260150_100521A-S14_set5_cell11_standardized.CNG.swc"
REFERENCE_PARAMETERS = CELL_DIR / "parameters" / "active_final_23C.json"
FINAL_PARAMETERS = CELL_DIR / "parameters" / "eCR_NMO260150_final_35C.json"
RESULT_PATH = CELL_DIR / "results" / "final_validation_35C.json"
ROBUSTNESS_PATH = CELL_DIR / "results" / "robustness.json"
TRACE_PATH = CELL_DIR / "results" / "final_representative_traces.csv"
CHANNEL_PATH = CELL_DIR / "results" / "channel_temperature_diagnostics.json"
FIGURE_PATH = CELL_DIR / "figures" / "channels_temperature.png"

TARGETS = {
    "rmp_mV": {"mean": -59.0, "sd": 8.2, "n": 31},
    "rin_MOhm": {"mean": 749.9, "sd": 307.0, "n": 31},
    "capacitance_pF": {"mean": 10.58, "sd": 2.2, "n": 31},
    "rheobase_pA": {"mean": 26.9, "sd": 20.5, "n": 26},
    "ap_threshold_mV_dvdt_10": {"mean": -35.3, "sd": 5.4, "n": 26},
    "first_spike_latency_ms": {"mean": 321.8, "sd": 235.8, "n": 26},
    "ap_base_width_ms_threshold_to_downstroke": {"mean": 1.4, "sd": 0.5, "n": 26},
    "ap_height_mV_peak_minus_threshold": {"mean": 64.8, "sd": 10.2, "n": 26},
    "ahp_mV_trough_minus_threshold": {"mean": -28.42, "sd": 5.2, "n": 26},
    "IAr_model_current_pA": {"mean": 165.7, "sd": 80.3, "n": 10},
    "Ih_model_current_pA": {"mean": -10.9, "sd": 5.0, "n": 11},
}

PROTOCOL = {
    "baseline_duration_ms": 60000.0,
    "current_step_delay_ms": 300.0,
    "current_step_duration_ms": 1000.0,
    "current_step_recovery_ms": 200.0,
    "current_increment_pA": 5.0,
    "current_range_pA": [0.0, 100.0],
    "threshold_definition": "first pre-spike upward crossing of dV/dt > 10 mV/ms",
    "ap_height_definition": "AP peak minus AP threshold",
    "base_width_definition": "threshold crossing to first downstroke crossing of threshold voltage",
}

TEMPERATURE_AUDIT = {
    "B_Na": {
        "celsius_or_Q10": "tadj=3^((celsius-23)/10) declared in rates TABLE but not applied to taus",
        "effective_scaling": "none from celsius in this source",
        "Tref_C": 23.0,
    },
    "B_DR": {
        "celsius_or_Q10": "tadj=3^((celsius-23)/10) declared but not used in rate equations",
        "effective_scaling": "none from celsius in this source",
        "Tref_C": 23.0,
    },
    "B_A": {
        "celsius_or_Q10": "tadj=3^((celsius-23)/10) divides activation/inactivation taus",
        "effective_scaling": "Q10 3 for kinetics",
        "Tref_C": 23.0,
    },
    "Ih_Kole": {
        "celsius_or_Q10": "no celsius/Q10 term in source",
        "effective_scaling": "none",
        "Tref_C": None,
    },
}


def dry_run_payload() -> dict[str, Any]:
    """Return the deterministic execution plan without importing NEURON."""

    return {
        "cell": "100521A-S14_set5_cell11",
        "nmo": "NMO_260150",
        "morphology": str(MORPHOLOGY.relative_to(CELL_DIR)),
        "temperature_C": 35.0,
        "protocol": PROTOCOL,
        "outputs": [
            str(path.relative_to(CELL_DIR))
            for path in (FINAL_PARAMETERS, RESULT_PATH, ROBUSTNESS_PATH, TRACE_PATH, CHANNEL_PATH, FIGURE_PATH)
        ],
    }


def make_cell(
    h: Any,
    parameters: dict[str, Any],
    *,
    temperature_C: float,
    dt_ms: float = 0.025,
    d_lambda: float = 0.1,
    diameter_scale: float = 1.0,
    active_scale: tuple[str, float] | None = None,
) -> ECRCell:
    """Instantiate one configured cell and set temperature before initialization."""

    active = deepcopy(parameters["active"])
    if active_scale is not None:
        mechanism, scale = active_scale
        active[mechanism] = {region: density * scale for region, density in active[mechanism].items()}
    h.celsius = float(temperature_C)
    h.dt = float(dt_ms)
    h.steps_per_ms = 1.0 / h.dt
    return ECRCell(
        h,
        morphology_path=MORPHOLOGY,
        passive=parameters["passive"],
        active=active,
        diameter_scale=diameter_scale,
        d_lambda=d_lambda,
        frequency_hz=100.0,
        ais={"enabled": False},
    )


def run_step(h: Any, cell: ECRCell, amplitude_pA: float, *, record_currents: bool = False) -> tuple[dict[str, list[float]], dict[str, Any]]:
    """Run and analyse one paper-aligned 1 s current step."""

    delay = PROTOCOL["current_step_delay_ms"]
    duration = PROTOCOL["current_step_duration_ms"]
    trace = run_iclamp(
        h,
        cell=cell,
        amplitude_nA=amplitude_pA / 1000.0,
        delay_ms=delay,
        duration_ms=duration,
        tstop_ms=delay + duration + PROTOCOL["current_step_recovery_ms"],
        v_init_mV=-60.0,
        record_currents=record_currents,
    )
    metrics = analyse_trace(trace, amplitude_nA=amplitude_pA / 1000.0, delay_ms=delay, duration_ms=duration)
    return trace, metrics


def exact_current_scan(h: Any, cell: ECRCell, *, maximum_pA: int = 100) -> tuple[list[dict[str, Any]], dict[float, dict[str, list[float]]]]:
    """Run the exact 5 pA protocol and retain representative traces."""

    rows: list[dict[str, Any]] = []
    traces: dict[float, dict[str, list[float]]] = {}
    for amplitude_pA in range(0, maximum_pA + 1, 5):
        trace, metrics = run_step(h, cell, float(amplitude_pA), record_currents=False)
        rows.append(metrics)
        traces[float(amplitude_pA)] = trace
    return rows, traces


def first_spiking_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the lowest-current spiking result."""

    return next((row for row in rows if row["spike_count"] > 0), None)


def baseline_test(h: Any, cell: ECRCell) -> dict[str, Any]:
    """Run the paper's one-minute zero-current spontaneous-activity screen."""

    clamp = h.IClamp(cell.soma(0.5))
    clamp.delay = 0.0
    clamp.dur = PROTOCOL["baseline_duration_ms"]
    clamp.amp = 0.0
    times = h.Vector().record(h._ref_t, 0.5)
    voltages = h.Vector().record(cell.soma(0.5)._ref_v, 0.5)
    h.tstop = PROTOCOL["baseline_duration_ms"]
    h.finitialize(-60.0)
    h.continuerun(h.tstop)
    t = list(times)
    v = list(voltages)
    indices = spike_crossings(t, v, start_ms=0.0, stop_ms=h.tstop)
    late = [value for time, value in zip(t, v) if time >= h.tstop - 1000.0]
    return {
        "duration_s": h.tstop / 1000.0,
        "spike_count": len(indices),
        "frequency_Hz": len(indices) / (h.tstop / 1000.0),
        "classification": "spontaneously active" if indices else "silent spontaneous baseline",
        "late_mean_mV": sum(late) / len(late),
    }


def passive_probe(h: Any, cell: ECRCell) -> dict[str, Any]:
    """Measure active-model RMP, Rin, and capacitance at the final temperature."""

    _, zero = run_step(h, cell, 0.0)
    _, negative = run_step(h, cell, -5.0)
    return {
        "rmp_mV": zero["rmp_mV"],
        "rin_MOhm_from_minus5pA_current_step": negative["rin_MOhm"],
        "modeled_whole_cell_capacitance_pF": cell.capacitance_pf(),
        "note": "Rin is a model current-step probe; the paper used five 1 s, -5 mV voltage steps from -70 mV.",
    }


def channel_diagnostics(h: Any, cell: ECRCell) -> tuple[dict[str, Any], dict[str, list[float]]]:
    """Apply the -60/-90/-40 mV channel protocol and summarize IAr and Ih."""

    trace = run_subthreshold_voltage_clamp(h, cell=cell, v_init_mV=-60.0)
    t = trace["time_ms"]
    iar = trace["IAr_model_current_pA"]
    ih = trace["Ih_model_current_pA"]
    rapid_window = [value for time, value in zip(t, iar) if 1200.0 <= time <= 1220.0]
    ih_window = [value for time, value in zip(t, ih) if 1000.0 <= time <= 1200.0]
    summary = {
        "IAr_model_current_pA": max(rapid_window),
        "Ih_model_current_pA": sum(ih_window) / len(ih_window),
        "protocol": "hold -60 mV; -90 mV for 1 s; -40 mV for 200 ms",
        "interpretation": "whole-cell model diagnostics, not exact-cell channel measurements",
    }
    return summary, trace


def variation_result(
    h: Any,
    parameters: dict[str, Any],
    *,
    label: str,
    dt_ms: float = 0.025,
    d_lambda: float = 0.1,
    diameter_scale: float = 1.0,
    active_scale: tuple[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate one lightweight numerical or biological sensitivity case."""

    cell = make_cell(
        h,
        parameters,
        temperature_C=35.0,
        dt_ms=dt_ms,
        d_lambda=d_lambda,
        diameter_scale=diameter_scale,
        active_scale=active_scale,
    )
    rows, _ = exact_current_scan(h, cell, maximum_pA=50)
    rheobase = first_spiking_row(rows)
    _, strong = run_step(h, cell, 100.0)
    result = {
        "label": label,
        "dt_ms": dt_ms,
        "d_lambda": d_lambda,
        "diameter_scale": diameter_scale,
        "active_scale": None if active_scale is None else {active_scale[0]: active_scale[1]},
        "inventory": cell.inventory(),
        "rheobase_pA": None if rheobase is None else rheobase["amplitude_nA"] * 1000.0,
        "rheobase_metrics": rheobase,
        "strong_100pA": strong,
    }
    cell.delete()
    return result


def robustness_suite(h: Any, parameters: dict[str, Any]) -> dict[str, Any]:
    """Run the requested bounded robustness matrix."""

    cases = [
        {"label": "nominal"},
        {"label": "half_dt", "dt_ms": 0.0125},
        {"label": "finer_d_lambda", "d_lambda": 0.05},
        {"label": "diameter_minus20pct", "diameter_scale": 0.8},
        {"label": "diameter_plus20pct", "diameter_scale": 1.2},
    ]
    for mechanism in ("B_Na", "B_DR", "B_A", "Ih_Kole"):
        for scale in (0.9, 1.1):
            cases.append({"label": f"{mechanism}_{scale:.1f}x", "active_scale": (mechanism, scale)})
    results = [variation_result(h, parameters, **case) for case in cases]
    nominal = results[0]
    comparison = []
    for row in results[1:]:
        comparison.append(
            {
                "label": row["label"],
                "rheobase_change_pA": None
                if row["rheobase_pA"] is None or nominal["rheobase_pA"] is None
                else row["rheobase_pA"] - nominal["rheobase_pA"],
                "firing_class_at_rheobase": None
                if row["rheobase_metrics"] is None
                else row["rheobase_metrics"]["firing_class"],
                "depolarization_block_at_100pA": row["strong_100pA"]["depolarization_block"],
                "recovery_pass_at_100pA": row["strong_100pA"]["recovery_pass_5mV"],
            }
        )
    return {
        "temperature_C": 35.0,
        "scope": "13 deterministic cases; 0-50 pA in 5 pA steps plus a 100 pA safety step",
        "ais_sensitivity": "not applicable: no reconstructed axon and no synthetic AIS",
        "nominal": nominal,
        "cases": results,
        "comparison_to_nominal": comparison,
    }


def write_trace_csv(path: Path, selected: dict[str, tuple[float, dict[str, list[float]]]]) -> None:
    """Write long-form representative traces for reuse without rerunning NEURON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["condition", "temperature_C", "current_pA", "time_ms", "voltage_mV"])
        for condition, (temperature, trace) in selected.items():
            current = float(condition.rsplit("_", 1)[-1].replace("pA", ""))
            for time, voltage in zip(trace["time_ms"][::4], trace["voltage_mV"][::4]):
                writer.writerow([condition, temperature, current, time, voltage])


def make_figure(
    channel_traces: dict[str, dict[str, list[float]]],
    representative: dict[str, tuple[float, dict[str, list[float]]]],
    reference_row: dict[str, Any],
    final_row: dict[str, Any],
) -> None:
    """Create the fifth and final original model figure."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    colors = {"23 C": "#495057", "35 C": "#e8590c"}
    for label, trace in channel_traces.items():
        times = trace["time_ms"]
        axes[0, 0].plot(times, trace["IAr_model_current_pA"], color=colors[label], label=label)
        axes[0, 1].plot(times, trace["Ih_model_current_pA"], color=colors[label], label=label)
    axes[0, 0].set(title="Rapid A-current diagnostic", xlabel="Time (ms)", ylabel="Whole-cell IAr (pA)", xlim=(1180, 1300))
    axes[0, 1].set(title="HCN current diagnostic", xlabel="Time (ms)", ylabel="Whole-cell Ih (pA)", xlim=(180, 1220))
    axes[0, 0].legend(frameon=False)
    axes[0, 1].legend(frameon=False)
    for condition, (temperature, trace) in representative.items():
        if "rheobase" not in condition:
            continue
        axes[1, 0].plot(trace["time_ms"], trace["voltage_mV"], label=condition.replace("_", " "))
    axes[1, 0].axvspan(300, 1300, color="#7048e8", alpha=0.06)
    axes[1, 0].set(title="Reference vs 35 C at tested rheobase", xlabel="Time (ms)", ylabel="Soma Vm (mV)")
    axes[1, 0].legend(frameon=False)
    metric_keys = [
        ("ap_threshold_mV_dvdt_10", "Threshold\n(mV)"),
        ("first_spike_latency_ms", "Latency\n(ms)"),
        ("ap_base_width_ms_threshold_to_downstroke", "Base width\n(ms)"),
        ("ap_height_mV_peak_minus_threshold", "AP height\n(mV)"),
    ]
    x = range(len(metric_keys))
    ref_z = [(reference_row[key] - TARGETS[key]["mean"]) / TARGETS[key]["sd"] for key, _ in metric_keys]
    final_z = [(final_row[key] - TARGETS[key]["mean"]) / TARGETS[key]["sd"] for key, _ in metric_keys]
    axes[1, 1].bar([value - 0.18 for value in x], ref_z, width=0.36, color=colors["23 C"], label="23 C")
    axes[1, 1].bar([value + 0.18 for value in x], final_z, width=0.36, color=colors["35 C"], label="35 C")
    axes[1, 1].axhspan(-1, 1, color="#b2f2bb", alpha=0.35)
    axes[1, 1].axhline(0, color="black", linewidth=0.8)
    axes[1, 1].set_xticks(list(x), [label for _, label in metric_keys])
    axes[1, 1].set(title="Population-target deviation", ylabel="Z score")
    axes[1, 1].legend(frameon=False)
    fig.suptitle("NMO_260150 channel diagnostics and 35 C translation (model outputs)", fontsize=16)
    fig.savefig(FIGURE_PATH, dpi=180)
    plt.close(fig)


def main() -> None:
    """Execute the complete deterministic validation workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan without importing NEURON")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps(dry_run_payload(), indent=2))
        return

    from neuron import h

    h.load_file("stdrun.hoc")
    library = ensure_mechanisms(h, mechanism_dir=CELL_DIR / "mechanisms")
    parameters = json.loads(REFERENCE_PARAMETERS.read_text(encoding="utf-8"))

    reference_cell = make_cell(h, parameters, temperature_C=23.0)
    reference_rows, reference_traces = exact_current_scan(h, reference_cell)
    reference_rheobase = first_spiking_row(reference_rows)
    reference_channels, reference_channel_trace = channel_diagnostics(h, reference_cell)
    reference_cell.delete()

    final_cell = make_cell(h, parameters, temperature_C=35.0)
    inventory = final_cell.inventory()
    baseline = baseline_test(h, final_cell)
    passive = passive_probe(h, final_cell)
    final_rows, final_traces = exact_current_scan(h, final_cell)
    final_rheobase = first_spiking_row(final_rows)
    if final_rheobase is None or reference_rheobase is None:
        raise RuntimeError("no action potential was found in the 0-100 pA final scan")
    final_channels, final_channel_trace = channel_diagnostics(h, final_cell)
    final_cell.delete()

    reference_rheobase_pA = reference_rheobase["amplitude_nA"] * 1000.0
    final_rheobase_pA = final_rheobase["amplitude_nA"] * 1000.0
    strong_row = final_rows[-1]
    validation = {
        "identity": {
            "NMO_ID": "NMO_260150",
            "cell_name": "100521A-S14_set5_cell11",
            "known_identity": IDENTITY_STATEMENT,
            "unconfirmed": "CR/calretinin identity",
            "mapping": "eCR-like computational analogue",
        },
        "evidence_category": "35 C model prediction constrained by NPFFCre-targeted / GRPRFlp-excluded population-level electrophysiology",
        "temperature_C": 35.0,
        "temperature_audit": TEMPERATURE_AUDIT,
        "inventory": inventory,
        "baseline_60s": baseline,
        "passive_probe": passive,
        "rheobase_pA_5pA_resolution": final_rheobase_pA,
        "rheobase_metrics": final_rheobase,
        "per_current": final_rows,
        "strong_100pA": strong_row,
        "channels": final_channels,
        "targets": TARGETS,
        "acceptance": {
            "delayed_target": "PASS" if final_rheobase["firing_class"] == "delayed" else "FAIL",
            "spontaneous_status": baseline["classification"],
            "depolarization_block": strong_row["depolarization_block"],
            "recovery": "PASS" if all(row["recovery_pass_5mV"] for row in final_rows) else "FAIL",
            "interpretation": "Tonic is a reported NPFF population phenotype; the long-delay target was not forced.",
        },
        "runtime": {"neuron_version": str(h.nrnversion()), "mechanism_library": str(library)},
    }
    write_json(RESULT_PATH, validation)

    final_parameter_payload = {
        "NMO_ID": "NMO_260150",
        "cell_name": "100521A-S14_set5_cell11",
        "known_identity": "NPFF-positive superficial dorsal-horn excitatory vertical interneuron",
        "unconfirmed_identity": "CR/calretinin",
        "medlock_mapping": "eCR-like computational analogue only",
        "morphology_path": str(MORPHOLOGY.relative_to(CELL_DIR)),
        "morphology_sha256": "AC078EE88E43CC9831544BE2242C24AC6212D26CF7C9A237A3597314A5E27F7F",
        "axon_status": "NO RECONSTRUCTED AXON",
        "diameter_status": "NeuroMorpho metadata says No Diameter; standardized CNG radius profile retained as model-defined nominal geometry",
        "diameter_scale": 1.0,
        "AIS_status": "NO SYNTHETIC AIS; native soma+dendrite model was excitable",
        "temperature_C": 35.0,
        "temperature_interpretation": "model prediction, not a direct experimental validation temperature",
        "passive": parameters["passive"],
        "active": parameters["active"],
        "mechanism_temperature_audit": TEMPERATURE_AUDIT,
        "dt_ms": 0.025,
        "nseg_rule": "odd nseg from d-lambda=0.1 at 100 Hz",
        "protocol": PROTOCOL,
        "experimental_targets": TARGETS,
        "evidence_category": "NPFFCre-targeted / GRPRFlp-excluded population-level electrophysiology",
        "reference_rheobase_pA": reference_rheobase_pA,
        "final_rheobase_pA": final_rheobase_pA,
        "model_status": "PARTIAL: quantitatively constrained tonic 35 C prediction; capacitance and delayed-latency targets are not met",
        "determinism": "no random processes; deterministic fixed-step integration",
    }
    write_json(FINAL_PARAMETERS, final_parameter_payload)

    robustness = robustness_suite(h, parameters)
    write_json(ROBUSTNESS_PATH, robustness)
    channel_payload = {
        "protocol": "-60 mV hold, -90 mV 1 s, -40 mV 200 ms",
        "reference_23C": reference_channels,
        "final_35C": final_channels,
        "temperature_audit": TEMPERATURE_AUDIT,
    }
    write_json(CHANNEL_PATH, channel_payload)

    representative = {
        f"reference_rheobase_{reference_rheobase_pA:.0f}pA": (23.0, reference_traces[reference_rheobase_pA]),
        f"final_rheobase_{final_rheobase_pA:.0f}pA": (35.0, final_traces[final_rheobase_pA]),
        "final_near_25pA": (35.0, final_traces[25.0]),
        "final_strong_100pA": (35.0, final_traces[100.0]),
    }
    write_trace_csv(TRACE_PATH, representative)
    make_figure(
        {"23 C": reference_channel_trace, "35 C": final_channel_trace},
        representative,
        reference_rheobase,
        final_rheobase,
    )
    print(
        json.dumps(
            {
                "temperature_C": 35.0,
                "rheobase_pA": final_rheobase_pA,
                "firing_class": final_rheobase["firing_class"],
                "baseline": baseline["classification"],
                "robustness_cases": len(robustness["cases"]),
                "result": str(RESULT_PATH),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
