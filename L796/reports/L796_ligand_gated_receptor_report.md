# L796 Ligand-Gated Receptor Report

Ligand-gated receptors were added to the FIXED, already-validated L796 single-cell active model (`parameters/L796_final_parameter_set.json`; see `reports/L796_single_cell_final_status.md` for the single-cell closeout, including the accepted AP half-width relaxed-pass). The active conductance densities were not changed while testing synapses. `h.celsius` is explicitly set to 6.3 degC throughout (the value the single-cell model was validated at).

**All synaptic conductances (AMPA/NMDA/GABA-A/glycine/nAChR-like weights) are phenomenological**: they are tuned to produce a physiological unitary EPSP/IPSP amplitude (target 0.5-5 mV), not measured or fit to any L796-specific synaptic recording. See `literature_targets/06_receptor_target_values.csv` for confidence grades on every kinetic parameter.

## Dendrite locations used

| location | section | path distance from soma (um) |
|---|---|---|
| proximal | dend[69] | 131.4 |
| mid | dend[41] | 395.0 |
| distal | dend[32] | 563.0 |

## 1a. Glutamatergic: AMPA + NMDA

AMPA: tau_rise=0.5 ms, tau_decay=2.5 ms, e=0.0 mV (AMPA_DynSyn.mod, tau values adjusted from mechanism defaults to match the literature-cited fast-AMPA range). NMDA: tau_rise=5.0 ms, tau_decay=70.0 ms, e=0.0 mV, Mg2+ block via the Jahr & Stevens (1990) equation implemented directly in NMDA_DynSyn.mod (mgo=1.0 mM) -- this is a real published equation, not a proxy. Co-located at a fixed NMDA:AMPA weight ratio of 0.5 (phenomenological assumption).

| location | receptors | weight AMPA (nS) | weight NMDA (nS) | amplitude (mV) | rise time (ms) | decay tau (ms) | latency (ms) |
|---|---|---|---|---|---|---|---|
| proximal | AMPA+NMDA | 1.920 | 0.960 | 2.033 | 2.92 | 29.09 | 0.75 |
| proximal | AMPA-only | 1.920 | 0.000 | 1.907 | 2.60 | 14.13 | 0.72 |
| mid | AMPA+NMDA | 1.920 | 0.960 | 1.564 | 7.50 | 28.89 | 2.37 |
| distal | AMPA+NMDA | 1.920 | 0.960 | 1.072 | 26.90 | 28.70 | 4.52 |

Unitary EPSP amplitude was calibrated to ~2 mV at the proximal location (2.033 mV achieved), within the 0.5-5 mV target. Applying the same weight at mid and distal locations shows clear proximal-to-distal attenuation (see table and `plots/receptors/L796_EPSP_traces_by_location.png`).

