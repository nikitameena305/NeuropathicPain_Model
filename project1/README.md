# Project 1: GABAergic Disinhibition in the Spinal Dorsal Horn

## Title
Computational Analysis of GABAergic Disinhibition in the Spinal Dorsal Horn During Neuropathic Pain

## Main Question
When GABAergic inhibition is reduced in the spinal dorsal horn, does projection-neuron firing increase enough to explain mechanical allodynia?

## Biological Hypothesis
Reducing inhibitory GABA/glycine synaptic strength in the spinal dorsal horn will increase projection-neuron output, especially NK1/pNK1 firing. This represents a computational signature of central sensitization and mechanical allodynia.

## Independent Variable
GABA inhibition strength:

- 100% = normal inhibition
- 75% = mild disinhibition
- 50% = moderate disinhibition
- 25% = severe disinhibition
- 0% = complete inhibitory loss

## Dependent Variables
Measured outputs:

1. Projection neuron firing rate
2. Total SDH spikes
3. Excitatory population firing rate
4. Inhibitory population firing rate
5. E/I ratio
6. Percentage increase from baseline

## Core Circuit Logic

Mechanical input
        ↓
Aβ / Aδ / C-fiber afferents
        ↓
SDH excitatory interneurons
        ↓
Projection neurons
        ↓
Pain output

GABAergic interneurons suppress this pathway.

When inhibition is reduced, projection-neuron output increases.

## Main Output Figures
- Baseline raster plot
- GABA strength vs projection neuron firing
- Population firing heatmap
- E/I ratio plot
- Summary table
