#!/usr/bin/env python3
"""Generate reproducibility-oriented repository and source-collection audits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Entry:
    """Represent one audited file or Git index entry."""

    path: str
    file_type: str
    size: int
    sha256: str
    model: str
    purpose: str
    decision: str
    reason: str
    destination: str


@dataclass(frozen=True)
class SourceSpec:
    """Describe an external source collection and its intended destination."""

    label: str
    root: Path
    destination: str


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Parsed repository and output settings.

    Example:
        ``python scripts/repository_inventory.py --root .``
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="LABEL|PATH|DESTINATION",
        help="Audit a read-only source collection before import; repeat as needed.",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Generate final retained-file, duplicate, and deletion manifests.",
    )
    return parser.parse_args()


def parse_source_spec(value: str) -> SourceSpec:
    """Parse one external source specification.

    Args:
        value: ``LABEL|PATH|DESTINATION`` string.

    Returns:
        Parsed source specification.

    Example:
        ``parse_source_spec('L571|C:/work/L571|cells/L571')``
    """
    parts = value.split("|", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--source requires LABEL|PATH|DESTINATION")
    label, source_root, destination = parts
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise argparse.ArgumentTypeError(f"source directory does not exist: {root}")
    return SourceSpec(label=label, root=root, destination=destination.strip("/"))


def sha256_file(path: Path) -> str:
    """Calculate a file SHA-256 digest.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal digest.

    Example:
        ``sha256_file(Path("README.md"))``
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Hash a textual Git-link target.

    Args:
        value: Text to hash.

    Returns:
        Lowercase hexadecimal digest.

    Example:
        ``sha256_text("deadbeef")``
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tracked_index(root: Path) -> list[tuple[str, str, str]]:
    """Read tracked paths, modes, and object IDs from the Git index.

    Args:
        root: Git repository root.

    Returns:
        Tuples of path, mode, and object ID.

    Example:
        ``tracked_index(Path.cwd())``
    """
    result = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    rows: list[tuple[str, str, str]] = []
    for record in result.stdout.split("\0"):
        if not record:
            continue
        metadata, path = record.split("\t", 1)
        mode, object_id, _stage = metadata.split()
        rows.append((path.replace("\\", "/"), mode, object_id))
    return rows


def classify_type(path: str) -> str:
    """Classify a repository file by path and extension.

    Args:
        path: POSIX-style repository path.

    Returns:
        Stable human-readable file type.

    Example:
        ``classify_type("cell/mechanisms/Na.mod")``
    """
    suffix = PurePosixPath(path).suffix.lower()
    lowered = path.lower()
    if suffix == ".mod":
        return "NMODL mechanism source"
    if suffix in {".swc", ".hoc", ".std"}:
        return "morphology"
    if suffix == ".py":
        return "Python source"
    if suffix in {".sh", ".ps1"}:
        return "shell source"
    if suffix == ".json":
        return "parameter/configuration" if "parameter" in lowered else "JSON result/data"
    if suffix in {".csv", ".dat", ".npz"}:
        return "simulation/validation data"
    if suffix in {".png", ".svg", ".jpg", ".jpeg"}:
        return "figure"
    if suffix in {".md", ".txt"}:
        return "report/documentation"
    if suffix in {".docx", ".html"}:
        return "rendered report"
    if suffix in {".yml", ".yaml", ".toml"} or "requirements" in lowered:
        return "environment/reproducibility"
    if suffix == ".log":
        return "execution/compilation log"
    if suffix == ".save":
        return "editor backup"
    return "project metadata/other"


def classify_model(path: str) -> str:
    """Associate a path with a cell model or historical scope.

    Args:
        path: POSIX-style repository path.

    Returns:
        Model or scope label.

    Example:
        ``classify_model("L796/results/fi.csv")``
    """
    lowered = path.lower()
    if lowered.startswith("cells/l796_projection_neuron/"):
        return "L796-ALT-PN"
    if lowered.startswith("cells/l292_e1_excitatory_interneuron/"):
        return "L292-E1-LCN"
    if lowered.startswith("cells/l571_inhibitory_interneuron/"):
        return "L571-LCN"
    if lowered.startswith("shared/mechanisms/"):
        return "shared mechanisms"
    if lowered.startswith("external/"):
        return "external Medlock reproduction"
    if lowered.startswith("archive/"):
        return "archived scientific history"
    if lowered.startswith("l796/"):
        return "L796-ALT-PN"
    if "2018004" in lowered or "drg" in lowered:
        return "DRG/ModelDB reference"
    if lowered.startswith(("project1/", "project3/", "project4/", "project5/")):
        return "legacy multi-population circuit"
    if lowered.startswith(("metadata/", "selected/", "scripts/")):
        return "shared morphology screening"
    return "legacy/shared project"


