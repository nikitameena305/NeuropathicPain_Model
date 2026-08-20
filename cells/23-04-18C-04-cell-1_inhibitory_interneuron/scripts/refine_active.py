"""Refine Cell 1 densities around the viable minimal-model region."""

from __future__ import annotations

import copy
import csv
import itertools
import json

from fit_active import TARGETS, evaluate
from pv_cell import ROOT, load_config, save_json


def main() -> None:
    base = load_config(ROOT / "parameters/active/active_initial_l571_kinetics.json")
    rows = []
    best = None
    combinations = itertools.product(
        [0.25, 0.30, 0.35],
        [0.008, 0.014, 0.020],
        [0.001, 0.002],
        [0.012, 0.020],
    )
    for ais_na, soma_na, soma_kdr, ais_kdr in combinations:
        config = copy.deepcopy(base)
        density = config["active"]["conductance_s_cm2"]
        density["soma"] = {"na": soma_na, "kdr": soma_kdr}
        density["dendrite"] = {"na": 0.0, "kdr": 0.0}
        density["ais_proxy"] = {"na": ais_na, "kdr": ais_kdr}
        density["distal_axon"] = {"na": 0.02, "kdr": 0.005}
        name = f"aisna_{ais_na:g}_sna_{soma_na:g}_sk_{soma_kdr:g}_aisk_{ais_kdr:g}"
        row, viable = evaluate(name, config)
        rows.append(row)
        if viable is not None and (best is None or row["score"] < best[0]):
            best = (row["score"], row, viable)
        print(name, row.get("rheobase_na"), row["score"])
    output = ROOT / "results/active/search"
    keys = sorted({key for row in rows for key in row})
    with (output / "active_refinement_grid.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    if best is None:
        raise RuntimeError("Refinement produced no viable candidate")
    _, row, config = best
    config["status"] = "active_fit_selected"
    config["fit_selection"] = {
        "coarse_grid": "results/active/search/active_fit_grid.csv",
        "refinement_grid": "results/active/search/active_refinement_grid.csv",
        "candidate": row["candidate"],
        "score": row["score"],
        "target_scope": "same-population adult mouse PV means; not exact-cell electrophysiology",
        "minimal_mechanism_constraint": "leak + fast Na + delayed-rectifier K only"
    }
    save_json(config, ROOT / "parameters/active/active_selected_parameters.json")
    save_json({"selected_row": row, "targets": TARGETS}, output / "active_refinement_selection.json")
    print(json.dumps({"selected": row}, indent=2))


if __name__ == "__main__":
    main()
