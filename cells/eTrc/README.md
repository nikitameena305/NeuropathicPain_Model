# NMO_109005 GRP eTrC-like model

This package contains a morphology-constrained NEURON model of **26-11-14-A-A6 / NMO_109005**, a mouse GRP-positive lamina-II excitatory interneuron used as a biologically informed transient-central/eTrC-like model.

GRP identity is experimentally supported. Exact eTrC membership and same-cell electrophysiology are not established for this reconstruction. Quantitative targets are therefore GRP population constraints from Dickie et al. (2019), not measurements from NMO_109005.

## Reproduce the final model

From a repository root on Linux with NEURON 9 and NumPy/Matplotlib installed:

```bash
python cells/eTrc/scripts/run_eTrC_final.py
```

The runner resolves paths from its own location, compiles the package-local MOD files with `nrnivmodl` when needed, sets `h.celsius = 35` before initialization, runs the declared current-clamp series, and rewrites the final traces, metrics, and active figures.

For the staged channel audit and lightweight robustness set:

```bash
python cells/eTrc/scripts/fit_active.py
```

For passive fitting and morphology QA, see each script's `--help`. Every script supports `--dry-run`.

## Result in one line

The final model has an 18 pA rheobase, a stable single spike, no depolarization block, and successful recovery, but its 25.25 ms first-spike latency, active-model Rin, and morphology-derived capacitance fail the corresponding GRP population constraints.

- Model status: **ENGINEERING READY / BIOLOGICALLY PROVISIONAL**
- Ready for network integration: **NO**
- Final mechanisms: `pas`, `B_Na`, `B_DR`
- Active distribution: soma plus a **MODEL-DEFINED PROXIMAL ACTIVE CHANNEL DOMAIN** on the unchanged native partial axon (path distance ≤20 µm); no synthetic geometry
- Canonical configuration: `parameters/eTrC_NMO109005_final_35C.json`
- Complete report: `report/eTrC_NMO109005_COMPLETE_REPORT.md`

Build products (`x86_64/`, `__pycache__/`, and `*.pyc`) are intentionally excluded from version control.

## Primary sources

- Dickie AC et al. *PAIN* 2019;160:442–462. DOI: [10.1097/j.pain.0000000000001406](https://doi.org/10.1097/j.pain.0000000000001406)
- [NeuroMorpho.Org NMO_109005 record](https://neuromorpho.org/neuron_info.jsp?neuron_name=26-11-14-A-A6)
- Reused mechanism source: Medlock/ModelDB model [267056](https://modeldb.science/267056)

