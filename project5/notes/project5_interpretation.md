
# Project 5 Interpretation: AMPA/NMDA contribution after GABA loss

## Biological question

When GABA inhibition is reduced, does NMDA make spinal dorsal horn projection-neuron output more persistent?

## Conditions tested

1. normal_AMPA_NMDA
   - Normal GABA inhibition
   - AMPA and NMDA both active

2. reduced_GABA
   - GABA inhibition reduced
   - AMPA and NMDA both active

3. reduced_GABA_NMDA_block
   - GABA inhibition reduced
   - NMDA blocked
   - AMPA remains active

4. reduced_GABA_AMPA_block
   - GABA inhibition reduced
   - AMPA blocked
   - NMDA remains active

## Main logic

AMPA is fast.
It gives quick excitation during stimulus.

NMDA is slow.
It decays slowly and can support late/persistent firing after the stimulus.

GABA is inhibitory.
It acts like a brake on SDH projection-neuron firing.

## Expected biological interpretation

If reduced_GABA gives high late firing, but reduced_GABA_NMDA_block reduces late firing,
then NMDA contributes to persistent pain-like output.

If reduced_GABA_AMPA_block strongly reduces stimulus-window firing,
then AMPA contributes to fast stimulus-driven activation.

## Important caution

This script is a receptor-level computational sensitivity model.
It separates AMPA and NMDA mathematically to test mechanism.
It is not yet a full biophysical receptor knockout unless the original NEURON/NetPyNE model
has explicit AMPA and NMDA synapse objects that are directly blocked.

## Output files

Summary CSV:
- project5/results/project5_ampa_nmda_gaba_summary.csv

Time-series CSV:
- project5/results/project5_projection_timeseries.csv

Figures:
- project5/figures/project5_ampa_vs_nmda_currents.png
- project5/figures/project5_projection_rate_traces.png
- project5/figures/project5_total_spike_count_barplot.png
- project5/figures/project5_late_spikes_barplot.png
- project5/figures/project5_persistent_firing_index.png