def describe_purpose(path: str, file_type: str) -> str:
    """Describe the scientific or reproducibility purpose of a file.

    Args:
        path: POSIX-style repository path.
        file_type: Result from :func:`classify_type`.

    Returns:
        Concise purpose description.

    Example:
        ``describe_purpose("results/fi.csv", "simulation/validation data")``
    """
    lowered = path.lower()
    if file_type == "NMODL mechanism source":
        return "Executable membrane or synaptic mechanism source"
    if file_type == "morphology":
        return "Cell reconstruction or morphology loader"
    if file_type in {"Python source", "shell source"}:
        return "Simulation, analysis, extraction, or validation workflow"
    if file_type == "simulation/validation data":
        return "Raw or summarized evidence for a model result"
    if file_type == "figure":
        return "Visualization of morphology, simulation, or validation output"
    if file_type in {"report/documentation", "rendered report"}:
        return "Scientific interpretation, provenance, or run documentation"
    if file_type == "parameter/configuration":
        return "Configuration-driven model parameters"
    if file_type == "environment/reproducibility":
        return "Software environment or build metadata"
    if file_type == "execution/compilation log":
        return "Execution provenance and diagnostic evidence"
    if file_type == "editor backup":
        return "Superseded editor-created source backup"
    if "screenshot" in lowered:
        return "Historical screenshot"
    return "Project metadata or historical artifact"


def planned_action(path: str, size: int, mode: str) -> tuple[str, str, str]:
    """Assign a conservative pre-cleanup decision and destination.

    Args:
        path: POSIX-style repository path.
        size: File size in bytes.
        mode: Git index mode.

    Returns:
        Decision, reason, and destination.

    Example:
        ``planned_action("L796/README.md", 100, "100644")``
    """
    lowered = path.lower()
    if path in {"README.md", ".gitignore"}:
        return "keep/update", "Canonical repository metadata", path
    if mode == "160000":
        return (
            "delete/replace with provenance note",
            "Broken Git link: referenced object is unavailable and no .gitmodules entry exists",
            "archive/other_exploratory_models/early_project_work/modeldb/2018004_GITLINK_NOTE.md",
        )
    if size == 0 and path in {
        "L796/threshold",
        "L796/morphology/L796.hoc",
        "logs/inspect_dorsal_horn_all.log",
    }:
        return "delete", "Zero-byte artifact with no executable or scientific content", ""
    if lowered.endswith(".save"):
        canonical = path[:-5]
        return "delete if canonical source retained", "Editor backup; canonical source is retained", canonical
    if lowered.startswith("l796/"):
        destination = "cells/L796_projection_neuron/" + path[len("L796/") :]
        return "move", "Consolidate the projection-neuron model without changing scientific content", destination
    destination = "archive/other_exploratory_models/early_project_work/" + path
    return (
        "move/archive",
        "Scientifically useful work outside the three current production-cell packages",
        destination,
    )


def build_repository_entries(root: Path) -> list[Entry]:
    """Build audit entries for the untouched tracked repository state.

    Args:
        root: Git repository root.

    Returns:
        One entry per tracked path.

    Example:
        ``build_repository_entries(Path.cwd())``
    """
    entries: list[Entry] = []
    for relative, mode, object_id in tracked_index(root):
        full_path = root / Path(relative)
        if mode == "160000":
            size = 0
            digest = sha256_text(object_id)
            file_type = "broken Git link"
        else:
            size = full_path.stat().st_size
            digest = sha256_file(full_path)
            file_type = classify_type(relative)
        decision, reason, destination = planned_action(relative, size, mode)
        entries.append(
            Entry(
                path=relative,
                file_type=file_type,
                size=size,
                sha256=digest,
                model=classify_model(relative),
                purpose=describe_purpose(relative, file_type),
                decision=decision,
                reason=reason,
                destination=destination,
            )
        )
    return entries


