from pathlib import Path
import shutil

ROOT = Path.home() / "NeuropathicPain_Model"
PROJECT = ROOT / "project1"

possible_files = [
    ROOT / "modeldb" / "267056" / "data" / "100mN_data.json",
    ROOT / "data" / "100mN_data.json",
]

PROJECT_DATA = PROJECT / "data"
PROJECT_DATA.mkdir(parents=True, exist_ok=True)

found = False

for f in possible_files:
    if f.exists():
        out = PROJECT_DATA / "baseline_100mN_data.json"
        shutil.copy2(f, out)
        print(f"Copied baseline data:")
        print(f"FROM: {f}")
        print(f"TO:   {out}")
        found = True
        break

if not found:
    print("ERROR: Could not find 100mN_data.json")
    print("Check where your ModelDB 267056 output is saved.")
    print("Try:")
    print("find ~/NeuropathicPain_Model -name '*100mN*' -o -name '*.json'")
