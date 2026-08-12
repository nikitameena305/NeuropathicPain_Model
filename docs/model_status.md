# Model status

Status is derived from retained executed results and reports. User-supplied expectations that lack a corresponding artifact are labelled as provenance gaps rather than promoted to validated claims.

| Model | Role | Morphology | Passive | Active | 35 °C | Overall |
|---|---|---|---|---|---|---|
| L796-ALT-PN | Projection neuron | Reconstructed `NMO_34019`; QA retained | PASS in selected historical model | Numerically usable; active densities feature-fitted; AP half-width relaxed-pass | Fixed-intrinsic sensitivity exists, but the requested selected 35 °C refit and firing-diagnosis artifacts were not found | **Engineering-ready / biologically provisional; temperature provenance needs attention** |
| L292-E1-LCN | Excitatory interneuron morphology scaffold | `NMO_34021`; QA PASS | 23 °C PASS | eTrC 23 °C PASS; delayed 23 °C PASS, both with disclosed biological limitations | eTrC PASS as prediction; delayed **FAIL** due depolarization block | **NOT READY** |
| L571-LCN | Inhibitory GABAergic interneuron | `NMO_34027`; QA PASS | Population-constrained PASS | Tonic phenotype and numerical checks PASS | Exploratory Q10=1 translation only | **READY WITH BIOLOGICAL LIMITATIONS** |

## L796 evidence boundary

`cells/L796_projection_neuron/reports/L796_single_cell_final_status.md` locks `parameters/L796_final_parameter_set.json` at 6.3 °C and documents the half-width limitation. The repository retains temperature sensitivity at 23/37 °C, but no selected 35 °C parameter JSON, 35 °C refit script, or explicitly named firing-diagnosis result was found in:

1. `origin/main` at pre-cleanup commit `c58e004`;
2. `C:\Users\Nikita\NeuropathicPain_Model`;
3. the supplied `Neuron` workspace source collections; or
4. the other remote branches visible during the audit.

This is a repository-provenance gap, not evidence that the scientific work never occurred. Restore those files with checksums and provenance before changing the temperature status.

## L292 scientific gate

The retained final report and results establish morphology, mechanisms, passive 23 °C, eTrC 23/35 °C, and delayed 23 °C stage passes. The delayed 35 °C configuration enters strong-drive depolarization block; bounded one-factor sodium and potassium diagnostics did not restore a robust solution. Synapse, population, and network stages therefore remain gated in the required build order.

## L571 evidence boundary

The 23 °C candidate is constrained against population-level rat lamina-I local-circuit-neuron measurements, not exact L571 electrophysiology. The 35 °C label changes `h.celsius` but retains Q10=1 in the fitted adapted mechanisms. It is suitable for exploratory numerical work only and is not fully biologically validated.

