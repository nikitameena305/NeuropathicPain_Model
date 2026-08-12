"""Intrinsic NetPyNE rules derived from ModelDB accession 267056."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from .catalog import load_population_specs


INITIAL_RULE: dict[str, Any] = {
    "conds": {},
    "globals": {},
    "secLists": {},
    "secs": {
        "dend": {
            "geom": {
                "L": 400.0,
                "nseg": 5,
                "diam": 3.0,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "ca": {"e": 132.4579341637009, "i": 5e-05, "o": 2.0},
                "k": {"e": -70.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "CaIntraCellDyn": {
                    "cai_inf": 5e-05,
                    "cai_tau": 2.0,
                    "depth": 0.1,
                },
                "HH2": {"gnabar": 0.0, "gkbar": 0.0, "vtraub": -50.2},
                "iKCa": {"gbar": 0.002, "gk": 0.0},
                "borgka": {"gkabar": 0.0001584},
                "KDRI": {"gkbar": 0.2061},
                "pas": {"g": 4.2e-05, "e": -65.0},
            },
            "topol": {"parentSec": "soma", "parentX": 0.0, "childX": 0.0},
        },
        "hillock": {
            "geom": {
                "L": 9.0,
                "nseg": 3,
                "diam": 1.5,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "k": {"e": -77.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "B_Na": {
                    "gnabar": 5.147,
                    "alpha_shift": 6.713,
                    "beta_shift": 9.906,
                },
                "HH2": {"gkbar": 0.0, "gnabar": 0.0, "vtraub": -50.2},
                "borgka": {"gkabar": 0.0005},
                "KDRI": {"gkbar": 0.2171},
                "pas": {"g": 4.2e-05, "e": -65.0},
            },
            "topol": {"parentSec": "soma", "parentX": 1.0, "childX": 0.0},
        },
        "soma": {
            "geom": {
                "L": 20.0,
                "nseg": 3,
                "diam": 20.0,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "ca": {"e": 132.4579341637009, "i": 5e-05, "o": 2.0},
                "k": {"e": -70.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "B_Na": {
                    "gnabar": 0.3066,
                    "alpha_shift": 6.713,
                    "beta_shift": 9.906,
                },
                "CaIntraCellDyn": {
                    "cai_inf": 5e-05,
                    "cai_tau": 1.0,
                    "depth": 0.1,
                },
                "HH2": {"gkbar": 0.0, "gnabar": 0.0, "vtraub": -50.2},
                "borgka": {"gkabar": 0.04957},
                "KDRI": {"gkbar": 1.06e-05},
                "iKCa": {"gbar": 0.002, "gk": 0.0},
                "pas": {"g": 4.2e-05, "e": -65.0},
            },
            "topol": {},
        },
    },
}


DELAYED_RULE: dict[str, Any] = {
    "conds": {},
    "globals": {},
    "secLists": {},
    "secs": {
        "dend": {
            "geom": {
                "L": 400.0,
                "nseg": 5,
                "diam": 3.0,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "ca": {"e": 132.4579341637009, "i": 5e-05, "o": 2.0},
                "k": {"e": -70.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "CaIntraCellDyn": {
                    "cai_inf": 5e-05,
                    "cai_tau": 2.0,
                    "depth": 0.1,
                },
                "HH2": {"gnabar": 0.0, "gkbar": 0.144, "vtraub": -50.2},
                "iKCa": {"gbar": 0.002, "gk": 0.0},
                "borgka": {"gkabar": 0.0009333},
                "KDRI": {"gkbar": 0.96e-05},
                "pas": {"g": 0.96e-06, "e": -65.0},
            },
            "topol": {"parentSec": "soma", "parentX": 0.0, "childX": 0.0},
        },
        "hillock": {
            "geom": {
                "L": 9.0,
                "nseg": 3,
                "diam": 1.5,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "k": {"e": -77.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "B_Na": {
                    "gnabar": 0.03,
                    "alpha_shift": 0.0,
                    "beta_shift": 0.0,
                },
                "HH2": {"gkbar": 0.304, "gnabar": 0.02375, "vtraub": -50.2},
                "borgka": {"gkabar": 0.1120},
                "KDRI": {"gkbar": 0.01547},
                "pas": {"g": 0.96e-06, "e": -65.0},
            },
            "topol": {"parentSec": "soma", "parentX": 1.0, "childX": 0.0},
        },
        "soma": {
            "geom": {
                "L": 20.0,
                "nseg": 3,
                "diam": 20.0,
                "Ra": 150.0,
                "cm": 1.0,
            },
            "ions": {
                "ca": {"e": 132.4579341637009, "i": 5e-05, "o": 2.0},
                "k": {"e": -70.0, "i": 54.4, "o": 2.5},
                "na": {"e": 50.0, "i": 10.0, "o": 140.0},
            },
            "mechs": {
                "B_Na": {
                    "gnabar": 0.0001652,
                    "alpha_shift": 0.0,
                    "beta_shift": 0.0,
                },
                "CaIntraCellDyn": {
                    "cai_inf": 5e-05,
                    "cai_tau": 1.0,
                    "depth": 0.1,
                },
                "HH2": {"gkbar": 0.0043, "gnabar": 0.08548, "vtraub": -50.2},
                "borgka": {"gkabar": 0.01090},
                "KDRI": {"gkbar": 0.0001110},
                "iKCa": {"gbar": 0.002, "gk": 0.0},
                "pas": {"g": 0.96e-06, "e": -65.0},
            },
            "topol": {},
        },
    },
}


BASE_RULES = {
    "initial": INITIAL_RULE,
    "delayed": DELAYED_RULE,
}


def build_cell_rules(
    *,
    config_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Create one independent NetPyNE cell rule per population.

    Args:
        config_path: Optional replacement population catalog.

    Returns:
        Mapping from rule label to a deep-copied NetPyNE rule dictionary.

    Example:
        `rules = build_cell_rules()`
    """
    rules: dict[str, dict[str, Any]] = {}
    for spec in load_population_specs(config_path=config_path):
        rule = deepcopy(BASE_RULES[spec.base_rule])
        rule["conds"] = {"cellType": spec.cell_type}
        rules[f"{spec.cell_type}_rule"] = rule
    return rules
