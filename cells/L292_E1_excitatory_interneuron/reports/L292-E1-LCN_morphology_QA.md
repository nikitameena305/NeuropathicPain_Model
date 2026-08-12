# L292-E1-LCN morphology QA

> No morphology repair was performed. All values below describe the official NeuroMorpho standardized SWC as downloaded.

## Provenance

- File: `L292-E1-LCN.CNG.swc`
- SHA-256: `65b44b3f94a93a77696ea31626073dd637250c48b0bae7d77bcaf9dfe654ea67`
- NeuroMorpho ID: NMO_34021
- Species / strain: rat / Wistar
- Region: spinal cord; lumbar; lamina I
- Cell classification: interneuron; local circuit neuron; multipolar
- Structural domains: Dendrites, Soma, Axon
- Physical integrity: Dendrites & Axon Complete

## Geometry and topology

- SWC nodes: 17823
- Maximal same-type unbranched chains (reported here as SWC sections): 951
- Section counts by type: {"axon": 503, "dendrite": 446, "soma": 2}
- Branch points: 471
- Terminals: 480
- Dendritic length: 7652.190 um
- Axonal length: 35061.175 um
- Diameter ranges: {"axon": {"max_um": 2.78, "mean_um": 0.3040233402120544, "min_um": 0.19}, "dendrite": {"max_um": 4.64, "mean_um": 1.0382332624867163, "min_um": 0.19}, "soma": {"max_um": 24.54, "mean_um": 18.5959, "min_um": 13.3384}}
- Soma dimensions: {"point_count": 6, "x_um": 24.54, "y_um": 32.0673, "z_um": 41.597300000000004}
- Root nodes: [1]
- Missing-parent nodes: []
- Unreachable nodes: []
- Cycles: 0
- Zero-length edges: 0
- Nonpositive radii: 0
- Suspicious non-soma diameters: 0

## Axon origin audit

Candidate type-transition origins: `[{"axon_node_id": 3771, "euclidean_distance_from_soma_centre_um": 37.1255483685651, "parent_node_id": 1, "parent_type": "soma"}]`

A type-2 axon origin is anatomical evidence for an axonal transition, not proof that the first imported axonal section is an AIS. Any proximal initiation zone remains a computational candidate until channel localization and spike-initiation timing are validated.