def source_action(spec: SourceSpec, relative: str) -> tuple[str, str, str]:
    """Choose a conservative action for one read-only source file.

    Args:
        spec: Source collection description.
        relative: POSIX-style path within the collection.

    Returns:
        Decision, reason, and destination.

    Example:
        ``source_action(spec, 'scripts/__pycache__/x.pyc')``
    """
    lowered = relative.lower()
    suffix = PurePosixPath(relative).suffix.lower()
    if "/.git/" in f"/{lowered}/" or lowered.startswith(".git/"):
        return "exclude", "Nested Git metadata is not scientific repository content", ""
    if "__pycache__/" in lowered or suffix in {".pyc", ".pyo"}:
        return "exclude", "Reproducible Python cache", ""
    if "/x86_64/" in f"/{lowered}/" or "/arm64/" in f"/{lowered}/":
        return "exclude", "Reproducible NEURON compilation artifact", ""
    if PurePosixPath(relative).name.lower() == "nrnmech.dll":
        return "exclude", "Reproducible NEURON compilation artifact", ""
    if spec.label == "L292" and lowered.startswith("mechanisms/"):
        if suffix == ".mod":
            return "move/import", "Canonical shared ModelDB-derived mechanism; HH2 includes the documented analytic singularity fix", f"shared/mechanisms/medlock_267056/{PurePosixPath(relative).name}"
        return "move/import", "Preserve cell-specific mechanism provenance", f"{spec.destination}/docs/{PurePosixPath(relative).name}"
    if spec.label == "L571" and lowered.startswith("mechanisms/medlock_reference/"):
        return "deduplicate against shared mechanisms", "Byte-identical ModelDB reference mechanism is retained once in the shared canonical set", f"shared/mechanisms/medlock_267056/{PurePosixPath(relative).name}"
    if spec.label == "L796-history":
        if relative.startswith(("L796_ALT_PN_biological", "L796_ALT_PN_channel")):
            return "move/import", "Current L796 evidence inventory", f"cells/L796_projection_neuron/docs/{relative}"
        return "move/import", "Scientifically useful historical audit retained with its superseded context", f"{spec.destination}/{relative}"
    destination = f"{spec.destination}/{relative}" if relative else spec.destination
    return "move/import", "Scientifically relevant source work preserved in the consolidated repository", destination


def build_source_entries(spec: SourceSpec) -> list[Entry]:
    """Build audit entries for one read-only external source collection.

    Args:
        spec: Source collection description.

    Returns:
        One entry per regular source file, including nested Git metadata as excluded entries.

    Example:
        ``build_source_entries(SourceSpec('L571', Path('L571'), 'cells/L571'))``
    """
    entries: list[Entry] = []
    for full_path in sorted(path for path in spec.root.rglob("*") if path.is_file()):
        relative = full_path.relative_to(spec.root).as_posix()
        decision, reason, destination = source_action(spec, relative)
        file_type = classify_type(relative)
        entries.append(
            Entry(
                path=f"{spec.label}:{relative}",
                file_type=file_type,
                size=full_path.stat().st_size,
                sha256=sha256_file(full_path),
                model=spec.label,
                purpose=describe_purpose(relative, file_type),
                decision=decision,
                reason=reason,
                destination=destination,
            )
        )
    return entries


def write_csv(path: Path, entries: list[Entry]) -> None:
    """Write the required machine-readable audit manifest.

    Args:
        path: CSV destination.
        entries: Audit records.

    Returns:
        None.

    Example:
        ``write_csv(Path("audit.csv"), entries)``
    """
    fieldnames = [
        "current_path",
        "file_type",
        "size_bytes",
        "sha256",
        "model_cell",
        "scientific_purpose",
        "decision",
        "reason",
        "destination_if_moved",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "current_path": entry.path,
                    "file_type": entry.file_type,
                    "size_bytes": entry.size,
                    "sha256": entry.sha256,
                    "model_cell": entry.model,
                    "scientific_purpose": entry.purpose,
                    "decision": entry.decision,
                    "reason": entry.reason,
                    "destination_if_moved": entry.destination,
                }
            )


