# Passive-property evidence and pre-fit decision

| Quantity | Best available target | Protocol and temperature | Evidence | Modeling decision |
|---|---:|---|---|---|
| Input resistance | 225 +/- 22 MOhm | 5-mV, 10-ms voltage-clamp step from -70 mV; adult PV cells; 21-24 C | Same PV population, population mean | Primary passive target |
| Whole-cell capacitance | 10.9 +/- 0.6 pF | Same protocol and cohort | Same PV population, population mean | Comparison gate; do not force with implausible `cm` |
| Membrane time constant | Not reported | Not available | Missing | Do not invent; report model prediction |
| Resting membrane potential | Not reported in the primary Gradwell target cohort | Cells were held at -60 mV in current clamp | Missing | Do not call -60 mV RMP |
| Hyperpolarizing response | No numerical amplitude reported for a matching pulse | Current-clamp steps were 800 ms; figures include responses | Same population, qualitative | Use standardized -20 pA, 800-ms engineering probe and report trace |
| Sag | No quantitative baseline target in the selected Gradwell adult table | Not available | Missing | No HCN in minimal baseline; report observed model sag |

## Gate and restrained ranges

- Input resistance acceptance: model within the reported mean +/- one SEM (203-247 MOhm).
- Whole-cell capacitance comparison: PASS only if the model-equivalent capacitance is within the reported mean +/- one SEM without requiring `cm < 0.5` or `cm > 1.5 uF/cm2`; otherwise preserve and label the failure.
- Candidate axial resistivity: 80-150 ohm cm (model assumption and sensitivity parameter).
- Candidate specific capacitance: 0.5-1.5 uF/cm2 (model assumption; no direct source-cell measurement).
- Leak reversal: chosen to stabilize the experimental holding condition near -60 mV; not presented as measured RMP.
- Leak conductance: fitted to input resistance for each restrained `Ra`/`cm` combination.

This decision was fixed before passive fitting. It prevents the model from using an implausibly low specific capacitance merely to reproduce an electrode-derived whole-cell capacitance estimate that may omit electrically remote reconstructed membrane.
