# README

`readme.md` file for the model associated with the paper: 

> Farooqui J, Nanivadekar AC, Capogrosso M, Lempka SF, Fisher LE. The effects of neuron morphology and spatial distribution on the selectivity of dorsal root ganglion stimulation. *J Neural Eng*. 2024 Sep 4. doi: 10.1088/1741-2552/ad7760. PMID: 39231464.



## Model Information

These files include a class definition for a sensory DRG pseudounipolar neuron and a sensory DRG axon, each of which can be instantiated for any value of fiber diameter in the continuous range [6, 20] um. The models are written in Python with NEURON.


The axon models are based on the MRG motor axon model:

> McIntyre CC, Richardson AG, Grill WM. Modeling the Excitability of Mammalian Nerve Fibers:  Influence of Afterpotentials on the Recovery Cycle. *J Neurophysiol*. 2002;87(2):995-1006. doi:10.1152/jn.00353.2001
(model can be found on ModelDB at: https://modeldb.science/3810)

modified with sensory mechanisms from:

> Gaines JL, Finn KE, Slopsema JP, Heyboer LA, Polasek KH. A model of motor and sensory axon activation in the median nerve using surface electrical stimulation. *J Comput Neurosci*. 2018;45(1):29-43. doi:10.1007/s10827-018-0689-5
(model can be found on ModelDB at: https://modeldb.science/243841)


The pseudounipolar neuron models are based on:

> Amir R, Devor M. Electrical Excitability of the Soma of Sensory Neurons Is Required for Spike Invasion of the Soma, but Not for Through-Conduction. *Biophys J.* 2003;84(4):2181-2191. doi:10.1016/S0006-3495(03)75024-3
(model can be found on ModelDB at: https://modeldb.science/51022)

with adaptations based on: 

> Graham RD, Bruns TM, Duan B, Lempka SF. The Effect of Clinically Controllable Factors on Neural Activation During Dorsal Root Ganglion Stimulation. *Neuromodulation*. 2021 Jun;24(4):655-671. doi: 10.1111/ner.13211



## Specifications

Specifications for the virtual environment used to develop this model are contained in the file `venv_spec_file.txt`

Additionally, NEURON v. 7.7 must be downloaded and installed.



## Usage

1. To instantiate a pseudounipolar neuron or axon with a given position (for both pseudounipolar neurons and axons) and orientation in space (pseudounipolar neurons only), import the class, instantiate an object, and call the `setXYZpos` function with the desired coordinates and angle. Examples below: 


---

# example axon instantiation

```python
from axon_class import axon

ax = axon(axonnodes=100, fiberD=7.3, pos=(0,0,0))
ax.setXYZpos(pos=(0,0,0))
```
---

---

# example psuedounipolar neuron instantiation
```python
from pseudounipolar_neuron_class import pseudounipolar_neuron

puni = pseudounipolar_neuron(
    centralFiberD=5.7, 
    peripheralFiberD=7.3, 
    neckFiberD=7.3, 
    numNodes_p = 100, 
    numNodes_c = 100, 
    somaSize = 80, 
    femElec='')
puni.setXYZpos(femdict=None, tjnPos=(0, 0, 0), neckAngle=90)
```

---


Standard relationships used to determine sizes of different psuedounipolar neuron parts based on fiber diameter:

```python
centralFiberD = (0.87 * peripheralFiberD) - 0.67
neckFiberD = peripheralFiberD
somaSize = (2.78088956*peripheralFiberD + 40.55727893)
```

(derived based on: 
Lee KH, Chung K, Chung JM, Coggeshall RE. Correlation of cell body size, axon size, and signal conduction velocity for individually labelled dorsal root ganglion cells in the cat. *J Comp Neurol.* 1986;243(3):335-346. doi:10.1002/cne.902430305 )


2. To inspect a specific section, use the function `getSectionFromDF` (parameters explained in code comments). 