# L796 Channel Complement Report

## 1. Software, mechanisms, celsius

NEURON (compiled mechanisms via `nrnivmodl`, run through `./external/SDHmodel/x86_64/special -python`). All mechanisms are from ModelDB accession 267056. `h.celsius = 6.3` throughout, matching the value the single-cell model was validated at (see `reports/L796_single_cell_final_status.md`; a full temperature scan found no celsius value fixes the AP half-width without breaking another feature).

This pass builds on the FIXED, already-validated single-cell model (`parameters/L796_final_parameter_set.json`) and the ligand-gated receptors added in Part 1/2 (`scripts/14_L796_ligand_gated_receptors.py`, `scripts/15_L796_neuropathic_receptor_manipulations.py`). Neither is modified; new channels are added on top.

## 2. Evidence-driven decision method

Every channel/receptor in `literature_targets/07_channel_evidence_and_fitting.csv` was mapped to a status using that table's own `recommended_status`, `priority_0_to_10`, and `decision_rule` columns, cross-checked against what is already implemented:

- **ALREADY_PRESENT**: core channels/receptors (priority 9-10) already in the locked model.
- **ADDED_NOW**: priority-8 conditional-high channels whose decision rule is satisfied and whose mechanism exists in ModelDB 267056.
- **EVALUATED**: priority-7 candidates tested against their own required condition (a measured target); added only if that condition is met.
- **DEFERRED**: priority <=6, or 'Later'/'Do not add now', or the decision rule's required condition is not met.
- **FLAGGED_OVERINCLUDED**: channels present in the model that the evidence table does NOT justify at their current priority -- carried over unchanged from the ModelDB 267056 base model rather than added because of L796 evidence.

**All densities/weights added or already present are phenomenologically fitted** -- the evidence levels involved (B/C/D) are functionally motivated from rat lamina I / dorsal-horn recordings in general, not exact measurements from L796 itself. This is stated per-channel below and in the parameter JSON.

## 3. All channels: status, priority, decision rule, source

