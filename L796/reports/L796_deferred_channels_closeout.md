# L796 deferred-channel closeout

## Purpose

This file closes the channel-complement stage. Deferred channels are not missing by mistake. They were deliberately not implemented because either:

1. no L796-specific target exists,
2. no vetted MOD file is available,
3. the required electrophysiological signature is absent,
4. the channel is not needed for the current modelling objective,
5. adding it would increase complexity without improving validation.

## Final decision

The current L796 model is closed as an excitability and synaptic-integration model.

It includes:

- passive leak
- fast Na+
- delayed rectifier K+
- persistent Na+ inherited from ModelDB base model
- L-type Ca2+ inherited from ModelDB base model
- calcium-activated K+
- CaAN/CAN
- calcium dynamics
- AMPA
- NMDA
- GABA-A
- glycine
- NK1/TACR1
- nAChR-like proxy

## Deferred channels

| Channel/receptor | Decision | Reason |
|---|---|---|
| A-type K+ | evaluated, kept at 0 S/cm2 | nonzero values broke rheobase/overshoot/amplitude or did not improve latency within bounds |
| T-type Ca2+ | deferred | no rebound burst/low-threshold spike; no vetted MOD |
| SK/BK KCa | deferred | generic KCa already covers AHP; no subtype-specific L796 target |
| N-type Ca2+ | deferred | presynaptic release not explicitly modelled |
| P/Q/R Ca2+ | deferred | no subtype-specific evidence or terminal model |
| HCN/Ih | deferred | no measured sag/resonance target for L796 |
| M-current/KCNQ | deferred | no pharmacological discriminating target |
| GABA-B/GIRK | deferred | slow inhibition not required for current project stage |
| Kainate | deferred | no AMPA-separated residual current |
| P2X | deferred | no vetted MOD in current mechanism set |
| 5-HT3 | deferred | no vetted MOD in current mechanism set |
| real nAChR | deferred | only Exp2Syn proxy used; real dorsal horn nAChR action is circuit/presynaptic |

## Completion statement

The L796 projection-neuron model is considered complete for:

- intrinsic excitability testing,
- ligand-gated synaptic response testing,
- normal vs neuropathic synaptic-condition comparison,
- future connection to a validated excitatory interneuron.

Remaining work belongs to future extensions, not to the current L796 closure.
