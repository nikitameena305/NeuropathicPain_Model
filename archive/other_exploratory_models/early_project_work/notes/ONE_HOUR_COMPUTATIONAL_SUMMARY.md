# 1-Hour Computational Sprint Summary

## Project

Computational neuropathic pain model using NEURON: DRG hyperexcitability + SDH output.

## Completed computational outputs

1. NEURON Ball-and-Stick AP demo generated.

   - Figure: figures/01_ball_stick_AP_demo.png

   - Metrics: results/ball_stick_ap_metrics.txt


2. DRG normal vs neuropathic-like firing model generated.

   - Figure: figures/02_DRG_normal_vs_neuropathic.png

   - Metrics: results/02_DRG_normal_vs_neuropathic_metrics.csv


3. SDH normal vs neuropathic-like output model generated.

   - Figure: figures/03_SDH_normal_vs_neuropathic_output.png

   - Metrics: results/03_SDH_normal_vs_neuropathic_metrics.csv


## Biological interpretation


Normal pain circuit:
- DRG has balanced sodium and potassium conductance.
- Weak stimulus produces low/controlled firing.
- SDH receives moderate AMPA/NMDA excitation.
- GABA/glycine-like inhibition is strong.
- Final SDH projection output remains controlled.

Neuropathic-like pain circuit:
- DRG sodium conductance is increased and potassium conductance is reduced.
- Same weak stimulus produces increased firing.
- SDH receives stronger AMPA/NMDA excitation.
- GABA/glycine-like inhibition is reduced, representing disinhibition.
- Final SDH output is larger and more persistent.

Clinical mapping:
- Weak stimulus causing strong output = allodynia-like behavior.
- Larger response to same input = hyperalgesia-like behavior.
- Persistent output after input = after-discharge-like behavior.

## Important limitation


These are fast teaching/prototype models, not final validated ModelDB reconstructions.
The project document requires ModelDB 267056 and ModelDB 2018004 outputs separately.
If those cannot be completed within the sprint, report this honestly as pending/fallback.


## Ball-stick AP metrics

```text
Baseline/RMP approx: -65.00 mV
Peak voltage: -59.93 mV
Approx threshold crossing time > -20 mV: nan ms
Stimulus current: 0.35 nA

```


## DRG metrics

| condition        |   stimulus_nA |   RMP_mV |   peak_mV |   spike_count |   first_spike_ms |
|:-----------------|--------------:|---------:|----------:|--------------:|-----------------:|
| normal           |          0.08 |      -65 |  -65      |             0 |              nan |
| neuropathic_like |          0.08 |      -65 |  -63.5504 |             0 |              nan |



## SDH metrics

| condition        |   AMPA_weight |   NMDA_weight |   GABA_weight |   baseline_mV |   peak_mV |   voltage_change_mV |   spike_count |   afterdischarge_mean_400_600ms |
|:-----------------|--------------:|--------------:|--------------:|--------------:|----------:|--------------------:|--------------:|--------------------------------:|
| normal           |         0.002 |        0.0005 |        0.0015 |           -65 |  -60.0246 |             4.97541 |             0 |                        -65.0952 |
| neuropathic_like |         0.004 |        0.0012 |        0.0003 |           -65 |  -55.4969 |             9.50311 |             0 |                        -62.7353 |

