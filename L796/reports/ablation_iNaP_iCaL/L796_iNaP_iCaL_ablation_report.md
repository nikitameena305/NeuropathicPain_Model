# L796 iNaP / iCaL ablation-control test

## Purpose

This test checks whether persistent Na (`iNaP`) and L-type Ca (`iCaL`) are necessary for the final L796 validation targets.

## Variants tested

- A: final model as-is

- B: CaL reduced from fitted 1.25 scale to ModelDB base scale 1.0

- C: CaL removed

- D: iNaP removed

- E: both CaL and iNaP removed

## Required pass criteria

- RMP between -76 and -70 mV

- Rin between 0.60 and 1.00 GOhm

- no spontaneous firing at 0 pA

- rheobase between 20 and 60 pA

- AP overshoot between +5 and +30 mV

- AP amplitude between 70 and 78 mV


## Summary table

| variant                 | CaL_operation   |   CaL_factor |   CaL_params_changed | iNaP_operation   |   iNaP_params_changed |   RMP_mV |   Rin_GOhm | spontaneous_at_0pA   |   rheobase_pA |   spikes_0pA |   spikes_20pA |   spikes_40pA |   spikes_60pA |   spikes_80pA |   spikes_100pA |   spikes_120pA |   threshold_mV |   peak_mV |   overshoot_mV |   amplitude_mV |   half_width_ms |   AHP_min_mV |   first_spike_latency_ms | pass_RMP   | pass_Rin   | pass_no_spontaneous   | pass_rheobase   | pass_overshoot   | pass_amplitude   |   required_pass_count | required_pass_all   |
|:------------------------|:----------------|-------------:|---------------------:|:-----------------|----------------------:|---------:|-----------:|:---------------------|--------------:|-------------:|--------------:|--------------:|--------------:|--------------:|---------------:|---------------:|---------------:|----------:|---------------:|---------------:|----------------:|-------------:|-------------------------:|:-----------|:-----------|:----------------------|:----------------|:-----------------|:-----------------|----------------------:|:--------------------|
| A_final_as_is           | none            |        nan   |                  380 | none             |                     1 | -72.5929 |   0.684248 | False                |           100 |            0 |             0 |             0 |             0 |             0 |              1 |              8 |       -42.9387 |   20.8387 |        20.8387 |        63.7774 |           0.675 |     -78.342  |                  149.425 | True       | True       | True                  | False           | True             | False            |                     4 | False               |
| B_CaL_ModelDB_scale_1p0 | scale           |          0.8 |                  380 | none             |                     1 | -72.5978 |   0.68467  | False                |           100 |            0 |             0 |             0 |             0 |             0 |              1 |              8 |       -42.8683 |   20.7736 |        20.7736 |        63.6419 |           0.65  |     -78.437  |                  149.575 | True       | True       | True                  | False           | True             | False            |                     4 | False               |
| C_CaL_removed           | zero            |        nan   |                  380 | none             |                     1 | -72.6171 |   0.686328 | False                |           100 |            0 |             0 |             0 |             0 |             0 |              1 |              8 |       -43.0095 |   20.478  |        20.478  |        63.4875 |           0.65  |     -78.9202 |                  150.15  | True       | True       | True                  | False           | True             | False            |                     4 | False               |
| D_iNaP_removed          | none            |        nan   |                  380 | zero             |                     1 | -72.642  |   0.687129 | False                |           100 |            0 |             0 |             0 |             0 |             0 |              1 |              1 |       -42.6513 |   19.6595 |        19.6595 |        62.3108 |           0.675 |     -78.2824 |                  152.2   | True       | True       | True                  | False           | True             | False            |                     4 | False               |
| E_CaL_and_iNaP_removed  | zero            |        nan   |                  380 | zero             |                     1 | -72.6659 |   0.689075 | False                |           100 |            0 |             0 |             0 |             0 |             0 |              1 |              1 |       -42.527  |   19.1955 |        19.1955 |        61.7225 |           0.65  |     -78.8341 |                  153.175 | True       | True       | True                  | False           | True             | False            |                     4 | False               |

## Interpretation rule

- If variant B passes all required criteria, CaL can be described as compatible with ModelDB base scale 1.0.

- If variant B fails but A passes, keep final CaL scale 1.25 and describe it as a fitted conductance.

- If C, D, or E pass, those channels are not strictly required for the present validation target set, but removing them would still require full receptor and neuropathic revalidation.


## Output files

- `/home/nikita/NeuropathicPain_Model/L796_temp23_test/results/ablation_iNaP_iCaL/L796_iNaP_iCaL_ablation_summary.csv`

- `/home/nikita/NeuropathicPain_Model/L796_temp23_test/figures/ablation_iNaP_iCaL/L796_iNaP_iCaL_ablation_FI_curves.png`

- `/home/nikita/NeuropathicPain_Model/L796_temp23_test/figures/ablation_iNaP_iCaL/L796_iNaP_iCaL_ablation_40pA_traces.png`
