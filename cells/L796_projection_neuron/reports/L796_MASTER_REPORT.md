# L796 Model: Passive/Active Validation and Somatic B_Na Tuning — Master Report

**Model:** L796-ALT-PN reconstructed morphology (superficial dorsal horn projection neuron)
**Date:** 2026-07-06
**Simulator:** NEURON 9.0.1, run via `./external/SDHmodel/x86_64/special -python`

## 1. Motivation

The L796 active model (as tuned through Step 5) places fast Na channels
(`B_Na`) only in the artificial axon initial segment (AIS) — the soma itself
carries `KDR`, `iNaP`, `iCaL`, and `iKCa`, but no fast Na conductance. Because
somatic voltage is only driven passively/back-propagated from the AIS spike,
the somatic action potential barely crosses 0 mV (~+0.8 mV peak) and is
abnormally wide (~3.5 ms half-width). Both fail comparison against superficial
dorsal horn projection-neuron literature.

This report documents:
1. A literature-target file consolidating passive and active validation
   criteria from the literature.
2. A passive validation script confirming RMP/Rin are already on target.
3. An active validation script confirming the somatic AP failures described
   above.
4. A tuning script that inserts `B_Na` into the soma and re-balances `KDR`,
   scored against literature AP-shape targets (not the old spike-count
   heuristic used in Step 5), with a before/after comparison.

## 2. Literature targets

Source file: `literature_targets/L796_literature_targets.json`

| Target | Value / range | Source |
|---|---|---|
| RMP | −72.8 mV (± 3 mV) | Luz, Szucs & Safronov 2014 (PN group); Li & Baccei 2012 |
| Input resistance (Rin) | 0.77 GΩ (± 0.15 GΩ) | Luz, Szucs & Safronov 2014 (PN group); Li & Baccei 2012 |
| AP amplitude | 70–78 mV | Zhang et al. 2021 |
| AP half-width | 0.87–1.14 ms | Zhang et al. 2021 |
| AP overshoot | +5 to +30 mV | Zhang et al. 2021 |
| Rheobase | 20–60 pA | Zhang et al. 2021; general SDH projection-neuron literature |
| Firing pattern | delayed or tonic | Prescott & De Koninck 2002 |

## 3. Passive validation (`scripts/05_passive_validation.py`)

Protocol: passive-only model (all sections `pas` only, no active
conductances), −10 pA step (100 ms delay, 500 ms duration, 900 ms tstop),
RMP measured pre-stimulus, Rin measured from steady-state deflection.

| Feature | Model value | Target | Result |
|---|---|---|---|
| RMP | −72.80 mV | −72.8 ± 3 mV | **PASS** |
| Rin | 0.7694 GΩ | 0.77 ± 0.15 GΩ | **PASS** |

Output: `validation/passive/L796_passive_validation.csv`, traces in
`traces/passive/`.

## 4. Active validation, baseline model (`scripts/06_active_validation.py`)

Baseline = current Step-5 best-tuned active model: `BNa_scale=1.45` (AIS
only), `KDR_scale=0.5`, `KCa_scale=0.25`, `CaL_scale=1.25`, `iNaP_scale=1.0`,
`CaAN_scale=1.25`. Soma has **no** fast Na channel. Rheobase found via a
5 pA sweep (0–100 pA); AP shape measured at the first spiking current using a
dV/dt-onset criterion (10 mV/ms).

| Feature | Model value | Target | Result |
|---|---|---|---|
| AP amplitude | 41.24 mV | 70–78 mV | **FAIL** |
| AP half-width | 3.525 ms | 0.87–1.14 ms | **FAIL** |
| AP overshoot | 0.82 mV | +5 to +30 mV | **FAIL** |
| Rheobase | 25 pA | 20–60 pA | PASS |
| Firing pattern | delayed | delayed/tonic | PASS |

This confirms the motivating diagnosis: the somatic AP essentially fails to
overshoot 0 mV and is roughly 3× too wide, while passive and firing-pattern /
rheobase properties are already acceptable.

Output: `validation/active/L796_active_validation.csv`, traces in
`traces/active_baseline/`.

## 5. Somatic B_Na tuning (`scripts/07_tuning.py`)

`B_Na` was inserted into the soma and swept over an absolute density grid;
`KDR_scale` (applied uniformly to soma/dendrite/AIS `KDR`, as in the Step 5
convention) was swept alongside it. All other active scales and all passive
parameters were held fixed at the Step 5 best-tuned values. Each candidate
was scored by the sum of normalized errors against the AP-shape literature
targets (amplitude, half-width, overshoot, rheobase) — explicitly **not**
the old Step 5 spike-count-pattern heuristic — using a fast/short protocol
(20 ms delay, 150 ms stimulus, 180 ms tstop) for search speed, then the
winning candidate was re-characterized with the full 900 ms protocol.

