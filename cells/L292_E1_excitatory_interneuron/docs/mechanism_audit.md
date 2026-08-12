# Active mechanism and temperature audit

Source snapshot: ModelDB 267056 commit `6286892a9e7aa67ad80f2c5d86007350f900c644`. The canonical sources are consolidated at repository path `shared/mechanisms/medlock_267056/`; the original L292 import manifest is retained as `docs/MANIFEST.txt` and the repository-wide manifest is in the shared directory. `HH2.mod` additionally contains the documented analytic singularity correction.

## Intrinsic mechanisms

| Channel / process | MOD file / suffix | Source and role | Location and released gmax | Reference temperature / Q10 | Celsius and TABLE audit | Evidence |
|---|---|---|---|---|---|---|
| Fast Na | `B_NA.mod` / `B_Na` | Melnick-style Na; eTrC spike initiation and small delayed contribution | eTrC soma 0.3066, hillock 5.147; delayed soma 0.0001652, hillock 0.03 S/cm2 | Code calculates nominal Q10=3 from 23°C | `tadj` is updated from celsius and is a TABLE dependency, but tau divides by `tau_factor`, not `tadj`; therefore celsius does not actually scale kinetics in this released file unless `tau_factor` changes. This is a source-code finding, not a repair. | C |
| Traub Na+K | `HH2.mod` / `HH2` | Traub & Miles/Destexhe; core delayed firing AP currents | Delayed dend gNa 0, gK 0.144; soma 0.08548/0.0043; hillock 0.02375/0.304 S/cm2 | 36°C, Q10=3 | Uses celsius in `tadj`; no TABLE; discrete update depends on global `dt` | C |
| A-type K | `borgka.mod` / `borgka` | Borg-Graham type adapted to sympathetic preganglionic-neuron data; creates/determines delay in Medlock rule | eTrC dend/soma/hillock 0.0001584/0.04957/0.0005; delayed 0.0009333/0.0109/0.112 S/cm2 | Q10=3 from 30°C; rate exponent also contains absolute temperature | No TABLE; celsius affects both rate scaling and voltage-dependent exponential factors | C; biological transfer to L292 is D |
| Inactivating KDR | `KDRI.mod` / `KDRI` | Melnick-style n4h potassium current | eTrC dend/soma/hillock 0.2061/1.06e-5/0.2171; delayed 9.6e-6/0.000111/0.01547 S/cm2 | PARAMETER says 37°C, but Q10 code is commented out | TABLE depends on dt and celsius even though rate functions use fixed `tau_factor=1`; changing celsius rebuilds equivalent values rather than applying a correction | C |
| Slow Ca-dependent K | `iKCa.mod` / `iKCa` | Slow AHP current, coupled to basal calcium dynamics | Soma and dendrite 0.002 S/cm2 in both excitatory rules | 22°C, Q10=3 | No TABLE; celsius changes tau; lower bound `taumin=0.1 ms` | C |
| Calcium concentration | `CaIntraCellDyn.mod` / `CaIntraCellDyn` | Destexhe calcium shell/removal process | depth 0.1 um; cai_inf 50 nM; tau 1 ms soma, 2 ms dendrite | No temperature correction | No TABLE and no celsius use | C |
| Passive leak | built-in `pas` | Sets e_pas and g_pas | eTrC 4.2e-5; delayed 9.6e-7 S/cm2 in simplified model | No kinetic Q10 | Conductance itself is not temperature-scaled | C; reconstructed fit required |

The released eTrC rule includes `HH2` with zero Na and K density. The reconstructed configuration omits that zero-current mechanism rather than implying a functional channel.

## Synaptic mechanisms

`AMPA_DynSyn`, `NMDA_DynSyn`, `GABAa_DynSyn`, `Glycine_DynSyn`, and `NK1_DynSyn` do not use `celsius`. NetPyNE overrides several MOD defaults; validation must test the configured NetPyNE values, not only mechanism defaults.

| Mechanism | MOD defaults (rise/decay ms, reversal mV) | Executed network override |
|---|---|---|
| AMPA | 0.1 / 5, 0 | 0.1 / 5 |
| NMDA | 5 / 70, 0 | 2 / 100 |
| GABA_A | 1 / 20, −80 | 0.1 / 20, −70 |
| Glycine | 1 / 10, −70 | 0.1 / 10, −70 |
| NK1 | 10 / 5000, 0 | 100 / 1000 or 200 / 3000 |

## 35°C gate

No universal Q10 will be applied. Before creating a 35°C parameter set:

1. eTrC and delayed 23°C models must pass their single-cell gates.
2. `B_Na` and `KDRI` celsius behavior must be treated as released-code behavior unless a separately named, source-documented repair is proposed and validated.
3. `HH2`, `borgka`, and `iKCa` must be revalidated independently because they use different reference temperatures and implementations.
4. `CaIntraCellDyn`, passive leak, and the synaptic mechanisms have no kinetic temperature correction in these files; any added correction would be an explicit assumption.
5. Results must be labeled **temperature-translated model** unless direct matching 35°C data are found.
