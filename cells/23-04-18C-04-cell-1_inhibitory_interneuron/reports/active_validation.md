# Active validation report

## Outcome

**Partial population match; not network-ready.** The selected 23 C minimal model reproduces a tonic response at 120 pA and the population AP threshold, but it fails rheobase, AP amplitude, half-width, and AHP gates. No exact-cell electrophysiology exists for NMO_170087.

| Metric | Population target | Model | Criterion | Status |
|---|---:|---:|---|---|
| Rheobase | 77 +/- 7 pA | 50 pA | 63-91 pA (mean +/- 2 SEM) | FAIL |
| AP threshold | -34.9 +/- 1.3 mV | -34.839 mV | -37.5 to -32.3 mV | PASS |
| AP amplitude | 44.8 +/- 1.6 mV | 33.514 mV | 41.6-48.0 mV | FAIL |
| AP half-width | 1.4 +/- 0.1 ms | 1.075 ms | 1.2-1.6 ms | FAIL |
| AHP relative to threshold | -17.6 +/- 1.6 mV | -36.877 mV | -20.8 to -14.4 mV | FAIL |
| Tonic persistence | tonic in 55-64.2% of PV cohorts | 30 spikes; last at 96.84% of 800-ms pulse at 120 pA | >=3 spikes; last after 80% | PASS |

The F-I response is non-monotonic at strong drive: 38 spikes at 200 pA, 2 at 300 pA, and 1 at 400 pA, consistent with a model depolarization-block transition. No quantitative population target validates that transition.

Timestep convergence is good across 0.05, 0.025, and 0.0125 ms (30 spikes in each case). Spatial convergence is incomplete: d_lambda 0.2 abolishes firing, while d_lambda 0.05 produces 33 rather than 30 spikes. The response is also sensitive to a 10% sodium reduction and to the length of the model-defined proximal-axon enrichment. These failures are preserved in `results/robustness/robustness_summary.csv`.
