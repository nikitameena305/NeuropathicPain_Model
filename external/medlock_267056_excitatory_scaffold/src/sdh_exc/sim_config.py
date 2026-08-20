"""Create deterministic NetPyNE simulation settings."""

from pathlib import Path
from typing import Any

from .catalog import load_population_specs


def build_sim_config(
    *,
    mode: str,
    output_dir: Path,
) -> Any:
    """Build the simulation and recording configuration.

    Args:
        mode: Exemplar, smoke, or production execution mode.
        output_dir: Directory in which NetPyNE writes results.

    Returns:
        A configured `netpyne.specs.SimConfig` object.

    Example:
        `cfg = build_sim_config(mode="smoke", output_dir=Path("results"))`
    """
    from netpyne import specs

    config = specs.SimConfig()
    config.duration = 5000.0 if mode == "production" else 800.0
    config.dt = 0.025
    config.recordStep = 0.025
    config.hParams = {"celsius": 36.0, "v_init": -60.0}

    config.seeds = {
        "conn": 1729,
        "stim": 2718,
        "loc": 3141,
    }
    config.recordCellsSpikes = -1
    config.recordCells = [
        (spec.cell_type, 0) for spec in load_population_specs()
    ]
    config.recordTraces["V_soma"] = {
        "sec": "soma",
        "loc": 0.5,
        "var": "v",
    }

    config.simLabel = f"sdh_exc_{mode}"
    config.saveFolder = str(output_dir)
    config.saveJson = True
    config.savePickle = False
    config.saveDataInclude = ["simData", "simConfig", "netParams"]

    config.analysis["plotRaster"] = {
        "include": ["allCells"],
        "orderBy": "pop",
        "popRates": True,
        "saveFig": True,
        "showFig": False,
    }
    config.analysis["plotTraces"] = {
        "include": config.recordCells,
        "saveFig": True,
        "showFig": False,
    }
    return config
