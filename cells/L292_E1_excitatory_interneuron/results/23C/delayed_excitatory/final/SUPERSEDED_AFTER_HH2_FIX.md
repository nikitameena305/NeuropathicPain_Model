# Superseded after HH2 numerical fix

This validation passed its configured gates, but the subsequent temperature
runtime probe exposed removable `0/0` singularities in the released `HH2.mod`
rate equations. The equations were made numerically safe with their analytic
limits and mechanisms were recompiled.

This directory is retained for provenance. The accepted rerun is stored in
`../final_after_HH2_singularity_fix/`.