**NMDA Mg2+ block relief with depolarization** (`plots/receptors/L796_NMDA_mgblock.png`): unblock fraction rises from 0.025 at -80 mV to -0.387 at +20 mV, measured via voltage clamp (a direct out-of-simulation call to the mechanism's own mgblock() function was tried first but found unreliable; see script comments). Peak NMDA current: -0.00300 nA at Vhold=-70 mV vs -0.00716 nA at Vhold=-20 mV -- NMDA contribution clearly grows with depolarization, confirming Mg2+ unblock.

**EPSP-to-spike via NMDA-dependent temporal summation** (5-pulse train, `plots/receptors/L796_AMPA_NMDA_summation.png`):

| frequency (Hz) | condition | peak depolarization (mV) | spike fired |
|---|---|---|---|
| 20 | AMPA+NMDA | 25.83 | True |
| 20 | AMPA-only | -59.05 | False |
| 50 | AMPA+NMDA | 30.82 | True |
| 50 | AMPA-only | -52.30 | False |

## 1b. Inhibitory: GABA-A + Glycine

GABA-A: tau_rise=1.0 ms, tau_decay=20.0 ms (GABAa_DynSyn.mod defaults). Glycine: tau_rise=1.0 ms, tau_decay=10.0 ms (Glycine_DynSyn.mod defaults). ECl = -70.0 mV for both (control condition, Coull 2003).

RMP (-72.43 mV) sits close to ECl (-70.0 mV), so at rest a chloride conductance has little driving force and is almost pure shunt -- a real property of GABA-A/glycine near rest, not a modeling artifact. IPSP amplitude/kinetics below were therefore characterized from a depolarized holding potential (+14.0 pA bias current, baseline ~-60 mV) to give adequate driving force; the shunting demonstration further below uses normal resting potential, since shunting does not require a large driving force to be effective.

| receptor | weight (nS) | amplitude (mV) | rise time (ms) | decay tau (ms) | latency (ms) |
|---|---|---|---|---|---|
| GABA-A | 6.129 | 2.003 | 14.02 | 27.21 | 3.80 |
| Glycine | 10.025 | 2.021 | 8.35 | 25.12 | 2.57 |
| GABA-A+Glycine | 16.154 | 3.449 | 11.22 | 26.54 | 2.32 |

**Glycine decays faster**, as expected (GABA-A tau_decay=20.0 ms vs Glycine tau_decay=10.0 ms at the mechanism level; somatic decay tau above is broadened by cable/membrane filtering but preserves the same ordering).

**Shunting inhibition** (`plots/receptors/L796_shunting_demo.png`): a 50 Hz excitatory train (AMPA+NMDA) that fires a spike alone is blocked when GABA-A+Glycine are co-activated simultaneously, at normal resting potential. A direct scan found the single-unitary-synapse GABA-A+Glycine weight (the same weight calibrated above for a ~2 mV IPSP) does NOT shunt-block this train -- blocking only occurs around 15x that weight, used here as a stand-in for convergent input from several co-active inhibitory interneurons (a population-level inhibitory barrage), not a claim that a single GABAergic/glycinergic synapse can shunt-block this train on its own:

| condition | peak depolarization (mV) | spike fired | inhibition weight multiplier |
|---|---|---|---|
| EPSP train alone | 30.82 | True | 0.0x |
| EPSP train + inhibition | -58.56 | False | 15.0x |

## 1c. nAChR-like receptor (documented proxy)

CAVEAT: in the dorsal horn, nAChR activation is predominantly ANTINOCICEPTIVE, acting largely PRESYNAPTICALLY and on INHIBITORY interneurons to enhance GABA/glycine release. Placing an nAChR-like conductance directly on the L796 projection-neuron soma/dendrite, as done here, is a simplification for demonstrating ligand-gated depolarization and summation; it does NOT reproduce the in-vivo cholinergic analgesic circuit, and no real, vetted nAChR .mod file was available in external/SDHmodel/mods, so this is a documented Exp2Syn PROXY (alpha4beta2-like kinetics: tau1=1 ms, tau2=30 ms, e=0 mV), not a validated nAChR model.

Single-pulse depolarization calibrated to ~2 mV: 2.014 mV achieved, decay tau 27.63 ms (synaptic tau2=30.0 ms).

| condition | peak depolarization above baseline (mV) | spike fired |
|---|---|---|
| nAChR-like alone | 2.01 | False |
| AMPA+NMDA alone | 2.03 | False |
| nAChR-like + AMPA+NMDA (combined) | 3.97 | False |

nAChR-like activation depolarizes L796 and summates with glutamatergic drive (`plots/receptors/L796_nAChR_depolarization.png`), demonstrating the requested ligand-gated cation-channel behavior -- but see the caveat above: this does not represent the real (predominantly presynaptic/interneuronal, antinociceptive) cholinergic circuit in the dorsal horn.

## 1d. Deferred: P2X and 5-HT3

No vetted P2X3/P2X4 or 5-HT3 .mod file is available in `external/SDHmodel/mods`. Per the guardrails, these are **not implemented** (not faked with an unlabeled proxy) and are listed as future work. Both are neuropathic-pain-relevant (P2X: microglia-BDNF-KCC2 axis, Tsuda 2003/Trang 2012; 5-HT3: descending facilitation, Suzuki 2004) -- see `literature_targets/06_receptor_target_values.csv`.

## Limitations

- All synaptic weights are phenomenological (tuned to a target EPSP/IPSP amplitude), not measured for L796; the underlying active-conductance densities they act on are themselves phenomenologically fitted (see the single-cell status report).
- The NMDA:AMPA weight ratio (0.5) and the AMPA/GABA-A/glycine tau values (mechanism defaults, with AMPA tau_rise/tau_decay adjusted to the literature-cited range) are assumptions/defaults, not L796-specific fits.
- The nAChR-like receptor is a documented Exp2Syn proxy on the projection neuron itself; it does not reproduce the presynaptic/interneuronal site of real dorsal-horn nAChR action.
- P2X and 5-HT3 are deferred (no vetted mechanism available), not implemented.
- The shunting demonstration uses 15x the single-unitary-synapse GABA-A+Glycine weight -- a direct scan confirmed the unitary weight alone (the same weight calibrated above for a realistic ~2 mV IPSP) does not block the excitatory train tested here. The multiplier is intended to represent several co-active inhibitory interneurons converging on the same location, not a single synapse; it was not independently validated against a specific convergence count from the literature.
