from pathlib import Path
import re
import pandas as pd

ROOT = Path.home() / "NeuropathicPain_Model"
MODEL = ROOT / "modeldb" / "2018004"
OUTDIR = ROOT / "deliverables" / "week1"
OUTDIR.mkdir(parents=True, exist_ok=True)

mod_files = sorted(MODEL.rglob("*.mod"))

rows = []

def guess_channel(name, text):
    low = (name + " " + text[:3000]).lower()

    if "nav" in low or "sodium" in low or "ina" in low or " na" in low:
        if "persistent" in low or "nap" in low:
            return "Persistent sodium current / INaP"
        return "Voltage-gated sodium current"
    if "kdr" in low or "potassium" in low or " ik" in low or "kchan" in low:
        return "Voltage-gated potassium current"
    if "leak" in low:
        return "Leak current"
    if "hcn" in low or "ih" in low:
        return "HCN / Ih current"
    if "pas" in low:
        return "Passive leak mechanism"
    if "extracellular" in low:
        return "Extracellular mechanism"
    return "Mechanism unclear - check manually"

for mf in mod_files:
    text = mf.read_text(errors="ignore")

    suffix_match = re.search(r"SUFFIX\s+([A-Za-z0-9_]+)", text)
    point_match = re.search(r"POINT_PROCESS\s+([A-Za-z0-9_]+)", text)
    nonspecific = re.findall(r"NONSPECIFIC_CURRENT\s+([A-Za-z0-9_]+)", text)
    useion = re.findall(r"USEION\s+([A-Za-z0-9_]+)", text)

    mech = None
    if suffix_match:
        mech = suffix_match.group(1)
    elif point_match:
        mech = point_match.group(1)
    else:
        mech = "not_found"

    rows.append({
        "mod_file": str(mf.relative_to(ROOT)),
        "mechanism_name": mech,
        "type": "POINT_PROCESS" if point_match else "DENSITY_MECHANISM",
        "ions_used": ", ".join(sorted(set(useion))) if useion else "",
        "nonspecific_current": ", ".join(sorted(set(nonspecific))) if nonspecific else "",
        "guessed_channel": guess_channel(mf.name, text),
    })

df = pd.DataFrame(rows)

out_csv = OUTDIR / "modeldb2018004_mod_inventory.csv"
out_md = OUTDIR / "modeldb2018004_mod_inventory.md"

df.to_csv(out_csv, index=False)

with open(out_md, "w") as f:
    f.write("# ModelDB 2018004 .mod inventory\n\n")
    if df.empty:
        f.write("No .mod files found.\n")
    else:
        f.write(df.to_markdown(index=False))

print("Found .mod files:", len(df))
print(df.to_string(index=False))
print("\nCreated:")
print(out_csv)
print(out_md)
