# Evidence-based ion-channel and receptor audit: L796-ALT-PN and a future excitatory interneuron

**Audit date:** 2026-07-09  
**Project scanned:** `C:\Users\Nikita\NeuropathicPain_Model`  
**Requested L796 cell:** L796-ALT-PN, rat lumbar lamina I anterolateral-tract projection neuron  
**Scope:** report and recommendations only; no model, morphology, or mechanism file was modified

> **Focused biological inventory:** The project-file audit below answers what can be verified in the available checkout. The projection-neuron-specific literature synthesis, evidence grades, score calculation, complete voltage-/ligand-gated list, and feature-by-feature fitting plan are provided in `L796_ALT_PN_biological_channel_inventory.md`. Its source-linked data table is `L796_ALT_PN_channel_evidence_and_fitting.csv`. These companion files supersede any interpretation of the priority scores as direct L796 expression measurements.

## Executive conclusion

The project checkout does **not currently contain the L796 NEURON model package**. A recursive scan found six files: three interneuron SWCs, one interneuron-selection report, one interneuron metadata JSON, and one candidate CSV. It found **zero `.hoc`, `.py`, or `.mod` files**, no L796 parameter JSON/CSV, no compiled mechanism library, no simulation output, and no L796 validation trace or feature table.

Therefore:

- No membrane mechanism can be honestly classified as inserted into L796.
- No project-local mechanism can be classified as compiled/available but uninserted.
- No receptor or synaptic point process can be confirmed as instantiated.
- No mechanism can be classified as loaded but unused.
- Conductances, reversal potentials, section locations, and insertion file/line numbers are all **not auditable from this checkout**.
- “Not demonstrated in the checkout” must not be confused with biological absence or with absence from a different, unscanned copy of the model.

The safest build order, once the actual L796 model package is restored, is:

1. establish and freeze passive targets;
2. establish a minimal fast-Na + delayed-rectifier-K spike model;
3. add A-type K only if a measured delayed/gap feature is a target;
4. add receptor models only for explicit circuit experiments;
5. add persistent Na, CaT/CaL, calcium dynamics, SK/BK, Ih, or M-current only when a named electrophysiological feature cannot be reproduced by the simpler model.

This is a reconstructed-morphology, feature-tuning problem—not an exact, cell-specific conductance-density reconstruction. The exact morphology identity is well supported, but most electrophysiological targets are group-level comparators.

## 1. Evidence hierarchy and interpretation rules

### 1.1 Evidence hierarchy

