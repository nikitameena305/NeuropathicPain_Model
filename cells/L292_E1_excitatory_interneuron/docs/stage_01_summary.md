# Stage 1 summary: evidence and morphology QA

## What was done

- Created the isolated `exc_interneuron/` tree without changing `L796/`.
- Audited Medlock paper and executed ModelDB source at a pinned commit.
- Downloaded and hash-pinned the official standardized L292-E1-LCN SWC and official standardization logs.
- Implemented and ran dependency-free morphology QA and a three-view morphology plot.
- Implemented a reusable morphology-first `RatLCN_L292E1` importer with d-lambda discretization after Ra/cm assignment.
- Copied only the required Medlock mechanisms into this isolated directory and audited their temperature behavior.

## Passed

- Rat / spinal cord / lumbar / lamina I / local-circuit metadata confirmed.
- Soma, dendrite, and axon domains present.
- One root; no missing parents, unreachable nodes, graph cycles, zero-length edges, nonpositive radii, or >20-um non-soma diameter flags.
- Axon type transition found at node 3771 from soma node 1; this is not automatically labeled an AIS.
- eTrC and common delayed Medlock rules extracted exactly; the five non-eTrC rules are parameter-identical.

## Failed or unavailable

- The official original Neurolucida `.dat` link returned a zero-byte payload on 2026-08-11. The invalid payload was not retained.
- No L292-E1-specific molecular/transmitter phenotype or intrinsic electrophysiology was found.
- No NEURON simulation result is accepted at this stage.

## Uncertain

- Whether L292-E1-LCN is excitatory.
- Whether its first axonal section contains a biological AIS.
- Reconstructed distal-axon channel distribution.
- Numeric target values for L292-specific Rin, tau, rheobase, AP threshold, half-width, and AHP.

## Next recommended action

Compile the isolated mechanism set, run passive-only validation at 23°C, and accept or adjust only passive parameters before attempting the eTrC active rule.
