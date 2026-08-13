# Temperature audit

The source current-clamp recordings were made at room temperature, reported as 21-24 C. The primary Cell 1 model is therefore evaluated at 23 C. This is an experimental-range model comparison, not evidence that the reconstructed cell itself was recorded.

Both active mechanisms use Q10 = 3 and Tref = 23 C with:

`rate_multiplier = Q10^((celsius - Tref) / 10)`

The multiplier accelerates gating time constants only. Maximal conductances, reversal potentials, passive conductance, and specific capacitance remain unchanged.

| Temperature | Interpretation | Rheobase | Spikes at 120 pA / 800 ms | AP half-width |
|---:|---|---:|---:|---:|
| 21 C | experimental-range model comparison | 50 pA | 27 | 1.25 ms |
| 23 C | primary model | 50 pA | 30 | 1.075 ms |
| 24 C | experimental-range model comparison | 50 pA | 32 | 1.00 ms |
| 35 C | **MODEL PREDICTION** | 150 pA | 0 | 0.625 ms at predicted rheobase |

There are no direct 35 C data in the selected PV evidence set. The loss of firing at 120 pA and increase in model rheobase to 150 pA demonstrate that the 35 C translation is not a validated physiological model and must not be used as if it were.
