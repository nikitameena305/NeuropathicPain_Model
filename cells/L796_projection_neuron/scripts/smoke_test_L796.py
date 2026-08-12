#!/usr/bin/env python3
"""Run a lightweight L796 morphology/parameter/current-clamp smoke test."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


CELL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CELL_ROOT.parents[1]


def parse_args() -> argparse.Namespace:
    """Parse smoke-test options.

    Returns:
        Parsed command-line namespace.

    Example:
        ``args = parse_args()``
    """
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="Import NEURON and execute the clamp.")
    mode.add_argument("--dry-run", action="store_true", help="Check paths without importing NEURON.")
    parser.add_argument("--current", type=float, default=0.04, help="Somatic current in nA.")
    return parser.parse_args()


def load_finish_module(script: Path):
    """Load the retained finalization model as a module.

    Args:
        script: Path to `13_finish_L796.py`.

    Returns:
        Imported module object.

    Example:
        ``module = load_finish_module(Path('13_finish_L796.py'))``
    """
    spec = importlib.util.spec_from_file_location("l796_finish_smoke", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """Validate inputs and optionally execute one deterministic clamp.

    Returns:
        Process status code.

    Example:
        ``raise SystemExit(main())``
    """
    args = parse_args()
    morphology = CELL_ROOT / "morphology/L796-ALT-PN.CNG.swc"
    parameters = CELL_ROOT / "parameters/L796_final_parameter_set.json"
    model_script = CELL_ROOT / "scripts/13_finish_L796.py"
    for path in (morphology, parameters, model_script):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)
    config = json.loads(parameters.read_text(encoding="utf-8"))
    plan = {
        "cell": "L796-ALT-PN",
        "morphology": str(morphology),
        "parameters": str(parameters),
        "temperature_C": 6.3,
        "current_nA": args.current,
        "mode": "run" if args.run else "dry-run",
    }
    if not args.run:
        print(json.dumps(plan, indent=2))
        return 0

    from neuron import load_mechanisms

    mechanism_dir = REPOSITORY_ROOT / "shared/mechanisms/medlock_267056"
    load_mechanisms(str(mechanism_dir))
    model = load_finish_module(model_script)
    model.h.celsius = 6.3
    soma, ais, groups, first_order = model.build_model()
    active = config["tuned_active_scales"]
    selected = {
        "soma_BNa": float(config["soma_BNa_S_per_cm2"]),
        "KDR_scale": float(active["KDR_scale"]),
    }
    model.set_conductance_scales(ais, groups, first_order, selected)
    time_ms, soma_mv = model.run_current_step(soma, args.current)
    spikes = model.count_spikes(time_ms, soma_mv)
    result = {
        **plan,
        "samples": int(time_ms.size),
        "sections": int(sum(1 for _section in model.h.allsec())),
        "spikes": int(len(spikes)),
        "completed": bool(time_ms.size and time_ms[-1] >= model.TSTOP),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
