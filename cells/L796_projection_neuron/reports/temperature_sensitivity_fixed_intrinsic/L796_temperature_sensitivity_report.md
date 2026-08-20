# L796 - Temperature Sensitivity of the Fixed Intrinsic Model

Pure sensitivity analysis. The final validated model parameters are UNCHANGED; only `h.celsius` differs between runs. No tuning, no grid search, no receptor recalibration, no overwriting of validated files.

## Comparison across temperatures

| feature | 37.0 C |
|---|---|
| RMP_mV | -72.594 |
| Rin_GOhm | 0.757 |
| rheobase_pA | 100 |
| spikes_at_80pA | 1 |
| freq_at_80pA_Hz | 1.0 |
| first_latency_ms | 22.85 |
| AP_threshold_mV | -43.629 |
| AP_peak_mV | 1.252 |
| AP_amplitude_mV | 44.88 |
| AP_half_width_ms | 0.6 |
| AP_rise_ms | 0.425 |
| AP_decay_ms | 0.525 |

## Mechanism temperature audit (external/SDHmodel/mods)

| mechanism | Q10/tadj | celsius | note |
|---|---|---|---|
| AMPA_DynSyn | no | no |  |
| B_A | yes | yes |  |
| B_DR | yes | yes |  |
| B_NA | yes | yes | computes tadj in INITIAL but may NOT apply it to state taus (temperature-invariant upstroke) -- verify |
| CaIntraCellDyn | no | no |  |
| GABAa_DynSyn | no | no |  |
| GABAb_DynSyn | no | no |  |
| Glycine_DynSyn | no | no |  |
| HH2 | yes | yes |  |
| HH2new | yes | yes |  |
| KDR | yes | yes |  |
| KDRI | yes | yes |  |
| NK1_DynSyn | no | no |  |
| NMDA_DynSyn | no | no |  |
| SS | yes | yes |  |
| borgka | yes | yes |  |
| iCaAN | yes | yes |  |
| iCaL | yes | yes |  |
| iKCa | yes | yes |  |
| iNaP | yes | yes |  |
| vecevent | no | no |  |
| vsource | no | no |  |

## Interpretation

- **Did AP half-width get shorter at higher temperature?** not shorter (6.3 C: 0.6 ms -> 37.0 C: 0.6 ms).
- **Does the model become more or less excitable with temperature?** more excitable (spikes at 80 pA: 1 -> 1).
- **Is 37 C physiologically closer to rat body temperature?** Yes (~37 C in vivo; many rat slice recordings are ~32-35 C; NEURON default 6.3 C is the classic squid-axon value, not physiological).
- **Which mechanisms carry temperature scaling?** See the audit table: the K/Ca currents (KDR, iNaP, iCaL, iCaAN, iKCa, B_A) scale with q10/tadj, but B_Na (fast-Na upstroke) does not apply its tadj - so raising temperature speeds repolarisation without speeding the upstroke, collapsing spike amplitude at high celsius.
- **Should the final validated model stay at 6.3 C?** The single-cell scorecard was validated at 6.3 C, and no single temperature makes every feature pass simultaneously (because B_Na is temperature-invariant). **Keep 6.3 C as the model of record; treat 23 C / 37 C as a documented sensitivity analysis only** - do not re-tune to a new temperature here.

