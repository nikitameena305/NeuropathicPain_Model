"""Structural and configuration tests that do not require NEURON."""

from __future__ import annotations

import json
import hashlib
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryStructureTests(unittest.TestCase):
    """Verify required model identities, selected parameters, and separation rules."""

    def test_selected_parameters_are_json(self) -> None:
        """Load every selected/current parameter file as JSON."""
        paths = [
            ROOT / "cells/L796_projection_neuron/parameters/L796_final_parameter_set.json",
            ROOT / "cells/L292_E1_excitatory_interneuron/parameters/eTrC/eTrC_final_35C.json",
            ROOT / "cells/L292_E1_excitatory_interneuron/parameters/common/delayed_excitatory_final_35C.json",
            ROOT / "cells/L571_inhibitory_interneuron/parameters/L571_final_23C.json",
            ROOT / "cells/L571_inhibitory_interneuron/parameters/L571_final_35C.json",
            ROOT
            / "cells/23-04-18C-04-cell-1_inhibitory_interneuron/parameters/final/NMO_170087_final_23C.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_required_morphologies_exist(self) -> None:
        """Confirm each production cell retains a non-empty morphology."""
        paths = [
            ROOT / "cells/L796_projection_neuron/morphology/L796-ALT-PN.CNG.swc",
            ROOT / "cells/L292_E1_excitatory_interneuron/morphology/primary/L292-E1-LCN.CNG.swc",
            ROOT / "cells/L571_inhibitory_interneuron/morphology/L571-LCN.CNG.swc",
            ROOT
            / "cells/23-04-18C-04-cell-1_inhibitory_interneuron/morphology/primary/23-04-18C-04-cell-1.CNG.swc",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertGreater(path.stat().st_size, 0)

    def test_grp_reference_is_not_inside_l292(self) -> None:
        """Keep the mouse GRP model out of the L292 production package."""
        l292 = ROOT / "cells/L292_E1_excitatory_interneuron"
        self.assertFalse(any("14-1-15-A-A2sep" in path.name for path in l292.rglob("*")))
        archived = ROOT / "archive/other_exploratory_models/GRP_14-1-15-A-A2sep_and_candidates"
        self.assertTrue(any("14-1-15-A-A2sep" in path.name for path in archived.rglob("*")))

    def test_canonical_mechanisms_and_variants_exist(self) -> None:
        """Verify shared mechanisms and justified L571 variants are present."""
        shared = ROOT / "shared/mechanisms/medlock_267056"
        for filename in ("B_NA.mod", "HH2.mod", "KDRI.mod", "KDR.mod", "iKCa.mod"):
            with self.subTest(filename=filename):
                self.assertTrue((shared / filename).is_file())
        l571 = ROOT / "cells/L571_inhibitory_interneuron/mechanisms"
        self.assertTrue((l571 / "l571_na.mod").is_file())
        self.assertTrue((l571 / "l571_kdr.mod").is_file())

    def test_nmo_170087_provenance_and_final_status(self) -> None:
        """Protect Cell 1 identity, immutable morphology, and provisional status."""
        cell = ROOT / "cells/23-04-18C-04-cell-1_inhibitory_interneuron"
        final = json.loads(
            (cell / "parameters/final/NMO_170087_final_23C.json").read_text(encoding="utf-8")
        )
        source = cell / final["morphology"]["source_file"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual("NMO_170087", final["model_id"])
        self.assertEqual(final["morphology"]["source_sha256"], digest)
        self.assertFalse(final["morphology"]["synthetic_axon"])
        self.assertEqual(
            "cells/L571_inhibitory_interneuron/mechanisms",
            final["active"]["mechanism_dependency"],
        )

        status = json.loads(
            (cell / "results/validation/final_status.json").read_text(encoding="utf-8")
        )
        self.assertEqual("ENGINEERING READY / BIOLOGICALLY PROVISIONAL", status["single_cell_implementation"])
        self.assertEqual("NO", status["network_integration"])
        self.assertTrue((cell / "docs/evidence/evidence_matrix.csv").is_file())
        self.assertTrue((cell / "reports/23-04-18C-04-cell-1_COMPLETE_MODEL_REPORT.docx").is_file())

    def test_no_committed_generated_artifacts(self) -> None:
        """Reject build/cache products from retained project content."""
        forbidden_dirs = {"__pycache__", "x86_64", "arm64", "i686"}
        forbidden_suffixes = {".pyc", ".pyo"}
        violations: list[str] = []
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for value in result.stdout.splitlines():
            path = Path(value)
            if any(part in forbidden_dirs for part in path.parts):
                violations.append(value)
            if path.suffix.lower() in forbidden_suffixes:
                violations.append(value)
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
