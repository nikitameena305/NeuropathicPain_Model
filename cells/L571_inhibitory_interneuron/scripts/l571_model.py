"""Core morphology, biophysics, simulation, and metric helpers for L571-LCN."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
_MECHANISMS_LOADED = False


def load_config(*, path: Path) -> dict[str, Any]:
    """Load a model configuration from JSON.

    Args:
        path: Configuration file path.

    Returns:
        Mutable configuration dictionary.

    Example:
        ``config = load_config(path=Path('parameters/cell.json'))``
    """

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(*, value: Any, path: Path) -> None:
    """Write JSON with stable indentation and strict finite-number checking.

    Args:
        value: JSON-serializable object.
        path: Destination path.

    Returns:
        None.

    Example:
        ``save_json(value=result, path=Path('result.json'))``
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def odd_scaled_nseg(*, base: int, scale: float) -> int:
    """Scale a segment count and force a positive odd integer.

    Args:
        base: Baseline odd segment count.
        scale: Positive multiplicative scale.

    Returns:
        Positive odd segment count.

    Example:
        ``nseg = odd_scaled_nseg(base=5, scale=2)``
    """

    candidate = max(1, int(math.ceil(base * scale)))
    return candidate if candidate % 2 else candidate + 1


class MorphologyHolder:
    """Empty Python target populated by NEURON Import3D.

    Example:
        ``holder = MorphologyHolder()``
    """

    pass


@dataclass
class Trace:
    """Hold one current-step recording.

    Args:
        time_ms: Sample times.
        soma_mv: Somatic membrane potential.
        ais_mv: Proximal reconstructed axon/AIS-proxy potential.
        dendrite_mv: Proximal dendritic potential.
        current_na: Injected somatic current.

    Returns:
        Recorded time series and stimulus amplitude.

    Example:
        ``trace = Trace(t, soma, ais, dendrite, 0.02)``
    """

    time_ms: np.ndarray
    soma_mv: np.ndarray
    ais_mv: np.ndarray
    dendrite_mv: np.ndarray
    current_na: float


