# NMO_170087 mouse PV+/Pax2+ inhibitory interneuron

## Identity

- **Original cell:** 23-04-18C-04-cell-1
- **NeuroMorpho:** NMO_170087
- **Species/strain:** mouse, Pvcre
- **Region:** lumbar spinal dorsal horn
- **Lamina:** II-III
- **Known identity:** PV reporter positive, Pax2 positive, inhibitory interneuron
- **Unknown:** exact-cell electrophysiology, exact-cell sex/age, channel densities, anatomically confirmed AIS
- **Medlock mapping:** iPV; a network-role mapping, not a source of blindly inherited conductances

## Why this morphology was selected

This is the highest-ranked mouse iPV candidate in the project audit because marker identity, inhibitory identity, laminar location, and morphology are linked at the same-cell level. It remains Tier 2 / morphology grade B because NeuroMorpho marks dendrites as moderate integrity and the axon as incomplete, while electrophysiology is available only for the PV population.

## Morphology quality

The checksum-protected standardized SWC has 2,897 nodes, one root, one connected component, no orphan/duplicate/zero-length/non-positive-radius records, 1,727.65 um dendritic cable, and 390.99 um reconstructed axon. No synthetic axon is added. A blank-line-only parser copy is used by Import3D and has a complete transformation ledger.

## Passive evidence and status

The primary target is adult mouse PV-population Rin = 225 +/- 22 MOhm at 21-24 C. The passive model gives 225.000 MOhm (**PASS**). The reported 10.9 +/- 0.6 pF whole-cell capacitance is not reproduced: the model equivalent is 35.230 pF and geometric capacitance is 37.981 pF (**preserved FAIL**). RMP and tau were not reported in the selected source and are not invented.

## Active evidence, channels, and status

Same-population evidence supports tonic or initial-burst firing, with tonic firing common. Quantitative adult targets include rheobase, AP threshold, amplitude, half-width, and AHP. The smallest active set—leak, fast Na, and delayed-rectifier K—uses existing audited project kinetics but Cell 1-specific fitted densities.

At 23 C, the model is tonic at 120-200 pA and matches AP threshold. It fails the population rheobase, amplitude, half-width, and AHP gates and enters depolarization block at strong current. The active solution is therefore biologically provisional.

## Temperature and robustness

The primary model is evaluated at 23 C within the reported 21-24 C experimental range. Both active mechanisms use Q10 = 3 and Tref = 23 C for gating rates only. The 35 C result is explicitly a **MODEL PREDICTION**: rheobase rises to 150 pA and 120 pA no longer evokes spikes.

Timestep convergence is good, but the response is sensitive to coarse spatial discretization, -10% sodium, and the length/presence of the model-defined proximal-axon enrichment. The native incomplete axon is used; the enriched 30-um region is a **MODEL-DEFINED AIS proxy**, not an anatomically confirmed AIS.

## Final status

**ENGINEERING READY / BIOLOGICALLY PROVISIONAL.** The implementation is reproducible and suitable for continued single-cell development. **It is not ready for network integration** because multiple biological and robustness gates fail.

## Run commands

From the repository root in the documented NEURON environment:

```bash
(cd cells/L571_inhibitory_interneuron/mechanisms && nrnivmodl)
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/morphology_qa.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/prepare_model_swc.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/fit_passive.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/fit_active.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/refine_active.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/targeted_active_search.py
python cells/23-04-18C-04-cell-1_inhibitory_interneuron/scripts/validate_cell.py
```

The final selected configuration is intentionally fixed in `parameters/final/NMO_170087_final_23C.json`; exploratory search scripts do not overwrite it.

## Important files

- Morphology provenance: `morphology/provenance/morphology_provenance.md`
- Evidence matrix: `docs/evidence/evidence_matrix.csv`
- Channel decisions: `docs/evidence/channel_justification.csv`
- Final parameters: `parameters/final/NMO_170087_final_23C.json`
- Passive metrics: `results/passive/passive_validation_metrics.json`
- Active metrics/F-I/traces: `results/active/`
- Temperature results: `results/temperature/`
- Robustness results: `results/robustness/`
- Complete report: `reports/23-04-18C-04-cell-1_COMPLETE_MODEL_REPORT.md` and `.docx`

## Known limitations

1. No electrophysiological recording is linked to this exact reconstructed cell.
2. Dendrites are moderate integrity, axon is incomplete, and the archive flags `No Diameter`.
3. The capacitance comparison fails even at the lower restrained cm boundary.
4. Active densities and distributions are fitted assumptions; molecular channel identity is not established.
5. The model-defined proximal-axon enrichment is essential and sensitive.
6. Four of seven active validation gates fail.
7. Strong-current depolarization block and 35 C behavior lack direct validation.
8. Spatial convergence is incomplete between d_lambda 0.1 and 0.05.
