# L292-E1-LCN Passive Validation at 23 °C

**Stage status:** PASS  
**Overall excitatory-model status:** NOT READY — active, temperature, robustness, and synapse gates remain.

## Identity and scope

L292-E1-LCN (`NMO_34021`) is used as a rat Wistar lumbar lamina-I local-circuit interneuron morphology scaffold. Its molecular identity is unknown. This passive fit does not establish eTrC, PKCgamma, VGLUT3, DOR, SST, or CR marker identity.

The official standardized SWC was used unchanged. Its recorded SHA-256 is `65b44b3f94a93a77696ea31626073dd637250c48b0bae7d77bcaf9dfe654ea67`.

## Protocol

- NEURON 9.0.1, Python 3.10.20, fixed step.
- Temperature set to 23 °C before initialization.
- Baseline numerical settings: `dt = 0.025 ms`, `d_lambda = 0.1` at 100 Hz.
- Somatic current steps: 0, −0.005, −0.01, and −0.02 nA.
- Step timing: 200 ms onset, 500 ms duration, 900 ms total run.
- Passive mechanism only; no active conductance was used for fitting.

## Parameter fit

| Parameter | Starting value | Final value | Reason | Evidence level |
|---|---:|---:|---|---|
| `e_pas` | −65 mV | −65 mV | Starting value produced the target resting voltage; no adjustment needed | C: Medlock-derived, consistent with project SDH target |
| `g_pas` | 4.2e-5 S/cm² | 2.9e-5 S/cm² | Leak-only fit required to bring reconstructed-cell Rin into 100–400 MΩ while retaining tau in 10–30 ms | D: reconstruction-specific fit validated against project targets |
| `Ra` | 150 Ω·cm | 150 Ω·cm | Retained supported starting value | C: Medlock/project reference |
| `cm` | 1.0 µF/cm² | 1.0 µF/cm² | Retained standard supported value | C: Medlock/project reference |

Intermediate preserved trials:

- `g_pas=4.2e-5`: Rin 72.905 MΩ (fail), tau 20.125 ms (pass).
- `g_pas=3.0e-5`: Rin 97.539 MΩ (slightly below gate), tau 28.475 ms (pass).
- `g_pas=2.9e-5`: Rin 100.453 MΩ and tau 29.475 ms (pass).

## Final passive measurements

All three hyperpolarizing steps produced the same values to displayed precision, confirming linearity.

| Metric | Result | Target/gate | Status |
|---|---:|---:|---|
| Resting membrane potential | −65.000 mV | −65 to −55 mV | PASS |
| Input resistance | 100.453 MΩ | 100–400 MΩ | PASS |
| Membrane time constant | 29.475 ms | 10–30 ms | PASS |
| Input capacitance estimate (`1000*tau/Rin`) | 293.421 pF | descriptive | RECORDED |
| Post-step recovery error, −0.005 nA | −0.00248 mV | absolute error ≤0.1 mV | PASS |
| Spontaneous spikes | 0 | 0 | PASS |
| Evoked spikes during passive steps | 0 | 0 | PASS |

## Numerical morphology validation

| Check | Result | Status |
|---|---:|---|
| NEURON section count | 950 | RECORDED |
| Soma sections | 1 | PASS |
| Dendrite sections | 446 | PASS |
| Axon sections | 503 | PASS |
| Total `nseg` at `d_lambda=0.1` | 4,234 | RECORDED |
| Minimum segment diameter | 0.190 µm | valid/positive | PASS |
| Maximum segment electrotonic fraction | 0.099871 | ≤0.1 | PASS |
| Root | one soma section | PASS |
| One connected morphology | true | PASS |
| All dendrites connected | true | PASS |
| All axons connected | true | PASS |
| Unreachable sections | 0 | PASS |

The static SWC QA reports 951 unbranched chains, whereas NEURON Import3D produces 950 sections because of soma representation. Both checks find one connected morphology, and this difference is not treated as lost neurite cable.

## Convergence

The strict matrix covered all combinations of:

- `dt = 0.05, 0.025, 0.0125 ms`
- `d_lambda = 0.2, 0.1, 0.05`

Against the 0.025-ms/0.1 baseline:

- Worst absolute Rin change: 0.01745%.
- Worst absolute tau change: 0.08482%.
- Worst absolute RMP change: 0 mV.
- All configured spatial criteria passed.
- `nseg` ranged from 2,534 to 7,614.

The ≤1% metric-change and ≤0.1 mV RMP/recovery tolerances are project numerical acceptance proposals, not experimental measurements.

## Artifacts

- Accepted parameters: `parameters/common/passive_23C.json`
- Final summary: `results/23C/passive/final_strict_dlambda/summary.json`
- Passive summary CSV: `results/23C/passive/final_strict_dlambda/metrics.csv`
- Voltage traces: `results/23C/passive/final_strict_dlambda/trace_*.csv`
- Trace/F-I SVG: `results/23C/passive/final_strict_dlambda/validation.svg`
- Strict convergence: `results/23C/passive/convergence_strict_dlambda/convergence.csv`

## Gate decision

The 23 °C passive stage is accepted. This authorizes active eTrC validation; it does not authorize population, synapse, 35 °C, or network readiness claims.
