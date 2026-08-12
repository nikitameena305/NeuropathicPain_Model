import math
import csv
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt


SWC_FILE = Path("L796-ALT-PN.CNG.swc")

TYPE_NAMES = {
    1: "soma",
    2: "axon",
    3: "basal_dendrite",
    4: "apical_dendrite",
}


def read_swc(path):
    nodes = {}
    comments = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#"):
                comments.append(line)
                continue

            parts = line.split()
            if len(parts) < 7:
                continue

            node_id = int(float(parts[0]))
            node_type = int(float(parts[1]))
            x = float(parts[2])
            y = float(parts[3])
            z = float(parts[4])
            radius = float(parts[5])
            parent = int(float(parts[6]))

            nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "x": x,
                "y": y,
                "z": z,
                "r": radius,
                "parent": parent,
            }

    return nodes, comments


def distance(a, b):
    return math.sqrt(
        (a["x"] - b["x"]) ** 2 +
        (a["y"] - b["y"]) ** 2 +
        (a["z"] - b["z"]) ** 2
    )


def frustum_area(length, r1, r2):
    # Lateral surface area of truncated cone/frustum.
    # Units: if length and radius are in micrometers, area is in micrometer^2.
    slant = math.sqrt(length ** 2 + (r1 - r2) ** 2)
    return math.pi * (r1 + r2) * slant


