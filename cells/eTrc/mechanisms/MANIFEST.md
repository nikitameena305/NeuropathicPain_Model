# Mechanism manifest

All MOD files are unmodified package-local copies from the repository's Medlock/ModelDB 267056 mechanism set. They are included so `cells/eTrc/` runs independently in both target repositories. Generated NMODL build products are not tracked.

| File | Role in final model | Audit outcome |
|---|---|---|
| `B_NA.mod` | **Retained** fast Na current in soma and model-defined proximal native-axon domain | Required for an overshooting AP. Source computes `tadj = 3^((celsius-23)/10)`, but gate tau uses `tau_factor`; rates are effectively temperature-independent. Tables are disabled in the runner to avoid stale parameter-dependent values. |
| `B_DR.mod` | **Retained** delayed-rectifier K current in soma and proximal native-axon domain | Required for repolarization/recovery. Source computes `tadj` but never applies it to rates; kinetics are effectively temperature-independent. Tables are disabled. |
| `B_A.mod` | Tested rapid A-current; rejected | Q10=3 relative to 23°C is applied to gate kinetics. Restrained densities shifted rest and rheobase without fixing latency; larger densities silenced the model. |
| `HH2.mod` | Tested basic Na/K comparator; rejected | Q10=3 relative to 36°C is applied to gate taus. Useful densities were tonic; high-K apparent single-spike regimes failed the depolarization-block/recovery screen. |
| `iCaL.mod` | Tested only as the Ca source in a KCa comparator; rejected | L-type, not T-type; Q10=3 relative to 23.5°C. Not retained. |
| `CaIntraCellDyn.mod` | Tested only with iCaL/iKCa; rejected | Ca handling was included whenever KCa was tested. Not retained. |
| `iKCa.mod` | Medlock-supported comparator; rejected | Q10=3 relative to 22°C. Did not provide a necessary, stable transient phenotype. Not retained. |

Final density, distribution, provenance, and reversal-potential values are stored in `../parameters/eTrC_NMO109005_final_35C.json`.

