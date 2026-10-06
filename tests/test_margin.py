"""Unit tests for margin calculation and margin removal algorithms."""

import unittest
from winamax_agent.models.margin import (
    calculate_overround,
    remove_margin_multiplicative,
    remove_margin_power,
    analyze_market_margin,
)


class TestMarginCalculations(unittest.TestCase):

    def test_calculate_overround(self):
        # 1X2 odds with ~5.73% margin
        odds = [2.00, 3.40, 3.80]
        # 1/2.0 + 1/3.4 + 1/3.8 = 0.50 + 0.294117 + 0.263157 = 1.05727
        overround = calculate_overround(odds)
        self.assertAlmostEqual(overround, 0.05727, places=4)

    def test_remove_margin_multiplicative_sums_to_one(self):
        odds_dict = {"home": 2.10, "draw": 3.40, "away": 3.60}
        fair_probs = remove_margin_multiplicative(odds_dict)
        self.assertAlmostEqual(sum(fair_probs.values()), 1.0, places=6)
        self.assertGreater(fair_probs["home"], fair_probs["draw"])
        self.assertGreater(fair_probs["draw"], fair_probs["away"])

    def test_remove_margin_power_sums_to_one(self):
        odds_dict = {"home": 1.50, "draw": 4.50, "away": 7.00}
        fair_probs = remove_margin_power(odds_dict)
        self.assertAlmostEqual(sum(fair_probs.values()), 1.0, places=4)
        # Favorite in power method gets slightly less penalty than underdog
        self.assertGreater(fair_probs["home"], 0.60)

    def test_analyze_market_margin(self):
        odds = {"home": 1.95, "away": 1.95}
        analysis = analyze_market_margin(odds)
        # 1/1.95 + 1/1.95 = 1.02564 -> margin is ~2.56%
        self.assertAlmostEqual(analysis.margin_pct, 2.564, places=2)
        self.assertAlmostEqual(analysis.fair_probs_multiplicative["home"], 0.50, places=4)
        self.assertAlmostEqual(analysis.fair_probs_multiplicative["away"], 0.50, places=4)

    def test_invalid_odds_raise_error(self):
        with self.assertRaises(ValueError):
            calculate_overround([0.95, 2.0])


if __name__ == "__main__":
    unittest.main()
