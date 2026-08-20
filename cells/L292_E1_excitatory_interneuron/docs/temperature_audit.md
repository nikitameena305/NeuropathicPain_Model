# Temperature Audit for Excitatory Interneuron Mechanisms

**Audit date:** 12 August 2026  
**Runtime:** NEURON 9.0.1, fixed step  
**35 °C policy:** Apply only behavior implemented by each mechanism. No universal Q10 is added.

## Summary

The staged mechanism set does not have one shared reference temperature or one shared Q10. Only `HH2`, `borgka`, and `iKCa` implement effective temperature dependence. `B_Na` computes a Q10-like factor but does not use it in tau; `KDRI` has disabled Q10 code. The calcium-decay and synaptic mechanisms use explicit time constants without `celsius` scaling.

Therefore, a run with `h.celsius = 35` is a **mechanism-supported partial temperature translation**, not a complete biophysical correction of every current.

## Intrinsic mechanisms

| Mechanism | Reference / formula | Uses `celsius` effectively? | Q10 / effect | TABLE behavior | Reversal / calcium handling | Decision at 35 °C |
|---|---|---|---|---|---|---|
| `B_Na` | Computes `tadj = 3^((celsius-23)/10)` | **No effective kinetic effect** | Q10=3 is computed, but `tadj` is absent from tau; `tau_factor` remains the only tau divisor | `TABLE inf,tau DEPEND tadj`; runtime probe confirms celsius rebuilds an identical table. RANGE `alpha_shift`, `beta_shift`, and `tau_factor` changes do update TABLE output | `USEION na READ ena`; NEURON ion reversal overrides MOD default | Keep released kinetics unchanged; do not invent missing Q10 application |
| `HH2` | `tadj = 3^((celsius-36)/10)` | Yes | Q10=3 divides `tau_m`, `tau_h`, and `tau_n`; steady-state gates unchanged | No TABLE; explicit fixed-step exponentials depend on `dt/tau` | Reads `ena`, `ek`; writes `ina`, `ik` | Use implemented scaling. Fixed-step only; no CVODE |
| `KDRI` | Q10 line commented out; local `tau_factor=1` | No | No effective Q10; alpha/beta unchanged | `TABLE inf,fac DEPEND dt,celsius`; celsius triggers rebuild but values are unchanged. Runtime one-step gates were identical at 23 and 35 °C | Reads `ek`; writes `ik`; NEURON overrides MOD `ek` default | Keep released temperature-invariant kinetics; do not restore commented Q10 without evidence |
| `borgka` | Thermodynamic voltage-rate exponent plus `q10=3^((celsius-30)/10)` | Yes | Q10=3 scales `taun`/`taul`; absolute temperature also appears in voltage-dependent exponentials, so both steady states and tau may change | No TABLE | Reads `ek`, writes `ik` | Use implemented scaling exactly |
| `iKCa` | `tadj = 3^((celsius-22)/10)` | Yes | Q10=3 divides `tau_m`, limited by `taumin=0.1 ms`; calcium-dependent steady state unchanged | No TABLE | Reads `cai` and `ek`; writes `ik` | Use implemented scaling exactly |
| `CaIntraCellDyn` | No temperature term | No | `cai_tau` remains explicit 1/2 ms by region | No TABLE | Reads `ica,cai`, writes `cai`; inward calcium drives a shell plus first-order decay | Keep source time constants unchanged; do not invent pump/buffer Q10 |

## Synaptic mechanisms

| Mechanism | Temperature term / Q10 | TABLE | Reversal and ionic handling | 35 °C decision |
|---|---|---|---|---|
| `AMPA_DynSyn` | None | None | Nonspecific current, `e=0 mV` | Retain explicit rise/decay/STP constants |
| `NMDA_DynSyn` | None | None | `e=0`; magnesium block uses `mgo`; splits 10% to `ica` and 90% nonspecific current | Retain explicit kinetics and Mg/Ca handling |
| `GABAa_DynSyn` | None | None | Nonspecific current, source default `e=-80 mV` | Retain explicit kinetics/reversal until synapse unit tests |
| `Glycine_DynSyn` | None | None | Nonspecific current, source default `e=-70 mV` | Retain explicit kinetics/reversal until synapse unit tests |
| `NK1_DynSyn` | None | None | `e=0`; empirical nonspecific current plus calcium-current write controlled by `ca_ratio` | Retain explicit 10/5000-ms kinetics; treat as empirical Medlock component |

## TABLE update verification

The runtime probe at −40 mV and `dt=0.025 ms` showed:

