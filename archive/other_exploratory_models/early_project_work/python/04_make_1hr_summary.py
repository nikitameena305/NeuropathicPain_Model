from pathlib import Path
import pandas as pd

Path("notes").mkdir(exist_ok=True)

summary = []

summary.append("# 1-Hour Computational Sprint Summary\n")
summary.append("## Project\n")
summary.append("Computational neuropathic pain model using NEURON: DRG hyperexcitability + SDH output.\n")

summary.append("## Completed computational outputs\n")
summary.append("1. NEURON Ball-and-Stick AP demo generated.\n")
summary.append("   - Figure: figures/01_ball_stick_AP_demo.png\n")
summary.append("   - Metrics: results/ball_stick_ap_metrics.txt\n\n")

summary.append("2. DRG normal vs neuropathic-like firing model generated.\n")
summary.append("   - Figure: figures/02_DRG_normal_vs_neuropathic.png\n")
summary.append("   - Metrics: results/02_DRG_normal_vs_neuropathic_metrics.csv\n\n")

summary.append("3. SDH normal vs neuropathic-like output model generated.\n")
summary.append("   - Figure: figures/03_SDH_normal_vs_neuropathic_output.png\n")
summary.append("   - Metrics: results/03_SDH_normal_vs_neuropathic_metrics.csv\n\n")

summary.append("## Biological interpretation\n")
summary.append("""
Normal pain circuit:
- DRG has balanced sodium and potassium conductance.
- Weak stimulus produces low/controlled firing.
- SDH receives moderate AMPA/NMDA excitation.
- GABA/glycine-like inhibition is strong.
- Final SDH projection output remains controlled.

Neuropathic-like pain circuit:
- DRG sodium conductance is increased and potassium conductance is reduced.
- Same weak stimulus produces increased firing.
- SDH receives stronger AMPA/NMDA excitation.
- GABA/glycine-like inhibition is reduced, representing disinhibition.
- Final SDH output is larger and more persistent.

Clinical mapping:
- Weak stimulus causing strong output = allodynia-like behavior.
- Larger response to same input = hyperalgesia-like behavior.
- Persistent output after input = after-discharge-like behavior.
""")

summary.append("## Important limitation\n")
summary.append("""
These are fast teaching/prototype models, not final validated ModelDB reconstructions.
The project document requires ModelDB 267056 and ModelDB 2018004 outputs separately.
If those cannot be completed within the sprint, report this honestly as pending/fallback.
""")

# Include metrics if available
for title, file in [
    ("Ball-stick AP metrics", "results/ball_stick_ap_metrics.txt"),
    ("DRG metrics", "results/02_DRG_normal_vs_neuropathic_metrics.csv"),
    ("SDH metrics", "results/03_SDH_normal_vs_neuropathic_metrics.csv"),
]:
    summary.append(f"\n## {title}\n")
    p = Path(file)
    if p.exists():
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            summary.append(df.to_markdown(index=False))
            summary.append("\n")
        else:
            summary.append("```text\n" + p.read_text() + "\n```\n")
    else:
        summary.append(f"Missing: {file}\n")

Path("notes/ONE_HOUR_COMPUTATIONAL_SUMMARY.md").write_text("\n".join(summary))
print("Saved notes/ONE_HOUR_COMPUTATIONAL_SUMMARY.md")
