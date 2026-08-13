"""NMO_170087 morphology, biophysics, simulation, and measurement helpers."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
MECHANISM_DIR = REPO_ROOT / "cells" / "L571_inhibitory_interneuron" / "mechanisms"
_MECHANISMS_LOADED = False


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def odd_nseg(length_um: float, lambda_um: float, d_lambda: float) -> int:
    value = int((length_um / (d_lambda * lambda_um) + 0.9) / 2) * 2 + 1
    return max(1, value)


class MorphologyHolder:
    pass


@dataclass
class Trace:
    time_ms: np.ndarray
    soma_mv: np.ndarray
    axon_mv: np.ndarray
    dendrite_mv: np.ndarray
    current_na: float


class PVCell:
    """Native NMO_170087 reconstruction with configuration-driven biophysics."""

    def __init__(self, config: dict[str, Any], passive_only: bool = False) -> None:
        from neuron import h, load_mechanisms

        global _MECHANISMS_LOADED
        self.h = h
        self.config = copy.deepcopy(config)
        h.load_file("stdrun.hoc")
        h.load_file("import3d.hoc")
        if not passive_only and config["active"]["enabled"] and not _MECHANISMS_LOADED:
            load_mechanisms(str(MECHANISM_DIR))
            _MECHANISMS_LOADED = True

        reader = h.Import3d_SWC_read()
        reader.input(str(ROOT / config["morphology"]["file"]))
        importer = h.Import3d_GUI(reader, 0)
        self.holder = MorphologyHolder()
        importer.instantiate(self.holder)
        self.soma = list(getattr(self.holder, "soma", []))
        self.dendrites = list(getattr(self.holder, "dend", []))
        self.axon = list(getattr(self.holder, "axon", []))
        if not self.soma or not self.dendrites or not self.axon:
            raise RuntimeError(
                f"Incomplete Import3D domains: soma={len(self.soma)}, "
                f"dendrite={len(self.dendrites)}, axon={len(self.axon)}"
            )
        self.sections = self.soma + self.dendrites + self.axon
        self._assign_passive()
        self._assign_nseg()
        self.axon_root = self._find_soma_connected(self.axon, "axon")
        self.proximal_dendrite = self._find_soma_connected(self.dendrites, "dendrite")
        self.axon_record_x = min(0.5, 20.0 / max(self.axon_root.L, 1e-9))
        if not passive_only and config["active"]["enabled"]:
            self._assign_active()

    def _assign_passive(self) -> None:
        values = self.config["passive"]
        for section in self.sections:
            section.Ra = values["ra_ohm_cm"]
            section.cm = values["cm_uf_cm2"]
            section.insert("pas")
            section.g_pas = values["g_pas_s_cm2"]
            section.e_pas = values["e_pas_mv"]

    def _assign_nseg(self) -> None:
        values = self.config["discretization"]
        for section in self.sections:
            electrotonic_length = self.h.lambda_f(values["frequency_hz"], sec=section)
            section.nseg = odd_nseg(section.L, electrotonic_length, values["d_lambda"])

    def _find_soma_connected(self, candidates: list[Any], label: str):
        roots = []
        for section in candidates:
            parent = self.h.SectionRef(sec=section).parent
            if parent is not None and "soma" in parent.name():
                roots.append(section)
        if not roots:
            raise RuntimeError(f"No soma-connected {label} section found")
        return roots[0]

    def _set_density(self, segment: Any, density: dict[str, float]) -> None:
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
        active = self.config["active"]
        densities = active["conductance_s_cm2"]
        for section in self.sections:
            section.insert("l571_na")
            section.insert("l571_kdr")
            section.ena = self.config["ions"]["ena_mv"]
            section.ek = self.config["ions"]["ek_mv"]
        for section in self.soma:
            for segment in section:
                self._set_density(segment, densities["soma"])
        for section in self.dendrites:
            for segment in section:
                self._set_density(segment, densities["dendrite"])
        self.h.distance(0, 0.5, sec=self.soma[0])
        for section in self.axon:
            for segment in section:
                region = (
                    "ais_proxy"
                    if self.h.distance(segment.x, sec=section) <= active["ais_proxy_max_distance_um"]
                    else "distal_axon"
                )
                self._set_density(segment, densities[region])

    def inventory(self) -> dict[str, Any]:
        area_by_domain = {
            "soma": sum(self.h.area(seg.x, sec=sec) for sec in self.soma for seg in sec),
            "dendrite": sum(self.h.area(seg.x, sec=sec) for sec in self.dendrites for seg in sec),
            "axon": sum(self.h.area(seg.x, sec=sec) for sec in self.axon for seg in sec),
        }
        return {
            "sections": {
                "total": len(self.sections),
                "soma": len(self.soma),
                "dendrite": len(self.dendrites),
                "axon": len(self.axon),
            },
            "segments": {
                "total": sum(sec.nseg for sec in self.sections),
                "soma": sum(sec.nseg for sec in self.soma),
                "dendrite": sum(sec.nseg for sec in self.dendrites),
                "axon": sum(sec.nseg for sec in self.axon),
            },
            "area_um2": {**area_by_domain, "total": sum(area_by_domain.values())},
            "geometric_capacitance_pf": sum(
                self.h.area(seg.x, sec=sec) * sec.cm * 0.01 for sec in self.sections for seg in sec
            ),
            "axon_root": self.axon_root.name(),
            "axon_root_length_um": self.axon_root.L,
            "axon_record_x": self.axon_record_x,
            "proximal_dendrite": self.proximal_dendrite.name(),
            "source_swc_unchanged": True,
            "synthetic_axon_added": False,
        }

    def dispose(self) -> None:
        for section in list(self.sections):
            self.h.delete_section(sec=section)
        self.sections = []


def run_step(
    cell: PVCell,
    current_na: float,
    *,
    dt_ms: float | None = None,
    v_init_mv: float | None = None,
    duration_ms: float | None = None,
) -> Trace:
    h = cell.h
    sim = cell.config["simulation"]
    h.celsius = cell.config["temperature_c"]
    h.dt = sim["dt_ms"] if dt_ms is None else dt_ms
    h.steps_per_ms = 1.0 / h.dt
    delay = sim["stim_delay_ms"]
    duration = sim["stim_duration_ms"] if duration_ms is None else duration_ms
    h.tstop = delay + duration + sim["post_stim_ms"]
    clamp = h.IClamp(cell.soma[0](0.5))
    clamp.delay = delay
    clamp.dur = duration
    clamp.amp = current_na
    time = h.Vector().record(h._ref_t)
    soma = h.Vector().record(cell.soma[0](0.5)._ref_v)
    axon = h.Vector().record(cell.axon_root(cell.axon_record_x)._ref_v)
    dendrite = h.Vector().record(cell.proximal_dendrite(0.5)._ref_v)
    initial = sim["v_init_mv"] if v_init_mv is None else v_init_mv
    h.finitialize(initial)
    h.continuerun(h.tstop)
    return Trace(
        np.asarray(time, dtype=float).copy(),
        np.asarray(soma, dtype=float).copy(),
        np.asarray(axon, dtype=float).copy(),
        np.asarray(dendrite, dtype=float).copy(),
        current_na,
    )


def passive_metrics(trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    from scipy.optimize import curve_fit

    delay = config["simulation"]["stim_delay_ms"]
    duration = config["simulation"]["stim_duration_ms"]
    pre = (trace.time_ms >= delay - 100.0) & (trace.time_ms < delay)
    steady = (trace.time_ms >= delay + duration - 100.0) & (trace.time_ms < delay + duration)
    baseline = float(np.mean(trace.soma_mv[pre]))
    steady_mv = float(np.mean(trace.soma_mv[steady]))
    rin = float((steady_mv - baseline) / trace.current_na)
    fit = (trace.time_ms >= delay) & (trace.time_ms <= delay + min(duration, 300.0))
    x = trace.time_ms[fit] - delay
    y = trace.soma_mv[fit]

    def response(t: np.ndarray, asymptote: float, tau: float) -> np.ndarray:
        return asymptote + (baseline - asymptote) * np.exp(-t / tau)

    params, _ = curve_fit(
        response,
        x,
        y,
        p0=(steady_mv, 20.0),
        bounds=([-120.0, 0.05], [-30.0, 2000.0]),
        maxfev=20000,
    )
    predicted = response(x, *params)
    tau = float(params[1])
    return {
        "baseline_equilibrium_mv": baseline,
        "steady_state_mv": steady_mv,
        "delta_v_mv": steady_mv - baseline,
        "rin_mohm": rin,
        "tau_ms_monoexponential": tau,
        "tau_fit_rmse_mv": float(np.sqrt(np.mean((predicted - y) ** 2))),
        "equivalent_capacitance_from_tau_rin_pf": float(1000.0 * tau / rin),
    }


def spike_times(trace: Trace, config: dict[str, Any], signal: str = "soma") -> np.ndarray:
    voltage = trace.soma_mv if signal == "soma" else trace.axon_mv
    crossing = config["simulation"]["spike_crossing_mv"]
    candidates = np.flatnonzero((voltage[:-1] < crossing) & (voltage[1:] >= crossing)) + 1
    accepted: list[int] = []
    for index in candidates:
        if not accepted or trace.time_ms[index] - trace.time_ms[accepted[-1]] >= 1.0:
            accepted.append(int(index))
    return trace.time_ms[np.asarray(accepted, dtype=int)] if accepted else np.asarray([], dtype=float)


def firing_metrics(trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    delay = config["simulation"]["stim_delay_ms"]
    duration = config["simulation"]["stim_duration_ms"]
    spikes = spike_times(trace, config)
    spikes = spikes[(spikes >= delay) & (spikes <= delay + duration)] - delay
    isi = np.diff(spikes)
    return {
        "current_na": trace.current_na,
        "spike_count": int(len(spikes)),
        "frequency_hz": float(len(spikes) / (duration / 1000.0)),
        "first_spike_latency_ms": float(spikes[0]) if len(spikes) else None,
        "last_spike_time_ms": float(spikes[-1]) if len(spikes) else None,
        "mean_isi_ms": float(np.mean(isi)) if len(isi) else None,
        "adaptation_ratio_last_over_first": float(isi[-1] / isi[0]) if len(isi) >= 2 else None,
        "tonic_persistence_fraction": float(spikes[-1] / duration) if len(spikes) else 0.0,
        "spike_times_relative_ms": [float(value) for value in spikes],
    }


def action_potential_metrics(trace: Trace, config: dict[str, Any]) -> dict[str, Any]:
    delay = config["simulation"]["stim_delay_ms"]
    duration = config["simulation"]["stim_duration_ms"]
    times = spike_times(trace, config)
    times = times[(times >= delay) & (times <= delay + duration)]
    if not len(times):
        return {"available": False}
    dt = float(np.median(np.diff(trace.time_ms)))
    crossing_index = int(np.searchsorted(trace.time_ms, times[0]))
    derivative = np.gradient(trace.soma_mv, trace.time_ms)
    search_start = max(0, crossing_index - int(8.0 / dt))
    peak_end = min(len(trace.soma_mv), crossing_index + int(5.0 / dt))
    peak_index = crossing_index + int(np.argmax(trace.soma_mv[crossing_index:peak_end]))
    candidates = np.flatnonzero(derivative[search_start:peak_index] >= 20.0)
    threshold_index = search_start + int(candidates[0]) if len(candidates) else crossing_index
    threshold = float(trace.soma_mv[threshold_index])
    peak = float(trace.soma_mv[peak_index])
    half_level = threshold + 0.5 * (peak - threshold)
    left_candidates = np.flatnonzero(trace.soma_mv[threshold_index : peak_index + 1] >= half_level)
    left = threshold_index + int(left_candidates[0])
    right_end = min(len(trace.soma_mv), peak_index + int(20.0 / dt))
    right_candidates = np.flatnonzero(trace.soma_mv[peak_index:right_end] <= half_level)
    right = peak_index + int(right_candidates[0]) if len(right_candidates) else right_end - 1
    ahp_start = min(len(trace.soma_mv) - 1, peak_index + max(1, int(1.0 / dt)))
    ahp_end = min(len(trace.soma_mv), peak_index + int(80.0 / dt))
    ahp = float(np.min(trace.soma_mv[ahp_start:ahp_end]))
    axon_times = spike_times(trace, config, signal="axon")
    axon_times = axon_times[(axon_times >= delay) & (axon_times <= delay + duration)]
    return {
        "available": True,
        "threshold_mv_dvdt_20_v_s": threshold,
        "peak_mv": peak,
        "amplitude_peak_minus_threshold_mv": peak - threshold,
        "half_width_ms": float(trace.time_ms[right] - trace.time_ms[left]),
        "ahp_min_mv": ahp,
        "ahp_relative_to_threshold_mv": ahp - threshold,
        "max_dvdt_v_s": float(np.max(derivative[search_start:right_end])),
        "soma_crossing_time_ms": float(times[0]),
        "axon_crossing_time_ms": float(axon_times[0]) if len(axon_times) else None,
        "axon_lead_ms": float(times[0] - axon_times[0]) if len(axon_times) else None,
    }
