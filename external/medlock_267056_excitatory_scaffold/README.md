# SDH excitatory interneuron populations

Minimal NEURON/NetPyNE project for the six excitatory spinal dorsal horn
populations described in the Medlock et al. network model:

- eTrC
- ePKCγ
- eVGLUT3
- eDOR
- eSST
- eCR

The production population contains 109 cells:

| Population | ModelDB label | Count | Intrinsic template |
|---|---|---:|---|
| eTrC | TrC | 10 | initial/transient |
| ePKCγ | PKC | 30 | delayed |
| eVGLUT3 | VGLUT3 | 4 | delayed |
| eDOR | DOR | 30 | delayed |
| eSST | SOM | 15 | delayed |
| eCR | CR | 20 | delayed |

## Scientific scope

This repository is a compact **Medlock reproduction scaffold**, not yet a
six-morphology biophysical upgrade. The source model assigns six population
labels but uses only two distinct intrinsic excitatory rule contents:
`EXinitialRule` for eTrC and `EXdelayedRule` for the other five populations.
The code creates independent copies for every population so later tuning of
one class cannot mutate another.

Included:

- the six population definitions;
- the two required intrinsic templates;
- the six MOD mechanisms used by those templates;
- exemplar, smoke-test, and production modes;
- deterministic seeds and dry-run support;
- structural tests and GitHub Actions.

Excluded intentionally:

- primary afferents, inhibitory cells, and pNK1 projection cells;
- synaptic connectivity and pain-condition perturbations;
- reconstructed SWC morphologies;
- large research notes, figures, and duplicate MOD catalogs.

Add those only after the isolated populations pass passive and active
validation.

## Installation

Linux, WSL, or an HPC Linux environment is recommended for NMODL compilation.
The environment is pinned to the project's NEURON 8.2.4 baseline.

```bash
conda env create -f environment.yml
conda activate sdh-excitatory
CC="gcc -std=gnu17" nrnivmodl mods
```

The explicit C17 flag is required when NEURON 8.2.4 is compiled with a modern
GCC whose default language mode is C23 (for example GCC 15 on Ubuntu 26.04).
Older GCC versions can also use the same command.

NEURON's 8.2.4 documentation recommends WSL as an option for Windows users:
https://www.neuronsimulator.org/en/8.2.4/

## Verify before simulation

```bash
python -m unittest discover -s tests -v
python -m sdh_exc.run --dry-run --mode exemplar
python -m sdh_exc.run --dry-run --mode smoke
python -m sdh_exc.run --dry-run --mode production
```

Expected totals:

- `exemplar`: 6 cells, one of each class;
- `smoke`: 13 cells;
- `production`: 109 cells.

## Run

Compile the mechanisms first, then run from the repository root:

```bash
python -m sdh_exc.run --run --mode exemplar
python -m sdh_exc.run --run --mode smoke
python -m sdh_exc.run --run --mode production
```

Use `--stim-amp` to change the common somatic IClamp amplitude:

```bash
python -m sdh_exc.run --run --mode exemplar --stim-amp 0.2
```

The default 0.2 nA step reliably activates both source templates in the
software smoke test. It is not a fitted rheobase or a claim that all six
biological populations receive identical current.

The exemplar and smoke modes run for 800 ms. Production reproduces the source
configuration's 5000 ms duration, 36 °C temperature, −60 mV initialization,
and 0.025 ms integration/recording step.

## Repository structure

```text
.
├── .github/workflows/tests.yml
├── environment.yml
├── mods/
│   ├── MANIFEST.txt
│   └── six required ModelDB mechanisms
├── pyproject.toml
├── src/sdh_exc/
│   ├── data/populations.json
│   ├── catalog.py
│   ├── cell_rules.py
│   ├── netparams.py
│   ├── run.py
│   └── sim_config.py
├── tests/
└── THIRD_PARTY_NOTICE.md
```

## Provenance and citation

The intrinsic templates and MOD files are derived from ModelDB accession
267056, commit `6286892a9e7aa67ad80f2c5d86007350f900c644`.

When using this repository, cite:

1. Medlock L, Sekiguchi KJ, Hong S, et al. *Multiscale computer model of the
   spinal dorsal horn reveals changes in network processing associated with
   chronic pain.* Journal of Neuroscience. 2022;42:5003–5016.
   https://doi.org/10.1523/JNEUROSCI.1198-21.2022
2. ModelDB accession 267056: https://modeldb.science/267056
3. McDougal RA, et al. *Twenty years of ModelDB and beyond.* J Comput
   Neurosci. 2017;42:1–10. https://doi.org/10.1007/s10827-016-0623-7

See `THIRD_PARTY_NOTICE.md` and `mods/MANIFEST.txt` for file-level provenance.

## Before making the GitHub repository public

No project license has been selected, and the upstream ModelDB snapshot does
not contain a root `LICENSE` file. Choose a license and confirm the applicable
third-party redistribution terms before public release. A private GitHub
repository can be used while that decision is pending.
