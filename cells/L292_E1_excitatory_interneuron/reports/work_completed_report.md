# Work Completed Report: Excitatory Interneuron Model Development

**Report date:** 11 August 2026  
**Project directory:** `C:\Users\Nikita\NeuropathicPain_Model\exc_interneuron`  
**Current phase:** Source audit and morphology QA completed; simulation validation is awaiting a usable NEURON installation.

## Executive summary

A new, isolated `exc_interneuron/` workspace has been created for developing six excitatory dorsal-horn interneuron models based on the L292-E1-LCN morphology and the Medlock et al. network model. The work completed so far establishes traceable scientific sources, imports and audits the official morphology, extracts the released Medlock parameters into structured configuration, stages the required NMODL mechanisms, and provides configuration-driven single-cell validation code.

The morphology/source foundation has passed the checks that can be performed without NEURON. No passive, active, synaptic, population, pain-condition, or temperature-comparison model has yet been accepted, because NEURON is not currently available in the runnable Python environment and the mechanisms have therefore not been compiled or simulated.

The existing `L796/` implementation was not edited.

## Scope and scientific identity

The workspace targets these six computational population identities:

1. eTrC
2. ePKCgamma
3. eVGLUT3
4. eDOR
5. eSST
6. eCR

The L292-E1-LCN reconstruction is a rat lamina-I local-circuit morphological scaffold. ePKCgamma/eVGLUT3/eDOR/eSST/eCR/eTrC labels refer to computational Medlock population identity and are not molecular identities experimentally confirmed for L292-E1-LCN.

This distinction is preserved throughout the documentation. The exact reconstruction's transmitter and molecular-marker identity remain unknown.

## Work completed

### 1. Evidence and source audit

Primary and official sources were reviewed and recorded:

- The Medlock et al. paper and its released ModelDB implementation.
- ModelDB model 267056, pinned to repository commit `6286892a9e7aa67ad80f2c5d86007350f900c644`.
- The official NeuroMorpho entry and standardized SWC for L292-E1-LCN.
- Szűcs et al. (2013), the source associated with the reconstruction.
- Yasaka et al. (2010), used only as supporting adult rat lamina-II physiology evidence rather than as a direct parameter source for this lamina-I juvenile reconstruction.

The evidence matrix separates direct source facts, supporting evidence, inferences, and provisional modeling choices. It also records conflicts rather than silently choosing one value. In particular:

- The Medlock paper reports simulations at 37 °C.
- The released ModelDB code executes at 36 °C.
- The released code uses `dt = 0.025 ms` and `v_init = -60 mV`.

These values are retained as reference conditions; the present project begins validation at 23 °C because that is close to the L292-E1 experimental recording temperature of 22–24 °C.

Supporting documents:

- `docs/evidence_matrix.md`
- `docs/medlock_excitatory_reference.md`
- `docs/mechanism_audit.md`
- `docs/stage_01_summary.md`

### 2. Isolated project structure

The following organized scaffold was created:

- `docs/` for evidence, source, and audit documentation.
- `morphology/primary/` and `morphology/alternatives/` for reconstruction inputs.
- `mechanisms/` for isolated NMODL source files.
- `parameters/common/` and one parameter directory for each of the six populations.
- `scripts/` for extraction, morphology QA, model construction, and validation.
- `results/` separated by temperature and validation stage.
- `figures/`, `reports/`, and one `final_models/` directory per population.

The later-stage result and final-model directories are intentionally gated placeholders. Their presence does not imply that the corresponding models have passed validation.

### 3. Official morphology acquisition and provenance

The official standardized NeuroMorpho reconstruction was downloaded without project-side geometry repair:

- File: `morphology/primary/L292-E1-LCN.CNG.swc`
- SHA-256: `65b44b3f94a93a77696ea31626073dd637250c48b0bae7d77bcaf9dfe654ea67`
- Species: rat, Wistar
- Region: lumbar spinal cord, lamina I
- Cell description: local-circuit multipolar interneuron
- Available structures: soma, dendrites, and axon
- NeuroMorpho physical-integrity label: `Dendrites & Axon Complete`
- Experimental age range: P14–P24
- Recording temperature: 22–24 °C

The official standardization logs are stored beside the SWC. They report 162 B1 radius outliers for which no action was taken and no A, B2, or C irregularities. These are documented provenance facts, not additional modifications made by this project.

The official original Neurolucida `.dat` endpoint returned a zero-byte response on 11 August 2026. The empty response was not retained as morphology input; the outcome is documented in `morphology/primary/ORIGINAL_DOWNLOAD_STATUS.md`.

