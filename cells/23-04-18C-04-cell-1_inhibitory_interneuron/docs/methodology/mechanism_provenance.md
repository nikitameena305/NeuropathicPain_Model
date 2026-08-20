# Mechanism provenance and equations

## Baseline decision

The final baseline contains only `pas`, `l571_na`, and `l571_kdr`. This is the smallest tested set that can generate repetitive firing in the imported reconstruction. SK, voltage-gated calcium, HCN/Ih, A-type potassium, and persistent sodium are excluded because no quantitative observation in the selected evidence set requires them and each would add weakly constrained states.

## Reused kinetic implementations

No MOD file is duplicated. `l571_na.mod` and `l571_kdr.mod` are loaded from `cells/L571_inhibitory_interneuron/mechanisms/`. Their names are historical; Cell 1 uses only their audited equations, not L571 conductance values.

### Fast sodium (`l571_na`)

- Current: `ina = gnabar * m^3 * h * (v - ena)`.
- Rate-equation origin: Medlock et al. ModelDB accession 267056 `B_NA.mod`, itself citing the Melnick dorsal-horn model lineage.
- States: activation `m`, inactivation `h`.
- Reversal: 60 mV (model assumption).
- Temperature: only `tau_m` and `tau_h` are divided by `Q10^((T-Tref)/10)`; steady-state gates and maximal conductance do not change.
- Final Q10/Tref: 3 / 23 C.

### Delayed rectifier (`l571_kdr`)

- Current: `ik = gkbar * n^4 * h * (v - ek)`.
- Rate-equation origin: Medlock ModelDB accession 267056 `KDRI.mod`.
- States: activation `n`, inactivation `h`.
- Reversal: -84 mV (model assumption).
- Temperature: `tau_n` and `tau_h` are divided by the same explicit Q10 factor; steady states and maximal conductance do not change.
- Final Q10/Tref: 3 / 23 C.

## Density distribution

| Region | Na (S/cm2) | KDR (S/cm2) | Classification |
|---|---:|---:|---|
| Soma | 0.006 | 0.003 | MODEL-FITTED |
| Dendrites | 0 | 0.002 | MODEL-FITTED/ASSUMED distribution |
| Proximal 30 um of native axon | 0.4 | 0.03 | MODEL-FITTED; MODEL-DEFINED AIS proxy |
| Distal reconstructed axon | 0.02 | 0.01 | MODEL-FITTED/ASSUMED distribution |

The proximal region is not anatomically confirmed as an AIS. The native incomplete axon is retained; no synthetic section is added. Robustness testing shows that making the axon passive or shortening the enriched region to 15 um abolishes firing at 120 pA, and a 10% global Na reduction reduces the response from 30 to 2 spikes. Consequently, the active solution is biologically provisional.

## Numerical compilation

The unchanged dependency compiled successfully with NEURON 9.0.1 using `nrnivmodl`. Generated `x86_64/` products are ignored and are not part of the deliverable.
