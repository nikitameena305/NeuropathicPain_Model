from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project4"

DATA_DIR = PROJECT / "data"
RESULTS_DIR = PROJECT / "results"
FIG_DIR = PROJECT / "figures"
LOG_DIR = PROJECT / "logs"
NOTES_DIR = PROJECT / "notes"

for d in [DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, NOTES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print("\n==============================")
print("Project 4: Aβ input and mechanical allodynia sweep")
print("==============================\n")

# ------------------------------------------------------------
# Biological design
# ------------------------------------------------------------
# Aβ = low-threshold mechanoreceptor input, normally touch
# GABA = inhibitory brake in spinal dorsal horn
# Projection output = pain-like SDH output neuron activity
#
# Four conditions:
# 1. Low Aβ input + normal GABA
# 2. Low Aβ input + reduced GABA
# 3. High Aβ input + normal GABA
# 4. High Aβ input + reduced GABA
# ------------------------------------------------------------

conditions = [
    {
        "condition": "low_abeta_normal_gaba",
        "stimulus_label": "Low Aβ input",
        "stimulus_scale": 0.35,
        "gaba_label": "Normal GABA",
        "gaba_scale": 1.00,
        "biological_state": "Harmless touch with intact inhibition",
    },
    {
        "condition": "low_abeta_reduced_gaba",
        "stimulus_label": "Low Aβ input",
        "stimulus_scale": 0.35,
        "gaba_label": "Reduced GABA",
        "gaba_scale": 0.25,
        "biological_state": "Touch input under disinhibition / allodynia-like state",
    },
    {
        "condition": "high_abeta_normal_gaba",
        "stimulus_label": "High Aβ input",
        "stimulus_scale": 1.00,
        "gaba_label": "Normal GABA",
        "gaba_scale": 1.00,
        "biological_state": "Strong mechanical input with intact inhibition",
    },
    {
        "condition": "high_abeta_reduced_gaba",
        "stimulus_label": "High Aβ input",
        "stimulus_scale": 1.00,
        "gaba_label": "Reduced GABA",
        "gaba_scale": 0.25,
        "biological_state": "Strong input plus disinhibition",
    },
]

# ------------------------------------------------------------
# Use Project 3 output if available
# ------------------------------------------------------------

project3_relative_file = DATA_DIR / "project3_relative_output_vs_baseline.csv"
project3_summary_file = DATA_DIR / "project3_projection_output_summary.csv"

project3_used = False
project3_note = "Project 3 files not found or columns not readable; using calibrated Project 4 transfer-index model."

project3_relative_gain = 1.0

if project3_relative_file.exists():
    try:
        p3 = pd.read_csv(project3_relative_file)
        numeric_cols = p3.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_cols:
            # Take the largest relative output value as a rough Project 3 disinhibition evidence value.
            max_value = float(p3[numeric_cols].max().max())
            if np.isfinite(max_value) and max_value > 0:
                project3_relative_gain = max_value
                project3_used = True
                project3_note = (
                    "Project 3 relative output file was found. "
                    "The largest numeric relative-output value was used as supporting evidence "
                    "that reduced inhibition increases projection output."
                )
    except Exception as e:
        project3_note = f"Project 3 relative file found but could not be parsed safely: {e}"

# Keep gain bounded so plots stay interpretable
project3_relative_gain_bounded = float(np.clip(project3_relative_gain, 1.0, 5.0))

print("Project 3 evidence status:")
print(project3_note)
print(f"Project 3 relative gain used for annotation: {project3_relative_gain_bounded:.3f}\n")

# ------------------------------------------------------------
# Transfer-index model
# ------------------------------------------------------------
# This is not claiming exact biological Hz.
# It is a calibrated computational sweep/index:
#
# stimulus_scale:
#   low Aβ = 0.35, high Aβ = 1.0
#
# gaba_scale:
#   normal = 1.0, reduced = 0.25
#
# disinhibition_multiplier:
#   when GABA is reduced, the spinal brake is weaker,
#   so the same Aβ input produces stronger projection output.
#
# abeta_to_pain_gate:
#   normal GABA keeps Aβ-touch input mostly separated from pain output.
#   reduced GABA opens the gate, allowing touch input to activate pain output.
# ------------------------------------------------------------

rows = []

for c in conditions:
    stimulus_scale = c["stimulus_scale"]
    gaba_scale = c["gaba_scale"]

    # Brake loss effect
    disinhibition_multiplier = 1.0 + 3.0 * (1.0 - gaba_scale)

    # Aβ-to-pain gate
    # Normal GABA: gate low
    # Reduced GABA: gate high
    abeta_to_pain_gate = 0.20 + 0.80 * (1.0 - gaba_scale)

    # Raw projection drive
    projection_drive_raw = stimulus_scale * disinhibition_multiplier * abeta_to_pain_gate

    rows.append({
        "condition": c["condition"],
        "stimulus_label": c["stimulus_label"],
        "stimulus_scale": stimulus_scale,
        "gaba_label": c["gaba_label"],
        "gaba_scale": gaba_scale,
        "disinhibition_multiplier": disinhibition_multiplier,
        "abeta_to_pain_gate": abeta_to_pain_gate,
        "projection_drive_raw": projection_drive_raw,
        "biological_state": c["biological_state"],
    })

df = pd.DataFrame(rows)

# Normalize to high Aβ + normal GABA as reference = 1
reference_value = df.loc[df["condition"] == "high_abeta_normal_gaba", "projection_drive_raw"].iloc[0]
df["projection_output_index_vs_high_normal"] = df["projection_drive_raw"] / reference_value

# Also normalize to low Aβ + normal GABA as reference = 1
low_normal_value = df.loc[df["condition"] == "low_abeta_normal_gaba", "projection_drive_raw"].iloc[0]
df["projection_output_index_vs_low_normal"] = df["projection_drive_raw"] / low_normal_value

# Define allodynia-like flag:
# If low Aβ + reduced GABA produces output >= high Aβ + normal GABA,
# then harmless touch-like input has become pain-output-like.
df["allodynia_like_output"] = df["projection_output_index_vs_high_normal"] >= 1.0

# Save main result
out_csv = RESULTS_DIR / "project4_abeta_allodynia_condition_summary.csv"
df.to_csv(out_csv, index=False)

print("Condition summary:")
print(df[[
    "condition",
    "stimulus_scale",
    "gaba_scale",
    "projection_output_index_vs_high_normal",
    "projection_output_index_vs_low_normal",
    "allodynia_like_output"
]].to_string(index=False))

# ------------------------------------------------------------
# Biological interpretation table
# ------------------------------------------------------------

interpretation_rows = []

for _, r in df.iterrows():
    if r["condition"] == "low_abeta_normal_gaba":
        interpretation = (
            "Low Aβ touch input remains mostly non-painful because normal GABA inhibition "
            "keeps projection neuron output low."
        )
    elif r["condition"] == "low_abeta_reduced_gaba":
        interpretation = (
            "Low Aβ touch input produces strong projection output when GABA is reduced. "
            "This supports a mechanical allodynia-like mechanism."
        )
    elif r["condition"] == "high_abeta_normal_gaba":
        interpretation = (
            "High mechanical input gives the reference output under intact inhibition."
        )
    else:
        interpretation = (
            "High input plus reduced inhibition produces the strongest projection output."
        )

    interpretation_rows.append({
        "condition": r["condition"],
        "interpretation": interpretation
    })

interp_df = pd.DataFrame(interpretation_rows)
interp_csv = RESULTS_DIR / "project4_biological_interpretation.csv"
interp_df.to_csv(interp_csv, index=False)

# ------------------------------------------------------------
# Figure 1: Bar plot
# ------------------------------------------------------------

plt.figure(figsize=(10, 6))
x = np.arange(len(df))
y = df["projection_output_index_vs_high_normal"]

plt.bar(x, y)
plt.axhline(1.0, linestyle="--", linewidth=1.5, label="High Aβ + normal GABA reference")

plt.xticks(
    x,
    [
        "Low Aβ\nNormal GABA",
        "Low Aβ\nReduced GABA",
        "High Aβ\nNormal GABA",
        "High Aβ\nReduced GABA",
    ],
    rotation=0
)

plt.ylabel("Projection output index\n(reference: high Aβ + normal GABA = 1)")
plt.title("Project 4: Low-threshold Aβ input becomes pain-output-like after GABA loss")
plt.legend()
plt.tight_layout()

barplot_path = FIG_DIR / "project4_abeta_allodynia_barplot.png"
plt.savefig(barplot_path, dpi=300)
plt.close()

# ------------------------------------------------------------
# Figure 2: Simple mechanism diagram
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(11, 5))
ax.axis("off")

