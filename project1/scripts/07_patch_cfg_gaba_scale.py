from pathlib import Path
import shutil
import re

ROOT = Path.home() / "NeuropathicPain_Model"
MODEL = ROOT / "modeldb" / "267056"

candidate_files = [
    MODEL / "cfg_mechanical.py",
    MODEL / "cfg.py",
    MODEL / "config.py",
]

target = None

for f in candidate_files:
    if f.exists():
        txt = f.read_text()
        if "SimConfig" in txt or "cfg =" in txt:
            target = f
            break

if target is None:
    print("ERROR: Could not automatically find cfg file.")
    print("Run this and paste output:")
    print("grep -Rni \"SimConfig\\|cfg =\" ~/NeuropathicPain_Model/modeldb/267056 --include='*.py' | head -50")
    raise SystemExit

text = target.read_text()

backup = target.with_suffix(target.suffix + ".project1_backup")
if not backup.exists():
    shutil.copy2(target, backup)
    print(f"Backup created: {backup}")
else:
    print(f"Backup already exists: {backup}")

# Add import os if missing
if "import os" not in text:
    text = "import os\n" + text

# Add cfg.GABA_SCALE after cfg is created
if "cfg.GABA_SCALE" not in text:
    pattern = r"(cfg\s*=\s*specs\.SimConfig\(\)\s*)"
    match = re.search(pattern, text)

    if match:
        insert = (
            match.group(1)
            + "\n"
            + "# Project 1: terminal-controlled GABA/Glycine inhibitory strength\n"
            + "# Example: GABA_SCALE=0.5 python init_mechanical.py\n"
            + "cfg.GABA_SCALE = float(os.environ.get('GABA_SCALE', '1.0'))\n"
        )
        text = re.sub(pattern, insert, text, count=1)
    else:
        text += (
            "\n\n# Project 1: terminal-controlled GABA/Glycine inhibitory strength\n"
            "cfg.GABA_SCALE = float(os.environ.get('GABA_SCALE', '1.0'))\n"
        )

target.write_text(text)

print(f"Patched config file: {target}")
print()
print("Verify with:")
print(f"grep -nE \"GABA_SCALE|import os|SimConfig|cfg =\" {target}")
