# Morphology provenance: NMO_260150

## Exact record

- NeuroMorpho ID: `NMO_260150`
- Cell name: `100521A-S14_set5_cell11`
- Archive: Todd
- Species/age: mouse, adult
- Region: spinal cord, superficial dorsal horn, laminae I-II
- Cell type: interneuron; excitatory; vertical; NPFF-positive
- Domains: soma and dendrites; **no axon**
- Physical integrity: dendrites complete
- Metadata attributes: `No Diameter`, `3D`, `Angles`
- Primary paper: Quillet et al. 2023, DOI 10.1038/s41598-023-32720-3, PMID 37041197
- API record: https://neuromorpho.org/api/neuron/id/260150

## Preserved files and checksums

| File | Role | SHA-256 |
|---|---|---|
| `NMO_260150_100521A-S14_set5_cell11_original.dat` | Untouched depositor-original Neurolucida DAT | `D8387F323ED6AD558B0513B797031F34681C36CC2666E50E84DB75F4E372B684` |
| `NMO_260150_100521A-S14_set5_cell11_standardized.CNG.swc` | NeuroMorpho standardized CNG SWC used by NEURON | `AC078EE88E43CC9831544BE2242C24AC6212D26CF7C9A237A3597314A5E27F7F` |

The depositor original is DAT, not SWC. The filenames intentionally distinguish provenance so the standardized derivative is never mislabeled as the original reconstruction.

## Geometry policy and QA

The standardized SWC contains 1,297 nodes: 3 soma and 1,294 dendrite nodes. It has one root and one connected component, 32 branch points, 33 dendritic endpoints, 1,331.73 um dendritic cable length, and a maximum root-path distance of 171.63 um. QA found no orphan nodes, duplicate-coordinate groups, zero-length segments, nonpositive radii, or axon nodes.

NeuroMorpho explicitly marks this record `No Diameter`. The radii present in the standardized SWC are therefore preserved as **model-defined nominal geometry**, not treated as measured diameters. The active/passive fit never adjusts them. The final robustness suite applies only global 0.8x, 1.0x, and 1.2x scales and labels these as sensitivity cases.

The standardized coordinate extents are X = 102.85 um, Y = 241.40 um, and Z = 49.99 um. These coordinates provide a useful visual QA projection, but the anatomical ventral direction is established from depositor/paper metadata rather than inferred from the CNG plot alone.
