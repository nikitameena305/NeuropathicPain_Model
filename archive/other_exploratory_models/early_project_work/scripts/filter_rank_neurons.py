#!/usr/bin/env python3

import sys
import pandas as pd

if len(sys.argv) < 4:
    print("Usage: python scripts/filter_rank_neurons.py input.csv output.csv region_keyword")
    sys.exit(1)

input_csv = sys.argv[1]
output_csv = sys.argv[2]
region_keyword = sys.argv[3].lower()

print(f"[input] {input_csv}")
print(f"[output] {output_csv}")
print(f"[region keyword] {region_keyword}")

df = pd.read_csv(input_csv, low_memory=False)

print(f"[loaded] {len(df)} rows")
print(f"[columns found] {len(df.columns)} columns")

def find_col(possible):
    lower_map = {c.lower().replace(" ", "_"): c for c in df.columns}
    for p in possible:
        key = p.lower().replace(" ", "_")
        if key in lower_map:
            return lower_map[key]
    return None

name_col = find_col(["neuron_name", "neuron name", "neuron_id", "archive_name", "name"])
species_col = find_col(["species"])
region_col = find_col(["brain_region", "brain region"])
cell_col = find_col(["cell_type", "cell type"])
stain_col = find_col(["stain", "staining"])
age_col = find_col(["age_classification", "age classification", "age"])
domain_col = find_col(["domain"])
physical_col = find_col(["physical_integrity", "physical integrity"])
structural_col = find_col(["structural_domain", "structural domain"])
soma_col = find_col(["soma_surface", "soma surface"])
archive_col = find_col(["archive"])

def text(row, col):
    if col is None:
        return ""
    val = row.get(col, "")
    if pd.isna(val):
        return ""
    return str(val).lower()

def score_row(row):
    score = 0

    species = text(row, species_col)
    region = text(row, region_col)
    cell = text(row, cell_col)
    stain = text(row, stain_col)
    age = text(row, age_col)
    domain = text(row, domain_col)
    physical = text(row, physical_col)
    structural = text(row, structural_col)
    soma = text(row, soma_col)

    # Region relevance
    if region_keyword in region:
        score += 5
    if "dorsal" in region and "horn" in region:
        score += 5
    if "spinal" in region:
        score += 2

    # Species relevance
    if "rat" in species:
        score += 5
    elif "mouse" in species:
        score += 4
    elif "human" in species:
        score += 2

    # Age relevance
    if "adult" in age:
        score += 3
    elif "young" in age:
        score += 1

    # Cell type relevance
    useful_cells = ["interneuron", "projection", "sensory", "nociceptor", "principal"]
    if any(x in cell for x in useful_cells):
        score += 3

    if "glia" in cell or "astrocyte" in cell:
        score -= 5

    # Morphology quality
    if "dendrite" in domain:
        score += 2
    if "axon" in domain:
        score += 1
    if "complete" in physical:
        score += 3
    if "intact" in physical:
        score += 2
    if "dendrite" in structural:
        score += 2
    if soma not in ["", "nan", "none"]:
        score += 1

    # Stain quality
    useful_stains = ["biocytin", "lucifer", "golgi", "neurobiotin"]
    if any(x in stain for x in useful_stains):
        score += 2

    return score

# Filter by region if brain_region column exists
if region_col:
    region_text = df[region_col].astype(str).str.lower()
    mask = (
        region_text.str.contains(region_keyword, na=False)
        | region_text.str.contains("dorsal", na=False)
        | region_text.str.contains("spinal", na=False)
    )
    filtered = df[mask].copy()
else:
    print("[warning] brain_region column not found, keeping all rows")
    filtered = df.copy()

print(f"[filtered] {len(filtered)} rows")

if len(filtered) == 0:
    print("[warning] No matching neurons found.")
    filtered.to_csv(output_csv, index=False)
    sys.exit(0)

# IMPORTANT: force apply result to be one scalar score per row
scores = []
for _, row in filtered.iterrows():
    scores.append(score_row(row))

filtered["suitability_score"] = scores

filtered = filtered.sort_values("suitability_score", ascending=False)

filtered.to_csv(output_csv, index=False)

print(f"[saved] {output_csv}")

show_cols = []
for c in [name_col, species_col, region_col, cell_col, stain_col, age_col, "suitability_score"]:
    if c and c in filtered.columns:
        show_cols.append(c)

print("\n[top 10 neurons]")
print(filtered[show_cols].head(10).to_string(index=False))
