# Pre-fit modeling decisions

1. The original SWC is immutable and imported directly; no cleaned or rescaled morphology is created.
2. Native morphology is tested first. No synthetic axon is manufactured.
3. The passive primary target is adult PV-population input resistance, 225 +/- 22 MOhm at 21-24 C.
4. The 10.9 +/- 0.6 pF whole-cell capacitance is a comparison gate, not a license to use implausible `cm`.
5. Because the selected source does not report unforced RMP, -60 mV is treated as the experimental holding condition, not a biological RMP measurement.
6. `Ra`, `cm`, `e_pas`, and `g_pas` are explicitly model-assumed or model-fitted.
7. The first active model contains only leak, fast Na, and delayed-rectifier K. Additional mechanisms require either an experimental observation or a preserved minimal-model failure.
8. Existing validated project channel kinetics may be reused to avoid unnecessary MOD duplication, but all Cell 1 densities and distributions are fitted independently.
9. Experimental-temperature validation is performed at 23 C, centered in the reported 21-24 C room-temperature range. Results at 35 C are labeled model predictions.
10. Randomness is not required for deterministic single-cell protocols; any future stochastic protocol must declare and store a seed.