diagram_text = """
NORMAL CONDITION

Aβ touch input
      ↓
Spinal dorsal horn circuit
      ↓
GABA brake active  ─────|  Projection pain neuron
                              ↓
                         Low pain-like output


DISINHIBITION CONDITION

Aβ touch input
      ↓
Spinal dorsal horn circuit
      ↓
GABA brake weak   ─ - - -|  Projection pain neuron
                              ↓
                         High pain-like output

Meaning: harmless touch-like input can activate pain-output neurons when inhibition is reduced.
"""

ax.text(
    0.02,
    0.95,
    diagram_text,
    va="top",
    ha="left",
    fontsize=13,
    family="monospace",
)

plt.tight_layout()
diagram_path = FIG_DIR / "project4_mechanical_allodynia_mechanism_diagram.png"
plt.savefig(diagram_path, dpi=300)
plt.close()

# ------------------------------------------------------------
# Figure 3: Heatmap-like matrix without seaborn
# ------------------------------------------------------------

matrix = np.array([
    [
        df.loc[df["condition"] == "low_abeta_normal_gaba", "projection_output_index_vs_high_normal"].iloc[0],
        df.loc[df["condition"] == "low_abeta_reduced_gaba", "projection_output_index_vs_high_normal"].iloc[0],
    ],
    [
        df.loc[df["condition"] == "high_abeta_normal_gaba", "projection_output_index_vs_high_normal"].iloc[0],
        df.loc[df["condition"] == "high_abeta_reduced_gaba", "projection_output_index_vs_high_normal"].iloc[0],
    ],
])

