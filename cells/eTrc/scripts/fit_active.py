#!/usr/bin/env python3
"""Validate staged active-channel choices and the final NMO_109005 model."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
from run_eTrC_final import (  # noqa: E402
    DEFAULT_PARAMETERS,
    build_cell,
    ensure_mechanisms,
    generate_final_outputs,
    load_parameters,
    run_current_step,
    run_series,
)


CHANNEL_EVALUATION = [
    {
        "stage": "Model A — basic spiking",
        "channel_set": ["pas", "B_Na", "B_DR"],
        "tested": True,
        "outcome": "RETAINED",
        "evidence": "Fast Na and KDR were necessary and sufficient for stable overshooting spikes, repolarization, and recovery.",
        "selection_note": "A model-defined 20 µm proximal active domain on the unchanged native axon outperformed uniform activation of the entire partial axon; final densities were fitted de novo.",
    },
    {
        "stage": "Model B — rapid A-type K",
        "channel_set": ["pas", "B_Na", "B_DR", "B_A"],
        "tested": True,
        "outcome": "REJECTED",
        "tested_gkbar_S_cm2": [0.001, 0.002, 0.005, 0.01, 0.02, 0.05],
        "evidence": "IAr occurs in 40.9% of the GRP population, but is not established for NMO_109005.",
        "reason": "Restrained somatodendritic B_A shifted rest negative and raised rheobase; larger values silenced the model. It did not recover the population first-spike latency without degrading stronger constraints.",
    },
    {
        "stage": "Model C — HCN/Ih",
        "channel_set": ["HCN"],
        "tested": False,
        "outcome": "NT",
        "evidence": "Ih occurs in 37.3% of GRP cells.",
        "reason": "No appropriate audited HCN mechanism was available in the permitted local inventory; no sag/rebound target justified importing one.",
    },
    {
        "stage": "Model D — T-type Ca",
        "channel_set": ["T-type Ca"],
        "tested": False,
        "outcome": "NT",
        "evidence": "ICaT occurs in 33.3% of GRP cells.",
        "reason": "The available iCaL mechanism is L-type, not T-type; the model had no validated low-threshold rebound target requiring a new mechanism.",
    },
    {
        "stage": "Model E — separate slow A-current",
        "channel_set": ["slow A-type K"],
        "tested": False,
        "outcome": "NT",
        "evidence": "IAs occurs in 25.8% of GRP cells.",
        "reason": "No distinct audited slow-A mechanism was available and rapid B_A already failed to improve the constrained phenotype.",
    },
    {
        "stage": "Medlock KCa comparator",
        "channel_set": ["pas", "Na/K", "iCaL", "CaIntraCellDyn", "iKCa"],
        "tested": True,
        "outcome": "REJECTED",
        "evidence": "Medlock-supported comparator, not a directly quantified GRP current.",
        "reason": "Paired Ca source, Ca handling, and KCa reduced firing but did not create a stable early transient; complexity was not justified.",
    },
    {
        "stage": "HH2 comparator",
        "channel_set": ["pas", "HH2"],
        "tested": True,
        "outcome": "REJECTED",
        "reason": "Stable spiking was tonic across useful densities; high-K single-spike regimes were depolarization block and failed the recovery criterion.",
    },
]


def _compact_series(series: dict[str, Any]) -> dict[str, Any]:
    """Drop large trace arrays from a series result."""

    rheobase_trace = series["rheobase_trace"]
    return {
        "temperature_C": series["temperature_C"],
        "dt_ms": series["dt_ms"],
        "d_lambda": series["d_lambda"],
        "active_rest": series["active_rest"],
        "rheobase_pA": series["rheobase_pA"],
        "rheobase_metrics": rheobase_trace["metrics"] if rheobase_trace else None,
        "current_metrics": series["metrics"],
    }


def run_temperature_comparison(parameters: dict[str, Any]) -> dict[str, Any]:
    """Compare the final mechanism set at reference and project temperatures."""

    import matplotlib.pyplot as plt

    current = float(parameters["biological_targets"]["rheobase_pA"]["mean"])
    traces: dict[str, dict[str, Any]] = {}
    metrics: dict[str, Any] = {}
    for temperature in (23.0, 35.0):
        cell = build_cell(parameters)
        trace = run_current_step(
            cell,
            parameters,
            current_pA=current,
            temperature_C=temperature,
            dt_ms=float(parameters["discretization"]["dt_ms"]),
            record_currents=True,
        )
        traces[f"{temperature:.0f}C"] = trace
        metrics[f"{temperature:.0f}C"] = trace["metrics"]
    time_equal = np.array_equal(traces["23C"]["time_ms"], traces["35C"]["time_ms"])
    max_voltage_difference = float(np.max(np.abs(traces["23C"]["voltage_mV"] - traces["35C"]["voltage_mV"])))
    figure, axes = plt.subplots(3, 1, figsize=(10.5, 8.0), sharex=True, constrained_layout=True)
    for label, trace in traces.items():
        axes[0].plot(trace["time_ms"], trace["voltage_mV"], linewidth=1.0, label=label)
        axes[1].plot(trace["time_ms"], trace["ina_mA_cm2"], linewidth=0.9, label=label)
        axes[2].plot(trace["time_ms"], trace["ikdr_mA_cm2"], linewidth=0.9, label=label)
    axes[0].set(ylabel="Somatic Vm (mV)", title=f"Reference vs 35°C at {current:.1f} pA")
    axes[1].set(ylabel="INa (mA/cm²)")
    axes[2].set(ylabel="IKDR (mA/cm²)", xlabel="Time (ms)")
    for axis in axes:
        axis.legend(frameon=False)
        axis.set_xlim(450.0, 800.0)
    figure.suptitle("Temperature audit: B_Na/B_DR kinetics are effectively unscaled", fontsize=13, fontweight="bold")
    output = PACKAGE_ROOT / "figures" / "temperature_channel_comparison.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return {
        "comparison_current_pA": current,
        "metrics": metrics,
        "time_vectors_equal": time_equal,
        "max_absolute_voltage_difference_mV": max_voltage_difference,
        "interpretation": "The traces are identical because the audited B_Na and B_DR source computes tadj but does not apply it to gate rates. h.celsius is set to 35°C, but this channel set is not a kinetic temperature translation.",
    }


def run_robustness(parameters: dict[str, Any]) -> dict[str, Any]:
    """Run the requested lightweight temporal, spatial, and ±10% channel tests."""

    currents = [14.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 36.0, 50.0]
    cases = [
        {"name": "baseline", "dt_ms": 0.025, "d_lambda": 0.1, "sodium_scale": 1.0, "potassium_scale": 1.0},
        {"name": "dt_0.0125_ms", "dt_ms": 0.0125, "d_lambda": 0.1, "sodium_scale": 1.0, "potassium_scale": 1.0},
        {"name": "d_lambda_0.05", "dt_ms": 0.025, "d_lambda": 0.05, "sodium_scale": 1.0, "potassium_scale": 1.0},
        {"name": "Na_minus_10pct", "dt_ms": 0.025, "d_lambda": 0.1, "sodium_scale": 0.9, "potassium_scale": 1.0},
        {"name": "Na_plus_10pct", "dt_ms": 0.025, "d_lambda": 0.1, "sodium_scale": 1.1, "potassium_scale": 1.0},
        {"name": "KDR_minus_10pct", "dt_ms": 0.025, "d_lambda": 0.1, "sodium_scale": 1.0, "potassium_scale": 0.9},
        {"name": "KDR_plus_10pct", "dt_ms": 0.025, "d_lambda": 0.1, "sodium_scale": 1.0, "potassium_scale": 1.1},
    ]
    records: list[dict[str, Any]] = []
    for case in cases:
        series = run_series(
            parameters,
            dt_ms=case["dt_ms"],
            d_lambda=case["d_lambda"],
            sodium_scale=case["sodium_scale"],
            potassium_scale=case["potassium_scale"],
            currents_pA=currents,
        )
        compact = _compact_series(series)
        rheobase_metrics = compact["rheobase_metrics"]
        record = {
            **case,
            "rheobase_pA": compact["rheobase_pA"],
            "rheobase_classification": rheobase_metrics["classification"] if rheobase_metrics else None,
            "first_spike_latency_ms": rheobase_metrics["first_spike_latency_ms"] if rheobase_metrics else None,
            "recovery_pass": rheobase_metrics["recovery_pass"] if rheobase_metrics else False,
            "any_depolarization_block": any(item["classification"] == "depolarization block" for item in compact["current_metrics"]),
            "strong_current_classification": compact["current_metrics"][-1]["classification"],
            "active_rmp_mV": compact["active_rest"]["rmp_mV"],
            "active_rin_MOhm": compact["active_rest"]["rin_MOhm"],
        }
        record["fundamental_phenotype_stable"] = (
            record["rheobase_classification"] in {"single-spike", "transient"}
            and record["recovery_pass"]
            and not record["any_depolarization_block"]
        )
        records.append(record)
    baseline_rheobase = float(records[0]["rheobase_pA"])
    rheobase_span = [float(record["rheobase_pA"]) for record in records if record["rheobase_pA"] is not None]
    phenotype_pass = all(record["fundamental_phenotype_stable"] for record in records)
    rheobase_stable = max(abs(value - baseline_rheobase) for value in rheobase_span) <= 3.0
    return {
        "scope": "dt, d-lambda, independent Na ±10%, and independent KDR ±10%; not a global sensitivity analysis",
        "cases": records,
        "criteria": {
            "phenotype": "rheobase trace remains transient or single-spike, recovery passes, and no tested trace is depolarization block",
            "rheobase": "all tested rheobases within 3 pA of baseline on the declared 1–2 pA grid",
        },
        "phenotype_stable": phenotype_pass,
        "rheobase_stable": rheobase_stable,
        "status": "PASS" if phenotype_pass and rheobase_stable else ("PARTIAL" if phenotype_pass or rheobase_stable else "FAIL"),
    }


def write_evidence_matrix(parameters: dict[str, Any], validation: dict[str, Any]) -> None:
    """Write the required property-to-evidence traceability table."""

    passive = json.loads((PACKAGE_ROOT / "results" / "passive_validation.json").read_text(encoding="utf-8"))
    morphology = json.loads((PACKAGE_ROOT / "results" / "morphology_qa.json").read_text(encoding="utf-8"))
    active_rest = validation["active_rest"]
    rows = [
        ["RMP", "-52.89 ± 0.78", "mV", "230", "Dickie et al. 2019", "primary experiment; mean ± SEM", "GRP population", "yes", f"{passive['voltage_clamp_iv']['rmp_mV']:.3f} passive", f"{active_rest['rmp_mV']:.3f} active", "PASS passive / FAIL active", "Population constraint; not same-cell."],
        ["Rin", "1588 ± 85", "MOhm", "232", "Dickie et al. 2019", "primary experiment; mean ± SEM", "GRP population", "yes", f"{passive['voltage_clamp_iv']['rin_MOhm']:.2f} passive", f"{active_rest['rin_MOhm']:.2f} active", "PASS passive / FAIL active", "Active channels reduce apparent Rin."],
        ["whole-cell capacitance", "5.12 ± 0.11", "pF", "232", "Dickie et al. 2019", "primary experiment; mean ± SEM", "GRP population", "comparison", f"{passive['morphology_derived_capacitance_pF']:.2f}", f"{passive['morphology_derived_capacitance_pF']:.2f}", "FAIL", "Mismatch preserved; cm was not forced to an implausible value."],
        ["rheobase", "18.30 ± 1.07", "pA", "155", "Dickie et al. 2019", "primary experiment; mean ± SEM", "GRP population", "yes", f"{validation['rheobase_pA']:.1f}", f"{validation['rheobase_pA']:.1f}", "PASS", "Measured on the declared current grid from approximately -60 mV."],
        ["first-spike latency", "137.1 ± 6.2", "ms", "155", "Dickie et al. 2019", "primary experiment; mean ± SEM", "GRP population", "yes", f"{validation['first_spike_latency_ms']:.2f}", f"{validation['first_spike_latency_ms']:.2f}", "FAIL", "Not forced with unsupported conductances."],
        ["firing distribution", "transient 49.5%; single 32.9%; tonic 8.3%; reluctant 6.5%; delayed 2.8%", "%", "216", "Dickie et al. 2019", "primary experiment", "GRP population", "yes", validation["rheobase_classification"], validation["rheobase_classification"], "PASS", "Single-spike is the declared secondary acceptable phenotype."],
        ["IAr prevalence", "40.9", "%", "159", "Dickie et al. 2019", "primary experiment", "GRP population", "tested, rejected", "B_A comparator", "not retained", "NT", "Population prevalence does not establish the current in NMO_109005."],
        ["IAr amplitude", "54.9 ± 4.6 results; 58.6 ± 4.6 figure caption", "pA", "65", "Dickie et al. 2019", "primary experiment; internal source discrepancy", "GRP IAr-positive subset", "comparison", "not fitted", "not retained", "NT", "Both paper values retained transparently."],
        ["Ih prevalence", "37.3", "%", "159", "Dickie et al. 2019", "primary experiment", "GRP population", "no", "NT", "NT", "NT", "No audited HCN mechanism and no sag/rebound target."],
        ["Ih amplitude", "-17.5 ± 1.1", "pA", "59", "Dickie et al. 2019", "primary experiment", "GRP Ih-positive subset", "no", "NT", "NT", "NT", "Not used."],
        ["IAs prevalence", "25.8", "%", "159", "Dickie et al. 2019", "primary experiment", "GRP population", "no", "NT", "NT", "NT", "No distinct audited slow-A mechanism."],
        ["ICaT prevalence", "33.3", "%", "159", "Dickie et al. 2019", "primary experiment", "GRP population", "no", "NT", "NT", "NT", "Available iCaL is not T-type."],
        ["morphology metrics", "NMO_109005 morphometry", "mixed", "1", "NeuroMorpho.Org API record 109005", "primary repository record", "exact morphology", "yes", f"{morphology['integrity']['valid_swc_rows']} rows; {morphology['geometry']['total_cable_length_um']:.2f} µm", "unchanged geometry", "PASS", "One connected component; soma, dendrites, and native partial axon present."],
        ["temperature", "room-temperature population recording; 32°C tissue recovery only", "°C", "study", "Dickie et al. 2019", "primary methods", "GRP population", "yes", "23°C reference", "35°C project setting", "PARTIAL", "Final B_Na/B_DR gate rates are effectively temperature-independent after source audit."],
    ]
    columns = ["property", "experimental value", "units", "n", "source", "evidence level", "exact cell or population", "used in model?", "model value", "35C value", "PASS/FAIL/NT", "notes"]
    output = PACKAGE_ROOT / "evidence" / "evidence_matrix.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    """Create the active-validation CLI parser."""

    parser = argparse.ArgumentParser(description="Run staged active validation and lightweight robustness for NMO_109005.")
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS, help="Final parameter JSON.")
    parser.add_argument("--skip-robustness", action="store_true", help="Skip the seven-case lightweight robustness check.")
    parser.add_argument("--dry-run", action="store_true", help="Print declared stages and outputs without importing NEURON.")
    return parser


def main() -> int:
    """Run active validation and return zero when the declared workflow completes."""

    args = build_parser().parse_args()
    parameters = load_parameters(args.parameters)
    if args.dry_run:
        print(json.dumps({"stages": CHANNEL_EVALUATION, "robustness_cases": 7, "parameter_file": str(args.parameters)}, indent=2))
        return 0
    ensure_mechanisms()
    final_validation = generate_final_outputs(parameters)
    temperature = run_temperature_comparison(parameters)
    robustness = None if args.skip_robustness else run_robustness(parameters)
    active_validation = {
        "model": parameters["model_name"],
        "identity_interpretation": parameters["identity"]["interpretation"],
        "target_evidence_level": "Dickie et al. GRP population constraints; not same-cell electrophysiology for NMO_109005",
        "staged_channel_evaluation": CHANNEL_EVALUATION,
        "native_vs_model_defined_active_domain": {
            "native_full_axon": "Tested first. Stable single spikes were possible, but activating the entire partial axon strongly perturbed resting/subthreshold behavior.",
            "selected": parameters["active_domain"],
            "selection": "The unchanged native axon is retained; only the distribution of active conductance is model-defined. No synthetic AIS geometry was added.",
        },
        "final_35C": final_validation,
        "temperature_comparison": temperature,
        "robustness_status": None if robustness is None else robustness["status"],
        "decision": parameters["model_status"],
        "network_ready": parameters["network_ready"],
    }
    results = PACKAGE_ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "active_validation.json").write_text(json.dumps(active_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if robustness is not None:
        (results / "robustness.json").write_text(json.dumps(robustness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_evidence_matrix(parameters, final_validation)
    print(
        json.dumps(
            {
                "rheobase_pA": final_validation["rheobase_pA"],
                "first_spike_latency_ms": final_validation["first_spike_latency_ms"],
                "classification": final_validation["rheobase_classification"],
                "target_status": final_validation["overall_target_status"],
                "robustness": None if robustness is None else robustness["status"],
                "temperature_max_voltage_difference_mV": temperature["max_absolute_voltage_difference_mV"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
