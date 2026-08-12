import pandas as pd
import sys
from pathlib import Path

input_csv = sys.argv[1]
output_csv = sys.argv[2]
target_region = sys.argv[3].lower() if len(sys.argv) > 3 else "dorsal horn"

df = pd.read_csv(input_csv, escapechar="\\")

# Make sure important columns exist
for col in [
    "neuron_name", "species", "brain_region", "cell_type",
    "domain", "physical_integrity", "stain",
    "soma_surface", "primary_branches",
    "reconstruction_software",
    "swc_standardized_url", "swc_source_url"
]:
    if col not in df.columns:
        df[col] = ""

# Convert to string safely
for col in df.columns:
    df[col] = df[col].astype(str)

def contains(text, word):
    return word.lower() in str(text).lower()

# ----------------------------
# 1. Basic filtering
# ----------------------------

filtered = df.copy()

# Correct or related brain region
filtered = filtered[filtered["brain_region"].str.lower().str.contains(target_region, na=False)]

# Dendrites required
filtered = filtered[filtered["domain"].str.lower().str.contains("dendrite", na=False)]

# Keep complete or dendrites-only usable neurons
filtered = filtered[
    filtered["physical_integrity"].str.lower().str.contains("complete|dendrites", na=False)
]

# Exclude unknown reconstruction software if available
filtered = filtered[
    ~filtered["reconstruction_software"].str.lower().str.contains("unknown", na=False)
]

# Prefer rows that have standardized SWC URL
filtered = filtered[filtered["swc_standardized_url"].str.len() > 10]

# ----------------------------
# 2. Scoring function
# ----------------------------

def score_row(row):
    score = 0

    brain_region = row.get("brain_region", "").lower()
    species = row.get("species", "").lower()
    integrity = row.get("physical_integrity", "").lower()
    stain = row.get("stain", "").lower()

    try:
        branches = float(row.get("primary_branches", 0))
    except:
        branches = 0

    # Brain region match: 40
    if target_region in brain_region:
        score += 40
    elif "spinal cord" in brain_region:
        score += 20

    # Species: 20
    if "rat" in species:
        score += 20
    elif "mouse" in species:
        score += 18
    elif any(x in species for x in ["human", "macaque", "monkey", "cat", "rabbit"]):
        score += 10

    # Physical integrity: 20
    if "complete" in integrity:
        score += 20
    elif "dendrites" in integrity:
        score += 12

    # Branch richness: 10
    if branches >= 5:
        score += 10
    elif branches >= 3:
        score += 5

    # Stain quality: 10
    if "biocytin" in stain or "neurobiotin" in stain:
        score += 10
    elif "lucifer" in stain:
        score += 7
    elif "dye" in stain:
        score += 5

    return score

filtered["suitability_score"] = filtered.apply(score_row, axis=1)

# Convert numeric columns
for col in ["soma_surface", "primary_branches"]:
    filtered[col] = pd.to_numeric(filtered[col], errors="coerce")

# Flag possible soma problems
filtered["soma_warning"] = filtered["soma_surface"].apply(
    lambda x: "CHECK_SOMA_SMALL" if pd.notna(x) and x < 200 else ""
)

filtered = filtered.sort_values("suitability_score", ascending=False)

# Save output
Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
filtered.to_csv(output_csv, index=False)

print(f"\nInput rows: {len(df)}")
print(f"Filtered rows: {len(filtered)}")
print(f"Saved: {output_csv}")

show_cols = [
    "neuron_name", "species", "brain_region", "cell_type",
    "physical_integrity", "domain", "stain",
    "soma_surface", "primary_branches",
    "suitability_score", "soma_warning",
    "swc_standardized_url"
]

available = [c for c in show_cols if c in filtered.columns]
print("\nTop candidates:")
print(filtered[available].head(20).to_string(index=False))
