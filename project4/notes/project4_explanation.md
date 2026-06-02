# Project 4: Low-threshold Aβ input becoming pain output

## Main question

Can harmless touch-like Aβ input activate pain projection neurons when inhibition is reduced?

## Biological idea

Aβ fibers normally carry light touch or mechanical input.  
In a healthy spinal dorsal horn, GABAergic inhibitory interneurons act like a brake.  
This brake prevents touch input from strongly activating pain projection neurons.

When GABA inhibition is reduced, the brake becomes weak.  
Then the same Aβ touch-like input can produce stronger projection neuron output.  
This is a computational representation of mechanical allodynia.

## Conditions tested

1. Low Aβ input + normal GABA
2. Low Aβ input + reduced GABA
3. High Aβ input + normal GABA
4. High Aβ input + reduced GABA

## Main result

The most important comparison is:

Low Aβ + normal GABA  
versus  
Low Aβ + reduced GABA

If low Aβ input produces much higher projection output after GABA reduction, it supports an allodynia-like mechanism.

## Key result file

- `project4/results/project4_abeta_allodynia_condition_summary.csv`

## Key figures

- `project4/figures/project4_abeta_allodynia_barplot.png`
- `project4/figures/project4_abeta_gaba_matrix.png`
- `project4/figures/project4_mechanical_allodynia_mechanism_diagram.png`

## Important caution

This is a projection-output index model.  
It compares relative output across conditions.  
It should not be written as exact biological Hz unless later connected to direct NEURON spike-count simulations.

## Best report statement

This project tests a core mechanism of mechanical allodynia.  
The simulation shows that low-threshold Aβ input remains weak under normal inhibition, but produces strong projection-output-like activity when GABA inhibition is reduced.  
This supports the hypothesis that spinal dorsal horn disinhibition can allow normally harmless touch input to access pain-output pathways.
