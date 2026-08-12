#!/usr/bin/env python3

import os
import re
import sys
import pandas as pd
import requests
from tqdm import tqdm

if len(sys.argv) < 4:
    print("Usage: python scripts/download_swc_from_csv.py input.csv output_dir limit")
    sys.exit(1)

csv_file = sys.argv[1]
outdir = sys.argv[2]
limit = int(sys.argv[3])

os.makedirs(outdir, exist_ok=True)

df = pd.read_csv(csv_file, low_memory=False)

if limit > 0:
    df = df.head(limit)

if "swc_source_url" not in df.columns:
    raise SystemExit("ERROR: swc_source_url column not found")

def clean_name(x):
    x = str(x)
    x = re.sub(r"[^A-Za-z0-9_.-]+", "_", x)
    return x[:120]

success = 0
failed = 0

for _, row in tqdm(df.iterrows(), total=len(df), desc="Downloading SWC"):
    name = clean_name(row.get("neuron_name", row.get("neuron_id", "neuron")))
    url = str(row.get("swc_source_url", ""))

    if not url.startswith("http"):
        print("Invalid URL:", name, url)
        failed += 1
        continue

    outfile = os.path.join(outdir, name + ".swc")

    try:
        r = requests.get(url, timeout=40)
        r.raise_for_status()

        text = r.text.strip()
        if len(text) < 20:
            raise ValueError("Downloaded file too small")

        with open(outfile, "w", encoding="utf-8") as f:
            f.write(text + "\n")

        success += 1

    except Exception as e:
        print("FAILED:", name, e)
        failed += 1

print("\nSuccess:", success)
print("Failed:", failed)
print("Output:", outdir)
