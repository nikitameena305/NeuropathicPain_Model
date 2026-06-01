import sys
import inspect
from pathlib import Path

MODEL_DIR = Path("modeldb/2018004").resolve()
sys.path.insert(0, str(MODEL_DIR))

from neuron import h

try:
    h.nrn_load_dll(str(MODEL_DIR / "x86_64" / "libnrnmech.so"))
    print("Loaded compiled mechanisms.")
except Exception as e:
    print("Mechanism load warning:", e)

import axon_class
import pseudounipolar_neuron_class

print("\naxon constructor:")
print(inspect.signature(axon_class.axon))

print("\npseudounipolar_neuron constructor:")
print(inspect.signature(pseudounipolar_neuron_class.pseudounipolar_neuron))

print("\naxon source first 80 lines:")
print("\n".join(inspect.getsource(axon_class.axon).splitlines()[:80]))

print("\npseudounipolar source first 100 lines:")
print("\n".join(inspect.getsource(pseudounipolar_neuron_class.pseudounipolar_neuron).splitlines()[:100]))
