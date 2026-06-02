# Direct GABA/Glycine Weight Editing Plan

## Project
Project 1: Computational Analysis of GABAergic Disinhibition in the Spinal Dorsal Horn During Neuropathic Pain

## Main Research Question
When GABAergic/glycinergic inhibition is reduced in the spinal dorsal horn, does NK1 projection-neuron firing increase enough to explain mechanical allodynia?

## Key Model File
The direct inhibitory synaptic connection rules are located in:

modeldb/267056/netParams_mechanical.py

## Important Model Evidence

The model defines inhibitory populations:

- PV: inhibitory interneurons
- DYN: inhibitory interneurons
- ISLET: inhibitory interneurons

The model defines the projection neuron population:

- NK1: projection neuron / pain-output neuron

The model defines inhibitory synaptic mechanisms:

- GABA: GABAa_DynSyn
- GLY: Glycine_DynSyn

## Direct Inhibitory Synapses Found

### PV inhibitory outputs
- PV_GABA->PKC
- PV_GLY->PKC
- PV_GABA->DOR
- PV_GLY->DOR

### ISLET inhibitory outputs
- ISLET_GABA->TrC
- ISLET_GABA->DYN

### DYN inhibitory outputs
- DYN_GABA->ISLET
- DYN_GABA->SOM
- DYN_GLY->SOM
- DYN_GABA->CR
- DYN_GLY->CR
- DYN_GABA->NK1
- DYN_GLY->NK1

## Most Important Pain-Relevant Inhibitory Gate

The strongest Project 1 target is:

DYN_GABA->NK1  
DYN_GLY->NK1

Reason:

NK1 neurons are projection neurons. They represent the final pain-output channel from the spinal dorsal horn to higher pain pathways.

Therefore, reducing DYN inhibition onto NK1 directly tests whether loss of inhibitory control increases pain-output firing.

## Biological Circuit Logic

Normal condition:

Mechanical input
        ↓
SDH excitatory neurons
        ↓
NK1 projection neurons
        ↓
Pain output controlled

DYN/PV/ISLET inhibitory neurons provide GABA/glycine brake.

Neuropathic-like disinhibition:

GABA/glycine brake reduced
        ↓
NK1 projection neuron escapes inhibition
        ↓
Projection firing increases
        ↓
Pain-like output increases

## Perturbation Plan

Test five inhibitory strength conditions:

- 100% inhibition = normal baseline
- 75% inhibition = mild disinhibition
- 50% inhibition = moderate disinhibition
- 25% inhibition = severe disinhibition
- 0% inhibition = complete inhibitory loss

## Technical Plan

Add one variable:

GABA_SCALE

Then multiply only inhibitory GABA and GLY connection weights by this value.

Target connection rules:

- Any connection with synMech = GABA
- Any connection with synMech = GLY

Do not change:

- AMPA
- NMDA
- NK1 receptor synapses
- sodium channels
- potassium channels
- stimulus strength
- morphology

## Main Output Metrics

For each GABA_SCALE condition measure:

1. NK1 projection-neuron firing rate
2. NK1 total spike count
3. Total SDH spikes
4. Excitatory population firing
5. Inhibitory population firing
6. E/I ratio
7. Percentage increase from baseline

## Expected Result

As GABA_SCALE decreases:

GABA/GLY inhibition decreases
        ↓
E/I ratio increases
        ↓
NK1 projection-neuron firing increases
        ↓
SDH pain-output amplification increases

## Report Statement

The ModelDB 267056 spinal dorsal horn network contains explicit GABA_A and glycine inhibitory synaptic mechanisms. Inhibitory populations PV, DYN, and ISLET provide GABA/glycine-mediated suppression of SDH neurons. The most pain-relevant inhibitory gate is DYN_GABA/DYN_GLY input onto NK1 projection neurons. Therefore, graded reduction of GABA/GLY synaptic weights provides a direct computational model of spinal disinhibition during neuropathic pain.
