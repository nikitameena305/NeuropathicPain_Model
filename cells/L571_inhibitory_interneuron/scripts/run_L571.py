#!/usr/bin/env python3
"""Run one deterministic current-step simulation of the L571-LCN model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from l571_model import (
    ROOT,
    L571Cell,
    action_potential_metrics,
    firing_metrics,
    load_config,
    passive_metrics,
    run_step,
    save_json,
    trace_to_dict,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Parsed argument namespace.

    Example:
        ``args = parse_args()``
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "parameters" / "L571_initial_23C.json",
        help="JSON model configuration.",
    )
    parser.add_argument("--current", type=float, default=0.02, help="Somatic current in nA.")
    parser.add_argument("--passive-only", action="store_true", help="Omit active channels.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned run without importing NEURON.",
    )
    return parser.parse_args()


def main() -> int:
    """Build, simulate, measure, and save one current step.

    Returns:
        Process status code.

    Example:
        ``raise SystemExit(main())``
    """

    args = parse_args()
    plan = {
        "config": str(args.config.resolve()),
        "current_na": args.current,
        "passive_only": args.passive_only,
        "output": str(args.output.resolve()) if args.output else None,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    config = load_config(path=args.config)
    cell = L571Cell(config=config, passive_only=args.passive_only)
    trace = run_step(cell, current_na=args.current)
    result = {
        "run": plan,
        "model": cell.summary(),
        "firing": firing_metrics(trace=trace, config=config),
        "action_potential": action_potential_metrics(trace=trace, config=config),
        "trace": trace_to_dict(trace=trace),
    }
    if args.current == 0:
        mask = trace.time_ms >= trace.time_ms[-1] - 100.0
        result["steady_zero_current_rmp_mv"] = float(trace.soma_mv[mask].mean())
    if args.current < 0:
        result["passive"] = passive_metrics(trace=trace, config=config)
    if args.output:
        save_json(value=result, path=args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "trace"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
