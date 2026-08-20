# L292-E1 parameter sets

## Current stage files

| Model/stage | Current file | Status |
|---|---|---|
| Passive 23 °C | `common/passive_23C.json` | PASS |
| eTrC 23 °C | `eTrC/eTrC_final_23C.json` | PASS with biological limitations |
| eTrC 35 °C | `eTrC/eTrC_final_35C.json` | PASS as a temperature-translated prediction |
| Delayed 23 °C | `common/delayed_excitatory_final_23C.json` | PASS with biological limitations |
| Delayed 35 °C | `common/delayed_excitatory_final_35C.json` | **FAILED GATE; retain as evidence** |

The remaining JSON files are historical mappings, area-preserving trials, mechanism-ablation diagnostics, or bounded one-factor tests. They are retained because they explain model development and the unresolved 35 °C depolarization block. Configuration inheritance uses `extends`; do not move an individual JSON without its parent chain.

All base configurations point to the canonical repository mechanism set at `shared/mechanisms/medlock_267056/`.

