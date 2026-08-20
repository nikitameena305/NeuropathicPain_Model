"""Coarse, fully retained fit of the minimal Na/KDR/leak active model."""

from __future__ import annotations

import copy
import csv
import itertools
import json
from pathlib import Path

from pv_cell import PVCell, ROOT, action_potential_metrics, firing_metrics, load_config, run_step, save_json


TARGETS = {
    "rheobase_pa": (77.0, 7.0),
    "threshold_mv": (-34.9, 1.3),
    "amplitude_mv": (44.8, 1.6),
    "half_width_ms": (1.4, 0.1),
    "ahp_relative_threshold_mv": (-17.6, 1.6),
}
SEARCH_CURRENTS_NA = [0.0, 0.04, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15, 0.20]


def candidate_configs(base: dict) -> list[tuple[str, dict]]:
    output = [("inherited_density_control", copy.deepcopy(base))]
    for soma_na, ais_na, ais_kdr in itertools.product(
        [0.002, 0.006], [0.05, 0.10, 0.20, 0.40], [0.03, 0.06]
    ):
        config = copy.deepcopy(base)
        density = config["active"]["conductance_s_cm2"]
        density["soma"] = {"na": soma_na, "kdr": 0.003}
        density["dendrite"] = {"na": 0.0, "kdr": 0.002}
        density["ais_proxy"] = {"na": ais_na, "kdr": ais_kdr}
        density["distal_axon"] = {"na": 0.02, "kdr": 0.01}
        name = f"sna_{soma_na:g}_aisna_{ais_na:g}_aisk_{ais_kdr:g}"
        output.append((name, config))
    return output


def evaluate(name: str, config: dict) -> tuple[dict, dict | None]:
    cell = PVCell(config)
    rheobase = None
    rheobase_trace = None
    for current in SEARCH_CURRENTS_NA:
        trace = run_step(cell, current, duration_ms=300.0)
        if firing_metrics(trace, config)["spike_count"]:
            rheobase = current
            rheobase_trace = trace
            break
    ap = action_potential_metrics(rheobase_trace, config) if rheobase_trace is not None else {"available": False}
    if rheobase is None or not ap["available"]:
        row = {"candidate": name, "rheobase_na": None, "score": 1e6, "spikes_at_2x": 0, "tonic_persistence_at_2x": 0.0}
    else:
        full = run_step(cell, min(0.4, 2.0 * rheobase))
        firing = firing_metrics(full, config)
        score = (
            abs(rheobase * 1000.0 - TARGETS["rheobase_pa"][0]) / TARGETS["rheobase_pa"][1]
            + 0.35 * abs(ap["threshold_mv_dvdt_20_v_s"] - TARGETS["threshold_mv"][0]) / TARGETS["threshold_mv"][1]
            + 0.20 * abs(ap["amplitude_peak_minus_threshold_mv"] - TARGETS["amplitude_mv"][0]) / TARGETS["amplitude_mv"][1]
            + 0.20 * abs(ap["half_width_ms"] - TARGETS["half_width_ms"][0]) / TARGETS["half_width_ms"][1]
            + 3.0 * max(0.0, 0.8 - firing["tonic_persistence_fraction"])
        )
        row = {
            "candidate": name,
            "soma_na_s_cm2": config["active"]["conductance_s_cm2"]["soma"]["na"],
            "soma_kdr_s_cm2": config["active"]["conductance_s_cm2"]["soma"]["kdr"],
            "dendrite_na_s_cm2": config["active"]["conductance_s_cm2"]["dendrite"]["na"],
            "dendrite_kdr_s_cm2": config["active"]["conductance_s_cm2"]["dendrite"]["kdr"],
            "ais_na_s_cm2": config["active"]["conductance_s_cm2"]["ais_proxy"]["na"],
            "ais_kdr_s_cm2": config["active"]["conductance_s_cm2"]["ais_proxy"]["kdr"],
            "distal_axon_na_s_cm2": config["active"]["conductance_s_cm2"]["distal_axon"]["na"],
            "distal_axon_kdr_s_cm2": config["active"]["conductance_s_cm2"]["distal_axon"]["kdr"],
            "rheobase_na": rheobase,
            "threshold_mv": ap["threshold_mv_dvdt_20_v_s"],
            "peak_mv": ap["peak_mv"],
            "amplitude_mv": ap["amplitude_peak_minus_threshold_mv"],
            "half_width_ms": ap["half_width_ms"],
            "ahp_relative_threshold_mv": ap["ahp_relative_to_threshold_mv"],
            "spikes_at_2x": firing["spike_count"],
            "frequency_hz_at_2x": firing["frequency_hz"],
            "tonic_persistence_at_2x": firing["tonic_persistence_fraction"],
            "adaptation_at_2x": firing["adaptation_ratio_last_over_first"],
            "score": score,
        }
    cell.dispose()
    return row, config if rheobase is not None else None


def main() -> None:
    base = load_config(ROOT / "parameters/active/active_initial_l571_kinetics.json")
    output_dir = ROOT / "results/active/search"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    best = None
    for name, config in candidate_configs(base):
        row, viable = evaluate(name, config)
        rows.append(row)
        if viable is not None and (best is None or row["score"] < best[0]):
            best = (row["score"], row, viable)
        print(name, row.get("rheobase_na"), row["score"])
    keys = sorted({key for row in rows for key in row})
    with (output_dir / "active_fit_grid.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    if best is None:
        raise RuntimeError("No candidate produced a spike by 200 pA")
    _, row, config = best
    config["status"] = "coarse_fit_selected"
    config["fit_selection"] = {
        "source_grid": "results/active/search/active_fit_grid.csv",
        "candidate": row["candidate"],
        "score": row["score"],
        "caution": "Population AP means are comparison targets; selected kinetics are model-derived and not cell-specific measurements."
    }
    save_json(config, ROOT / "parameters/active/active_selected_parameters.json")
    save_json({"selected_row": row, "targets": TARGETS}, output_dir / "active_fit_selection.json")
    print(json.dumps({"selected": row}, indent=2))


if __name__ == "__main__":
    main()
