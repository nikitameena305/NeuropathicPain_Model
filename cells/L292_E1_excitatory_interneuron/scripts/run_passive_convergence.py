"""Run an isolated fixed-step and d-lambda convergence matrix."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _label(value: float) -> str:
    """Return a deterministic filesystem-safe floating-point label."""

    return f"{value:g}".replace("-", "m").replace(".", "p")


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description="Run passive numerical convergence for L292-E1-LCN.")
    parser.add_argument("--config", type=Path, required=True, help="Validated passive-candidate JSON configuration.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for all convergence runs.")
    return parser


def main() -> int:
    """Run every matrix point in a fresh NEURON process and aggregate results."""

    args = _build_parser().parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    convergence = config["numerical_convergence"]
    dt_values = [float(value) for value in convergence["dt_ms"]]
    d_lambda_values = [float(value) for value in convergence["d_lambda"]]
    current_nA = float(convergence["current_nA"])
    baseline_dt = float(convergence["baseline"]["dt_ms"])
    baseline_d_lambda = float(convergence["baseline"]["d_lambda"])
    relative_tolerance = float(convergence["relative_tolerance_fraction"])
    rmp_tolerance = float(convergence["rmp_absolute_tolerance_mV"])
    project_dir = config_path.parents[2]
    validator = project_dir / "scripts" / "validate_single_cell.py"
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty convergence directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for dt_ms in dt_values:
        for d_lambda in d_lambda_values:
            run_dir = output_dir / f"dt_{_label(dt_ms)}__dlambda_{_label(d_lambda)}"
            command = [
                sys.executable,
                str(validator),
                "--config",
                str(config_path),
                "--output-dir",
                str(run_dir),
                "--passive-only",
                "--dt-ms",
                str(dt_ms),
                "--d-lambda",
                str(d_lambda),
                "--current-steps-nA",
                str(current_nA),
                "0.0",
            ]
            print(f"RUN dt={dt_ms:g} ms d_lambda={d_lambda:g}", flush=True)
            subprocess.run(command, cwd=project_dir, check=True)
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            passive = summary["passive_reference"]
            zero = next(row for row in summary["per_current"] if row["amplitude_nA"] == 0.0)
            rows.append(
                {
                    "dt_ms": dt_ms,
                    "d_lambda": d_lambda,
                    "rmp_mV": float(zero["rmp_mV"]),
                    "rin_MOhm": float(passive["rin_MOhm"]),
                    "tau_ms": float(passive["tau_ms"]),
                    "capacitance_pF": float(passive["input_capacitance_pF"]),
                    "recovery_error_mV": float(passive["post_step_recovery_error_mV"]),
                    "section_count": int(summary["morphology"]["section_count"]),
                    "total_nseg": int(summary["morphology"]["total_nseg"]),
                    "stage_gate_passed": bool(summary["assessment"]["all_executed_gates_pass"]),
                    "result_directory": str(run_dir.relative_to(project_dir)),
                }
            )

    baseline = next(
        row
        for row in rows
        if row["dt_ms"] == baseline_dt and row["d_lambda"] == baseline_d_lambda
    )
    for row in rows:
        row["rin_relative_delta"] = (row["rin_MOhm"] - baseline["rin_MOhm"]) / baseline["rin_MOhm"]
        row["tau_relative_delta"] = (row["tau_ms"] - baseline["tau_ms"]) / baseline["tau_ms"]
        row["rmp_delta_mV"] = row["rmp_mV"] - baseline["rmp_mV"]
        row["convergence_pass"] = bool(
            abs(row["rin_relative_delta"]) <= relative_tolerance
            and abs(row["tau_relative_delta"]) <= relative_tolerance
            and abs(row["rmp_delta_mV"]) <= rmp_tolerance
            and row["stage_gate_passed"]
        )

    fieldnames = list(rows[0])
    with (output_dir / "convergence.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    aggregate = {
        "criterion": convergence,
        "baseline": baseline,
        "rows": rows,
        "all_convergence_checks_pass": all(row["convergence_pass"] for row in rows),
    }
    (output_dir / "convergence.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"all_convergence_checks_pass": aggregate["all_convergence_checks_pass"]}, indent=2))
    return 0 if aggregate["all_convergence_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