class L571Cell:
    """Instantiate the full L571 morphology and assign configured mechanisms."""

    def __init__(self, *, config: dict[str, Any], passive_only: bool = False) -> None:
        """Build the cell after assigning passive Ra and d-lambda discretization.

        Args:
            config: Complete model configuration.
            passive_only: If true, omit all active conductances.

        Returns:
            Initialized L571 cell wrapper.

        Example:
            ``cell = L571Cell(config=config, passive_only=True)``
        """

        from neuron import h, load_mechanisms

        global _MECHANISMS_LOADED

        self.h = h
        self.config = copy.deepcopy(config)
        h.load_file("stdrun.hoc")
        h.load_file("import3d.hoc")
        if not passive_only and not _MECHANISMS_LOADED:
            load_mechanisms(str(ROOT / "mechanisms"))
            _MECHANISMS_LOADED = True
        reader = h.Import3d_SWC_read()
        morphology_path = ROOT / config["morphology"]["file"]
        reader.input(str(morphology_path))
        importer = h.Import3d_GUI(reader, 0)
        self.holder = MorphologyHolder()
        importer.instantiate(self.holder)
        self.soma = list(getattr(self.holder, "soma", []))
        self.dendrites = list(getattr(self.holder, "dend", []))
        self.axon = list(getattr(self.holder, "axon", []))
        if not self.soma or not self.dendrites or not self.axon:
            raise RuntimeError(
                f"Import3D domains incomplete: soma={len(self.soma)}, "
                f"dendrites={len(self.dendrites)}, axon={len(self.axon)}"
            )
        self.sections = self.soma + self.dendrites + self.axon
        self._assign_passive()
        self._assign_nseg()
        self.ais_section = self._find_axon_root()
        self.ais_record_x = min(0.5, 20.0 / self.ais_section.L)
        self.proximal_dendrite = self._find_proximal_dendrite()
        if not passive_only and config["active"]["enabled"]:
            self._assign_active()

    def _assign_passive(self) -> None:
        """Insert uniform passive properties before d-lambda calculation.

        Returns:
            None.

        Example:
            ``cell._assign_passive()``
        """

        passive = self.config["passive"]
        for section in self.sections:
            section.Ra = passive["ra_ohm_cm"]
            section.cm = passive["cm_uf_cm2"]
            section.insert("pas")
            section.g_pas = passive["g_pas_s_cm2"]
            section.e_pas = passive["e_pas_mv"]

    def _assign_nseg(self) -> None:
        """Apply the odd d-lambda discretization after Ra and cm are final.

        Returns:
            None.

        Example:
            ``cell._assign_nseg()``
        """

        settings = self.config["discretization"]
        for section in self.sections:
            lambda_um = self.h.lambda_f(settings["frequency_hz"], sec=section)
            base = int((section.L / (settings["d_lambda"] * lambda_um) + 0.9) / 2) * 2 + 1
            section.nseg = odd_scaled_nseg(base=max(1, base), scale=settings["nseg_scale"])

    def _find_axon_root(self):
        """Find the reconstructed axon section connected nearest the soma.

        Returns:
            Proximal axon section used as an AIS proxy.

        Example:
            ``ais = cell._find_axon_root()``
        """

        roots = []
        for section in self.axon:
            parent = self.h.SectionRef(sec=section).parent
            if parent is not None and "soma" in parent.name():
                roots.append(section)
        if len(roots) != 1:
            raise RuntimeError(f"Expected one soma-connected axon root, found {len(roots)}")
        return roots[0]

    def _find_proximal_dendrite(self):
        """Find a soma-connected dendrite for simultaneous recording.

        Returns:
            First soma-connected dendritic section.

        Example:
            ``dendrite = cell._find_proximal_dendrite()``
        """

        for section in self.dendrites:
            parent = self.h.SectionRef(sec=section).parent
            if parent is not None and "soma" in parent.name():
                return section
        return self.dendrites[0]

    def _configure_mechanism(self, *, segment: Any, density: dict[str, float]) -> None:
        """Set conductance and temperature parameters on one segment.

        Args:
            segment: NEURON segment containing both L571 mechanisms.
            density: Sodium and potassium conductance density mapping.

        Returns:
            None.

        Example:
            ``cell._configure_mechanism(segment=seg, density={'na': 0.1, 'kdr': 0.01})``
        """

        active = self.config["active"]
        segment.l571_na.gnabar = density["na"]
        segment.l571_na.q10 = active["q10_na"]
        segment.l571_na.tref = active["reference_temperature_c"]
        segment.l571_na.temperature_scaling = float(active["temperature_scaling"])
        segment.l571_kdr.gkbar = density["kdr"]
        segment.l571_kdr.q10 = active["q10_kdr"]
        segment.l571_kdr.tref = active["reference_temperature_c"]
        segment.l571_kdr.temperature_scaling = float(active["temperature_scaling"])

    def _assign_active(self) -> None:
        """Insert only fast Na and delayed-rectifier K conductances.

        Returns:
            None.

        Example:
            ``cell._assign_active()``
        """

        density = self.config["active"]["conductance_s_cm2"]
        for section in self.sections:
            section.insert("l571_na")
            section.insert("l571_kdr")
            section.ena = self.config["ions"]["ena_mv"]
            section.ek = self.config["ions"]["ek_mv"]
        for section in self.soma:
            for segment in section:
                self._configure_mechanism(segment=segment, density=density["soma"])
        for section in self.dendrites:
            for segment in section:
                self._configure_mechanism(segment=segment, density=density["dendrite"])
        self.h.distance(0, 0.5, sec=self.soma[0])
        max_distance = self.config["active"]["ais_proxy_max_distance_um"]
        for section in self.axon:
            for segment in section:
                distance = self.h.distance(segment.x, sec=section)
                region = "ais_proxy" if distance <= max_distance else "distal_axon"
                self._configure_mechanism(segment=segment, density=density[region])

    def summary(self) -> dict[str, Any]:
        """Return morphology and discretization counts from instantiated NEURON sections.

        Returns:
            JSON-serializable section summary.

        Example:
            ``summary = cell.summary()``
        """

        return {
            "section_count": len(self.sections),
            "sections_by_domain": {
                "soma": len(self.soma),
                "dendrite": len(self.dendrites),
                "axon": len(self.axon),
            },
            "nseg_total": sum(section.nseg for section in self.sections),
            "nseg_by_domain": {
                "soma": sum(section.nseg for section in self.soma),
                "dendrite": sum(section.nseg for section in self.dendrites),
                "axon": sum(section.nseg for section in self.axon),
            },
            "ais_proxy_section": self.ais_section.name(),
            "ais_proxy_section_length_um": self.ais_section.L,
            "ais_record_x": self.ais_record_x,
            "ais_record_path_distance_approx_um": self.ais_record_x * self.ais_section.L,
            "proximal_dendrite_section": self.proximal_dendrite.name(),
        }

    def dispose(self) -> None:
        """Delete this cell's sections from the global NEURON interpreter.

        Returns:
            None.

        Example:
            ``cell.dispose()``
        """

        for section in list(self.sections):
            self.h.delete_section(sec=section)
        self.sections = []


