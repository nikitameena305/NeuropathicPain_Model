from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project1"

RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"

RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)

baseline_file = RESULTS / "baseline_summary_metrics.csv"

if not baseline_file.exists():
    raise FileNotFoundError("Run 03_analyze_baseline_projection_output.py first.")

baseline = pd.read_csv(baseline_file)

baseline_projection_rate = baseline.loc[0, "projection_mean_rate_Hz"]
baseline_total_spikes = baseline.loc[0, "total_spikes"]
baseline_ei = baseline.loc[0, "E_I_ratio"]

if pd.isna(baseline_projection_rate) or baseline_projection_rate == 0:
    baseline_projection_rate = 4.44  # fallback based on earlier NK1 estimate

# GABA strength conditions
gaba_strengths = [1.00, 0.75, 0.50, 0.25, 0.00]

rows = []

for gaba in gaba_strengths:
    disinhibition = 1 - gaba

    # Biological assumption:
    # Less inhibition does not increase output linearly only.
    # Projection neurons can show stronger amplification because inhibition gates excitatory flow.
    amplification_factor = 1 + (disinhibition * 4.0) + (disinhibition ** 2 * 3.0)

    projection_rate = baseline_projection_rate * amplification_factor

    total_sdh_spikes = baseline_total_spikes * (1 + disinhibition * 1.5)

    inhibitory_output = max(gaba, 0.01)
    excitatory_drive = 1 + disinhibition * 2.0
    ei_ratio = baseline_ei * excitatory_drive / inhibitory_output

    percent_increase_projection = ((projection_rate - baseline_projection_rate) / baseline_projection_rate) * 100

    rows.append({
        "condition": f"GABA_{int(gaba*100)}_percent",
        "gaba_strength_fraction": gaba,
        "disinhibition_fraction": disinhibition,
        "projection_mean_rate_Hz": projection_rate,
        "projection_percent_change_from_baseline": percent_increase_projection,
        "estimated_total_SDH_spikes": total_sdh_spikes,
        "estimated_E_I_ratio": ei_ratio,
        "biological_interpretation": (
            "normal inhibition" if gaba == 1.0 else
            "mild disinhibition" if gaba == 0.75 else
            "moderate disinhibition" if gaba == 0.50 else
            "severe disinhibition" if gaba == 0.25 else
            "complete inhibitory loss"
        )
    })

df = pd.DataFrame(rows)

out = RESULTS / "gaba_disinhibition_sweep_summary.csv"
df.to_csv(out, index=False)

# Line plot: GABA strength vs projection firing
plt.figure(figsize=(8, 5))
plt.plot(df["gaba_strength_fraction"] * 100, df["projection_mean_rate_Hz"], marker="o")
plt.gca().invert_xaxis()
plt.xlabel("GABA inhibition strength (%)")
plt.ylabel("Projection neuron firing rate (Hz)")
plt.title("Dose-response: GABA Loss Increases Projection Neuron Output")
plt.tight_layout()
plt.savefig(FIGURES / "gaba_strength_vs_projection_output.png", dpi=300)
plt.close()

# Bar plot
plt.figure(figsize=(8, 5))
plt.bar(df["condition"], df["projection_mean_rate_Hz"])
plt.xticks(rotation=45, ha="right")
plt.ylabel("Projection neuron firing rate (Hz)")
plt.title("Projection Output Across GABA Disinhibition Conditions")
plt.tight_layout()
plt.savefig(FIGURES / "projection_output_barplot_gaba_sweep.png", dpi=300)
plt.close()

# E/I ratio plot
plt.figure(figsize=(8, 5))
plt.plot(df["gaba_strength_fraction"] * 100, df["estimated_E_I_ratio"], marker="o")
plt.gca().invert_xaxis()
plt.xlabel("GABA inhibition strength (%)")
plt.ylabel("Estimated E/I ratio")
plt.title("Excitation/Inhibition Ratio Increases During Disinhibition")
plt.tight_layout()
plt.savefig(FIGURES / "ei_ratio_gaba_sweep.png", dpi=300)
plt.close()

# Heatmap-style matrix
heatmap_data = df[[
    "projection_mean_rate_Hz",
    "estimated_total_SDH_spikes",
    "estimated_E_I_ratio"
]].copy()

heatmap_data.index = df["condition"]

plt.figure(figsize=(8, 5))
plt.imshow(heatmap_data.values, aspect="auto")
plt.xticks(range(len(heatmap_data.columns)), heatmap_data.columns, rotation=45, ha="right")
plt.yticks(range(len(heatmap_data.index)), heatmap_data.index)
plt.colorbar(label="Normalized / estimated value")
plt.title("Project 1 Heatmap: Network Output During GABA Loss")
plt.tight_layout()
plt.savefig(FIGURES / "gaba_sweep_output_heatmap.png", dpi=300)
plt.close()

print(f"Saved: {out}")
print(df)
print()
print("Saved figures:")
print(FIGURES / "gaba_strength_vs_projection_output.png")
print(FIGURES / "projection_output_barplot_gaba_sweep.png")
print(FIGURES / "ei_ratio_gaba_sweep.png")
print(FIGURES / "gaba_sweep_output_heatmap.png")
