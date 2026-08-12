# Excitatory Interneuron Model Readiness Report

**Date:** 12 August 2026  
**Workspace:** `C:\Users\Nikita\NeuropathicPain_Model\exc_interneuron`  
**Final status:** **NOT READY**  
**Failed gate:** Common delayed-excitatory model at 35 °C — strong-drive depolarization block.

## Executive summary

The isolated excitatory-interneuron workspace is runnable in WSL with Python 3.10.20 and NEURON 9.0.1. The official L292-E1-LCN morphology passes topology QA, all staged mechanisms compile and load, the reconstructed passive model passes at 23 °C, and both the eTrC and common delayed intrinsic models pass their 23 °C validation stages.

The mechanism-specific temperature audit was completed without applying a universal Q10. The eTrC model retained a validated transient phenotype at 35 °C. The delayed model did not: at moderate-to-strong current it entered sustained depolarization after a small number of spikes. Multiple bounded one-factor diagnostics did not restore stable firing across the tested range. Further multi-conductance fitting was stopped because direct L292-E1 or population-marker-specific 35 °C targets are unavailable.

Because the delayed intrinsic model underlies ePKCgamma, eVGLUT3, eDOR, eSST, and eCR, the six-population, robustness-acceptance, synapse-unit-test, and final-wrapper gates remain closed.

The protected L796 and inhibitory L571 directories were not modified.

## CONFIRMED

- L292-E1-LCN is NeuroMorpho reconstruction `NMO_34021`.
- Species/strain: Wistar rat.
- Region: lumbar spinal cord, lamina I.
- Morphological description: local-circuit multipolar interneuron.
- Structural domains: soma, dendrites, and axon.
- NeuroMorpho integrity label: `Dendrites & Axon Complete`.
- Official SWC SHA-256: `65b44b3f94a93a77696ea31626073dd637250c48b0bae7d77bcaf9dfe654ea67`.
- Morphology QA: one root and one connected morphology; zero cycles, missing parents, unreachable nodes, zero-length edges, or non-positive radii.
- The axon-origin candidate is documented, but it is not called a histologically confirmed AIS.
- All 11 staged MOD files compile and load in NEURON 9.0.1.

## MEDLOCK-DERIVED

- eTrC, ePKCgamma, eVGLUT3, eDOR, eSST, and eCR are computational population identities.
- eTrC uses the released `EXinitialRule` mechanism architecture.
- ePKCgamma, eVGLUT3, eDOR, eSST, and eCR use the common released delayed-spiking rule.
- The released delayed rules are parameter-identical after condition labels are removed; no marker-specific intrinsic conductances were invented.
- Mechanism parameters, population mappings, connectivity probabilities, synaptic weights, mechanisms, and delays were extracted from ModelDB 267056 at commit `6286892a9e7aa67ad80f2c5d86007350f900c644`.
- The released baseline uses a simplified soma–dendrite–hillock cell. Mapping it to a full SWC reconstruction is a biophysical upgrade requiring revalidation.

## EXPERIMENTALLY SUPPORTED

- The morphology source experiments were conducted at approximately 22–24 °C, supporting 23 °C as the first validation temperature.
- Project dorsal-horn target ranges used for passive validation were RMP −65 to −55 mV, Rin 100–400 MΩ, and tau 10–30 ms.
- The eTrC waveform was compared with project SDH target ranges for threshold, peak, and half-width.
- Rat dorsal-horn literature supports the existence of delayed excitatory firing phenotypes, but it does not provide exact individual L292-E1 or marker-specific conductance targets for this reconstruction.

## UNKNOWN

- The molecular identity of L292-E1-LCN is unknown.
- L292-E1-LCN is not proven to be eTrC, PKCgamma-positive, VGLUT3-positive, DOR-positive, SST-positive, or CR-positive.
- Exact individual L292-E1 electrophysiology is unavailable.
- Exact marker-specific active conductances and 35 °C waveform targets are unavailable.
- All reconstructed-cell 35 °C values are temperature-translated predictions unless direct experimental data are later supplied.
- The provisional proximal axonal region is a computational initiation-region mapping, not a confirmed biological AIS.