def main():
    if not SWC_FILE.exists():
        raise FileNotFoundError(f"Cannot find {SWC_FILE}")

    nodes, comments = read_swc(SWC_FILE)

    children = defaultdict(list)
    missing_parent_edges = []
    root_nodes = []

    for nid, n in nodes.items():
        parent = n["parent"]

        if parent == -1:
            root_nodes.append(nid)
        elif parent in nodes:
            children[parent].append(nid)
        else:
            missing_parent_edges.append((nid, parent))

    type_counts = defaultdict(int)
    radii_by_type = defaultdict(list)

    for n in nodes.values():
        type_counts[n["type"]] += 1
        radii_by_type[n["type"]].append(n["r"])

    length_by_type = defaultdict(float)
    area_by_type = defaultdict(float)
    total_length = 0.0
    total_area_segments = 0.0

    for nid, n in nodes.items():
        parent = n["parent"]
        if parent != -1 and parent in nodes:
            p = nodes[parent]
            L = distance(n, p)
            area = frustum_area(L, n["r"], p["r"])

            # Assign segment to child node type.
            t = n["type"]
            length_by_type[t] += L
            area_by_type[t] += area
            total_length += L
            total_area_segments += area

    # Soma area estimate.
    soma_nodes = [n for n in nodes.values() if n["type"] == 1]
    soma_sphere_area = sum(4 * math.pi * (n["r"] ** 2) for n in soma_nodes)

    # If soma has multiple points, segment area already captures soma segments.
    # If soma is one point, sphere estimate is useful.
    total_area_with_soma_sphere = total_area_segments + soma_sphere_area

    branch_points = [nid for nid, ch in children.items() if len(ch) > 1]
    tips = [nid for nid in nodes if len(children[nid]) == 0]

    xs = np.array([n["x"] for n in nodes.values()])
    ys = np.array([n["y"] for n in nodes.values()])
    zs = np.array([n["z"] for n in nodes.values()])
    rs = np.array([n["r"] for n in nodes.values()])

    bbox = {
        "x_min": xs.min(), "x_max": xs.max(),
        "y_min": ys.min(), "y_max": ys.max(),
        "z_min": zs.min(), "z_max": zs.max(),
        "x_span": xs.max() - xs.min(),
        "y_span": ys.max() - ys.min(),
        "z_span": zs.max() - zs.min(),
    }

    # Save summary text
    report = []
    report.append("L796-ALT-PN SWC MORPHOLOGY CHECK")
    report.append("=" * 45)
    report.append(f"SWC file: {SWC_FILE}")
    report.append(f"Total nodes: {len(nodes)}")
    report.append(f"Root nodes: {len(root_nodes)}")
    report.append(f"Missing-parent edges: {len(missing_parent_edges)}")
    report.append("")
    report.append("Node counts by SWC type:")
    for t in sorted(type_counts):
        name = TYPE_NAMES.get(t, f"type_{t}")
        report.append(f"  Type {t} ({name}): {type_counts[t]}")
    report.append("")
    report.append(f"Total cable length: {total_length:.2f} µm")
    report.append(f"Total segment surface area, frustum only: {total_area_segments:.2f} µm²")
    report.append(f"Soma sphere area estimate: {soma_sphere_area:.2f} µm²")
    report.append(f"Total area with soma sphere estimate: {total_area_with_soma_sphere:.2f} µm²")
    report.append("")
    report.append(f"Branch points: {len(branch_points)}")
    report.append(f"Terminal tips: {len(tips)}")
    report.append("")
    report.append("Radius / diameter:")
    report.append(f"  Min radius: {rs.min():.4f} µm")
    report.append(f"  Max radius: {rs.max():.4f} µm")
    report.append(f"  Mean radius: {rs.mean():.4f} µm")
    report.append(f"  Min diameter: {2*rs.min():.4f} µm")
    report.append(f"  Max diameter: {2*rs.max():.4f} µm")
    report.append("")
    report.append("Bounding box:")
    for k, v in bbox.items():
        report.append(f"  {k}: {v:.2f} µm")
    report.append("")
    report.append("Interpretation:")
    if type_counts.get(1, 0) > 0:
        report.append("  [OK] Soma nodes present.")
    else:
        report.append("  [WARNING] No soma nodes found.")

    if type_counts.get(3, 0) + type_counts.get(4, 0) > 0:
        report.append("  [OK] Dendritic nodes present.")
    else:
        report.append("  [WARNING] No dendritic nodes found.")

    if type_counts.get(2, 0) > 0:
        report.append("  [OK] Axon nodes present.")
    else:
        report.append("  [WARNING] No axon nodes found.")

    if len(missing_parent_edges) == 0:
        report.append("  [OK] No missing-parent connectivity errors.")
    else:
        report.append("  [WARNING] Some nodes refer to missing parents.")

    Path("L796_morphology_check_report.txt").write_text("\n".join(report), encoding="utf-8")

    # Save type metrics CSV
    with open("L796_morphology_type_metrics.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "swc_type", "type_name", "node_count",
            "total_length_um", "segment_area_um2",
            "mean_radius_um", "min_radius_um", "max_radius_um"
        ])

        for t in sorted(type_counts):
            radii = np.array(radii_by_type[t])
            writer.writerow([
                t,
                TYPE_NAMES.get(t, f"type_{t}"),
                type_counts[t],
                f"{length_by_type[t]:.4f}",
                f"{area_by_type[t]:.4f}",
                f"{radii.mean():.4f}",
                f"{radii.min():.4f}",
                f"{radii.max():.4f}",
            ])

    # Save global summary CSV
    with open("L796_morphology_global_summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["total_nodes", len(nodes), "count"])
        writer.writerow(["root_nodes", len(root_nodes), "count"])
        writer.writerow(["missing_parent_edges", len(missing_parent_edges), "count"])
        writer.writerow(["total_length", f"{total_length:.4f}", "um"])
        writer.writerow(["segment_surface_area", f"{total_area_segments:.4f}", "um2"])
        writer.writerow(["soma_sphere_area_estimate", f"{soma_sphere_area:.4f}", "um2"])
        writer.writerow(["total_area_with_soma_sphere_estimate", f"{total_area_with_soma_sphere:.4f}", "um2"])
        writer.writerow(["branch_points", len(branch_points), "count"])
        writer.writerow(["terminal_tips", len(tips), "count"])
        writer.writerow(["min_diameter", f"{2*rs.min():.4f}", "um"])
        writer.writerow(["max_diameter", f"{2*rs.max():.4f}", "um"])
        writer.writerow(["x_span", f"{bbox['x_span']:.4f}", "um"])
        writer.writerow(["y_span", f"{bbox['y_span']:.4f}", "um"])
        writer.writerow(["z_span", f"{bbox['z_span']:.4f}", "um"])

    # Plot helper
    def plot_projection(xkey, ykey, filename, title):
        plt.figure(figsize=(8, 8))

        for nid, n in nodes.items():
            parent = n["parent"]
            if parent != -1 and parent in nodes:
                p = nodes[parent]

                t = n["type"]
                if t == 1:
                    color = "black"
                elif t == 2:
                    color = "red"
                elif t == 3:
                    color = "blue"
                elif t == 4:
                    color = "green"
                else:
                    color = "gray"

                plt.plot([p[xkey], n[xkey]], [p[ykey], n[ykey]], color=color, linewidth=0.6)

        plt.xlabel(f"{xkey} (µm)")
        plt.ylabel(f"{ykey} (µm)")
        plt.title(title)
        plt.axis("equal")
        plt.grid(True, alpha=0.3)

        # Dummy legend
        plt.plot([], [], color="black", label="soma")
        plt.plot([], [], color="blue", label="dendrite")
        plt.plot([], [], color="red", label="axon")
        plt.plot([], [], color="green", label="apical dendrite")
        plt.legend()

        plt.tight_layout()
        plt.savefig(filename, dpi=250)
        plt.close()

    plot_projection("x", "y", "L796_morphology_XY.png", "L796-ALT-PN morphology: XY view")
    plot_projection("x", "z", "L796_morphology_XZ.png", "L796-ALT-PN morphology: XZ view")
    plot_projection("y", "z", "L796_morphology_YZ.png", "L796-ALT-PN morphology: YZ view")

    print("\n".join(report))
    print("\nSaved files:")
    print("  L796_morphology_check_report.txt")
    print("  L796_morphology_global_summary.csv")
    print("  L796_morphology_type_metrics.csv")
    print("  L796_morphology_XY.png")
    print("  L796_morphology_XZ.png")
    print("  L796_morphology_YZ.png")


if __name__ == "__main__":
    main()
