"""Targeted active search after the documented coarse and refinement sweeps."""

from __future__ import annotations

import copy
import csv
import json

from fit_active import TARGETS, evaluate
from pv_cell import ROOT, load_config, save_json


CANDIDATES = [
    (0.08, 0.008, 0.0015, 0.020),
    (0.08, 0.010, 0.0015, 0.030),
    (0.10, 0.008, 0.0015, 0.030),
    (0.10, 0.010, 0.0015, 0.030),
    (0.10, 0.012, 0.0020, 0.040),
    (0.12, 0.008, 0.0015, 0.030),
    (0.12, 0.010, 0.0020, 0.040),
    (0.12, 0.012, 0.0020, 0.050),
    (0.15, 0.006, 0.0015, 0.030),
    (0.15, 0.008, 0.0020, 0.040),
    (0.15, 0.010, 0.0020, 0.050),
    (0.18, 0.006, 0.0020, 0.040),
]


def main() -> None:
    base = load_config(ROOT / "parameters/active/active_initial_l571_kinetics.json")
    rows = []
    best = None
    for ais_na, soma_na, soma_kdr, ais_kdr in CANDIDATES:
        config = copy.deepcopy(base)
        density = config["active"]["conductance_s_cm2"]
        density["soma"] = {"na": soma_na, "kdr": soma_kdr}
        density["dendrite"] = {"na": 0.0, "kdr": 0.0}
        density["ais_proxy"] = {"na": ais_na, "kdr": ais_kdr}
        density["distal_axon"] = {"na": 0.015, "kdr": 0.005}
        name = f"aisna_{ais_na:g}_sna_{soma_na:g}_sk_{soma_kdr:g}_aisk_{ais_kdr:g}"
        row, viable = evaluate(name, config)
        rows.append(row)
        if viable is not None and (best is None or row["score"] < best[0]):
            best = (row["score"], row, viable)
        print(name, row.get("rheobase_na"), row["score"])
    output = ROOT / "results/active/search"
    keys = sorted({key for row in rows for key in row})
    with (output / "active_targeted_grid.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    if best is None:
        raise RuntimeError("Targeted search produced no viable candidate")
    _, row, config = best
    config["status"] = "active_fit_selected"
    config["fit_selection"] = {
        "coarse_grid": "results/active/search/active_fit_grid.csv",
        "refinement_grid": "results/active/search/active_refinement_grid.csv",
        "targeted_grid": "results/active/search/active_targeted_grid.csv",
        "candidate": row["candidate"],
        "score": row["score"],
        "rheobase_resolution": "10-20 pA search grid, matching the 20-pA experimental increment scale",
        "target_scope": "same-population adult mouse PV means; not exact-cell electrophysiology",
        "minimal_mechanism_constraint": "leak + fast Na + delayed-rectifier K only"
    }
    save_json(config, ROOT / "parameters/active/active_selected_parameters.json")
    save_json({"selected_row": row, "targets": TARGETS}, output / "active_targeted_selection.json")
    print(json.dumps({"selected": row}, indent=2))


if __name__ == "__main__":
    main()
