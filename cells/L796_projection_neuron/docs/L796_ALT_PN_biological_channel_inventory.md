# Biological ion-channel and receptor inventory for L796-ALT-PN

**Date:** 2026-07-09  
**Cell:** L796-ALT-PN (NeuroMorpho NMO_34019), young Wistar rat, lumbar spinal cord lamina I, anterolateral-tract projection neuron  
**Purpose:** decide which mechanisms are biologically defensible and which electrophysiological measurements must constrain them  
**Scope:** evidence and recommendations only; no model code was changed

## Bottom line

There is no published patch-seq, single-cell RNA-seq, voltage-clamp channel panel, or conductance-density map for the exact reconstructed L796 cell. Its morphology and projection-neuron identity are direct evidence; its channel complement must be inferred from identified rat lamina-I projection neurons, then tested against the intended L796 firing phenotype.

The biologically defensible starting model is:

1. passive leak, membrane capacitance, and axial resistance;
2. a fast transient Na current concentrated in the axon initial segment/axon, with lower somatodendritic density;
3. a delayed-rectifier K current for repolarization and repetitive firing;
4. AMPA and NMDA excitation;
5. GABA_A and glycine inhibition with an explicit chloride reversal or KCC2-dependent chloride state;
6. NK1/TACR1 signaling if L796 is assumed or experimentally shown to be NK1-positive.

A-type K, T-type Ca, HCN, persistent Na, high-voltage-activated Ca, SK/BK, M current, NALCN, GIRK, and intracellular Ca handling are **not all default requirements**. Each should be added only when a named measurement requires it.

## 1. What is known about the exact cell

NeuroMorpho identifies L796-ALT-PN as NMO_34019: a P14-P21 Wistar rat lumbar lamina-I principal/projection neuron, anterolateral-targeting, with soma, dendrites, and axon reconstructed. The same archive also contains a different cell named L796-LCN; it must not be conflated with L796-ALT-PN.

