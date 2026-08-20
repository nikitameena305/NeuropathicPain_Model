# L571-LCN inhibitory interneuron

## Identity and scope

- **Cell:** L571-LCN, NeuroMorpho `NMO_34027`
- **Species/strain:** Wistar rat
- **Region:** lumbar spinal cord, lamina I
- **Role:** GABAergic local-circuit inhibitory interneuron
- **Morphology:** `morphology/L571-LCN.CNG.swc`

The deposited metadata are in `morphology/neuromorpho_metadata.json`; the unchanged standardized morphology and its QA are documented in `reports/morphology_qa.md`.

## Current status

**READY WITH BIOLOGICAL LIMITATIONS.** The 23 °C model is constrained by population-level rat lamina-I LCN measurements. The 35 °C model is an exploratory temperature-labelled translation with Q10=1 for the selected adapted mechanisms, not direct 35 °C experimental validation.

## Key files

- Selected parameters: [parameters/README.md](parameters/README.md)
- Cell-specific mechanisms: `mechanisms/l571_na.mod`, `mechanisms/l571_kdr.mod`
- ModelDB reference mechanisms: `../../shared/mechanisms/medlock_267056/`
- Validation report: `reports/L571_final_validation.md`
- Machine-readable metrics: `results/23C/validation_metrics.json`, `results/35C/validation_metrics.json`
- F-I and selected traces: `results/23C/`, `results/35C/`

## Run

From the repository root:

```bash
(cd cells/L571_inhibitory_interneuron/mechanisms && nrnivmodl)
python cells/L571_inhibitory_interneuron/scripts/run_L571.py \
  --config cells/L571_inhibitory_interneuron/parameters/L571_final_23C.json \
  --current 0.1
```

For a reduced validation sweep:

```bash
python cells/L571_inhibitory_interneuron/scripts/validate_L571.py --quick
```

## Known limitations

- Exact individual L571 rheobase, AP waveform, firing class, and membrane time constant are unavailable.
- The fitted active densities are model-derived.
- The reconstructed proximal axon is an AIS proxy, not a histologically confirmed AIS.
- The 35 °C result is not fully temperature-corrected or experimentally validated.

