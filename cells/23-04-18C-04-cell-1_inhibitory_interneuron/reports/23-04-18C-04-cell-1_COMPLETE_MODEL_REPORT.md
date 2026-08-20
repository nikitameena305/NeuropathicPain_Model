# Complete single-cell model report

## 23-04-18C-04-cell-1 / NMO_170087

**Species:** mouse  
**Region:** lumbar spinal dorsal horn  
**Lamina:** II-III  
**Known identity:** PV reporter positive, Pax2 positive, inhibitory interneuron  
**Medlock target:** iPV  
**Report date:** 2026-08-13  
**NEURON:** 9.0.1  
**Status:** ENGINEERING READY / BIOLOGICALLY PROVISIONAL; NOT READY FOR NETWORK INTEGRATION

## 1. Executive summary

NMO_170087 is a reconstructed mouse lumbar dorsal-horn interneuron with same-cell PV reporter and Pax2 labeling. It was selected as the strongest available real-morphology analogue for the Medlock iPV population. The geometry and marker identity are cell-specific; every electrophysiological target is from the genetically defined PV population and no trace is linked to this reconstruction.

Morphology QA passes structural checks, but NeuroMorpho grades dendrites moderate and the axon incomplete and flags `No Diameter`. The source SWC is preserved byte-for-byte. The NEURON model imports a separately checksummed copy that removes blank lines only.

The passive model reproduces adult PV input resistance (225.000 versus 225 +/- 22 MOhm) but does not reproduce the 10.9 +/- 0.6 pF whole-cell capacitance estimate within a restrained cm range. The active model uses the smallest tested channel set: leak, fast Na, and delayed-rectifier K. It reproduces a population-supported tonic phenotype and AP threshold but fails rheobase, AP amplitude, AP half-width, and AHP gates. Strong-current block, spatial sensitivity, sodium-density sensitivity, dependence on a model-defined proximal-axon region, and an unvalidated 35 C translation prevent network integration.

## 2. Biological identity

| Field | Evidence-backed statement | Classification |
|---|---|---|
| Cell | 23-04-18C-04-cell-1 / NMO_170087 | SC |
| Species | Mouse | SC archive metadata |
| Strain/reporter | Pvcre; Cre-dependent Brainbow labeling | SC/cohort context |
| Region | Lumbar spinal dorsal horn | SC |
| Lamina | II-III | SC |
| Marker | PV reporter positive | SC |
| Inhibitory marker | Pax2 positive | SC |
| Cell class | Inhibitory interneuron | SC inference strongly supported by Pax2 |
| Medlock mapping | iPV | M mapping, not biological identity |
| Exact-cell firing class | Unknown | Not measured/linked |

The phrase “PV+/Pax2+ inhibitory interneuron” is justified. The phrase “the exact cell is tonic” is not justified. Tonic firing is a population-level modeling target.

## 3. Morphology provenance

The standardized SWC was downloaded from NeuroMorpho on 2026-08-13 from the exact NMO_170087 record. Its SHA256 is `e2ecaffc1ebcf9c88b72224fa4172aa93dfb013edb3ad40ee2bfadebe06ec915`. The source paper is Gradwell et al., *Pain* 2022 (DOI 10.1097/j.pain.0000000000002422; PMID 34326298; PMCID PMC8832545).

The source used PVCre Brainbow labeling, sagittal 60-um sections, a 40x oil objective, and Neurolucida reconstruction. NeuroMorpho records all three domains, but dendrites are “Moderate” and axon “Incomplete.” The archive `No Diameter` flag creates additional uncertainty for cable properties.

The model copy checksum is `0e05613af9b747d3ca856d1b643c7c776d8207df2397637d302144834ea8c9f2`. Its sole transformation is removal of 15 blank lines. There are zero coordinate, topology, type, parent, or radius changes.

## 4. Morphology QA

