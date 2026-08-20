# Common Delayed Excitatory Model Validation at 23 °C

**Stage status:** PASS WITH DISCLOSED LIMITATIONS  
**Applicable Medlock identities:** ePKCgamma, eVGLUT3, eDOR, eSST, and eCR  
**Overall six-population status:** NOT READY — temperature, robustness, synapse, and all-six gates remain.

## Identity and scope

The intrinsic model uses the released Medlock delayed-spiking rule on the L292-E1-LCN morphology scaffold. The five population labels remain computational connectivity identities. L292-E1-LCN is not experimentally proven to express PKCgamma, VGLUT3, DOR, SST, or CR.

The released `PKCRule`, `SOMRule`, `CRRule`, and `EXdelayedRule` are parameter-identical after conditions are removed. No population-specific intrinsic conductance was invented.

## Mechanism architecture

Derived from ModelDB 267056 at commit `6286892a9e7aa67ad80f2c5d86007350f900c644`:

- `borgka`: A-type potassium current central to onset delay.
- `KDRI`: inactivating delayed-rectifier potassium.
- `HH2`: sodium plus delayed-rectifier potassium.
- `B_Na`: additional sodium current in soma and provisional proximal axon.
- `iKCa` and `CaIntraCellDyn`: released calcium-dependent potassium/current-handling components.
- Validated reconstructed passive foundation.
- Distal reconstructed axon remains passive.

The same D-level region-wise area transformation used for eTrC preserves released total maximum conductance per simplified compartment when mapped to the larger reconstruction. Kinetics, reversals, mechanism set, and within-region ratios are unchanged.

## Protocol

- NEURON 9.0.1, 23 °C set before initialization.
- Fixed `dt = 0.025 ms`; `d_lambda = 0.1` at 100 Hz.
- 500-ms somatic depolarizing steps after 200-ms baseline.
- 1,200-ms total time, providing 500 ms of post-step recovery.
- Broad sweep followed by 50-pA and 10-pA rheobase refinement.
- Final currents: −0.02, 0, 0.37, 0.38, 0.39, 0.75, and 1.0 nA.

## Rest and active passive recheck

| Metric | Result | Interpretation |
|---|---:|---|
| RMP | −65.910 mV | Within configured −69 to −59 mV range |
| Active-model Rin at −0.02 nA | 82.112 MΩ | Below passive-only 100.453 MΩ; disclosed mapping limitation |
| Active-model tau at −0.02 nA | 23.925 ms | Within project 10–30 ms range |
| Spontaneous spikes | 0 | PASS |
| Maximum absolute final recovery error | 0.00665 mV | PASS against D-level 0.1-mV gate |

## Delayed firing and F-I behavior

| Current | Spikes | Rate | First-spike latency | Last-spike time | Mean ISI | ISI CV | Last/first ISI ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.37 nA | 0 | 0 Hz | — | — | — | — | — |
| 0.38 nA | 1 | 2 Hz | 450.375 ms | 450.375 ms | — | — | — |
| 0.39 nA | 2 | 4 Hz | 412.150 ms | 496.275 ms | 84.125 ms | — | — |
| 0.75 nA | 15 | 30 Hz | 149.450 ms | 482.150 ms | 23.764 ms | 0.135 | 0.648 |
| 1.00 nA | 23 | 46 Hz | 14.125 ms | 486.600 ms | 21.476 ms | 0.775 | 0.164 |

The tested rheobase is **0.38 nA**, bracketed by 0.37–0.38 nA at 0.01-nA resolution. First-spike latency decreases monotonically with current. The model has a clear delayed onset near rheobase without spontaneous firing, abnormal bursting, permanent plateau, depolarization block, or recovery failure.

The ISI ratio is reported numerically because classifying ratios below one as “adaptation” versus frequency acceleration is convention-dependent.

## Action-potential measurements

| Current | Threshold | Peak | Threshold-to-peak amplitude | Half-width | Max dV/dt | AHP depth |
|---:|---:|---:|---:|---:|---:|---:|
| 0.38 nA | −27.412 mV | +20.013 mV | 47.425 mV | 1.635 ms | 60.696 V/s | 28.208 mV |
| 0.39 nA | −27.475 mV | +20.414 mV | 47.889 mV | 1.638 ms | 63.078 V/s | 28.159 mV |
| 0.75 nA | −27.638 mV | +20.759 mV | 48.397 mV | 1.650 ms | 63.412 V/s | 26.805 mV |
| 1.00 nA | −28.541 mV | +22.448 mV | 50.989 mV | 1.674 ms | 73.423 V/s | 27.967 mV |

Exact marker-specific delayed-population threshold and half-width targets are unavailable. eTrC-specific waveform ranges were not imposed. These values are model predictions and are retained for future experimental comparison.

## Mechanism contribution diagnostics

One-factor diagnostics used `dt=0.05 ms`, `d_lambda=0.2`, and identical 0.4/0.75-nA steps. They are causal sensitivity tests, not final validation runs.

| Perturbation | Latency change at 0.4 nA | Latency change at 0.75 nA | Interpretation |
|---|---:|---:|---|
| Remove `borgka` | −349.35 ms | −135.50 ms | Dominant A-type contribution to onset delay; spike count increased strongly |
| Remove `KDRI` | −55.05 ms | −8.60 ms | Supporting delayed-rectifier contribution |
| Remove HH2 K component | −68.00 ms | −14.85 ms | KDR contribution; repetitive firing was disrupted at 0.75 nA |
| Sodium maxima −10% | +94.75 ms | +7.20 ms | Reduced inward drive prolongs near-rheobase delay and reduces spiking |

This supports retaining the released combination rather than tuning one current to force a desired latency.

## Provisional proximal-axon timing

The soma crosses 0 mV before the provisional proximal axon in the delayed model. Provisional-axon-minus-soma crossing delay is approximately +0.0246 to +0.0271 ms. Thus the recorded evidence does not support proximal-axon-first initiation for this delayed mapping.

## Gate decision

The common delayed intrinsic model passes the 23 °C stage because it has a refined rheobase, a robust decreasing latency–current relation, stable repetitive firing at moderate/strong drive, complete recovery, and no spontaneous firing or block. Unknown marker-specific waveform targets and reduced active Rin remain disclosed limitations.

## Principal artifacts

- Final runnable configuration: `parameters/common/delayed_excitatory_final_23C.json`
- Final structured results after HH2 singularity correction: `results/23C/delayed_excitatory/final_after_HH2_singularity_fix/`
- Mechanism diagnostics: `results/23C/delayed_excitatory/mechanism_contribution/`
- Broad and refined trials: `results/23C/delayed_excitatory/broad_initial_retry/` and `rheobase_refinement_*`