### 4. Morphology quality assurance

The dependency-free QA script was run successfully against the official standardized SWC.

| Check or measurement | Result |
|---|---:|
| Total nodes | 17,823 |
| Unbranched SWC chain sections | 951 |
| Branch points | 471 |
| Dendritic cable length | 7,652.190183 µm |
| Axonal cable length | 35,061.174817 µm |
| Root nodes | 1 (`node 1`) |
| Missing-parent references | 0 |
| Unreachable nodes | 0 |
| Cycles | 0 |
| Zero-length edges | 0 |
| Non-positive radii | 0 |
| Suspicious non-soma diameters (`<= 0` or `> 20 µm`) | 0 |
| First axonal origin candidate | node 3771, parent soma node 1 |
| Candidate distance from soma centroid | 37.1255 µm |

The proximal axonal structure is described only as an axon-origin candidate. It is not claimed to be a histologically confirmed axon initial segment.

Generated QA artifacts:

- `results/23C/passive/morphology_qa.json`
- `reports/L292-E1-LCN_morphology_QA.md`
- `figures/L292-E1-LCN_morphology.svg`

### 5. Exact extraction of the Medlock reference model

The released Medlock Python sources were executed through a safe extraction script with NEURON/NetPyNE interfaces stubbed for data capture. The resulting structured reference contains the released:

- Cell-rule parameters.
- Population-to-rule mappings.
- Synaptic mechanisms.
- Connection probabilities, weights, and delays.

The extracted data are stored in `parameters/common/medlock_modeldb_267056_reference.json`.

The audit confirmed that:

- eTrC maps to the released `EXinitialRule`.
- The other five requested excitatory populations map to delayed-spiking rules.
- The released `PKCRule`, `SOMRule`, `CRRule`, and `EXdelayedRule` are parameter-identical after their condition labels are removed.

Therefore, the five delayed population names are currently computational identities mapped to the same released intrinsic rule. Population-specific intrinsic differences must not be invented without additional evidence and validation.

### 6. Mechanism staging and audit

The project now contains an isolated copy of the required mechanism sources:

- `AMPA_DynSyn.mod`
- `B_NA.mod`
- `borgka.mod`
- `CaIntraCellDyn.mod`
- `GABAa_DynSyn.mod`
- `Glycine_DynSyn.mod`
- `HH2.mod`
- `iKCa.mod`
- `KDRI.mod`
- `NK1_DynSyn.mod`
- `NMDA_DynSyn.mod`

`mechanisms/MANIFEST.txt` and `docs/mechanism_audit.md` record their origin and the initial temperature/Q10 review. No mechanism is reported as compiled or numerically validated yet.

### 7. Configuration-driven model and validation code

The following reusable scripts were implemented:

- `scripts/morphology_qa.py` parses and validates the SWC without NEURON and writes structured QA outputs.
- `scripts/extract_medlock_reference.py` extracts the released Medlock configuration into deterministic JSON.
- `scripts/rat_lcn.py` imports the real morphology, builds section groups, assigns passive properties before discretization, applies d-lambda discretization, and supports configuration-driven active conductances.
- `scripts/validate_single_cell.py` provides deterministic passive and current-clamp validation workflows with dry-run support and structured JSON, CSV, and SVG outputs when NEURON is available.

The model code applies a provisional 9 µm proximal-axon candidate region to represent the released Medlock hillock conductance rules by path distance. This is explicitly labeled a modeling proposal, not confirmed anatomy. The remaining axon is passive at this stage.

Initial configuration files were added:

- `parameters/common/passive_23C.json`
- `parameters/common/delayed_excitatory_23C.json`
- `parameters/eTrC/eTrC_23C.json`

The validation script reports its current ranges and their rationale before simulation, fixes random seeds, sets `h.celsius` before initialization, and emits structured metrics and traces. Configuration files are the source of parameter values rather than hard-coded per-population scripts.

## Verification performed

The following checks have completed successfully:

- The official SWC checksum and metadata were recorded.
- Morphology QA ran to completion and produced JSON, Markdown, and SVG artifacts.
- The Medlock reference extraction ran to completion and produced structured JSON.
- All project Python scripts passed Python 3.12 byte-code compilation.
- The existing `L796/` implementation was left unchanged.

The directory supplied by the user is not currently a Git worktree, so a Git diff/status audit is unavailable. File isolation and direct inspection were used instead.

## Current validation status