1. **Current project files:** decisive for project status and mechanism use.
2. **Exact-cell identity:** NeuroMorpho confirms L796-ALT-PN as NMO_34019, rat/Wistar, P14–P21, lumbar lamina I, projection/principal cell, anterolateral-targeting, with soma, dendrites, and axon ([NeuroMorpho L796-ALT-PN](https://neuromorpho.org/neuron_info.jsp?neuron_name=L796-ALT-PN)).
3. **Same-dataset physiology:** Luz, Szucs & Safronov 2014 provides group-level passive properties and firing classes for identified lamina I projection neurons, not cell-specific channel densities ([PMC3979609](https://pmc.ncbi.nlm.nih.gov/articles/PMC3979609/)).
4. **Identified lamina I projection-neuron studies:** used for plausible active and synaptic features, not as exact L796 measurements.
5. **Broader lamina I/dorsal-horn studies:** used only to motivate a conditional test.
6. **Transcriptomic expression:** insufficient by itself to justify a mechanism.

### 1.2 Status vocabulary

- **Present:** directly instantiated or inserted in scanned project code.
- **Available:** a matching project-local MOD or compiled mechanism is present but not instantiated.
- **Missing from checkout:** neither code nor project-local compiled support is present.
- **Not auditable:** the required model or output file is absent.
- **Conditional:** add only if a measurable target feature and suitable evidence exist.

Core NEURON distributions commonly include generic mechanisms such as `pas`, `hh`, `ExpSyn`, and `Exp2Syn`. That runtime fact does **not** prove that this project inserts or uses them. Generic exponential synapses also do not by themselves establish receptor-specific AMPA, NMDA, GABA, glycine, or NK1 biology.

## 2. Full project inventory

### 2.1 Extension inventory

| Requested class | Count | Finding |
|---|---:|---|
| `.hoc` | 0 | No morphology loader, cell template, section assignment, insertion, protocol, or run-control HOC |
| `.py` | 0 | No Python cell builder, parameter loader, simulation, feature extraction, optimization, or plotting script |
| `.mod` | 0 | No project-local density mechanism or point-process source |
| `.json` | 1 | Future interneuron selection metadata; no L796 biophysical parameters |
| `.csv` | 1 | Ranked future interneuron candidates; no L796 conductance or validation table |
| Report/validation files | 1 Markdown report | Interneuron morphology-search report, not L796 electrophysiological validation |
| Morphologies | 3 SWCs | Future GRP-expressing excitatory-interneuron candidates |

### 2.2 All six files

| Relative path | Role | Relevance to this audit |
|---|---|---|
| `L796/interneurons/01_interneuron_search_report.md` | Candidate-selection report | Supports future interneuron identity/morphology selection; contains no NEURON mechanisms |
| `L796/interneurons/selected_interneuron_metadata.json` | Rank-1 candidate metadata | Selects `14-1-15-A-A2sep`, a mouse GRP-expressing excitatory interneuron |
| `L796/interneurons/top10_excitatory_interneuron_candidates.csv` | Candidate ranking | All listed top candidates are GRP-expressing excitatory dorsal-horn interneurons |
| `L796/interneurons/morphologies/01_14-1-15-A-A2sep.CNG.swc` | Rank-1 morphology | Morphology only; no membrane biophysics |
| `L796/interneurons/morphologies/02_26-11-14-A-A4b.CNG.swc` | Rank-2 morphology | Morphology only; no membrane biophysics |
| `L796/interneurons/morphologies/03_19-3-15-A.CNG.swc` | Rank-3 morphology | Morphology only; no membrane biophysics |

No L796-ALT-PN SWC is present in this checkout either, although the exact standardized morphology is available from NeuroMorpho.

## 3. Exact current-mechanism audit

### 3.1 Required A–D classification

| Class | Confirmed mechanisms | Evidence |
|---|---|---|
| A. Inserted into membrane sections | **None demonstrated** | No `.hoc` or `.py` cell-building code |
| B. Compiled/available but not inserted | **None demonstrated** | No `.mod`, `nrnmech.dll`, `libnrnmech.so`, or build manifest |
| C. Point processes/synapses | **None demonstrated** | No synapse construction or `NetCon` code |
| D. Loaded but unused | **None demonstrated** | No mechanism loader or simulation script |

This table does not assert that a separate copy of the model has no mechanisms. It states that the supplied project folder contains no evidence from which those classes can be determined.

### 3.2 Inserted-mechanism detail

There are zero confirmed inserted channels/receptors. Consequently, the requested fields have the following audit result:

| Mechanism | Ion/current | Location | Conductance/density | Reversal | Insertion file/line | Behaviour |
|---|---|---|---|---|---|---|
| No confirmed inserted mechanism | Not auditable | Not auditable | Not auditable | Not auditable | N/A—no insertion source exists | Not auditable |

## 4. Mechanism audit by biological class

### A. Passive mechanisms

No `pas` insertion, `g_pas`, `e_pas`, `Ra`, or `cm` assignment is present. Passive behaviour is therefore not auditable.

When the model code is restored, record section-specific `Ra`, `cm`, `g_pas`, and `e_pas`, including any soma/dendrite/axon differences. Passive parameters must first reproduce resting membrane potential, input resistance, and membrane time constant under the same temperature, ionic conditions, and current-pulse protocol used for the comparison data.

### B. Voltage-gated active channels

No fast Na, persistent Na, delayed rectifier K, A-type K, CaL, CaT, KCa, SK, BK, HCN/Ih, or KCNQ/M mechanism is present in the checkout.

The minimal defensible active set for a spiking model is fast Na + delayed-rectifier K, with axon/AIS enrichment tested because dorsal-horn neurons rely strongly on axonal/initial-segment Na current for spike generation ([Safronov et al. 1997](https://pmc.ncbi.nlm.nih.gov/articles/PMC1159869/)). A-type K has direct lamina I projection-neuron support for delayed/gap behaviour, but should be added only if that behaviour is an intended target ([Ruscheweyh et al. 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC1664848/)).

### C. Calcium dynamics

No calcium channel, `USEION ca` mechanism, intracellular calcium pool/buffer/pump, or calcium-dependent K mechanism is present.

Calcium dynamics should not be added merely because a calcium channel is biologically plausible. Add a minimal calcium state only when required by one of these targets:

- low-threshold/rebound or burst behaviour;
- AP falling-phase hump or width that needs CaT support;
- AHP/adaptation that needs SK/BK coupling;
- activity-dependent intracellular calcium;
- a calcium-dependent plasticity/release experiment.

AP-evoked calcium transients have been measured in lamina I neurons, with somatic/dendritic signals peaking after AP firing and decaying on a much slower timescale than the spike ([Harding et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7275865/)). This supports calcium as a measurable future validation target, not as an automatic baseline mechanism.

### D. Ligand-gated and synaptic receptors

No synapse or receptor point process is present.

AMPA and NMDA have strong direct relevance to excitation of lamina I projection neurons. AMPA/kainate-mediated miniature EPSCs have been recorded in identified lamina I projection neurons ([Dahlhaus et al. 2005](https://pmc.ncbi.nlm.nih.gov/articles/PMC1464766/)); AMPA and NMDA components are present at primary-afferent synapses onto lamina I/NK1R-positive neurons ([Tong et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4131007/)).

Glycine and GABA_A both matter, but they are not interchangeable. Adult rat lamina I neurons expressed both receptor classes, while fast miniature inhibition was predominantly glycinergic and GABA_A contributions could be slower/extrasynaptic ([Chéry & De Koninck 1999](https://pmc.ncbi.nlm.nih.gov/articles/PMC6782499/)). Identified projection neurons receive both glycinergic and GABAergic feed-forward inhibition ([Li et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4323529/)).

GABA_B and NK1 are metabotropic, not simple ligand-gated conductances. GABA_B can act postsynaptically through GIRK and presynaptically by reducing transmitter release ([Li & Baccei 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6053268/)). NK1/TACR1 activation by Substance P is slow neuromodulation; a projection-neuron study links SP/NK1 activation to NALCN-dependent inward current ([Ford et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6095712/)). Neither should be represented as an ordinary fast `Exp2Syn` without an explicit phenomenological justification.

## 5. Requested presence/absence matrix

In this table, “missing” means missing from the scanned project checkout.

| Requested mechanism | Biological class | Current status | Audit interpretation |
|---|---|---|---|
| Fast Na+ | Voltage-gated | Missing/not demonstrated | Essential for regenerative spikes; location and density unknown |
| Persistent Na+ | Voltage-gated | Missing/not demonstrated | Conditional for plateau, spontaneous, or sustained firing |
| Delayed rectifier K+ | Voltage-gated | Missing/not demonstrated | Essential for repolarization and repetitive firing |
| A-type K+ | Voltage-gated | Missing/not demonstrated | Strongly conditional on delayed/gap firing |
| CaL | Voltage-gated Ca | Missing/not demonstrated | Do not add without plateau/burst/Ca target |
| CaT | Voltage-gated Ca | Missing/not demonstrated | Conditional on low-threshold, rebound, burst, or AP-hump target |
| Generic KCa | Ca-activated K | Missing/not demonstrated | Prefer a named SK or BK mechanism tied to a measured AHP feature |
| SK-type KCa | Ca-activated K | Missing/not demonstrated | Conditional on medium AHP/adaptation/burst termination |
| BK-type KCa | Ca-activated K | Missing/not demonstrated | Conditional on fast AHP/spike repolarization/width |
| HCN/Ih | Hyperpolarization activated | Missing/not demonstrated | Add only if sag/rebound is measured and underfit |
| M-current/KCNQ | Voltage-gated K | Missing/not demonstrated | Add only if slow adaptation/phasic control is measured and underfit |
| Leak/passive | Passive | Missing/not demonstrated | Required before active fitting |
| Intracellular Ca dynamics | State/dynamics | Missing/not demonstrated | Required only when Ca-dependent mechanisms/features are modeled |
| AMPA | Ionotropic synapse | Missing/not demonstrated | Essential first excitatory receptor for circuit coupling |
| NMDA | Ionotropic synapse | Missing/not demonstrated | Strong for temporal integration/plasticity; requires Mg block |
| NK1/Substance P receptor | Metabotropic receptor | Missing/not demonstrated | Conditional on postsynaptic TACR1/NK1 evidence and slow-response target |
| GABA_A | Ionotropic synapse | Missing/not demonstrated | Useful/strong for fast inhibitory circuit experiments |
| GABA_B | Metabotropic receptor | Missing/not demonstrated | Optional for slow postsynaptic/presynaptic modulation |
| Glycine | Ionotropic synapse | Missing/not demonstrated | Strong for lamina I fast inhibition |

## 6. Voltage-gated channel classification

Because the model code is absent, the “already present” class is empty.

| Classification | Mechanisms | Decision rule |
|---|---|---|
| Already present | None confirmed | Reclassify only after tracing actual insertion code |
| Strongly recommended | Fast Na; delayed-rectifier K; A-type K **only for delayed/gap target** | Each maps to spike generation, repolarization, or directly observed delay/gap behaviour |
| Optional | Persistent Na; CaT; SK; BK | Add only for plateau/sustained firing, rebound/burst/AP hump, medium AHP/adaptation, or fast AHP/spike width |
| Not recommended unless literature and data support it | CaL; HCN/Ih; KCNQ/M; unspecified generic KCa | No exact-L796 requirement has been demonstrated; each adds identifiability burden |

Fast Na and delayed-rectifier K are “strongly recommended,” rather than “already present,” solely because the current checkout cannot establish implementation status.

## 7. Ligand-gated and neuromodulatory receptor audit

| Receptor | Present? | Project-local MOD/compiled support? | Recommended representation | Main validation |
|---|---|---|---|---|
| AMPA | No evidence | None found | Conductance point process with fast kinetics and calibrated reversal | EPSC/EPSP amplitude, kinetics, I–V, summation |
| NMDA | No evidence | None found | Voltage- and Mg-dependent conductance, not a plain exponential synapse | Slow EPSC/EPSP component, I–V, temporal integration |
| NK1/TACR1 | No evidence | None found | Slow GPCR/phenomenological pathway; possibly NALCN/GIRK modulation | SP-evoked slow current/depolarization and excitability change |
| GABA_A | No evidence | None found | Chloride conductance with age/condition-appropriate `E_GABA` and kinetics | IPSC/IPSP amplitude, decay, reversal |
| GABA_B | No evidence | None found | GIRK-mediated slow postsynaptic effect and/or presynaptic release modulation | Baclofen-like slow outward current and/or reduced event frequency |
| Glycine | No evidence | None found | Chloride conductance with receptor-specific fast kinetics | IPSC/IPSP amplitude, fast decay, reversal |

For neuropathic-pain simulations, chloride reversal must be an explicit assumption. Changing inhibition by weight alone can be misleading if injury-dependent chloride homeostasis is part of the hypothesis.

## 8. L796 feature-validation status

No simulation or validation output exists in the checkout, so none of the listed model features is currently validated here.

| Feature | Current validation status | Evidence/target boundary | Required plot or calculation |
|---|---|---|---|
| Resting membrane potential | Not auditable | Same-dataset PN group: −72.8 ± 0.9 mV; tonic PN group: −72.6 ± 1.1 mV; not exact-cell values | Baseline voltage over ≥1 s with no current |
| Input resistance | Not auditable | Same-dataset PN group: 0.77 ± 0.05 GΩ; measured with 500 ms, −10 to −20 pA pulses | Steady-state ΔV/ΔI and I–V line |
| Membrane time constant | Not auditable | No exact-L796 value established | Exponential fit to small hyperpolarizing response |
| Rheobase | Not auditable | Must be protocol-defined; broader studies define minimum current eliciting an AP | Fine current-step search |
| AP threshold | Not auditable | Broader identified PN comparator only; do not call it exact L796 | dV/dt threshold and phase plot |
| AP amplitude | Not auditable | No local trace | Threshold-relative and baseline-relative amplitude |
| AP overshoot | Not auditable | No local trace | Peak voltage above 0 mV |
| AP half-width | Not auditable | Identified PN studies support broad cell-type variation | Half-height width |
| AHP depth | Not auditable | No local trace | Minimum voltage after single AP and train |
| Firing frequency | Not auditable | Same-dataset PNs include tonic, gap, burst, unclassified classes | f–I curve and spike-count heatmap |
| Adaptation ratio | Not auditable | No exact target | Last/first or last-three/first-three ISI ratio, definition stated |
| Sag/rebound | Not auditable | Validation gate for Ih; not a reason by itself to add Ih | Negative current-step family, sag ratio, rebound spike count |
| Delay to first spike | Not auditable | Validation gate for A-type K; gap/delay is holding-potential dependent | First-spike latency vs current and pre-pulse voltage |
| Synaptic EPSP/IPSP amplitudes | Not auditable | Receptor-specific direct literature exists, but project has no synapses | Single-event amplitude/kinetics and weight-response curves |

The L796 identity and morphology do not supply exact conductance densities. Publication-safe language is: **the model is feature-tuned against identified lamina I projection-neuron data**, not reconstructed from cell-specific ion-channel measurements.

## 9. Future excitatory interneuron

### 9.1 Identity caveat

The selected morphology `14-1-15-A-A2sep` is a **mouse GRP-expressing excitatory interneuron**, not a Tac1/Substance-P-labelled neuron. The source study reports that SP cells tended to be radial and delayed-firing, whereas most GRP cells were transient- or single-spiking ([Dickie et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6330098/)).

Consequences:

- Do not assign Tac1/SP release to this GRP morphology by default.
- Do not choose an A-current merely because SP cells can be delayed-firing; first choose whether the future model represents the selected GRP phenotype or a separate Tac1/SP phenotype.
- If a Tac1/SP interneuron is required, use Tac1/SP-specific morphology and electrophysiology where possible, or explicitly label the model as a phenotype–morphology composite.

### 9.2 Minimal firing-type-dependent channel set

| Intended interneuron phenotype | Minimal set | Conditional additions | Avoid initially |
|---|---|---|---|
| GRP-like transient/single-spike | Leak + fast Na + delayed-rectifier K | A slow outward current only if required to terminate firing; receptor outputs | CaL, Ih, M, KCa without failed-feature evidence |
| Tac1/SP radial delayed-firing | Leak + fast Na + delayed-rectifier K + tested A-type K | CaT only if rebound/low-threshold or AP-hump data demand it | Automatic CaL/persistent-Na pacemaker set |
| Tonic excitatory interneuron | Leak + fast Na + delayed-rectifier K | Persistent Na, M, or SK only if f–I/adaptation targets require them | Burst mechanisms without a burst target |
| Bursting/low-threshold phenotype | Leak + fast Na + delayed-rectifier K | CaT, possibly persistent Na/Ca and calcium dynamics; KCa for termination | Generic “all calcium channels” approach |

### 9.3 Output to L796

- Model glutamatergic transmission by placing AMPA, then NMDA, receptors on L796 and driving them from interneuron spikes.
- Tac1 encodes the precursor for Substance P; it is not an ion channel.
- Substance P release is a presynaptic signal. NK1/TACR1 is the postsynaptic receptor target.
- Add a Tac1/SP output pathway only for a verified SP-releasing interneuron and a verified/assumed TACR1-positive postsynaptic target.
- Dense-core peptide release is commonly more frequency dependent and slower than single-vesicle glutamate release; it should not share AMPA kinetics or a single unexamined weight.

## 10. Neuropathic-pain priority table

Scores follow the requested scale: 10 essential; 8–9 strongly recommended; 5–7 optional/useful; 1–4 low priority unless specific evidence supports it.

| Channel/receptor | Biological role | Why it matters | Evidence needed | Current project status | Score | Difficulty | Validation feature |
|---|---|---|---|---|---:|---|---|
| Leak/passive | RMP, input resistance, time constant | Foundation for both cells and all synaptic integration | Same-preparation passive ephys + morphology fit | Missing/not demonstrated | 10 | Low–medium | RMP, Rin, tau, subthreshold I–V |
| Fast Na+ | AP initiation/propagation | Required for spikes; AIS/axon placement strongly plausible | AP waveform + dorsal-horn/AIS evidence + tested MOD | Missing/not demonstrated | 10 | Medium | Threshold, dV/dt, amplitude, overshoot |
| Delayed-rectifier K+ | AP repolarization/repetitive firing | Required for stable trains and spike width | AP/f–I ephys + tested MOD | Missing/not demonstrated | 10 | Medium | Half-width, repolarization, f–I |
| A-type K+ | First-spike delay/gap | Directly maps to delayed/gap firing in lamina I; relevant to SP radial phenotype | Holding-potential-dependent delay + 4-AP/A-current evidence | Missing/not demonstrated | 8 | Medium | First-spike latency, first ISI, pre-pulse dependence |
| Persistent Na+ | Subthreshold amplification/plateau/sustained firing | Can support tonic or spontaneous firing but risks hyperexcitability | Ramp/PIC or riluzole-sensitive evidence + fitted feature | Missing/not demonstrated | 6 | Medium–high | Rheobase, plateau, f–I, spontaneous firing |
| CaT | Low-threshold current, rebound, burst, AP hump | Supported in subsets of lamina I PNs; phenotype dependent | Voltage-clamp or rebound/burst/AP-hump evidence | Missing/not demonstrated | 6 | High | Rebound, burst threshold, AP width/hump |
| CaL | High-threshold Ca influx/plateau | Useful only if sustained Ca/plateau or burst feature demands it | Pharmacology/Ca imaging + failed simpler model | Missing/not demonstrated | 3 | High | Plateau duration, Ca transient, burst |
| Generic KCa | Ca-dependent outward current | Unspecified KCa obscures mechanism identity | AHP pharmacology and named channel evidence | Missing/not demonstrated | 2 | High | AHP and adaptation |
| SK-type KCa | Medium AHP/adaptation/burst termination | Could correct AHP/adaptation after Ca is modeled | Apamin-sensitive AHP or strong cell-type evidence | Missing/not demonstrated | 5 | High | mAHP, adaptation ratio, burst termination |
| BK-type KCa | Fast AHP/spike repolarization | Could correct broad spikes/fast AHP | BK-blocker-sensitive waveform evidence | Missing/not demonstrated | 5 | High | fAHP, half-width, max firing rate |
| HCN/Ih | Sag/rebound/resting conductance | Only useful if measured sag/rebound is underfit | Sag and ZD7288/HCN evidence in target phenotype | Missing/not demonstrated | 3 | Medium | Sag ratio, rebound, Rin |
| M-current/KCNQ | Slow adaptation/phasic control | Only useful if slow adaptation cannot be matched otherwise | XE991/retigabine evidence or strong target feature | Missing/not demonstrated | 3 | Medium | Adaptation, rheobase, long-pulse firing |
| Intracellular Ca dynamics | Couples Ca entry to concentration-dependent mechanisms | Needed for SK/BK, Ca traces, peptide/plasticity mechanisms | Ca transient kinetics and buffering assumptions | Missing/not demonstrated | 5 | High | Peak/decay of [Ca]i, AHP coupling |
| AMPA | Fast glutamatergic excitation | First receptor for excitatory interneuron → L796 coupling | EPSC/EPSP kinetics, reversal, connection strength | Missing/not demonstrated | 10 | Medium | EPSC/EPSP amplitude and decay |
| NMDA | Slow voltage-dependent excitation/integration | Important for strong/polysynaptic nociceptive drive and plasticity | NMDA component, Mg dependence, temporal integration | Missing/not demonstrated | 8 | High | I–V, slow EPSP, summation/plateau |
| NK1/TACR1 | Slow Substance-P neuromodulation | Pain-relevant only if postsynaptic TACR1/NK1 is supported | TACR1/NK1 or SP-response evidence + slow-current data | Missing/not demonstrated | 7 | High | SP-evoked current/depolarization, excitability |
| GABA_A | Fast/tonic chloride inhibition | Needed for inhibitory gating experiments | IPSC kinetics/reversal and chloride assumptions | Missing/not demonstrated | 7 | Medium | IPSC/IPSP amplitude, decay, Erev |
| GABA_B | Slow GIRK and presynaptic inhibition | Relevant to slow modulation, not minimal first-pass circuit | Baclofen-sensitive post- or presynaptic effect | Missing/not demonstrated | 5 | High | Slow outward current/event-frequency reduction |
| Glycine | Fast chloride inhibition | Strong direct relevance to lamina I fast inhibition | GlyR IPSC kinetics/reversal and connection data | Missing/not demonstrated | 8 | Medium | Fast IPSC/IPSP, Erev |
| Tac1/Substance P output | Neuropeptide release signal, not a channel | Conditional output for a verified Tac1/SP excitatory interneuron | Presynaptic Tac1/SP identity + postsynaptic TACR1 response | Selected morphology is GRP, not Tac1 | 7 | High | Frequency-dependent slow SP effect |

## 11. Validation plots and scripts before and after each addition

These are scripts to create after the actual model package is restored; none currently exists.

### 11.1 Baseline scripts that must run before any new channel

1. **`validate_passive`**
   - zero-current RMP;
   - −10 and −20 pA, 500 ms pulses;
   - Rin from steady-state ΔV/ΔI;
   - tau from exponential fit;
   - subthreshold I–V curve.
2. **`validate_active_steps`**
   - 500 ms current-step family from subthreshold through suprathreshold;
   - rheobase search;
   - voltage traces, f–I, spike count, first-spike latency, ISI sequence;
   - threshold, amplitude, overshoot, half-width, AHP;
   - adaptation ratio with the exact formula recorded.
3. **`validate_numerics`**
   - timestep/convergence comparison;
   - temperature and ion concentrations printed;
   - section counts, area, `nseg`, and all mechanism parameters exported.

### 11.2 Mechanism-specific before/after tests

| Proposed addition | Required pre-addition failure | Before/after plots |
|---|---|---|
| Fast Na/AIS refinement | AP threshold, dV/dt, amplitude, or propagation wrong | Phase plot; soma/AIS/axon voltage overlay; threshold and peak |
| Delayed-rectifier K refinement | Repolarization, half-width, max firing, or depolarization block wrong | AP overlay; K current; f–I; depolarization-block boundary |
| A-type K | Missing delayed/gap behaviour that is an explicit target | First-spike latency vs current; first ISI; hyperpolarizing pre-pulse dependence; A-current voltage-clamp family |
| Persistent Na | Rheobase too high or plateau/sustained firing absent despite correct passive/core channels | Slow voltage ramp; subthreshold I–V; f–I; plateau duration; spontaneous activity |
| CaT | Rebound/burst/AP hump target underfit | Hyperpolarizing pre-pulse then release; low-threshold voltage steps; AP falling phase |
| CaL | Measured high-threshold Ca/plateau target underfit | Long depolarizing steps; Ca current; voltage and [Ca]i |
| SK | Medium AHP/adaptation/burst termination underfit | Single-AP and train AHP; ISI adaptation; [Ca]i–SK current overlay |
| BK | Spike too broad or fast AHP underfit | AP half-width/fAHP; BK current; high-frequency train |
| Ih | Measured sag/rebound underfit | Negative-step family; sag ratio vs voltage; rebound latency/spikes |
| M/KCNQ | Measured slow adaptation/phasic firing underfit | Long-step firing; instantaneous frequency; M-current deactivation |
| AMPA | Circuit requires fast excitation | EPSC/EPSP weight curves; kinetics; I–V/reversal; summation |
| NMDA | Slow integration/plasticity target underfit by AMPA | AMPA-only vs AMPA+NMDA; Mg-dependent I–V; train summation |
| Glycine/GABA_A | Inhibitory gating experiment specified | Isolated receptor traces; reversal; conductance; excitation–inhibition timing |
| GABA_B | Slow or presynaptic inhibitory modulation specified | Slow GIRK current; membrane resistance; release/event frequency |
| NK1/SP | Verified Tac1→TACR1 experiment specified | SP pulse/train vs slow current, RMP, rheobase, f–I; recovery time |

Every addition should be evaluated by parameter freezing: first save the full pre-addition feature vector, then add one mechanism, fit only a minimal parameter subset, and re-run all passive and active tests to detect regressions.

## 12. Final recommendation

### Keep

- Keep the exact L796-ALT-PN identity separate from the sibling L796-LCN.
- Keep the three interneuron morphologies and candidate metadata as morphology-selection assets.
- Keep the rank-1 cell labelled as GRP-expressing unless stronger cell-specific evidence changes that annotation.
- Once the actual model is supplied, keep only existing mechanisms that survive a file/line trace and reproduce a named feature without destabilizing previously validated features.

### Add first

After restoring the model package:

1. passive/leak parameters and passive validation;
2. fast Na with explicit soma/AIS/axon placement;
3. delayed-rectifier K;
4. a complete baseline active-feature validation suite;
5. AMPA for the first excitatory interneuron→L796 circuit experiment.

### Add later, conditionally

- A-type K for an explicit delayed/gap L796 or Tac1/SP radial-interneuron phenotype.
- NMDA after AMPA-only synaptic validation, when slow integration or plasticity is required.
- Glycine and GABA_A when inhibitory gating is part of the circuit experiment.
- Persistent Na, CaT, SK, or BK only when a specific plateau, rebound/burst/AP-hump, AHP, adaptation, or width feature fails.
- NK1/TACR1 and Tac1/SP release only after confirming presynaptic Tac1/SP identity and postsynaptic receptor/response.
- GABA_B for a defined slow or presynaptic modulatory experiment.

### Do not add now

- CaL, Ih, M-current, generic KCa, or a broad calcium-handling stack without a failed measurable feature.
- Tac1/SP output to the selected GRP morphology by assumption.
- Receptor mechanisms solely because transcripts are reported.
- Multiple overlapping mechanisms in one fitting round.
- A generic exponential synapse relabelled as NMDA, GABA_B, or NK1 without reproducing the defining voltage dependence or slow signaling.

## 13. Reproducibility checklist

| Item | Present in scanned checkout? | Action |
|---|---|---|
| L796-ALT-PN SWC | No | Restore/download exact NMO_34019 morphology and record checksum |
| L796 cell/template code | No | Restore `.hoc`/`.py` sources |
| MOD sources | No | Restore all `.mod` files and mechanism provenance |
| Compiled mechanism library | No | Rebuild from source; do not rely on opaque binary only |
| L796 parameter JSON/CSV | No | Restore/export parameters with units and section scope |
| Simulation protocols | No | Create passive, active, synaptic, and numerical-validation scripts |
| L796 validation features/traces | No | Save raw traces, extracted feature table, plots, and protocol metadata |
| Future interneuron morphologies | Yes, three | Preserve provenance and phenotype caveat |
| Future interneuron metadata | Yes | Keep GRP annotation distinct from Tac1/SP |
| Temperature/ionic conditions | No | Make explicit in every run |
| Random seeds/synapse placement | No | Record when network/synaptic simulations begin |

## 14. References

1. [NeuroMorpho: L796-ALT-PN exact cell record](https://neuromorpho.org/neuron_info.jsp?neuron_name=L796-ALT-PN)
2. [Luz, Szucs & Safronov 2014: identified lamina I local-circuit and projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC3979609/)
3. [Ruscheweyh et al. 2004: membrane/discharge properties and A-current in lamina I projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC1664848/)
4. [Prescott & De Koninck 2002: firing classes of adult rat lamina I neurons](https://pubmed.ncbi.nlm.nih.gov/11897852/)
5. [Safronov, Wolff & Vogel 1997: Na-channel distribution and axonal spike initiation](https://pmc.ncbi.nlm.nih.gov/articles/PMC1159869/)
6. [Dahlhaus et al. 2005: synaptic input to identified lamina I projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC1464766/)
7. [Tong et al. 2014: AMPA/NMDA components at lamina I synapses](https://pmc.ncbi.nlm.nih.gov/articles/PMC4131007/)
8. [Chéry & De Koninck 1999: glycine and GABA_A IPSCs in lamina I](https://pmc.ncbi.nlm.nih.gov/articles/PMC6782499/)
9. [Li et al. 2015: glycinergic and GABAergic inhibition of projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC4323529/)
10. [Li & Baccei 2018: GABA_B signaling in adult spinal projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC6053268/)
11. [Ford et al. 2018: SP/NK1 activation of NALCN in spinal projection neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC6095712/)
12. [Harding et al. 2020: AP-evoked calcium responses in lamina I neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC7275865/)
13. [Dickie et al. 2019: SP versus GRP excitatory interneuron morphology and firing](https://pmc.ncbi.nlm.nih.gov/articles/PMC6330098/)
14. [Luz et al. 2019: NMDA-dependent signal processing in lamina I spino-parabrachial neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC6917718/)
