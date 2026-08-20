# Mechanism provenance and temperature audit

Only four final mechanisms are retained. Conductance densities were fitted locally against NPFF-targeted population constraints and were not copied from source models.

| Mechanism | Ion/role | Source | Local modification | Distribution/density (S/cm2) | Temperature handling | Reason retained |
|---|---|---|---|---|---|---|
| `B_Na` | Na; spike upstroke | `shared/mechanisms/medlock_267056/B_NA.mod`, ModelDB 267056 | File/suffix capitalization made consistent; `ena` moved from `PARAMETER` to `ASSIGNED` for NEURON 9 compatibility; kinetics unchanged | soma 0.12; dendrite 0.0048 | `tadj=3^((celsius-23)/10)` is declared in a rates table but not applied to taus; effective source scaling is none, Tref declaration 23 C | Minimal fast sodium mechanism needed for AP generation |
| `B_DR` | K; delayed rectification/repolarization | `shared/mechanisms/medlock_267056/B_DR.mod`, ModelDB 267056 | `ek` moved from `PARAMETER` to `ASSIGNED`; kinetics unchanged | soma 0.30; dendrite 0.030 | `tadj` is declared but not used in the rate equations; effective source scaling is none, Tref declaration 23 C | Minimal delayed rectifier needed for stable repetitive spiking and recovery |
| `B_A` | K; model representation of rapid IA | `shared/mechanisms/medlock_267056/B_A.mod`, ModelDB 267056 | `ek` moved from `PARAMETER` to `ASSIGNED`; kinetics unchanged | soma 0.005; dendrite 0 | Q10 = 3 for activation/inactivation kinetics, Tref = 23 C | Population evidence: IAr in 10/16 cells; selected density gives 178.1 pA versus 165.7 +/- 80.3 pA. Exact-cell expression is unknown |
| `Ih_Kole` | mixed cation/HCN; subthreshold Ih | ModelDB 149100 mechanism derived from Kole et al. 2006 | Suffix renamed for namespace clarity; removable singularity guarded numerically; kinetics unchanged | soma and dendrite 5.7e-5 | No `celsius`, Q10, or Tref term in this source | Population evidence: Ih in 11/16 cells; selected density gives -10.72 pA versus -10.9 +/- 5.0 pA. Exact-cell expression is unknown |

The source HCN study is Kole, Hallermann & Stuart (2006), *Journal of Neuroscience* 26:1677-1687, DOI [10.1523/JNEUROSCI.3664-05.2006](https://doi.org/10.1523/JNEUROSCI.3664-05.2006). It supplies a published mechanism candidate, not dorsal-horn or NMO_260150 expression evidence.

## Rejected mechanisms

- Slow IA: observed in only 4/16 cells and not required after rapid IA/HCN testing.
- T-type Ca: explicitly absent from all 16 tested NPFF-targeted cells.
- Ca/KCa: not required for stable APs, recovery, or block avoidance.
- Synaptic/Y1/TRPV1 mechanisms: evidence is recorded for future network work but is not an intrinsic-cell fitting target.
- Synthetic AIS: not required for excitability; the exact morphology has no reconstructed axon.

## Portable-build audit

All four MOD sources compiled with NEURON 9.0.2 using `nrnivmodl` with zero compiler warnings after the compatibility declarations above. Compiled `x86_64` output is excluded; `run_eCR_final.py` builds and loads a hash-keyed library under the operating-system temporary directory.
