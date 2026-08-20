# L292-E1-LCN excitatory-interneuron scaffold

## Identity and scope

- **Cell:** L292-E1-LCN, NeuroMorpho `NMO_34021`
- **Species/strain:** Wistar rat
- **Region:** lumbar spinal cord, lamina I
- **Role:** excitatory local-circuit morphology scaffold
- **Morphology:** `morphology/primary/L292-E1-LCN.CNG.swc`

L292-E1's molecular identity is unknown. The eTrC, ePKCγ, eVGLUT3, eDOR, eSST, and eCR names are Medlock computational identities mapped onto this morphology; they are not experimentally confirmed molecular identities of L292-E1.

## Current status

**NOT READY.** The retained evidence shows:

| Gate | Status |
|---|---|
| Morphology QA | PASS |
| Shared mechanisms | PASS; HH2 removable singularity corrected analytically |
| Passive 23 °C | PASS |
| eTrC 23 °C | PASS with biological limitations |
| Delayed 23 °C | PASS with biological limitations |
| Temperature audit | PASS |
| eTrC 35 °C | PASS as a temperature-translated prediction |
| Delayed 35 °C | **FAIL: depolarization block under strong drive** |
| Synapse/population/network gates | Not run; correctly gated |

The failed 35 °C traces and one-factor diagnostics are preserved under `results/35C/delayed_excitatory/`.

## Key files

- Morphology provenance: `morphology/primary/L292-E1-LCN.metadata.json`
- Morphology QA: `reports/L292-E1-LCN_morphology_QA.md`
- Current parameters: [parameters/README.md](parameters/README.md)
- Shared mechanisms: `../../shared/mechanisms/medlock_267056/`
- ModelDB extraction: `parameters/common/medlock_modeldb_267056_reference.json`
- Mechanism/temperature audit: `docs/mechanism_audit.md`, `docs/temperature_audit.md`
- Final status: `reports/excitatory_interneurons_final_report.md`

## Run

From the repository root:

```bash
(cd shared/mechanisms/medlock_267056 && nrnivmodl)
python cells/L292_E1_excitatory_interneuron/scripts/validate_single_cell.py \
  --config cells/L292_E1_excitatory_interneuron/parameters/eTrC/eTrC_final_35C.json \
  --output-dir /tmp/l292-etrC-35C
```

To reproduce the retained failed gate, use `parameters/common/delayed_excitatory_final_35C.json` and a new output directory. Do not overwrite the recorded evidence.

## Known limitations

- Mapping a simplified Medlock rule to the reconstructed morphology is a biophysical upgrade requiring independent validation.
- L292-E1 has no confirmed Medlock molecular-population identity.
- The 35 °C results are mechanism-supported translations, not direct cell-specific experimental validation.
- Delayed 35 °C failure blocks six-population and network readiness.

