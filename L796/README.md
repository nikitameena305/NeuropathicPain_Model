# L796 ALT-PN Single-Cell Model

This folder contains the L796 ALT-PN reconstructed morphology and modelling workflow used for morphology inspection, passive fitting, active conductance grid search, current-step validation, and final Step 5 tuning.

## Model status

The current final model is the Step 5 tuned active model.

Passive fitting is complete. Active conductances are feature-tuned because exact L796 active conductance densities were not available from the morphology source. Therefore, this model should be treated as a morphology-based, passive-fitted, feature-tuned active model, not an exact biological reconstruction.

## Folder structure

```text
L796/
├── README.md
├── morphology/              # SWC and HOC morphology files
├── scripts/                 # Python/NEURON workflow scripts
├── reports/                 # Text reports and markdown summaries
├── parameters/              # Final JSON parameter sets
├── results/                 # CSV and DAT result files
├── figures/                 # PNG figures grouped by modelling step
└── traces/                  # Raw/final trace outputs