## Environment and mechanisms

| Item | Result |
|---|---|
| WSL distribution | Ubuntu-26.04 |
| Environment | `/home/nikita/NeuropathicPain_Model/pain_neuron_env` |
| Python | 3.10.20 |
| NEURON | 9.0.1 |
| `nrnivmodl` | `/home/nikita/NeuropathicPain_Model/pain_neuron_env/bin/nrnivmodl` |
| Compile/load | PASS for every staged mechanism |
| Solver constraint | Fixed step; HH2/KDRI are not CVODE-compatible |
| Threading constraint | HH2/KDRI VERBATIM and several GLOBAL assignments are not thread-safe |

The temperature audit found effective built-in scaling only in `HH2`, `borgka`, and `iKCa`. `B_Na` computes but does not apply its Q10 factor to tau; `KDRI` has commented-out Q10 code. Calcium-decay and synaptic time constants are temperature-invariant in the released source.

One compatibility correction was applied to `HH2.mod`: removable rate-equation singularities now use their analytic limit. No kinetics were changed away from the singular points. Mechanisms recompiled, and the delayed 23 °C model re-passed afterward.

## Morphology and passive 23 °C validation

| Metric | Result | Gate |
|---|---:|---|
| NEURON sections | 950 | recorded |
| Total `nseg` at strict `d_lambda=0.1` | 4,234 | recorded |
| Minimum segment diameter | 0.190 µm | PASS |
| Maximum electrotonic segment fraction | 0.099871 | PASS, ≤0.1 |
| RMP | −65.000 mV | PASS |
| Rin | 100.453 MΩ | PASS |
| Tau | 29.475 ms | PASS |
| Capacitance estimate | 293.421 pF | recorded |
| Recovery error | 0.00248 mV at −0.005 nA | PASS |

The leak-only fit changed `g_pas` from the Medlock starting value `4.2e-5` to `2.9e-5 S/cm²`; `e_pas`, `Ra`, and `cm` remained −65 mV, 150 Ω·cm, and 1 µF/cm². All nine `dt × d_lambda` passive convergence combinations passed. Worst changes were 0.01745% for Rin and 0.08482% for tau.

## eTrC intrinsic model

### 23 °C

| Metric | Result |
|---|---:|
| RMP | −66.492 mV |
| Active Rin | 65.208 MΩ |
| Active tau | 18.675 ms |
| Tested rheobase | 0.56 nA, bracket 0.55–0.56 nA |
| Phenotype | one-spike transient/initial |
| AP threshold | −39.60 to −42.86 mV |
| AP peak | +22.23 to +27.14 mV |
| AP half-width | 0.828–0.856 ms |
| First-spike latency | 17.30→3.98 ms with increasing current |
| Spontaneous firing / block | none / none |

The provisional proximal-axon 0-mV crossing preceded the soma by about 0.0054–0.0089 ms, smaller than the 0.025-ms time step; it is supportive but not conclusive initiation evidence.

### 35 °C

| Metric | Result |
|---|---:|
| RMP | −66.660 mV |
| Active Rin | 61.792 MΩ |
| Active tau | 18.200 ms |
| Tested rheobase | 0.88 nA, bracket 0.87–0.88 nA |
| Phenotype | one-spike transient retained |
| AP threshold at rheobase | −39.389 mV |
| AP peak at rheobase | +20.300 mV |
| AP half-width at rheobase | 0.874 ms |
| Spontaneous firing / block through 1.5 nA | none / none |

**eTrC 35 °C stage: PASS as a temperature-translated prediction.** Active numerical convergence and robustness remain pending because the common delayed 35 °C gate failed before the shared robustness stage.

## Common delayed intrinsic model

### 23 °C

