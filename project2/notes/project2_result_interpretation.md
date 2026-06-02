# Project 2 Result Interpretation

## Main finding
The combined condition, hyperexcitable DRG + reduced GABA, produced the strongest predicted SDH projection output.

## Why this matters
This supports the idea that neuropathic pain can be amplified by two mechanisms acting together:

1. Peripheral sensitization:
   DRG neurons become hyperexcitable and send stronger input to the spinal dorsal horn.

2. Central disinhibition:
   GABAergic inhibition in the SDH becomes weaker, so projection neurons are less controlled.

## Condition-wise interpretation

### C1: Normal DRG + Normal GABA
This is the baseline control condition.
Input is normal and inhibitory brake is normal.

### C2: Hyperexcitable DRG + Normal GABA
Peripheral input is stronger, but spinal inhibition is still present.
Output increases compared with baseline.

### C3: Normal DRG + Reduced GABA
Input is normal, but inhibitory control is weaker.
Output increases because the spinal brake is reduced.

### C4: Hyperexcitable DRG + Reduced GABA
Both mechanisms act together.
Input is stronger and inhibition is weaker.
This produces the strongest output.

## Simple analogy
DRG hyperexcitability is like pressing the accelerator.
GABA inhibition is like the brake.

Neuropathic pain becomes strongest when:
accelerator is pressed more and brake is weak.

## Link to Tigerholm et al. 2014
Tigerholm et al. showed that C-nociceptor axons can show activity-dependent changes in excitability and conduction.
In this project, DRG hyperexcitability represents increased peripheral nociceptive drive entering the SDH.

## Limitation
This project uses baseline ModelDB 267056 spike output and applies biological scaling factors.
The next stronger version should directly modify the NetPyNE/NEURON model parameters and rerun all four conditions.
