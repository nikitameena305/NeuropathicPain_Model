"""Command-line runner with a dependency-free dry-run mode."""

import argparse
from importlib.util import find_spec
import json
from pathlib import Path
from typing import Sequence

from .catalog import VALID_MODES
from .netparams import build_netparams, describe_network
from .sim_config import build_sim_config


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for the population runner.

    Args:
        argv: Optional argument sequence; defaults to process arguments.

    Returns:
        Parsed command-line options.

    Example:
        `args = parse_args(["--dry-run", "--mode", "smoke"])`
    """
    parser = argparse.ArgumentParser(
        description="Run six SDH excitatory interneuron populations."
    )
    parser.add_argument("--mode", choices=VALID_MODES, default="exemplar")
    parser.add_argument(
        "--stim-amp",
        type=float,
        default=0.2,
        help="Common somatic IClamp amplitude in nA.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Base directory for simulation outputs.",
    )
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned build without importing NEURON.",
    )
    execution.add_argument(
        "--run",
        action="store_true",
        help="Require a real NEURON/NetPyNE simulation.",
    )
    return parser.parse_args(argv)


def dependencies_available() -> bool:
    """Check whether NEURON and NetPyNE can be imported.

    Args:
        None.

    Returns:
        True when both required packages are discoverable.

    Example:
        `available = dependencies_available()`
    """
    return find_spec("neuron") is not None and find_spec("netpyne") is not None


def use_dry_run(*, args: argparse.Namespace) -> bool:
    """Resolve explicit and automatic dry-run behavior.

    Args:
        args: Parsed command-line arguments.

    Returns:
        True when the command should avoid NEURON imports.

    Example:
        `dry_run = use_dry_run(args=parse_args(["--dry-run"]))`
    """
    if args.dry_run:
        return True
    if args.run:
        if not dependencies_available():
            raise RuntimeError(
                "--run was requested but NEURON/NetPyNE are unavailable."
            )
        return False
    return not dependencies_available()


def load_mechanisms() -> None:
    """Load mechanisms compiled in the repository root when needed.

    Args:
        None.

    Returns:
        None.

    Example:
        `load_mechanisms()`
    """
    from neuron import h
    from neuron import load_mechanisms as neuron_load_mechanisms

    probe = h.Section(name="sdh_exc_mechanism_probe")
    try:
        probe.insert("B_Na")
        return
    except (ValueError, RuntimeError):
        pass

    project_root = Path(__file__).resolve().parents[2]
    loaded = neuron_load_mechanisms(str(project_root))
    if not loaded:
        raise RuntimeError(
            "Compiled mechanisms were not found. Run "
            "`CC=\"gcc -std=gnu17\" nrnivmodl mods` first."
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a dry-run description or a NetPyNE simulation.

    Args:
        argv: Optional command-line argument sequence.

    Returns:
        Process exit status; zero indicates success.

    Example:
        `main(["--dry-run", "--mode", "exemplar"])`
    """
    args = parse_args(argv)
    if use_dry_run(args=args):
        print(
            json.dumps(
                describe_network(mode=args.mode, stim_amp=args.stim_amp),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    load_mechanisms()
    from netpyne import sim

    output_dir = args.output_dir / args.mode
    output_dir.mkdir(parents=True, exist_ok=True)
    net_params = build_netparams(mode=args.mode, stim_amp=args.stim_amp)
    sim_config = build_sim_config(mode=args.mode, output_dir=output_dir)
    sim.createSimulateAnalyze(netParams=net_params, simConfig=sim_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