| Metric | Result |
|---|---:|
| RMP | −65.910 mV |
| Active Rin | 82.112 MΩ |
| Active tau | 23.925 ms |
| Tested rheobase | 0.38 nA, bracket 0.37–0.38 nA |
| First-spike latency | 450.38 ms at 0.38 nA; 149.45 ms at 0.75 nA; 14.13 ms at 1.0 nA |
| Firing | 1, 15, and 23 spikes at those currents |
| Spontaneous firing / block | none / none |
| Maximum final recovery error | 0.00665 mV |

Mechanism diagnostics identified `borgka` A-type K as the dominant delay contributor; KDRI and HH2 K made smaller contributions, and reducing sodium prolonged near-rheobase delay.

**Delayed 23 °C stage: PASS with unknown marker-specific waveform targets disclosed.**

### 35 °C failure

The unchanged mechanism-supported translation retained stable RMP, Rin/tau, recovery, and a decreasing latency-current relation, but it did not retain stable firing over the required range:

- At 0.45 nA: 17 spikes with 133.4-ms first-spike latency; no block.
- At 0.55 nA: two spikes followed by a late mean voltage of −36.28 mV; block.
- At 0.75 nA: one low-overshoot spike followed by sustained depolarization; block.
- At 1.0 nA: one low-overshoot spike followed by sustained depolarization; block.

One-factor diagnostics tested sodium −10%, +10%, and +20%; KDRI +10%; HH2 K +10%; and A-type K +10%. Sodium increases improved moderate-current firing, but block persisted at 0.75 and 1.0 nA. No single tested adjustment restored the complete phenotype.

**Delayed 35 °C stage: FAIL — `NOT_READY_DEPOLARIZATION_BLOCK_AT_35C`.**

## Readiness gate

| Required gate | Status |
|---|---|
| Morphology QA | PASS |
| Mechanisms compile/load | PASS |
| Passive model at 23 °C | PASS |
| eTrC active model at 23 °C | PASS |
| Delayed model at 23 °C | PASS |
| Temperature audit | PASS |
| eTrC at 35 °C | PASS |
| Delayed model at 35 °C | **FAIL** |
| All six configurations run | NOT RUN — gated |
| Robustness tests | NOT RUN — gated |
| Active numerical convergence | NOT RUN — gated |
| Synapse unit tests | NOT RUN — gated |

## Gated outputs

The following were intentionally not presented as validated deliverables:

- final ePKCgamma/eVGLUT3/eDOR/eSST/eCR 35 °C configurations;
- six-population single-cell smoke tests;
- `scripts/validate_all_six.py` as a claimed final validator;
- final-model `parameters.json`, `run.py`, `validate.py`, and README wrappers;
- robustness acceptance, synapse unit tests, or any network/circuit simulation.

Creating these after a failed shared delayed-intrinsic gate would violate the prescribed build order.

## Required next scientific decision

Further progress requires one of two explicit directions:

1. Supply/approve experimental 35 °C delayed-cell targets and authorize a controlled multi-conductance refit; or
2. Treat depolarization block above the moderate-current operating window as an allowed phenotype and define a justified maximum validation current.

Without that decision, the correct overall status is **NOT READY**.

## Principal artifacts

- Mechanism logs: `reports/mechanism_compile_log.txt`, `reports/mechanism_compile_log_after_HH2_singularity_fix.txt`
- Passive: `parameters/common/passive_23C.json`, `results/23C/passive/final_strict_dlambda/`
- eTrC 23 °C: `parameters/eTrC/eTrC_final_23C.json`, `results/23C/eTrC/final/`
- Delayed 23 °C: `parameters/common/delayed_excitatory_final_23C.json`, `results/23C/delayed_excitatory/final_after_HH2_singularity_fix/`
- eTrC 35 °C: `parameters/eTrC/eTrC_final_35C.json`, `results/35C/eTrC/final/`
- Delayed 35 °C failed gate: `parameters/common/delayed_excitatory_final_35C.json`, `results/35C/delayed_excitatory/`
- Temperature audit: `docs/temperature_audit.md`
