"""Construct NetPyNE parameters for isolated excitatory populations."""

from pathlib import Path
from typing import Any

from .catalog import counts_for_mode, load_population_specs
from .cell_rules import build_cell_rules


def describe_network(
    *,
    mode: str,
    stim_amp: float,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Describe a planned build without importing NEURON or NetPyNE.

    Args:
        mode: Exemplar, smoke, or production population size mode.
        stim_amp: Common somatic current step in nA.
        config_path: Optional replacement population catalog.

    Returns:
        JSON-serializable population and mechanism summary.

    Example:
        `summary = describe_network(mode="smoke", stim_amp=0.2)`
    """
    counts = counts_for_mode(mode=mode, config_path=config_path)
    specs = load_population_specs(config_path=config_path)
    return {
        "mode": mode,
        "total_cells": sum(counts.values()),
        "counts": counts,
        "base_rules": {spec.cell_type: spec.base_rule for spec in specs},
        "stimulus": {
            "type": "IClamp",
            "delay_ms": 100.0,
            "duration_ms": 500.0,
            "amplitude_nA": stim_amp,
        },
        "required_mod_files": [
            "B_NA.mod",
            "HH2.mod",
            "KDRI.mod",
            "borgka.mod",
            "iKCa.mod",
            "CaIntraCellDyn.mod",
        ],
    }


def build_netparams(
    *,
    mode: str,
    stim_amp: float = 0.2,
    config_path: Path | None = None,
) -> Any:
    """Build NetPyNE cell, population, and stimulation parameters.

    Args:
        mode: Exemplar, smoke, or production population size mode.
        stim_amp: Common somatic current step in nA.
        config_path: Optional replacement population catalog.

    Returns:
        A populated `netpyne.specs.NetParams` object.

    Example:
        `net_params = build_netparams(mode="exemplar", stim_amp=0.2)`
    """
    from netpyne import specs

    net_params = specs.NetParams()
    net_params.defaultThreshold = -30.0

    for label, rule in build_cell_rules(config_path=config_path).items():
        net_params.cellParams[label] = rule

    counts = counts_for_mode(mode=mode, config_path=config_path)
    for spec in load_population_specs(config_path=config_path):
        net_params.popParams[spec.cell_type] = {
            "cellType": spec.cell_type,
            "numCells": counts[spec.cell_type],
        }

    net_params.stimSourceParams["somatic_step"] = {
        "type": "IClamp",
        "del": 100.0,
        "dur": 500.0,
        "amp": float(stim_amp),
    }
    for spec in load_population_specs(config_path=config_path):
        net_params.stimTargetParams[f"somatic_step_to_{spec.cell_type}"] = {
            "source": "somatic_step",
            "conds": {"pop": spec.cell_type},
            "sec": "soma",
            "loc": 0.5,
        }

    return net_params
