#!/usr/bin/env bash
set -e

ROOT="$HOME/NeuropathicPain_Model"
MODEL="$ROOT/modeldb/267056"
PROJECT="$ROOT/project1"

mkdir -p "$PROJECT/data/direct_runs"
mkdir -p "$PROJECT/results/direct_runs"
mkdir -p "$PROJECT/figures/direct_runs"
mkdir -p "$PROJECT/logs"

cd "$MODEL"

for SCALE in 1.00 0.75 0.50 0.25 0.00
do
    LABEL=$(echo "$SCALE" | sed 's/\.//g')

    echo "=============================================="
    echo "Running direct NEURON SDH simulation"
    echo "GABA_SCALE = $SCALE"
    echo "=============================================="

    export GABA_SCALE="$SCALE"

    python init_mechanical.py 2>&1 | tee "$PROJECT/logs/gaba_scale_${LABEL}.log"

    if [ -f "$MODEL/data/100mN_data.json" ]; then
        cp "$MODEL/data/100mN_data.json" "$PROJECT/data/direct_runs/gaba_scale_${LABEL}_100mN_data.json"
        echo "Copied output to project1/data/direct_runs/gaba_scale_${LABEL}_100mN_data.json"
    else
        echo "WARNING: data/100mN_data.json not found after run."
    fi

    echo ""
done

echo "All direct GABA sweep runs completed."