**Grid (final, after widening once during review):**
- Soma `B_Na` density: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50 S/cm²
- `KDR_scale`: 0.35, 0.45, 0.55, 0.65, 0.75, 0.90, 1.05, 1.20, 1.35, 1.50
  (originally specified as 0.35–0.9; every top candidate from that first
  pass sat at the 0.9 edge with half-width still improving, so the grid was
  widened up to 1.5 on request)

**Best candidate:** soma `B_Na` density = 0.10 S/cm², `KDR_scale` = 1.5

### Before / after comparison (full 900 ms protocol)

| Feature | Before (no somatic B_Na) | After (tuned) | Target | Before result | After result |
|---|---|---|---|---|---|
| AP amplitude | 41.24 mV | **77.95 mV** | 70–78 mV | FAIL | **PASS** |
| AP half-width | 3.525 ms | **1.475 ms** | 0.87–1.14 ms | FAIL | FAIL (improved 2.4×) |
| AP overshoot | 0.82 mV | **34.75 mV** | +5 to +30 mV | FAIL | FAIL (just above upper bound) |
| Rheobase | 40 pA | 30 pA | 20–60 pA | PASS | PASS |
| Firing pattern | delayed | delayed | delayed/tonic | PASS | PASS |

Winning parameter set saved to
`validation/tuning/L796_best_tuned_parameter_set.json`; all 80 scored
candidates in `validation/tuning/L796_tuning_all_candidates.csv`; before/after
voltage traces in `traces/tuning/`.

### Interpretation

- Adding somatic `B_Na` fixes the core qualitative failure: the somatic AP
  now clearly overshoots 0 mV (+34.75 mV vs +0.82 mV before) and AP
  amplitude now falls inside the literature range.
- Half-width improved by more than 2× (3.53 → 1.48 ms) but plateaus short of
  the 0.87–1.14 ms target. Within the grid, half-width kept improving as
  `KDR_scale` increased, but the marginal gain shrank sharply near the top of
  the range (1.65 ms at KDR 0.9 → 1.48 ms at KDR 1.5), suggesting the
  remaining gap is set by the intrinsic gating kinetics of the `B_Na`
  mechanism itself (fixed in `B_NA.mod`), not by density/KDR balance alone.
  Reaching the literature half-width would likely require tuning `B_Na`
  kinetics (e.g. `tau_factor`), which was out of scope for this pass.
- Overshoot is fixed directionally but the winning candidate lands slightly
  above the 30 mV upper bound. Lower-density soma `B_Na` (~0.05 S/cm²)
  configurations land overshoot and rheobase inside their target bands, but
  at the cost of amplitude dropping just under 70 mV and half-width staying
  ~1.9 ms — a genuine three-way tradeoff within this grid, not a scoring
  bug.
- Rheobase and firing pattern (delayed) remain within range in both the
  before and after models.

## 6. Summary table (all validations)

| Validation | Feature | Result |
|---|---|---|
| Passive | RMP | PASS |
| Passive | Rin | PASS |
| Active (baseline) | AP amplitude | FAIL |
| Active (baseline) | AP half-width | FAIL |
| Active (baseline) | AP overshoot | FAIL |
| Active (baseline) | Rheobase | PASS |
| Active (baseline) | Firing pattern | PASS |
| Active (tuned, after) | AP amplitude | PASS |
| Active (tuned, after) | AP half-width | FAIL (improved 2.4×) |
| Active (tuned, after) | AP overshoot | FAIL (just above range) |
| Active (tuned, after) | Rheobase | PASS |
| Active (tuned, after) | Firing pattern | PASS |

## 7. Files produced

```
literature_targets/L796_literature_targets.json
scripts/05_passive_validation.py
scripts/06_active_validation.py
scripts/07_tuning.py
validation/passive/L796_passive_validation.csv
validation/active/L796_active_validation.csv
validation/tuning/L796_tuning_all_candidates.csv
validation/tuning/L796_before_after_comparison.csv
validation/tuning/L796_best_tuned_parameter_set.json
traces/passive/
traces/active_baseline/
traces/tuning/
interneurons/morphologies/ (placeholder for future circuit work)
```

## 8. Suggested next steps

1. If a full literature-range half-width/overshoot match is required, tune
   `B_Na` kinetics (`tau_factor`, `alpha_shift`/`beta_shift` in `B_NA.mod`)
   rather than density/KDR alone.
2. Consider a joint density+KDR+kinetics search once the kinetics parameters
   are in scope, since density/KDR alone appear to have hit a plateau.
3. Adopt the winning soma `B_Na` density (0.10 S/cm²) and `KDR_scale` (1.5)
   as the new Step 6 baseline if the amplitude/rheobase/firing-pattern gains
   are sufficient for current modeling purposes.
