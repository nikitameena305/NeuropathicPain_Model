import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

outdir = Path("deliverables/advanced")
outdir.mkdir(parents=True, exist_ok=True)

inhibition_levels = np.array([1.0, 0.75, 0.5, 0.25, 0.1])
baseline_output = 20

rows = []
for inh in inhibition_levels:
    # simple conceptual model: less inhibition = higher output
    sdh_output = baseline_output / inh
    rows.append({
        "relative_GABA_inhibition": inh,
        "predicted_SDH_output_Hz": sdh_output,
        "interpretation": "less inhibition increases SDH output"
    })

df = pd.DataFrame(rows)
df.to_csv(outdir / "GABA_disinhibition_sweep.csv", index=False)

plt.figure(figsize=(7,5))
plt.plot(df["relative_GABA_inhibition"], df["predicted_SDH_output_Hz"], marker="o")
plt.gca().invert_xaxis()
plt.xlabel("Relative GABA inhibition")
plt.ylabel("Predicted SDH output (Hz)")
plt.title("Conceptual GABA disinhibition sweep")
plt.tight_layout()
plt.savefig(outdir / "GABA_disinhibition_sweep.png", dpi=300)

print(df)
print("Saved advanced GABA sweep.")
