# L796 Lamina I ALT Projection-Neuron Model -- Final Completion Report

## Defect addressed

The Step-5 model inserted fast sodium (B_Na) only in the artificial AIS. The soma carried KDR, iNaP, iCaL, and iKCa but no fast Na, so the somatic AP recorded in that model was an electrotonically-conducted echo of the AIS spike (peak ~+2.6 mV, half-width ~1.9 ms) rather than a genuine regenerative somatic action potential.

This script (`scripts/13_finish_L796.py`) inserts B_Na into the soma and the 3 first-order (proximal) dendrites directly attached to the soma (dend[0], dend[75], dend[76]), with a single tunable density `soma_BNa` (S/cm2) applied to both, `ena = 55 mV`. The KDR scale (shared by soma, dendrites, and AIS) was re-searched jointly with `soma_BNa` because adding somatic fast Na changes how much repolarizing K+ current is needed for a sharp AP. All other tuned active scales (AIS BNa_scale, KCa_scale, CaL_scale, iNaP_scale, CaAN_scale) were kept fixed at the Step-5 best-tuned values. Passive parameters (e_pas, g_pas, cm, Ra) were kept fixed throughout.

## Search

**Primary grid (task-specified):** soma_BNa in [0.05, 0.1, 0.2, 0.35, 0.5] S/cm2 x KDR_scale in [0.5, 0.7, 0.9] (15 candidates), each screened at currents [-10, 0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200] pA over a 1 s step.

Candidates were rejected if they fired spontaneously at 0 pA, moved RMP outside (-76.0, -70.0) mV, moved Rin outside (0.6, 1.0) GOhm, or moved rheobase outside (20.0, 60.0) pA. Surviving candidates were scored by summed normalized error against the AP overshoot/half-width/amplitude target ranges (lower is better).

On the primary grid, the best surviving candidate (soma_BNa=0.05, KDR_scale=0.9) sat at the KDR_scale upper edge of the tested range, with half-width still above the 1.14 ms target and shrinking monotonically as KDR_scale increased. This edge effect indicated the target might be reachable just outside the literal task-specified grid, so a **refinement grid** (clearly a deliberate extension beyond the specified values, not a substitute for it) was also run: soma_BNa in [0.04, 0.05, 0.06] S/cm2 x KDR_scale in [0.9, 1.2, 1.6, 2.0, 2.5] (15 candidates), same protocol and constraints.

24 / 30 candidates survived the constraints across both grids. Full results (both grids, tagged by the `grid` column): `results/final_model/L796_final_search_candidates.csv`.

**Winning candidate (from the refinement grid):**

- soma_BNa = 0.04 S/cm2 (soma + proximal dendrites)
- KDR_scale = 2.0
- total AP-target error = 1.1481

## Before vs after (1 s somatic current-clamp sweep, 0-300 pA in 20 pA steps)

| Feature | Before (Step 5) | After (final) |
|---|---|---|
| RMP (mV) | -72.52 | -72.43 |
| Rin (GOhm) | 0.884 | 0.890 |
| tau (ms) | 207.91 | 212.67 |
| Rheobase (pA) | 40 | 40 |
| AP threshold (mV) | -40.38 | -42.31 |
| AP peak / overshoot (mV) | 0.82 | 27.96 |
| AP amplitude (mV) | 41.19 | 70.26 |
| AP half-width (ms) | 3.525 | 1.450 |
| AHP depth from threshold (mV) | 30.83 | 35.24 |
| Firing frequency at ~2x rheobase (Hz) | 10.00 | 10.00 |
| Adaptation ratio | 1.005 | 1.026 |
| First-spike latency (ms) | 143.90 | 118.42 |

Figures: `figures/final_model/L796_final_before_after_AP_overlay.png`, `figures/final_model/L796_final_before_after_FI_curve.png`.

## Validation vs literature targets (final model)

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
| Firing frequency at ~2x rheobase (Hz) | not specified (informational) | n/a | 10.000 | MEASURED |
| Adaptation ratio (last ISI / first ISI) | not specified (informational) | n/a | 1.026 | MEASURED |
| First-spike latency (ms) | not specified (informational) | n/a | 118.425 | MEASURED |

Full CSV: `results/L796_final_validation_vs_targets.csv` (also copied to `results/final_model/L796_final_validation_vs_targets.csv`).

## Acceptance check

- Somatic AP overshoot > 0 mV: **YES** (27.96 mV)
- Half-width <= 1.14 ms: **NO** (1.450 ms)
- RMP within (-76.0, -70.0) mV: **YES** (-72.43 mV)
- Rin within (0.6, 1.0) GOhm: **YES** (0.890 GOhm)
- Rheobase within (20.0, 60.0) pA: **YES** (40 pA)

**The bounds could not all be met simultaneously.** The closest achievable candidate is reported above. See the trade-off discussion below.

## Remaining limitations

- Even after extending KDR_scale beyond the task-specified upper bound (up to 2.5, vs. 0.9 specified) and exploring soma_BNa in [0.04, 0.05, 0.06] S/cm2, the best surviving candidate's half-width (1.450 ms) could not be brought down to the 1.14 ms target without raising soma_BNa enough to break the AP amplitude target (70-78 mV) or trigger spontaneous firing. A wider search that also varies KCa_scale/CaL_scale (currently held fixed at their Step-5 values) might close the remaining gap, but was out of scope here.
- AP threshold, AHP depth, firing frequency at 2x rheobase, adaptation ratio, and first-spike latency are reported as measured, informational values: the source literature (Zhang 2021, Luz 2014) used for this validation did not supply numeric targets for these features, so no PASS/FAIL verdict is assigned to them.
- Because the proximal dendrites and soma share a single `soma_BNa` density rather than independent densities, the search cannot separately tune backpropagation-related dendritic excitability vs. the somatic spike shape; this was a deliberate simplification to keep the search tractable, consistent with the task's tunable-density specification.
- The model does not reproduce a specific published L796 recording; it is tuned to fall within reported population ranges (Zhang 2021, Luz 2014), so cell-to-cell variability within those ranges is not captured.