| Metric | Result |
|---|---:|
| Nodes | 2,897 |
| Soma / dendrite / axon nodes | 9 / 2,240 / 648 |
| Roots / components | 1 / 1 |
| Orphans | 0 |
| Duplicate coordinates or records | 0 |
| Zero-length segments | 0 |
| Non-positive radii | 0 |
| Branch points / endpoints | 30 / 34 |
| Dendritic cable | 1,727.654 um |
| Axonal cable | 390.994 um |
| Total cable | 2,129.952 um |
| Maximum root path | 215.263 um |
| Imported surface | 7,596.193 um2 |
| NeuroMorpho soma surface | 396.349 um2 |
| Imported soma surface | 427.408 um2 |
| Structural QA | PASS |
| Anatomical completeness | LIMITED: moderate dendrites, incomplete axon |

The XY, XZ, YZ, and soma/proximal zoom figures show a clean connected arbor without plotting artifacts. Structural integrity does not imply completeness.

## 5. Evidence hierarchy

| Level | Meaning | Cell 1 use |
|---|---|---|
| SC | Same reconstructed cell | Geometry, PV, Pax2, location |
| SP | Same identified population | Mouse dorsal-horn PV physiology |
| PL | Population level | All passive/active quantitative targets |
| AN | Anatomical analogue | Not needed for primary baseline |
| M | Medlock-derived | iPV mapping; kinetic lineage only |
| F | Fitted | Leak and active conductance densities |
| A | Assumed | Ra, cm range, reversals, regional distribution |
| P | Prediction | Exact-morphology outputs and 35 C translation |

The evidence matrix was written before fitting. It does not merge cohort values as though they were same-cell measurements.

## 6. Passive electrophysiology

The strongest adult PV passive source is Gradwell et al. 2022 (*Front Neural Circuits*; DOI 10.3389/fncir.2022.834173). At 21-24 C, adult PV neurons had Rin 225 +/- 22 MOhm and whole-cell capacitance 10.9 +/- 0.6 pF. Rin and capacitance were derived from a 5-mV, 10-ms voltage-clamp step from -70 mV.

The source did not report membrane time constant or unforced RMP. Current-clamp experiments held cells at -60 mV using bias current; -60 mV is therefore not labeled RMP. The model uses a standardized -20 pA, 800-ms pulse to obtain a stable voltage response and to remain compatible with the published 800-ms active protocol.

## 7. Passive model parameters

| Parameter | Value | Units | Source/reason | Confidence |
|---|---:|---|---|---|
| Ra | 150 | ohm cm | restrained grid; model assumption | Low |
| cm | 0.5 | uF/cm2 | lower pre-registered boundary minimizes capacitance mismatch | Low |
| g_pas | 6.076828312e-5 | S/cm2 | fitted to Rin | Moderate |
| e_pas | -60 | mV | experimental holding condition, not RMP | Low |
| d_lambda | 0.1 at 100 Hz | dimensionless | numerical baseline | Engineering |
| dt | 0.025 | ms | converged fixed step | Engineering |

## 8. Passive validation

| Metric | Experimental target | Model | Error | Gate |
|---|---:|---:|---:|---|
| Rin | 225 +/- 22 MOhm | 225.000 MOhm | approximately 0% | PASS |
| Equivalent C from tau/Rin | 10.9 +/- 0.6 pF | 35.230 pF | 223.2% | FAIL |
| Geometric capacitance | no equivalent target | 37.981 pF | n/a | REPORTED |
| Mono-exponential tau | not reported | 7.927 ms | n/a | NO TARGET |

The capacitance failure is not concealed. Achieving 10.9 pF would require cm below the restrained 0.5-1.5 uF/cm2 range. Whole-cell electrode capacitance and total reconstructed membrane capacitance are not identical observables, so the failed comparison was not treated as a reason to distort cm further.

## 9. Active electrophysiology

Gradwell et al. report tonic firing in 64.2% of a broader PV cohort and in 55% of the adult cohort; the remainder was predominantly initial bursting. Adult population values at rheobase were 77 +/- 7 pA, threshold -34.9 +/- 1.3 mV, amplitude 44.8 +/- 1.6 mV, half-width 1.4 +/- 0.1 ms, AHP relative to threshold -17.6 +/- 1.6 mV, and AHP half-width 28.9 +/- 6.9 ms. Measurements were at 21-24 C, from -60 mV, with 800-ms steps in 20-pA increments. Voltages were reported without correction for a 14.7-mV liquid junction potential.

