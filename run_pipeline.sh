#!/bin/bash
set -e

echo "Step 1: Morphology check"
python scripts/01_check_morphology.py

echo "Step 2: Passive sweep"
python scripts/02_passive_sweep.py

echo "Step 3: Active sweep with eFEL"
python scripts/03_active_sweep_efel.py

echo "Step 4: Plot best candidate"
python scripts/04_plot_best_candidate.py

echo "DONE. Check results/ and figures/"
