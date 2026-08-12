#!/usr/bin/env bash
set -e

echo "Running L796 validation pipeline..."

mkdir -p results/ap_features figures/ap_features validation/ap_features validation/ais_soma figures/validation reports

echo "1. AIS-soma summary during stimulus window..."
python scripts/make_AIS_soma_summary_stim_window.py

echo "2. Convert AIS-soma summary to markdown..."
python - <<'PY'
import pandas as pd
inp = "validation/ais_soma/L796_step5_AIS_soma_summary_STIM_WINDOW.csv"
out = "validation/ais_soma/L796_step5_AIS_soma_summary_STIM_WINDOW.md"
df = pd.read_csv(inp)
for col in ["mean_AIS_lead_ms", "mean_AIS_minus_soma_peak_mV", "max_soma_peak_mV", "max_AIS_peak_mV"]:
    df[col] = df[col].round(3)
df.to_markdown(out, index=False)
print(df.to_markdown(index=False))
PY

echo "3. Extracting somatic AP features..."
python scripts/extract_step5_somatic_AP_features.py

echo "4. Making model validation table..."
python scripts/make_model_validation_table.py

echo "5. Copying final validation outputs to reports..."
cp validation/ais_soma/L796_step5_AIS_soma_summary_STIM_WINDOW.csv reports/
cp validation/ais_soma/L796_step5_AIS_soma_summary_STIM_WINDOW.md reports/
cp validation/ap_features/L796_model_vs_literature_validation_table.csv reports/
cp validation/ap_features/L796_model_vs_literature_validation_table.md reports/

echo "Validation complete."
