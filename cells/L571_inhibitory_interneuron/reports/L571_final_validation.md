# L571-LCN final validation

## Scope and identity

**CONFIRMED:** rat; lumbar spinal cord; lamina I; local-circuit interneuron; VGAT-positive/GABAergic reconstructed example; multipolar; soma, dendrites, and axon reconstructed.

**POPULATION-LEVEL CONSTRAINT:** tonic firing is common/predominant among non-rhythmic rat lamina-I LCNs; population Rin is approximately 0.9 ± 0.1 GΩ.

**UNKNOWN:** exact individual L571 firing class, rheobase, AP waveform parameters, membrane tau, and behaviour at 35 C.

The 23 C candidate is constrained against experiments performed at 22–24 C. The 35 C candidate sets `h.celsius = 35` before initialization but deliberately retains Q10=1 for the selected active mechanisms because the executed Medlock source does not apply a correction and no L571-specific correction is available. It is therefore a conservative temperature-labelled translation with a major biological limitation, not direct 35 C validation.

## Results

| Feature | Target/source | 23 C result | 35 C result | Status | Confidence |
|---|---|---:|---:|---|---|
| RMP | Luz 2014 tonic rat LCN population: -69.1 ± 1.2 mV | -69.21301365241918 | -69.21301365241918 | PASS | B population-level |
| Rin | Szücs 2013 rat LCN population: 0.9 ± 0.1 GΩ | 950.5687501962441 | 950.5687501962441 | PASS | B population-level |
| Membrane tau | No exact L571 or LCN target in audited sources | 112.33189477613074 | 112.33189477613074 | NO EXPERIMENTAL TARGET | D unknown |
| Rheobase | No exact L571 target | 0.04 | 0.04 | NO EXPERIMENTAL TARGET | D unknown |
| AP threshold | No exact L571 waveform target | -44.330547670167945 | -44.330547670167945 | NO EXPERIMENTAL TARGET | D unknown |
| AP peak | No exact L571 waveform target | 19.85919609140956 | 19.85919609140956 | NO EXPERIMENTAL TARGET | D unknown |
| AP half-width | No exact L571 waveform target | 0.8249999999992497 | 0.8249999999992497 | NO EXPERIMENTAL TARGET | D unknown |
| AHP | No exact L571 waveform target | -77.30922525891495 | -77.30922525891495 | NO EXPERIMENTAL TARGET | D unknown |
| Tonic persistence | Luz 2014 rat LCN population; regular discharge during 500 ms pulse | 0.9588500000009245 | 0.9588500000009245 | PASS | B population-level |
| Spontaneous firing | Luz 2014: 40/85 LCNs rhythmic; exact L571 class unknown | False | False | PLAUSIBLE | B population-level; D individual unknown |
| AIS-to-soma timing | No experiment; reconstructed proximal axon is an AIS proxy | 0.07499999999993179 | 0.07499999999993179 | NO EXPERIMENTAL TARGET | C model-derived |

## Phenotype and numerical checks

- 23 C rheobase on the tested 5 pA grid: 0.04 nA; representative firing at 0.1 nA: 13 spikes, persistence 0.959.
- 35 C rheobase on the same grid: 0.04 nA; representative firing at 0.1 nA: 13 spikes, persistence 0.959.
- Pathology flags at 23 C: {'spontaneous_firing': False, 'spontaneous_rate_hz_during_500_ms_window': 0.0, 'gap_signature_at_strong_current': False, 'burst_signature_at_strong_current': False, 'depolarization_block_at_strong_current': False, 'abnormal_post_stimulus_plateau': False, 'post_stimulus_recovery_delta_mv': -4.3948456640547136}.
- Pathology flags at 35 C: {'spontaneous_firing': False, 'spontaneous_rate_hz_during_500_ms_window': 0.0, 'gap_signature_at_strong_current': False, 'burst_signature_at_strong_current': False, 'depolarization_block_at_strong_current': False, 'abnormal_post_stimulus_plateau': False, 'post_stimulus_recovery_delta_mv': -4.3948456640547136}.
- Full nseg, dt, initial-voltage, and ±5/±10% Na/K perturbation results are stored in each temperature's `validation_metrics.json`.

## Decision

**READY WITH BIOLOGICAL LIMITATIONS**

The 23 C model is population-constrained rather than L571-electrophysiology-specific. The 35 C model is suitable as a clearly labelled exploratory translation, but its active-channel temperature dependence remains unresolved and must not be presented as experimentally validated.
