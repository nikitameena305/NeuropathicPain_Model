"""Fit a lightweight passive NMO_260150 model to Quillet et al. population targets."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

from ecr_model import ECRCell, analyse_trace, neuron_available, run_iclamp, write_json


TARGETS = {
    "rmp_mV": {"mean": -59.0, "sd": 8.2, "n": 31},
    "rin_MOhm": {"mean": 750.0, "sd": 307.0, "n": 31},
    "whole_cell_capacitance_pF": {"mean": 10.58, "sd": 2.2, "n": 31},
}


def coarse_candidates() -> list[dict[str, float]]:
    """Return the predeclared 128-candidate passive grid.

    Args:
        None.

    Returns:
        Passive parameter mappings.

    Example:
        ``grid = coarse_candidates()``
    """

    ra_values = (100.0, 150.0, 200.0, 250.0)
    cm_values = (0.5, 0.75, 1.0, 1.25)
    g_values = (2e-5, 3e-5, 4e-5, 5e-5, 6.5e-5, 8e-5, 1e-4, 1.3e-4)
    return [
        {
            "Ra_ohm_cm": ra,
            "cm_uF_cm2": cm,
            "g_pas_S_cm2": g_pas,
            "e_pas_mV": -59.0,
        }
        for ra, cm, g_pas in itertools.product(ra_values, cm_values, g_values)
    ]


def local_candidates(best: dict[str, float]) -> list[dict[str, float]]:
    """Return at most 45 bounded refinements around the coarse optimum.

    Args:
        best: Best coarse passive parameter mapping.

    Returns:
        Deduplicated local parameter mappings.

    Example:
        ``grid = local_candidates(best)``
    """

    ra_values = sorted({max(75.0, best["Ra_ohm_cm"] + delta) for delta in (-25.0, 0.0, 25.0)})
    cm_values = sorted({max(0.5, best["cm_uF_cm2"] + delta) for delta in (-0.1, 0.0, 0.1)})
    g_values = sorted({best["g_pas_S_cm2"] * scale for scale in (0.8, 0.9, 1.0, 1.1, 1.2)})
    return [
        {
            "Ra_ohm_cm": ra,
            "cm_uF_cm2": cm,
            "g_pas_S_cm2": g_pas,
            "e_pas_mV": -59.0,
        }
        for ra, cm, g_pas in itertools.product(ra_values, cm_values, g_values)
    ]


def score_candidate(*, rmp_mV: float, rin_MOhm: float, capacitance_pF: float) -> float:
    """Calculate a transparent sum-of-squared target z scores.

    Args:
        rmp_mV: Modeled resting membrane potential.
        rin_MOhm: Modeled input resistance.
        capacitance_pF: Modeled whole-cell capacitance.

    Returns:
        Lower-is-better score.

    Example:
        ``score = score_candidate(rmp_mV=-59, rin_MOhm=750, capacitance_pF=15)``
    """

    values = {
        "rmp_mV": rmp_mV,
        "rin_MOhm": rin_MOhm,
        "whole_cell_capacitance_pF": capacitance_pF,
    }
    return sum(
        ((values[name] - target["mean"])/target["sd"]) ** 2
        for name, target in TARGETS.items()
    )


def evaluate_candidate(
    h: Any,
    *,
    cell: ECRCell,
    passive: dict[str, float],
    dt_ms: float,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    """Run one -5 pA, 1-second passive validation step.

    Args:
        h: NEURON hoc interface.
        cell: Reused morphology instance.
        passive: Candidate passive parameters.
        dt_ms: Fixed integration time step.

    Returns:
        Candidate result and raw trace.

    Example:
        ``result, trace = evaluate_candidate(h, cell=cell, passive=params, dt_ms=0.025)``
    """

    cell.apply_passive(passive)
    cell.configure_nseg(d_lambda=0.1, frequency_hz=100.0)
    h.dt = dt_ms
    h.steps_per_ms = 1.0/dt_ms
    trace = run_iclamp(
        h,
        cell=cell,
        amplitude_nA=-0.005,
        delay_ms=200.0,
        duration_ms=1000.0,
        tstop_ms=1400.0,
        v_init_mV=passive["e_pas_mV"],
    )
    metrics = analyse_trace(trace, amplitude_nA=-0.005, delay_ms=200.0, duration_ms=1000.0)
    capacitance = cell.capacitance_pf()
    result = {
        "passive": passive,
        "metrics": {
            "rmp_mV": metrics["rmp_mV"],
            "rin_MOhm": metrics["rin_MOhm"],
            "tau_ms": metrics["tau_ms"],
            "whole_cell_capacitance_pF": capacitance,
            "post_step_recovery_error_mV": metrics["post_step_recovery_error_mV"],
        },
    }
    result["score_z2"] = score_candidate(
        rmp_mV=float(metrics["rmp_mV"]),
        rin_MOhm=float(metrics["rin_MOhm"]),
        capacitance_pF=capacitance,
    )
    return result, trace


def write_figure(
    *,
    output_path: Path,
    best: dict[str, Any],
    trace: dict[str, list[float]],
) -> None:
    """Plot the best passive trace and target comparisons.

    Args:
        output_path: Destination PNG.
        best: Best candidate result.
        trace: Best candidate trace.

    Returns:
        None.

    Example:
        ``write_figure(output_path=path, best=result, trace=trace)``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    axes[0].plot(trace["time_ms"], trace["voltage_mV"], color="#2563eb", linewidth=1.0)
    axes[0].axvspan(200, 1200, color="#93c5fd", alpha=0.2, label="-5 pA")
    axes[0].set(title="Best passive response", xlabel="Time (ms)", ylabel="Soma Vm (mV)")
    axes[0].legend(frameon=False)
    metrics = best["metrics"]
    names = ("RMP", "Rin", "Capacitance")
    model = (
        metrics["rmp_mV"],
        metrics["rin_MOhm"],
        metrics["whole_cell_capacitance_pF"],
    )
    target = (TARGETS["rmp_mV"]["mean"], TARGETS["rin_MOhm"]["mean"], TARGETS["whole_cell_capacitance_pF"]["mean"])
    sd = (TARGETS["rmp_mV"]["sd"], TARGETS["rin_MOhm"]["sd"], TARGETS["whole_cell_capacitance_pF"]["sd"])
    z_values = [(value - mean)/spread for value, mean, spread in zip(model, target, sd)]
    bars = axes[1].bar(names, z_values, color=("#0f766e", "#7c3aed", "#d97706"))
    axes[1].axhspan(-1, 1, color="#dcfce7", alpha=0.7, label="population mean +/- 1 SD")
    axes[1].axhline(0, color="#111827", linewidth=0.8)
    axes[1].set(title="Model deviation from NPFF-targeted population", ylabel="Z score")
    axes[1].legend(frameon=False, fontsize=8)
    for bar, value in zip(bars, model):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height(), f" {value:.2f}", ha="center", va="bottom", fontsize=8)
    figure.suptitle("NMO_260150 passive validation - room-temperature reference proxy")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, facecolor="white")
    plt.close(figure)


