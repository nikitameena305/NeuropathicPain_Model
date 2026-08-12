# Repository validation report

Validation was run on 2026-08-12 from the reorganized repository. Generated
`x86_64/`, `__pycache__/`, and `*.pyc` products were removed after the checks;
they are reproducible build artifacts and are excluded by `.gitignore`.

## Environment

- WSL Ubuntu 26.04
- Python 3.10.20
- NEURON 9.0.1
- NumPy 2.2.6
- SciPy 1.15.3
- Matplotlib 3.10.9
- pandas 2.3.3

The reusable environment specification is in `environment/environment.yml`,
with a matching root `requirements.txt` for Python dependencies.

## Automated repository checks

`python -m unittest discover -s tests -v` passed all five tests. The tests
confirm that each production cell has a non-empty morphology, selected JSON
parameters parse, the shared mechanisms and L571 variants exist, the GRP
candidate is separated from L292, and generated build/cache files are not
tracked.

`python -m compileall -q cells scripts tests external` passed. The archival
L796 1-second editor snapshot is intentionally outside this executable-code
check because it preserves its original malformed experiment state. The active
copy was repaired by restoring the feature-summary loop indentation and
removing the misplaced call that referenced `best_params` before assignment;
no scientific parameter was changed.

## NEURON smoke tests

`bash scripts/run_smoke_tests.sh` passed in the environment above:

| Model | Test | Result |
|---|---|---|
| L796-ALT-PN | Selected 6.3 °C parameters, 0.04 nA clamp | PASS: 200 sections, 56,001 samples, 5 spikes, completed to `tstop` |
| L292-E1-LCN eTrC | Selected 35 °C parameters at -0.02, 0.0, and 0.88 nA | PASS: rheobase 0.88 nA; validator classification `STAGE_GATE_PASSED` |
| L571-LCN | Selected 23 °C parameters, 0.1 nA clamp | PASS: 340 sections, 9,948 segments, 14 spikes, complete AP metrics |

The shared 22-file ModelDB 267056 mechanism set and both L571-specific
mechanisms compiled successfully with `nrnivmodl`. Compiler warnings are
limited to retained upstream thread-safety/CVODE notices and deprecated
VecStim API calls; no compilation errors occurred.

## Scientific gates

These smoke-test passes establish importability and numerical execution, not
new biological validation. L292 remains **NOT READY** because its retained
delayed-firing 35 °C experiment fails through depolarization block. L796 remains
engineering-ready/biologically provisional because the requested selected
35 °C refit and explicit firing-diagnosis artifacts were not present in the
audited sources. L571 remains **READY WITH BIOLOGICAL LIMITATIONS** because its
fit is population-constrained and its 35 °C translation is exploratory.