No exact-cell F-I curve or firing trace exists for NMO_170087. Model comparisons use the source’s uncorrected voltage convention and are labeled SP/PL.

## 10. Ion channels

| Mechanism | Ion/role | Location | Evidence | Decision |
|---|---|---|---|---|
| `pas` | leak/subthreshold | all sections | passive response requires it | Include |
| `l571_na` | Na; AP initiation/upstroke | soma, native axon; absent dendrites | spiking requires fast Na; exact isoform unknown | Include |
| `l571_kdr` | K; repolarization/repetitive firing | soma, dendrites, native axon | repetitive narrow spikes require outward current; exact isoform unknown | Include |
| SK | K(Ca); slow AHP/adaptation | none | same-population modulation exists | Exclude baseline: adds Ca/buffering parameters and would likely deepen already excessive AHP |
| VGCC | Ca entry | none | no quantitative Cell 1 target | Exclude |
| HCN/Ih | sag/rebound | none | no quantitative selected sag target | Exclude |
| A-type K | delay/transient firing | none | target is tonic, not delayed | Exclude |

The Na and KDR equations are reused from audited project mechanisms to avoid MOD duplication. The kinetic lineage is Medlock ModelDB 267056, but all Cell 1 densities are newly fitted. Q10 and Tref are explicit.

## 11. Active parameters

| Region | Na (S/cm2) | KDR (S/cm2) | Status |
|---|---:|---:|---|
| Soma | 0.006 | 0.003 | MODEL-FITTED |
| Dendrites | 0 | 0.002 | MODEL-FITTED/ASSUMED |
| Proximal 30 um native axon | 0.4 | 0.03 | MODEL-FITTED; MODEL-DEFINED AIS proxy |
| Distal native axon | 0.02 | 0.01 | MODEL-FITTED/ASSUMED |

The source’s moderate/incomplete morphology and archive diameter warning make exact density interpretation uncertain. The proximal region is not histologically confirmed as an AIS.

## 12. Active validation

| Metric | Population target | Model | Acceptance | Status |
|---|---:|---:|---|---|
| Active-model Rin probe | 225 +/- 22 MOhm passive target | 219.738 MOhm | 203-247 MOhm | PASS |
| Rheobase | 77 +/- 7 pA | 50 pA | 63-91 pA | FAIL |
| AP threshold | -34.9 +/- 1.3 mV | -34.839 mV | -37.5 to -32.3 | PASS |
| AP amplitude | 44.8 +/- 1.6 mV | 33.514 mV | 41.6-48.0 | FAIL |
| AP half-width | 1.4 +/- 0.1 ms | 1.075 ms | 1.2-1.6 | FAIL |
| AHP relative threshold | -17.6 +/- 1.6 mV | -36.877 mV | -20.8 to -14.4 | FAIL |
| Tonic persistence | tonic common | 30 spikes at 120 pA; final spike at 96.84% | >=3 spikes and >=80% | PASS |
| Recovery | engineering target | returns near baseline | within 5 mV | PASS |

At 120 pA the model fires 30 spikes (37.5 Hz), with an adaptation ratio of 1.037. The F-I curve rises through 200 pA (38 spikes, 47.5 Hz) and then collapses at 300-400 pA, a model-predicted depolarization-block transition without a matching experimental threshold.

## 13. Temperature

Experimental recordings were at 21-24 C. The 23 C model is primary. Q10 = 3 and Tref = 23 C scale Na and KDR time constants through `Q10^((T-Tref)/10)`; conductance maxima and passive properties do not scale.

| Temperature | Classification | Rheobase | Spikes at 120 pA | Interpretation |
|---:|---|---:|---:|---|
| 21 C | experimental-range model | 50 pA | 27 | comparison |
| 23 C | primary model | 50 pA | 30 | primary |
| 24 C | experimental-range model | 50 pA | 32 | comparison |
| 35 C | MODEL PREDICTION | 150 pA | 0 | not experimentally validated |

The 35 C translation is not ready for physiological network simulation.

## 14. AIS and axon

