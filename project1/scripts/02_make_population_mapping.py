from pathlib import Path
import pandas as pd
import json
import re

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project1"

RESULTS = PROJECT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# Known population sizes from the SDH mechanical stimulation network summary.
# This assumes sequential population construction. We will mark it as inferred.
population_sizes = [
    ("Ab_SAI", 10, "low-threshold mechanoreceptor input"),
    ("Ab_SAII", 10, "low-threshold mechanoreceptor input"),
    ("Ad", 20, "A-delta nociceptive input"),
    ("C_PEP", 80, "peptidergic C-fiber nociceptive input"),
    ("C_NP", 80, "non-peptidergic C-fiber nociceptive input"),
    ("PKC", 10, "excitatory interneuron"),
    ("VGLUT3", 5, "excitatory interneuron"),
    ("PV", 15, "inhibitory interneuron"),
    ("DOR", 15, "inhibitory interneuron"),
    ("TrC", 10, "excitatory/transient central neuron"),
    ("DYN", 10, "inhibitory interneuron"),
    ("SOM", 5, "excitatory/interneuron population"),
    ("CR", 5, "interneuron population"),
    ("ISLET", 1, "inhibitory interneuron"),
    ("NK1", 9, "projection neuron / pain output neuron"),
]

rows = []
cell_id = 0

for pop, n, role in population_sizes:
    for _ in range(n):
        if pop in ["PV", "DOR", "DYN", "ISLET"]:
            broad_class = "inhibitory"
        elif pop in ["NK1"]:
            broad_class = "projection"
        elif pop in ["Ab_SAI", "Ab_SAII", "Ad", "C_PEP", "C_NP"]:
            broad_class = "primary_afferent_input"
        else:
            broad_class = "excitatory_or_interneuron"

        rows.append({
            "cell_id": cell_id,
            "population": pop,
            "broad_class": broad_class,
            "biological_role": role,
            "mapping_status": "inferred_from_population_order"
        })
        cell_id += 1

df = pd.DataFrame(rows)

out = RESULTS / "project1_population_mapping_inferred.csv"
df.to_csv(out, index=False)

print(f"Saved: {out}")
print(df.head())
print()
print("Population counts:")
print(df.groupby(["population", "broad_class"]).size())
print()
print("Total mapped cells:", len(df))
