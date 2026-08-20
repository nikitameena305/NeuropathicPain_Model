"""Load and validate the configuration for six excitatory populations."""

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
from typing import Any


VALID_MODES = ("exemplar", "smoke", "production")


@dataclass(frozen=True)
class PopulationSpec:
    """Describe one configured SDH excitatory population."""

    cell_type: str
    display_name: str
    modeldb_label: str
    base_rule: str
    counts: dict[str, int]

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PopulationSpec":
        """Build a validated population specification.

        Args:
            payload: One population mapping loaded from the JSON catalog.

        Returns:
            An immutable population specification.

        Example:
            `PopulationSpec.from_mapping({"cell_type": "eTrC", ...})`
        """
        counts = {mode: int(payload["counts"][mode]) for mode in VALID_MODES}
        if any(value < 1 for value in counts.values()):
            raise ValueError("Every population count must be positive.")
        base_rule = str(payload["base_rule"])
        if base_rule not in {"initial", "delayed"}:
            raise ValueError(f"Unknown base rule: {base_rule}")
        return cls(
            cell_type=str(payload["cell_type"]),
            display_name=str(payload["display_name"]),
            modeldb_label=str(payload["modeldb_label"]),
            base_rule=base_rule,
            counts=counts,
        )


def load_population_specs(
    *,
    config_path: Path | None = None,
) -> tuple[PopulationSpec, ...]:
    """Load the six population definitions from JSON.

    Args:
        config_path: Optional replacement catalog path for testing or extension.

    Returns:
        Six population specifications in declared order.

    Example:
        `specs = load_population_specs()`
    """
    if config_path is None:
        resource = resources.files("sdh_exc").joinpath("data/populations.json")
        payload = json.loads(resource.read_text(encoding="utf-8"))
    else:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    specs = tuple(
        PopulationSpec.from_mapping(item) for item in payload["populations"]
    )
    cell_types = {spec.cell_type for spec in specs}
    if len(specs) != 6 or len(cell_types) != 6:
        raise ValueError("The catalog must contain six unique population types.")
    return specs


def counts_for_mode(
    *,
    mode: str,
    config_path: Path | None = None,
) -> dict[str, int]:
    """Return configured counts for one execution mode.

    Args:
        mode: One of exemplar, smoke, or production.
        config_path: Optional replacement population catalog.

    Returns:
        Mapping from canonical cell type to cell count.

    Example:
        `counts = counts_for_mode(mode="smoke")`
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Mode must be one of {VALID_MODES}; received {mode!r}.")
    return {
        spec.cell_type: spec.counts[mode]
        for spec in load_population_specs(config_path=config_path)
    }
