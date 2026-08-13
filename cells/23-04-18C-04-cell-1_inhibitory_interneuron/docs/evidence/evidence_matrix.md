# Cell 1 evidence matrix

## Evidence hierarchy

| Code | Meaning | Application to this cell |
|---|---|---|
| SC | Same reconstructed cell | Morphology, PV reporter label, Pax2 label, lumbar lamina II-III location |
| SP | Same identified population | Mouse PV-lineage dorsal-horn electrophysiology |
| PL | Population level | Passive and active means/distributions; no trace is linked to NMO_170087 |
| AN | Anatomical analogue | Not required for the baseline Cell 1 targets |
| M | Medlock-derived | iPV mapping and later comparison only; no conductance is inherited blindly |
| F | Model-fitted | Leak conductance and active density values |
| A | Model-assumed | Axial resistivity, specific capacitance range, leak reversal interpretation, channel distribution |
| P | Model prediction | Exact-morphology outputs and all 35 C behavior |

The complete, machine-readable table is [evidence_matrix.csv](evidence_matrix.csv). The key scientific boundary is that the geometry and marker identity are same-cell evidence, whereas all electrophysiology is same-population and population-level.

## Primary sources

1. Gradwell MA et al. *Diversity of inhibitory and excitatory parvalbumin interneuron circuits in the dorsal horn.* Pain (2022). DOI: [10.1097/j.pain.0000000000002422](https://doi.org/10.1097/j.pain.0000000000002422); PMID: [34326298](https://pubmed.ncbi.nlm.nih.gov/34326298/); PMCID: [PMC8832545](https://pmc.ncbi.nlm.nih.gov/articles/PMC8832545/). Primary morphology/identity source and PV population firing evidence.
2. Gradwell MA et al. *Altered Intrinsic Properties and Inhibitory Connectivity in Aged Parvalbumin-Expressing Dorsal Horn Neurons.* Front Neural Circuits (2022). DOI: [10.3389/fncir.2022.834173](https://doi.org/10.3389/fncir.2022.834173); PMID: [35874431](https://pubmed.ncbi.nlm.nih.gov/35874431/); PMCID: [PMC9305305](https://pmc.ncbi.nlm.nih.gov/articles/PMC9305305/). Strongest quantitative adult PV passive/active population targets.
3. Ma et al. *Modulation of SK Channels via Calcium Buffering Tunes Intrinsic Excitability and Firing Properties of Spinal Dorsal Horn Neurons.* J Neurosci (2023). DOI: [10.1523/JNEUROSCI.0426-23.2023](https://doi.org/10.1523/JNEUROSCI.0426-23.2023); PMID: [37451982](https://pubmed.ncbi.nlm.nih.gov/37451982/); PMCID: [PMC10401647](https://pmc.ncbi.nlm.nih.gov/articles/PMC10401647/). Secondary same-population naive reference and SK perturbation evidence.
4. Gradwell MA et al. *Heteromeric alpha/beta glycine receptors regulate excitability in parvalbumin-expressing dorsal horn neurons.* J Physiol (2017). DOI: [10.1113/JP274926](https://doi.org/10.1113/JP274926); PMID: [28905384](https://pubmed.ncbi.nlm.nih.gov/28905384/); PMCID: [PMC5709328](https://pmc.ncbi.nlm.nih.gov/articles/PMC5709328/). Supporting PV physiology and Ih context, not a source of baseline intrinsic parameters for this exact reconstruction.

## Target selection before fitting

The passive fit will prioritize the adult PV population input resistance of **225 +/- 22 MOhm** at 21-24 C. The source does not report a membrane time constant or an unforced RMP. The reported **-60 mV** is an experimentally imposed current-clamp holding potential and must not be represented as a measured RMP.

The **10.9 +/- 0.6 pF** whole-cell capacitance is retained as a comparison, not an unconditional geometric-fit target. NeuroMorpho reports 7083.34 um2 surface; with 1 uF/cm2 that corresponds to about 70.8 pF before importer-dependent geometry differences. Equating an electrode-derived capacitance estimate to total reconstructed membrane capacitance would therefore require an unusually small specific capacitance. The fit will preserve a restrained specific-capacitance range and explicitly report whether the capacitance gate passes.

Ma et al.'s naive PV value of **-52.79 +/- 1.26 mV** is a secondary same-population cohort and will not be silently merged with the Gradwell adult target set. A baseline near -60 mV is used to reproduce the current-clamp condition; it is classified as model-assumed/fitted rather than an exact-cell measurement.
