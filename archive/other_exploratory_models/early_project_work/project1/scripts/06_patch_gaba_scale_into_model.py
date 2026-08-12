from pathlib import Path
import re
import shutil

ROOT = Path.home() / "NeuropathicPain_Model"
MODEL = ROOT / "modeldb" / "267056"
target = MODEL / "netParams_mechanical.py"

if not target.exists():
    raise FileNotFoundError(f"Cannot find {target}")

text = target.read_text()

backup = target.with_suffix(".py.project1_backup")
if not backup.exists():
    shutil.copy2(target, backup)
    print(f"Backup created: {backup}")
else:
    print(f"Backup already exists: {backup}")

# Add GABA_SCALE after imports / cfg area if not present
if "GABA_SCALE" not in text:
    insert_text = """
# Project 1 GABA/Glycine disinhibition multiplier
# 1.0 = normal inhibition, 0.75 = mild loss, 0.5 = moderate loss,
# 0.25 = severe loss, 0.0 = complete inhibitory synaptic loss.
GABA_SCALE = getattr(cfg, 'GABA_SCALE', 1.0)

"""
    # Insert before Synaptic Mechanisms section if possible
    marker = "#   Synaptic Mechanisms"
    if marker in text:
        text = text.replace(marker, insert_text + marker)
    else:
        text = insert_text + text

# Multiply only weights inside connection blocks whose synMech is GABA or GLY.
# We target cfg.* weights in inhibitory connection rules.
inhibitory_conn_names = [
    "PV_GABA->PKC",
    "PV_GLY->PKC",
    "PV_GABA->DOR",
    "PV_GLY->DOR",
    "ISLET_GABA->TrC",
    "DYN_GABA->ISLET",
    "ISLET_GABA->DYN",
    "DYN_GABA->SOM",
    "DYN_GLY->SOM",
    "DYN_GABA->CR",
    "DYN_GLY->CR",
    "DYN_GABA->NK1",
    "DYN_GLY->NK1",
]

for conn in inhibitory_conn_names:
    pattern = (
        r"(netParams\.connParams\['" + re.escape(conn) + r"'\]\s*=\s*\{.*?"
        r"'weight'\s*:\s*)(cfg\.[A-Za-z0-9_]+)(\s*,)"
    )

    def repl(m):
        existing = m.group(2)
        if "GABA_SCALE" in existing:
            return m.group(0)
        return m.group(1) + existing + " * GABA_SCALE" + m.group(3)

    text_new = re.sub(pattern, repl, text, flags=re.DOTALL)
    text = text_new

target.write_text(text)

print("Patch complete.")
print("Inserted GABA_SCALE and multiplied inhibitory GABA/GLY connection weights.")
print()
print("Check with:")
print("grep -nE 'GABA_SCALE|PV_GABA|PV_GLY|ISLET_GABA|DYN_GABA|DYN_GLY' ~/NeuropathicPain_Model/modeldb/267056/netParams_mechanical.py")
