# Neuropathic Pain Model

Reproducible NEURON models and validation evidence for three rat spinal dorsal-horn neurons. The models are intentionally separate: a shared morphology or mechanism source does not imply a shared biological identity.

## Current cells

| Cell | Role | Current status |
|---|---|---|
| [L292-E1-LCN](cells/L292_E1_excitatory_interneuron/README.md) | Excitatory interneuron morphology scaffold | **NOT READY**: the delayed model enters depolarization block at 35 °C |
| [L571-LCN](cells/L571_inhibitory_interneuron/README.md) | Inhibitory GABAergic interneuron | **READY WITH BIOLOGICAL LIMITATIONS** |
| [L796-ALT-PN](cells/L796_projection_neuron/README.md) | Projection neuron | **Engineering-ready / biologically provisional** |

The exact scientific gates, including the L796 temperature-provenance gap found during cleanup, are recorded in [docs/model_status.md](docs/model_status.md).

## Layout

```text
.
├── cells/
│   ├── L292_E1_excitatory_interneuron/
│   ├── L571_inhibitory_interneuron/
│   └── L796_projection_neuron/
├── shared/mechanisms/medlock_267056/
├── external/medlock_267056_excitatory_scaffold/
├── environment/
├── scripts/
├── tests/
├── docs/
└── archive/
```

`external/medlock_267056_excitatory_scaffold/` is a compact, independently runnable Medlock reproduction scaffold. It is not the L292 reconstructed-cell model. Historical early circuit work and the separate mouse GRP morphology candidates are documented under [archive/](archive/README.md).

## Environment

The recorded validation environment used Python 3.10.20, NEURON 9.0.1, NumPy 2.2.6, SciPy 1.15.3, Matplotlib 3.10.9, and pandas 2.3.3 in WSL. Recreate it with:

```bash
conda env create -f environment/environment.yml
conda activate neuropathic-pain-model
```

## Compile mechanisms

Compile the canonical ModelDB-derived set and the separate L571 variants:

```bash
(cd shared/mechanisms/medlock_267056 && nrnivmodl)
(cd cells/L571_inhibitory_interneuron/mechanisms && nrnivmodl)
```

Generated `x86_64/`, `arm64/`, `special`, and `nrnmech.dll` files are ignored and must not be committed.

## Quick validation

Run structure and configuration checks without NEURON:

```bash
python -m unittest discover -s tests -v
python cells/L292_E1_excitatory_interneuron/scripts/validate_single_cell.py \
  --config cells/L292_E1_excitatory_interneuron/parameters/eTrC/eTrC_final_35C.json \
  --output-dir /tmp/l292-dry-run --dry-run
python cells/L571_inhibitory_interneuron/scripts/run_L571.py --dry-run
python cells/L796_projection_neuron/scripts/smoke_test_L796.py --dry-run
```

After compiling mechanisms, run the three lightweight current-clamp smoke tests:

```bash
bash scripts/run_smoke_tests.sh
```

These smoke tests confirm loading and execution; they do not replace the recorded validation protocols or change any scientific parameter.

## Reproducibility and audit records

- [Before-cleanup audit](docs/repository_audit_before_cleanup.md) and [CSV](docs/repository_audit_before_cleanup.csv)
- [External source audit](docs/source_collections_before_import.md) and [CSV](docs/source_collections_before_import.csv)
- [Duplicate audit](docs/duplicate_file_audit.csv)
- [Deletion manifest](docs/deletion_manifest.md)
- [Retained-file manifest](docs/repository_manifest.md) and [CSV](docs/repository_manifest.csv)
- [Scientific status](docs/model_status.md)

No individual retained file exceeds GitHub's 100 MB file limit. The convergence and trace collections remain sizeable; use Git LFS in future if substantially larger raw recordings are added.