def run_step(
    cell: L571Cell,
    *,
    current_na: float,
    dt_ms: float | None = None,
    v_init_mv: float | None = None,
) -> Trace:
    """Run one fixed-step somatic current pulse and record three compartments.

    Args:
        cell: Configured L571 cell.
        current_na: Somatic current amplitude.
        dt_ms: Optional timestep override.
        v_init_mv: Optional initial voltage override.

    Returns:
        Recorded trace.

    Example:
        ``trace = run_step(cell, current_na=0.02)``
    """

    h = cell.h
    simulation = cell.config["simulation"]
    h.celsius = cell.config["temperature_c"]
    h.dt = simulation["dt_ms"] if dt_ms is None else dt_ms
    h.steps_per_ms = 1.0 / h.dt
    delay = simulation["stim_delay_ms"]
    duration = simulation["stim_duration_ms"]
    h.tstop = delay + duration + simulation["post_stim_ms"]
    clamp = h.IClamp(cell.soma[0](0.5))
    clamp.delay = delay
    clamp.dur = duration
    clamp.amp = current_na
    time = h.Vector().record(h._ref_t)
    soma = h.Vector().record(cell.soma[0](0.5)._ref_v)
    ais = h.Vector().record(cell.ais_section(cell.ais_record_x)._ref_v)
    dendrite = h.Vector().record(cell.proximal_dendrite(0.5)._ref_v)
    initial = simulation["v_init_mv"] if v_init_mv is None else v_init_mv
    h.finitialize(initial)
    h.continuerun(h.tstop)
    return Trace(
        time_ms=np.asarray(time, dtype=float).copy(),
        soma_mv=np.asarray(soma, dtype=float).copy(),
        ais_mv=np.asarray(ais, dtype=float).copy(),
        dendrite_mv=np.asarray(dendrite, dtype=float).copy(),
        current_na=current_na,
    )


def spike_times(*, time_ms: np.ndarray, voltage_mv: np.ndarray, crossing_mv: float) -> np.ndarray:
    """Detect upward voltage crossings with a 1 ms refractory period.

    Args:
        time_ms: Sample times.
        voltage_mv: Voltage trace.
        crossing_mv: Detection crossing level.

    Returns:
        Spike times in milliseconds.

    Example:
        ``times = spike_times(time_ms=t, voltage_mv=v, crossing_mv=-20)``
    """

    indices = np.flatnonzero((voltage_mv[:-1] < crossing_mv) & (voltage_mv[1:] >= crossing_mv)) + 1
    accepted: list[int] = []
    for index in indices:
        if not accepted or time_ms[index] - time_ms[accepted[-1]] >= 1.0:
            accepted.append(index)
    return time_ms[np.asarray(accepted, dtype=int)] if accepted else np.asarray([], dtype=float)