Direct source: [NeuroMorpho: L796-ALT-PN](https://neuromorpho.org/neuron_info.jsp?neuron_name=L796-ALT-PN).

The source experiment did not publish an L796-specific molecular profile or a full voltage-clamp decomposition of its currents. Consequently, statements below use four evidence levels:

| Grade | Meaning | Permitted conclusion |
|---|---|---|
| A | Exact L796 cell | Identity, morphology, age, region, projection class |
| B | Retrogradely identified rat lamina-I projection neurons | Strongest functional evidence for a mechanism class |
| C | Rat/mouse lamina-I neurons or mouse spinal projection-neuron transcriptomics | Plausible population evidence; not proof for L796 |
| D | Broader dorsal-horn or other-neuron evidence | Hypothesis only |

## 2. Basis of the priority ranking

The score is an implementation priority, not an expression score.

| Points | Criterion |
|---:|---|
| 0-3 | Required to reproduce a core measurable feature: resting/passive behavior, action potentials, or a defined synaptic input |
| 0-2 | Demonstrated in identified rat lamina-I projection neurons |
| 0-2 | Supported by pharmacology, voltage clamp, imaging, or anatomy rather than transcript alone |
| 0-2 | Directly relevant to neuropathic-pain circuit behavior |
| 0-1 | A validated NEURON mechanism and discriminating fitting protocol are practical |

Interpretation:

- **10:** essential to the intended model;
- **8-9:** strongly recommended;
- **5-7:** conditional or useful;
- **1-4:** do not add unless a specific target feature or new evidence supports it.

A transcript can raise a hypothesis, but cannot by itself earn the “demonstrated function” points. A mechanism also loses priority when its effect cannot be separated from another mechanism with the available recordings.

## 3. Voltage-gated and intrinsic mechanisms

| Mechanism | Likely molecular family | Evidence for an L796-like PN | Recommendation and score | Where to place initially | What must be fitted/validated |
|---|---|---|---|---|---|
| Passive leak | `pas`; molecular leak identity unresolved | A/B: passive physiology and complete morphology require it | **Essential, 10** | Soma, dendrites, AIS/axon; region-specific only if attenuation data demand it | Resting potential, input resistance, membrane time constant, subthreshold I-V, dendritic attenuation |
| Fast transient Na | Generic NaT; exact alpha subtype unresolved | B: axon/AIS-dominant fast Na current and spike initiation in rat dorsal-horn neurons | **Essential, 10** | Highest in AIS/axon; lower soma; dendrites only if backpropagation requires it | AP threshold, maximum dV/dt, amplitude, overshoot, AIS-before-soma timing, propagation |
| Delayed-rectifier K | Generic KDR; exact Kv family unresolved | Functional necessity for repolarization; no exact L796 subtype measurement | **Essential, 10** | AIS/axon and soma; dendritic density only if data require | AP half-width, repolarization slope, repetitive firing, depolarization block |
| A-type K | Kv4/Kv1-like current; subtype unresolved | B: gap/delayed firing in identified projection neurons has A-current properties | **Strongly recommended only for gap/delay phenotype, 8** | Soma/proximal dendrite first; AIS only if latency data require | First-spike latency, first interspike gap, holding-potential/prepulse dependence, 4-AP sensitivity |
| T-type Ca | CaV3 family | B/C: low-threshold Ca current underlies burst behavior in a PN subset; common but not universal in adult rat lamina-I neurons | **Conditional, 7** | Soma and dendrites | Low-threshold inward current, rebound, burst threshold, AP afterdepolarization, Ni/Z944 sensitivity |
| High-voltage-activated Ca | N-, L-, and possibly P/Q/R-type | B/C: T, N, and L currents were recorded in labelled rat spinothalamic/trigeminothalamic cells; AP-evoked Ca enters lamina-I somata and dendrites | **Conditional, 5** | Soma/dendrites; presynaptic Ca at modeled axon terminals | Ca current I-V, AP-evoked Ca transient, plateau/afterdepolarization, transmitter release |
| Intracellular Ca dynamics | Buffers, pumps, extrusion, optional stores | C: AP-evoked Ca transients invade lamina-I dendrites; ryanodine-sensitive stores amplify somatic/nuclear responses | **Add with Ca or KCa, 6** | Compartments containing Ca channels/KCa | Baseline Ca, decay time, peak transient, accumulation during trains |
| SK-type KCa | KCNN family | No direct L796 pharmacology found; general mechanism for medium AHP/adaptation | **Conditional, 5** | Soma/proximal dendrite coupled to Ca source | Apamin-sensitive AHP, adaptation ratio, post-train AHP |
| BK-type KCa | KCNMA1 family | No direct L796 pharmacology found; plausible fast repolarization/AHP mechanism | **Conditional, 4** | Soma/AIS coupled locally to Ca | Spike width, fast AHP, iberiotoxin/paxilline-sensitive component |
| Persistent Na | NaP; subtype unresolved | Broader lamina-I/developmental evidence, but not an exact L796 requirement | **Low priority unless plateau/tonic inward current is measured, 4** | Soma/AIS | Slow ramp hysteresis, TTX/riluzole-sensitive persistent current, rheobase, plateau |
| HCN/Ih | HCN1-4 | C: reported in subsets of mouse lamina-I spinobulbar neurons; no exact L796 sag measurement | **Do not add without sag/rebound, 4** | Dendrites and soma if required | Sag ratio, rebound amplitude/spikes, resonance, ZD7288 sensitivity |
| M current | KCNQ2-5 | No direct identified-L796 functional evidence found | **Low priority, 3** | AIS/soma only if supported | XE991-sensitive current, adaptation, near-threshold excitability |
| NALCN Na leak | NALCN | C: enhances neonatal spino-parabrachial PN excitability and carries part of NK1/SP inward current | **Conditional for explicit SP/NK1 signaling, 6** | Soma/dendrites | SP-evoked slow inward current, resting excitability, NALCN perturbation |
| GIRK | KCNJ3/5/6/9 family | C: downstream component of GABA_B and NK1 pathways in spinal PNs | **Conditional with metabotropic receptors, 4** | Soma/dendrites | Baclofen-evoked outward current, SP response under pathway blockers |

Primary evidence:

- Axon/AIS-dominant Na and spike initiation: [Safronov, Wolff & Vogel 1997](https://pmc.ncbi.nlm.nih.gov/articles/PMC1159869/).
- Gap firing/A-current and PN bursting/low-threshold Ca: [Ruscheweyh et al. 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC1664848/).
- Same-source population physiology for young rat lamina-I PNs: [Luz, Szucs & Safronov 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC3979609/).
- T, N, and L Ca currents in labelled rat ascending dorsal-horn neurons: [Murase & Randic 1989](https://pubmed.ncbi.nlm.nih.gov/2482353/).
- Low-voltage-activated Ca in 27/34 adult rat lamina-I neurons: [Harding et al. 2021](https://pubmed.ncbi.nlm.nih.gov/33871884/).
- AP-evoked somatic/dendritic Ca and intracellular-store amplification: [Harding et al. 2020](https://pubmed.ncbi.nlm.nih.gov/32341097/).
- NALCN and SP/NK1 signaling in spinal projection neurons: [Ford, Ren & Baccei 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6095712/).

## 4. Ligand-gated and metabotropic receptors

| Receptor/pathway | Current/signaling | Evidence for an L796-like PN | Recommendation and score | Validation target |
|---|---|---|---|---|
| AMPA | Fast glutamatergic cation current; reversal near 0 mV | B: AMPA/kainate mEPSCs and afferent-evoked EPSCs in identified rat lamina-I PNs | **Essential for excitatory input, 10** | mEPSC/eEPSC amplitude, rise/decay, paired-pulse behavior, EPSP amplitude |
| NMDA | Voltage-dependent glutamatergic Na/K/Ca current; Mg block | B/C: NMDA component in afferent-evoked EPSCs; GluN2B/GluN2D dominate adult rat lamina-I synaptic responses | **Strongly recommended, 9** | AMPA:NMDA ratio, I-V/Mg block, decay, temporal summation, wind-up |
| GABA_A | Fast Cl/HCO3 current | B: every tested identified rat lamina-I PN responded to GABA; GABAergic mIPSCs recorded | **Essential for inhibitory circuit model, 9** | IPSC amplitude/kinetics, E_GABA, shunting, IPSP at physiological chloride |
| Glycine receptor | Fast Cl current | B: every tested identified rat lamina-I PN responded to glycine; glycinergic mIPSCs recorded | **Essential for inhibitory circuit model, 9** | IPSC amplitude/kinetics, E_Gly, GABA:glycine contribution |
| NK1/TACR1 | GPCR activated by substance P; no single fixed reversal | B: about 80% of rat lamina-I PNs express NK1, but exact L796 status is unknown | **Strong conditional recommendation, 8** | NK1 immunostatus if possible; SP-evoked slow depolarization/current and firing increase |
| GABA_B | Metabotropic; postsynaptic GIRK and presynaptic release inhibition | C: functional signaling in identified adult spinal PNs, with injury-dependent plasticity | **Later/conditional, 5** | Baclofen-evoked outward current and suppression of glutamate release |
| Kainate receptor | Ionotropic glutamate current | AMPA/kainate components are difficult to separate in older PN recordings; cluster-level transcript evidence is not L796-specific | **Low priority as a separate mechanism, 3** | Residual CNQX-sensitive current after selective AMPA separation |
| P2X, 5-HT3, nicotinic ACh | Ionotropic modulatory inputs | No direct exact-L796 requirement established in this audit | **Do not add now, 1-3** | Only after a defined pathway and agonist/antagonist response are selected |

Primary evidence:

- AMPA/kainate, NMDA, GABA_A, and glycine responses in identified rat lamina-I projection neurons: [Dahlhaus et al. 2005](https://pmc.ncbi.nlm.nih.gov/articles/PMC1464766/).
- Adult rat lamina-I NMDAR subunits and slow synaptic amplification: [Hildebrand et al. 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC3923208/).
- Junctional/extrasynaptic GABA_A and glycine currents in adult rat lamina I: [Chéry & De Koninck 1999](https://pmc.ncbi.nlm.nih.gov/articles/PMC6782499/).
- NK1 in approximately 80% of rat lamina-I PNs and preferential substance-P afferent innervation: [Todd et al. 2002](https://pmc.ncbi.nlm.nih.gov/articles/PMC6757649/).
- GABA_B/GIRK signaling in identified adult spinal projection neurons: [Brewer & Baccei 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6053268/).

## 5. Chloride homeostasis is mandatory in a neuropathic-pain simulation

KCC2/SLC12A5 is a transporter, not a ligand-gated receptor. It nevertheless controls the reversal of GABA_A and glycine currents. Peripheral nerve injury reduces KCC2 in rat lamina-I neurons, shifts the anion gradient, and can make normally inhibitory responses less inhibitory or excitatory.

Therefore:

- do not validate GABA_A or glycine using an arbitrary fixed reversal alone;
- define normal and neuropathic chloride states;
- fit or constrain E_Cl/E_GABA/E_Gly from gramicidin-perforated-patch or published condition-matched data;
- test whether the same inhibitory synaptic conductance changes from hyperpolarizing/shunting toward depolarizing after KCC2 reduction.

Primary source: [Coull et al. 2003](https://pubmed.ncbi.nlm.nih.gov/12931188/).

Priority: **9/10 for a neuropathic-pain circuit model**, although it is not an ion channel.

## 6. What RNA-seq can and cannot tell us

No exact-cell RNA-seq was found for L796.

Two useful population resources exist:

1. Häring et al. used mouse dorsal-horn single-cell RNA-seq to define 15 excitatory and 15 inhibitory classes and associated projection neurons mainly with an excitatory Glut15 class. This supports molecular heterogeneity and supplies candidate genes, but it is mouse, cluster-level, and not a retrogradely identified rat L796 transcriptome.
2. Wercberger et al. used projection-neuron-centric retro-TRAP/RNA-seq and in-situ validation. The study supports strong molecular heterogeneity among spinal projection neurons and identifies populations involving `Tacr1`, `Cck`, `Nptx2`, `Nmb`, `Crh`, `Tac1`, `Lypd1`, and `Elavl4`. This does not imply that every L796-like neuron expresses all of them, and it does not yield membrane conductance densities.

Sources: [Häring et al. 2018](https://www.nature.com/articles/s41593-018-0141-1) and [Wercberger et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8285968/).

Use RNA-seq in this order:

1. identify a candidate molecular PN subtype;
2. verify the gene in retrogradely labelled, age/segment/species-matched neurons by RNAscope or immunohistochemistry;
3. demonstrate a corresponding current pharmacologically or by voltage clamp;
4. only then choose a kinetic mechanism and fit conductance.

Transcript abundance must not be converted directly into NEURON `gbar`.

## 7. What should actually be fitted

Do not fit every parameter simultaneously. Fit in stages and freeze each accepted stage before adding the next.

### Stage 1: morphology and passive membrane

Fit:

- specific membrane capacitance or an effective value accounting for spines;
- axial resistivity;
- leak conductance and reversal;
- any justified soma/dendrite regional difference.

Targets:

- resting membrane potential;
- input resistance;
- membrane time constant, preferably a multi-exponential fit;
- steady-state subthreshold I-V;
- voltage attenuation from dendrite to soma if data become available.

Same-dataset PN comparators from Luz et al. are group-level, not exact L796 values: resting potential approximately -72.8 ± 0.9 mV and input resistance approximately 0.77 ± 0.05 GOhm. Preserve that label in plots and tables.

### Stage 2: spike initiation and waveform

Fit NaT and KDR together, with AIS geometry/density treated explicitly.

Targets:

- rheobase;
- AP threshold;
- maximum dV/dt;
- AP amplitude and overshoot;
- half-width;
- fast AHP;
- axonal propagation and AIS-before-soma onset if recordings permit.

### Stage 3: repetitive firing

Targets:

- f-I curve across several current steps;
- spike count;
- first-spike latency;
- first and steady-state interspike intervals;
- adaptation ratio;
- AHP depth and decay;
- depolarization block.

Only then decide:

- add A-type K if delay/gap and prepulse dependence are missing;
- add SK if medium AHP/adaptation is missing;
- add BK if spike narrowing/fast AHP is missing;
- add NaP only if a measured persistent inward current, plateau, or hysteresis is missing.

### Stage 4: conditional Ca and Ih features

- Fit CaT only against low-threshold current, burst, rebound, or afterdepolarization.
- Fit HCN only against sag, rebound, and preferably resonance/ZD7288 data.
- Fit high-voltage Ca and Ca handling against measured Ca transients or voltage-clamp currents.
- Fit CaL only if a nimodipine-sensitive plateau/current is part of the target phenotype.

### Stage 5: synapses

Fit receptor kinetics before synaptic weight.

- AMPA: rise, decay, quantal amplitude, EPSP/EPSC.
- NMDA: voltage dependence, Mg block, decay, AMPA:NMDA ratio, temporal summation.
- GABA_A/glycine: separate kinetics and proportions; validate at physiological E_Cl.
- NK1: seconds-long SP response, not an `Exp2Syn`-like fast conductance.
- GABA_B: slow postsynaptic current and/or presynaptic release suppression.

## 8. Minimal validation experiment set

| Question | Protocol | Mechanisms constrained |
|---|---|---|
| Is passive structure correct? | Small hyperpolarizing/depolarizing steps | leak, Cm, Ra |
| Is spike initiation correct? | Near-rheobase steps plus phase-plane plot | NaT, KDR, AIS |
| Is repetitive firing correct? | 0.5-1 s current-step family | NaT, KDR, A-type, KCa, M, NaP |
| Is there an A current? | Hyperpolarized versus depolarized holding/prepulse | A-type K |
| Is there Ih? | Long hyperpolarizing steps; ZD7288 if experimental | HCN |
| Is there T current? | De-inactivation prepulse then low-voltage steps; Ni/Z944 | CaT |
| Is there HVA Ca? | Ca-current I-V and subtype blockers; Ca imaging | CaN/L/PQ/R and Ca handling |
| Is inhibition truly inhibitory? | Gramicidin E_GABA/E_Gly and conductance input | GABA_A, GlyR, KCC2 |
| Is SP/NK1 needed? | Substance P with NK1 antagonist; slow time scale | NK1, NALCN, GIRK |
| Is synaptic integration correct? | AMPA/NMDA and GABA/glycine pharmacological isolation | receptor kinetics and weights |

Use multi-objective fitting with held-out protocols. A channel is justified only if it improves its target feature without degrading already accepted passive, waveform, and firing targets.

## 9. Final implementation order

### Keep or establish first

- morphology;
- passive leak/Cm/Ra;
- fast transient Na with AIS emphasis;
- delayed-rectifier K;
- explicit temperature and ionic concentrations;
- AMPA, NMDA, GABA_A, and glycine for circuit simulations;
- explicit chloride/KCC2 state for neuropathic-pain comparisons.

### Add next if the target phenotype requires it

- A-type K for gap/delayed firing;
- CaT for low-threshold burst/rebound/afterdepolarization;
- NK1 plus an appropriate slow signaling/current model for Substance P responses.

### Add later

- HVA Ca plus intracellular Ca dynamics;
- SK or BK when AHP/adaptation/spike-width data require them;
- GABA_B/GIRK;
- NALCN as part of a validated NK1/SP response.

### Do not add now

- HCN without sag/rebound evidence;
- M current without an XE991-sensitive or equivalent target;
- persistent Na without a persistent inward-current/plateau target;
- separate kainate, P2X, 5-HT3, or nicotinic mechanisms without a defined afferent pathway and pharmacological feature;
- arbitrary ion-channel genes merely because they appear in a dorsal-horn RNA-seq cluster.

## 10. Evidence-safe conclusion

The closest-to-biology L796 model will not be the model with the largest channel list. It will be the smallest mechanism set that jointly reproduces passive properties, AIS-driven spike initiation, the chosen projection-neuron firing class, receptor-specific synaptic kinetics, and the normal-versus-neuropathic chloride state.

The most important unresolved biological decision is L796's intended firing phenotype. If its source recording is tonic-like, start with leak + NaT + KDR and test whether A-type K is needed for any initial gap. If the target trace shows true gap/delayed firing, A-type K becomes high priority. If it shows a low-threshold burst or afterdepolarization, CaT becomes high priority. Without those traces, adding both currents at large conductance would be overfitting rather than biological realism.