The native reconstructed axon is incomplete. No synthetic axon is created. The model applies enriched Na/KDR density to the first 30 um of native axonal path distance and labels this region **MODEL-DEFINED AIS proxy**.

At 120 pA, shortening enrichment to 15 um or making the reconstructed axon passive abolishes spiking; lengthening it to 45 um produces 36 rather than 30 spikes. The native axon’s incomplete state and the model’s dependence on this distribution are major limitations.

## 15. Numerical robustness

| Test family | Conditions | Outcome |
|---|---|---|
| dt | 0.05 / 0.025 / 0.0125 ms | 30 spikes at every dt; first-AP peak differs by 0.13 mV |
| d_lambda | 0.2 / 0.1 / 0.05 | 0 / 30 / 33 spikes; incomplete spatial convergence |
| Initial voltage | -70 / -60 / -50 mV | 30 spikes each |
| Global Na | -10% / baseline / +10% | 2 / 30 / 33 spikes; high sensitivity |
| Global KDR | -10% / baseline / +10% | 31 / 30 / 29 spikes |
| g_pas +/-5% | 32 / 28 spikes | moderate sensitivity |
| cm +/-10% | 32 / 29 spikes | moderate sensitivity |
| Ra +/-10% | 30 / 31 spikes | small sensitivity |
| Temperature | 22 / 24 C | 29 / 32 spikes |
| Proximal enrichment | 15 / 30 / 45 um | 0 / 30 / 36 spikes |

The model passes timestep and initialization checks but fails a strict robustness interpretation for spatial discretization, sodium density, and proximal-axon definition.

## 16. Comparison with Medlock

| Feature | Real reconstructed cell/population | Cell 1 model | Medlock iPV | Interpretation |
|---|---|---|---|---|
| Identity | Mouse PV+/Pax2+, lamina II-III | same morphology/identity | abstract iPV population | mapping only |
| Morphology | real 3D; moderate dendrites; incomplete axon | native import | reduced rule-based morphology | Cell 1 is anatomically richer but incomplete |
| Rin | 225 +/- 22 MOhm population | 225.000 passive; 219.738 active probe | model-defined | real-population target prioritized |
| Capacitance | 10.9 +/- 0.6 pF population | 35.230 pF equivalent; fail | model-defined | mismatch exposed |
| Active mechanisms | molecular densities unknown | Na + KDR + leak | broader rule set/model mechanisms | minimal set used |
| Firing | tonic common; initial burst also present | tonic at 120-200 pA | iPV phenotype | population match only |
| Temperature | 21-24 C experiments | 23 C primary | project/model convention | 35 C only a prediction |

Medlock conductances were not copied. Its mechanism equations are a documented kinetic lineage/control, subordinate to real-cell and same-population evidence.

## 17. Limitations

1. No exact-cell electrophysiology is linked to NMO_170087.
2. NeuroMorpho grades dendrites moderate, axon incomplete, and diameters unconfirmed.
3. Passive capacitance comparison fails at the lowest restrained cm.
4. Ra, cm, reversals, channel identities, densities, and distributions are assumed/fitted.
5. The active model fails four population gates.
6. AHP half-width is not modeled accurately by the minimal channel set.
7. Strong-current depolarization block has no matching quantitative target.
8. Spatial convergence is incomplete at the phenotype level.
9. The response is highly sensitive to Na density and proximal-axon enrichment.
10. The 35 C translation is unvalidated and qualitatively different from 23 C.

## 18. What is directly supported

| Claim | Support | Confidence |
|---|---|---|
| PV reporter positive | exact reconstructed cell | High |
| Pax2 positive/inhibitory identity | exact reconstructed cell | High |
| Lumbar dorsal horn lamina II-III | exact reconstructed cell | High |
| Native morphology topology | exact deposited reconstruction | High for deposited data; completeness limited |
| Adult PV Rin and waveform target values | same identified population | Moderate-high, population only |
| Tonic firing common in PV cohorts | same identified population | Moderate-high, population distribution |

## 19. What is model-derived

