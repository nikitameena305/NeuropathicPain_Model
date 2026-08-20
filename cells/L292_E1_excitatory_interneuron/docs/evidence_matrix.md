# Evidence matrix

Evidence classes requested for this build:

- **A:** exact L292-E1-specific evidence.
- **B:** rat dorsal-horn excitatory-interneuron evidence.
- **C:** Medlock model-derived.
- **D:** explicit assumption or new computational proposal requiring validation.
- **E:** unknown.

An empty measurement is retained as unknown; it is not replaced with a plausible-looking number.

## Identity layers

| Layer | Evidence | Class | Interpretation |
|---|---|---:|---|
| Rat morphology | L292-E1-LCN, NMO_34021; rat Wistar, lumbar spinal cord, lamina I, local-circuit multipolar interneuron; dendrites and axon listed complete | A | Confirmed morphology metadata, not transmitter identity |
| Morphology recording temperature | The source study states all recordings were at 22–24°C | A | Justifies a 23°C first model stage |
| Molecular identity of L292-E1-LCN | No cell-specific PKCgamma, VGLUT3, DOR, SST, CR, TrC, VGAT, or VGLUT2 result was found | E | Must remain unknown |
| eTrC / other population identity | Population names and cell rules from Medlock ModelDB 267056 | C | Computational identity only |
| Proximal 9-um initiation region | Medlock's 9-um hillock rule mapped to the reconstructed proximal axon by path distance | D | Candidate initiation zone, not a confirmed AIS |
| Distal axon physiology | Passive pending evidence and propagation validation | D/E | No invented distal channel distribution |

## Requested intrinsic and synaptic parameters

| Parameter | L292-E1-specific (A) | Rat excitatory evidence (B) | Medlock-derived (C) | Assumption / unknown | Working use |
|---|---|---|---|---|---|
| RMP | Not reported | Adult rat lamina-II excitatory cells: −64.1 ± 1.7 mV SEM; no liquid-junction correction | `e_pas=-65 mV`, but this is not a measured RMP; network `v_init=-60 mV` | Exact L292 RMP is E | B target band −69 to −59 mV; report protocol mismatch |
| Rin | Not reported | No transmitter-confirmed value suitable as an exact L292 target was found. Source-study LCN group mean 0.9 ± 0.1 GΩ mixes/does not identify this cell's transmitter phenotype | Not stated; must be measured from executed rule | Exact L292 and marker-specific Rin are E | Measure; do not force a fabricated target |
| Membrane tau | Not reported | Not found in the audited sources | Not stated | E | Measure only |
| Rheobase | Not reported | Not found as a population-specific numeric target in audited sources | Not stated; requires executing current steps | E until measured | Report with tested current resolution |
| AP threshold | Not reported | No directly comparable numeric target found | Not stated in released code/paper | E | Measure; no pass band yet |
| AP peak | Not reported | No directly comparable numeric target found | Paper gives spike height, not absolute peak | E | Measure |
| AP amplitude | Not reported | No directly comparable numeric target found | Delayed-neuron spike height 107 mV from starting voltage, compared by authors with 110 mV experimental | C | Compare without converting to an absolute peak |
| AP half-width | Not reported | No directly comparable numeric target found | Not stated in the audited paper/code | E | Measure only |
| AHP | Not reported | No directly comparable numeric target found | Not stated | E | Measure only |
| eTrC firing phenotype | Not reported | Transient firing occurs among rat excitatory dorsal-horn interneurons, but not assigned to L292-E1 | 1–2 spikes within 100 ms of current onset | C | Primary eTrC active gate |
| Delayed firing phenotype | Not reported | 18/22 rat excitatory lamina-II neurons showed delayed, gap, or reluctant patterns; patterns were holding-voltage dependent | First-spike latency decreases as injected current increases | B/C | Primary delayed-cell gate |
| Adaptation | Not reported | Not numerically reported for a matching population | Not numerically stated | E | Measure last/first ISI and retain definition |
| Active channels | Not reported | A-type current associated with delayed/gap/reluctant patterns; Kv4-containing channels implicated | eTrC: B_Na, borgka, KDRI, iKCa/Ca dynamics; delayed: same plus HH2, with exact densities in source JSON | Reconstructed-compartment mapping is D | Use exact rule values as starting values only |
| Channel distributions | Not reported | No L292-specific distribution | ModelDB soma/dendrite/hillock distributions | Mapping hillock to reconstructed proximal axon is D; distal axon is E | Validate spike initiation at three sites |
| Temperature | Source recordings 22–24°C | Yasaka recordings at room temperature | Paper says 37°C; executable cfg says 36°C | 35°C model is a future translation | Start 23°C; keep 36/37 conflict visible |
| Synaptic receptors | Not reported | Not L292-specific | AMPA, NMDA, NK1, GABA_A, glycine with exact released kinetics | Whether L292 bears each receptor is E | Population identity only |
| Connectivity | Not reported | Qualitative literature constraints underlie Medlock | Exact ModelDB rules, weights, probabilities and delays extracted | Reconstructed-cell synapse placement is D | Do not wire until single-cell gates pass |

## Primary sources audited

1. [Medlock et al. 2022 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8996343/) and [ModelDB 267056 source](https://github.com/ModelDBRepository/267056).
2. [NeuroMorpho L292-E1-LCN record](https://neuromorpho.org/neuron_info.jsp?neuron_name=L292-E1-LCN).
3. [Szucs et al. 2013 morphology-source paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC3738926/).
4. [Yasaka et al. 2010 rat excitatory/inhibitory interneuron study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3170912/).

## Explicit conflicts and limits

- Paper methods say 37°C; released `cfg_mechanical.py` executes at 36°C. Executed source is used when describing the released model, while the paper value is retained as a conflict.
- The source morphology is lamina I in young rats; Yasaka physiology is lamina II in adult rats. Yasaka values are class B context, not cell-specific truth.
- The morphology paper reports many tested LCNs were VGAT-positive, but does not identify L292-E1-LCN's molecular/transmitter status. The reconstruction is therefore not claimed to be excitatory or marker-confirmed.
- A 500-ms IClamp step is a project protocol choice for initial reconstruction tests. The Medlock paper states that somatic IClamp intensities were varied but does not provide an exact reusable current-step series in the released network configuration.
