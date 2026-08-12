"""Probe runtime temperature behavior of the staged intrinsic mechanisms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _serialise(value: Any) -> Any:
    """Convert a NEURON scalar or array-like value to JSON data."""

    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return str(value)


def _selected(mechanism: Any, names: list[str]) -> dict[str, Any]:
    """Read named mechanism variables that are available at runtime."""

    result: dict[str, Any] = {}
    for name in names:
        if hasattr(mechanism, name):
            result[name] = _serialise(getattr(mechanism, name))
    return result


def main() -> int:
    """Run deterministic gate/tau probes without a current-clamp experiment."""

    parser = argparse.ArgumentParser(description="Probe 23/35 C mechanism runtime values.")
    parser.add_argument("--mechanism-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import neuron
    from neuron import h

    neuron.load_mechanisms(str(args.mechanism_dir.resolve()))
    h.load_file("stdrun.hoc")
    h.dt = 0.025
    h.steps_per_ms = 40.0
    h.cvode_active(0)
    section = h.Section(name="temperature_probe")
    section.L = 20.0
    section.diam = 20.0
    for name in ("B_Na", "HH2", "KDRI", "borgka", "iKCa"):
        section.insert(name)
    segment = section(0.5)
    segment.ena = 50.0
    segment.ek = -70.0
    segment.cai = 5e-05
    segment.B_Na.gnabar = 0.0
    segment.HH2.gnabar = 0.0
    segment.HH2.gkbar = 0.0
    segment.KDRI.gkbar = 0.0
    segment.borgka.gkabar = 0.0
    segment.iKCa.gbar = 0.0

    variables = {
        "B_Na": ["inf", "tau", "tadj", "tau_factor", "alpha_shift", "beta_shift"],
        "HH2": ["m_inf", "h_inf", "n_inf", "tau_m", "tau_h", "tau_n", "m_exp", "h_exp", "n_exp"],
        "KDRI": ["n", "h"],
        "borgka": ["n", "l", "ninf", "linf", "taun", "taul"],
        "iKCa": ["m", "m_inf", "tau_m"],
    }

    snapshots: dict[str, Any] = {}
    for temperature in (23.0, 35.0):
        h.celsius = temperature
        h.finitialize(-40.0)
        snapshots[str(int(temperature))] = {
            name: _selected(getattr(segment, name), selected_names)
            for name, selected_names in variables.items()
        }

    h.celsius = 23.0
    segment.B_Na.alpha_shift = 0.0
    segment.B_Na.beta_shift = 0.0
    segment.B_Na.tau_factor = 1.0
    h.finitialize(-40.0)
    bna_table_baseline = _selected(segment.B_Na, ["inf", "tau", "tadj"])
    segment.B_Na.alpha_shift = 10.0
    segment.B_Na.beta_shift = 10.0
    segment.B_Na.tau_factor = 2.0
    h.finitialize(-40.0)
    bna_table_after_range_change = _selected(segment.B_Na, ["inf", "tau", "tadj"])
    original_usetable = int(h.usetable_B_Na)
    h.usetable_B_Na = 0
    h.finitialize(-40.0)
    bna_direct_after_range_change = _selected(segment.B_Na, ["inf", "tau", "tadj"])
    h.usetable_B_Na = original_usetable

    kdri_step: dict[str, Any] = {}
    for temperature in (23.0, 35.0):
        h.celsius = temperature
        h.finitialize(-65.0)
        before = _selected(segment.KDRI, ["n", "h"])
        segment.v = -40.0
        h.fadvance()
        after = _selected(segment.KDRI, ["n", "h"])
        kdri_step[str(int(temperature))] = {"before": before, "after_one_0p025ms_step_at_minus40mV": after}

    result = {
        "software": {"neuron": neuron.__version__},
        "probe_voltage_mV": -40.0,
        "dt_ms": 0.025,
        "temperature_snapshots": snapshots,
        "B_Na_TABLE_parameter_dependency_probe": {
            "usetable_default": original_usetable,
            "baseline": bna_table_baseline,
            "after_RANGE_change_with_TABLE": bna_table_after_range_change,
            "after_RANGE_change_without_TABLE": bna_direct_after_range_change,
        },
        "KDRI_one_step_probe": kdri_step,
        "interpretation_note": "This diagnostic verifies code behavior; it does not supply missing biological Q10 values.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
