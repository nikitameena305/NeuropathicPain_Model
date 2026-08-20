import pandas as pd
import sys

csv_path = sys.argv[1]

# escapechar helps if CSV has JSON-like columns
df = pd.read_csv(csv_path, escapechar="\\")

print("\nFile:", csv_path)
print("Shape:", df.shape)
print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

important_cols = [
    "neuron_name", "species", "brain_region", "cell_type",
    "domain", "physical_integrity", "stain",
    "soma_surface", "total_length", "primary_branches",
    "swc_source_url", "swc_standardized_url"
]

print("\nImportant columns preview:")
available = [c for c in important_cols if c in df.columns]
print(df[available].head(10).to_string(index=False))

if "brain_region" in df.columns:
    print("\nTop brain regions:")
    print(df["brain_region"].value_counts().head(20))

if "species" in df.columns:
    print("\nSpecies counts:")
    print(df["species"].value_counts())

if "physical_integrity" in df.columns:
    print("\nPhysical integrity counts:")
    print(df["physical_integrity"].value_counts())

if "domain" in df.columns:
    print("\nDomain counts:")
    print(df["domain"].value_counts().head(20))
