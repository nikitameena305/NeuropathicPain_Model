# Repository instructions

This repository is the isolated six-population SDH excitatory reproduction
scaffold derived from ModelDB 267056.

Preserve these scientific boundaries:

1. Keep `exemplar`, `smoke`, and `production` counts separate.
2. Treat the baseline as six population labels but two intrinsic rule
   contents.
3. Do not add morphology, conductance, synapse, or connectivity changes to the
   reproduction mode.
4. Put biological upgrades in a separately named mode and validate morphology,
   passive properties, active firing, and synapses before population scaling.
5. Do not infer numerical conductance density directly from expression data.
6. Keep source commit, citations, MOD hashes, seeds, and environment versions
   traceable.

All NEURON-dependent commands must retain a dry-run path. Run the unit tests,
compile the MOD files, and execute the six-cell exemplar before merging.
