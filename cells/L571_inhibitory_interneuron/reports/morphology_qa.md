# L571-LCN morphology QA

The official NeuroMorpho standardized SWC was analysed without project-side repair, scaling, simplification, or shrinkage correction.

- SHA-256: `696b553d7c31f58f305c79e32bb05d14c7a385b48947b93518a9abe1c01b867f`
- SWC nodes: 10478 ({'soma': 5, 'axon': 8638, 'dendrite': 1835})
- Root count: 1; missing parents: 0; unreachable nodes: 0
- Branches (SWC graph definition): 340 ({'soma': 1, 'dendrite': 222, 'axon': 117})
- Bifurcations: 167; terminals: 174
- Dendritic length: 3086.01 µm
- Axonal length: 20997.30 µm
- Total edge length: 24113.71 µm
- Dendritic diameter range: {'min': 0.19, 'max': 3.71}
- Axonal diameter range: {'min': 0.19, 'max': 2.6}
- Soma point count: 5; soma bounds: {'x_min_um': -10.6563, 'x_max_um': 9.788400000000001, 'x_extent_um': 20.4447, 'y_min_um': -20.9716, 'y_max_um': 3.8938, 'y_extent_um': 24.865399999999998, 'z_min_um': -13.5884, 'z_max_um': 6.228400000000001, 'z_extent_um': 19.8168}
- Zero-length edges: 0; non-positive radii: 0
- Abrupt same-type diameter changes ≥2.5-fold: 47
- Axon origin: {'node': 1841, 'parent': 1, 'parent_type': 'soma', 'diameter_um': 1.67, 'first_edge_length_um': 28.13573350741011, 'coordinates_um': [-5.73, -35.83, -2.61]}

## Interpretation

The graph is a single connected tree containing soma, dendrites, and axon. The axon begins from soma node 1 through a 28.14 µm edge. This long first edge and the absence of an experimental ankyrin-G/myelin annotation mean that the proximal reconstructed axon is used only as an **AIS proxy**, not claimed as a histologically confirmed AIS.

The official NeuroMorpho standardization log reports 77 B1 warnings and no A, B2, or C irregularities. It explicitly records that no action was taken on the flagged radii, long segments, abrupt radius transitions, or the eight daughters of soma node 1. The project makes no additional repair. NeuroMorpho reports 90% z-axis shrinkage and no correction; coordinates remain as deposited.
