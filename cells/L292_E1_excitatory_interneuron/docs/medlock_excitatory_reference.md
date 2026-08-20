# Medlock excitatory reference audit

This audit is based on the executed files `cells.py`, `cfg_mechanical.py`, and `netParams_mechanical.py` from [ModelDBRepository/267056](https://github.com/ModelDBRepository/267056) at commit `6286892a9e7aa67ad80f2c5d86007350f900c644`. The complete extracted dictionaries, hashes, synapses, and connection rules are stored in `parameters/common/medlock_modeldb_267056_reference.json`.

## Exact intrinsic-rule mapping

| Project label | ModelDB population | Count | Executed cell type | Intrinsic rule |
|---|---|---:|---|---|
| eTrC | TrC | 10 | EXib | `EXinitialRule` |
| ePKCgamma | PKC | 30 | PKC | `PKCRule` |
| eVGLUT3 | VGLUT3 | 4 | EXdl | `EXdelayedRule` |
| eDOR | DOR | 30 | EXdl | `EXdelayedRule` |
| eSST | SOM | 15 | SOM | `SOMRule` |
| eCR | CR | 20 | CR | `CRRule` |

After removing NetPyNE `conds`, `PKCRule`, `SOMRule`, and `CRRule` are parameter-identical to `EXdelayedRule`. Therefore the released code has **two excitatory intrinsic phenotypes**, not six molecularly distinct conductance sets.

## Released simplified geometry

All excitatory rules use three cylinders, not reconstructed SWCs:

| Compartment | L (um) | Diameter (um) | nseg | Ra (ohm cm) | cm (uF/cm2) |
|---|---:|---:|---:|---:|---:|
| Soma | 20 | 20 | 3 | 150 | 1 |
| Dendrite | 400 | 3 | 5 | 150 | 1 |
| Hillock | 9 | 1.5 | 3 | 150 | 1 |

The dendrite connects to soma(0), and the hillock connects to soma(1). The released code calls the latter `hillock`; the paper describes it as an AIS. Neither label proves that a reconstructed axon section is anatomically an AIS.

## eTrC / `EXinitialRule` conductance densities

Units are S/cm2 except where noted.

| Mechanism parameter | Dendrite | Soma | Hillock |
|---|---:|---:|---:|
| `pas.g` | 4.2e-5 | 4.2e-5 | 4.2e-5 |
| `pas.e` (mV) | −65 | −65 | −65 |
| `B_Na.gnabar` | absent | 0.3066 | 5.147 |
| `B_Na.alpha_shift` (mV) | — | 6.713 | 6.713 |
| `B_Na.beta_shift` (mV) | — | 9.906 | 9.906 |
| `HH2.gnabar` | 0 | 0 | 0 |
| `HH2.gkbar` | 0 | 0 | 0 |
| `borgka.gkabar` | 0.0001584 | 0.04957 | 0.0005 |
| `KDRI.gkbar` | 0.2061 | 1.06e-5 | 0.2171 |
| `iKCa.gbar` | 0.002 | 0.002 | absent |
| Ca removal tau (ms) | 2 | 1 | absent |

The Medlock paper defines the computational target as 1–2 spikes within 100 ms of current onset.

## Common delayed rule for the other five populations

| Mechanism parameter | Dendrite | Soma | Hillock |
|---|---:|---:|---:|
| `pas.g` | 9.6e-7 | 9.6e-7 | 9.6e-7 |
| `pas.e` (mV) | −65 | −65 | −65 |
| `B_Na.gnabar` | absent | 0.0001652 | 0.03 |
| `HH2.gnabar` | 0 | 0.08548 | 0.02375 |
| `HH2.gkbar` | 0.144 | 0.0043 | 0.304 |
| `HH2.vtraub` (mV) | −50.2 | −50.2 | −50.2 |
| `borgka.gkabar` | 0.0009333 | 0.0109 | 0.112 |
| `KDRI.gkbar` | 9.6e-6 | 0.000111 | 0.01547 |
| `iKCa.gbar` | 0.002 | 0.002 | absent |
| Ca removal tau (ms) | 2 | 1 | absent |

The delayed phenotype explicitly contains both `borgka` A-type current and `KDRI`; this was confirmed from source rather than inferred from channel names. The paper target is decreasing first-spike latency with increasing current. It reports delayed-neuron spike height of 107 mV from starting voltage.

## Temperature and numerical protocol

| Item | Paper | Executed ModelDB source |
|---|---|---|
| Temperature | 37°C | `cfg.hParams['celsius'] = 36` |
| Integration step | 25 us | `cfg.dt = 0.025 ms` |
| Initial voltage | not an experimental RMP | `v_init = −60 mV` |
| Network duration | 5 s | 5000 ms |
| Current injection | Somatic IClamp; conductances tuned across current intensities | No reusable single-cell IClamp amplitude/duration series is present in the released network config |

This project reports the 36/37°C mismatch instead of merging it. The 23°C reconstruction is a source-temperature model derived from the 22–24°C morphology experiment, not an exact Medlock reproduction.

## Synaptic mechanisms in the executed source

| Label | MOD mechanism | Rise (ms) | Decay (ms) | Reversal (mV) | Notes |
|---|---|---:|---:|---:|---|
| AMPA | `AMPA_DynSyn` | 0.1 | 5 | 0 | Dynamic presynaptic state |
| NMDA | `NMDA_DynSyn` | 2 | 100 | 0 | Mg block; values override MOD defaults |
| NK13 | `NK1_DynSyn` | 100 | 1000 | 0 | Used for eSST/eCR to pNK1 |
| NK23 | `NK1_DynSyn` | 200 | 3000 | 0 | Separate configured NK1 timescale |
| GABA | `GABAa_DynSyn` | 0.1 | 20 | −70 | Values override MOD defaults |
| GLY | `Glycine_DynSyn` | 0.1 | 10 | −70 | Rise overrides MOD default |

All released connection rules use probability 0.2 and dendritic location 0.5. Exact weights and delays are retained in the machine-readable reference. Rule counts by excitatory population are:

| Population | Input receptor rules | Output receptor rules |
|---|---:|---:|
| TrC | 4 | 4 |
| PKC | 8 | 5 |
| VGLUT3 | 4 | 6 |
| DOR | 6 | 4 |
| SOM/eSST | 16 | 3 |
| CR | 14 | 3 |

Notable executed-source paths include C-peptidergic/nonpeptidergic AMPA input to TrC; A-beta SAI/SAII AMPA+NMDA input to PKC and VGLUT3; A-delta AMPA+NMDA input to DOR, SOM, and CR; and eSST/eCR AMPA+NMDA+NK1 output to pNK1. These statements describe the released computational network, not independently confirmed synapses on L292-E1-LCN.
