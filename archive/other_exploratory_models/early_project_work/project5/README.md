# Project 5: AMPA/NMDA contribution after GABA loss

## Question

When inhibition is reduced, does NMDA make spinal dorsal horn projection-neuron output more persistent?

## Biological background

GABA normally inhibits spinal dorsal horn projection neurons.  
When GABA inhibition is reduced, excitatory synaptic inputs can produce exaggerated pain-like output.

AMPA receptors produce fast excitatory responses.  
NMDA receptors produce slower and more persistent excitatory responses.

Therefore, after GABA loss, NMDA may contribute strongly to late or persistent firing after the stimulus has ended.

## Conditions tested

1. Normal AMPA/NMDA  
2. Reduced GABA  
3. Reduced GABA + NMDA block  
4. Reduced GABA + AMPA block  

## Output metrics

- Total spike count
- Stimulus-window spike count
- Late-window spike count
- Stimulus projection-neuron firing rate
- Late projection-neuron firing rate
- Persistent firing index

## Main interpretation

If reduced GABA increases late firing, and NMDA block reduces that late firing, then NMDA contributes to persistent SDH output after disinhibition.

If AMPA block reduces early stimulus-driven firing, then AMPA contributes mainly to fast activation.

## Important note

This is a receptor-level computational sensitivity model.  
It separates AMPA and NMDA contributions mathematically to test mechanism.  
A future stronger version can directly modify explicit AMPA/NMDA synapses inside the original NEURON/NetPyNE model if those receptor mechanisms are exposed in the source code.

## Files

### Script

- `scripts/project5_ampa_nmda_gaba_loss.py`

### Results

- `results/project5_ampa_nmda_gaba_summary.csv`
- `results/project5_projection_timeseries.csv`

### Figures

- `figures/project5_ampa_vs_nmda_currents.png`
- `figures/project5_projection_rate_traces.png`
- `figures/project5_total_spike_count_barplot.png`
- `figures/project5_late_spikes_barplot.png`
- `figures/project5_persistent_firing_index.png`

### Logs

- `logs/project5_terminal_output.txt`

### Notes

- `notes/project5_interpretation.md`
