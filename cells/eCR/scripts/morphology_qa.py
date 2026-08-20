"""Audit NMO_260150 topology and geometry without changing the source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path


TYPE_NAMES = {0: "undefined", 1: "soma", 2: "axon", 3: "dendrite", 4: "apical"}


@dataclass(frozen=True)
class SwcNode:
    """Store one immutable SWC row.

    Args:
        node_id: Unique SWC identifier.
        node_type: SWC structure code.
        x: X coordinate in micrometres.
        y: Y coordinate in micrometres.
        z: Z coordinate in micrometres.
        radius: Standardized-file radius in micrometres.
        parent_id: Parent identifier, or -1 for a root.

    Returns:
        Parsed SWC node.

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


def parse_swc(path: Path) -> tuple[dict[int, SwcNode], dict[str, int]]:
    """Parse valid seven-column SWC rows and count skipped text rows.

    Args:
        path: Standardized SWC path.

    Returns:
        Node mapping and row-count metadata.

    Example:
        ``nodes, rows = parse_swc(Path("cell.swc"))``
    """

    nodes: dict[int, SwcNode] = {}
    row_counts = {"total_rows": 0, "comment_rows": 0, "blank_rows": 0, "valid_swc_rows": 0}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            row_counts["total_rows"] += 1
            line = raw_line.strip()
            if not line:
                row_counts["blank_rows"] += 1
                continue
            if line.startswith("#"):
                row_counts["comment_rows"] += 1
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
            row_counts["valid_swc_rows"] += 1
    if not nodes:
        raise ValueError(f"{path}: no SWC nodes found")
    return nodes, row_counts


