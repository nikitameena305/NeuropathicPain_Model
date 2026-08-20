#!/usr/bin/env python3
"""Validate and plot the unmodified NMO_109005 SWC morphology."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SwcNode:
    """Represent one valid seven-column SWC record."""

    node_id: int
    node_type: int
    x_um: float
    y_um: float
    z_um: float
    radius_um: float
    parent_id: int


def parse_swc(path: Path) -> tuple[dict[int, SwcNode], list[dict[str, object]], int]:
    """Parse an SWC file without repairing or rewriting it.

    Args:
        path: Input morphology path.

    Returns:
        Node mapping, invalid-row records, and comment-line count.

    Example:
        ``nodes, invalid, comments = parse_swc(Path("cell.swc"))``
    """

    nodes: dict[int, SwcNode] = {}
    invalid: list[dict[str, object]] = []
    comments = 0
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            comments += 1
            continue
        fields = line.split()
        if len(fields) != 7:
            invalid.append({"line": line_number, "reason": f"expected 7 columns, found {len(fields)}"})
            continue
        try:
            node = SwcNode(
                node_id=int(fields[0]),
                node_type=int(fields[1]),
                x_um=float(fields[2]),
                y_um=float(fields[3]),
                z_um=float(fields[4]),
                radius_um=float(fields[5]),
                parent_id=int(fields[6]),
            )
        except ValueError as exc:
            invalid.append({"line": line_number, "reason": str(exc)})
            continue
        if node.node_id in nodes:
            invalid.append({"line": line_number, "reason": f"duplicate node id {node.node_id}"})
            continue
        nodes[node.node_id] = node
    return nodes, invalid, comments


def edge_length(node: SwcNode, parent: SwcNode) -> float:
    """Return Euclidean edge length in micrometres.

    Args:
        node: Child SWC node.
        parent: Parent SWC node.

    Returns:
        Edge length in micrometres.

    Example:
        ``length = edge_length(child, parent)``
    """

    return math.dist((node.x_um, node.y_um, node.z_um), (parent.x_um, parent.y_um, parent.z_um))


def build_children(nodes: dict[int, SwcNode]) -> dict[int, list[int]]:
    """Build the parent-to-children lookup.

    Args:
        nodes: Parsed node mapping.

    Returns:
        Child node identifiers for every parent.

    Example:
        ``children = build_children(nodes)``
    """

    children: dict[int, list[int]] = defaultdict(list)
    for node in nodes.values():
        if node.parent_id in nodes:
            children[node.parent_id].append(node.node_id)
    return children


def connected_components(nodes: dict[int, SwcNode]) -> list[list[int]]:
    """Find undirected connected components in the SWC topology.

    Args:
        nodes: Parsed node mapping.

    Returns:
        Components as node-identifier lists.

    Example:
        ``components = connected_components(nodes)``
    """

    neighbours: dict[int, list[int]] = defaultdict(list)
    for node in nodes.values():
        if node.parent_id in nodes:
            neighbours[node.node_id].append(node.parent_id)
            neighbours[node.parent_id].append(node.node_id)
    unseen = set(nodes)
    components: list[list[int]] = []
    while unseen:
        start = next(iter(unseen))
        stack = [start]
        unseen.remove(start)
        component: list[int] = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in neighbours[current]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def morphology_metrics(nodes: dict[int, SwcNode], *, source_path: Path, invalid: list[dict[str, object]], comment_lines: int) -> dict[str, object]:
    """Calculate morphology integrity and geometry metrics.

    Args:
        nodes: Parsed node mapping.
        source_path: Original SWC path.
        invalid: Invalid-row audit records.
        comment_lines: Number of comment lines.

    Returns:
        JSON-serialisable QA record.

    Example:
        ``record = morphology_metrics(nodes, source_path=path, invalid=[], comment_lines=2)``
    """

    children = build_children(nodes)
    components = connected_components(nodes)
    roots = sorted(node.node_id for node in nodes.values() if node.parent_id == -1)
    orphans = sorted(node.node_id for node in nodes.values() if node.parent_id != -1 and node.parent_id not in nodes)
    coordinate_counts = Counter((node.x_um, node.y_um, node.z_um) for node in nodes.values())
    duplicate_coordinates = sum(count - 1 for count in coordinate_counts.values() if count > 1)
    lengths_um: Counter[int] = Counter()
    surface_um2: Counter[int] = Counter()
    zero_length_edges: list[list[int]] = []
    type_origins: Counter[int] = Counter()
    for node in nodes.values():
        if node.parent_id not in nodes:
            continue
        parent = nodes[node.parent_id]
        length_um = edge_length(node, parent)
        lengths_um[node.node_type] += length_um
        surface_um2[node.node_type] += math.pi * (node.radius_um + parent.radius_um) * length_um
        if length_um == 0.0:
            zero_length_edges.append([node.parent_id, node.node_id])
        if node.node_type != parent.node_type:
            type_origins[node.node_type] += 1
    axis_values = {
        "x": [node.x_um for node in nodes.values()],
        "y": [node.y_um for node in nodes.values()],
        "z": [node.z_um for node in nodes.values()],
    }
    extents = {axis: max(values) - min(values) for axis, values in axis_values.items()}
    soma_nodes = [node for node in nodes.values() if node.node_type == 1]
    axon_nodes = [node for node in nodes.values() if node.node_type == 2]
    dendrite_nodes = [node for node in nodes.values() if node.node_type in {3, 4}]
    sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return {
        "identity": {
            "cell_name": "26-11-14-A-A6",
            "neuromorpho_id": "NMO_109005",
            "species": "mouse",
            "known_identity": "GRP-positive excitatory interneuron",
            "region": "mid-lumbar spinal dorsal horn, lamina II",
            "physical_integrity": "Dendrites & Axon Moderate",
            "axon_interpretation": "native reconstructed axon; partial/moderate physical integrity",
            "source": "NeuroMorpho.Org API record 109005; Todd archive; Dickie et al. 2019",
        },
        "file": {
            "path": source_path.as_posix(),
            "format": "SWC text",
            "size_bytes": source_path.stat().st_size,
            "sha256": sha256,
            "comment_lines": comment_lines,
        },
        "integrity": {
            "valid_swc_rows": len(nodes),
            "invalid_rows": invalid,
            "root_ids": roots,
            "orphan_parent_node_ids": orphans,
            "connected_component_count": len(components),
            "component_sizes": sorted((len(component) for component in components), reverse=True),
            "duplicate_coordinate_rows_beyond_first": duplicate_coordinates,
            "zero_length_edges": zero_length_edges,
            "nonpositive_radius_node_ids": sorted(node.node_id for node in nodes.values() if node.radius_um <= 0.0),
            "pass": not invalid and len(roots) == 1 and not orphans and len(components) == 1 and not zero_length_edges and all(node.radius_um > 0.0 for node in nodes.values()),
        },
        "topology": {
            "type_counts": {str(key): value for key, value in sorted(Counter(node.node_type for node in nodes.values()).items())},
            "soma_present": bool(soma_nodes),
            "axon_present": bool(axon_nodes),
            "dendrites_present": bool(dendrite_nodes),
            "branch_points": sum(1 for node_id in nodes if len(children[node_id]) > 1),
            "endpoints": sum(1 for node_id in nodes if not children[node_id]),
            "primary_dendrite_origins": type_origins[3] + type_origins[4],
            "axon_origins": type_origins[2],
        },
        "geometry": {
            "radius_range_um": [min(node.radius_um for node in nodes.values()), max(node.radius_um for node in nodes.values())],
            "length_um_by_child_type": {str(key): value for key, value in sorted(lengths_um.items())},
            "surface_area_um2_by_child_type_approx": {str(key): value for key, value in sorted(surface_um2.items())},
            "total_cable_length_um": sum(lengths_um.values()),
            "total_surface_area_um2_approx": sum(surface_um2.values()),
            "extent_um": extents,
            "bounds_um": {axis: [min(values), max(values)] for axis, values in axis_values.items()},
        },
        "population_comparison_note": "The reconstructed geometry is retained without rescaling; Dickie et al. Table 3 GRP values are population mean +/- SD, not same-cell targets.",
    }


def write_projection_figure(nodes: dict[int, SwcNode], *, output_path: Path) -> None:
    """Write one three-panel XY/XZ/YZ morphology figure.

    Args:
        nodes: Parsed node mapping.
        output_path: PNG destination.

    Returns:
        None.

    Example:
        ``write_projection_figure(nodes, output_path=Path("morphology.png"))``
    """

    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    projections = [("x_um", "y_um", "XY"), ("x_um", "z_um", "XZ"), ("y_um", "z_um", "YZ")]
    colours = {1: "#222222", 2: "#d97706", 3: "#0f766e", 4: "#0f766e"}
    figure, axes = plt.subplots(1, 3, figsize=(12.0, 4.2), constrained_layout=True)
    for axis, (horizontal, vertical, title) in zip(axes, projections):
        for node in nodes.values():
            if node.parent_id not in nodes:
                continue
            parent = nodes[node.parent_id]
            axis.plot(
                [getattr(parent, horizontal), getattr(node, horizontal)],
                [getattr(parent, vertical), getattr(node, vertical)],
                color=colours.get(node.node_type, "#64748b"),
                linewidth=0.55 if node.node_type != 1 else 1.5,
                alpha=0.9,
            )
        axis.set_title(title)
        axis.set_xlabel(f"{horizontal[0].upper()} (um)")
        axis.set_ylabel(f"{vertical[0].upper()} (um)")
        axis.set_aspect("equal", adjustable="datalim")
        axis.grid(alpha=0.16, linewidth=0.5)
    legend = [
        Line2D([0], [0], color="#222222", lw=2, label="Soma"),
        Line2D([0], [0], color="#0f766e", lw=2, label="Dendrites"),
        Line2D([0], [0], color="#d97706", lw=2, label="Native axon (partial)"),
    ]
    axes[1].legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    figure.suptitle("NMO_109005 / 26-11-14-A-A6 morphology QA", fontsize=13, fontweight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser.

    Returns:
        Configured argument parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Audit NMO_109005 morphology without modifying it.")
    parser.add_argument("--swc", type=Path, required=True, help="Path to the existing SWC morphology.")
    parser.add_argument("--output-json", type=Path, required=True, help="Machine-readable QA output.")
    parser.add_argument("--plot", type=Path, required=True, help="Three-projection PNG output.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned paths without reading or writing files.")
    return parser


def main() -> int:
    """Run morphology QA and return a process exit code.

    Returns:
        Zero on a valid connected morphology, otherwise one.

    Example:
        ``raise SystemExit(main())``
    """

    args = build_parser().parse_args()
    if args.dry_run:
        print(json.dumps({"swc": str(args.swc), "output_json": str(args.output_json), "plot": str(args.plot)}, indent=2))
        return 0
    nodes, invalid, comment_lines = parse_swc(args.swc)
    if not nodes:
        raise ValueError(f"No valid SWC rows found in {args.swc}")
    record = morphology_metrics(nodes, source_path=args.swc, invalid=invalid, comment_lines=comment_lines)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_projection_figure(nodes, output_path=args.plot)
    print(json.dumps({"pass": record["integrity"]["pass"], "output": str(args.output_json)}, indent=2))
    return 0 if record["integrity"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