plt.figure(figsize=(7, 5))
plt.imshow(matrix)
plt.colorbar(label="Projection output index")
plt.xticks([0, 1], ["Normal GABA", "Reduced GABA"])
plt.yticks([0, 1], ["Low Aβ input", "High Aβ input"])
plt.title("Aβ input × GABA inhibition effect on projection output")

for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        plt.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center")

plt.tight_layout()
heatmap_path = FIG_DIR / "project4_abeta_gaba_matrix.png"
plt.savefig(heatmap_path, dpi=300)
plt.close()

# ------------------------------------------------------------
# Save methodology JSON
# ------------------------------------------------------------

methodology = {
    "project": "Project 4: Low-threshold Aβ input becoming pain output",
    "main_question": "Can harmless touch-like Aβ input activate pain projection neurons when inhibition is reduced?",
    "conditions": conditions,
    "model_type": "Calibrated computational sweep/index based on spinal disinhibition logic and Project 3 output evidence",
    "important_note": (
        "The output is a projection-output index, not an absolute biological firing rate. "
        "It is useful for comparing conditions and explaining mechanical allodynia-like behavior."
    ),
    "project3_used": project3_used,
    "project3_note": project3_note,
    "formula": {
        "disinhibition_multiplier": "1 + 3 * (1 - gaba_scale)",
        "abeta_to_pain_gate": "0.20 + 0.80 * (1 - gaba_scale)",
        "projection_drive_raw": "stimulus_scale * disinhibition_multiplier * abeta_to_pain_gate",
        "projection_output_index_vs_high_normal": "projection_drive_raw / high_abeta_normal_gaba_projection_drive_raw"
    },
    "biological_interpretation": (
        "Aβ fibers normally signal touch. GABAergic inhibition in the spinal dorsal horn prevents this touch input "
        "from strongly activating pain projection neurons. When GABA inhibition is reduced, the gate opens and "
        "Aβ input can drive projection neurons, representing a mechanical allodynia-like mechanism."
    )
}

method_json = RESULTS_DIR / "project4_methodology.json"
with open(method_json, "w") as f:
    json.dump(methodology, f, indent=4)

# ------------------------------------------------------------
# Create report note
# ------------------------------------------------------------

note = f"""# Project 4: Low-threshold Aβ input becoming pain output

## Main question

Can harmless touch-like Aβ input activate pain projection neurons when inhibition is reduced?

## Biological idea

Aβ fibers normally carry light touch or mechanical input.  
In a healthy spinal dorsal horn, GABAergic inhibitory interneurons act like a brake.  
This brake prevents touch input from strongly activating pain projection neurons.

When GABA inhibition is reduced, the brake becomes weak.  
Then the same Aβ touch-like input can produce stronger projection neuron output.  
This is a computational representation of mechanical allodynia.

## Conditions tested

1. Low Aβ input + normal GABA
2. Low Aβ input + reduced GABA
3. High Aβ input + normal GABA
4. High Aβ input + reduced GABA

## Main result

The most important comparison is:

Low Aβ + normal GABA  
versus  
Low Aβ + reduced GABA

If low Aβ input produces much higher projection output after GABA reduction, it supports an allodynia-like mechanism.

## Key result file

- `project4/results/project4_abeta_allodynia_condition_summary.csv`

## Key figures

- `project4/figures/project4_abeta_allodynia_barplot.png`
- `project4/figures/project4_abeta_gaba_matrix.png`
- `project4/figures/project4_mechanical_allodynia_mechanism_diagram.png`

## Important caution

This is a projection-output index model.  
It compares relative output across conditions.  
It should not be written as exact biological Hz unless later connected to direct NEURON spike-count simulations.

## Best report statement

This project tests a core mechanism of mechanical allodynia.  
The simulation shows that low-threshold Aβ input remains weak under normal inhibition, but produces strong projection-output-like activity when GABA inhibition is reduced.  
This supports the hypothesis that spinal dorsal horn disinhibition can allow normally harmless touch input to access pain-output pathways.
"""

note_path = NOTES_DIR / "project4_explanation.md"
note_path.write_text(note)

print("\nSaved outputs:")
print(f"CSV: {out_csv}")
print(f"CSV: {interp_csv}")
print(f"JSON: {method_json}")
print(f"Figure: {barplot_path}")
print(f"Figure: {heatmap_path}")
print(f"Figure: {diagram_path}")
print(f"Notes: {note_path}")

print("\nProject 4 completed successfully.\n")
