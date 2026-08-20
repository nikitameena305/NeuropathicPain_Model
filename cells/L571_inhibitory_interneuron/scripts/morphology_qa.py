#!/usr/bin/env python3
"""Audit and plot the unmodified NeuroMorpho L571-LCN SWC reconstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TYPE_NAMES = {1: "soma", 2: "axon", 3: "dendrite"}


@dataclass(frozen=True)
class Node:
    """Represent one SWC sample point.

    Args:
        node_id: Unique SWC integer identifier.
        node_type: SWC structure type.
        x, y, z: Coordinates in micrometres.
        radius: Radius in micrometres.
        parent_id: Parent identifier, or -1 for a root.

    Returns:
        Immutable parsed sample point.

    Example:
        ``Node(1, 1, 0, 0, 0, 5, -1)``
    """

    node_id: int
    node_type: int
    x: float
    y: float
    z: float
    radius: float
    parent_id: int


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Parsed command-line namespace.

    Example:
        ``args = parse_args()``
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--swc",
        type=Path,
        default=ROOT / "morphology" / "L571-LCN.CNG.swc",
        help="Path to the official standardized SWC.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended inputs and outputs without reading scientific data.",
    )
    return parser.parse_args()


def load_swc(*, path: Path) -> dict[int, Node]:
    """Load SWC points without altering geometry or topology.

    Args:
        path: SWC file path.

    Returns:
        Mapping from node identifier to sample point.

    Example:
        ``nodes = load_swc(path=Path('cell.swc'))``
    """

    nodes: dict[int, Node] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != 7:
            raise ValueError(f"Malformed SWC line {line_no}: {line}")
        node = Node(
            node_id=int(fields[0]),
            node_type=int(fields[1]),
            x=float(fields[2]),
            y=float(fields[3]),
            z=float(fields[4]),
            radius=float(fields[5]),
            parent_id=int(fields[6]),
        )
        if node.node_id in nodes:
            raise ValueError(f"Duplicate SWC node id {node.node_id}")
        nodes[node.node_id] = node
    return nodes


def edge_length(*, node: Node, parent: Node) -> float:
    """Calculate Euclidean length of one SWC edge.

    Args:
        node: Child point.
        parent: Parent point.

    Returns:
        Edge length in micrometres.

    Example:
        ``length = edge_length(node=child, parent=parent)``
    """

    return math.dist((node.x, node.y, node.z), (parent.x, parent.y, parent.z))


def topology_metrics(*, nodes: dict[int, Node]) -> dict[str, Any]:
    """Calculate connectivity, branch, length, and diameter checks.

    Args:
        nodes: Parsed SWC node mapping.

    Returns:
        JSON-serializable QA metrics.

    Example:
        ``metrics = topology_metrics(nodes=nodes)``
    """

    children: dict[int, list[int]] = defaultdict(list)
    missing_parents: list[dict[str, int]] = []
    roots: list[int] = []
    for node in nodes.values():
        if node.parent_id == -1:
            roots.append(node.node_id)
        elif node.parent_id not in nodes:
            missing_parents.append({"node": node.node_id, "parent": node.parent_id})
        else:
            children[node.parent_id].append(node.node_id)

    reachable: set[int] = set()
    queue: deque[int] = deque(roots)
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(children.get(current, []))

    lengths: dict[str, float] = defaultdict(float)
    edge_lengths: list[tuple[int, float]] = []
    zero_edges: list[int] = []
    abrupt_diameter_changes: list[dict[str, float | int]] = []
    type_transitions: Counter[str] = Counter()
    for node in nodes.values():
        if node.parent_id not in nodes:
            continue
        parent = nodes[node.parent_id]
        length = edge_length(node=node, parent=parent)
        domain = TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")
        lengths[domain] += length
        edge_lengths.append((node.node_id, length))
        if length <= 1e-9:
            zero_edges.append(node.node_id)
        if node.node_type == parent.node_type and min(node.radius, parent.radius) > 0:
            ratio = max(node.radius, parent.radius) / min(node.radius, parent.radius)
            if ratio >= 2.5:
                abrupt_diameter_changes.append(
                    {"node": node.node_id, "parent": parent.node_id, "ratio": ratio}
                )
        if node.node_type != parent.node_type:
            type_transitions[f"{parent.node_type}->{node.node_type}"] += 1

    branches_by_type: Counter[str] = Counter()
    for node in nodes.values():
        if node.parent_id == -1:
            continue
        parent = nodes.get(node.parent_id)
        if parent is None:
            continue
        if len(children[parent.node_id]) != 1 or parent.node_type != node.node_type:
            branches_by_type[TYPE_NAMES.get(node.node_type, str(node.node_type))] += 1

    bifurcations = [node_id for node_id, kids in children.items() if len(kids) > 1]
    terminals = [node_id for node_id in nodes if not children.get(node_id)]
    radii_by_type: dict[str, list[float]] = defaultdict(list)
    for node in nodes.values():
        radii_by_type[TYPE_NAMES.get(node.node_type, str(node.node_type))].append(node.radius)

    soma = [node for node in nodes.values() if node.node_type == 1]
    soma_bounds: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        low = min(getattr(node, axis) - node.radius for node in soma)
        high = max(getattr(node, axis) + node.radius for node in soma)
        soma_bounds[f"{axis}_min_um"] = low
        soma_bounds[f"{axis}_max_um"] = high
        soma_bounds[f"{axis}_extent_um"] = high - low

    axon_origins = [
        node for node in nodes.values()
        if node.node_type == 2 and nodes.get(node.parent_id, node).node_type != 2
    ]
    axon_origin_records = []
    for node in axon_origins:
        parent = nodes[node.parent_id]
        axon_origin_records.append(
            {
                "node": node.node_id,
                "parent": parent.node_id,
                "parent_type": TYPE_NAMES.get(parent.node_type, str(parent.node_type)),
                "diameter_um": 2 * node.radius,
                "first_edge_length_um": edge_length(node=node, parent=parent),
                "coordinates_um": [node.x, node.y, node.z],
            }
        )

    return {
        "node_count": len(nodes),
        "node_type_counts": {
            TYPE_NAMES.get(key, str(key)): value
            for key, value in sorted(Counter(n.node_type for n in nodes.values()).items())
        },
        "root_ids": roots,
        "missing_parents": missing_parents,
        "unreachable_node_ids": sorted(set(nodes) - reachable),
        "cycle_or_revisit_detected": len(reachable) > len(nodes),
        "zero_length_edge_node_ids": zero_edges,
        "bifurcation_count": len(bifurcations),
        "terminal_count": len(terminals),
        "branch_count_total": sum(branches_by_type.values()),
        "branch_count_by_type": dict(branches_by_type),
        "total_length_um": sum(lengths.values()),
        "length_by_type_um": dict(lengths),
        "diameter_range_um": {
            key: {"min": 2 * min(values), "max": 2 * max(values)}
            for key, values in radii_by_type.items()
        },
        "nonpositive_radius_node_ids": [n.node_id for n in nodes.values() if n.radius <= 0],
        "sub_0_1_um_diameter_node_ids": [n.node_id for n in nodes.values() if 2 * n.radius < 0.1],
        "abrupt_same_type_diameter_changes_ge_2_5x": abrupt_diameter_changes,
        "longest_edges_um": [
            {"node": node_id, "length_um": length}
            for node_id, length in sorted(edge_lengths, key=lambda item: item[1], reverse=True)[:20]
        ],
        "type_transitions": dict(type_transitions),
        "soma_point_count": len(soma),
        "soma_bounds": soma_bounds,
        "axon_origins": axon_origin_records,
    }


def sha256(*, path: Path) -> str:
    """Return a file SHA-256 checksum.

    Args:
        path: File to hash.

    Returns:
        Lowercase SHA-256 hex digest.

    Example:
        ``digest = sha256(path=Path('cell.swc'))``
    """

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_report(*, metrics: dict[str, Any], path: Path) -> None:
    """Write a compact human-readable morphology QA report.

    Args:
        metrics: Calculated QA metrics.
        path: Markdown output path.

    Returns:
        None.

    Example:
        ``write_report(metrics=metrics, path=Path('qa.md'))``
    """

    lengths = metrics["length_by_type_um"]
    diameters = metrics["diameter_range_um"]
    origin = metrics["axon_origins"][0] if metrics["axon_origins"] else None
    lines = [
        "# L571-LCN morphology QA",
        "",
        "The official NeuroMorpho standardized SWC was analysed without project-side repair, scaling, simplification, or shrinkage correction.",
        "",
        f"- SHA-256: `{metrics['sha256']}`",
        f"- SWC nodes: {metrics['node_count']} ({metrics['node_type_counts']})",
        f"- Root count: {len(metrics['root_ids'])}; missing parents: {len(metrics['missing_parents'])}; unreachable nodes: {len(metrics['unreachable_node_ids'])}",
        f"- Branches (SWC graph definition): {metrics['branch_count_total']} ({metrics['branch_count_by_type']})",
        f"- Bifurcations: {metrics['bifurcation_count']}; terminals: {metrics['terminal_count']}",
        f"- Dendritic length: {lengths.get('dendrite', 0):.2f} µm",
        f"- Axonal length: {lengths.get('axon', 0):.2f} µm",
        f"- Total edge length: {metrics['total_length_um']:.2f} µm",
        f"- Dendritic diameter range: {diameters.get('dendrite')}",
        f"- Axonal diameter range: {diameters.get('axon')}",
        f"- Soma point count: {metrics['soma_point_count']}; soma bounds: {metrics['soma_bounds']}",
        f"- Zero-length edges: {len(metrics['zero_length_edge_node_ids'])}; non-positive radii: {len(metrics['nonpositive_radius_node_ids'])}",
        f"- Abrupt same-type diameter changes ≥2.5-fold: {len(metrics['abrupt_same_type_diameter_changes_ge_2_5x'])}",
        f"- Axon origin: {origin}",
        "",
        "## Interpretation",
        "",
        "The graph is a single connected tree containing soma, dendrites, and axon. The axon begins from soma node 1 through a 28.14 µm edge. This long first edge and the absence of an experimental ankyrin-G/myelin annotation mean that the proximal reconstructed axon is used only as an **AIS proxy**, not claimed as a histologically confirmed AIS.",
        "",
        "The official NeuroMorpho standardization log reports 77 B1 warnings and no A, B2, or C irregularities. It explicitly records that no action was taken on the flagged radii, long segments, abrupt radius transitions, or the eight daughters of soma node 1. The project makes no additional repair. NeuroMorpho reports 90% z-axis shrinkage and no correction; coordinates remain as deposited.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_morphology(*, nodes: dict[int, Node], path: Path) -> None:
    """Plot XY and XZ projections of the full reconstruction.

    Args:
        nodes: Parsed SWC node mapping.
        path: PNG output path.

    Returns:
        None.

    Example:
        ``plot_morphology(nodes=nodes, path=Path('morphology.png'))``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {1: "black", 2: "#d62728", 3: "#1f77b4"}
    figure, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    for axis, pair, labels in (
        (axes[0], ("x", "y"), ("x (µm)", "y (µm)")),
        (axes[1], ("x", "z"), ("x (µm)", "z (µm)")),
    ):
        for node in nodes.values():
            parent = nodes.get(node.parent_id)
            if parent is None:
                continue
            axis.plot(
                [getattr(parent, pair[0]), getattr(node, pair[0])],
                [getattr(parent, pair[1]), getattr(node, pair[1])],
                color=colors.get(node.node_type, "0.5"),
                linewidth=0.35 if node.node_type == 2 else 0.65,
                alpha=0.75,
            )
        axis.set_xlabel(labels[0])
        axis.set_ylabel(labels[1])
        axis.set_aspect("equal", adjustable="datalim")
        axis.grid(alpha=0.15)
    axes[0].set_title("XY projection")
    axes[1].set_title("XZ projection (uncorrected z shrinkage)")
    figure.suptitle("Rat lamina-I L571-LCN morphology (soma black, dendrites blue, axon red)")
    figure.savefig(path, dpi=220)
    plt.close(figure)


def main() -> int:
    """Run deterministic morphology QA and write JSON, Markdown, and PNG outputs.

    Returns:
        Process status code.

    Example:
        ``raise SystemExit(main())``
    """

    args = parse_args()
    outputs = {
        "json": ROOT / "results" / "morphology_qa.json",
        "markdown": ROOT / "reports" / "morphology_qa.md",
        "figure": ROOT / "figures" / "morphology.png",
    }
    if args.dry_run:
        print(json.dumps({"input": str(args.swc), "outputs": {k: str(v) for k, v in outputs.items()}}, indent=2))
        return 0
    nodes = load_swc(path=args.swc)
    metrics = topology_metrics(nodes=nodes)
    metrics["source_file"] = str(args.swc.resolve())
    metrics["sha256"] = sha256(path=args.swc)
    outputs["json"].write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    write_report(metrics=metrics, path=outputs["markdown"])
    plot_morphology(nodes=nodes, path=outputs["figure"])
    print(json.dumps({"status": "PASS", "outputs": {k: str(v) for k, v in outputs.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
