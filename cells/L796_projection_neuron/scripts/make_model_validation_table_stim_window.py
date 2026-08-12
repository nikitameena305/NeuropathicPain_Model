import os
import pandas as pd

os.makedirs("validation/ap_features", exist_ok=True)

SUMMARY = "results/ap_features/L796_step5_somatic_AP_features_summary_STIM_WINDOW.csv"
AIS_SUMMARY = "validation/ais_soma/L796_step5_AIS_soma_summary_STIM_WINDOW.csv"

if not os.path.exists(SUMMARY):
    raise FileNotFoundError(f"Missing corrected AP summary: {SUMMARY}")

df = pd.read_csv(SUMMARY)

def get_at_current(current):
    row = df[df["current_pA"] == current]
    if len(row) == 0:
        return None
    return row.iloc[0]

row40 = get_at_current(40)
row60 = get_at_current(60)
row120 = get_at_current(120)

table = [
    {
        "Validation item": "Model identity",
        "Model result": "L796-ALT-PN reconstructed morphology",
        "Comparison source": "NeuroMorpho / Szucs archive",
        "Interpretation": "Direct morphology identity; active electrophysiology is not L796-specific",
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
        "Validation item": "Coarse rheobase",
        "Model result": "between 20 and 40 pA",
        "Comparison source": "Current Step 5 sweep",
        "Interpretation": "Needs fine rheobase sweep for exact value",
    },
]

if row40 is not None:
    table.append({
        "Validation item": "40 pA soma spike count",
        "Model result": f"{int(row40['soma_spike_count'])} spikes / 500 ms",
        "Comparison source": "Step 5 stimulus-window validation",
        "Interpretation": "Firing begins in the 20-40 pA range",
    })

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
            "Interpretation": "Secondary comparison only; Ruscheweyh is not L796-specific",
        },
        {
            "Validation item": "60 pA soma AP peak",
            "Model result": f"{row60['mean_soma_peak_mV']:.2f} mV",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Somatic AP peak is lower than AIS peak; compare cautiously",
        },
        {
            "Validation item": "60 pA soma AP amplitude",
            "Model result": f"{row60['mean_soma_AP_amplitude_mV']:.2f} mV",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Secondary active-property validation",
        },
        {
            "Validation item": "60 pA soma AP half-width",
            "Model result": f"{row60['mean_soma_half_width_ms']:.3f} ms",
            "Comparison source": "Ruscheweyh 2004 active AP comparison",
            "Interpretation": "Useful for active waveform comparison",
        },
        {
            "Validation item": "60 pA first-spike latency",
            "Model result": f"{row60['first_spike_latency_ms']:.2f} ms",
            "Comparison source": "Prescott/Luz firing-class logic",
            "Interpretation": "Supports delayed repetitive / tonic-like response",
        },
    ])

if row120 is not None:
    table.extend([
        {
            "Validation item": "120 pA soma spike count",
            "Model result": f"{int(row120['soma_spike_count'])} spikes / 500 ms",
            "Comparison source": "Step 5 stimulus-window validation",
            "Interpretation": "High-current firing saturates at 6 spikes",
        },
        {
            "Validation item": "120 pA recovery",
            "Model result": f"{row120['recovery_soma_mV']:.2f} mV",
            "Comparison source": "Internal stability criterion",
            "Interpretation": "High-current recovery remains close to resting potential",
        },
    ])

if os.path.exists(AIS_SUMMARY):
    ais = pd.read_csv(AIS_SUMMARY)
    table.append({
        "Validation item": "AIS-soma spike initiation",
        "Model result": f"AIS leads soma by about {ais['mean_AIS_lead_ms'].mean():.3f} ms",
        "Comparison source": "Model AIS-soma timing analysis",
        "Interpretation": "Supports AIS-dominant spike initiation in the model",
    })

out = pd.DataFrame(table)

csv_path = "validation/ap_features/L796_model_vs_literature_validation_table_STIM_WINDOW.csv"
md_path = "validation/ap_features/L796_model_vs_literature_validation_table_STIM_WINDOW.md"

out.to_csv(csv_path, index=False)
out.to_markdown(md_path, index=False)

print("\nCorrected validation table:\n")
print(out.to_string(index=False))
print(f"\nSaved CSV: {csv_path}")
print(f"Saved MD:  {md_path}")
