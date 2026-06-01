# Computational Neuropathic Pain Model using NEURON

This repository contains Week 1 work for a summer research project on computational modelling of neuropathic pain using the NEURON Simulation Environment.

## Focus

DRG-Spinal Dorsal Horn circuit modelling with emphasis on GABAergic inhibitory dorsal horn mechanisms.

## Week 1 Completed

- NEURON/Python environment setup
- Ball-and-stick action potential demonstration
- Simplified DRG normal vs neuropathic-like prototype
- Simplified SDH normal vs neuropathic-like prototype
- ModelDB 267056 SDH firing output analysis
- ModelDB 2018004 AP parameter extraction and mechanism inventory
- NeuroMorpho DRG/SDH candidate morphology table
- Morphology decision and fallback logic
- Required 5-point paper summaries
- Advanced conceptual GABA disinhibition sweep

## Biological idea

Neuropathic pain involves abnormal excitability and central sensitization. In the SDH, reduced GABAergic/glycinergic inhibition can amplify pain signalling. This project uses NEURON-based modelling to explore how DRG input and SDH inhibitory balance affect output firing.

## Main folders

- `python/` — analysis and simulation scripts
- `figures/` — generated plots
- `results/` — processed CSV/TXT outputs
- `submission_week1/week1/` — final Week 1 deliverables
- `deliverables/advanced/` — advanced exploratory outputs
- `notes/` — summaries and documentation
- `logs/` — command/output logs

## Note

Large raw ModelDB, SWC, and environment files are ignored from Git and kept locally.
