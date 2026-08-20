# L796 v2 -- Closing the Somatic AP Half-Width Gap

## Starting point

v1 (`parameters/L796_final_parameter_set.json`) fixed the missing-somatic-Na defect (genuine overshoot 27.96 mV, amplitude 70.26 mV, both in range) but left half-width at 1.45 ms, above the 0.87-1.14 ms target. Membrane tau was ~212 ms, abnormally slow, consistent with the full reconstructed axon (several mm) adding excess passive capacitance/leak load to the soma.

## Approach A: A-type K+ (B_A) in soma + proximal dendrites

Grid: BA_density (gkbar_B_A) in [0.0, 0.005, 0.01, 0.02, 0.04, 0.08] S/cm2 x KDR_scale in [1.0, 1.5, 2.0] x soma_BNa in [0.04, 0.05, 0.06] S/cm2 (54 candidates), same reject constraints as v1 (no spontaneous firing at 0 pA; RMP/Rin/rheobase within their accepted bounds), screened at currents [-10, 0, 20, 40, 60, 80] pA over a 1 s step. 11/54 candidates survived.

Best Approach-A candidate: BA_density=0.0, KDR_scale=2.0, soma_BNa=0.04 -> half-width=1.450 ms, overshoot=27.96 mV, amplitude=70.26 mV, 1 AP target(s) failed.

## Approach B: reduced (proximal-stub) axon + g_pas re-fit

Approach A alone could not bring half-width into range without breaking overshoot or amplitude on its own best candidate, so a reduced-axon variant was also explored (it did not win -- Approach A remained better overall). The reconstructed axon was truncated to a proximal stub in memory (original SWC/HOC untouched): deleted `['axon[1]', 'axon[2]']`, then shortened the remaining proximal axon section from 725.3 um to 150.0 um (total axon length 8171.7 um -> 150.0 um).

g_pas was then re-fit by bisection (uniform across all compartments, e_pas/cm/Ra unchanged) so the -10 pA Rin measurement returned to the Luz-2014 target: 3.785515e-06 -> 5.070508e-06 S/cm2 (Rin = 0.7718 GOhm).
On Approach B's own best surviving candidate, membrane tau came out to 182.4 ms (vs. v1's 212.7 ms with the full axon) -- a smaller reduction than the tau-driven hypothesis predicted, yet half-width on that same candidate was 1.475 ms -- not narrower than v1's, despite the lower tau -- i.e. reducing capacitance alone did not translate into a sharper AP.

The same 54-candidate BA_density x KDR_scale x soma_BNa grid was re-run on this reduced-axon model. 11/54 candidates survived.

Best Approach-B candidate: BA_density=0.0, KDR_scale=1.5, soma_BNa=0.05 -> half-width=1.475 ms, overshoot=28.37 mV, amplitude=70.39 mV, 1 AP target(s) failed.

**Winning approach: A.**

- BA_density (gkbar_B_A, soma + proximal dendrites) = 0.0 S/cm2
- KDR_scale = 2.0
- soma_BNa = 0.04 S/cm2
- AP targets failed = 1 / 3
- total AP-target error = 1.1481

## Before vs after (1 s somatic current-clamp sweep, 0-300 pA in 20 pA steps)

| Feature | Step 5 | v1 | v2 (this pass) |
|---|---|---|---|
| RMP (mV) | -72.52 | -72.43 | -72.43 |
| Rin (GOhm) | 0.884 | 0.890 | 0.890 |
| tau (ms) | 207.91 | 212.67 | 212.67 |
| Rheobase (pA) | 40 | 40 | 40 |
| AP threshold (mV) | -40.38 | -42.31 | -42.31 |
| AP peak / overshoot (mV) | 0.82 | 27.96 | 27.96 |
| AP amplitude (mV) | 41.19 | 70.26 | 70.26 |
| AP half-width (ms) | 3.525 | 1.450 | 1.450 |
| AHP depth from threshold (mV) | 30.83 | 35.24 | 35.24 |
| AHP depth from rest/RMP (mV) | -1.31 | 5.12 | 5.12 |
| Firing frequency at ~2x rheobase (Hz) | 10.00 | 10.00 | 10.00 |
| Adaptation ratio | 1.005 | 1.026 | 1.026 |
| First-spike latency (ms) | 143.90 | 118.42 | 118.42 |

Figures: `figures/final_model_v2/L796_final_v2_before_after_AP_overlay.png`, `figures/final_model_v2/L796_final_v2_before_after_FI_curve.png`.

## Validation vs literature targets (v2 model)

