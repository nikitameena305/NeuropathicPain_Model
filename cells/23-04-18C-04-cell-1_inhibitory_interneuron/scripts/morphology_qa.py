"""Deterministic structural QA and diagnostic plots for NMO_170087.

The script operates on the unmodified NeuroMorpho standardized SWC.  It does
not repair topology or synthesize neuronal processes.  All thresholds used for
diagnostic flags are reported in the machine-readable output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np


CELL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWC = CELL_ROOT / "morphology/primary/23-04-18C-04-cell-1.CNG.swc"
DEFAULT_RESULTS = CELL_ROOT / "results/morphology_qa"
DEFAULT_FIGURES = CELL_ROOT / "figures/morphology"
TYPE_NAMES = {1: "soma", 2: "axon", 3: "dendrite", 4: "apical_dendrite"}


@dataclass(frozen=True)
class Node:
    """One SWC record."""

    node_id: int
    node_type: int
    x_um: float
    y_um: float
    z_um: float
    radius_um: float
    parent_id: int

    @property
    def xyz(self) -> np.ndarray:
        """Return the spatial coordinate as a NumPy vector."""

        return np.asarray((self.x_um, self.y_um, self.z_um), dtype=float)


def parse_swc(path: Path) -> tuple[list[Node], list[str]]:
    """Parse SWC rows while preserving the source comments."""

    nodes: list[Node] = []
    comments: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.strip()
        if not text:
            continue
        if text.startswith("#"):
            comments.append(text)
            continue
        fields = text.split()
        if len(fields) != 7:
            raise ValueError(f"{path}:{line_number}: expected 7 SWC fields, found {len(fields)}")
        nodes.append(
            Node(
                node_id=int(fields[0]),
                node_type=int(fields[1]),
                x_um=float(fields[2]),
                y_um=float(fields[3]),
                z_um=float(fields[4]),
                radius_um=float(fields[5]),
                parent_id=int(fields[6]),
            )
        )
    if not nodes:
        raise ValueError(f"No SWC nodes found in {path}")
    return nodes, comments


def edge_length(node: Node, parent: Node) -> float:
    """Return Euclidean parent-child length in micrometres."""

    return float(np.linalg.norm(node.xyz - parent.xyz))


def connected_components(nodes: Iterable[Node]) -> list[list[int]]:
    """Return undirected connected components over valid SWC edges."""

    node_list = list(nodes)
    by_id = {node.node_id: node for node in node_list}
    neighbours: dict[int, set[int]] = {node.node_id: set() for node in node_list}
    for node in node_list:
        if node.parent_id in by_id:
            neighbours[node.node_id].add(node.parent_id)
            neighbours[node.parent_id].add(node.node_id)
    components: list[list[int]] = []
    unseen = set(neighbours)
    while unseen:
        start = min(unseen)
        queue = deque([start])
        component: list[int] = []
        unseen.remove(start)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbour in sorted(neighbours[current]):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    queue.append(neighbour)
        components.append(sorted(component))
    return components


def maximum_path_distance(nodes: Iterable[Node]) -> tuple[float | None, bool]:
    """Compute maximum root-to-node path distance and flag parent cycles."""

    node_list = list(nodes)
    by_id = {node.node_id: node for node in node_list}
    cache: dict[int, float] = {}
    visiting: set[int] = set()
    cycle_detected = False

    def distance(node_id: int) -> float:
        nonlocal cycle_detected
        if node_id in cache:
            return cache[node_id]
        if node_id in visiting:
            cycle_detected = True
            return math.nan
        visiting.add(node_id)
        node = by_id[node_id]
        if node.parent_id == -1 or node.parent_id not in by_id:
            value = 0.0
        else:
            parent_distance = distance(node.parent_id)
            value = parent_distance + edge_length(node, by_id[node.parent_id])
        visiting.remove(node_id)
        cache[node_id] = value
        return value

    values = [distance(node.node_id) for node in node_list]
    finite = [value for value in values if math.isfinite(value)]
    return (max(finite) if finite else None), cycle_detected


def calculate_metrics(nodes: list[Node], *, sha256: str) -> dict[str, object]:
    """Calculate topology, geometry, and integrity metrics."""

    by_id = {node.node_id: node for node in nodes}
    id_counts = Counter(node.node_id for node in nodes)
    children: dict[int, list[int]] = defaultdict(list)
    orphans: list[int] = []
    edge_lengths: dict[int, float] = {}
    for node in nodes:
        if node.parent_id == -1:
            continue
        if node.parent_id not in by_id:
            orphans.append(node.node_id)
            continue
        children[node.parent_id].append(node.node_id)
        edge_lengths[node.node_id] = edge_length(node, by_id[node.parent_id])

    coordinate_groups: dict[tuple[float, float, float], list[int]] = defaultdict(list)
    exact_groups: dict[tuple[int, float, float, float, float, int], list[int]] = defaultdict(list)
    for node in nodes:
        coordinate_groups[(node.x_um, node.y_um, node.z_um)].append(node.node_id)
        exact_groups[
            (node.node_type, node.x_um, node.y_um, node.z_um, node.radius_um, node.parent_id)
        ].append(node.node_id)
    duplicate_coordinate_groups = [ids for ids in coordinate_groups.values() if len(ids) > 1]
    duplicate_record_groups = [ids for ids in exact_groups.values() if len(ids) > 1]

    type_counts = Counter(node.node_type for node in nodes)
    type_lengths: dict[str, float] = defaultdict(float)
    total_length = 0.0
    for node_id, length_um in edge_lengths.items():
        node = by_id[node_id]
        name = TYPE_NAMES.get(node.node_type, f"type_{node.node_type}")
        type_lengths[name] += length_um
        total_length += length_um

    radii = np.asarray([node.radius_um for node in nodes], dtype=float)
    neurite_diameters = np.asarray(
        [2.0 * node.radius_um for node in nodes if node.node_type != 1], dtype=float
    )
    extents = {}
    for axis, values in (
        ("x", [node.x_um for node in nodes]),
        ("y", [node.y_um for node in nodes]),
        ("z", [node.z_um for node in nodes]),
    ):
        extents[axis] = {
            "minimum_um": float(min(values)),
            "maximum_um": float(max(values)),
            "span_um": float(max(values) - min(values)),
        }

    max_path_um, cycle_detected = maximum_path_distance(nodes)
    components = connected_components(nodes)
    roots = [node.node_id for node in nodes if node.parent_id == -1]
    zero_length = [node_id for node_id, length in edge_lengths.items() if length <= 1e-12]
    branch_points = sorted(node_id for node_id, values in children.items() if len(values) > 1)
    endpoints = sorted(
        node.node_id for node in nodes if node.node_type != 1 and not children.get(node.node_id)
    )
    nonpositive_radius = sorted(node.node_id for node in nodes if node.radius_um <= 0.0)
    suspicious_neurite_diameter = sorted(
        node.node_id for node in nodes if node.node_type != 1 and 2.0 * node.radius_um > 10.0
    )
    severe_flags = {
        "duplicate_node_ids": sorted(node_id for node_id, count in id_counts.items() if count > 1),
        "orphan_node_ids": sorted(orphans),
        "cycle_detected": cycle_detected,
        "nonpositive_radius_node_ids": nonpositive_radius,
    }
    structural_pass = not any(
        (
            severe_flags["duplicate_node_ids"],
            severe_flags["orphan_node_ids"],
            severe_flags["cycle_detected"],
            severe_flags["nonpositive_radius_node_ids"],
        )
    ) and len(components) == 1

    return {
        "schema_version": "1.0",
        "source_file": str(DEFAULT_SWC.relative_to(CELL_ROOT)).replace("\\", "/"),
        "sha256": sha256,
        "thresholds": {
            "zero_length_um": 1e-12,
            "suspicious_neurite_diameter_um": 10.0,
        },
        "node_count": len(nodes),
        "node_counts_by_type": {
            TYPE_NAMES.get(key, f"type_{key}"): value for key, value in sorted(type_counts.items())
        },
        "root_count": len(roots),
        "root_node_ids": roots,
        "orphan_count": len(orphans),
        "orphan_node_ids": sorted(orphans),
        "connected_component_count": len(components),
        "connected_component_sizes": [len(component) for component in components],
        "duplicate_node_id_count": len(severe_flags["duplicate_node_ids"]),
        "duplicate_node_ids": severe_flags["duplicate_node_ids"],
        "duplicate_coordinate_group_count": len(duplicate_coordinate_groups),
        "duplicate_coordinate_groups": duplicate_coordinate_groups,
        "duplicate_exact_record_group_count": len(duplicate_record_groups),
        "duplicate_exact_record_groups": duplicate_record_groups,
        "zero_length_segment_count": len(zero_length),
        "zero_length_segment_node_ids": zero_length,
        "nonpositive_radius_count": len(nonpositive_radius),
        "nonpositive_radius_node_ids": nonpositive_radius,
        "suspicious_neurite_diameter_count": len(suspicious_neurite_diameter),
        "suspicious_neurite_diameter_node_ids": suspicious_neurite_diameter,
        "branch_point_count": len(branch_points),
        "branch_point_node_ids": branch_points,
        "endpoint_count": len(endpoints),
        "endpoint_node_ids": endpoints,
        "total_cable_length_um": total_length,
        "cable_length_by_child_type_um": dict(sorted(type_lengths.items())),
        "maximum_root_path_distance_um": max_path_um,
        "cycle_detected": cycle_detected,
        "radius_um": {
            "minimum": float(np.min(radii)),
            "median": float(np.median(radii)),
            "maximum": float(np.max(radii)),
        },
        "neurite_diameter_um": {
            "minimum": float(np.min(neurite_diameters)),
            "median": float(np.median(neurite_diameters)),
            "maximum": float(np.max(neurite_diameters)),
        },
        "coordinate_extents_um": extents,
        "reported_neuromorpho_soma_surface_um2": 396.349,
        "reported_neuromorpho_total_surface_um2": 7083.34,
        "integrity_from_neuromorpho": {
            "dendrites": "Moderate",
            "axon": "Incomplete",
        },
        "structural_qa_pass": structural_pass,
        "scientific_limitations": [
            "NeuroMorpho marks the dendrites as moderate integrity and the axon as incomplete.",
            "The deposited record is tagged 'No Diameter'; diameter-dependent cable results require sensitivity testing.",
            "A structural pass does not establish anatomical completeness or biophysical validity.",
        ],
    }


def plot_projection(
    nodes: list[Node],
    *,
    axes: tuple[str, str],
    output: Path,
    title: str,
    limits: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> None:
    """Plot parent-child SWC segments in one anatomical projection."""

    by_id = {node.node_id: node for node in nodes}
    axis_index = {"x": 0, "y": 1, "z": 2}
    colors = {1: "#111827", 2: "#d97706", 3: "#2563eb", 4: "#7c3aed"}
    labels_seen: set[int] = set()
    fig, ax = plt.subplots(figsize=(7.2, 7.2), constrained_layout=True)
    for node in nodes:
        parent = by_id.get(node.parent_id)
        if parent is None:
            continue
        values = np.vstack((parent.xyz, node.xyz))
        label = TYPE_NAMES.get(node.node_type, f"type {node.node_type}")
        ax.plot(
            values[:, axis_index[axes[0]]],
            values[:, axis_index[axes[1]]],
            color=colors.get(node.node_type, "#6b7280"),
            linewidth=1.6 if node.node_type == 1 else 0.7,
            alpha=0.88,
            label=label if node.node_type not in labels_seen else None,
        )
        labels_seen.add(node.node_type)
    ax.scatter(
        [node.xyz[axis_index[axes[0]]] for node in nodes if node.node_type == 1],
        [node.xyz[axis_index[axes[1]]] for node in nodes if node.node_type == 1],
        s=11,
        color=colors[1],
        zorder=5,
    )
    ax.set_title(title, fontsize=12, weight="bold")
    ax.set_xlabel(f"{axes[0].upper()} (µm)")
    ax.set_ylabel(f"{axes[1].upper()} (µm)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18, linewidth=0.6)
    if limits:
        ax.set_xlim(*limits[0])
        ax.set_ylim(*limits[1])
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="best", frameon=False, fontsize=9)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_type_table(nodes: list[Node], output: Path) -> None:
    """Write compact per-SWC-type counts and edge lengths."""

    by_id = {node.node_id: node for node in nodes}
    counts = Counter(node.node_type for node in nodes)
    lengths: dict[int, float] = defaultdict(float)
    for node in nodes:
        parent = by_id.get(node.parent_id)
        if parent is not None:
            lengths[node.node_type] += edge_length(node, parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("swc_type", "domain", "node_count", "cable_length_um"))
        for node_type in sorted(counts):
            writer.writerow(
                (node_type, TYPE_NAMES.get(node_type, f"type_{node_type}"), counts[node_type], lengths[node_type])
            )


def main() -> None:
    """Run QA and emit JSON, CSV, and four morphology views."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swc", type=Path, default=DEFAULT_SWC)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES)
    args = parser.parse_args()
    source = args.swc.resolve()
    nodes, comments = parse_swc(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    metrics = calculate_metrics(nodes, sha256=digest)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "morphology_qa.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.results_dir / "source_comments.txt").write_text("\n".join(comments) + "\n", encoding="utf-8")
    write_type_table(nodes, args.results_dir / "morphology_type_metrics.csv")
    plot_projection(
        nodes,
        axes=("x", "y"),
        output=args.figures_dir / "morphology_xy.png",
        title="NMO_170087 native morphology - XY",
    )
    plot_projection(
        nodes,
        axes=("x", "z"),
        output=args.figures_dir / "morphology_xz.png",
        title="NMO_170087 native morphology - XZ",
    )
    plot_projection(
        nodes,
        axes=("y", "z"),
        output=args.figures_dir / "morphology_yz.png",
        title="NMO_170087 native morphology - YZ",
    )
    soma = next(node for node in nodes if node.node_type == 1)
    plot_projection(
        nodes,
        axes=("x", "y"),
        output=args.figures_dir / "soma_proximal_zoom_xy.png",
        title="NMO_170087 soma and proximal neurites - XY",
        limits=((soma.x_um - 45.0, soma.x_um + 45.0), (soma.y_um - 45.0, soma.y_um + 45.0)),
    )
    print(json.dumps(metrics, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
