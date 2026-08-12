#!/usr/bin/env python3
"""Generate publication figures for the L292-E1-LCN report.

Every trace and numerical panel is derived from files already stored in this
workspace.  Schematic panels describe model roles or validation gates only;
they do not assert unvalidated synaptic connectivity.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "L292_E1_LCN_report_figures"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#12324A"
BLUE = "#2878A5"
TEAL = "#1B8A89"
GREEN = "#2E7D5B"
GOLD = "#B78324"
RED = "#A83232"
PALE_BLUE = "#E8F1F6"
PALE_GREEN = "#E7F4EC"
PALE_RED = "#F9E8E8"
PALE_GOLD = "#F8F0DC"
GRAY = "#5E6A71"
LIGHT = "#DDE4E8"
AXON = "#D55E00"
DEND = "#0072B2"
SOMA = "#1B9E77"


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "axes.titleweight": "bold",
        "axes.edgecolor": "#65747C",
        "axes.linewidth": 0.8,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.3,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def add_source(fig: plt.Figure, text: str) -> None:
    fig.text(0.01, 0.005, text, fontsize=6.8, color=GRAY, ha="left", va="bottom")


def read_swc(path: Path):
    nodes = {}
    order = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split()
            nid = int(p[0])
            nodes[nid] = {
                "id": nid,
                "type": int(p[1]),
                "x": float(p[2]),
                "y": float(p[3]),
                "z": float(p[4]),
                "r": float(p[5]),
                "parent": int(p[6]),
            }
            order.append(nid)
    return nodes, order


def morphology_segments(nodes, order, projection="xy", types=None, centre=None, radius=None):
    a, b = ("x", "y") if projection == "xy" else ("x", "z")
    by_type = {1: [], 2: [], 3: []}
    for nid in order:
        n = nodes[nid]
        pid = n["parent"]
        if pid < 0 or pid not in nodes:
            continue
        if types is not None and n["type"] not in types:
            continue
        p = nodes[pid]
        if centre is not None and radius is not None:
            if max(
                np.hypot(n["x"] - centre[0], n["y"] - centre[1]),
                np.hypot(p["x"] - centre[0], p["y"] - centre[1]),
            ) > radius:
                continue
        by_type.setdefault(n["type"], []).append([(p[a], p[b]), (n[a], n[b])])
    return by_type


def draw_morphology(ax, nodes, order, projection="xy", types=None, centre=None, radius=None):
    segs = morphology_segments(nodes, order, projection, types, centre, radius)
    for t, color, width, zorder in [(2, AXON, 0.32, 1), (3, DEND, 0.6, 2), (1, SOMA, 2.0, 3)]:
        if segs.get(t):
            lc = LineCollection(segs[t], colors=color, linewidths=width, alpha=0.9, zorder=zorder)
            ax.add_collection(lc)
    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (µm)")
    ax.set_ylabel(("y" if projection == "xy" else "z") + " (µm)")
    ax.spines[["top", "right"]].set_visible(False)


def read_trace(rel: str):
    data = np.genfromtxt(ROOT / rel, delimiter=",", names=True)
    return data


def read_metrics(rel: str):
    with (ROOT / rel).open("r", newline="", encoding="utf-8") as fh:
        out = []
        for row in csv.DictReader(fh):
            clean = {}
            for k, v in row.items():
                if v == "":
                    clean[k] = None
                elif v in {"True", "False"}:
                    clean[k] = v == "True"
                else:
                    try:
                        clean[k] = float(v)
                    except ValueError:
                        clean[k] = v
            out.append(clean)
    return out


def shade_stimulus(ax, delay=200.0, duration=500.0):
    ax.axvspan(delay, delay + duration, color=PALE_GOLD, alpha=0.65, lw=0, zorder=0)
    ax.text(delay + duration - 5, 0.98, "IClamp", transform=ax.get_xaxis_transform(),
            ha="right", va="top", fontsize=7, color=GOLD)


def panel_trace(ax, rel, title, color=BLUE, ylim=None, sites=False):
    d = read_trace(rel)
    shade_stimulus(ax)
    ax.plot(d["time_ms"], d["v_soma_mV"], color=color, lw=1.0, label="soma")
    if sites:
        ax.plot(d["time_ms"], d["v_proximal_axon_candidate_mV"], color=AXON, lw=0.85,
                label="proximal axon candidate")
        ax.plot(d["time_ms"], d["v_proximal_dendrite_mV"], color=TEAL, lw=0.75,
                label="proximal dendrite")
    ax.set_title(title)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Membrane potential (mV)")
    if ylim:
        ax.set_ylim(*ylim)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=LIGHT, lw=0.5, alpha=0.7)


def status_box(ax, xy, width, height, title, subtitle, fill, edge, title_color=None):
    x, y = xy
    box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.018,rounding_size=0.018",
                         facecolor=fill, edgecolor=edge, linewidth=1.2)
    ax.add_patch(box)
    ax.text(x + width / 2, y + height * 0.62, title, ha="center", va="center",
            fontsize=10, fontweight="bold", color=title_color or edge)
    ax.text(x + width / 2, y + height * 0.29, subtitle, ha="center", va="center",
            fontsize=7.8, color=NAVY, wrap=True)


def arrow(ax, start, end, color=GRAY):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.2, color=color))


def figure_morphologies():
    swc = ROOT / "morphology" / "primary" / "L292-E1-LCN.CNG.swc"
    nodes, order = read_swc(swc)
    legend = [Line2D([0], [0], color=SOMA, lw=3, label="soma"),
              Line2D([0], [0], color=DEND, lw=2, label="dendrite"),
              Line2D([0], [0], color=AXON, lw=2, label="axon")]

    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    draw_morphology(ax, nodes, order, "xy")
    ax.set_title("Complete L292-E1-LCN morphology (XY projection)")
    ax.legend(handles=legend, loc="upper right", frameon=False)
    add_source(fig, "DIRECT MORPHOLOGY DATA — official NeuroMorpho standardized SWC; geometry unaltered.")
    save(fig, "01_complete_morphology_xy.png")

    fig, ax = plt.subplots(figsize=(7.2, 5.8))
    draw_morphology(ax, nodes, order, "xy", types={1, 3})
    ax.set_title("Soma and dendritic arbor (XY projection)")
    ax.legend(handles=legend[:2], loc="best", frameon=False)
    add_source(fig, "DIRECT MORPHOLOGY DATA — SWC types 1 (soma) and 3 (dendrite).")
    save(fig, "02_soma_dendrites_xy.png")

    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    draw_morphology(ax, nodes, order, "xy", types={2})
    ax.set_title("Complete axonal arbor (XY projection)")
    ax.legend(handles=[legend[2]], loc="best", frameon=False)
    add_source(fig, "DIRECT MORPHOLOGY DATA — SWC type 2 (axon); no geometry smoothing or repair.")
    save(fig, "03_complete_axon_xy.png")

    soma_pts = np.array([[n["x"], n["y"], n["z"]] for n in nodes.values() if n["type"] == 1])
    centre = soma_pts.mean(axis=0)
    cand = nodes[3771]
    fig, ax = plt.subplots(figsize=(7.2, 5.5))
    draw_morphology(ax, nodes, order, "xy", centre=(centre[0], centre[1]), radius=130)
    ax.scatter([cand["x"]], [cand["y"]], s=70, marker="*", color=RED, zorder=5,
               label="axon-origin candidate: node 3771")
    ax.scatter([centre[0]], [centre[1]], s=40, facecolor="white", edgecolor=NAVY, zorder=5,
               label="soma centroid")
    ax.set_xlim(centre[0] - 130, centre[0] + 130)
    ax.set_ylim(centre[1] - 130, centre[1] + 130)
    ax.set_title("Soma-to-axon-origin region")
    ax.legend(loc="upper right", frameon=True, framealpha=0.95)
    add_source(fig, "DIRECT MORPHOLOGY DATA — candidate is 37.126 µm from soma centroid; AIS identity is unconfirmed.")
    save(fig, "04_axon_origin_region.png")

    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    draw_morphology(ax, nodes, order, "xz")
    ax.set_title("Complete L292-E1-LCN morphology (XZ projection)")
    ax.legend(handles=legend, loc="best", frameon=False)
    add_source(fig, "DIRECT MORPHOLOGY DATA — alternative projection of the same unaltered SWC.")
    save(fig, "05_complete_morphology_xz.png")


def figure_passive():
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for amp, fname, color in [
        (0.0, "trace_p0p000_nA.csv", GRAY),
        (-0.005, "trace_m0p005_nA.csv", TEAL),
        (-0.01, "trace_m0p010_nA.csv", BLUE),
        (-0.02, "trace_m0p020_nA.csv", NAVY),
    ]:
        d = read_trace(f"results/23C/passive/final_strict_dlambda/{fname}")
        ax.plot(d["time_ms"], d["v_soma_mV"], lw=1.0, color=color, label=f"{amp:g} nA")
    shade_stimulus(ax)
    ax.set_title("Passive 23 °C current-clamp responses")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Somatic membrane potential (mV)")
    ax.legend(ncol=4, frameon=False, loc="lower center")
    ax.grid(axis="y", color=LIGHT, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    add_source(fig, "MODEL-DERIVED — 500 ms somatic IClamp; dt=0.025 ms; d_lambda=0.1; 23 °C.")
    save(fig, "06_passive_23C_response.png")

    rows = read_metrics("results/23C/passive/convergence_strict_dlambda/convergence.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.55), sharex=True)
    for dl, color in [(0.2, GOLD), (0.1, BLUE), (0.05, TEAL)]:
        subset = sorted([r for r in rows if r["d_lambda"] == dl], key=lambda r: r["dt_ms"])
        x = [r["dt_ms"] for r in subset]
        axes[0].plot(x, [r["rin_MOhm"] for r in subset], "o-", color=color, lw=1.2, ms=4,
                     label=f"d_lambda={dl:g}")
        axes[1].plot(x, [r["tau_ms"] for r in subset], "o-", color=color, lw=1.2, ms=4)
    axes[0].set_title("Input resistance")
    axes[0].set_ylabel("Rin (MΩ)")
    axes[0].ticklabel_format(axis="y", style="plain", useOffset=False)
    axes[1].set_title("Membrane time constant")
    axes[1].set_ylabel("Tau (ms)")
    for ax in axes:
        ax.set_xlabel("dt (ms)")
        ax.grid(color=LIGHT, lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, fontsize=7.8)
    fig.suptitle("Passive numerical convergence: all 9 dt × d_lambda combinations passed", y=1.02,
                 fontsize=11, fontweight="bold")
    add_source(fig, "MODEL-DERIVED — strict convergence grid; worst relative differences: Rin 0.01745%, tau 0.08482%.")
    save(fig, "07_passive_convergence.png")


def figure_etrc_23():
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 6.2), sharex=True, sharey=True)
    for ax, amp, fname in zip(axes.flat, [0.55, 0.56, 0.75, 1.5],
                              ["trace_p0p550_nA.csv", "trace_p0p560_nA.csv",
                               "trace_p0p750_nA.csv", "trace_p1p500_nA.csv"]):
        panel_trace(ax, f"results/23C/eTrC/final/{fname}", f"{amp:g} nA", BLUE, (-75, 35))
    fig.suptitle("eTrC current-clamp series at 23 °C", y=1.01, fontsize=12, fontweight="bold")
    fig.tight_layout()
    add_source(fig, "MODEL-DERIVED — 500 ms somatic steps; one-spike transient phenotype above 0.56 nA.")
    save(fig, "08_eTrC_23C_traces.png")

    d = read_trace("results/23C/eTrC/final/trace_p0p560_nA.csv")
    mask = (d["time_ms"] >= 214) & (d["time_ms"] <= 221)
    fig, ax = plt.subplots(figsize=(7.3, 4.0))
    ax.plot(d["time_ms"][mask], d["v_soma_mV"][mask], color=BLUE, lw=1.5, label="soma")
    ax.plot(d["time_ms"][mask], d["v_proximal_axon_candidate_mV"][mask], color=AXON, lw=1.1,
            label="proximal axon candidate")
    ax.plot(d["time_ms"][mask], d["v_proximal_dendrite_mV"][mask], color=TEAL, lw=1.0,
            label="proximal dendrite")
    ax.axhline(0, color=GRAY, lw=0.6, ls="--")
    ax.set_title("eTrC rheobase action potential at 23 °C (0.56 nA)")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Membrane potential (mV)")
    ax.legend(frameon=False)
    ax.grid(color=LIGHT, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    add_source(fig, "MODEL-DERIVED — interpolated proximal-axon zero crossing leads soma by 0.00893 ms; below dt=0.025 ms.")
    save(fig, "09_eTrC_23C_AP_zoom.png")

    rows = read_metrics("results/23C/eTrC/final/metrics.csv")
    rows = [r for r in rows if r["first_spike_latency_ms"] is not None]
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot([r["amplitude_nA"] for r in rows], [r["first_spike_latency_ms"] for r in rows],
            "o-", color=BLUE, lw=1.5, ms=5)
    ax.set_title("eTrC first-spike latency decreases with current at 23 °C")
    ax.set_xlabel("Injected current (nA)")
    ax.set_ylabel("First-spike latency from step onset (ms)")
    ax.grid(color=LIGHT, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    add_source(fig, "MODEL-DERIVED — accepted final 23 °C current series.")
    save(fig, "10_eTrC_23C_latency_current.png")


def figure_delayed_23():
    fig, axes = plt.subplots(3, 1, figsize=(7.5, 7.2), sharex=True, sharey=True)
    for ax, amp, fname in zip(axes, [0.38, 0.75, 1.0],
                              ["trace_p0p380_nA.csv", "trace_p0p750_nA.csv", "trace_p1p000_nA.csv"]):
        panel_trace(ax, f"results/23C/delayed_excitatory/final_after_HH2_singularity_fix/{fname}",
                    f"{amp:g} nA", TEAL, (-75, 30))
    fig.suptitle("Common delayed-excitatory current-clamp series at 23 °C", y=1.01,
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    add_source(fig, "MODEL-DERIVED — 500 ms somatic steps; no depolarization block in the tested series.")
    save(fig, "11_delayed_23C_traces.png")

    rows = read_metrics("results/23C/delayed_excitatory/final_after_HH2_singularity_fix/metrics.csv")
    rows = [r for r in rows if r["first_spike_latency_ms"] is not None]
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot([r["amplitude_nA"] for r in rows], [r["first_spike_latency_ms"] for r in rows],
            "o-", color=TEAL, lw=1.5, ms=5)
    for r in rows:
        ax.annotate(f"{int(r['spike_count'])} spike{'s' if r['spike_count'] != 1 else ''}",
                    (r["amplitude_nA"], r["first_spike_latency_ms"]), xytext=(5, 5),
                    textcoords="offset points", fontsize=7, color=GRAY)
    ax.set_title("Delayed phenotype at 23 °C: latency falls as current rises")
    ax.set_xlabel("Injected current (nA)")
    ax.set_ylabel("First-spike latency from step onset (ms)")
    ax.grid(color=LIGHT, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    add_source(fig, "MODEL-DERIVED — accepted post-HH2-fix result set.")
    save(fig, "12_delayed_23C_latency_current.png")


def figure_temperature_and_failure():
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8), sharey=True)
    panel_trace(axes[0], "results/23C/eTrC/final/trace_p0p560_nA.csv", "23 °C rheobase: 0.56 nA", BLUE,
                (-75, 30))
    panel_trace(axes[1], "results/35C/eTrC/final/trace_p0p880_nA.csv", "35 °C rheobase: 0.88 nA", AXON,
                (-75, 30))
    fig.suptitle("eTrC phenotype retained after mechanism-specific temperature translation", y=1.02,
                 fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    add_source(fig, "MODEL-DERIVED / TEMPERATURE-TRANSLATED PREDICTION — no universal Q10; 500 ms somatic IClamp.")
    save(fig, "13_eTrC_23C_vs_35C.png")

    fig, axes = plt.subplots(2, 2, figsize=(7.7, 6.3), sharex=True, sharey=True)
    specs = [
        ("results/35C/delayed_excitatory/intermediate_current_diagnostic/trace_p0p450_nA.csv", "0.45 nA — 17 spikes, stable"),
        ("results/35C/delayed_excitatory/intermediate_current_diagnostic/trace_p0p550_nA.csv", "0.55 nA — 2 spikes, block"),
        ("results/35C/delayed_excitatory/initial_translation/trace_p0p750_nA.csv", "0.75 nA — 1 spike, block"),
        ("results/35C/delayed_excitatory/initial_translation/trace_p1p000_nA.csv", "1.00 nA — 1 spike, block"),
    ]
    for ax, (rel, title) in zip(axes.flat, specs):
        panel_trace(ax, rel, title, RED if "block" in title else GREEN, (-75, 15))
    fig.suptitle("Common delayed-excitatory model at 35 °C: failed depolarization-block gate", y=1.01,
                 fontsize=11.5, fontweight="bold", color=RED)
    fig.tight_layout()
    add_source(fig, "TEMPERATURE-TRANSLATED PREDICTION — actual stored traces; yellow band marks the 500 ms stimulus.")
    save(fig, "14_delayed_35C_block_traces.png")

    intermediate = read_metrics("results/35C/delayed_excitatory/intermediate_current_diagnostic/metrics.csv")
    initial = read_metrics("results/35C/delayed_excitatory/initial_translation/metrics.csv")
    merged = {r["amplitude_nA"]: r for r in intermediate}
    merged.update({r["amplitude_nA"]: r for r in initial if r["amplitude_nA"] in {0.75, 1.0}})
    rows = [merged[k] for k in sorted(merged)]
    x = [r["amplitude_nA"] for r in rows]
    spikes = [r["spike_count"] for r in rows]
    late = [r["late_step_mean_voltage_mV"] for r in rows]
    blocks = [r["depolarization_block_flag"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(7.2, 4.1))
    colors = [RED if b else GREEN for b in blocks]
    ax1.bar(x, spikes, width=0.055, color=colors, alpha=0.85, label="spike count")
    ax1.set_xlabel("Injected current (nA)")
    ax1.set_ylabel("Spike count")
    ax2 = ax1.twinx()
    ax2.plot(x, late, "o-", color=NAVY, lw=1.6, label="late-step mean Vm")
    ax2.axhline(-40, color=RED, ls="--", lw=0.9, label="block criterion component: Vm > -40 mV")
    ax2.set_ylabel("Late-step mean Vm (mV)")
    ax1.set_title("Transition from stable delayed firing to depolarization block at 35 °C")
    handles = [Rectangle((0, 0), 1, 1, color=GREEN, label="no block"),
               Rectangle((0, 0), 1, 1, color=RED, label="block"),
               Line2D([0], [0], color=NAVY, marker="o", label="late-step mean Vm")]
    ax1.legend(handles=handles, frameon=False, loc="upper right")
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    add_source(fig, "TEMPERATURE-TRANSLATED PREDICTION — combined intermediate-current and initial-translation summaries.")
    save(fig, "15_depolarization_block_transition.png")

    variants = [
        ("baseline", "Baseline"),
        ("sodium_minus10pct", "Na -10%"),
        ("sodium_plus10pct", "Na +10%"),
        ("sodium_plus20pct", "Na +20%"),
        ("KDRI_plus10pct", "KDRI +10%"),
        ("HH2K_plus10pct", "HH2 K +10%"),
        ("borgka_plus10pct", "A-type K +10%"),
    ]
    currents = [0.45, 0.55, 0.75]
    matrix = np.full((len(variants), len(currents)), np.nan)
    block = np.zeros_like(matrix, dtype=bool)
    for i, (folder, _) in enumerate(variants):
        rows = read_metrics(f"results/35C/delayed_excitatory/one_factor_block_diagnostics/{folder}/metrics.csv")
        by_amp = {round(r["amplitude_nA"], 2): r for r in rows}
        for j, amp in enumerate(currents):
            if amp in by_amp:
                matrix[i, j] = by_amp[amp]["spike_count"]
                block[i, j] = bool(by_amp[amp]["depolarization_block_flag"])
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=np.nanmax(matrix))
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if np.isnan(matrix[i, j]):
                txt = "not tested"
            else:
                txt = f"{int(matrix[i, j])} spikes\n" + ("BLOCK" if block[i, j] else "no block")
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.5,
                    color="white" if matrix[i, j] > np.nanmax(matrix) * 0.45 else NAVY,
                    fontweight="bold" if block[i, j] else "normal")
            if block[i, j]:
                ax.add_patch(Rectangle((j - 0.49, i - 0.49), 0.98, 0.98, fill=False,
                                       edgecolor=RED, linewidth=2.0))
    ax.set_xticks(range(len(currents)), [f"{x:g} nA" for x in currents])
    ax.set_yticks(range(len(variants)), [v[1] for v in variants])
    ax.set_title("One-factor 35 °C diagnostics: none restored stable firing across the range")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label("Spike count")
    add_source(fig, "MODEL-DERIVED DIAGNOSTICS — red outline marks the configured depolarization-block flag.")
    save(fig, "16_one_factor_diagnostics.png")

    mechanisms = ["HH2", "borgka", "iKCa", "B_Na", "KDRI", "Ca dynamics", "Synapses", "pas"]
    category = [2, 2, 2, 1, 1, 0, 0, 0]
    colors = [GREEN if c == 2 else GOLD if c == 1 else GRAY for c in category]
    labels = ["effective", "effective", "effective", "computed but not applied to tau",
              "Q10 commented out", "no celsius use", "no celsius use", "no kinetic scaling"]
    fig, ax = plt.subplots(figsize=(7.3, 4.4))
    y = np.arange(len(mechanisms))
    ax.barh(y, [1] * len(y), color=colors, height=0.62)
    ax.set_yticks(y, mechanisms)
    ax.set_xlim(0, 1.42)
    ax.set_xticks([])
    ax.invert_yaxis()
    for yi, lab in zip(y, labels):
        ax.text(0.03, yi, lab, va="center", ha="left", color="white", fontsize=8,
                fontweight="bold" if "effective" == lab else "normal")
    ax.text(1.04, 0.5, "NO UNIVERSAL Q10\nWAS APPLIED", transform=ax.transAxes,
            ha="center", va="center", fontsize=9, fontweight="bold", color=RED,
            bbox=dict(boxstyle="round,pad=0.45", fc=PALE_RED, ec=RED))
    ax.set_title("Mechanism-specific temperature audit")
    ax.spines[:].set_visible(False)
    add_source(fig, "SOURCE-CODE AUDIT — current MOD files and accepted post-HH2 runtime probe.")
    save(fig, "17_temperature_audit_summary.png")


def figure_schematics():
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    status_box(ax, (0.03, 0.36), 0.25, 0.30, "L292-E1-LCN", "shared reconstructed\nmorphology scaffold", PALE_BLUE, NAVY)
    status_box(ax, (0.39, 0.59), 0.23, 0.22, "EXinitialRule", "eTrC only", PALE_GREEN, GREEN)
    status_box(ax, (0.39, 0.18), 0.23, 0.22, "common delayed rule", "shared by five\npopulation labels", PALE_RED, RED)
    arrow(ax, (0.28, 0.52), (0.39, 0.70)); arrow(ax, (0.28, 0.48), (0.39, 0.29))
    for y, label, edge in [(0.74, "eTrC", GREEN), (0.50, "ePKCgamma  •  eVGLUT3", RED),
                           (0.30, "eDOR  •  eSST  •  eCR", RED)]:
        status_box(ax, (0.70, y - 0.07), 0.27, 0.14, label,
                   "computational population\nidentity", "white", edge)
    arrow(ax, (0.62, 0.70), (0.70, 0.74), GREEN)
    arrow(ax, (0.62, 0.29), (0.70, 0.50), RED)
    arrow(ax, (0.62, 0.29), (0.70, 0.30), RED)
    ax.set_title("Six-population interpretation: one morphology scaffold, two intrinsic architectures",
                 fontsize=12, fontweight="bold", color=NAVY)
    add_source(fig, "MEDLOCK-DERIVED population mapping; not a claim that L292-E1 expresses all six molecular identities.")
    save(fig, "18_six_population_mapping.png")

    gates = [
        ("Morphology QA", "PASS", GREEN), ("Mechanism compile", "PASS", GREEN),
        ("Passive 23 °C", "PASS", GREEN), ("eTrC 23 °C", "PASS", GREEN),
        ("Delayed 23 °C", "PASS", GREEN), ("Temperature audit", "PASS", GREEN),
        ("eTrC 35 °C", "PASS", GREEN), ("Delayed 35 °C", "FAIL", RED),
        ("Six models / synapses / network", "GATED", GRAY),
    ]
    fig, ax = plt.subplots(figsize=(7.5, 7.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ys = np.linspace(0.91, 0.09, len(gates))
    for idx, ((name, stat, color), y) in enumerate(zip(gates, ys)):
        fill = PALE_GREEN if stat == "PASS" else PALE_RED if stat == "FAIL" else "#EEF1F3"
        status_box(ax, (0.20, y - 0.038), 0.60, 0.076, name, stat, fill, color)
        if idx < len(gates) - 1:
            arrow(ax, (0.50, y - 0.040), (0.50, ys[idx + 1] + 0.040), color)
    ax.set_title("Readiness-gate sequence", fontsize=12, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.01, "The failed delayed 35 °C gate correctly prevents downstream claims.",
            ha="center", color=RED, fontweight="bold", fontsize=9)
    add_source(fig, "PROJECT VALIDATION LOGIC — build order preserved; downstream stages were not run.")
    save(fig, "19_readiness_gate_flow.png")

    fig, ax = plt.subplots(figsize=(7.5, 3.7))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    status_box(ax, (0.04, 0.31), 0.27, 0.36, "L292-E1-LCN", "excitatory interneuron\nmorphology scaffold\nCURRENT REPORT", PALE_BLUE, BLUE)
    status_box(ax, (0.365, 0.31), 0.27, 0.36, "L571-LCN", "inhibitory interneuron\nseparate workspace", "#F1ECFA", "#6E4AA5")
    status_box(ax, (0.69, 0.31), 0.27, 0.36, "L796-ALT-PN", "projection neuron\nseparate workspace", PALE_GOLD, GOLD)
    ax.text(0.5, 0.82, "Principal spinal dorsal-horn cell-model components", ha="center",
            fontsize=12, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.15, "Component inventory only — no synaptic connectivity is asserted or validated here.",
            ha="center", fontsize=9, color=RED, fontweight="bold")
    add_source(fig, "PROJECT SCOPE SCHEMATIC — labels reflect workspace roles, not a validated circuit diagram.")
    save(fig, "20_three_neuron_project_components.png")


def main():
    figure_morphologies()
    figure_passive()
    figure_etrc_23()
    figure_delayed_23()
    figure_temperature_and_failure()
    figure_schematics()
    generated = sorted(OUT.glob("*.png"))
    print(f"FIGURES: {len(generated)}")
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