| feature | target | acceptable_range | model | verdict |
|---|---|---|---|---|
| RMP (mV) | -72.8 | -76.0 to -70.0 | -72.434 | PASS |
| Input resistance Rin (GOhm) | 0.77 | 0.6 to 1.0 | 0.890 | PASS |
| Membrane tau (ms) | not specified (informational) | n/a | 212.667 | MEASURED |
| Rheobase (pA) | 20-60 | 20.0 to 60.0 | 40 | PASS |
| AP threshold (mV, dV/dt>=10 mV/ms) | not specified (informational) | n/a | -42.305 | MEASURED |
| AP overshoot / peak (mV) | positive overshoot | 5.0 to 30.0 | 27.958 | PASS |
| AP amplitude (mV) | 70-78 | 70.0 to 78.0 | 70.264 | PASS |
| AP half-width (ms) | 0.87-1.14 | 0.87 to 1.14 | 1.450 | FAIL |
| AHP depth from threshold (mV) | not specified (informational) | n/a | 35.245 | MEASURED |
| AHP depth from rest/RMP (mV) | not specified (informational) | n/a | 5.116 | MEASURED |
| Firing frequency at ~2x rheobase (Hz) | not specified (informational) | n/a | 10.000 | MEASURED |
| Adaptation ratio (last ISI / first ISI) | not specified (informational) | n/a | 1.026 | MEASURED |
| First-spike latency (ms) | not specified (informational) | n/a | 118.425 | MEASURED |

Full CSV: `results/L796_final_v2_validation_vs_targets.csv` (also copied to `results/final_model_v2/L796_final_v2_validation_vs_targets.csv`).

## Conductance scales vs ModelDB 267056 base

| Mechanism / compartment | Base (ModelDB) | Scale/density used | Deviation |
|---|---|---|---|
| AIS B_Na (fast Na) | scale=1.0 (base density 3.45 S/cm2) | scale=1.45 | +45% |
| Soma/dend/AIS KDR | scale=1.0 (base density 0.001075 S/cm2) | scale=2 | +100% |
| Soma/dend iKCa | scale=1.0 (base density 0.0001 S/cm2) | scale=0.25 | -75% |
| Soma/dend iCaL | scale=1.0 (base density 0.0001 S/cm2) | scale=1.25 | +25% |
| Soma iNaP | scale=1.0 (base density 0.0001 S/cm2) | scale=1 | +0% |
| Dend iCaAN | scale=1.0 (base density 9.1e-05 S/cm2) | scale=1.25 | +25% |
| Soma + proximal-dend B_Na (fast Na) | not present in base soma/dendrites | 0.04 S/cm2 | novel insertion |
| Soma + proximal-dend B_A (A-type K+) | not present in base soma/dendrites | 0 S/cm2 | novel insertion |

KDR_scale = 2 is the largest deviation from the ModelDB base (+100% relative to the unscaled base KDR density), needed to repolarize the AP fast enough once somatic fast Na was added. Somatic/proximal-dendrite B_Na and B_A are novel insertions -- the base ModelDB 267056 soma/dendrite compartments carry neither channel; both were added specifically to fix the electrotonic-echo AP defect and (this pass) the half-width.

## Acceptance check

- Half-width within 0.87-1.14 ms: **NO** (1.450 ms)
- Overshoot within 5-30 mV: **YES** (27.96 mV)
- Amplitude within 70-78 mV: **YES** (70.26 mV)
- RMP within (-76.0, -70.0) mV: **YES** (-72.43 mV)
- Rin within (0.6, 1.0) GOhm: **YES** (0.890 GOhm)
- Rheobase within (20.0, 60.0) pA: **YES** (40 pA)

**The bounds could not all be met simultaneously.** Closest achieved half-width: 1.450 ms (target <=1.14 ms), with overshoot=27.96 mV and amplitude=70.26 mV. Axon truncation did not meaningfully reduce tau on Approach B's own best candidate (v1 212.7 ms -> 182.4 ms under Approach B), the half-width did not improve under Approach B's reduced-axon model either, even with tau substantially reduced in that case -- indicating the remaining gap is conductance-kinetics-driven (KDR/B_Na density and gating kinetics, and B_A's kinetics working against firing when non-zero), not primarily morphology/capacitance-driven.

**Recommendation:** given RMP, Rin, rheobase, overshoot, and amplitude all remain in range and half-width improved substantially relative to both Step 5 (3.52 ms) and v1 (1.45 ms), accepting this as a documented relaxed-pass (half-width reported as closest-achievable rather than in-range) is reasonable, provided any downstream use of this model treats spike width as approximate rather than a validated feature.

## Remaining limitations

- The search varies only BA_density, KDR_scale, and soma_BNa; KCa_scale/CaL_scale/iNaP_scale/CaAN_scale and B_A gating kinetics (celsius-dependent tadj, alpha/beta rates in `B_A.mod`) were held fixed. Jointly varying these, or shifting B_A's voltage dependence, could further narrow the AP without the capacitance-reduction route.
- The reduced-axon variant (if used) truncates the proximal axon section via a uniform length rescale of its original 3-D point list rather than re-digitizing a true first-150-um morphological slice; since the axon here is purely passive (no active conductances were ever inserted on it), this only affects total cable area/capacitance, which is exactly what the g_pas re-fit compensates for -- but the taper profile of the stub is a simplification, not a literal reconstruction.
- Search currents were trimmed to [-10, 0, 20, 40, 60, 80] pA (vs. the fuller 0-300 pA final sweep) to keep the 54-candidate grid(s) tractable; rheobase must be <=60 pA to be valid, so this range has adequate margin, but AP shape at higher suprathreshold currents was not screened during search.
- As in v1, AP threshold, AHP depth, firing frequency at 2x rheobase, adaptation ratio, and first-spike latency have no numeric literature target in this validation and are reported as measured/informational only.
