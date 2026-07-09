# NeuropathicPain_Model

Computational modelling project for spinal dorsal horn pain circuitry.

## Current completed module

### L796 ALT-PN model

This folder contains a NEURON model of the rat lamina I anterolateral-tract projection neuron L796.

Main components:

- morphology import and validation
- passive membrane fitting
- active voltage-gated conductance fitting
- somatic/proximal-dendritic B_Na correction
- ligand-gated receptor testing
- normal vs neuropathic synaptic manipulation
- evidence-driven channel-complement audit

## Current validation status

The final L796 model passes:

- RMP
- input resistance
- rheobase
- AP overshoot
- AP amplitude
- no spontaneous firing at 0 pA

Documented limitation:

- AP half-width remains broad: 1.450 ms vs 0.87-1.14 ms target.

## Important interpretation

This model is suitable for excitability and synaptic-integration studies. It is not yet fully validated for precise AP waveform kinetics.

## Main folders

- `L796/morphology/` — SWC/HOC morphology files
- `L796/mechanisms/mods/` — MOD mechanism source files
- `L796/scripts/` — NEURON/Python simulation scripts
- `L796/parameters/` — fitted parameter JSON files
- `L796/results/` — validation CSV/JSON outputs
- `L796/figures/` and `L796/plots/` — generated plots
- `L796/reports/` — final reports
- `L796/literature_targets/` — literature-based validation targets

## Next step

Build and validate a separate excitatory interneuron model, then connect it to L796 through AMPA/NMDA and Substance P/NK1 signalling.
