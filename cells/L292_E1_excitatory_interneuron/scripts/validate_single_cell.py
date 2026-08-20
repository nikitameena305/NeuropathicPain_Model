"""Run deterministic passive or active validation on RatLCN_L292E1."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import platform
import statistics
from pathlib import Path
from typing import Any, Sequence

from rat_lcn import IDENTITY_STATEMENT, RatLCN_L292E1, load_model_config


def neuron_available() -> bool:
    """Check whether the NEURON Python module is importable.

    Args:
        None.

    Returns:
        True when NEURON can be imported.

    Example:
        ``if neuron_available(): ...``
    """

    return importlib.util.find_spec("neuron") is not None


def mean_in_window(times: Sequence[float], values: Sequence[float], *, start_ms: float, stop_ms: float) -> float:
    """Calculate a trace mean over a closed-open time interval.

    Args:
        times: Sample times in milliseconds.
        values: Samples corresponding to ``times``.
        start_ms: Window start.
        stop_ms: Window end.

    Returns:
        Arithmetic mean over selected samples.

    Example:
        ``baseline = mean_in_window(t, v, start_ms=100, stop_ms=150)``
    """

    selected = [value for time, value in zip(times, values) if start_ms <= time < stop_ms]
    if not selected:
        raise ValueError(f"no samples in [{start_ms}, {stop_ms}) ms")
    return statistics.fmean(selected)


def first_crossing_index(values: Sequence[float], *, level: float, start_index: int = 1) -> int | None:
    """Find the first upward crossing of a voltage level.

    Args:
        values: Voltage samples.
        level: Crossing level in millivolts.
        start_index: First candidate sample index.

    Returns:
        Crossing index, or None.

    Example:
        ``index = first_crossing_index(trace, level=0.0)``
    """

    for index in range(max(1, start_index), len(values)):
        if values[index - 1] < level <= values[index]:
            return index
    return None


def spike_crossings(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    start_ms: float,
    stop_ms: float,
    level_mV: float = 0.0,
) -> list[int]:
    """Detect spike up-crossings in a time window.

    Args:
        times: Sample times.
        voltages: Voltage samples.
        start_ms: Detection-window start.
        stop_ms: Detection-window end.
        level_mV: Spike detection level.

    Returns:
        Sample indices of detected spikes.

    Example:
        ``indices = spike_crossings(t, v, start_ms=200, stop_ms=700)``
    """

    return [
        index
        for index in range(1, len(voltages))
        if start_ms <= times[index] < stop_ms and voltages[index - 1] < level_mV <= voltages[index]
    ]


def local_peak_index(voltages: Sequence[float], *, crossing_index: int, stop_index: int) -> int:
    """Find the voltage peak following a detected spike crossing.

    Args:
        voltages: Voltage samples.
        crossing_index: Up-crossing sample.
        stop_index: Exclusive search limit.

    Returns:
        Index of the maximum voltage.

    Example:
        ``peak = local_peak_index(v, crossing_index=index, stop_index=index + 200)``
    """

    stop = max(crossing_index + 1, min(stop_index, len(voltages)))
    return max(range(crossing_index, stop), key=lambda index: voltages[index])


def threshold_index(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    peak_index: int,
    search_start_index: int,
    derivative_threshold_mV_ms: float = 10.0,
) -> int:
    """Estimate AP threshold by the first dV/dt crossing before the peak.

    Args:
        times: Sample times.
        voltages: Voltage samples.
        peak_index: Spike peak index.
        search_start_index: Earliest sample to consider.
        derivative_threshold_mV_ms: Threshold derivative.

    Returns:
        Estimated AP threshold index.

    Example:
        ``index = threshold_index(t, v, peak_index=peak, search_start_index=start)``
    """

    derivatives = [0.0] * len(voltages)
    for index in range(max(1, search_start_index), peak_index + 1):
        delta_t = times[index] - times[index - 1]
        if delta_t > 0.0:
            derivatives[index] = (voltages[index] - voltages[index - 1]) / delta_t
    candidates = [
        index
        for index in range(max(1, search_start_index), peak_index + 1)
        if derivatives[index - 1] < derivative_threshold_mV_ms <= derivatives[index]
    ]
    return candidates[-1] if candidates else max(search_start_index, peak_index - 1)


def crossing_time(
    times: Sequence[float],
    values: Sequence[float],
    *,
    start_index: int,
    stop_index: int,
    level: float,
    upward: bool,
) -> float | None:
    """Linearly interpolate a level crossing between trace samples.

    Args:
        times: Sample times.
        values: Samples.
        start_index: Inclusive search start.
        stop_index: Exclusive search end.
        level: Crossing level.
        upward: Search upward when True, downward otherwise.

    Returns:
        Interpolated crossing time, or None.

    Example:
        ``time = crossing_time(t, v, start_index=10, stop_index=20, level=-20, upward=True)``
    """

    for index in range(max(1, start_index), min(stop_index, len(values))):
        before, after = values[index - 1], values[index]
        crossed = before < level <= after if upward else before >= level > after
        if crossed:
            fraction = 0.0 if after == before else (level - before) / (after - before)
            return times[index - 1] + fraction * (times[index] - times[index - 1])
    return None


def ap_waveform_metrics(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    spike_indices: Sequence[int],
    stimulus_start_ms: float,
) -> dict[str, float | None]:
    """Measure threshold, peak, amplitude, half-width, and AHP of the first AP.

    Args:
        times: Sample times.
        voltages: Soma voltage samples.
        spike_indices: Detected spike indices.
        stimulus_start_ms: Current-step onset.

    Returns:
        First-AP waveform metrics.

    Example:
        ``metrics = ap_waveform_metrics(t, v, spike_indices=spikes, stimulus_start_ms=200)``
    """

    empty = {"ap_threshold_mV": None, "ap_peak_mV": None, "ap_amplitude_mV": None, "ap_half_width_ms": None, "ahp_mV": None}
    if not spike_indices:
        return empty
    first = spike_indices[0]
    next_spike = spike_indices[1] if len(spike_indices) > 1 else len(voltages)
    sample_dt = max(times[1] - times[0], 1e-9)
    peak_stop = min(next_spike, first + max(2, int(5.0 / sample_dt)))
    peak = local_peak_index(voltages, crossing_index=first, stop_index=peak_stop)
    search_start = max(1, first - int(20.0 / sample_dt))
    threshold = threshold_index(times, voltages, peak_index=peak, search_start_index=search_start)
    threshold_voltage = voltages[threshold]
    peak_voltage = voltages[peak]
    half_level = threshold_voltage + 0.5 * (peak_voltage - threshold_voltage)
    up_time = crossing_time(times, voltages, start_index=threshold, stop_index=peak + 1, level=half_level, upward=True)
    down_stop = min(next_spike, peak + max(2, int(20.0 / sample_dt)))
    down_time = crossing_time(times, voltages, start_index=peak + 1, stop_index=down_stop, level=half_level, upward=False)
    ahp_stop = min(next_spike, peak + max(2, int(50.0 / sample_dt)))
    ahp_minimum = min(voltages[peak:ahp_stop]) if ahp_stop > peak else peak_voltage
    return {
        "ap_threshold_mV": threshold_voltage,
        "ap_peak_mV": peak_voltage,
        "ap_amplitude_mV": peak_voltage - threshold_voltage,
        "ap_half_width_ms": None if up_time is None or down_time is None else down_time - up_time,
        "ahp_mV": threshold_voltage - ahp_minimum,
        "first_spike_latency_ms": times[first] - stimulus_start_ms,
    }


def passive_tau_ms(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    stimulus_start_ms: float,
    rmp_mV: float,
    steady_state_mV: float,
) -> float | None:
    """Estimate membrane tau from the 63.2% voltage transition.

    Args:
        times: Sample times.
        voltages: Voltage trace.
        stimulus_start_ms: Current-step onset.
        rmp_mV: Pre-step baseline voltage.
        steady_state_mV: Late-step voltage.

    Returns:
        Tau in milliseconds, or None when no crossing is found.

    Example:
        ``tau = passive_tau_ms(t, v, stimulus_start_ms=200, rmp_mV=-65, steady_state_mV=-75)``
    """

    target = rmp_mV + 0.6321205588 * (steady_state_mV - rmp_mV)
    start_index = next((index for index, time in enumerate(times) if time >= stimulus_start_ms), 1)
    if steady_state_mV < rmp_mV:
        for index in range(max(1, start_index), len(voltages)):
            if voltages[index - 1] > target >= voltages[index]:
                return times[index] - stimulus_start_ms
    else:
        for index in range(max(1, start_index), len(voltages)):
            if voltages[index - 1] < target <= voltages[index]:
                return times[index] - stimulus_start_ms
    return None


def analyse_trace(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    amplitude_nA: float,
    delay_ms: float,
    duration_ms: float,
) -> dict[str, Any]:
    """Calculate passive, firing, waveform, and stability metrics for one trace.

    Args:
        times: Sample times.
        voltages: Soma voltage.
        amplitude_nA: Injected current.
        delay_ms: Step onset.
        duration_ms: Step duration.

    Returns:
        Machine-readable metric dictionary.

    Example:
        ``metrics = analyse_trace(t, v, amplitude_nA=0.1, delay_ms=200, duration_ms=500)``
    """

    stop_ms = delay_ms + duration_ms
    rmp = mean_in_window(times, voltages, start_ms=max(0.0, delay_ms - 50.0), stop_ms=delay_ms)
    steady_state = mean_in_window(times, voltages, start_ms=stop_ms - min(50.0, duration_ms / 4.0), stop_ms=stop_ms)
    stim_spikes = spike_crossings(times, voltages, start_ms=delay_ms, stop_ms=stop_ms)
    baseline_spikes = spike_crossings(times, voltages, start_ms=0.0, stop_ms=delay_ms)
    spike_times = [times[index] for index in stim_spikes]
    isi = [later - earlier for earlier, later in zip(spike_times, spike_times[1:])]
    waveform = ap_waveform_metrics(times, voltages, spike_indices=stim_spikes, stimulus_start_ms=delay_ms)
    tau = passive_tau_ms(times, voltages, stimulus_start_ms=delay_ms, rmp_mV=rmp, steady_state_mV=steady_state) if amplitude_nA != 0.0 and not stim_spikes else None
    rin = (steady_state - rmp) / amplitude_nA if amplitude_nA != 0.0 and not stim_spikes else None
    recovery_mean = None
    recovery_error = None
    if times[-1] > stop_ms:
        recovery_mean = mean_in_window(
            times,
            voltages,
            start_ms=max(stop_ms, times[-1] - 50.0),
            stop_ms=times[-1] + 0.5 * (times[-1] - times[-2]),
        )
        recovery_error = recovery_mean - rmp
    stimulus_derivatives = [
        (voltages[index] - voltages[index - 1]) / (times[index] - times[index - 1])
        for index in range(1, len(times))
        if delay_ms <= times[index] < stop_ms and times[index] > times[index - 1]
    ]
    late_voltage = mean_in_window(times, voltages, start_ms=stop_ms - min(100.0, duration_ms / 3.0), stop_ms=stop_ms)
    late_spike_count = sum(1 for spike_time in spike_times if spike_time >= stop_ms - min(100.0, duration_ms / 3.0))
    return {
        "amplitude_nA": amplitude_nA,
        "rmp_mV": rmp,
        "steady_state_mV": steady_state,
        "rin_MOhm": rin,
        "tau_ms": tau,
        "input_capacitance_pF": None if rin is None or tau is None or rin == 0.0 else 1000.0 * tau / rin,
        "post_step_recovery_mean_mV": recovery_mean,
        "post_step_recovery_error_mV": recovery_error,
        "max_dvdt_V_s": None if not stimulus_derivatives else max(stimulus_derivatives),
        "spike_count": len(stim_spikes),
        "spike_times_ms": spike_times,
        "first_spike_latency_ms": None if not spike_times else spike_times[0] - delay_ms,
        "last_spike_time_ms": None if not spike_times else spike_times[-1] - delay_ms,
        "mean_isi_ms": None if not isi else statistics.fmean(isi),
        "isi_cv": None if len(isi) < 2 or statistics.fmean(isi) == 0.0 else statistics.pstdev(isi) / statistics.fmean(isi),
        "adaptation_ratio_last_over_first_isi": None if len(isi) < 2 or isi[0] == 0.0 else isi[-1] / isi[0],
        "firing_rate_Hz": 1000.0 * len(stim_spikes) / duration_ms,
        "spontaneous_spike_count": len(baseline_spikes),
        "late_step_mean_voltage_mV": late_voltage,
        "depolarization_block_flag": bool(amplitude_nA > 0.0 and len(stim_spikes) > 0 and late_spike_count == 0 and late_voltage > -40.0),
        **waveform,
    }


def initiation_metrics(
    times: Sequence[float],
    traces: dict[str, Sequence[float]],
    *,
    stimulus_start_ms: float,
    stimulus_stop_ms: float,
) -> dict[str, Any]:
    """Compare 0-mV crossing times at soma, dendrite, and proximal axon candidate.

    Args:
        times: Sample times.
        traces: Site-name to voltage trace mapping.
        stimulus_start_ms: Search start.
        stimulus_stop_ms: Search end.

    Returns:
        Crossing times and earliest recorded site.

    Example:
        ``result = initiation_metrics(t, traces, stimulus_start_ms=200, stimulus_stop_ms=700)``
    """

    crossings: dict[str, float | None] = {}
    for name, trace in traces.items():
        indices = spike_crossings(times, trace, start_ms=stimulus_start_ms, stop_ms=stimulus_stop_ms)
        if not indices:
            crossings[name] = None
        else:
            index = indices[0]
            crossings[name] = crossing_time(
                times,
                trace,
                start_index=index,
                stop_index=index + 1,
                level=0.0,
                upward=True,
            )
    finite = {name: value for name, value in crossings.items() if value is not None}
    earliest = None if not finite else min(finite, key=finite.get)
    axon_time = crossings.get("proximal_axon_candidate")
    soma_time = crossings.get("soma")
    axon_minus_soma = None if axon_time is None or soma_time is None else axon_time - soma_time
    return {
        "first_zero_crossing_ms": crossings,
        "earliest_recorded_site": earliest,
        "provisional_ais_minus_soma_zero_crossing_ms": axon_minus_soma,
        "provisional_ais_precedes_soma": None if axon_minus_soma is None else axon_minus_soma < 0.0,
    }


def safe_amp_name(amplitude_nA: float) -> str:
    """Create a filesystem-safe deterministic current-amplitude label.

    Args:
        amplitude_nA: Current amplitude.

    Returns:
        Label such as ``p0p100`` or ``m0p050``.

    Example:
        ``name = safe_amp_name(-0.05)``
    """

    sign = "m" if amplitude_nA < 0.0 else "p"
    return sign + f"{abs(amplitude_nA):.3f}".replace(".", "p")


def write_trace_csv(
    output_path: Path,
    *,
    times: Sequence[float],
    traces: dict[str, Sequence[float]],
) -> None:
    """Write time-aligned voltage traces as CSV.

    Args:
        output_path: Destination CSV.
        times: Sample times.
        traces: Voltage traces by recording site.

    Returns:
        None.

    Example:
        ``write_trace_csv(path, times=t, traces=traces)``
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    names = list(traces)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ms", *[f"v_{name}_mV" for name in names]])
        for index, time in enumerate(times):
            writer.writerow([f"{time:.6f}", *[f"{traces[name][index]:.6f}" for name in names]])


