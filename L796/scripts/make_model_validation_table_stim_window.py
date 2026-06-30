import os
import pandas as pd

os.makedirs("validation/ap_features", exist_ok=True)

summary_path = "results/ap_features/L796_step5_somatic_AP_features_summary_STIM_WINDOW.csv"

df = pd.read_csv(summary_path)

def get_at_current(current):
    row = df[df["current_pA"] == current]
    if len(row) == 0:
        return None
    return row.iloc[0]

row60 = get_at_current(60)
row120 = get_at_current(120)

table = [
    {
        "Validation item": "Model identity",
        "Model result": "L796-ALT-PN reconstructed morphology",
        "Comparison source": "NeuroMorpho / Szucs archive",
        "Interpretation": "Direct morphology identity; exact active electrophysiology not cell-specific",
    },
    {
        "Validation item": "Passive RMP",
        "Model result": "about -72.8 mV",
        "Comparison source": "Luz, Szucs & Safronov 2014 PN group",
        "Interpretation": "Good passive target match",
    },
    {
        "Validation item": "Passive RIN",
        "Model result": "about 0.756-0.769 GOhm",
        "Comparison source": "Luz, Szucs & Safronov 2014 PN group",
        "Interpretation": "Good passive target match",
    },
    {
        "Validation item": "Rheobase",
        "Model result": "between 20 and 40 pA",
        "Comparison source": "Lamina I projection neuron literature",
        "Interpretation": "Needs fine rheobase sweep for exact value",
    },
]

if row60 is not None:
    table.extend([
        {
            "Validation item": "60 pA soma spike count",
            "Model result": f"{int(row60['soma_spike_count'])} spikes / 500 ms",
            "Comparison source": "Qualitative firing-class comparison",
            "Interpretation": "Repetitive tonic-like response",
        },
        {
            "Validation item": "60 pA soma AP threshold",
            "Model result": f"{row60['mean_soma_threshold_mV']:.2f} mV",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Secondary comparison; Ruscheweyh is not L796-specific",
        },
        {
            "Validation item": "60 pA soma AP peak",
            "Model result": f"{row60['mean_soma_peak_mV']:.2f} mV",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Use cautiously; somatic peak is lower than AIS peak",
        },
        {
            "Validation item": "60 pA soma AP half-width",
            "Model result": f"{row60['mean_soma_half_width_ms']:.3f} ms",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Use for secondary active validation",
        },
        {
            "Validation item": "60 pA first-spike latency",
            "Model result": f"{row60['first_spike_latency_ms']:.2f} ms",
            "Comparison source": "Prescott/Luz firing-class logic",
            "Interpretation": "Supports delayed repetitive / tonic-like response",
        },
    ])

if row120 is not None:
    table.append({
        "Validation item": "120 pA recovery",
        "Model result": f"{row120['recovery_soma_mV']:.2f} mV",
        "Comparison source": "Internal stability criterion",
        "Interpretation": "Checks high-current recovery near resting voltage",
    })

out = pd.DataFrame(table)

csv_path = "validation/ap_features/L796_model_vs_literature_validation_table_STIM_WINDOW.csv"
md_path = "validation/ap_features/L796_model_vs_literature_validation_table_STIM_WINDOW.md"

out.to_csv(csv_path, index=False)
out.to_markdown(md_path, index=False)

print(out.to_string(index=False))
print(f"\nSaved CSV: {csv_path}")
print(f"Saved MD:  {md_path}")
