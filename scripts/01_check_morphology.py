from pathlib import Path
import pandas as pd
import neurom as nm
from neurom import features as nf

MORPH_FILE = Path("morphologies/L360.swc")
OUT = Path("results/morphology/morphology_report.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

m = nm.load_morphology(str(MORPH_FILE))

report = {
    "file": MORPH_FILE.name,
    "soma_radius_um": None,
    "total_neurite_length_um": None,
    "n_neurites": None,
    "n_sections": None,
}

try:
    report["soma_radius_um"] = float(nf.get("soma_radius", m))
except Exception:
    report["soma_radius_um"] = "NA"

try:
    report["total_neurite_length_um"] = float(nf.get("total_length", m))
except Exception:
    report["total_neurite_length_um"] = "NA"

try:
    report["n_neurites"] = int(nf.get("number_of_neurites", m))
except Exception:
    report["n_neurites"] = "NA"

try:
    report["n_sections"] = int(nf.get("number_of_sections", m))
except Exception:
    report["n_sections"] = "NA"

df = pd.DataFrame([report])
df.to_csv(OUT, index=False)

print(df.to_string(index=False))
print(f"\nSaved: {OUT}")