def build_parser() -> argparse.ArgumentParser:
    """Build the passive-fit command-line parser.

    Args:
        None.

    Returns:
        Configured parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Fit passive NMO_260150 parameters with <=173 simulations.")
    parser.add_argument("--dry-run", action="store_true", help="Print the bounded search plan without importing NEURON.")
    parser.add_argument("--dt-ms", type=float, default=0.025, help="Fixed integration step; default 0.025 ms.")
    return parser


def main() -> int:
    """Fit passive parameters and write parameters, validation JSON, and one figure.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python fit_passive.py``
    """

    args = build_parser().parse_args()
    cell_dir = Path(__file__).resolve().parent.parent
    plan = {
        "coarse_candidate_count": len(coarse_candidates()),
        "maximum_local_candidate_count": 45,
        "maximum_total_simulations": 173,
        "targets": TARGETS,
        "temperature_C": 23.0,
        "temperature_label": "operational room-temperature proxy; not a reported chamber temperature",
        "diameter_policy": "fixed standardized SWC radius profile treated as model-defined; not tuned",
    }
    print(json.dumps(plan, indent=2))
    if args.dry_run or not neuron_available():
        if not neuron_available():
            print("NEURON is unavailable; completed dry-run only.")
        return 0

    import neuron
    from neuron import h

    h.load_file("stdrun.hoc")
    h.celsius = 23.0
    h.cvode_active(0)
    swc = cell_dir / "morphology" / "NMO_260150_100521A-S14_set5_cell11_standardized.CNG.swc"
    cell = ECRCell(h, morphology_path=swc, passive=coarse_candidates()[0])
    evaluated: list[dict[str, Any]] = []
    best_trace: dict[str, list[float]] | None = None
    for candidate in coarse_candidates():
        result, trace = evaluate_candidate(h, cell=cell, passive=candidate, dt_ms=args.dt_ms)
        evaluated.append(result)
        if best_trace is None or result["score_z2"] < min(row["score_z2"] for row in evaluated[:-1]):
            best_trace = trace
    coarse_best = min(evaluated, key=lambda row: row["score_z2"])
    for candidate in local_candidates(coarse_best["passive"]):
        result, trace = evaluate_candidate(h, cell=cell, passive=candidate, dt_ms=args.dt_ms)
        evaluated.append(result)
        if result["score_z2"] < min(row["score_z2"] for row in evaluated[:-1]):
            best_trace = trace
    best = min(evaluated, key=lambda row: row["score_z2"])
    best_result, best_trace = evaluate_candidate(
        h,
        cell=cell,
        passive=best["passive"],
        dt_ms=args.dt_ms,
    )
    validation = {
        "identity_statement": "NPFF-targeted / GRPR-excluded population constraints applied to exact NMO_260150 morphology only",
        "source_condition": "room-temperature experimental reference; chamber temperature not numerically reported",
        "operational_reference_temperature_C": 23.0,
        "targets": TARGETS,
        "search": {
            "coarse_count": len(coarse_candidates()),
            "local_count": len(local_candidates(coarse_best["passive"])),
            "evaluated_count": len(evaluated),
            "top_10": sorted(evaluated, key=lambda row: row["score_z2"])[:10],
        },
        "best": best_result,
        "morphology_inventory": cell.inventory(),
        "interpretation": {
            "rmp_rin_priority": "RMP and Rin prioritized over capacitance",
            "capacitance_policy": "cm was not allowed below 0.5 uF/cm2; remaining mismatch is preserved",
            "diameter_policy": "standardized SWC profile fixed and classified as model-defined",
        },
    }
    parameter_payload = {
        "model": "NMO_260150 passive native soma+dendrite",
        "status": "passive-stage fitted model parameter set",
        "passive": best_result["passive"],
        "temperature_C": 23.0,
        "temperature_evidence": "operational room-temperature proxy, not an experimental chamber value",
        "d_lambda": 0.1,
        "frequency_Hz": 100.0,
        "dt_ms": args.dt_ms,
        "diameter_scale": 1.0,
        "diameter_status": "model-defined standardized profile; NeuroMorpho metadata says No Diameter",
        "experimental_targets": TARGETS,
        "evidence_category": "NPFFCre-targeted / GRPRFlp-excluded population",
    }
    write_json(cell_dir / "parameters" / "passive_final.json", parameter_payload)
    write_json(cell_dir / "results" / "passive_validation.json", validation)
    write_figure(output_path=cell_dir / "figures" / "passive_validation.png", best=best_result, trace=best_trace)
    print(json.dumps({"evaluated": len(evaluated), "best": best_result}, indent=2))
    cell.delete()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