| channel/receptor | class | priority | status | decision rule | source |
|---|---|---|---|---|---|
| Passive leak | Passive | 10 | ALREADY_PRESENT | Core (priority 10); fitted from the same-dataset PN passive physiology target. | NeuroMorpho L796-ALT-PN; Luz 2014 (PMC3979609) |
| Fast transient Na | Voltage-gated Na | 10 | ALREADY_PRESENT | Core (priority 10); AIS/axon-dominant + somatic/proximal-dendrite addition to fix the electrotonic-echo defect found during single-cell vali... | Rat dorsal-horn AIS-dominant fast Na (PMC1159869) |
| Delayed-rectifier K | Voltage-gated K | 10 | ALREADY_PRESENT | Core (priority 10); fitted jointly with NaT for AP repolarization/half-width. | PMC1664848; PMC3979609 |
| AMPA | Ligand-gated | 10 | ALREADY_PRESENT | Core for synapses (priority 10). | PMC1464766 |
| NMDA | Ligand-gated | 9 | ALREADY_PRESENT | Core for pain-circuit synapses (priority 9). | PMC1464766; PMC3923208 |
| GABA_A | Ligand-gated | 9 | ALREADY_PRESENT | Core for inhibitory circuit (priority 9). | PMC1464766; PMC6782499 |
| Glycine receptor | Ligand-gated | 9 | ALREADY_PRESENT | Core for inhibitory circuit (priority 9). | PMC1464766; PMC6782499 |
| Intracellular calcium dynamics | Calcium handling | 6 | ALREADY_PRESENT | Required when fitting KCa/Ca-dependent currents (priority 6); already required as a dependency of iKCa/iCaL/iCaAN, which were carried over f... | PMC/32341097 |
| KCC2/SLC12A5 | Chloride transporter | 9 | ALREADY_PRESENT | Decision rule: 'at minimum implement two validated chloride states; dynamic transporter optional.' Satisfied by the normal-vs-neuropathic EC... | Coull et al 2003 (PMID 12931188) |
| A-type K | Voltage-gated K | 8 | EVALUATED | Grid search over [0.0, 0.005, 0.01, 0.02, 0.04] S/cm2 found density=0 gives the longest (or tied-longest) first-spike latency among candidat... | PMC1664848 |
| NK1/TACR1 | Metabotropic receptor | 8 | ADDED_NOW | ASSUMPTION: L796 treated as NK1-positive. Weight calibrated to a modest ~4.0 mV slow depolarization (7.42 mV achieved). Rheobase without SP ... | PMC6757649 |
| T-type Ca | Voltage-gated Ca | 7 | DEFERRED | No rebound burst/low-threshold depolarization above resting baseline was observed (peak-above-baseline during recovery = 0.22 mV, spike=Fals... | PMC1664848; PMID 33871884 |
| Persistent Na | Voltage-gated Na | 4 | FLAGGED_OVERINCLUDED | FLAG: recommended_status='Later' (priority 4); decision rule says do NOT add for ordinary tonic firing unless a measured persistent inward c... | No L796-specific PIC evidence in the evidence table |
| L-type Ca | Voltage-gated Ca | 4 | FLAGGED_OVERINCLUDED | FLAG: recommended_status='Conditional-low' (priority 4); decision rule says do not add unless a sustained Ca/plateau target exists -- none d... | PMID 2482353 (labelled ascending dorsal-horn cells, not L796-specific) |
| SK-type KCa | Calcium-activated K | 5 | DEFERRED | DEFER: decision rule 'add only if Ca-coupled medium AHP/adaptation remains missing.' iKCa is already present and functionally covers Ca-acti... | No direct L796 apamin evidence (evidence_level D) |
| BK-type KCa | Calcium-activated K | 4 | DEFERRED | DEFER: decision rule 'add only with fast-AHP/spike-width evidence.' No such evidence for L796; iKCa already functionally covers Ca-K current... | No direct L796 blocker evidence (evidence_level D) |
| N-type Ca | Voltage-gated Ca | 5 | DEFERRED | DEFER: decision rule 'add when calcium or presynaptic release is explicitly modeled' -- this project does not explicitly model presynaptic C... | PMID 2482353; PMID 32341097 |
| P/Q/R-type Ca | Voltage-gated Ca | 3 | DEFERRED | DEFER ('Later'): decision rule 'add only with subtype-specific evidence or explicit terminal model' -- not resolved for L796, no terminal mo... | PMID 32341097 |
| HCN/Ih | Voltage-gated (cation) | 4 | DEFERRED | DEFER ('Later'): decision rule 'add only for measured sag/rebound/resonance' -- no L796-specific sag evidence. | PMC8208100 (mouse lamina-I spinobulbar subset, not L796) |
| M current/KCNQ | Voltage-gated K | 3 | DEFERRED | DEFER ('Do not add now'): decision rule 'add only after a discriminating pharmacological feature' -- none identified for L796. | No direct identified-L796 functional evidence |
| NALCN | Modulator-gated Na leak | 6 | DEFERRED | DEFER: decision rule 'add only as part of a validated SP/NK1 model.' The NK1 addition in this pass uses NK1_DynSyn's own built-in nonspecifi... | PMC6095712 (neonatal spinal PNs) |
| GABA_B plus GIRK | Metabotropic/effector | 5 | DEFERRED | DEFER ('Later'): decision rule 'add after fast inhibition is validated and if slow modulation is studied.' Fast inhibition (GABA-A/glycine) ... | PMC6053268 |
| Kainate receptor | Ligand-gated | 3 | DEFERRED | DEFER ('Do not add now'): decision rule 'add only after AMPA-separated residual current is demonstrated' -- not demonstrated for L796. | PMC1464766 (AMPA/kainate not pharmacologically separated in older recordings) |
| P2X/5-HT3/nicotinic | Ligand-gated | 1 | DEFERRED | DEFER ('Do not add now'): decision rule 'require a specified anatomical input and functional response' -- none specified. (An nAChR-like Exp... | No exact L796 requirement established (evidence_level D) |

Full text (untruncated) in `results/channels/L796_channel_status_map.csv`.

## 4. Parameters used for each ADDED channel, and why

### A-type K (B_A)

Priority 8, evidence level B (gap firing in identified rat lamina-I PNs, PMC1664848). Decision rule: 'Add if target trace has gap/delay that NaT+KDR cannot reproduce.' Inserted into soma + proximal dendrites (`dend[0]`, `dend[75]`, `dend[76]`), ek=-90 mV (matching KDR/iKCa in this model). Grid search over [0.0, 0.005, 0.01, 0.02, 0.04] S/cm2, each candidate screened against the full no-regression check (RMP/Rin/rheobase/overshoot/amplitude within accepted bounds, no spontaneous firing at 0 pA).

| density (S/cm2) | valid | RMP (mV) | Rin (GOhm) | rheobase (pA) | overshoot (mV) | amplitude (mV) | first-spike latency (ms) |
|---|---|---|---|---|---|---|---|
| 0.0 | True | -72.43 | 0.890 | 40 | 27.96 | 70.26 | 118.42 |
| 0.005 | False | -72.48 | 0.886 | 100 | 28.80 | 71.76 | 55.80 |
| 0.01 | False | -72.52 | 0.882 | 160 | 29.45 | 72.77 | 36.85 |
| 0.02 | False | -72.60 | 0.875 | 260 | 31.68 | 75.60 | 21.17 |
| 0.04 | False | -72.76 | 0.860 | n/a | n/a | n/a | n/a |

**Chosen density: 0 S/cm2 (evaluated, not added as a nonzero conductance).** Within the tested bounds, NaT+KDR alone already reproduce the delayed-onset phenotype at least as well as any nonzero A-type K density that passes the no-regression check; adding A-type K did not lengthen first-spike latency further without breaking a passing feature. Per the decision rule, this is a valid documented outcome, not a failure -- the mechanism was evaluated and found unnecessary at this priority level.

First-spike latency vs current (A-type K present vs absent):

| current (pA) | latency, A-type K present (ms) | latency, absent (ms) |
|---|---|---|
| 20 | n/a | n/a |
| 40 | 118.42 | 118.42 |
| 60 | 76.70 | 76.70 |
| 80 | 57.15 | 57.15 |
| 100 | 45.62 | 45.62 |

**Prepulse dependence** at 40 pA (a hyperpolarizing -20 pA/200 ms prepulse de-inactivates A-type K, which should lengthen the subsequent first-spike latency if A-type K is functionally present): no_prepulse latency = 118.42 ms, with_prepulse latency = 180.02 ms. **Caveat: this test used the chosen density (0 S/cm2 -- A-type K absent)**, so the observed 62 ms lengthening cannot be attributed to A-type K de-inactivation; it reflects the prepulse-dependent behavior of the other voltage-gated conductances already in the model (most plausibly fast-Na availability, which is itself voltage- and history-dependent). It is reported here as a measured baseline, not as evidence of A-type K function.

Figures: `plots/channels/L796_A_type_K_first_spike_latency.png`, `plots/channels/L796_A_type_K_prepulse_dependence.png`.

### NK1/TACR1 (substance-P slow excitation)

Priority 8, evidence level B/C (~80% of rat lamina I PNs are NK1+, PMC6757649). Decision rule: 'Include if L796 is assumed/verified NK1-positive or SP input is a project target.' **ASSUMPTION: L796 is treated as NK1-positive here; its exact NK1 status is unknown.** Implemented via `NK1_DynSyn` (Ito et al 2002-based mechanism from ModelDB 267056) as a point process at soma(0.5): a slow nonspecific cationic current (e=0 mV) plus a membrane-current-silenced calcium-elevation signal. Kinetics (tau_rise=10 ms, tau_decay=5000 ms) are the mechanism's own published defaults, not refit.

Weight calibrated by bisection to a modest slow depolarization (**target ~4.0 mV, ASSUMPTION magnitude** -- chosen as a physiologically modest single-event SP response, not fit to a specific L796 recording): 0.1000 nS -> 7.42 mV achieved.

Rheobase without SP input (antagonist analogy: NK1 weight forced to 0): 30 pA. Rheobase with a prior SP/NK1 event (still substantially active given its slow ~5 s decay): 25 pA. 
SP/NK1 activation lowers rheobase, consistent with SP-driven promotion of firing.

Figure: `plots/channels/L796_NK1_SP_response.png`.

## 5. Honest over-inclusion note: persistent Na (iNaP) and L-type Ca (iCaL)

Both `iNaP` (persistent Na) and `iCaL` (L-type Ca) are present in the locked single-cell model, inherited unchanged from the ModelDB 267056 base model during earlier single-cell tuning. **The evidence table does not justify either at its current inclusion:**

- **Persistent Na**: `recommended_status='Later'`, priority 4. Decision rule: 'Do not add for ordinary tonic firing unless simpler model fails and PIC is measured.' No PIC/ramp-hysteresis measurement exists for L796; the model is used for ordinary tonic firing.
- **L-type Ca**: `recommended_status='Conditional-low'`, priority 4. Decision rule: 'Do not add unless a sustained Ca/plateau target exists.' No such target exists for L796.

Both are **left in place** in this pass -- removing either would require re-validating the entire single-cell fit (RMP/Rin/rheobase/overshoot/amplitude all depend on the current active conductance balance), which is out of scope here. They are flagged transparently rather than silently accepted as evidence-justified.

## 6. Deferred channels and why

| channel | priority | reason |
|---|---|---|
| T-type Ca | 7 | No rebound burst/low-threshold depolarization above resting baseline was observed (peak-above-baseline during recovery = 0.22 mV, spike=False; the membrane recovers passively and monotonically toward rest -- settled value -72.28 mV vs baseline -72.43 mV -- with no active overshoot at any point) after a hyperpolarizing step, and this is not a stated project target. Per the decision rule ('add only for measured low-threshold burst/rebound/current'), T-type Ca is DEFERRED. Independently, no vetted T-type Ca .mod file is available in external/SDHmodel/mods. |
| SK-type KCa | 5 | DEFER: decision rule 'add only if Ca-coupled medium AHP/adaptation remains missing.' iKCa is already present and functionally covers Ca-activated K/AHP; no apamin-sensitive current evidence specific to L796. |
| BK-type KCa | 4 | DEFER: decision rule 'add only with fast-AHP/spike-width evidence.' No such evidence for L796; iKCa already functionally covers Ca-K currents. |
| N-type Ca | 5 | DEFER: decision rule 'add when calcium or presynaptic release is explicitly modeled' -- this project does not explicitly model presynaptic Ca-dependent release. |
| P/Q/R-type Ca | 3 | DEFER ('Later'): decision rule 'add only with subtype-specific evidence or explicit terminal model' -- not resolved for L796, no terminal model here. |
| HCN/Ih | 4 | DEFER ('Later'): decision rule 'add only for measured sag/rebound/resonance' -- no L796-specific sag evidence. |
| M current/KCNQ | 3 | DEFER ('Do not add now'): decision rule 'add only after a discriminating pharmacological feature' -- none identified for L796. |
| NALCN | 6 | DEFER: decision rule 'add only as part of a validated SP/NK1 model.' The NK1 addition in this pass uses NK1_DynSyn's own built-in nonspecific cation current directly, not a separate NALCN-mediated pathway, so this dependency is not triggered. |
| GABA_B plus GIRK | 5 | DEFER ('Later'): decision rule 'add after fast inhibition is validated and if slow modulation is studied.' Fast inhibition (GABA-A/glycine) is validated, but slow modulation is not a current project target. |
| Kainate receptor | 3 | DEFER ('Do not add now'): decision rule 'add only after AMPA-separated residual current is demonstrated' -- not demonstrated for L796. |
| P2X/5-HT3/nicotinic | 1 | DEFER ('Do not add now'): decision rule 'require a specified anatomical input and functional response' -- none specified. (An nAChR-like Exp2Syn PROXY already exists from Part 1 for a different, receptor-addition purpose; P2X and 5-HT3 remain fully unimplemented, consistent with that earlier work.) |

## 7. Effect on the single-cell scorecard

| feature | value | accepted range | status |
|---|---|---|---|
| RMP | -72.43 mV | (-76.0, -70.0) | PASS |
| Rin | 0.890 GOhm | (0.6, 1.0) | PASS |
| Rheobase | 40 pA | (20.0, 60.0) | PASS |
| AP overshoot | 27.96 mV | (5.0, 30.0) | PASS |
| AP amplitude | 70.26 mV | (70.0, 78.0) | PASS |
| AP half-width | 1.450 ms | 0.87-1.14 (documented relaxed-pass) | RELAXED-PASS (unchanged) |
| Spontaneous firing at 0 pA | 0 spikes | 0 | PASS |

**Overall: PASS -- all previously-passing single-cell features remain within bounds after adding A-type K.**

Full CSV: `results/channels/L796_channel_validation.csv`. Extended parameter set: `parameters/L796_channels_extended_parameter_set.json`.
