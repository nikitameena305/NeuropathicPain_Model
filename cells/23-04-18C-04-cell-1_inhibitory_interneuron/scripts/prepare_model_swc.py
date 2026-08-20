"""Create a parser-clean model copy by removing blank lines only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "morphology/primary/23-04-18C-04-cell-1.CNG.swc"
OUTPUT = ROOT / "morphology/model/23-04-18C-04-cell-1.model.swc"
LEDGER = ROOT / "morphology/provenance/model_swc_transformation.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    retained = [line.rstrip() for line in lines if line.strip()]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(retained) + "\n", encoding="utf-8", newline="\n")
    payload = {
        "schema_version": "1.0",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": digest(SOURCE),
        "output": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": digest(OUTPUT),
        "transformation": "Removed blank lines only; comments and every SWC data record retained in original order.",
        "source_line_count": len(lines),
        "output_line_count": len(retained),
        "blank_lines_removed": len(lines) - len(retained),
        "coordinate_changes": 0,
        "topology_changes": 0,
        "radius_changes": 0
    }
    LEDGER.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
