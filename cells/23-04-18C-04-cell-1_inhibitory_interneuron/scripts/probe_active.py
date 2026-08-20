"""Run a concise deterministic active probe for a candidate configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pv_cell import PVCell, ROOT, action_potential_metrics, firing_metrics, load_config, passive_metrics, run_step


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "parameters/active/active_initial_l571_kinetics.json")
    args = parser.parse_args()
    config = load_config(args.config)
    cell = PVCell(config)
    rows = []
    first = None
    first_trace = None
    for index in range(0, 41):
        current = index * 0.005
        trace = run_step(cell, current)
        metric = firing_metrics(trace, config)
        rows.append(metric)
        if first is None and metric["spike_count"]:
            first = current
            first_trace = trace
            break
    representative_current = min(0.4, (first or 0.1) * 2.0)
    representative = run_step(cell, representative_current)
    zero = run_step(cell, 0.0)
    negative = run_step(cell, -0.02)
    result = {
        "config": str(args.config),
        "inventory": cell.inventory(),
        "active_baseline_mv": float(zero.soma_mv[-400:].mean()),
        "active_rin": passive_metrics(negative, config),
        "rheobase_na_5pa_resolution": first,
        "rheobase_ap": action_potential_metrics(first_trace, config) if first_trace is not None else {"available": False},
        "representative_current_na": representative_current,
        "representative_firing": firing_metrics(representative, config),
        "representative_ap": action_potential_metrics(representative, config),
        "tested_until_rheobase": rows
    }
    cell.dispose()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
