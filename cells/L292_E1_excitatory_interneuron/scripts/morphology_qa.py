"""Audit an SWC morphology without changing its contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TYPE_NAMES = {0: "undefined", 1: "soma", 2: "axon", 3: "dendrite", 4: "apical"}


@dataclass(frozen=True)
class SwcNode:
    """Represent one immutable SWC sample point.

    Args:
        node_id: Integer SWC point identifier.
        node_type: SWC structure type.
        x: X coordinate in micrometres.
        y: Y coordinate in micrometres.
        z: Z coordinate in micrometres.
        radius: Point radius in micrometres.
        parent_id: Parent point identifier, or -1 for a root.

    Returns:
        A parsed SWC point.

    Example:
        ``SwcNode(1, 1, 0.0, 0.0, 0.0, 5.0, -1)``
    """

    node_id: int
    node_type: int
    x: float
    y: float
    z: float
    radius: float
    parent_id: int


def parse_swc(path: Path) -> dict[int, SwcNode]:
    """Parse an SWC file using only the Python standard library.

    Args:
        path: Path to the SWC file.

    Returns:
        Mapping from node identifier to parsed node.

    Example:
        ``nodes = parse_swc(Path("cell.swc"))``
    """

    nodes: dict[int, SwcNode] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 7:
                raise ValueError(f"{path}:{line_number}: expected 7 fields, found {len(fields)}")
            node = SwcNode(
                node_id=int(fields[0]),
                node_type=int(fields[1]),
                x=float(fields[2]),
                y=float(fields[3]),
                z=float(fields[4]),
                radius=float(fields[5]),
                parent_id=int(fields[6]),
            )
            if node.node_id in nodes:
                raise ValueError(f"{path}:{line_number}: duplicate node id {node.node_id}")
            nodes[node.node_id] = node
    if not nodes:
        raise ValueError(f"{path}: no SWC nodes found")
    return nodes


def edge_length(node: SwcNode, parent: SwcNode) -> float:
    """Calculate Euclidean length of one SWC edge.

    Args:
        node: Child point.
        parent: Parent point.

    Returns:
        Edge length in micrometres.

    Example:
        ``length_um = edge_length(child, parent)``
    """

    return math.dist((node.x, node.y, node.z), (parent.x, parent.y, parent.z))


def build_children(nodes: dict[int, SwcNode]) -> dict[int, list[int]]:
    """Build a deterministic parent-to-children map.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        Child identifiers sorted for every parent.

    Example:
        ``children = build_children(nodes)``
    """

    children: dict[int, list[int]] = defaultdict(list)
    for node in nodes.values():
        if node.parent_id in nodes:
            children[node.parent_id].append(node.node_id)
    return {key: sorted(value) for key, value in children.items()}


def count_sections(nodes: dict[int, SwcNode], children: dict[int, list[int]]) -> Counter[str]:
    """Count maximal same-type unbranched chains as SWC sections.

    Args:
        nodes: Parsed SWC nodes.
        children: Parent-to-children map.

    Returns:
        Section counts keyed by anatomical type.

    Example:
        ``counts = count_sections(nodes, children)``
    """

    counts: Counter[str] = Counter()
    for node in nodes.values():
        parent = nodes.get(node.parent_id)
        starts_chain = parent is None or parent.node_type != node.node_type or len(children.get(parent.node_id, [])) != 1
        if starts_chain:
            counts[TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")] += 1
    return counts


def find_cycles(nodes: dict[int, SwcNode]) -> list[list[int]]:
    """Find cycles in the parent-pointer graph.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        Unique cycles represented by node identifiers.

    Example:
        ``cycles = find_cycles(nodes)``
    """

    cycles: list[list[int]] = []
    globally_done: set[int] = set()
    for start in sorted(nodes):
        if start in globally_done:
            continue
        path: list[int] = []
        positions: dict[int, int] = {}
        current = start
        while current in nodes and current not in globally_done:
            if current in positions:
                cycles.append(path[positions[current] :])
                break
            positions[current] = len(path)
            path.append(current)
            current = nodes[current].parent_id
        globally_done.update(path)
    return cycles


def reachable_nodes(nodes: dict[int, SwcNode], children: dict[int, list[int]]) -> set[int]:
    """Return all nodes reachable from declared SWC roots.

    Args:
        nodes: Parsed SWC nodes.
        children: Parent-to-children map.

    Returns:
        Set of reachable node identifiers.

    Example:
        ``reachable = reachable_nodes(nodes, children)``
    """

    roots = sorted(node.node_id for node in nodes.values() if node.parent_id == -1)
    visited: set[int] = set()
    queue: deque[int] = deque(roots)
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(children.get(node_id, []))
    return visited


def soma_dimensions(nodes: Iterable[SwcNode]) -> dict[str, float | int | None]:
    """Measure the radius-expanded bounding box of soma points.

    Args:
        nodes: SWC nodes to search for type-1 soma points.

    Returns:
        Soma point count and X/Y/Z dimensions in micrometres.

    Example:
        ``dimensions = soma_dimensions(nodes.values())``
    """

    soma = [node for node in nodes if node.node_type == 1]
    if not soma:
        return {"point_count": 0, "x_um": None, "y_um": None, "z_um": None}
    dimensions: dict[str, float | int | None] = {"point_count": len(soma)}
    for axis in ("x", "y", "z"):
        lower = min(getattr(node, axis) - node.radius for node in soma)
        upper = max(getattr(node, axis) + node.radius for node in soma)
        dimensions[f"{axis}_um"] = upper - lower
    return dimensions


def morphology_metrics(nodes: dict[int, SwcNode]) -> dict[str, object]:
    """Calculate topology, geometry, and provenance-neutral QA metrics.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        JSON-serializable morphology QA dictionary.

    Example:
        ``metrics = morphology_metrics(parse_swc(path))``
    """

    children = build_children(nodes)
    roots = sorted(node.node_id for node in nodes.values() if node.parent_id == -1)
    missing_parents = sorted(node.node_id for node in nodes.values() if node.parent_id != -1 and node.parent_id not in nodes)
    reachable = reachable_nodes(nodes, children)
    lengths: Counter[str] = Counter()
    diameter_values: dict[str, list[float]] = defaultdict(list)
    zero_length_edges: list[dict[str, int]] = []
    transitions: Counter[str] = Counter()
    for node in nodes.values():
        type_name = TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")
        diameter_values[type_name].append(2.0 * node.radius)
        parent = nodes.get(node.parent_id)
        if parent is None:
            continue
        length = edge_length(node, parent)
        lengths[type_name] += length
        if length == 0.0:
            zero_length_edges.append({"parent": parent.node_id, "child": node.node_id})
        parent_type = TYPE_NAMES.get(parent.node_type, f"type_{parent.node_type}")
        transitions[f"{parent_type}->{type_name}"] += 1

    branch_points = sorted(node_id for node_id, child_ids in children.items() if len(child_ids) > 1)
    axon_origins: list[dict[str, object]] = []
    soma_nodes = [node for node in nodes.values() if node.node_type == 1]
    soma_centre = (
        sum(node.x for node in soma_nodes) / len(soma_nodes),
        sum(node.y for node in soma_nodes) / len(soma_nodes),
        sum(node.z for node in soma_nodes) / len(soma_nodes),
    ) if soma_nodes else (0.0, 0.0, 0.0)
    for node in sorted(nodes.values(), key=lambda item: item.node_id):
        parent = nodes.get(node.parent_id)
        if node.node_type == 2 and (parent is None or parent.node_type != 2):
            axon_origins.append(
                {
                    "axon_node_id": node.node_id,
                    "parent_node_id": node.parent_id,
                    "parent_type": None if parent is None else TYPE_NAMES.get(parent.node_type, f"type_{parent.node_type}"),
                    "euclidean_distance_from_soma_centre_um": math.dist((node.x, node.y, node.z), soma_centre),
                }
            )

    diameter_ranges = {
        name: {"min_um": min(values), "max_um": max(values), "mean_um": sum(values) / len(values)}
        for name, values in sorted(diameter_values.items())
    }
    non_soma_suspicious = sorted(
        node.node_id for node in nodes.values() if node.node_type != 1 and (node.radius <= 0.0 or 2.0 * node.radius > 20.0)
    )
    nonpositive_radii = sorted(node.node_id for node in nodes.values() if node.radius <= 0.0)

    return {
        "node_count": len(nodes),
        "node_type_counts": dict(sorted(Counter(TYPE_NAMES.get(node.node_type, f"type_{node.node_type}") for node in nodes.values()).items())),
        "swc_chain_section_counts": dict(sorted(count_sections(nodes, children).items())),
        "swc_chain_section_total": sum(count_sections(nodes, children).values()),
        "root_node_ids": roots,
        "missing_parent_node_ids": missing_parents,
        "unreachable_node_ids": sorted(set(nodes) - reachable),
        "cycle_count": len(find_cycles(nodes)),
        "cycles": find_cycles(nodes),
        "branch_point_count": len(branch_points),
        "branch_point_node_ids": branch_points,
        "terminal_count": sum(1 for node_id in nodes if not children.get(node_id)),
        "zero_length_edge_count": len(zero_length_edges),
        "zero_length_edges": zero_length_edges,
        "total_length_um_by_child_type": dict(sorted(lengths.items())),
        "total_neurite_length_um": sum(value for key, value in lengths.items() if key != "soma"),
        "diameter_ranges_um": diameter_ranges,
        "nonpositive_radius_node_ids": nonpositive_radii,
        "suspicious_non_soma_diameter_node_ids": non_soma_suspicious,
        "suspicious_diameter_rule": "non-soma diameter <= 0 or > 20 um; flags require review and are not auto-repaired",
        "soma_dimensions": soma_dimensions(nodes.values()),
        "axon_origin_candidates": axon_origins,
        "parent_child_type_transitions": dict(sorted(transitions.items())),
    }


def sha256(path: Path) -> str:
    """Calculate a file's SHA-256 digest.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal digest.

    Example:
        ``digest = sha256(Path("cell.swc"))``
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_morphology_svg(nodes: dict[int, SwcNode], output_path: Path) -> None:
    """Write three orthogonal morphology projections as a standalone SVG.

    Args:
        nodes: Parsed SWC nodes.
        output_path: Destination SVG path.

    Returns:
        None.

    Example:
        ``write_morphology_svg(nodes, Path("morphology.svg"))``
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    projections = (("x", "y", "XY"), ("x", "z", "XZ"), ("y", "z", "YZ"))
    width, height, margin, panel_width = 1260, 440, 35, 400
    colours = {1: "#111827", 2: "#dc2626", 3: "#2563eb", 4: "#7c3aed"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.label{font-size:15px;font-weight:600}.legend{font-size:12px}</style>',
    ]
    for panel_index, (horizontal, vertical, label) in enumerate(projections):
        values_h = [getattr(node, horizontal) for node in nodes.values()]
        values_v = [getattr(node, vertical) for node in nodes.values()]
        min_h, max_h = min(values_h), max(values_h)
        min_v, max_v = min(values_v), max(values_v)
        span_h = max(max_h - min_h, 1.0)
        span_v = max(max_v - min_v, 1.0)
        scale = min((panel_width - 2 * margin) / span_h, (height - 2 * margin - 35) / span_v)
        offset_x = panel_index * panel_width + margin + ((panel_width - 2 * margin) - span_h * scale) / 2
        offset_y = margin + 25 + ((height - 2 * margin - 35) - span_v * scale) / 2
        parts.append(f'<text class="label" x="{panel_index * panel_width + 12}" y="22">{label} projection</text>')
        for node in nodes.values():
            parent = nodes.get(node.parent_id)
            if parent is None:
                continue
            x1 = offset_x + (getattr(parent, horizontal) - min_h) * scale
            y1 = offset_y + (max_v - getattr(parent, vertical)) * scale
            x2 = offset_x + (getattr(node, horizontal) - min_h) * scale
            y2 = offset_y + (max_v - getattr(node, vertical)) * scale
            colour = colours.get(node.node_type, "#6b7280")
            stroke_width = 1.15 if node.node_type == 1 else 0.48
            parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{colour}" stroke-width="{stroke_width}" stroke-linecap="round" opacity="0.82"/>'
            )
    legend_x = 1210
    for index, (label, colour) in enumerate((("soma", "#111827"), ("axon", "#dc2626"), ("dendrite", "#2563eb"))):
        y = 55 + index * 20
        parts.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 16}" y2="{y}" stroke="{colour}" stroke-width="3"/>')
        parts.append(f'<text class="legend" x="{legend_x + 20}" y="{y + 4}">{label}</text>')
    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")


def render_markdown(metrics: dict[str, object], metadata: dict[str, object], swc_path: Path) -> str:
    """Render the QA result as a concise Markdown report.

    Args:
        metrics: Calculated morphology metrics.
        metadata: Curated source metadata.
        swc_path: Audited SWC path.

    Returns:
        Markdown report text.

    Example:
        ``text = render_markdown(metrics, metadata, swc_path)``
    """

    lengths = metrics["total_length_um_by_child_type"]
    diameters = metrics["diameter_ranges_um"]
    lines = [
        "# L292-E1-LCN morphology QA",
        "",
        "> No morphology repair was performed. All values below describe the official NeuroMorpho standardized SWC as downloaded.",
        "",
        "## Provenance",
        "",
        f"- File: `{swc_path.name}`",
        f"- SHA-256: `{metrics['sha256']}`",
        f"- NeuroMorpho ID: {metadata.get('neuromorpho_id', 'unknown')}",
        f"- Species / strain: {metadata.get('species', 'unknown')} / {metadata.get('strain', 'unknown')}",
        f"- Region: {metadata.get('region', 'unknown')}",
        f"- Cell classification: {metadata.get('cell_class', 'unknown')}",
        f"- Structural domains: {metadata.get('structural_domains', 'unknown')}",
        f"- Physical integrity: {metadata.get('physical_integrity', 'unknown')}",
        "",
        "## Geometry and topology",
        "",
        f"- SWC nodes: {metrics['node_count']}",
        f"- Maximal same-type unbranched chains (reported here as SWC sections): {metrics['swc_chain_section_total']}",
        f"- Section counts by type: {json.dumps(metrics['swc_chain_section_counts'], sort_keys=True)}",
        f"- Branch points: {metrics['branch_point_count']}",
        f"- Terminals: {metrics['terminal_count']}",
        f"- Dendritic length: {float(lengths.get('dendrite', 0.0)):.3f} um",
        f"- Axonal length: {float(lengths.get('axon', 0.0)):.3f} um",
        f"- Diameter ranges: {json.dumps(diameters, sort_keys=True)}",
        f"- Soma dimensions: {json.dumps(metrics['soma_dimensions'], sort_keys=True)}",
        f"- Root nodes: {metrics['root_node_ids']}",
        f"- Missing-parent nodes: {metrics['missing_parent_node_ids']}",
        f"- Unreachable nodes: {metrics['unreachable_node_ids']}",
        f"- Cycles: {metrics['cycle_count']}",
        f"- Zero-length edges: {metrics['zero_length_edge_count']}",
        f"- Nonpositive radii: {len(metrics['nonpositive_radius_node_ids'])}",
        f"- Suspicious non-soma diameters: {len(metrics['suspicious_non_soma_diameter_node_ids'])}",
        "",
        "## Axon origin audit",
        "",
        f"Candidate type-transition origins: `{json.dumps(metrics['axon_origin_candidates'], sort_keys=True)}`",
        "",
        "A type-2 axon origin is anatomical evidence for an axonal transition, not proof that the first imported axonal section is an AIS. Any proximal initiation zone remains a computational candidate until channel localization and spike-initiation timing are validated.",
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Args:
        None.

    Returns:
        Configured argument parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Audit an SWC morphology without repairing it.")
    parser.add_argument("--swc", type=Path, required=True, help="Official SWC file to audit.")
    parser.add_argument("--metadata", type=Path, required=True, help="Curated JSON metadata file.")
    parser.add_argument("--output-json", type=Path, required=True, help="Machine-readable QA output.")
    parser.add_argument("--report", type=Path, required=True, help="Markdown QA report.")
    parser.add_argument("--plot", type=Path, required=True, help="Three-view SVG morphology plot.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned paths without reading or writing files.")
    return parser


def main() -> int:
    """Run morphology QA from command-line arguments.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python morphology_qa.py --help``
    """

    args = build_parser().parse_args()
    if args.dry_run:
        print(json.dumps({"swc": str(args.swc), "metadata": str(args.metadata), "outputs": [str(args.output_json), str(args.report), str(args.plot)]}, indent=2))
        return 0
    nodes = parse_swc(args.swc)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8-sig"))
    metrics = morphology_metrics(nodes)
    metrics["source_file"] = str(args.swc)
    metrics["sha256"] = sha256(args.swc)
    metrics["metadata"] = metadata
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(render_markdown(metrics, metadata, args.swc), encoding="utf-8")
    write_morphology_svg(nodes, args.plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
