# NMO_260150 NPFF eCR-like interneuron model

This folder contains one deterministic NEURON model of **100521A-S14_set5_cell11 (NMO_260150)**. Its real biological identity is an **NPFF-positive superficial dorsal-horn excitatory vertical interneuron**. It is used as a biologically informed analogue of the Medlock eCR population; CR/calretinin identity is **not experimentally demonstrated**.

## Evidence boundaries

- **Exact cell:** NeuroMorpho morphology and metadata only. The record is mouse, adult, superficial laminae I-II dorsal horn, excitatory vertical, NPFF-positive, with dendrites and soma but no axon.
- **Morphology population:** Quillet et al. reconstructed 30 Brainbow-labelled, pro-NPFF-immunoreactive cells. Virtually all were vertical cells, every reconstruction had more ventral than dorsal dendritic length, and the reported spine density was 30.7 +/- 3.7 per 100 um.
- **Electrophysiology population:** recordings targeted GFP-positive/mCherry-negative cells in NPFFCre;GRPRFlp mice. The patched cells were not individually confirmed post hoc as pro-NPFF-positive; the authors called them NPFF cells “for convenience.” These measurements are therefore **NPFFCre-targeted / GRPRFlp-excluded population evidence**, not exact-cell data.
- **Network mapping:** eCR-like is a computational mapping, not a biological cell-type claim.
- **35 C results:** temperature-translated model predictions constrained by room-temperature population electrophysiology, not direct validation at 35 C.

Primary biology: Quillet et al. (2023), *Scientific Reports* 13:5891, [doi:10.1038/s41598-023-32720-3](https://doi.org/10.1038/s41598-023-32720-3). Exact morphology metadata are preserved in `evidence/neuromorpho_NMO_260150_metadata.json` from the [NeuroMorpho API](https://neuromorpho.org/api/neuron/id/260150).

## Final model

The native reconstruction is represented by one soma and 64 maximal-unbranched dendritic sections. There is no reconstructed axon and no synthetic AIS. NeuroMorpho marks the reconstruction `No Diameter`; the standardized CNG SWC radius profile is therefore retained only as **model-defined nominal geometry**, with +/-20% global sensitivity tests. It is not reported as measured anatomy.

Uniform passive parameters are Ra = 225 ohm cm, cm = 0.5 uF/cm2, g_pas = 3.6e-5 S/cm2, and e_pas = -59 mV. The final active set is deliberately minimal:

- `B_Na`: fast sodium; 0.12 S/cm2 soma and 0.0048 S/cm2 dendrite.
- `B_DR`: delayed-rectifier potassium; 0.30 S/cm2 soma and 0.030 S/cm2 dendrite.
- `B_A`: rapid A-type potassium representation; 0.005 S/cm2 soma, absent from dendrites.
- `Ih_Kole`: HCN current; 5.7e-5 S/cm2 uniformly in soma and dendrites.

No slow A-current, T-type calcium, Ca/KCa adaptation, synaptic bombardment, Y1 receptor mechanism, axon, or AIS is included. Densities are fitted model parameters, not measurements from NMO_260150.

At 35 C, the model predicts RMP -59.06 mV, current-step Rin 664.99 MOhm, rheobase 20 pA, threshold -40.25 mV, first-spike latency 12.62 ms, base width 1.95 ms, AP height 60.54 mV, and AHP -35.87 mV. The one-minute zero-current baseline is silent; the rheobase response is tonic, recovery passes, and no depolarization block occurs at 100 pA. Tonic firing is present in 30.8% of the measured population. The preferred delayed target was not reproduced and was not forced. Modeled capacitance is 18.45 pF versus 10.58 +/- 2.2 pF; that mismatch is retained because lowering cm below 0.5 uF/cm2 or tuning an unmeasured diameter was rejected.

## Reproduce

Requirements: Python 3, NEURON 9.x, a C/C++ toolchain, `nrnivmodl`, NumPy, SciPy, and Matplotlib. The runner compiles the four portable MOD sources into the operating-system temporary directory; no platform binary is committed.

```bash
python cells/eCR/scripts/run_eCR_final.py --dry-run
python cells/eCR/scripts/run_eCR_final.py
```

The second command runs the one-minute baseline, exact 0-100 pA scan in 5 pA increments, channel protocol, 23 C comparison, and 13-case robustness suite. Outputs use deterministic fixed-step integration and require no random seed.

## Folder guide

- `morphology/`: untouched depositor DAT plus the NeuroMorpho standardized CNG SWC.
- `mechanisms/`: the four portable MOD sources only.
- `parameters/`: passive, reference-condition active, and final 35 C configurations.
- `scripts/`: morphology QA, passive fit, active fit, one helper, and the single final runner.
- `results/`: structured JSON and reusable CSV traces.
- `figures/`: five original model/QA figures; no paper figure was copied.
- `evidence/`: exact metadata, provenance, and source-to-model evidence matrix.
- `report/`: complete Markdown and rendered/verified Word reports.

## Readiness

Status is **PARTIAL**. The model is reproducible and numerically robust as an intrinsic, tonic 35 C prediction, but it is **not network-ready** under the project gate: capacitance and delayed-latency targets are unmet, there is no reconstructed axon, and synapse unit tests have not been performed. See `report/eCR_NMO260150_COMPLETE_REPORT.md` for the full audit.
