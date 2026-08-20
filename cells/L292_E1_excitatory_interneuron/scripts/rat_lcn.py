"""Reusable reconstructed rat L292-E1 local-circuit neuron scaffold."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable


IDENTITY_STATEMENT = (
    "The L292-E1-LCN reconstruction is a rat lamina-I local-circuit morphological scaffold. "
    "ePKCgamma/eVGLUT3/eDOR/eSST/eCR/eTrC labels refer to computational Medlock population "
    "identity and are not molecular identities experimentally confirmed for L292-E1-LCN."
)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge a configuration override into a copied base mapping."""

    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_model_config(path: Path, _seen: set[Path] | None = None) -> dict[str, Any]:
    """Load and minimally validate a model JSON configuration.

    Args:
        path: Configuration path.

    Returns:
        Parsed model configuration.

    Example:
        ``config = load_model_config(Path("parameters.json"))``
    """

    resolved = path.resolve()
    seen = set() if _seen is None else set(_seen)
    if resolved in seen:
        raise ValueError(f"configuration inheritance cycle at {resolved}")
    seen.add(resolved)
    config = json.loads(resolved.read_text(encoding="utf-8-sig"))
    extends = config.pop("extends", None)
    if extends is not None:
        parent = load_model_config((resolved.parent / str(extends)).resolve(), seen)
        config = _deep_merge(parent, config)
    for key in ("morphology", "simulation", "passive"):
        if key not in config:
            raise ValueError(f"{path}: missing required key {key!r}")
    return config


def _as_sections(value: Any) -> list[Any]:
    """Convert an Import3D-created section attribute to a Python list.

    Args:
        value: NEURON Section, SectionList, or section array.

    Returns:
        List of NEURON sections.

    Example:
        ``sections = _as_sections(cell.soma)``
    """

    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return [value]


def _unique_sections(sections: Iterable[Any]) -> list[Any]:
    """Deduplicate NEURON sections while retaining import order.

    Args:
        sections: Sections to deduplicate.

    Returns:
        Ordered unique section list.

    Example:
        ``unique = _unique_sections(sections)``
    """

    result: list[Any] = []
    seen: set[str] = set()
    for section in sections:
        name = section.name()
        if name not in seen:
            seen.add(name)
            result.append(section)
    return result


