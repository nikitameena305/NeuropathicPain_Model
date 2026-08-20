"""Extract executable Medlock ModelDB parameters without importing NEURON/NetPyNE."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from typing import Any


class StubNetParams:
    """Provide only the mutable dictionaries used by the Medlock source.

    Args:
        None.

    Returns:
        A lightweight NetParams substitute.

    Example:
        ``params = StubNetParams()``
    """

    def __init__(self) -> None:
        self.popParams: dict[str, Any] = {}
        self.cellParams: dict[str, Any] = {}
        self.synMechParams: dict[str, Any] = {}
        self.connParams: dict[str, Any] = {}


class StubSimConfig:
    """Provide SimConfig containers touched by cfg_mechanical.py.

    Args:
        None.

    Returns:
        A lightweight SimConfig substitute.

    Example:
        ``config = StubSimConfig()``
    """

    def __init__(self) -> None:
        self.recordTraces: dict[str, Any] = {}
        self.analysis: dict[str, Any] = {}


def sha256(path: Path) -> str:
    """Calculate a source file's SHA-256 digest.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal digest.

    Example:
        ``digest = sha256(Path("cells.py"))``
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(*, name: str, path: Path) -> types.ModuleType:
    """Execute a Python source file as a named module.

    Args:
        name: Temporary module name.
        path: Source file path.

    Returns:
        Executed module.

    Example:
        ``module = load_module(name="cells", path=source / "cells.py")``
    """

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot construct import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_stubs() -> None:
    """Install minimal in-memory neuron and netpyne modules.

    Args:
        None.

    Returns:
        None.

    Example:
        ``install_stubs()``
    """

    specs = types.SimpleNamespace(NetParams=StubNetParams, SimConfig=StubSimConfig)
    netpyne = types.ModuleType("netpyne")
    netpyne.specs = specs
    netpyne.sim = types.SimpleNamespace()
    neuron = types.ModuleType("neuron")
    neuron.h = types.SimpleNamespace()
    genrn = types.ModuleType("genrn")
    spkt_gen = types.ModuleType("spkt_gen")
    spkt_gen.__all__ = []
    sys.modules.update({"netpyne": netpyne, "neuron": neuron, "genrn": genrn, "spkt_gen": spkt_gen})


def without_conditions(rule: dict[str, Any]) -> dict[str, Any]:
    """Return a cell-rule copy excluding NetPyNE selection conditions.

    Args:
        rule: Extracted cell rule.

    Returns:
        Copy without the ``conds`` entry.

    Example:
        ``same = without_conditions(rule_a) == without_conditions(rule_b)``
    """

    return {key: value for key, value in rule.items() if key != "conds"}


def build_connectivity_index(conn_params: dict[str, Any], *, populations: list[str]) -> dict[str, Any]:
    """Index Medlock connection rules by pre- and postsynaptic population.

    Args:
        conn_params: Executed NetPyNE connection rules.
        populations: Excitatory population labels of interest.

    Returns:
        Input and output rule lists for every requested population.

    Example:
        ``index = build_connectivity_index(params, populations=["TrC", "PKC"])``
    """

    index: dict[str, Any] = {population: {"inputs": [], "outputs": []} for population in populations}
    for name, rule in conn_params.items():
        pre = rule.get("preConds", {}).get("popLabel")
        post = rule.get("postConds", {}).get("popLabel")
        record = {"name": name, **rule}
        if post in index:
            index[post]["inputs"].append(record)
        if pre in index:
            index[pre]["outputs"].append(record)
    return index


def extract_reference(*, source_dir: Path, commit: str) -> dict[str, Any]:
    """Execute the released parameter files against safe lightweight stubs.

    Args:
        source_dir: Checked-out ModelDB 267056 repository.
        commit: Audited Git commit identifier.

    Returns:
        JSON-serializable executable reference.

    Example:
        ``reference = extract_reference(source_dir=path, commit=sha)``
    """

    install_stubs()
    sys.path.insert(0, str(source_dir))
    original_cwd = Path.cwd()
    try:
        os.chdir(source_dir)
        cells = load_module(name="cells", path=source_dir / "cells.py")
        cfg_module = load_module(name="cfg_mechanical", path=source_dir / "cfg_mechanical.py")
        net_module = load_module(name="netParams_mechanical", path=source_dir / "netParams_mechanical.py")
    finally:
        os.chdir(original_cwd)
    net_params = net_module.netParams
    cfg = cfg_module.cfg
    rule_names = ["EXinitialRule", "EXdelayedRule", "PKCRule", "SOMRule", "CRRule"]
    rules = {name: getattr(cells, name) for name in rule_names}
    delayed_base = without_conditions(rules["EXdelayedRule"])
    mappings = {
        "eTrC": {"modeldb_population": "TrC", "cell_type": "EXib", "rule": "EXinitialRule", "count": 10},
        "ePKCgamma": {"modeldb_population": "PKC", "cell_type": "PKC", "rule": "PKCRule", "count": 30},
        "eVGLUT3": {"modeldb_population": "VGLUT3", "cell_type": "EXdl", "rule": "EXdelayedRule", "count": 4},
        "eDOR": {"modeldb_population": "DOR", "cell_type": "EXdl", "rule": "EXdelayedRule", "count": 30},
        "eSST": {"modeldb_population": "SOM", "cell_type": "SOM", "rule": "SOMRule", "count": 15},
        "eCR": {"modeldb_population": "CR", "cell_type": "CR", "rule": "CRRule", "count": 20},
    }
    population_labels = [entry["modeldb_population"] for entry in mappings.values()]
    return {
        "source": {
            "modeldb_accession": 267056,
            "repository": "https://github.com/ModelDBRepository/267056",
            "commit": commit,
            "file_sha256": {name: sha256(source_dir / name) for name in ("cells.py", "cfg_mechanical.py", "netParams_mechanical.py")},
        },
        "executed_configuration": {
            "celsius": cfg.hParams["celsius"],
            "v_init_mV": cfg.hParams["v_init"],
            "dt_ms": cfg.dt,
            "record_step_ms": cfg.recordStep,
            "network_duration_ms": cfg.duration,
            "default_spike_threshold_mV": net_params.defaultThreshold,
        },
        "population_mappings": mappings,
        "population_count_total": sum(entry["count"] for entry in mappings.values()),
        "delayed_rule_equivalence": {
            name: without_conditions(rules[name]) == delayed_base
            for name in ("PKCRule", "SOMRule", "CRRule", "EXdelayedRule")
        },
        "cell_rules": rules,
        "synaptic_mechanisms": net_params.synMechParams,
        "connectivity_by_population": build_connectivity_index(net_params.connParams, populations=population_labels),
        "all_connection_rules": net_params.connParams,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Args:
        None.

    Returns:
        Configured parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Extract exact Medlock ModelDB parameters through safe stubs.")
    parser.add_argument("--source-dir", type=Path, required=True, help="Checkout of ModelDBRepository/267056.")
    parser.add_argument("--commit", required=True, help="Audited Git commit SHA.")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned source and output without execution.")
    return parser


def main() -> int:
    """Extract the ModelDB executable reference.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python extract_medlock_reference.py --help``
    """

    args = build_parser().parse_args()
    if args.dry_run:
        print(json.dumps({"source_dir": str(args.source_dir), "commit": args.commit, "output": str(args.output)}, indent=2))
        return 0
    result = extract_reference(source_dir=args.source_dir.resolve(), commit=args.commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
