from pathlib import Path
import pandas as pd

candidates = list(Path("metadata").glob("*.csv")) + list(Path("selected").glob("*.csv"))

print("CSV files found:")
for c in candidates:
    print(" -", c)

frames = []
for c in candidates:
    try:
        df = pd.read_csv(c, escapechar="\\")
        df["source_file"] = str(c)
        frames.append(df)
    except Exception as e:
        print("Skipping", c, e)

if not frames:
    raise SystemExit("No CSV files found in metadata/ or selected/")

df = pd.concat(frames, ignore_index=True)

# Normalize missing columns
needed = [
    "neuron_name","species","brain_region","cell_type","soma_surface",
    "domain","physical_integrity","total_length","primary_branches",
    "swc_standardized_url","neuron_page_url","source_file"
]
for col in needed:
    if col not in df.columns:
        df[col] = ""

for col in df.columns:
    df[col] = df[col].astype(str)

# DRG entries
drg = df[df["brain_region"].str.lower().str.contains("dorsal root ganglion|drg", na=False)].copy()

# If exact DRG absent, try peripheral nervous system as possible DRG-related but flag it
if len(drg) < 5:
    alt = df[df["brain_region"].str.lower().str.contains("peripheral nervous system", na=False)].copy()
    alt["note"] = "Not exact DRG; review manually"
    drg = pd.concat([drg, alt], ignore_index=True)

drg["table_group"] = "DRG"
drg = drg.drop_duplicates(subset=["neuron_name"]).head(5)

# SDH/spinal cord entries
sdh = df[
    df["brain_region"].str.lower().str.contains("dorsal horn|spinal cord", na=False) |
    df["cell_type"].str.lower().str.contains("interneuron|projection", na=False)
].copy()

sdh["table_group"] = "SDH"
sdh = sdh.drop_duplicates(subset=["neuron_name"]).head(3)

out = pd.concat([drg, sdh], ignore_index=True)

cols = [
    "table_group","neuron_name","species","brain_region","cell_type",
    "soma_surface","domain","physical_integrity","total_length",
    "primary_branches","swc_standardized_url","neuron_page_url",
    "source_file"
]

out = out[cols]
out.to_csv("results/neuromorpho_week1_table.csv", index=False)

print("\nWeek 1 NeuroMorpho table:")
print(out.to_string(index=False))
print("\nSaved: results/neuromorpho_week1_table.csv")

if len(drg) < 5:
    print("\nWARNING: fewer than 5 exact DRG entries. Use fallback statement.")
if len(sdh) < 3:
    print("\nWARNING: fewer than 3 SDH/spinal cord entries. Use fallback statement.")
