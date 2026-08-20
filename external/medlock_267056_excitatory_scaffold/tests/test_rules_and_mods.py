"""Validate rule independence and the minimal mechanism inventory."""

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from sdh_exc.cell_rules import build_cell_rules


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MOD_HASHES = {
    "B_NA.mod": "7177506EFAD6B6F60F1B9AC86686617BF5FFC94B8754585E2BB1E3AE6AE77496",
    "borgka.mod": "11229AF171B80435E0D20A472D1D64EEBE90B4ACDC5533877C8804F212A4910D",
    "CaIntraCellDyn.mod": "7A6578DF5A3122EDF4536FF98EDBB42A769C4D23B981A32FC82C1F1779FB6BD5",
    "HH2.mod": "8610826D2F69D7BAE61780022490DB020D5A5BEEFFBECB8CAA396A404E1E27BA",
    "iKCa.mod": "7EF01E9F2129281B83AA4F3080C06203D1096C45F041EADF5B7221C105EC61C8",
    "KDRI.mod": "FC6E0B93628D41F318C64AB134DDAA3E4F9E840BE180FE5857A528AE75A3CE36",
}


class CellRuleTests(unittest.TestCase):
    """Verify the source-derived intrinsic rule behavior."""

    def test_every_population_has_an_independent_rule(self) -> None:
        """Verify mutation of one rule cannot affect another.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_rules_and_mods`
        """
        rules = build_cell_rules()
        self.assertEqual(len(rules), 6)
        rules["ePKCgamma_rule"]["secs"]["soma"]["mechs"]["HH2"][
            "gnabar"
        ] = 99.0
        self.assertNotEqual(
            rules["eVGLUT3_rule"]["secs"]["soma"]["mechs"]["HH2"]["gnabar"],
            99.0,
        )

    def test_five_delayed_rules_share_baseline_content(self) -> None:
        """Verify the five delayed classes reproduce one intrinsic template.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_rules_and_mods`
        """
        rules = build_cell_rules()
        delayed_labels = (
            "ePKCgamma_rule",
            "eVGLUT3_rule",
            "eDOR_rule",
            "eSST_rule",
            "eCR_rule",
        )
        normalized = []
        for label in delayed_labels:
            rule = deepcopy(rules[label])
            rule["conds"] = {}
            normalized.append(rule)
        self.assertTrue(all(rule == normalized[0] for rule in normalized[1:]))

    def test_initial_rule_differs_from_delayed_rule(self) -> None:
        """Verify eTrC retains its distinct initial/transient template.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_rules_and_mods`
        """
        rules = build_cell_rules()
        self.assertNotEqual(
            rules["eTrC_rule"]["secs"]["soma"]["mechs"]["KDRI"]["gkbar"],
            rules["ePKCgamma_rule"]["secs"]["soma"]["mechs"]["KDRI"][
                "gkbar"
            ],
        )


class ModInventoryTests(unittest.TestCase):
    """Verify downloaded ModelDB mechanism provenance."""

    def test_required_mod_hashes(self) -> None:
        """Verify every required MOD file matches the recorded source hash.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_rules_and_mods`
        """
        for filename, expected_hash in EXPECTED_MOD_HASHES.items():
            path = PROJECT_ROOT / "mods" / filename
            self.assertTrue(path.is_file(), filename)
            digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            self.assertEqual(digest, expected_hash, filename)

    def test_mod_files_start_with_title(self) -> None:
        """Verify MOD files follow the project's NMODL header rule.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_rules_and_mods`
        """
        for filename in EXPECTED_MOD_HASHES:
            first_line = (
                PROJECT_ROOT / "mods" / filename
            ).read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(first_line.startswith("TITLE"), filename)


if __name__ == "__main__":
    unittest.main()
