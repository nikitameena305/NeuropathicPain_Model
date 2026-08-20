import sys
from pathlib import Path

MODEL_DIR = Path("modeldb/2018004").resolve()
sys.path.insert(0, str(MODEL_DIR))

from neuron import h

# Load compiled mechanisms if available
try:
    h.nrn_load_dll(str(MODEL_DIR / "x86_64" / "libnrnmech.so"))
    print("Loaded compiled mechanisms.")
except Exception as e:
    print("Mechanism load warning:", e)

import axon_class
import pseudounipolar_neuron_class

print("\naxon_class public names:")
print([x for x in dir(axon_class) if not x.startswith("_")])

print("\npseudounipolar_neuron_class public names:")
print([x for x in dir(pseudounipolar_neuron_class) if not x.startswith("_")])

print("\nCurrently existing NEURON sections:")
for sec in h.allsec():
    print(sec.name())