def firing_metrics(*, trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    """Measure spike-train statistics during the configured pulse.

    Args:
        trace: Current-step recording.
        config: Model configuration.

    Returns:
        Spike count, rate, latency, ISI, adaptation, and persistence metrics.

    Example:
        ``metrics = firing_metrics(trace=trace, config=config)``
    """

    simulation = config["simulation"]
    delay = simulation["stim_delay_ms"]
    duration = simulation["stim_duration_ms"]
    all_spikes = spike_times(
        time_ms=trace.time_ms,
        voltage_mv=trace.soma_mv,
        crossing_mv=simulation["spike_crossing_mv"],
    )
    spikes = all_spikes[(all_spikes >= delay) & (all_spikes <= delay + duration)]
    intervals = np.diff(spikes)
    mean_isi = float(np.mean(intervals)) if len(intervals) else None
    isi_cv = float(np.std(intervals, ddof=1) / mean_isi) if len(intervals) > 1 and mean_isi else None
    adaptation = float(intervals[-1] / intervals[0]) if len(intervals) >= 2 and intervals[0] else None
    return {
        "current_na": trace.current_na,
        "spike_count": int(len(spikes)),
        "firing_rate_hz": float(len(spikes) / (duration / 1000.0)),
        "first_spike_latency_ms": float(spikes[0] - delay) if len(spikes) else None,
        "last_spike_time_ms": float(spikes[-1] - delay) if len(spikes) else None,
        "mean_isi_ms": mean_isi,
        "isi_cv": isi_cv,
        "adaptation_ratio_last_over_first": adaptation,
        "tonic_persistence_fraction": float((spikes[-1] - delay) / duration) if len(spikes) else 0.0,
        "spike_times_relative_ms": [float(value - delay) for value in spikes],
    }


def passive_metrics(*, trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    """Measure RMP, input resistance, and a mono-exponential membrane tau.

    Args:
        trace: Hyperpolarizing current-step recording.
        config: Model configuration.

    Returns:
        Passive response metrics.

    Example:
        ``metrics = passive_metrics(trace=trace, config=config)``
    """

    from scipy.optimize import curve_fit

    delay = config["simulation"]["stim_delay_ms"]
    duration = config["simulation"]["stim_duration_ms"]
    pre = (trace.time_ms >= delay - 100) & (trace.time_ms < delay)
    steady = (trace.time_ms >= delay + duration - 100) & (trace.time_ms < delay + duration)
    rmp = float(np.mean(trace.soma_mv[pre]))
    steady_mv = float(np.mean(trace.soma_mv[steady]))
    rin_mohm = float((steady_mv - rmp) / trace.current_na)
    fit_mask = (trace.time_ms >= delay) & (trace.time_ms <= delay + duration)
    x = trace.time_ms[fit_mask] - delay
    y = trace.soma_mv[fit_mask]

    def exponential(time: np.ndarray, steady_value: float, tau_ms: float) -> np.ndarray:
        """Evaluate the fitted charging exponential.

        Args:
            time: Time since step onset.
            steady_value: Asymptotic voltage.
            tau_ms: Time constant.

        Returns:
            Predicted voltage samples.

        Example:
            ``predicted = exponential(time=x, steady_value=-80, tau_ms=50)``
        """

        return steady_value + (rmp - steady_value) * np.exp(-time / tau_ms)

    try:
        parameters, _ = curve_fit(
            exponential,
            x,
            y,
            p0=(steady_mv, 100.0),
            bounds=([-120.0, 0.05], [-30.0, 2000.0]),
            maxfev=20000,
        )
        tau_ms = float(parameters[1])
        fitted = exponential(x, *parameters)
        rmse = float(np.sqrt(np.mean((fitted - y) ** 2)))
    except (RuntimeError, ValueError):
        tau_ms = None
        rmse = None
    return {
        "rmp_mv": rmp,
        "steady_state_mv": steady_mv,
        "delta_v_mv": steady_mv - rmp,
        "current_na": trace.current_na,
        "rin_mohm": rin_mohm,
        "tau_ms_monoexponential": tau_ms,
        "tau_fit_rmse_mv": rmse,
    }


def action_potential_metrics(*, trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    """Measure first-stimulus-spike waveform and AIS-to-soma timing.

    Args:
        trace: Suprathreshold recording.
        config: Model configuration.

    Returns:
        Threshold, peak, amplitude, width, AHP, dV/dt, and timing metrics.

    Example:
        ``metrics = action_potential_metrics(trace=trace, config=config)``
    """

    simulation = config["simulation"]
    delay = simulation["stim_delay_ms"]
    duration = simulation["stim_duration_ms"]
    crossings = spike_times(
        time_ms=trace.time_ms,
        voltage_mv=trace.soma_mv,
        crossing_mv=simulation["spike_crossing_mv"],
    )
    crossings = crossings[(crossings >= delay) & (crossings <= delay + duration)]
    if not len(crossings):
        return {"available": False}
    crossing_index = int(np.searchsorted(trace.time_ms, crossings[0]))
    dt = float(np.median(np.diff(trace.time_ms)))
    peak_window_end = min(len(trace.soma_mv), crossing_index + max(2, int(5.0 / dt)))
    peak_index = crossing_index + int(np.argmax(trace.soma_mv[crossing_index:peak_window_end]))
    derivative = np.gradient(trace.soma_mv, trace.time_ms)
    search_start = max(0, peak_index - int(8.0 / dt))
    candidates = np.flatnonzero(derivative[search_start:peak_index] >= 20.0)
    threshold_index = search_start + int(candidates[0]) if len(candidates) else crossing_index
    threshold_mv = float(trace.soma_mv[threshold_index])
    peak_mv = float(trace.soma_mv[peak_index])
    half_level = threshold_mv + 0.5 * (peak_mv - threshold_mv)
    left_candidates = np.flatnonzero(trace.soma_mv[threshold_index:peak_index + 1] >= half_level)
    left = threshold_index + int(left_candidates[0]) if len(left_candidates) else threshold_index
    right_limit = min(len(trace.soma_mv), peak_index + max(2, int(20.0 / dt)))
    right_candidates = np.flatnonzero(trace.soma_mv[peak_index:right_limit] <= half_level)
    right = peak_index + int(right_candidates[0]) if len(right_candidates) else right_limit - 1
    ahp_start = min(len(trace.soma_mv) - 1, peak_index + max(1, int(1.0 / dt)))
    ahp_end = min(len(trace.soma_mv), peak_index + max(2, int(80.0 / dt)))
    ahp_mv = float(np.min(trace.soma_mv[ahp_start:ahp_end])) if ahp_end > ahp_start else None
    ais_crossings = spike_times(
        time_ms=trace.time_ms,
        voltage_mv=trace.ais_mv,
        crossing_mv=simulation["spike_crossing_mv"],
    )
    ais_crossings = ais_crossings[(ais_crossings >= delay) & (ais_crossings <= delay + duration)]
    timing = float(crossings[0] - ais_crossings[0]) if len(ais_crossings) else None
    return {
        "available": True,
        "threshold_mv_dvdt_20_v_s": threshold_mv,
        "peak_mv": peak_mv,
        "amplitude_mv": peak_mv - threshold_mv,
        "half_width_ms": float(trace.time_ms[right] - trace.time_ms[left]),
        "ahp_min_mv": ahp_mv,
        "ahp_depth_from_threshold_mv": float(threshold_mv - ahp_mv) if ahp_mv is not None else None,
        "max_dvdt_v_s": float(np.max(derivative[search_start:right_limit])),
        "ais_to_soma_crossing_delay_ms": timing,
        "soma_crossing_time_ms": float(crossings[0]),
        "ais_crossing_time_ms": float(ais_crossings[0]) if len(ais_crossings) else None,
    }


def trace_to_dict(*, trace: Trace) -> dict[str, Any]:
    """Convert a Trace to a compact JSON mapping.

    Args:
        trace: Recorded trace.

    Returns:
        Mapping containing all samples as lists.

    Example:
        ``payload = trace_to_dict(trace=trace)``
    """

    return {
        "current_na": trace.current_na,
        "time_ms": trace.time_ms.tolist(),
        "soma_mv": trace.soma_mv.tolist(),
        "ais_mv": trace.ais_mv.tolist(),
        "proximal_dendrite_mv": trace.dendrite_mv.tolist(),
    }
