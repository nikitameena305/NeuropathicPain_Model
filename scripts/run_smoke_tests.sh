#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
smoke_dir="$(mktemp -d)"
trap 'rm -rf -- "$smoke_dir"' EXIT

cd "$repo_root/shared/mechanisms/medlock_267056"
nrnivmodl

cd "$repo_root/cells/L571_inhibitory_interneuron/mechanisms"
nrnivmodl

cd "$repo_root"
python cells/L796_projection_neuron/scripts/smoke_test_L796.py --run

python cells/L292_E1_excitatory_interneuron/scripts/validate_single_cell.py \
  --config cells/L292_E1_excitatory_interneuron/parameters/eTrC/eTrC_final_35C.json \
  --output-dir "$smoke_dir/l292" \
  --current-steps-nA -0.02 0.0 0.88

python cells/L571_inhibitory_interneuron/scripts/run_L571.py \
  --config cells/L571_inhibitory_interneuron/parameters/L571_final_23C.json \
  --current 0.1 \
  --output "$smoke_dir/l571.json"

echo "All three single-cell smoke tests completed."
