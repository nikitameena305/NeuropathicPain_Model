# L796 Single-Cell Model — Final Status

## Summary

**The single-cell model is locked as `parameters/L796_final_parameter_set.json`, with AP
half-width accepted as a documented relaxed-pass.** Temperature correction was tested as
required by this task and does **not** close the half-width gap without breaking another
passing feature. Active conductance densities remain **phenomenologically fitted**, not
measured for L796 specifically.

## What was checked (Part 0a)

None of the prior L796 scripts (`13_finish_L796.py`, `15_close_halfwidth_v2.py`) ever set
`h.celsius` explicitly. NEURON's default is `6.3 degC` (the classic Hodgkin-Huxley squid-axon
value) — every previously reported v1/v2 number (RMP, Rin, rheobase, overshoot, amplitude,
half-width) was therefore produced at 6.3 degC, not at any physiological temperature.

Inspection of the ModelDB 267056 mechanisms shows this matters: `KDR`, `iNaP`, `iCaL`, `iCaAN`,
`iKCa`, and `B_A` all scale their gating **tau** by a real `q10`/`tadj` factor of the form
`3^((celsius - ref)/10)` (ref ranges 22-37 degC across mechanisms) — so raising celsius
genuinely speeds up repolarization. `B_Na` (the fast-Na spike current) is the exception: it
computes a `tadj` variable in its `INITIAL` block but never actually multiplies it into the
state time constants, so **B_Na's kinetics are temperature-invariant** in this implementation
(upstroke speed does not change with celsius; only the repolarizing K+/Ca2+ currents do).

Zhang 2021 (the half-width literature target) records at approximately 32 degC.

### Coarse scan (20 pA current resolution, v1 densities: soma_BNa=0.04, KDR_scale=2.0)

| celsius | RMP | Rin | rheobase (pA) | overshoot (mV) | amplitude (mV) | half-width (ms) | all pass? |
|---|---|---|---|---|---|---|---|
| 6.3 (prior default) | -72.43 PASS | 0.890 PASS | 40 PASS | 27.96 PASS | 70.26 PASS | 1.450 FAIL | No |
| 12.0 | -72.43 PASS | 0.890 PASS | 60 PASS | 28.25 PASS | 71.18 PASS | 1.025 PASS | **Yes (coarse)** |
| 23.0 | -72.44 PASS | 0.890 PASS | 100 FAIL | 20.84 PASS | 64.03 FAIL | 0.675 FAIL | No |
| 35.0 (Zhang 2021 recording temp) | -72.44 PASS | 0.890 PASS | 160 FAIL | 1.42 FAIL | 44.48 FAIL | 0.600 FAIL | No |

At the literal Zhang-2021-matched temperature (35 degC), half-width over-shrinks past the
target window and rheobase/overshoot/amplitude all fail badly: the faster K+/Ca2+ currents
increasingly out-compete the temperature-invariant B_Na current as celsius rises, clamping the
spike down and raising the current needed to reach threshold.

### Fine-resolution re-check (5 pA current resolution, spike shape measured at the *true*
### rheobase rather than the nearest 20 pA multiple)

celsius=12.0 looked like a full pass at 20 pA resolution, but that used a spike evoked well
above the true rheobase (60 pA vs the true ~45 pA), and near-threshold spikes are measurably
smaller. Re-measured properly:

| celsius | rheobase (pA) | overshoot (mV) | amplitude (mV) | half-width (ms) | all pass? |
|---|---|---|---|---|---|
| 11.0 | 40 PASS | 23.97 PASS | 65.82 **FAIL** (short by 4.2 mV) | 1.125 PASS | No |
| 11.5 | 40 PASS | 22.54 PASS | 64.01 **FAIL** (short by 6.0 mV) | 1.075 PASS | No |
| 12.0 | 45 PASS | 24.84 PASS | 66.99 **FAIL** (short by 3.0 mV) | 1.050 PASS | No |
| 12.5 | 45 PASS | 23.97 PASS | 65.84 **FAIL** (short by 4.2 mV) | 1.050 PASS | No |
| 13.0 | 45 PASS | 22.72 PASS | 64.42 **FAIL** (short by 5.6 mV) | 1.025 PASS | No |

Under a resolution-robust measurement (spike shape at the true rheobase, not the nearest
coarse current step), **no celsius value in the tested range achieves a simultaneous pass**:
low celsius (near 6.3) passes everything except half-width; the 11-13 degC band gets
half-width, overshoot, RMP, and Rin right but amplitude falls consistently 3-6 mV short of the
70 mV floor; and celsius >= 18 additionally breaks rheobase.

## Conclusion (Part 0b)

**Temperature does not close the half-width gap without breaking a passing feature.** This is
consistent with, and adds evidence to, the v2 study's conclusion that the remaining half-width
gap is channel-kinetics-driven: even deliberately exploiting the mechanisms' own built-in
temperature sensitivity cannot simultaneously satisfy all six target features, because B_Na
(the current that sets spike amplitude/overshoot) does not speed up with temperature while the
repolarizing currents do — there is no celsius value where the two are back in the balance that
the v1 density-tuning found at 6.3 degC.

**AP half-width is accepted as a documented relaxed-pass** (closest achieved: 1.45 ms vs a
0.87-1.14 ms target), exactly as anticipated by this task's Part 0b fallback.

`parameters/L796_final_parameter_set.json` is locked as the single-cell model of record.
`h.celsius` will be **explicitly set to 6.3 degC** in all subsequent (receptor/neuropathic)
scripts, to document this previously-implicit value rather than leaving it as an unstated
NEURON default, and because it is the value under which every other feature (RMP, Rin,
rheobase, overshoot, amplitude) was validated.

## On the nature of the active-conductance densities

The active conductance densities in `parameters/L796_final_parameter_set.json` (soma_BNa,
proximal-dendrite B_Na, KDR_scale, and the other scale factors carried over from Step 5) are
**phenomenologically fitted** to reproduce literature-reported feature *ranges* (Luz 2014,
Zhang 2021) — they are not measured conductance densities for L796 specifically, and the base
densities themselves come from ModelDB 267056 (a different preparation). This was already true
of the v1/v2 models and remains true here; it is restated for the record because Part 1 of this
task (ligand-gated receptors) builds directly on top of this fixed, phenomenological active
model.

## Locked single-cell feature scorecard (celsius = 6.3 degC)

| feature | target | model | verdict |
|---|---|---|---|
| RMP (mV) | -72.8 | -72.43 | PASS |
| Rin (GOhm) | 0.77 | 0.890 | PASS |
| Rheobase (pA) | 20-60 | 40 | PASS |
| AP overshoot (mV) | 5-30 | 27.96 | PASS |
| AP amplitude (mV) | 70-78 | 70.26 | PASS |
| AP half-width (ms) | 0.87-1.14 | 1.45 | FAIL (accepted relaxed-pass) |

**Verdict: single-cell model finalized with one documented relaxed-pass (half-width,
channel-kinetics-limited). Proceeding to Part 1 (ligand-gated receptors) on this fixed model.**