def write_metrics_csv(output_path: Path, rows: Sequence[dict[str, Any]]) -> None:
    """Write scalar per-current metrics as CSV.

    Args:
        output_path: Destination CSV.
        rows: Metric dictionaries.

    Returns:
        None.

    Example:
        ``write_metrics_csv(path, rows)``
    """

    scalar_keys = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (list, dict))})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=scalar_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_validation_svg(output_path: Path, *, trace_records: Sequence[dict[str, Any]], metrics: Sequence[dict[str, Any]]) -> None:
    """Write a dependency-free SVG of voltage traces and the F-I curve.

    Args:
        output_path: Destination SVG.
        trace_records: Recorded time and soma traces.
        metrics: Per-current metric rows.

    Returns:
        None.

    Example:
        ``write_validation_svg(path, trace_records=traces, metrics=rows)``
    """

    width, height = 1200, 720
    left, right, top, bottom = 70, 40, 45, 55
    trace_height = 480
    all_times = [time for record in trace_records for time in record["times"]]
    all_values = [value for record in trace_records for value in record["soma"]]
    min_t, max_t = min(all_times), max(all_times)
    min_v, max_v = min(all_values), max(all_values)
    span_t, span_v = max(max_t - min_t, 1.0), max(max_v - min_v, 1.0)
    colours = ("#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2", "#4b5563", "#be123c")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.title{font-size:18px;font-weight:600}.axis{font-size:12px}.legend{font-size:11px}</style>',
        '<text class="title" x="20" y="26">RatLCN_L292E1 validation traces</text>',
        f'<line x1="{left}" y1="{top + trace_height}" x2="{width - right}" y2="{top + trace_height}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + trace_height}" stroke="#111827"/>',
    ]
    for record_index, record in enumerate(trace_records):
        step = max(1, len(record["times"]) // 2500)
        points = []
        for time, value in zip(record["times"][::step], record["soma"][::step]):
            x = left + (time - min_t) / span_t * (width - left - right)
            y = top + (max_v - value) / span_v * trace_height
            points.append(f"{x:.2f},{y:.2f}")
        colour = colours[record_index % len(colours)]
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colour}" stroke-width="1" opacity="0.85"/>')
        legend_x = left + (record_index % 4) * 175
        legend_y = top + 16 + (record_index // 4) * 16
        parts.append(f'<text class="legend" x="{legend_x}" y="{legend_y}" fill="{colour}">{record["amplitude_nA"]:.3f} nA</text>')
    parts.extend(
        [
            f'<text class="axis" x="{width / 2 - 25}" y="{top + trace_height + 35}">time (ms)</text>',
            f'<text class="axis" transform="translate(18 {top + trace_height / 2}) rotate(-90)">voltage (mV)</text>',
        ]
    )
    fi_top, fi_height = 590, 90
    positive = [row for row in metrics if row["amplitude_nA"] >= 0.0]
    if positive:
        min_i, max_i = min(row["amplitude_nA"] for row in positive), max(row["amplitude_nA"] for row in positive)
        max_rate = max(max(row["firing_rate_Hz"] for row in positive), 1.0)
        fi_points = []
        for row in positive:
            x = left + (row["amplitude_nA"] - min_i) / max(max_i - min_i, 1e-9) * (width - left - right)
            y = fi_top + fi_height - row["firing_rate_Hz"] / max_rate * fi_height
            fi_points.append(f"{x:.2f},{y:.2f}")
        parts.append(f'<line x1="{left}" y1="{fi_top + fi_height}" x2="{width - right}" y2="{fi_top + fi_height}" stroke="#111827"/>')
        parts.append(f'<polyline points="{" ".join(fi_points)}" fill="none" stroke="#111827" stroke-width="1.5"/>')
        for point in fi_points:
            x, y = point.split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#111827"/>')
        parts.append(f'<text class="axis" x="{left}" y="{fi_top - 8}">F-I curve (Hz vs nA)</text>')
    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def run_current_step(
    *,
    h: Any,
    cell: RatLCN_L292E1,
    amplitude_nA: float,
    delay_ms: float,
    duration_ms: float,
    tstop_ms: float,
    v_init_mV: float,
) -> tuple[list[float], dict[str, list[float]]]:
    """Run one deterministic somatic IClamp step.

    Args:
        h: NEURON hoc interface.
        cell: Instantiated morphology.
        amplitude_nA: Step current.
        delay_ms: Step onset.
        duration_ms: Step duration.
        tstop_ms: Simulation stop time.
        v_init_mV: Initialization voltage.

    Returns:
        Time samples and voltage traces by site.

    Example:
        ``times, traces = run_current_step(h=h, cell=cell, amplitude_nA=0.1, ...)``
    """

    sites = cell.recording_sites()
    clamp = h.IClamp(sites["soma"])
    clamp.delay = delay_ms
    clamp.dur = duration_ms
    clamp.amp = amplitude_nA
    t_vector = h.Vector().record(h._ref_t)
    vectors = {name: h.Vector().record(segment._ref_v) for name, segment in sites.items()}
    h.tstop = tstop_ms
    h.finitialize(v_init_mV)
    h.continuerun(tstop_ms)
    return list(t_vector), {name: list(vector) for name, vector in vectors.items()}


def assess_model(metrics: Sequence[dict[str, Any]], *, phenotype: str, targets: dict[str, Any]) -> dict[str, Any]:
    """Apply explicit qualitative and quantitative validation gates.

    Args:
        metrics: Per-current results.
        phenotype: Expected computational phenotype.
        targets: Configured evidence-backed targets.

    Returns:
        Gate results and readiness classification.

    Example:
        ``assessment = assess_model(rows, phenotype="transient", targets=targets)``
    """

    zero = next((row for row in metrics if row["amplitude_nA"] == 0.0), None)
    spiking = [row for row in metrics if row["amplitude_nA"] > 0.0 and row["spike_count"] > 0]
    checks: dict[str, bool | None] = {
        "no_spontaneous_firing": None if zero is None else zero["spontaneous_spike_count"] == 0 and zero["spike_count"] == 0,
        "no_depolarization_block_in_tested_steps": not any(row["depolarization_block_flag"] for row in metrics),
    }
    rmp_range = targets.get("rmp_mV")
    checks["rmp_in_target"] = None if zero is None or not rmp_range else rmp_range[0] <= zero["rmp_mV"] <= rmp_range[1]
    if phenotype == "passive":
        passive_rows = [row for row in metrics if row["amplitude_nA"] < 0.0 and row["rin_MOhm"] is not None]
        rin_range = targets.get("rin_MOhm")
        tau_range = targets.get("tau_ms")
        recovery_tolerance = float(targets.get("post_step_recovery_tolerance_mV", 0.1))
        checks["no_evoked_spikes"] = not any(row["spike_count"] for row in metrics)
        checks["rin_in_target"] = bool(passive_rows) and bool(rin_range) and all(
            rin_range[0] <= row["rin_MOhm"] <= rin_range[1] for row in passive_rows
        )
        checks["tau_in_target"] = bool(passive_rows) and bool(tau_range) and all(
            row["tau_ms"] is not None and tau_range[0] <= row["tau_ms"] <= tau_range[1] for row in passive_rows
        )
        checks["post_step_recovery_within_tolerance"] = bool(passive_rows) and all(
            row["post_step_recovery_error_mV"] is not None
            and abs(row["post_step_recovery_error_mV"]) <= recovery_tolerance
            for row in passive_rows
        )
    else:
        checks["spikes_at_one_or_more_positive_steps"] = bool(spiking)
    if phenotype == "transient":
        checks["medlock_transient_1_to_2_spikes_within_100_ms"] = bool(spiking) and all(
            1 <= row["spike_count"] <= 2
            and row["first_spike_latency_ms"] is not None
            and row["first_spike_latency_ms"] <= 100.0
            for row in spiking
        )
    elif phenotype == "delayed":
        ordered = sorted(spiking, key=lambda row: row["amplitude_nA"])
        latencies = [row["first_spike_latency_ms"] for row in ordered if row["first_spike_latency_ms"] is not None]
        checks["latency_decreases_with_current"] = len(latencies) >= 2 and all(later <= earlier for earlier, later in zip(latencies, latencies[1:]))
    waveform_ranges = {
        "ap_threshold_mV": targets.get("ap_threshold_mV"),
        "ap_peak_mV": targets.get("ap_peak_mV"),
        "ap_half_width_ms": targets.get("ap_half_width_ms"),
    }
    for metric_name, metric_range in waveform_ranges.items():
        if metric_range:
            checks[f"{metric_name}_in_target"] = bool(spiking) and all(
                row[metric_name] is not None and metric_range[0] <= row[metric_name] <= metric_range[1]
                for row in spiking
            )
    active_recovery_tolerance = targets.get("post_step_recovery_tolerance_mV")
    if active_recovery_tolerance is not None:
        checks["post_step_recovery_within_tolerance"] = all(
            row["post_step_recovery_error_mV"] is not None
            and abs(row["post_step_recovery_error_mV"]) <= float(active_recovery_tolerance)
            for row in metrics
        )
    mandatory = [value for value in checks.values() if value is not None]
    passed = bool(mandatory) and all(mandatory)
    return {
        "checks": checks,
        "all_executed_gates_pass": passed,
        "classification": "STAGE_GATE_PASSED" if passed else "NOT_READY_STAGE_GATE_FAILED",
        "note": "A stage pass is not final model readiness and does not confirm molecular identity or 35C translation.",
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the validation command-line parser.

    Args:
        None.

    Returns:
        Configured parser.

    Example:
        ``parser = build_parser()``
    """

    parser = argparse.ArgumentParser(description="Validate a reconstructed L292-E1 cell configuration.")
    parser.add_argument("--config", type=Path, required=True, help="Model JSON configuration.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Structured output directory.")
    parser.add_argument("--temperature", type=float, help="Override configured celsius before initialization.")
    parser.add_argument("--dt-ms", type=float, help="Override the configured fixed time step in milliseconds.")
    parser.add_argument("--d-lambda", type=float, help="Override the configured d-lambda spatial fraction.")
    parser.add_argument(
        "--current-steps-nA",
        type=float,
        nargs="+",
        help="Override configured somatic current steps in nA; values are saved in the summary.",
    )
    parser.add_argument("--passive-only", action="store_true", help="Do not insert active mechanisms.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned ranges and dependencies without importing NEURON.")
    return parser


def main() -> int:
    """Validate one configuration and write machine-readable results.

    Args:
        None. Arguments are read from ``sys.argv``.

    Returns:
        Process exit status.

    Example:
        ``python validate_single_cell.py --help``
    """

    args = build_parser().parse_args()
    config = load_model_config(args.config)
    base_dir = args.config.resolve().parents[2]
    simulation = config["simulation"]
    protocol = config.get("protocol", {})
    configured_amplitudes = protocol.get("current_steps_nA", [-0.05, 0.0, 0.05, 0.1, 0.2, 0.3])
    amplitudes = [float(value) for value in (args.current_steps_nA or configured_amplitudes)]
    temperature = float(args.temperature if args.temperature is not None else simulation["celsius"])
    dt_ms = float(args.dt_ms if args.dt_ms is not None else simulation["dt_ms"])
    discretization = dict(config.get("discretization", {}))
    if args.d_lambda is not None:
        discretization["d_lambda"] = float(args.d_lambda)
    plan = {
        "model": config.get("model_name"),
        "config_status": config.get("status", "unknown"),
        "temperature_C": temperature,
        "dt_ms": dt_ms,
        "d_lambda": discretization.get("d_lambda", 0.1),
        "current_steps_nA": amplitudes,
        "range_reason": protocol.get("range_reason", "not documented"),
        "passive_only": args.passive_only,
        "output_dir": str(args.output_dir.resolve()),
    }
    print("Planned parameter/current ranges before execution:")
    print(json.dumps(plan, indent=2))
    if args.dry_run or not neuron_available():
        if not neuron_available():
            print("NEURON is not importable; dry-run completed without simulation.")
        return 0

    import neuron
    from neuron import h

    mechanism_dir = (base_dir / config["mechanisms"]["directory"]).resolve()
    if not neuron.load_mechanisms(str(mechanism_dir)):
        print(f"Mechanisms were already loaded or no additional library was loaded from {mechanism_dir}")
    # NEURON 9 does not expose stdrun variables such as steps_per_ms until
    # stdrun.hoc is loaded.  Load it before applying the fixed-step settings.
    h.load_file("stdrun.hoc")
    h.celsius = temperature
    h.dt = dt_ms
    h.steps_per_ms = 1.0 / h.dt
    h.cvode_active(0)
    morphology_path = base_dir / config["morphology"]["path"]
    active = None if args.passive_only else config.get("active")
    cell = RatLCN_L292E1(
        morphology_path=morphology_path,
        passive=config["passive"],
        discretization=discretization,
        active=active,
    )
    delay_ms = float(protocol.get("delay_ms", 200.0))
    duration_ms = float(protocol.get("duration_ms", 500.0))
    tstop_ms = float(protocol.get("tstop_ms", delay_ms + duration_ms + 200.0))
    v_init_mV = float(simulation["v_init_mV"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metric_rows: list[dict[str, Any]] = []
    trace_records: list[dict[str, Any]] = []
    initiation_by_current: dict[str, Any] = {}
    for amplitude in amplitudes:
        times, traces = run_current_step(
            h=h,
            cell=cell,
            amplitude_nA=amplitude,
            delay_ms=delay_ms,
            duration_ms=duration_ms,
            tstop_ms=tstop_ms,
            v_init_mV=v_init_mV,
        )
        row = analyse_trace(times, traces["soma"], amplitude_nA=amplitude, delay_ms=delay_ms, duration_ms=duration_ms)
        metric_rows.append(row)
        initiation_by_current[str(amplitude)] = initiation_metrics(
            times,
            traces,
            stimulus_start_ms=delay_ms,
            stimulus_stop_ms=delay_ms + duration_ms,
        )
        trace_records.append({"amplitude_nA": amplitude, "times": times, "soma": traces["soma"]})
        write_trace_csv(args.output_dir / f"trace_{safe_amp_name(amplitude)}_nA.csv", times=times, traces=traces)

    positive_spiking = [row for row in metric_rows if row["amplitude_nA"] > 0.0 and row["spike_count"] > 0]
    rheobase = None if not positive_spiking else min(row["amplitude_nA"] for row in positive_spiking)
    negative_rows = [row for row in metric_rows if row["amplitude_nA"] < 0.0 and row["rin_MOhm"] is not None]
    passive_reference = None if not negative_rows else min(negative_rows, key=lambda row: abs(row["amplitude_nA"]))
    assessment = assess_model(
        metric_rows,
        phenotype=config.get("intrinsic_phenotype", "unknown"),
        targets=config.get("validation_targets", {}),
    )
    inventory = cell.section_inventory(frequency_Hz=float(config.get("discretization", {}).get("frequency_Hz", 100.0)))
    connectivity = cell.connectivity_summary()
    summary = {
        "identity_statement": IDENTITY_STATEMENT,
        "model_name": config.get("model_name"),
        "configuration_status": config.get("status"),
        "temperature_C": temperature,
        "temperature_label": "experimental-source-temperature" if temperature == 23.0 else "temperature-translated model",
        "passive_only": args.passive_only,
        "software": {"python": platform.python_version(), "neuron": neuron.__version__, "platform": platform.platform()},
        "protocol": {
            "delay_ms": delay_ms,
            "duration_ms": duration_ms,
            "tstop_ms": tstop_ms,
            "dt_ms": float(h.dt),
            "d_lambda": float(discretization.get("d_lambda", 0.1)),
            "frequency_Hz": float(discretization.get("frequency_Hz", 100.0)),
            "current_steps_nA": amplitudes,
        },
        "morphology": {
            "path": str(morphology_path),
            "section_count": len(cell.all_sections),
            "soma_sections": len(cell.soma_sections),
            "dendrite_sections": len(cell.dendrite_sections),
            "axon_sections": len(cell.axon_sections),
            "total_nseg": sum(int(section.nseg) for section in cell.all_sections),
            "minimum_segment_diameter_um": min(row["minimum_segment_diameter_um"] for row in inventory),
            "maximum_segment_electrotonic_fraction": max(
                row["maximum_segment_electrotonic_fraction"] for row in inventory
            ),
            "proximal_axon_candidate_segment_count": len(cell.proximal_axon_candidate_segments),
            "connectivity": connectivity,
        },
        "rheobase_nA_with_tested_resolution": rheobase,
        "passive_reference": passive_reference,
        "per_current": metric_rows,
        "initiation_by_current": initiation_by_current,
        "assessment": assessment,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "section_inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_metrics_csv(args.output_dir / "metrics.csv", metric_rows)
    write_validation_svg(args.output_dir / "validation.svg", trace_records=trace_records, metrics=metric_rows)
    print(json.dumps({"rheobase_nA": rheobase, "classification": assessment["classification"], "summary": str(args.output_dir / "summary.json")}, indent=2))
    return 0 if assessment["all_executed_gates_pass"] or args.passive_only else 2


if __name__ == "__main__":
    raise SystemExit(main())