| Stage | Status | Meaning |
|---|---|---|
| Source and evidence audit | Completed | Sources, conflicts, and evidence grades documented |
| Morphology provenance | Completed | Official standardized reconstruction and checksum recorded |
| Morphology QA | Passed | Structural/parser checks completed without detected topology errors |
| Passive validation at 23 °C | Not run | Requires NEURON |
| eTrC active validation at 23 °C | Not run | Requires passive acceptance, compiled mechanisms, and NEURON |
| Delayed-excitatory validation at 23 °C | Not run | Requires passive acceptance, compiled mechanisms, and NEURON |
| Six population-specific models | Not accepted | Population mappings are staged; intrinsic validation is incomplete |
| Synapse unit tests | Not run | Must follow active single-cell validation |
| 35/36/37 °C comparison | Not run | Temperature/Q10 behavior must be tested after 23 °C acceptance |
| Morphology sensitivity | Not run | Alternative morphology set has not been selected and simulated |
| Scaled population smoke test | Not run | Gated by single-cell and synapse stages |
| Full population and pain experiments | Not run | Gated by all preceding validation stages |
| HPC/GPU optimization | Not started | Correctly deferred until scientific validation is complete |

### Per-model readiness

| Model | Current state |
|---|---|
| eTrC | Released initial-spiking rule mapped and configuration staged; not simulated or accepted |
| ePKCgamma | Released delayed-spiking identity mapped; no population-specific intrinsic evidence validated |
| eVGLUT3 | Released delayed-spiking identity mapped; no population-specific intrinsic evidence validated |
| eDOR | Released delayed-spiking identity mapped; no population-specific intrinsic evidence validated |
| eSST | Released delayed-spiking identity mapped; no population-specific intrinsic evidence validated |
| eCR | Released delayed-spiking identity mapped; no population-specific intrinsic evidence validated |

No directory under `final_models/` should be treated as a validated deliverable at this point.

## Environment blocker

No compatible NEURON runtime is presently available to the project:

- The Windows system environment has no usable Python/NEURON installation.
- The bundled Python environment does not include the `neuron` package.
- A temporary `pip install neuron` attempt found no compatible Windows wheel in the configured package index.
- WSL Ubuntu 26.04 is available, and its package catalog exposes `neuron`, `neuron-dev`, and `python3-neuron`, but these packages have not been installed.

Consequently, the NMODL sources have not been compiled and no NEURON trace or electrophysiology metric has been produced. This is an environment limitation, not a scientific validation pass or failure.

## Recommended next action

Continue in the prescribed build order:

1. Install a working NEURON runtime in WSL and record its exact version.
2. Compile only the isolated `exc_interneuron/mechanisms/` sources and save the compiler log.
3. Run the passive-only 23 °C protocol on the real L292-E1-LCN morphology.
4. Compare resting potential, input resistance, membrane time constant, voltage sag, and numerical stability against the documented acceptance ranges.
5. If adjustment is required, tune only the explicitly allowed passive parameters first and retain every run's configuration and result.
6. Accept passive behavior before enabling the eTrC and delayed-spiking active rules.
7. Proceed to synapse unit tests, scaled population smoke tests, full population work, pain-condition experiments, and only then HPC/GPU optimization.

This ordering prevents later simulations from depending on an unvalidated single-cell foundation.

## Principal artifact index

| Artifact | Purpose |
|---|---|
| `README.md` | Workspace scope, workflow, and status |
| `docs/evidence_matrix.md` | Claim-to-source traceability and evidence grades |
| `docs/medlock_excitatory_reference.md` | Mapping of requested excitatory populations to the released model |
| `docs/mechanism_audit.md` | Mechanism provenance and temperature review |
| `docs/stage_01_summary.md` | Completed source/morphology-stage summary |
| `morphology/primary/L292-E1-LCN.CNG.swc` | Official standardized morphology |
| `morphology/primary/L292-E1-LCN.metadata.json` | Morphology metadata and provenance |
| `reports/L292-E1-LCN_morphology_QA.md` | Human-readable morphology QA report |
| `results/23C/passive/morphology_qa.json` | Machine-readable morphology QA results |
| `parameters/common/medlock_modeldb_267056_reference.json` | Exact extracted released parameter/connectivity reference |
| `scripts/rat_lcn.py` | Morphology import and configurable cell construction |
| `scripts/validate_single_cell.py` | Passive/active single-cell validation runner |

## Bottom line

The project has a traceable and structurally validated morphology foundation, an audited Medlock reference, isolated mechanisms, initial parameter configurations, and deterministic validation tooling. The work is ready for the first NEURON-dependent milestone—mechanism compilation followed by passive validation at 23 °C—but none of the six active cell models is yet scientifically accepted or ready for population simulations.
