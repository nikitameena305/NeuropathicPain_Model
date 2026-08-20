"""Shared, deterministic NMO_260150 model and measurement utilities."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from morphology_qa import SwcNode, parse_swc


IDENTITY_STATEMENT = (
    "NPFF-positive superficial dorsal-horn excitatory vertical interneuron used as a "
    "biologically informed analogue of the Medlock eCR population"
)


def neuron_available() -> bool:
    """Check whether NEURON can be imported without importing it at module load.

    Args:
        None.

    Returns:
        True when the ``neuron`` package is importable.

    Example:
        ``if neuron_available(): ...``
    """

    try:
        import importlib.util

        return importlib.util.find_spec("neuron") is not None
    except (ImportError, ValueError):
        return False


def mechanism_digest(mechanism_dir: Path) -> str:
    """Hash the portable MOD sources for a deterministic temporary build cache.

    Args:
        mechanism_dir: Directory containing final MOD files.

    Returns:
        First 16 hexadecimal characters of the combined SHA-256 digest.

    Example:
        ``key = mechanism_digest(Path("mechanisms"))``
    """

    digest = hashlib.sha256()
    for path in sorted(mechanism_dir.glob("*.mod")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def ensure_mechanisms(h: Any, *, mechanism_dir: Path) -> Path:
    """Compile final MOD files into a temporary cache and load the shared library.

    Args:
        h: NEURON hoc interface.
        mechanism_dir: Portable source-only mechanism directory.

    Returns:
        Loaded mechanism library path.

    Example:
        ``library = ensure_mechanisms(h, mechanism_dir=cell_dir / "mechanisms")``
    """

    cache = Path(tempfile.gettempdir()) / f"ecr_nmo260150_nrn_{mechanism_digest(mechanism_dir)}"
    candidates = (
        cache / "x86_64" / ".libs" / "libnrnmech.so",
        cache / "x86_64" / "libnrnmech.so",
        cache / "aarch64" / ".libs" / "libnrnmech.so",
        cache / "aarch64" / "libnrnmech.so",
    )
    library = next((path for path in candidates if path.exists()), None)
    if library is None:
        colocated_compiler = Path(sys.executable).parent / "nrnivmodl"
        compiler = shutil.which("nrnivmodl") or (
            str(colocated_compiler) if colocated_compiler.exists() else None
        )
        if compiler is None:
            raise RuntimeError("nrnivmodl is required to compile cells/eCR/mechanisms")
        cache.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [compiler, str(mechanism_dir.resolve())],
            cwd=cache,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"nrnivmodl failed:\n{result.stdout}\n{result.stderr}")
        library = next((path for path in candidates if path.exists()), None)
        if library is None:
            raise RuntimeError(f"nrnivmodl completed but no libnrnmech.so was found under {cache}")
    h.nrn_load_dll(str(library))
    return library


def build_children(nodes: dict[int, SwcNode]) -> dict[int, list[int]]:
    """Build a sorted SWC child map.

    Args:
        nodes: Parsed SWC nodes.

    Returns:
        Child identifiers keyed by parent identifier.

    Example:
        ``children = build_children(nodes)``
    """

    children: dict[int, list[int]] = defaultdict(list)
    for node in nodes.values():
        if node.parent_id in nodes:
            children[node.parent_id].append(node.node_id)
    return {parent: sorted(child_ids) for parent, child_ids in children.items()}


class ECRCell:
    """Instantiate the native soma+dendrite NMO_260150 model.

    Args:
        h: NEURON hoc interface.
        morphology_path: Standardized NeuroMorpho SWC path.
        passive: Passive parameter mapping.
        diameter_scale: Global model-defined radius-profile multiplier.
        d_lambda: Spatial discretization fraction.
        frequency_hz: Frequency used by NEURON's d-lambda rule.
        active: Optional channel-density mapping by mechanism and region.
        ais: Optional explicitly model-defined AIS configuration.

    Returns:
        Instantiated cell with section lists.

    Example:
        ``cell = ECRCell(h, morphology_path=swc, passive=params)``
    """

    def __init__(
        self,
        h: Any,
        *,
        morphology_path: Path,
        passive: dict[str, float],
        diameter_scale: float = 1.0,
        d_lambda: float = 0.1,
        frequency_hz: float = 100.0,
        active: dict[str, dict[str, float]] | None = None,
        ais: dict[str, float | bool] | None = None,
    ) -> None:
        self.h = h
        self.nodes, _ = parse_swc(morphology_path)
        self.children = build_children(self.nodes)
        self.diameter_scale = float(diameter_scale)
        self.soma = h.Section(name="soma", cell=self)
        self.dendrites: list[Any] = []
        self.axons: list[Any] = []
        self.all_sections: list[Any] = [self.soma]
        self._build_native_morphology()
        ais_config = ais or {}
        if bool(ais_config.get("enabled", False)):
            self._add_model_defined_ais(ais_config)
        self.apply_passive(passive)
        self.configure_nseg(d_lambda=d_lambda, frequency_hz=frequency_hz)
        if active:
            self.apply_active(active)

    def _diameter(self, node: SwcNode) -> float:
        """Convert one standardized radius into the model-defined nominal diameter.

        Args:
            node: SWC point.

        Returns:
            Positive diameter in micrometres.

        Example:
            ``diameter = self._diameter(node)``
        """

        return max(2.0 * node.radius * self.diameter_scale, 0.05)

    def _add_point(self, section: Any, node: SwcNode) -> None:
        """Append one SWC coordinate to a NEURON section.

        Args:
            section: Target NEURON section.
            node: SWC point.

        Returns:
            None.

        Example:
            ``self._add_point(section, node)``
        """

        self.h.pt3dadd(node.x, node.y, node.z, self._diameter(node), sec=section)

    def _build_native_morphology(self) -> None:
        """Create one soma and maximal unbranched dendritic sections.

        Args:
            None.

        Returns:
            None.

        Example:
            ``self._build_native_morphology()``
        """

        soma_nodes = sorted((node for node in self.nodes.values() if node.node_type == 1), key=lambda node: node.node_id)
        if not soma_nodes:
            raise ValueError("NMO_260150 SWC has no soma nodes")
        root = next((node for node in soma_nodes if node.parent_id == -1), soma_nodes[0])
        soma_children = [self.nodes[node_id] for node_id in self.children.get(root.node_id, []) if self.nodes[node_id].node_type == 1]
        ordered_soma = ([soma_children[0]] if soma_children else []) + [root] + (soma_children[1:2] if len(soma_children) > 1 else [])
        if len(ordered_soma) == 1:
            ordered_soma = [ordered_soma[0], ordered_soma[0]]
        self.h.pt3dclear(sec=self.soma)
        for node in ordered_soma:
            self._add_point(self.soma, node)
        for node in sorted(self.nodes.values(), key=lambda item: item.node_id):
            parent = self.nodes.get(node.parent_id)
            if node.node_type == 1 or parent is None or parent.node_type != 1:
                continue
            self._build_chain(start_id=node.node_id, parent_node_id=parent.node_id, parent_section=self.soma)

    def _build_chain(self, *, start_id: int, parent_node_id: int, parent_section: Any) -> None:
        """Create one maximal same-type unbranched neurite section recursively.

        Args:
            start_id: First non-soma node in the new section.
            parent_node_id: Coordinate duplicated at section origin.
            parent_section: NEURON section to connect at its distal end.

        Returns:
            None.

        Example:
            ``self._build_chain(start_id=4, parent_node_id=1, parent_section=self.soma)``
        """

        start = self.nodes[start_id]
        region = "axon" if start.node_type == 2 else "dendrite"
        collection = self.axons if region == "axon" else self.dendrites
        section = self.h.Section(name=f"{region}[{len(collection)}]", cell=self)
        collection.append(section)
        self.all_sections.append(section)
        section.connect(parent_section(0.5 if parent_section is self.soma else 1.0), 0.0)
        self.h.pt3dclear(sec=section)
        self._add_point(section, self.nodes[parent_node_id])
        current_id = start_id
        self._add_point(section, self.nodes[current_id])
        while True:
            compatible = [
                child_id
                for child_id in self.children.get(current_id, [])
                if self.nodes[child_id].node_type == self.nodes[current_id].node_type
            ]
            if len(compatible) != 1:
                break
            current_id = compatible[0]
            self._add_point(section, self.nodes[current_id])
        for child_id in self.children.get(current_id, []):
            self._build_chain(start_id=child_id, parent_node_id=current_id, parent_section=section)

    def _add_model_defined_ais(self, ais: dict[str, float | bool]) -> None:
        """Attach an explicitly synthetic AIS to the soma.

        Args:
            ais: AIS length and diameter configuration.

        Returns:
            None.

        Example:
            ``self._add_model_defined_ais({"length_um": 25.0, "diameter_um": 1.0})``
        """

        section = self.h.Section(name="model_defined_ais", cell=self)
        section.L = float(ais.get("length_um", 25.0))
        section.diam = float(ais.get("diameter_um", 1.0))
        section.connect(self.soma(1.0), 0.0)
        self.axons.append(section)
        self.all_sections.append(section)

    def apply_passive(self, passive: dict[str, float]) -> None:
        """Apply passive parameters uniformly without altering the diameter policy.

        Args:
            passive: Mapping containing Ra, cm, g_pas, and e_pas.

        Returns:
            None.

        Example:
            ``cell.apply_passive({"Ra_ohm_cm": 150, ...})``
        """

        for section in self.all_sections:
            section.Ra = float(passive["Ra_ohm_cm"])
            section.cm = float(passive["cm_uF_cm2"])
            if not self.h.ismembrane("pas", sec=section):
                section.insert("pas")
            for segment in section:
                segment.pas.g = float(passive["g_pas_S_cm2"])
                segment.pas.e = float(passive["e_pas_mV"])

    def configure_nseg(self, *, d_lambda: float, frequency_hz: float) -> None:
        """Set odd nseg values with NEURON's frequency-dependent d-lambda rule.

        Args:
            d_lambda: Maximum electrotonic segment fraction.
            frequency_hz: Frequency for lambda calculation.

        Returns:
            None.

        Example:
            ``cell.configure_nseg(d_lambda=0.1, frequency_hz=100.0)``
        """

        for section in self.all_sections:
            lambda_um = float(self.h.lambda_f(frequency_hz, sec=section))
            estimate = int((section.L/(max(d_lambda, 1e-6)*max(lambda_um, 1e-9)) + 0.9)/2.0)
            section.nseg = max(1, 2*estimate + 1)

    def region_name(self, section: Any) -> str:
        """Map one section to a conductance-distribution region.

        Args:
            section: NEURON section.

        Returns:
            ``soma``, ``dendrite``, or ``ais``.

        Example:
            ``region = cell.region_name(section)``
        """

        if section is self.soma:
            return "soma"
        if section in self.axons:
            return "ais"
        return "dendrite"

    def apply_active(self, active: dict[str, dict[str, float]]) -> None:
        """Insert selected mechanisms using configuration-driven regional densities.

        Args:
            active: Mechanism-to-region density mapping.

        Returns:
            None.

        Example:
            ``cell.apply_active({"B_Na": {"soma": 0.05}})``
        """

        fields = {
            "B_Na": "gnabar",
            "B_DR": "gkbar",
            "B_A": "gkbar",
            "Ih_Kole": "gIhbar",
        }
        for mechanism, regional in active.items():
            if mechanism not in fields:
                raise ValueError(f"unsupported mechanism {mechanism}")
            for section in self.all_sections:
                density = float(regional.get(self.region_name(section), 0.0))
                if density <= 0.0:
                    continue
                if not self.h.ismembrane(mechanism, sec=section):
                    section.insert(mechanism)
                for segment in section:
                    setattr(segment, f"{fields[mechanism]}_{mechanism}", density)
                    if mechanism == "B_Na":
                        segment.ena = 53.0
                    if mechanism in ("B_DR", "B_A"):
                        segment.ek = -84.0

    def total_area_um2(self) -> float:
        """Return total membrane area represented by all segments.

        Args:
            None.

        Returns:
            Area in square micrometres.

        Example:
            ``area = cell.total_area_um2()``
        """

        return sum(float(self.h.area(segment.x, sec=section)) for section in self.all_sections for segment in section)

    def capacitance_pf(self) -> float:
        """Return modeled whole-cell capacitance from segment area and specific cm.

        Args:
            None.

        Returns:
            Capacitance in picofarads.

        Example:
            ``capacitance = cell.capacitance_pf()``
        """

        return sum(
            float(section.cm)*float(self.h.area(segment.x, sec=section))*0.01
            for section in self.all_sections
            for segment in section
        )

    def inventory(self) -> dict[str, Any]:
        """Summarize model geometry and discretization.

        Args:
            None.

        Returns:
            JSON-serializable inventory.

        Example:
            ``inventory = cell.inventory()``
        """

        return {
            "section_count": len(self.all_sections),
            "soma_section_count": 1,
            "dendrite_section_count": len(self.dendrites),
            "axon_or_ais_section_count": len(self.axons),
            "total_nseg": sum(int(section.nseg) for section in self.all_sections),
            "total_area_um2": self.total_area_um2(),
            "modeled_whole_cell_capacitance_pF": self.capacitance_pf(),
            "diameter_scale": self.diameter_scale,
            "ais_status": "MODEL-DEFINED AIS" if self.axons else "NO AIS; NO RECONSTRUCTED AXON",
        }

    def delete(self) -> None:
        """Delete all instantiated sections after a bounded search batch.

        Args:
            None.

        Returns:
            None.

        Example:
            ``cell.delete()``
        """

        for section in reversed(self.all_sections):
            self.h.delete_section(sec=section)


def run_iclamp(
    h: Any,
    *,
    cell: ECRCell,
    amplitude_nA: float,
    delay_ms: float,
    duration_ms: float,
    tstop_ms: float,
    v_init_mV: float,
    record_currents: bool = False,
) -> dict[str, list[float]]:
    """Run one deterministic somatic fixed-step current clamp.

    Args:
        h: NEURON hoc interface.
        cell: Instantiated cell.
        amplitude_nA: Step amplitude.
        delay_ms: Step onset.
        duration_ms: Step duration.
        tstop_ms: Simulation stop time.
        v_init_mV: Initialization voltage.
        record_currents: Record selected somatic mechanism currents.

    Returns:
        Time, voltage, and optional density-current traces.

    Example:
        ``trace = run_iclamp(h, cell=cell, amplitude_nA=0.025, ...)``
    """

    clamp = h.IClamp(cell.soma(0.5))
    clamp.delay = delay_ms
    clamp.dur = duration_ms
    clamp.amp = amplitude_nA
    vectors: dict[str, Any] = {
        "time_ms": h.Vector().record(h._ref_t),
        "voltage_mV": h.Vector().record(cell.soma(0.5)._ref_v),
    }
    if record_currents:
        segment = cell.soma(0.5)
        references = {
            "ina_B_Na_mA_cm2": "_ref_ina_B_Na",
            "ik_B_DR_mA_cm2": "_ref_ik_B_DR",
            "ik_B_A_mA_cm2": "_ref_ik_B_A",
            "ih_Ih_Kole_mA_cm2": "_ref_ihcn_Ih_Kole",
        }
        for name, reference_name in references.items():
            if hasattr(segment, reference_name):
                vectors[name] = h.Vector().record(getattr(segment, reference_name))
    h.tstop = float(tstop_ms)
    h.finitialize(float(v_init_mV))
    h.continuerun(float(tstop_ms))
    return {name: list(vector) for name, vector in vectors.items()}


def run_subthreshold_voltage_clamp(
    h: Any,
    *,
    cell: ECRCell,
    v_init_mV: float = -60.0,
) -> dict[str, list[float]]:
    """Run the Quillet et al. -60/-90/-40 mV channel-diagnostic protocol.

    Args:
        h: NEURON hoc interface.
        cell: Instantiated cell.
        v_init_mV: Initialization and first holding voltage.

    Returns:
        Time, clamp current, whole-cell IAr, and whole-cell Ih traces.

    Example:
        ``trace = run_subthreshold_voltage_clamp(h, cell=cell)``
    """

    clamp = h.SEClamp(cell.soma(0.5))
    clamp.rs = 0.001
    clamp.dur1 = 200.0
    clamp.amp1 = -60.0
    clamp.dur2 = 1000.0
    clamp.amp2 = -90.0
    clamp.dur3 = 200.0
    clamp.amp3 = -40.0
    time_vector = h.Vector().record(h._ref_t)
    clamp_vector = h.Vector().record(clamp._ref_i)
    areas: list[float] = []
    ia_vectors: list[Any | None] = []
    ih_vectors: list[Any | None] = []
    for section in cell.all_sections:
        for segment in section:
            areas.append(float(h.area(segment.x, sec=section)))
            ia_vectors.append(
                h.Vector().record(segment._ref_ik_B_A) if hasattr(segment, "_ref_ik_B_A") else None
            )
            ih_vectors.append(
                h.Vector().record(segment._ref_ihcn_Ih_Kole)
                if hasattr(segment, "_ref_ihcn_Ih_Kole")
                else None
            )
    h.tstop = 1400.0
    h.finitialize(v_init_mV)
    h.continuerun(1400.0)
    times = list(time_vector)
    ia_total = [
        sum(float(vector[index])*area*10.0 for vector, area in zip(ia_vectors, areas) if vector is not None)
        for index in range(len(times))
    ]
    ih_total = [
        sum(float(vector[index])*area*10.0 for vector, area in zip(ih_vectors, areas) if vector is not None)
        for index in range(len(times))
    ]
    return {
        "time_ms": times,
        "clamp_current_nA": list(clamp_vector),
        "IAr_model_current_pA": ia_total,
        "Ih_model_current_pA": ih_total,
    }


def spike_crossings(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    start_ms: float,
    stop_ms: float,
    crossing_mV: float = -10.0,
) -> list[int]:
    """Find refractory-separated upward voltage crossings.

    Args:
        times: Sample times.
        voltages: Membrane voltages.
        start_ms: Analysis-window start.
        stop_ms: Analysis-window stop.
        crossing_mV: Event crossing voltage.

    Returns:
        Sample indices for candidate action potentials.

    Example:
        ``indices = spike_crossings(t, v, start_ms=200, stop_ms=1200)``
    """

    indices: list[int] = []
    last_time = -math.inf
    for index in range(1, len(times)):
        if not (start_ms <= times[index] <= stop_ms):
            continue
        if voltages[index - 1] < crossing_mV <= voltages[index] and times[index] - last_time >= 2.0:
            indices.append(index)
            last_time = times[index]
    return indices


def threshold_index(
    times: Sequence[float],
    voltages: Sequence[float],
    *,
    spike_index: int,
    dvdt_threshold_mV_ms: float = 10.0,
) -> int | None:
    """Find the first dV/dt threshold crossing preceding an action potential.

    Args:
        times: Sample times.
        voltages: Membrane voltages.
        spike_index: Candidate spike sample index.
        dvdt_threshold_mV_ms: Paper-defined threshold criterion.

    Returns:
        Threshold sample index or None.

    Example:
        ``index = threshold_index(t, v, spike_index=spikes[0])``
    """

    start = max(1, spike_index - 4000)
    derivatives = [
        (voltages[index] - voltages[index - 1])/max(times[index] - times[index - 1], 1e-12)
        for index in range(start, spike_index + 1)
    ]
    crossings = [
        start + offset
        for offset in range(1, len(derivatives))
        if derivatives[offset - 1] < dvdt_threshold_mV_ms <= derivatives[offset]
    ]
    return crossings[-1] if crossings else None


def analyse_trace(
    trace: dict[str, Sequence[float]],
    *,
    amplitude_nA: float,
    delay_ms: float,
    duration_ms: float,
) -> dict[str, Any]:
    """Measure passive and first-spike metrics from one current-clamp trace.

    Args:
        trace: Time-aligned trace mapping.
        amplitude_nA: Applied current.
        delay_ms: Step onset.
        duration_ms: Step duration.

    Returns:
        JSON-serializable scalar metrics.

    Example:
        ``metrics = analyse_trace(trace, amplitude_nA=0.025, delay_ms=200, duration_ms=1000)``
    """

    times = trace["time_ms"]
    voltages = trace["voltage_mV"]
    step_stop = delay_ms + duration_ms
    baseline_values = [value for time, value in zip(times, voltages) if max(0.0, delay_ms - 100.0) <= time < delay_ms]
    steady_values = [value for time, value in zip(times, voltages) if step_stop - 100.0 <= time <= step_stop]
    recovery_values = [value for time, value in zip(times, voltages) if times[-1] - 100.0 <= time <= times[-1]]
    rmp = sum(baseline_values)/len(baseline_values)
    steady = sum(steady_values)/len(steady_values)
    recovery = sum(recovery_values)/len(recovery_values)
    spikes = spike_crossings(times, voltages, start_ms=delay_ms, stop_ms=step_stop)
    spontaneous = spike_crossings(times, voltages, start_ms=0.0, stop_ms=max(0.0, delay_ms - 1e-9))
    first_latency = None if not spikes else times[spikes[0]] - delay_ms
    threshold_voltage = None
    threshold_time = None
    ap_peak = None
    ap_height = None
    ap_base_width = None
    ahp = None
    if spikes:
        threshold = threshold_index(times, voltages, spike_index=spikes[0])
        if threshold is not None:
            threshold_voltage = voltages[threshold]
            threshold_time = times[threshold]
            peak_stop = min(len(times), spikes[0] + max(2, int(5.0/max(times[1] - times[0], 1e-9))))
            peak_index = max(range(threshold, peak_stop), key=lambda index: voltages[index])
            ap_peak = voltages[peak_index]
            ap_height = ap_peak - threshold_voltage
            downstroke = next(
                (index for index in range(peak_index + 1, len(times)) if voltages[index] <= threshold_voltage),
                None,
            )
            if downstroke is not None:
                ap_base_width = times[downstroke] - threshold_time
                ahp_stop_time = min(step_stop, times[downstroke] + 50.0)
                ahp_values = [
                    value
                    for time, value in zip(times[downstroke:], voltages[downstroke:])
                    if time <= ahp_stop_time
                ]
                if ahp_values:
                    ahp = min(ahp_values) - threshold_voltage
    rin = None if amplitude_nA == 0.0 else (steady - rmp)/amplitude_nA
    tau = None
    if amplitude_nA < 0.0:
        target = rmp + 0.632*(steady - rmp)
        target_index = next(
            (
                index
                for index, (time, value) in enumerate(zip(times, voltages))
                if time >= delay_ms and value <= target
            ),
            None,
        )
        if target_index is not None:
            tau = times[target_index] - delay_ms
    spike_times = [times[index] for index in spikes]
    if not spikes:
        firing_class = "silent"
    elif first_latency is not None and first_latency >= 100.0:
        firing_class = "delayed"
    elif len(spikes) <= 2 and spike_times[-1] <= delay_ms + 0.25*duration_ms:
        firing_class = "single"
    elif spike_times[-1] >= delay_ms + 0.8*duration_ms:
        firing_class = "tonic"
    else:
        firing_class = "transient"
    late_values = [value for time, value in zip(times, voltages) if step_stop - 100.0 <= time <= step_stop]
    late_spikes = [time for time in spike_times if time >= step_stop - 200.0]
    depolarization_block = bool(spikes and not late_spikes and sum(late_values)/len(late_values) > -30.0)
    return {
        "amplitude_nA": amplitude_nA,
        "rmp_mV": rmp,
        "steady_state_mV": steady,
        "rin_MOhm": rin,
        "tau_ms": tau,
        "spike_count": len(spikes),
        "spike_times_ms": spike_times,
        "first_spike_latency_ms": first_latency,
        "threshold_time_ms": threshold_time,
        "ap_threshold_mV_dvdt_10": threshold_voltage,
        "ap_peak_mV": ap_peak,
        "ap_height_mV_peak_minus_threshold": ap_height,
        "ap_base_width_ms_threshold_to_downstroke": ap_base_width,
        "ahp_mV_trough_minus_threshold": ahp,
        "firing_class": firing_class,
        "spontaneous_spike_count_before_step": len(spontaneous),
        "post_step_recovery_error_mV": recovery - rmp,
        "recovery_pass_5mV": abs(recovery - rmp) <= 5.0,
        "depolarization_block": depolarization_block,
    }


def write_json(path: Path, payload: Any) -> None:
    """Write stable, sorted JSON with a final newline.

    Args:
        path: Destination path.
        payload: JSON-serializable object.

    Returns:
        None.

    Example:
        ``write_json(Path("result.json"), result)``
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
