#!/usr/bin/env python3
"""Fit and validate passive parameters for NMO_109005 with a bounded search."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence


TARGETS = {
    "rmp_mV": {"mean": -52.89, "sem": 0.78, "n": 230},
    "rin_MOhm": {"mean": 1588.0, "sem": 85.0, "n": 232},
    "whole_cell_capacitance_pF": {"mean": 5.12, "sem": 0.11, "n": 232},
}


def as_sections(value: Any) -> list[Any]:
    """Convert an Import3D section attribute to a list.

    Args:
        value: Section, SectionList-like value, array, or None.

    Returns:
        Concrete list of NEURON sections.

    Example:
        ``sections = as_sections(cell.soma)``
    """

    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return [value]


def unique_sections(sections: Iterable[Any]) -> list[Any]:
    """Deduplicate NEURON sections while preserving order.

    Args:
        sections: Candidate section sequence.

    Returns:
        Unique section list.

    Example:
        ``sections = unique_sections(imported)``
    """

    result: list[Any] = []
    seen: set[str] = set()
    for section in sections:
        name = section.name()
        if name not in seen:
            seen.add(name)
            result.append(section)
    return result


class ETrCMorphology:
    """Load NMO_109005 and expose soma, dendrite, and native-axon groups."""

    def __init__(self, *, morphology_path: Path, passive: dict[str, float], discretization: dict[str, float]) -> None:
        """Instantiate the existing SWC and apply passive parameters.

        Args:
            morphology_path: Existing NMO_109005 SWC.
            passive: Passive parameter mapping.
            discretization: d-lambda settings.

        Returns:
            None.

        Example:
            ``cell = ETrCMorphology(morphology_path=swc, passive=p, discretization=d)``
        """

        from neuron import h

        self.h = h
        self.morphology_path = morphology_path.resolve()
        h.load_file("stdrun.hoc")
        h.load_file("import3d.hoc")
        before = {section.name() for section in h.allsec()}
        source_text = self.morphology_path.read_text(encoding="utf-8-sig")
        normalised_text = "\n".join(line.rstrip("\r") for line in source_text.splitlines() if line.strip()) + "\n"
        with tempfile.TemporaryDirectory(prefix="etrC_swc_") as temporary_directory:
            import_path = Path(temporary_directory) / self.morphology_path.name
            import_path.write_text(normalised_text, encoding="utf-8", newline="\n")
            reader = h.Import3d_SWC_read()
            reader.input(str(import_path))
            importer = h.Import3d_GUI(reader, 0)
            importer.instantiate(self)
        imported = [section for section in h.allsec() if section.name() not in before]
        self.soma_sections = unique_sections(as_sections(getattr(self, "soma", None)) or [section for section in imported if "soma" in section.name().lower()])
        self.dendrite_sections = unique_sections(
            as_sections(getattr(self, "dend", None))
            + as_sections(getattr(self, "apic", None))
            or [section for section in imported if "dend" in section.name().lower() or "apic" in section.name().lower()]
        )
        self.axon_sections = unique_sections(as_sections(getattr(self, "axon", None)) or [section for section in imported if "axon" in section.name().lower()])
        self.all_sections = unique_sections(imported)
        if not self.soma_sections or not self.dendrite_sections or not self.axon_sections:
            raise RuntimeError(
                "Import3D did not expose soma, dendrite, and axon groups: "
                f"soma={len(self.soma_sections)}, dendrite={len(self.dendrite_sections)}, axon={len(self.axon_sections)}"
            )
        self.apply_passive(passive=passive, discretization=discretization)

    def apply_passive(self, *, passive: dict[str, float], discretization: dict[str, float]) -> None:
        """Apply passive properties and recalculate odd d-lambda nseg values.

        Args:
            passive: Ra, cm, g_pas, and e_pas values.
            discretization: Frequency and d-lambda fraction.

        Returns:
            None.

        Example:
            ``cell.apply_passive(passive=p, discretization=d)``
        """

        for section in self.all_sections:
            section.Ra = float(passive["Ra_ohm_cm"])
            section.cm = float(passive["cm_uF_cm2"])
            if not self.h.ismembrane("pas", sec=section):
                section.insert("pas")
            for segment in section:
                segment.g_pas = float(passive["g_pas_S_cm2"])
                segment.e_pas = float(passive["e_pas_mV"])
        self.set_discretization(discretization=discretization)

    def set_discretization(self, *, discretization: dict[str, float]) -> None:
        """Set odd nseg from the d-lambda rule after Ra and cm assignment.

        Args:
            discretization: Frequency and d-lambda fraction.

        Returns:
            None.

        Example:
            ``cell.set_discretization(discretization={"frequency_Hz": 100, "d_lambda": 0.1})``
        """

        frequency = float(discretization.get("frequency_Hz", 100.0))
        d_lambda = float(discretization.get("d_lambda", 0.1))
        if frequency <= 0.0 or d_lambda <= 0.0:
            raise ValueError("frequency_Hz and d_lambda must be positive")
        for section in self.all_sections:
            electrotonic_length = float(self.h.lambda_f(frequency, sec=section))
            if not math.isfinite(electrotonic_length) or electrotonic_length <= 0.0:
                raise RuntimeError(f"Invalid lambda_f for {section.name()}: {electrotonic_length}")
            required = max(1, math.ceil(float(section.L) / (d_lambda * electrotonic_length)))
            section.nseg = required if required % 2 else required + 1

    def total_area_um2(self) -> float:
        """Return NEURON segment surface area in square micrometres.

        Returns:
            Total membrane area.

        Example:
            ``area = cell.total_area_um2()``
        """

        return sum(float(self.h.area(segment.x, sec=section)) for section in self.all_sections for segment in section)

    def total_capacitance_pF(self) -> float:
        """Return morphology-derived ideal membrane capacitance.

        Returns:
            Sum of area times section cm in pF.

        Example:
            ``capacitance = cell.total_capacitance_pF()``
        """

        return sum(
            float(self.h.area(segment.x, sec=section)) * float(section.cm) * 0.01
            for section in self.all_sections
            for segment in section
        )


def mean_window(times: Sequence[float], values: Sequence[float], *, start_ms: float, stop_ms: float) -> float:
    """Calculate the arithmetic mean over a closed time window.

    Args:
        times: Sample times in ms.
        values: Samples paired with times.
        start_ms: Window start.
        stop_ms: Window end.

    Returns:
        Window mean.

    Example:
        ``value = mean_window(t, v, start_ms=10, stop_ms=20)``
    """

    selected = [value for time, value in zip(times, values) if start_ms <= time <= stop_ms]
    if not selected:
        raise ValueError(f"No samples in {start_ms}-{stop_ms} ms")
    return sum(selected) / len(selected)


def run_iv_protocol(cell: ETrCMorphology, *, dt_ms: float = 0.05) -> dict[str, object]:
    """Reproduce the Dickie 100-ms, -70 to -50 mV passive I-V protocol.

    Args:
        cell: Instantiated passive cell.
        dt_ms: Fixed integration step.

    Returns:
        Command voltages, steady currents, fitted RMP, and Rin.

    Example:
        ``result = run_iv_protocol(cell, dt_ms=0.05)``
    """

    import numpy as np

    h = cell.h
    h.cvode.active(0)
    h.dt = float(dt_ms)
    h.steps_per_ms = 1.0 / h.dt
    commands = [float(value) for value in np.arange(-70.0, -49.99, 2.5)]
    currents: list[float] = []
    clamp = h.SEClamp(cell.soma_sections[0](0.5))
    clamp.dur1 = 100.0
    clamp.amp1 = -60.0
    clamp.dur2 = 100.0
    clamp.dur3 = 50.0
    clamp.amp3 = -60.0
    clamp.rs = 1e-5
    current_vector = h.Vector().record(clamp._ref_i)
    time_vector = h.Vector().record(h._ref_t)
    for command in commands:
        clamp.amp2 = command
        h.finitialize(-60.0)
        h.continuerun(250.0)
        currents.append(mean_window(list(time_vector), list(current_vector), start_ms=180.0, stop_ms=198.0))
    slope_nA_per_mV, intercept_nA = np.polyfit(np.asarray(commands), np.asarray(currents), 1)
    if slope_nA_per_mV <= 0.0:
        raise RuntimeError(f"Non-positive I-V slope {slope_nA_per_mV}")
    return {
        "holding_mV": -60.0,
        "step_duration_ms": 100.0,
        "command_voltages_mV": commands,
        "steady_clamp_currents_nA": currents,
        "linear_slope_nA_per_mV": float(slope_nA_per_mV),
        "linear_intercept_nA": float(intercept_nA),
        "rmp_mV": float(-intercept_nA / slope_nA_per_mV),
        "rin_MOhm": float(1.0 / slope_nA_per_mV),
    }


def run_current_step(cell: ETrCMorphology, *, amplitude_nA: float = -0.005, dt_ms: float = 0.025) -> dict[str, object]:
    """Run a small hyperpolarising current step for the passive trace figure.

    Args:
        cell: Instantiated passive cell.
        amplitude_nA: Somatic current amplitude.
        dt_ms: Fixed integration step.

    Returns:
        Trace and steady passive metrics.

    Example:
        ``trace = run_current_step(cell, amplitude_nA=-0.005)``
    """

    h = cell.h
    h.cvode.active(0)
    h.dt = float(dt_ms)
    h.steps_per_ms = 1.0 / h.dt
    clamp = h.IClamp(cell.soma_sections[0](0.5))
    clamp.delay = 200.0
    clamp.dur = 500.0
    clamp.amp = float(amplitude_nA)
    time_vector = h.Vector().record(h._ref_t)
    voltage_vector = h.Vector().record(cell.soma_sections[0](0.5)._ref_v)
    h.finitialize(float(cell.soma_sections[0](0.5).e_pas))
    h.continuerun(900.0)
    times = list(time_vector)
    voltages = list(voltage_vector)
    rmp = mean_window(times, voltages, start_ms=150.0, stop_ms=195.0)
    steady = mean_window(times, voltages, start_ms=650.0, stop_ms=695.0)
    return {
        "amplitude_nA": amplitude_nA,
        "delay_ms": 200.0,
        "duration_ms": 500.0,
        "time_ms": times,
        "voltage_mV": voltages,
        "rmp_mV": rmp,
        "steady_voltage_mV": steady,
        "rin_MOhm": (steady - rmp) / amplitude_nA,
    }


def objective(metrics: dict[str, object], *, capacitance_pF: float) -> float:
    """Score passive candidates while preventing capacitance from forcing absurd cm.

    Args:
        metrics: I-V protocol metrics.
        capacitance_pF: Morphology-derived ideal capacitance.

    Returns:
        Lower-is-better scalar objective.

    Example:
        ``score = objective(metrics, capacitance_pF=50.0)``
    """

    rmp_error = (float(metrics["rmp_mV"]) - TARGETS["rmp_mV"]["mean"]) / TARGETS["rmp_mV"]["sem"]
    rin_error = (float(metrics["rin_MOhm"]) - TARGETS["rin_MOhm"]["mean"]) / TARGETS["rin_MOhm"]["sem"]
    capacitance_log_error = math.log(capacitance_pF / TARGETS["whole_cell_capacitance_pF"]["mean"])
    return rmp_error**2 + rin_error**2 + 0.25 * capacitance_log_error**2


def candidate_parameters() -> list[dict[str, float]]:
    """Return the bounded 144-candidate passive coarse grid.

    Returns:
        Candidate parameter mappings.

    Example:
        ``candidates = candidate_parameters()``
    """

    return [
        {"Ra_ohm_cm": ra, "cm_uF_cm2": cm, "g_pas_S_cm2": g_pas, "e_pas_mV": e_pas}
        for ra, cm, g_pas, e_pas in itertools.product(
            [100.0, 150.0, 200.0, 250.0],
            [0.7, 1.0, 1.3],
            [6.0e-6, 8.0e-6, 1.0e-5, 1.2e-5],
            [-54.0, -52.89, -51.8],
        )
    ]


def local_candidates(best: dict[str, float]) -> list[dict[str, float]]:
    """Return 25 local refinements around the best coarse candidate.

    Args:
        best: Best coarse parameter mapping.

    Returns:
        Local candidate mappings.

    Example:
        ``local = local_candidates(best)``
    """

    return [
        {
            "Ra_ohm_cm": best["Ra_ohm_cm"],
            "cm_uF_cm2": best["cm_uF_cm2"],
            "g_pas_S_cm2": best["g_pas_S_cm2"] * g_scale,
            "e_pas_mV": TARGETS["rmp_mV"]["mean"] + e_offset,
        }
        for g_scale, e_offset in itertools.product([0.85, 0.925, 1.0, 1.075, 1.15], [-0.4, -0.2, 0.0, 0.2, 0.4])
    ]


def evaluate_candidates(cell: ETrCMorphology, *, candidates: Sequence[dict[str, float]], discretization: dict[str, float]) -> list[dict[str, object]]:
    """Evaluate a bounded candidate sequence with the paper's passive I-V protocol.

    Args:
        cell: Reusable morphology instance.
        candidates: Passive parameter candidates.
        discretization: d-lambda settings.

    Returns:
        Ranked candidate records.

    Example:
        ``ranked = evaluate_candidates(cell, candidates=candidates, discretization=disc)``
    """

    results: list[dict[str, object]] = []
    for index, parameters in enumerate(candidates, 1):
        cell.apply_passive(passive=parameters, discretization=discretization)
        metrics = run_iv_protocol(cell)
        capacitance = cell.total_capacitance_pF()
        results.append(
            {
                "candidate_index": index,
                "parameters": dict(parameters),
                "metrics": {"rmp_mV": metrics["rmp_mV"], "rin_MOhm": metrics["rin_MOhm"], "whole_cell_capacitance_pF": capacitance},
                "objective": objective(metrics, capacitance_pF=capacitance),
            }
        )
    return sorted(results, key=lambda item: float(item["objective"]))


def acceptance(*, rmp_mV: float, rin_MOhm: float, capacitance_pF: float) -> dict[str, object]:
    """Assess model values against GRP population means using two-SEM bands.

    Args:
        rmp_mV: Model resting potential.
        rin_MOhm: Model input resistance.
        capacitance_pF: Morphology-derived capacitance.

    Returns:
        Per-target and overall status.

    Example:
        ``status = acceptance(rmp_mV=-53, rin_MOhm=1600, capacitance_pF=50)``
    """

    values = {"rmp_mV": rmp_mV, "rin_MOhm": rin_MOhm, "whole_cell_capacitance_pF": capacitance_pF}
    checks: dict[str, bool] = {}
    for key, value in values.items():
        target = TARGETS[key]
        checks[key] = abs(value - target["mean"]) <= 2.0 * target["sem"]
    return {
        "criterion": "model value within GRP mean +/- 2 SEM; a population constraint, not a same-cell acceptance interval",
        "checks": checks,
        "overall": "PASS" if all(checks.values()) else ("PARTIAL" if checks["rmp_mV"] and checks["rin_MOhm"] else "FAIL"),
    }


def write_figure(*, iv: dict[str, object], trace: dict[str, object], capacitance_pF: float, output_path: Path) -> None:
    """Write the concise passive-validation PNG.

    Args:
        iv: Final voltage-clamp I-V result.
        trace: Hyperpolarising current-clamp trace.
        capacitance_pF: Morphology-derived capacitance.
        output_path: Figure destination.

    Returns:
        None.

    Example:
        ``write_figure(iv=iv, trace=trace, capacitance_pF=cap, output_path=path)``
    """

    import matplotlib.pyplot as plt
    import numpy as np

    figure, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True)
    axes[0].plot(trace["time_ms"], trace["voltage_mV"], color="#0f766e", linewidth=1.2)
    axes[0].axvspan(200.0, 700.0, color="#cbd5e1", alpha=0.35, label=f"{1000 * trace['amplitude_nA']:.1f} pA")
    axes[0].set(title="Passive current step", xlabel="Time (ms)", ylabel="Somatic Vm (mV)")
    axes[0].legend(frameon=False)
    commands = np.asarray(iv["command_voltages_mV"])
    currents = np.asarray(iv["steady_clamp_currents_nA"])
    fitted = float(iv["linear_slope_nA_per_mV"]) * commands + float(iv["linear_intercept_nA"])
    axes[1].scatter(commands, 1000.0 * currents, color="#d97706", label="Model")
    axes[1].plot(commands, 1000.0 * fitted, color="#1e293b", linewidth=1.2, label="Linear fit")
    axes[1].axhline(0.0, color="#64748b", linewidth=0.8)
    axes[1].set(title="Dickie passive I-V protocol", xlabel="Command voltage (mV)", ylabel="Steady clamp current (pA)")
    axes[1].legend(frameon=False)
    labels = ["RMP", "Rin", "Capacitance"]
    model = [float(iv["rmp_mV"]), float(iv["rin_MOhm"]), capacitance_pF]
    target = [TARGETS["rmp_mV"]["mean"], TARGETS["rin_MOhm"]["mean"], TARGETS["whole_cell_capacitance_pF"]["mean"]]
    ratios = [abs(value / expected) for value, expected in zip(model, target)]
    bars = axes[2].bar(labels, ratios, color=["#0f766e", "#0f766e", "#dc2626"])
    axes[2].axhline(1.0, color="#1e293b", linestyle="--", linewidth=1.0, label="Population mean")
    axes[2].set(title="Model / population target", ylabel="Absolute ratio")
    axes[2].tick_params(axis="x", rotation=20)
    axes[2].legend(frameon=False)
    for bar, value, expected in zip(bars, model, target):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}\n(target {expected:.2f})", ha="center", va="bottom", fontsize=8)
    figure.suptitle("NMO_109005 passive validation (GRP population constraints)", fontsize=13, fontweight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser.

    Returns:
        Configured argument parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Bounded passive fit for NMO_109005.")
    parser.add_argument("--morphology", type=Path, required=True, help="Existing SWC morphology.")
    parser.add_argument("--parameters", type=Path, required=True, help="Final passive JSON destination.")
    parser.add_argument("--results", type=Path, required=True, help="Passive validation JSON destination.")
    parser.add_argument("--figure", type=Path, required=True, help="Passive validation PNG destination.")
    parser.add_argument("--dry-run", action="store_true", help="Print bounded search size without importing NEURON.")
    return parser


def main() -> int:
    """Run the passive fit and return a process exit code.

    Returns:
        Zero when RMP and Rin pass, otherwise one.

    Example:
        ``raise SystemExit(main())``
    """

    args = build_parser().parse_args()
    coarse = candidate_parameters()
    if args.dry_run:
        print(json.dumps({"coarse_candidates": len(coarse), "local_candidates_max": 25, "outputs": [str(args.parameters), str(args.results), str(args.figure)]}, indent=2))
        return 0
    from neuron import h

    h("forall delete_section()")
    discretization = {"frequency_Hz": 100.0, "d_lambda": 0.1}
    cell = ETrCMorphology(morphology_path=args.morphology, passive=coarse[0], discretization=discretization)
    coarse_ranked = evaluate_candidates(cell, candidates=coarse, discretization=discretization)
    best_coarse = dict(coarse_ranked[0]["parameters"])
    local = local_candidates(best_coarse)
    local_ranked = evaluate_candidates(cell, candidates=local, discretization=discretization)
    best = min(coarse_ranked[0], local_ranked[0], key=lambda item: float(item["objective"]))
    selected = dict(best["parameters"])
    cell.apply_passive(passive=selected, discretization=discretization)
    final_iv = run_iv_protocol(cell, dt_ms=0.025)
    final_trace = run_current_step(cell, amplitude_nA=-0.005, dt_ms=0.025)
    capacitance = cell.total_capacitance_pF()
    status = acceptance(rmp_mV=float(final_iv["rmp_mV"]), rin_MOhm=float(final_iv["rin_MOhm"]), capacitance_pF=capacitance)
    parameter_record = {
        "model": "NMO_109005 passive fit",
        "identity": "GRP-positive lamina-II excitatory interneuron; population targets are not same-cell recordings",
        "parameters": selected,
        "discretization": discretization,
        "morphology_path": args.morphology.as_posix(),
        "provenance": {
            "targets": "Dickie et al. 2019, PAIN 160:442-462, DOI 10.1097/j.pain.0000000000001406",
            "parameter_type": "fitted to GRP population-level RMP and Rin with plausible cm/Ra bounds",
            "capacitance_policy": "whole-cell capacitance retained as a comparison; cm was not forced to an implausible value",
        },
    }
    validation_record = {
        "targets": TARGETS,
        "target_evidence_level": "GRP population mean +/- SEM; not NMO_109005 same-cell electrophysiology",
        "search": {
            "coarse_candidate_count": len(coarse),
            "local_candidate_count": len(local),
            "coarse_top5": coarse_ranked[:5],
            "local_top5": local_ranked[:5],
            "objective_note": "RMP and Rin use SEM-normalised error; capacitance uses a low-weight log error to prevent an absurd specific cm.",
        },
        "selected_parameters": selected,
        "morphology_area_um2": cell.total_area_um2(),
        "morphology_derived_capacitance_pF": capacitance,
        "voltage_clamp_iv": final_iv,
        "current_clamp_confirmation": {key: value for key, value in final_trace.items() if key not in {"time_ms", "voltage_mV"}},
        "nseg": {"total": sum(int(section.nseg) for section in cell.all_sections), "all_odd": all(int(section.nseg) % 2 == 1 for section in cell.all_sections)},
        "acceptance": status,
        "limitation": "The reconstructed membrane area makes the morphology-derived capacitance far larger than the reported 5.12 pF population mean; this mismatch is preserved rather than hidden by an implausibly small cm.",
    }
    args.parameters.parent.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.parameters.write_text(json.dumps(parameter_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.results.write_text(json.dumps(validation_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_figure(iv=final_iv, trace=final_trace, capacitance_pF=capacitance, output_path=args.figure)
    print(json.dumps({"selected_parameters": selected, "metrics": best["metrics"], "final_acceptance": status, "results": str(args.results)}, indent=2))
    return 0 if status["checks"]["rmp_mV"] and status["checks"]["rin_MOhm"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
