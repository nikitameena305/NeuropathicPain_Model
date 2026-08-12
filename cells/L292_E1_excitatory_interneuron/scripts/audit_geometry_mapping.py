"""Compare reconstructed active-region areas with Medlock's simplified cell."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

from rat_lcn import RatLCN_L292E1, load_model_config


def _area_um2(h: Any, segments: Iterable[Any]) -> float:
    """Sum NEURON segment membrane area in square micrometres."""

    return sum(float(h.area(segment.x, sec=segment.sec)) for segment in segments)


def main() -> int:
    """Build the mapped cell without advancing time and write the area audit."""

    parser = argparse.ArgumentParser(description="Audit Medlock-to-reconstruction region areas.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_model_config(args.config)
    project_dir = args.config.resolve().parents[2]

    import neuron
    from neuron import h

    mechanism_dir = (project_dir / config["mechanisms"]["directory"]).resolve()
    neuron.load_mechanisms(str(mechanism_dir))
    h.load_file("stdrun.hoc")
    h.celsius = float(config["simulation"]["celsius"])
    cell = RatLCN_L292E1(
        morphology_path=project_dir / config["morphology"]["path"],
        passive=config["passive"],
        discretization=config["discretization"],
        active=config["active"],
    )
    soma_segments = [segment for section in cell.soma_sections for segment in section]
    dendrite_segments = [segment for section in cell.dendrite_sections for segment in section]
    axon_segments = [segment for section in cell.axon_sections for segment in section]
    proximal_keys = {
        (segment.sec.name(), round(float(segment.x), 12))
        for segment in cell.proximal_axon_candidate_segments
    }
    distal_segments = [
        segment
        for segment in axon_segments
        if (segment.sec.name(), round(float(segment.x), 12)) not in proximal_keys
    ]
    reconstructed = {
        "soma": _area_um2(h, soma_segments),
        "dendrite": _area_um2(h, dendrite_segments),
        "proximal_axon_candidate": _area_um2(h, cell.proximal_axon_candidate_segments),
        "axon_distal": _area_um2(h, distal_segments),
    }
    medlock = {
        "soma": math.pi * 20.0 * 20.0,
        "dendrite": math.pi * 3.0 * 400.0,
        "proximal_axon_candidate": math.pi * 1.5 * 9.0,
    }
    ratios = {
        region: {
            "medlock_over_reconstructed_density_scale": medlock[region] / reconstructed[region],
            "reconstructed_over_medlock_area_ratio": reconstructed[region] / medlock[region],
        }
        for region in medlock
    }
    result = {
        "identity_note": "This is a geometry audit, not evidence that L292-E1-LCN has eTrC molecular identity.",
        "medlock_area_formula": "cylindrical lateral area = pi * diameter * length; end caps excluded as in cable sections",
        "medlock_area_um2": medlock,
        "reconstructed_area_um2": reconstructed,
        "area_ratios": ratios,
        "provisional_ais_segment_count": len(cell.proximal_axon_candidate_segments),
        "proposal_note": (
            "A region-wise Medlock/reconstructed area ratio can preserve each original compartment's total "
            "maximum conductance when mapping density to the reconstruction. This is a D-level computational "
            "proposal that requires active validation, not a source parameter."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