def sha256(path: Path) -> str:
    """Calculate a lowercase SHA-256 checksum.

    Args:
        path: File to hash.

    Returns:
        Hexadecimal digest.

    Example:
        ``digest = sha256(Path("cell.swc"))``
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def edge_length(child: SwcNode, parent: SwcNode) -> float:
    """Return one parent-child Euclidean distance in micrometres.

    Args:
        child: Child node.
        parent: Parent node.

    Returns:
        Edge length in micrometres.

    Example:
        ``length = edge_length(child, parent)``
    """

    return math.dist((child.x, child.y, child.z), (parent.x, parent.y, parent.z))


def build_adjacency(nodes: dict[int, SwcNode]) -> tuple[dict[int, list[int]], dict[int, set[int]]]:
    """Build deterministic directed and undirected adjacency maps.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        Children and undirected-neighbour mappings.

    Example:
        ``children, neighbours = build_adjacency(nodes)``
    """

    children: dict[int, list[int]] = defaultdict(list)
    neighbours: dict[int, set[int]] = {node_id: set() for node_id in nodes}
    for node in nodes.values():
        if node.parent_id in nodes:
            children[node.parent_id].append(node.node_id)
            neighbours[node.parent_id].add(node.node_id)
            neighbours[node.node_id].add(node.parent_id)
    return {key: sorted(value) for key, value in children.items()}, neighbours


def connected_components(neighbours: dict[int, set[int]]) -> list[list[int]]:
    """Find connected components in the undirected SWC graph.

    Args:
        neighbours: Undirected adjacency map.

    Returns:
        Components sorted by first node identifier.

    Example:
        ``components = connected_components(neighbours)``
    """

    remaining = set(neighbours)
    components: list[list[int]] = []
    while remaining:
        start = min(remaining)
        queue: deque[int] = deque([start])
        component: list[int] = []
        while queue:
            node_id = queue.popleft()
            if node_id not in remaining:
                continue
            remaining.remove(node_id)
            component.append(node_id)
            queue.extend(sorted(neighbours[node_id]))
        components.append(sorted(component))
    return components


def maximum_path_distance(
    nodes: dict[int, SwcNode],
    *,
    roots: list[int],
) -> tuple[float | None, int | None]:
    """Calculate the longest directed cable path from any declared root.

    Args:
        nodes: Parsed SWC nodes.
        roots: Nodes with parent -1.

    Returns:
        Maximum path distance and terminal node identifier.

    Example:
        ``distance, terminal = maximum_path_distance(nodes, roots=roots)``
    """

    cache: dict[int, float] = {node_id: 0.0 for node_id in roots}
    visiting: set[int] = set()

    def distance_to(node_id: int) -> float:
        """Resolve one root-to-node distance recursively.

        Args:
            node_id: Target node identifier.

        Returns:
            Cable distance, or NaN if disconnected/cyclic.

        Example:
            ``value = distance_to(7)``
        """

        if node_id in cache:
            return cache[node_id]
        if node_id in visiting:
            return math.nan
        visiting.add(node_id)
        node = nodes[node_id]
        parent = nodes.get(node.parent_id)
        if parent is None:
            value = math.nan
        else:
            parent_distance = distance_to(parent.node_id)
            value = parent_distance + edge_length(node, parent)
        visiting.remove(node_id)
        cache[node_id] = value
        return value

    finite = [(distance_to(node_id), node_id) for node_id in sorted(nodes)]
    finite = [(distance, node_id) for distance, node_id in finite if math.isfinite(distance)]
    if not finite:
        return None, None
    distance, terminal = max(finite)
    return distance, terminal


def summarize_radii(nodes: dict[int, SwcNode]) -> dict[str, dict[str, float | int]]:
    """Summarize radii while explicitly withholding anatomical interpretation.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        Counts and descriptive statistics by node type.

    Example:
        ``summary = summarize_radii(nodes)``
    """

    grouped: dict[str, list[float]] = defaultdict(list)
    for node in nodes.values():
        grouped[TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")].append(node.radius)
    result: dict[str, dict[str, float | int]] = {}
    for name, values in sorted(grouped.items()):
        ordered = sorted(values)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
        result[name] = {
            "count": len(values),
            "min_um": min(values),
            "median_um": median,
            "mean_um": sum(values) / len(values),
            "max_um": max(values),
        }
    return result


def morphology_metrics(
    nodes: dict[int, SwcNode],
    *,
    row_counts: dict[str, int],
) -> dict[str, object]:
    """Calculate the complete task-specified morphology QA result.

    Args:
        nodes: Parsed SWC nodes.
        row_counts: Parser row counts.

    Returns:
        JSON-serializable QA dictionary.

    Example:
        ``metrics = morphology_metrics(nodes, row_counts=rows)``
    """

    children, neighbours = build_adjacency(nodes)
    roots = sorted(node.node_id for node in nodes.values() if node.parent_id == -1)
    missing_parent_nodes = sorted(
        node.node_id for node in nodes.values() if node.parent_id != -1 and node.parent_id not in nodes
    )
    components = connected_components(neighbours)
    duplicate_groups: dict[tuple[float, float, float], list[int]] = defaultdict(list)
    for node in nodes.values():
        duplicate_groups[(node.x, node.y, node.z)].append(node.node_id)
    duplicates = [ids for ids in duplicate_groups.values() if len(ids) > 1]
    zero_length_edges: list[dict[str, int]] = []
    cable_length: Counter[str] = Counter()
    all_lengths: list[float] = []
    for node in nodes.values():
        parent = nodes.get(node.parent_id)
        if parent is None:
            continue
        length = edge_length(node, parent)
        all_lengths.append(length)
        cable_length[TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")] += length
        if length == 0.0:
            zero_length_edges.append({"parent_id": parent.node_id, "child_id": node.node_id})
    branch_points = sorted(node_id for node_id, child_ids in children.items() if len(child_ids) > 1)
    endpoints = sorted(
        node_id for node_id, node in nodes.items() if node.node_type != 1 and not children.get(node_id)
    )
    max_path_um, max_path_node = maximum_path_distance(nodes, roots=roots)
    extents = {
        axis: {
            "min_um": min(getattr(node, axis) for node in nodes.values()),
            "max_um": max(getattr(node, axis) for node in nodes.values()),
            "extent_um": max(getattr(node, axis) for node in nodes.values())
            - min(getattr(node, axis) for node in nodes.values()),
        }
        for axis in ("x", "y", "z")
    }
    return {
        "row_counts": row_counts,
        "node_count": len(nodes),
        "node_type_counts": dict(
            sorted(Counter(TYPE_NAMES.get(node.node_type, f"type_{node.node_type}") for node in nodes.values()).items())
        ),
        "soma_node_count": sum(node.node_type == 1 for node in nodes.values()),
        "dendrite_node_count": sum(node.node_type in (3, 4) for node in nodes.values()),
        "axon_node_count": sum(node.node_type == 2 for node in nodes.values()),
        "root_count": len(roots),
        "root_node_ids": roots,
        "connected_component_count": len(components),
        "connected_component_sizes": [len(component) for component in components],
        "orphan_node_ids": missing_parent_nodes,
        "duplicate_coordinate_group_count": len(duplicates),
        "duplicate_coordinate_node_groups": sorted(duplicates, key=lambda ids: ids[0]),
        "zero_length_segment_count": len(zero_length_edges),
        "zero_length_segments": zero_length_edges,
        "nonpositive_radius_node_ids": sorted(node.node_id for node in nodes.values() if node.radius <= 0.0),
        "standardized_file_radius_distribution_um": summarize_radii(nodes),
        "diameter_evidence_status": "NO DIAMETER per NeuroMorpho metadata; SWC radii are standardized/model-defined and are not treated as measured anatomy",
        "branch_point_count": len(branch_points),
        "branch_point_node_ids": branch_points,
        "endpoint_count": len(endpoints),
        "endpoint_node_ids": endpoints,
        "dendritic_cable_length_um": cable_length.get("dendrite", 0.0) + cable_length.get("apical", 0.0),
        "axon_cable_length_um": cable_length.get("axon", 0.0),
        "total_neurite_cable_length_um": sum(
            length for name, length in cable_length.items() if name != "soma"
        ),
        "coordinate_extents_um": extents,
        "maximum_root_path_distance_um": max_path_um,
        "maximum_root_path_terminal_node_id": max_path_node,
        "all_required_topology_checks_pass": (
            len(roots) == 1
            and len(components) == 1
            and not missing_parent_nodes
            and not zero_length_edges
            and not any(node.radius <= 0.0 for node in nodes.values())
        ),
    }


def write_figure(nodes: dict[int, SwcNode], *, output_path: Path) -> None:
    """Render one original three-projection morphology PNG.

    Args:
        nodes: Parsed SWC nodes.
        output_path: Destination PNG path.

    Returns:
        None.

    Example:
        ``write_figure(nodes, output_path=Path("morphology.png"))``
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    projections = (("x", "y", "XY"), ("x", "z", "XZ"), ("y", "z", "YZ"))
    colours = {1: "#111827", 2: "#dc2626", 3: "#2563eb", 4: "#7c3aed"}
    figure, axes = plt.subplots(1, 3, figsize=(12, 4.2), constrained_layout=True)
    for axis, (horizontal, vertical, label) in zip(axes, projections):
        for node in nodes.values():
            parent = nodes.get(node.parent_id)
            if parent is None:
                continue
            axis.plot(
                [getattr(parent, horizontal), getattr(node, horizontal)],
                [getattr(parent, vertical), getattr(node, vertical)],
                color=colours.get(node.node_type, "#6b7280"),
                linewidth=0.45 if node.node_type != 1 else 1.5,
                alpha=0.9,
            )
        axis.set_title(f"{label} projection")
        axis.set_xlabel(f"{horizontal.upper()} (um)")
        axis.set_ylabel(f"{vertical.upper()} (um)")
        axis.set_aspect("equal", adjustable="datalim")
        axis.grid(alpha=0.15)
    figure.suptitle("NMO_260150 - standardized coordinates; diameters not measured", fontsize=12)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, facecolor="white")
    plt.close(figure)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface.

    Args:
        None.

    Returns:
        Configured parser.

    Example:
        ``parser = build_parser()``
    """

    script_dir = Path(__file__).resolve().parent
    cell_dir = script_dir.parent
    parser = argparse.ArgumentParser(description="Audit NMO_260150 and create one three-view figure.")
    parser.add_argument(
        "--swc",
        type=Path,
        default=cell_dir / "morphology" / "NMO_260150_100521A-S14_set5_cell11_standardized.CNG.swc",
    )
    parser.add_argument("--output-json", type=Path, default=cell_dir / "results" / "morphology_qa.json")
    parser.add_argument("--figure", type=Path, default=cell_dir / "figures" / "morphology.png")
    parser.add_argument("--dry-run", action="store_true", help="Print planned paths without reading or writing files.")
    return parser


def main() -> int:
    """Run morphology QA and write deterministic outputs.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python morphology_qa.py``
    """

    args = build_parser().parse_args()
    plan = {"swc": str(args.swc), "output_json": str(args.output_json), "figure": str(args.figure)}
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    nodes, row_counts = parse_swc(args.swc)
    metrics = morphology_metrics(nodes, row_counts=row_counts)
    metrics["source_file"] = args.swc.name
    metrics["sha256"] = sha256(args.swc)
    metrics["model_diameter_policy"] = {
        "nominal": "preserve NeuroMorpho standardized SWC radius profile as model-defined geometry",
        "interpretation": "not measured anatomy",
        "robustness_scales": [0.8, 1.0, 1.2],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_figure(nodes, output_path=args.figure)
    print(json.dumps({"qa_pass": metrics["all_required_topology_checks_pass"], **plan}, indent=2))
    return 0 if metrics["all_required_topology_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