class RatLCN_L292E1:
    """Instantiate morphology independently from physiological identity.

    Args:
        morphology_path: Official standardized SWC reconstruction.
        passive: Passive-property configuration.
        discretization: d-lambda settings applied after Ra and cm.
        active: Optional region-specific mechanism configuration.

    Returns:
        A NEURON cell with soma, dendrite, and axon section groups.

    Example:
        ``cell = RatLCN_L292E1(morphology_path=swc, passive=passive, discretization=disc)``
    """

    def __init__(
        self,
        *,
        morphology_path: Path,
        passive: dict[str, float],
        discretization: dict[str, float],
        active: dict[str, Any] | None = None,
    ) -> None:
        from neuron import h

        self.h = h
        self.morphology_path = morphology_path.resolve()
        self.h.load_file("stdrun.hoc")
        self.h.load_file("import3d.hoc")
        before = {section.name() for section in self.h.allsec()}
        reader = self.h.Import3d_SWC_read()
        reader.input(str(self.morphology_path))
        importer = self.h.Import3d_GUI(reader, 0)
        importer.instantiate(self)
        imported = [section for section in self.h.allsec() if section.name() not in before]
        imported_soma = _as_sections(getattr(self, "soma", None))
        imported_dend = _as_sections(getattr(self, "dend", None)) + _as_sections(getattr(self, "apic", None))
        imported_axon = _as_sections(getattr(self, "axon", None))
        self.soma_sections = _unique_sections(imported_soma or [section for section in imported if "soma" in section.name().lower()])
        self.dendrite_sections = _unique_sections(imported_dend or [section for section in imported if "dend" in section.name().lower() or "apic" in section.name().lower()])
        self.axon_sections = _unique_sections(imported_axon or [section for section in imported if "axon" in section.name().lower()])
        self.all_sections = _unique_sections(imported)
        if not self.soma_sections or not self.dendrite_sections or not self.axon_sections:
            raise RuntimeError(
                "Import3D did not expose all required section groups: "
                f"soma={len(self.soma_sections)}, dendrite={len(self.dendrite_sections)}, axon={len(self.axon_sections)}"
            )
        self._assign_passive(passive=passive)
        self._assign_d_lambda(discretization=discretization)
        self.proximal_axon_candidate_segments: list[Any] = []
        if active:
            self.apply_active(active=active)

    def _assign_passive(self, *, passive: dict[str, float]) -> None:
        """Assign Ra, cm, and passive leak before discretization.

        Args:
            passive: Ra, cm, g_pas, and e_pas values.

        Returns:
            None.

        Example:
            ``cell._assign_passive(passive=passive)``
        """

        required = ("Ra_ohm_cm", "cm_uF_cm2", "g_pas_S_cm2", "e_pas_mV")
        missing = [key for key in required if key not in passive]
        if missing:
            raise ValueError(f"passive configuration missing {missing}")
        for section in self.all_sections:
            section.Ra = float(passive["Ra_ohm_cm"])
            section.cm = float(passive["cm_uF_cm2"])
            section.insert("pas")
            for segment in section:
                segment.g_pas = float(passive["g_pas_S_cm2"])
                segment.e_pas = float(passive["e_pas_mV"])

    def _assign_d_lambda(self, *, discretization: dict[str, float]) -> None:
        """Choose odd nseg values after Ra and cm have their final passive values.

        Args:
            discretization: Frequency and d-lambda fraction.

        Returns:
            None.

        Example:
            ``cell._assign_d_lambda(discretization={"frequency_Hz": 100, "d_lambda": 0.1})``
        """

        frequency = float(discretization.get("frequency_Hz", 100.0))
        d_lambda = float(discretization.get("d_lambda", 0.1))
        if frequency <= 0.0 or d_lambda <= 0.0:
            raise ValueError("frequency_Hz and d_lambda must be positive")
        for section in self.all_sections:
            electrotonic_length = float(self.h.lambda_f(frequency, sec=section))
            if not math.isfinite(electrotonic_length) or electrotonic_length <= 0.0:
                raise RuntimeError(f"invalid lambda_f for {section.name()}: {electrotonic_length}")
            required = max(1, math.ceil(float(section.L) / (d_lambda * electrotonic_length)))
            section.nseg = required if required % 2 == 1 else required + 1

    def _insert_and_set(self, *, sections: Iterable[Any], region: dict[str, Any]) -> None:
        """Insert mechanisms and set ionic/reversal parameters in one region.

        Args:
            sections: Target sections.
            region: Region configuration with ions and mechanisms.

        Returns:
            None.

        Example:
            ``cell._insert_and_set(sections=cell.soma_sections, region=region)``
        """

        mechanisms = region.get("mechanisms", {})
        for section in sections:
            for mechanism_name in mechanisms:
                section.insert(mechanism_name)
            for segment in section:
                self._set_segment(segment=segment, region=region)

    @staticmethod
    def _set_segment(*, segment: Any, region: dict[str, Any]) -> None:
        """Set ion reversals and RANGE parameters on one segment.

        Args:
            segment: NEURON segment.
            region: Region parameter mapping.

        Returns:
            None.

        Example:
            ``RatLCN_L292E1._set_segment(segment=seg, region=region)``
        """

        for ion_name, values in region.get("ions", {}).items():
            reversal_key = f"e{ion_name}"
            if "e_mV" in values and hasattr(segment, reversal_key):
                setattr(segment, reversal_key, float(values["e_mV"]))
            internal_key = f"{ion_name}i"
            if "i_mM" in values and hasattr(segment, internal_key):
                setattr(segment, internal_key, float(values["i_mM"]))
            external_key = f"{ion_name}o"
            if "o_mM" in values and hasattr(segment, external_key):
                setattr(segment, external_key, float(values["o_mM"]))
        conductance_scale = float(region.get("conductance_scale", 1.0))
        if conductance_scale <= 0.0:
            raise ValueError(f"conductance_scale must be positive, got {conductance_scale}")
        conductance_parameters = {"g", "gbar", "gkbar", "gkabar", "gnabar", "pcabar"}
        for mechanism_name, parameters in region.get("mechanisms", {}).items():
            for parameter_name, value in parameters.items():
                attribute = f"{parameter_name}_{mechanism_name}"
                if not hasattr(segment, attribute):
                    raise AttributeError(f"{segment}: mechanism parameter {attribute!r} is unavailable")
                assigned_value = float(value)
                if parameter_name in conductance_parameters:
                    assigned_value *= conductance_scale
                setattr(segment, attribute, assigned_value)

    def _zero_conductances(self, *, sections: Iterable[Any], mechanisms: dict[str, dict[str, float]]) -> None:
        """Zero known conductance RANGE variables before piecewise axon assignment.

        Args:
            sections: Axonal sections receiving piecewise rules.
            mechanisms: Union of mechanisms and parameters.

        Returns:
            None.

        Example:
            ``cell._zero_conductances(sections=cell.axon_sections, mechanisms=union)``
        """

        conductance_names = {"gnabar", "gkbar", "gkabar", "gbar", "pcabar"}
        for section in sections:
            for mechanism_name in mechanisms:
                section.insert(mechanism_name)
            for segment in section:
                for mechanism_name, parameters in mechanisms.items():
                    for parameter_name in conductance_names.intersection(parameters):
                        attribute = f"{parameter_name}_{mechanism_name}"
                        if hasattr(segment, attribute):
                            setattr(segment, attribute, 0.0)

    def apply_active(self, *, active: dict[str, Any]) -> None:
        """Apply physiology from configuration while retaining morphology identity.

        Args:
            active: Region-specific mechanism, ion, and proximal-axon candidate rules.

        Returns:
            None.

        Example:
            ``cell.apply_active(active=config["active"])``
        """

        regions = active.get("regions", {})
        self._insert_and_set(sections=self.soma_sections, region=regions.get("soma", {}))
        self._insert_and_set(sections=self.dendrite_sections, region=regions.get("dendrite", {}))
        proximal = regions.get("proximal_axon_candidate", {})
        distal = regions.get("axon_distal", {})
        soma = self.soma_sections[0]
        self.h.distance(0.0, 0.5, sec=soma)
        endpoint_distances = {
            section.name(): (
                float(self.h.distance(0.0, sec=section)),
                float(self.h.distance(1.0, sec=section)),
            )
            for section in self.axon_sections
        }
        axon_origin_distance = min(min(values) for values in endpoint_distances.values())
        max_path_um = float(proximal.get("max_path_from_axon_origin_um", 0.0))
        maximum_segment_length_um = float(proximal.get("maximum_segment_length_um", 0.0))
        if maximum_segment_length_um > 0.0 and max_path_um > 0.0:
            for section in self.axon_sections:
                near_distance, far_distance = sorted(endpoint_distances[section.name()])
                if near_distance <= axon_origin_distance + max_path_um and far_distance >= axon_origin_distance:
                    required = max(1, math.ceil(float(section.L) / maximum_segment_length_um))
                    odd_required = required if required % 2 == 1 else required + 1
                    section.nseg = max(int(section.nseg), odd_required)
        union: dict[str, dict[str, float]] = {}
        for region in (proximal, distal):
            for mechanism_name, parameters in region.get("mechanisms", {}).items():
                union.setdefault(mechanism_name, {}).update(parameters)
        self._zero_conductances(sections=self.axon_sections, mechanisms=union)
        self.h.distance(0.0, 0.5, sec=soma)
        distances = [(float(self.h.distance(segment.x, sec=section)), segment) for section in self.axon_sections for segment in section]
        self.proximal_axon_candidate_segments = []
        for absolute_distance, segment in distances:
            relative_distance = absolute_distance - axon_origin_distance
            region = proximal if relative_distance <= max_path_um else distal
            self._set_segment(segment=segment, region=region)
            if relative_distance <= max_path_um:
                self.proximal_axon_candidate_segments.append(segment)

    def recording_sites(self) -> dict[str, Any]:
        """Return soma, proximal dendrite, and proximal axon candidate sites.

        Args:
            None.

        Returns:
            Mapping of recording-site names to NEURON segments.

        Example:
            ``sites = cell.recording_sites()``
        """

        soma_site = self.soma_sections[0](0.5)
        self.h.distance(0.0, 0.5, sec=self.soma_sections[0])
        dendrite_site = min(
            (segment for section in self.dendrite_sections for segment in section),
            key=lambda segment: float(self.h.distance(segment.x, sec=segment.sec)),
        )
        axon_pool = self.proximal_axon_candidate_segments or [segment for section in self.axon_sections for segment in section]
        axon_site = min(axon_pool, key=lambda segment: float(self.h.distance(segment.x, sec=segment.sec)))
        return {"soma": soma_site, "proximal_dendrite": dendrite_site, "proximal_axon_candidate": axon_site}

    def section_inventory(self, *, frequency_Hz: float = 100.0) -> list[dict[str, float | int | str]]:
        """Describe imported sections and d-lambda discretization.

        Args:
            frequency_Hz: Frequency used for lambda reporting.

        Returns:
            One machine-readable row per imported section.

        Example:
            ``rows = cell.section_inventory(frequency_Hz=100.0)``
        """

        groups: dict[str, str] = {}
        for name, sections in (("soma", self.soma_sections), ("dendrite", self.dendrite_sections), ("axon", self.axon_sections)):
            groups.update({section.name(): name for section in sections})
        return [
            {
                "section": section.name(),
                "group": groups.get(section.name(), "unknown"),
                "L_um": float(section.L),
                "diam_um": float(section.diam),
                "minimum_segment_diameter_um": min(float(segment.diam) for segment in section),
                "maximum_segment_diameter_um": max(float(segment.diam) for segment in section),
                "Ra_ohm_cm": float(section.Ra),
                "cm_uF_cm2": float(section.cm),
                "nseg": int(section.nseg),
                "lambda_um": float(self.h.lambda_f(float(frequency_Hz), sec=section)),
                "maximum_segment_electrotonic_fraction": float(section.L)
                / (int(section.nseg) * float(self.h.lambda_f(float(frequency_Hz), sec=section))),
            }
            for section in self.all_sections
        ]

    def connectivity_summary(self) -> dict[str, Any]:
        """Report imported-section connectivity without changing morphology.

        Returns:
            Root, reachability, and structural-group connectivity checks.
        """

        section_names = {section.name() for section in self.all_sections}
        children: dict[str, list[str]] = {name: [] for name in section_names}
        roots: list[str] = []
        external_parent_sections: list[str] = []
        for section in self.all_sections:
            parent_segment = section.parentseg()
            if parent_segment is None:
                roots.append(section.name())
                continue
            parent_name = parent_segment.sec.name()
            if parent_name not in section_names:
                external_parent_sections.append(section.name())
                continue
            children[parent_name].append(section.name())
        reachable: set[str] = set()
        stack = list(roots)
        while stack:
            name = stack.pop()
            if name in reachable:
                continue
            reachable.add(name)
            stack.extend(children[name])
        soma_names = {section.name() for section in self.soma_sections}
        dendrite_names = {section.name() for section in self.dendrite_sections}
        axon_names = {section.name() for section in self.axon_sections}
        return {
            "root_sections": sorted(roots),
            "one_connected_morphology": len(roots) == 1 and reachable == section_names,
            "soma_is_root": len(roots) == 1 and roots[0] in soma_names,
            "all_dendrites_connected": dendrite_names.issubset(reachable),
            "all_axons_connected": axon_names.issubset(reachable),
            "external_parent_sections": sorted(external_parent_sections),
            "unreachable_sections": sorted(section_names - reachable),
        }