def write_markdown(path: Path, entries: list[Entry]) -> None:
    """Write the human-readable before-cleanup audit.

    Args:
        path: Markdown destination.
        entries: Audit records.

    Returns:
        None.

    Example:
        ``write_markdown(Path("audit.md"), entries)``
    """
    counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        counts[entry.decision] += 1
    lines = [
        "# Repository audit before cleanup",
        "",
        "This manifest captures the untouched tracked state of `origin/main` before any file move or deletion.",
        "The cleanup branch was created first. SHA-256 values are file-content hashes; the one broken Git-link",
        "entry is the SHA-256 of its unavailable Git object ID and is labelled explicitly.",
        "",
        f"- Tracked entries: {len(entries)}",
        f"- Total regular-file bytes: {sum(entry.size for entry in entries)}",
        "- External uncommitted model work is audited separately before import.",
        "",
        "## Planned decisions",
        "",
    ]
    for decision, count in sorted(counts.items()):
        lines.append(f"- `{decision}`: {count}")
    lines.extend(
        [
            "",
            "## Important safeguards",
            "",
            "- L796 scientific outputs and failed/diagnostic experiments are retained and moved as a unit.",
            "- Early circuit, ModelDB, morphology-screening, and submission work is archived, not discarded.",
            "- Zero-byte junk and editor backups are the only ordinary-file deletion candidates at this stage.",
            "- L292-E1-LCN, L571-LCN, the separate GRP morphology set, and the Medlock scaffold are imported only after a separate source audit.",
            "",
            "## Complete manifest",
            "",
            "The complete per-file audit is in `repository_audit_before_cleanup.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def duplicate_decision(paths: list[str]) -> tuple[str, str, str]:
    """Classify a byte-identical duplicate group conservatively.

    Args:
        paths: Repository paths sharing one SHA-256.

    Returns:
        Decision, canonical path, and reason.

    Example:
        ``duplicate_decision(["a", "b"])``
    """
    normalized = sorted(paths, key=lambda item: (len(item), item))
    if any("L796/scripts/L796_step5_best_traces/" in item for item in paths):
        preferred = [item for item in paths if "L796/traces/step5_best_traces/" in item]
        if preferred:
            return "remove generated script-output copy", preferred[0], "Canonical trace belongs under traces/, not scripts/."
    if any(item.startswith("submission_week1/") for item in paths):
        preferred = [item for item in paths if not item.startswith("submission_week1/")]
        if preferred:
            return "remove redundant submission-package copy", preferred[0], "Byte-identical evidence is retained in its canonical source area."
    return "retain or review in scientific context", normalized[0], "Byte identity alone does not prove that experiment-specific context is redundant."


def write_duplicates(path: Path, entries: list[Entry]) -> None:
    """Write the required duplicate-file audit.

    Args:
        path: CSV destination.
        entries: Repository audit entries.

    Returns:
        None.

    Example:
        ``write_duplicates(Path("duplicates.csv"), entries)``
    """
    groups: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.size > 0:
            groups[entry.sha256].append(entry)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["SHA256", "paths", "size", "decision", "canonical_path", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for digest, group in sorted(groups.items()):
            if len(group) < 2:
                continue
            paths = [entry.path for entry in group]
            decision, canonical, reason = duplicate_decision(paths)
            writer.writerow(
                {
                    "SHA256": digest,
                    "paths": " | ".join(sorted(paths)),
                    "size": group[0].size,
                    "decision": decision,
                    "canonical_path": canonical,
                    "reason": reason,
                }
            )


def write_source_markdown(path: Path, specs: list[SourceSpec], entries: list[Entry]) -> None:
    """Write a human-readable audit of uncommitted source collections.

    Args:
        path: Markdown destination.
        specs: Audited source descriptions.
        entries: Source audit records.

    Returns:
        None.

    Example:
        ``write_source_markdown(Path('source.md'), specs, entries)``
    """
    counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        counts[entry.decision] += 1
    lines = [
        "# External source collections before import",
        "",
        "These local collections are treated as read-only sources. No source file is deleted or modified by the consolidation.",
        "Generated caches/build products are excluded from Git; all exclusions remain in their original local folders.",
        "",
        "## Collections",
        "",
    ]
    for spec in specs:
        lines.append(f"- `{spec.label}`: `{spec.root}` -> `{spec.destination}`")
    lines.extend(["", "## Decisions", ""])
    for decision, count in sorted(counts.items()):
        lines.append(f"- `{decision}`: {count}")
    lines.extend(
        [
            "",
            "The complete file-level audit, including SHA-256 values, is in `source_collections_before_import.csv`.",
            "Exact duplicate groups within and across the collections are in `source_collection_duplicate_audit.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def retained_files(root: Path) -> list[Path]:
    """List retained regular files while excluding Git and generated build/cache products.

    Args:
        root: Repository root.

    Returns:
        Sorted retained paths.

    Example:
        ``paths = retained_files(Path.cwd())``
    """
    excluded_dirs = {".git", "__pycache__", "x86_64", "arm64", "i686", "node_modules"}
    excluded_names = {
        "repository_manifest.csv",
        "repository_manifest.md",
        "duplicate_file_audit.csv",
        "deletion_manifest.md",
    }
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in excluded_dirs for part in relative.parts):
            continue
        if relative.parent == Path("docs") and relative.name in excluded_names:
            continue
        files.append(path)
    return sorted(files)


def final_status(path: str) -> tuple[str, str, str]:
    """Classify final-file status, origin, and current/history role.

    Args:
        path: POSIX-style repository path.

    Returns:
        Status, source/generated, and current/historical labels.

    Example:
        ``final_status('cells/L571/parameters/final.json')``
    """
    lowered = path.lower()
    file_type = classify_type(path)
    source_generated = "generated" if file_type in {
        "simulation/validation data",
        "figure",
        "rendered report",
        "execution/compilation log",
    } else "source"
    if lowered.startswith("archive/"):
        return "retained archive", source_generated, "historical"
    if "delayed_excitatory_final_35c.json" in lowered:
        return "retained failed gate", "source", "current failed gate"
    if any(token in lowered for token in ("/diagnostic", "one_factor", "/trials/", "step3_", "initial_")):
        return "retained development evidence", source_generated, "historical/diagnostic"
    selected = {
        "l796_final_parameter_set.json",
        "etrc_final_23c.json",
        "etrc_final_35c.json",
        "delayed_excitatory_final_23c.json",
        "l571_final_23c.json",
        "l571_final_35c.json",
    }
    if PurePosixPath(lowered).name in selected:
        return "selected/current", source_generated, "current"
    return "retained", source_generated, "current/supporting"


def build_final_entries(root: Path) -> list[Entry]:
    """Build entries for every retained final file.

    Args:
        root: Repository root.

    Returns:
        Final inventory entries.

    Example:
        ``entries = build_final_entries(Path.cwd())``
    """
    entries: list[Entry] = []
    for full_path in retained_files(root):
        relative = full_path.relative_to(root).as_posix()
        file_type = classify_type(relative)
        status, source_generated, history = final_status(relative)
        entries.append(
            Entry(
                path=relative,
                file_type=file_type,
                size=full_path.stat().st_size,
                sha256=sha256_file(full_path),
                model=classify_model(relative),
                purpose=describe_purpose(relative, file_type),
                decision=status,
                reason=source_generated,
                destination=history,
            )
        )
    return entries


def write_final_manifest(path: Path, entries: list[Entry]) -> None:
    """Write the final retained-file CSV manifest.

    Args:
        path: CSV destination.
        entries: Final entries.

    Returns:
        None.

    Example:
        ``write_final_manifest(Path('manifest.csv'), entries)``
    """
    fields = [
        "path",
        "cell_model",
        "purpose",
        "SHA256",
        "size_bytes",
        "status",
        "source_generated",
        "current_historical",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "path": entry.path,
                    "cell_model": entry.model,
                    "purpose": entry.purpose,
                    "SHA256": entry.sha256,
                    "size_bytes": entry.size,
                    "status": entry.decision,
                    "source_generated": entry.reason,
                    "current_historical": entry.destination,
                }
            )


def write_final_manifest_markdown(path: Path, entries: list[Entry]) -> None:
    """Write a concise summary of the final retained-file manifest.

    Args:
        path: Markdown destination.
        entries: Final entries.

    Returns:
        None.

    Example:
        ``write_final_manifest_markdown(Path('manifest.md'), entries)``
    """
    by_model: dict[str, int] = defaultdict(int)
    for entry in entries:
        by_model[entry.model] += 1
    lines = [
        "# Repository manifest",
        "",
        "The machine-readable CSV records every retained regular file except the manifest files themselves,",
        "which are self-excluded to avoid recursive hashes. Generated Git-ignored build/cache products are also excluded.",
        "",
        f"- Retained files: {len(entries)}",
        f"- Retained bytes: {sum(entry.size for entry in entries)}",
        "",
        "## Files by model/scope",
        "",
    ]
    for model, count in sorted(by_model.items()):
        lines.append(f"- {model}: {count}")
    lines.extend(["", "See `repository_manifest.csv` for paths, purposes, SHA-256 values, sizes, and status labels.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def final_duplicate_decision(paths: list[str]) -> tuple[str, str, str]:
    """Explain one duplicate group remaining after cleanup.

    Args:
        paths: Final paths sharing one digest.

    Returns:
        Decision, canonical path, and reason.

    Example:
        ``final_duplicate_decision(['shared/a.mod', 'external/a.mod'])``
    """
    canonical = sorted(paths, key=lambda item: (item.startswith("archive/"), len(item), item))[0]
    if any(item.startswith("external/medlock_267056_excitatory_scaffold/") for item in paths):
        shared = [item for item in paths if item.startswith("shared/mechanisms/")]
        if shared:
            return "retain justified snapshot duplicate", shared[0], "External scaffold remains independently runnable and preserves its audited upstream snapshot."
    if any("/validation/baseline_v1/" in item for item in paths):
        return "retain validated snapshot", canonical, "Immutable baseline package preserves model-of-record context."
    if any("/results/" in item for item in paths):
        return "retain experiment-context duplicate", canonical, "Byte-identical output occurs in distinct documented protocols or stage directories."
    if all(item.startswith("archive/") for item in paths):
        return "retain archive-context duplicate", canonical, "Historical package context remains scientifically useful."
    return "reviewed and retained", canonical, "No safe context-free deletion was justified after structural deduplication."


def write_final_duplicates(path: Path, entries: list[Entry]) -> None:
    """Write duplicate groups remaining in the final repository.

    Args:
        path: CSV destination.
        entries: Final inventory entries.

    Returns:
        None.

    Example:
        ``write_final_duplicates(Path('duplicates.csv'), entries)``
    """
    groups: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.size > 0:
            groups[entry.sha256].append(entry)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["SHA256", "paths", "size", "decision", "canonical_path", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for digest, group in sorted(groups.items()):
            if len(group) < 2:
                continue
            paths = [entry.path for entry in group]
            decision, canonical, reason = final_duplicate_decision(paths)
            writer.writerow(
                {
                    "SHA256": digest,
                    "paths": " | ".join(sorted(paths)),
                    "size": group[0].size,
                    "decision": decision,
                    "canonical_path": canonical,
                    "reason": reason,
                }
            )


def old_to_final(path: str) -> str:
    """Map an original tracked path to its planned final location.

    Args:
        path: Original repository path.

    Returns:
        Expected final path.

    Example:
        ``old_to_final('L796/README.md')``
    """
    if path in {"README.md", ".gitignore"}:
        return path
    if path.startswith("L796/"):
        return "cells/L796_projection_neuron/" + path[len("L796/") :]
    return "archive/other_exploratory_models/early_project_work/" + path


def duplicate_replacements(output: Path) -> dict[str, str]:
    """Read pre-cleanup duplicate groups into noncanonical-to-canonical mappings.

    Args:
        output: Documentation directory.

    Returns:
        Original path replacement mapping.

    Example:
        ``mapping = duplicate_replacements(Path('docs'))``
    """
    mapping: dict[str, str] = {}
    audit = output / "duplicate_file_audit_before_cleanup.csv"
    with audit.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row["decision"].startswith("remove"):
                continue
            canonical = row["canonical_path"]
            for candidate in row["paths"].split(" | "):
                if candidate != canonical:
                    mapping[candidate] = old_to_final(canonical)
    mapping.update(
        {
            "L796/scripts/L796_step5_all_tuning_candidates.csv": "cells/L796_projection_neuron/results/step5_final_model/L796_step5_all_tuning_candidates.csv",
            "L796/scripts/L796_step5_best_model_features.csv": "cells/L796_projection_neuron/results/step5_final_model/L796_step5_best_model_features.csv",
            "L796/scripts/L796_step5_best_tuned_parameter_set.json": "cells/L796_projection_neuron/parameters/L796_step5_best_tuned_parameter_set.json",
            "L796/scripts/L796_step5_top20_tuned_candidates.csv": "cells/L796_projection_neuron/results/step5_final_model/L796_step5_top20_tuned_candidates.csv",
            "L796/scripts/L796_step5_tuned_AIS_trace_overlay.png": "cells/L796_projection_neuron/figures/step5_final_model/L796_step5_tuned_AIS_trace_overlay.png",
            "L796/scripts/L796_step5_tuned_FI_curve.png": "cells/L796_projection_neuron/figures/step5_final_model/L796_step5_tuned_FI_curve.png",
            "L796/scripts/L796_step5_tuned_frequency_curve.png": "cells/L796_projection_neuron/figures/step5_final_model/L796_step5_tuned_frequency_curve.png",
            "L796/scripts/L796_step5_tuning_report.txt": "cells/L796_projection_neuron/reports/L796_step5_tuning_report.txt",
            "python/01_ball_stick_ap_demo.py.save": "archive/other_exploratory_models/early_project_work/python/01_ball_stick_ap_demo.py",
        }
    )
    return mapping


def write_deletion_manifest(root: Path, output: Path) -> int:
    """Write one explanation for every deleted original tracked entry.

    Args:
        root: Repository root.
        output: Documentation directory.

    Returns:
        Number of deleted entries.

    Example:
        ``count = write_deletion_manifest(Path.cwd(), Path('docs'))``
    """
    replacements = duplicate_replacements(output)
    historical_save = "archive/L796/historical_scripts/L796_step5_1sec_sweep_fixed_1000ms_historical.py"
    shared_prefix = "shared/mechanisms/medlock_267056/"
    rows: list[tuple[str, str, str]] = []
    audit_path = output / "repository_audit_before_cleanup.csv"
    with audit_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            original = row["current_path"]
            if original == "modeldb/2018004":
                rows.append((original, row["reason"], "archive/other_exploratory_models/early_project_work/modeldb/2018004_GITLINK_NOTE.md"))
                continue
            if original == "L796/scripts/L796_step5_1sec_sweep.py.save" and (root / historical_save).is_file():
                continue
            if original.startswith("L796/mechanisms/mods/"):
                expected = shared_prefix + PurePosixPath(original).name
            else:
                expected = old_to_final(original)
            if (root / expected).exists():
                continue
            replacement = replacements.get(original, "")
            reason = row["reason"]
            if replacement:
                reason = "Byte-identical redundant copy removed after SHA-256 verification."
            rows.append((original, reason, replacement))
    lines = [
        "# Deletion manifest",
        "",
        "Every deleted path from the pre-cleanup tracked tree is listed below. Moves and the renamed historical",
        "1000 ms L796 script variant are not deletions. Original content remains recoverable from Git commit `c58e004`.",
        "",
        "| Old path | Reason | Replacement/canonical path |",
        "|---|---|---|",
    ]
    for old, reason, replacement in rows:
        lines.append(f"| `{old}` | {reason.replace('|', '/')} | `{replacement}` |")
    lines.append("")
    (output / "deletion_manifest.md").write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def main() -> int:
    """Generate all before-cleanup inventory artifacts.

    Returns:
        Process exit code.

    Example:
        ``raise SystemExit(main())``
    """
    args = parse_args()
    root = args.root.resolve()
    output = (root / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not args.final:
        entries = build_repository_entries(root)
        write_csv(output / "repository_audit_before_cleanup.csv", entries)
        write_markdown(output / "repository_audit_before_cleanup.md", entries)
        write_duplicates(output / "duplicate_file_audit.csv", entries)
        print(f"Audited {len(entries)} tracked entries in {root}")
    specs = [parse_source_spec(value) for value in args.source]
    if specs:
        source_entries = [entry for spec in specs for entry in build_source_entries(spec)]
        write_csv(output / "source_collections_before_import.csv", source_entries)
        write_source_markdown(output / "source_collections_before_import.md", specs, source_entries)
        write_duplicates(output / "source_collection_duplicate_audit.csv", source_entries)
        print(f"Audited {len(source_entries)} source-collection files")
    if args.final:
        final_entries = build_final_entries(root)
        write_final_manifest(output / "repository_manifest.csv", final_entries)
        write_final_manifest_markdown(output / "repository_manifest.md", final_entries)
        write_final_duplicates(output / "duplicate_file_audit.csv", final_entries)
        deleted = write_deletion_manifest(root, output)
        print(f"Final retained files: {len(final_entries)}; deleted original entries: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
