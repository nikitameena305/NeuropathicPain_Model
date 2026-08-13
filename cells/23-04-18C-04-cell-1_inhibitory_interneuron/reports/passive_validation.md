# Passive validation report

## Outcome

**Primary gate: PASS. Comparison gate: FAIL.**

The native imported reconstruction was fitted without active conductances. A deterministic grid varied Ra (80-150 ohm cm) and cm (0.5-1.5 uF/cm2); leak conductance was tuned within each combination. The selected fit uses Ra 150 ohm cm, cm 0.5 uF/cm2, g_pas 6.076828312e-5 S/cm2, and e_pas -60 mV.

| Metric | Target | Model | Error | Criterion | Status | Evidence |
|---|---:|---:|---:|---|---|---|
| Input resistance | 225 +/- 22 MOhm | 225.000 MOhm | 0.000 MOhm | 203-247 MOhm | PASS | SP/PL |
| Equivalent capacitance, tau/Rin | 10.9 +/- 0.6 pF | 35.230 pF | 24.330 pF (223.2%) | 10.3-11.5 pF with restrained cm | FAIL | SP/PL comparison |
| Geometric capacitance | not directly equivalent | 37.981 pF | n/a | reported, not fitted | NOT A GATE | P |
| Mono-exponential tau | not reported | 7.927 ms | n/a | report prediction | NO TARGET | P |
| Passive equilibrium | RMP not reported | -60.000 mV | n/a | holding-condition model | NO TARGET | A/F |

The failed capacitance comparison is retained because forcing 10.9 pF would require a specific capacitance below the pre-registered restrained range. The published value is an electrode-derived whole-cell estimate, while the model includes 7596.19 um2 of imported membrane. Active development proceeded cautiously because the primary input-resistance gate passed and the capacitance observables are not strictly equivalent.
