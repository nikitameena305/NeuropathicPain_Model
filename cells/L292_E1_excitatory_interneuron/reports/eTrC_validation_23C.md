# eTrC Validation on L292-E1-LCN at 23 °C

**Stage status:** PASS WITH DISCLOSED LIMITATIONS  
**Overall six-population status:** NOT READY — delayed, temperature, robustness, synapse, and all-six gates remain.

## Identity

The morphology is L292-E1-LCN (`NMO_34021`), a rat Wistar lumbar lamina-I local-circuit interneuron reconstruction. The eTrC label is the Medlock computational population identity mapped onto this scaffold. It is not an experimentally confirmed molecular identity of L292-E1-LCN.

## Model construction

The active architecture is derived from ModelDB 267056 `EXinitialRule`, commit `6286892a9e7aa67ad80f2c5d86007350f900c644`:

- Sodium: `B_Na` in soma and putative/provisional proximal axonal initiation region.
- Potassium: `KDRI`, `borgka`, and `iKCa` as specified by the released rule.
- Calcium handling: `CaIntraCellDyn` in soma and dendrites.
- Leak: validated reconstructed-cell `pas` parameters from `passive_23C.json`.
- Distal reconstructed axon: passive pending propagation-specific evidence.
- Provisional proximal region: first 9 µm of axonal path, with at most 3-µm segments. This is not a biologically confirmed AIS.

## Geometry transformation audit

Directly applying Medlock densities to the full reconstruction changes total maximum conductance because mapped areas differ substantially from the simplified cell:

| Region | Medlock area | Reconstructed mapped area | Reconstructed/Medlock |
|---|---:|---:|---:|
| Soma | 1,256.64 µm² | 2,850.46 µm² | 2.268× |
| Dendrite | 3,769.91 µm² | 27,841.37 µm² | 7.385× |
| Provisional proximal axon | 42.41 µm² | 77.35 µm² | 1.824× |

The selected D-level transformation multiplies maximum conductance densities within each region by `Medlock area / reconstructed area`. It preserves the released total maximum conductance, mechanism set, kinetics, reversals, and within-region channel ratios. This is a computational morphology transform, not an experimental parameter.

The exact-density alternative was retained as a diagnostic. After correcting proximal-axon discretization it had a tested rheobase of 1.0 nA and active Rin below the selected candidate. It was not accepted.

## Protocol

- NEURON 9.0.1, fixed step.
- `h.celsius = 23` before initialization.
- `dt = 0.025 ms`, `d_lambda = 0.1` at 100 Hz.
- 500-ms somatic current steps after a 200-ms baseline.
- Broad range followed by 50-pA and 10-pA rheobase refinement.
- Final currents: −0.02, 0, 0.50, 0.55, 0.56, 0.60, 0.75, 1.0, and 1.5 nA.

## Rest and passive recheck with active mechanisms

| Metric | Result | Interpretation |
|---|---:|---|
| RMP | −66.492 mV | Within configured −69 to −59 mV range |
| Active-model Rin at −0.02 nA | 65.208 MΩ | Below passive-only 100.453 MΩ; disclosed limitation |
| Active-model tau at −0.02 nA | 18.675 ms | Within project 10–30 ms range |
| Spontaneous spikes | 0 | PASS |
| Recovery error | ≤0.0411 mV | PASS against D-level 0.1-mV numerical gate |

No active conductance was arbitrarily retuned to conceal the Rin reduction.

## Firing phenotype and rheobase

- 0.55 nA: no spike.
- 0.56 nA: one spike.
- Tested rheobase: **0.56 nA**, bracketed at 0.55–0.56 nA with 0.01-nA resolution.
- All tested suprathreshold currents produced one spike during the 500-ms step (reported F-I rate 2 Hz).
- First-spike latency decreased from 17.30 ms at rheobase to 3.975 ms at 1.5 nA.
- No bursting, spontaneous firing, permanent plateau, or depolarization block was detected.
- Mean ISI, ISI CV, and adaptation ratio are not defined for a one-spike transient response.

The observed phenotype is therefore transient/initial and matches Medlock's qualitative `EXinitialRule` definition of 1–2 spikes within 100 ms. It was measured rather than imposed by the population name.

## Action-potential metrics

| Current | Threshold | Peak | Threshold-to-peak amplitude | Half-width | Max dV/dt | AHP depth | First-spike latency |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.56 nA | −39.603 mV | +22.232 mV | 61.835 mV | 0.828 ms | 163.617 V/s | 27.351 mV | 17.300 ms |
| 0.75 nA | −41.126 mV | +25.345 mV | 66.471 mV | 0.834 ms | 186.964 V/s | 25.154 mV | 9.225 ms |
| 1.50 nA | −42.862 mV | +27.136 mV | 69.998 mV | 0.856 ms | 200.771 V/s | 21.364 mV | 3.975 ms |

Threshold, peak, and half-width pass the project’s sourced SDH eTrC ranges. The reconstructed 23 °C AP rises about 88.7–93.6 mV from RMP to peak, below the Medlock paper’s reported 107-mV height-from-start comparison. This disagreement is retained rather than tuned away because the geometries and temperatures differ and individual L292-E1 physiology is unavailable.

## Provisional proximal-axon timing

Interpolated 0-mV crossing produced:

| Current | Provisional axon minus soma time | Earliest recorded site |
|---:|---:|---|
| 0.56 nA | −0.00893 ms | provisional proximal axon |
| 0.60 nA | −0.00810 ms | provisional proximal axon |
| 0.75 nA | −0.00721 ms | provisional proximal axon |
| 1.00 nA | −0.00640 ms | provisional proximal axon |
| 1.50 nA | −0.00543 ms | provisional proximal axon |

Negative values mean the provisional axonal site crossed first. These differences are smaller than one 0.025-ms time step, so they support but do not conclusively prove axonal initiation. The claim remains conditional on active-model dt/nseg convergence.

## Gate decision

The eTrC intrinsic model passes the 23 °C stage because it:

- uses the validated passive foundation and source-derived mechanism architecture;
- has RMP and AP waveform metrics within configured ranges;
- exhibits the released qualitative transient phenotype;
- has a refined rheobase bracket;
- has no spontaneous firing, block, abnormal bursting, or recovery failure; and
- records all requested soma/dendrite/provisional-axon traces and metrics.

Limitations: active Rin is reduced relative to the passive-only model, the 107-mV Medlock height comparison is not reproduced, provisional initiation timing is sub-time-step, and no exact L292-E1 electrophysiology or marker identity is known.

## Principal artifacts

- Final runnable configuration: `parameters/eTrC/eTrC_final_23C.json`
- Final structured results: `results/23C/eTrC/final/`
- Geometry audit: `results/23C/eTrC/geometry_mapping_audit_refined_axon.json`
- Source-density diagnostic: `results/23C/eTrC/exact_density_refined_axon/`
- Accepted candidate trials: `results/23C/eTrC/area_preserved_*`
