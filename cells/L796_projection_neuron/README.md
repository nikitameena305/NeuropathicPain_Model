# L796-ALT-PN projection neuron

## Identity and scope

- **Cell:** L796-ALT-PN, NeuroMorpho `NMO_34019`
- **Species/strain:** young Wistar rat
- **Region:** lumbar spinal cord, lamina I
- **Role:** anterolateral-tract projection neuron
- **Morphology:** `morphology/L796-ALT-PN.CNG.swc`

Identity evidence and biological limits are summarized in [docs/L796_ALT_PN_biological_channel_inventory.md](docs/L796_ALT_PN_biological_channel_inventory.md). Do not confuse this cell with L796-LCN.

## Current status

**Engineering-ready / biologically provisional.** Morphology import, passive fitting, active fitting, rheobase/AP features, recovery, receptor tests, current recordings, and diagnostic channel experiments are retained. Active conductances are phenomenologically fitted to projection-neuron feature ranges rather than measured for L796.

The current repository-supported model of record is `parameters/L796_final_parameter_set.json`, explicitly associated by its final-status report with **6.3 °C** and one relaxed AP-half-width gate. The cleanup request described a selected, numerically validated 35 °C refit and firing-diagnosis experiment, but neither artifact was present on `origin/main` or in the audited local source collections. Until those artifacts are restored, this repository must not claim that its selected L796 parameter file is validated at 35 °C. See [docs/model_status.md](../../docs/model_status.md).

## Key files

- Current parameters: `parameters/L796_final_parameter_set.json`
- Parameter history: [parameters/README.md](parameters/README.md)
- Shared mechanisms: `../../shared/mechanisms/medlock_267056/`
- Morphology QA: `reports/L796_morphology_check_report.txt`
- Current scientific status: `reports/L796_single_cell_final_status.md`
- Temperature sensitivity: `reports/temperature_sensitivity_fixed_intrinsic/L796_temperature_sensitivity_report.md`
- F-I/AP/recovery evidence: `results/`, `traces/`, and `validation/`
- Channel and firing diagnostics: `results/channels/`, `results/step3_active_grid/`, and `reports/L796_channel_complement_report.md`

## Run

From the repository root:

```bash
(cd shared/mechanisms/medlock_267056 && nrnivmodl)
python cells/L796_projection_neuron/scripts/smoke_test_L796.py --run
```

Run the retained validation-output pipeline from the cell directory:

```bash
cd cells/L796_projection_neuron
bash run_validation.sh
```

## Known limitations

- Active densities are feature-fitted and not L796-specific measurements.
- The repository-supported selected model uses the historical 6.3 °C validation condition.
- AP half-width is a documented relaxed pass in that model.
- The requested 35 °C selected parameter set and firing-diagnosis artifact are missing and require provenance recovery.
- The model's limited/phasic firing must not be represented as a fully biologically validated firing phenotype.