- `B_Na` 23→35 °C: `tadj` changed 1.0→3.73719, but tau stayed 0.35684/10.02409 ms. Thus temperature is listed as a TABLE dependency but has no effective output because the source equation does not use it.
- Changing `B_Na` RANGE values `alpha_shift`, `beta_shift`, and `tau_factor` changed table output and matched `usetable=0` direct evaluation. NEURON 9 correctly invalidated/rebuilt the table for these RANGE changes.
- `KDRI` 23→35 °C: one-step `n/h` values were identical. Its TABLE includes `celsius`, but source alpha/beta do not.
- `HH2` tau at −40 mV changed by the expected factor 3.73719 between 23 and 35 °C.

## Numerical compatibility correction

The released `HH2` alpha-rate expressions had removable `0/0` singularities at exact voltages. The runtime probe produced NaN for `n_inf/tau_n` at `v=-40 mV` with `vtraub=-55 mV`.

`HH2.mod` was changed only to evaluate `x/(exp(x/y)-1)` through the standard analytic-limit `vtrap` expression near `x=0`. Away from the singularity, the original equation is unchanged. After recompilation:

- `n_inf=0.266113` at the probe voltage.
- `tau_n=6.93751 ms` at 23 °C.
- `tau_n=1.85634 ms` at 35 °C.
- The complete delayed 23 °C model re-passed with rheobase 0.38 nA.

Compiler log: `reports/mechanism_compile_log_after_HH2_singularity_fix.txt`.

## Solver, thread, and scaling constraints

- `HH2` and `KDRI` contain `VERBATIM` return blocks; NEURON reports them as non-thread-safe and incompatible with CVODE. Validation must remain fixed-step.
- `KDRI` and `borgka` expose GLOBAL variables that are not thread-safe under the present implementation.
- These limitations do not block deterministic single-cell fixed-step tests, but they block an HPC/thread-safety readiness claim.
- Ionic reversals are assigned from configuration after mechanism insertion. Compiler warnings that MOD parameter defaults are ignored are expected under NEURON ion handling.

## 35 °C translation gate

For both eTrC and delayed models:

1. Set `h.celsius=35` before initialization.
2. Keep morphology, passive parameters, conductance architecture, and region-wise mapping fixed.
3. Allow only the effective built-in scaling described above.
4. Re-measure rest/passive behavior, rheobase, F-I, AP waveform, latency/adaptation, recovery, block, and provisional-axon timing.
5. Record values as temperature-translated predictions. Do not claim direct experimental validation at 35 °C.

## Translation outcome

### eTrC

The final eTrC 35 °C configuration passed its stage gates without conductance retuning:

- RMP remained within range.
- The transient one-spike phenotype was retained.
- Tested rheobase shifted from 0.56 nA at 23 °C to 0.88 nA at 35 °C.
- AP threshold, peak, and half-width remained within configured project ranges.
- No spontaneous firing, recovery failure, or depolarization block occurred through 1.5 nA.

Artifacts: `parameters/eTrC/eTrC_final_35C.json` and `results/35C/eTrC/final/`.

### Delayed excitatory model

The unchanged 35 °C translation did **not** pass:

- RMP, active Rin/tau, and recovery remained stable.
- A decreasing latency-current relationship remained detectable.
- At 0.75 and 1.0 nA, the model generated one low-overshoot AP and then remained above −40 mV without late spikes, meeting the configured depolarization-block definition.
- Intermediate tests showed sustained firing at 0.45 nA but block from approximately 0.55 nA upward.

One-factor tests did not produce a robust solution across moderate and strong drive:

- sodium maxima −10%, +10%, and +20%;
- KDRI +10%;
- HH2 K +10%;
- `borgka` +10%.

Sodium +10/+20% improved moderate-current spike count and overshoot, but block persisted at 0.75/1.0 nA. Further multi-conductance fitting was not performed because it lacks direct L292-E1 or marker-specific 35 °C targets and would no longer be a simple mechanism-supported translation.

Artifact: `parameters/common/delayed_excitatory_final_35C.json`, status `NOT_READY_DEPOLARIZATION_BLOCK_AT_35C`.

## Artifacts

- Source probe before numerical fix: `results/35C/temperature_runtime_probe.json`
- Accepted probe after numerical fix: `results/35C/temperature_runtime_probe_after_HH2_fix.json`
- Original compile log: `reports/mechanism_compile_log.txt`
- Post-fix compile log: `reports/mechanism_compile_log_after_HH2_singularity_fix.txt`