| Item | Classification | Confidence |
|---|---|---|
| Ra, cm, e_pas | MODEL-ASSUMED/FITTED | Low |
| g_pas | MODEL-FITTED to Rin | Moderate |
| Na/KDR kinetic choice | MEDLOCK-DERIVED/project-reused | Low-moderate |
| All channel densities | MODEL-FITTED | Low |
| Proximal 30-um enrichment | MODEL-ASSUMED/FITTED | Low |
| Exact-cell F-I and waveform | MODEL-PREDICTED | Low |
| 35 C response | MODEL-PREDICTED | Low |

## 20. Final model status

**Single-cell implementation:** ENGINEERING READY / BIOLOGICALLY PROVISIONAL.  
**Network integration:** **NO.**

The package is reproducible, auditable, and suitable for targeted single-cell refinement. It is not a defensible production network component because the active phenotype depends on a sensitive model-defined axonal region, four quantitative active gates fail, spatial convergence is incomplete, and the 35 C translation lacks physiological support.

## 21. Reproducibility

Environment: Linux/WSL, Python 3.10.20, NEURON 9.0.1, NumPy 2.2.6. Commands are run from repository root on branch `repo-reorganization-2026-08`.

```bash
(cd cells/L571_inhibitory_interneuron/mechanisms && nrnivmodl)
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/morphology_qa.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/prepare_model_swc.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/fit_passive.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/fit_active.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/refine_active.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/targeted_active_search.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/validate_cell.py
python -m unittest discover -s tests
```

Deterministic identifier/seed 170087 is stored even though current protocols contain no stochastic process. Full sweeps, selected JSON, traces, metrics, and figures are retained. Build products are excluded.

## 22. File manifest

- `morphology/primary/`: immutable downloaded SWC.
- `morphology/model/`: blank-line-only parser copy.
- `morphology/metadata/`: raw and consolidated NeuroMorpho metadata.
- `morphology/provenance/`: narrative and machine-readable transformation ledger.
- `parameters/passive/`, `active/`, `final/`: search inputs and frozen final configuration.
- `mechanisms/MANIFEST.md`: dependency declaration; no duplicated MOD files.
- `scripts/`: QA, conversion, fitting, validation, and report builders.
- `results/morphology_qa/`, `passive/`, `active/`, `temperature/`, `robustness/`, `validation/`: machine-readable outputs.
- `figures/morphology/`, `passive/`, `active/`, `final/`: publication-scale figures.
- `docs/evidence/`: evidence matrix, passive evidence, and channel audit.
- `docs/methodology/`: pre-fit, mechanism, and temperature decisions.
- `reports/`: focused validation reports and complete Markdown/DOCX report.

## 23. References

1. Gradwell MA et al. Diversity of inhibitory and excitatory parvalbumin interneuron circuits in the dorsal horn. *Pain*. 2022;163:e432-e452. DOI 10.1097/j.pain.0000000000002422. PMID 34326298. PMCID PMC8832545.
2. Gradwell MA et al. Altered Intrinsic Properties and Inhibitory Connectivity in Aged Parvalbumin-Expressing Dorsal Horn Neurons. *Front Neural Circuits*. 2022;16:834173. DOI 10.3389/fncir.2022.834173. PMID 35874431. PMCID PMC9305305.
3. Ma et al. Modulation of SK Channels via Calcium Buffering Tunes Intrinsic Excitability and Firing Properties of Spinal Dorsal Horn Neurons. *J Neurosci*. 2023;43:5608-5623. DOI 10.1523/JNEUROSCI.0426-23.2023. PMID 37451982. PMCID PMC10401647.
4. Gradwell MA et al. Heteromeric alpha/beta glycine receptors regulate excitability in parvalbumin-expressing dorsal horn neurons. *J Physiol*. 2017. DOI 10.1113/JP274926. PMID 28905384. PMCID PMC5709328.
5. Medlock L et al. Computational model and mechanisms deposited as ModelDB accession 267056 (2022); used only as documented kinetic lineage/control.

## Appendices

The Word report embeds the final parameter set, passive/active validation tables, F-I data, morphology QA, evidence matrix, channel justification, and robustness summary. The source CSV/JSON files remain authoritative for machine-readable precision.
