# External source collections before import

These local collections are treated as read-only sources. No source file is deleted or modified by the consolidation.
Generated caches/build products are excluded from Git; all exclusions remain in their original local folders.

## Collections

- `L292`: `C:\Users\Nikita\NeuropathicPain_Model\exc_interneuron` -> `cells/L292_E1_excitatory_interneuron`
- `L571`: `C:\Users\Nikita\OneDrive\Documents\Neuron\inhibitory_interneuron_L571-LCN` -> `cells/L571_inhibitory_interneuron`
- `GRP-reference`: `C:\Users\Nikita\NeuropathicPain_Model\L796\interneurons` -> `archive/other_exploratory_models/GRP_14-1-15-A-A2sep_and_candidates`
- `L796-history`: `C:\Users\Nikita\NeuropathicPain_Model\reports` -> `archive/L796/historical_audits`
- `Medlock-scaffold`: `C:\Users\Nikita\OneDrive\Documents\Neuron\sdh-excitatory-interneurons` -> `external/medlock_267056_excitatory_scaffold`

## Decisions

- `deduplicate against shared mechanisms`: 4
- `exclude`: 71
- `move/import`: 601

The complete file-level audit, including SHA-256 values, is in `source_collections_before_import.csv`.
Exact duplicate groups within and across the collections are in `source_collection_duplicate_audit.csv`.
