"""Structural tests for configured population modes."""

import unittest

from sdh_exc.catalog import counts_for_mode, load_population_specs


class PopulationCatalogTests(unittest.TestCase):
    """Verify the six canonical population definitions."""

    def test_six_unique_population_types(self) -> None:
        """Verify exactly six unique canonical cell types.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_catalog`
        """
        specs = load_population_specs()
        self.assertEqual(len(specs), 6)
        self.assertEqual(len({spec.cell_type for spec in specs}), 6)

    def test_expected_mode_totals(self) -> None:
        """Verify exemplar, smoke, and production population totals.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_catalog`
        """
        self.assertEqual(sum(counts_for_mode(mode="exemplar").values()), 6)
        self.assertEqual(sum(counts_for_mode(mode="smoke").values()), 13)
        self.assertEqual(sum(counts_for_mode(mode="production").values()), 109)

    def test_production_counts_match_modeldb(self) -> None:
        """Verify the published ModelDB population composition.

        Args:
            None.

        Returns:
            None.

        Example:
            `python -m unittest tests.test_catalog`
        """
        self.assertEqual(
            counts_for_mode(mode="production"),
            {
                "eTrC": 10,
                "ePKCgamma": 30,
                "eVGLUT3": 4,
                "eDOR": 30,
                "eSST": 15,
                "eCR": 20,
            },
        )


if __name__ == "__main__":
    unittest.main()
