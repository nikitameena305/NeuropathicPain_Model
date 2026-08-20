# Morphology provenance: NMO_170087

## Identity and acquisition

- **NeuroMorpho ID:** NMO_170087
- **Deposited name:** 23-04-18C-04-cell-1
- **Downloaded:** 2026-08-13
- **Record:** https://neuromorpho.org/neuron_info.jsp?neuron_name=23-04-18C-04-cell-1
- **Standardized SWC:** https://neuromorpho.org/dableFiles/hughes/CNG%20version/23-04-18C-04-cell-1.CNG.swc
- **Stored original:** `morphology/primary/23-04-18C-04-cell-1.CNG.swc`
- **SHA256:** `e2ecaffc1ebcf9c88b72224fa4172aa93dfb013edb3ad40ee2bfadebe06ec915`

The archive identifies the reconstruction as a mouse Pvcre, parvalbumin-reporter-positive, Pax2-positive inhibitory interneuron from lumbar dorsal horn laminae II-III. The source is Gradwell et al. (2022; DOI 10.1097/j.pain.0000000000002422; PMID 34326298; PMCID PMC8832545).

## Reconstruction context and limitations

Gradwell et al. used Cre-dependent Brainbow labeling in PVCre mice, 60-um sagittal sections, and Neurolucida reconstruction. NeuroMorpho records soma, dendrite, and axon domains, but grades dendrites **Moderate** and the axon **Incomplete**. It also carries the archive attribute **No Diameter**. Thus the deposited radii are computational inputs supplied by the standardized archive, not direct evidence of complete native diameters.

The archive sex field is `Male/Female` and the exact reconstructed cell's sex is unresolved. Likewise, `young adult` and 20-30 g describe the archive/cohort context rather than a uniquely linked animal record.

## Transformation ledger

The checksum-protected downloaded SWC remains the sole biological source morphology. A separately stored parser-clean model copy removes blank lines only; it retains every comment and SWC data row in its original order and changes no coordinate, parent identifier, type, or radius. The exact transformation and both checksums are stored in `morphology/provenance/model_swc_transformation.json`. This prevents repeated NEURON Import3D warnings without silently changing geometry.

The model imports the parser-clean copy at runtime with NEURON Import3D, which converts SWC nodes to NEURON sections in memory. Section subdivision with the d-lambda rule is a numerical discretization choice and does not rewrite either SWC.

No synthetic axon is added. The native, incomplete reconstructed axon is retained. Any proximal-axon sodium-density enrichment is explicitly a **MODEL-DEFINED spike-initiation proxy**, not an anatomically confirmed AIS.

## Structural QA outcome

The source has one root, one connected component, no orphan nodes, no duplicate coordinates or records, no zero-length segments, and no non-positive radii. This is a structural pass only. It does not override the archive's moderate-dendrite and incomplete-axon flags or establish biophysical validity.

Generated source-preserving QA outputs are under `results/morphology_qa/` and `figures/morphology/`.
