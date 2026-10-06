"""Unit tests for Fractional Kelly staking calculations, bounds, and rules."""

import unittest
from winamax_agent.staking.kelly import calculate_kelly_stake


class TestKellyStaking(unittest.TestCase):

    def test_ev_negative_or_zero_returns_zero_stake(self):
        # Odds 2.0, true prob 0.45 -> EV = (0.45 * 2.0) - 1.0 = -0.10 <= 0
        res = calculate_kelly_stake(
            true_prob=0.45,
            odds=2.0,
            bankroll=500.0,
            kelly_multiplier=0.50,
            min_stake=1.0,
            max_stake=20.0,
        )
        self.assertEqual(res.final_stake_eur, 0.0)
        self.assertEqual(res.raw_stake_eur, 0.0)

    def test_positive_ev_demi_kelly(self):
        # Odds 2.0, true prob 0.55 -> EV = (0.55 * 2.0) - 1.0 = +0.10
        # b = 1.0. Full Kelly = 0.10 / 1.0 = 0.10 (10% of bankroll)
        # Demi-Kelly = 0.50 * 0.10 = 0.05 (5% of bankroll)
        # Bankroll 200 € -> raw stake = 10.00 €
        res = calculate_kelly_stake(
            true_prob=0.55,
            odds=2.0,
            bankroll=200.0,
            kelly_multiplier=0.50,
            min_stake=1.0,
            max_stake=20.0,
        )
        self.assertEqual(res.full_kelly_fraction, 0.10)
        self.assertEqual(res.fractional_kelly, 0.05)
        self.assertEqual(res.raw_stake_eur, 10.00)
        self.assertEqual(res.final_stake_eur, 10.00)
        self.assertFalse(res.is_capped)
        self.assertFalse(res.is_floored)

    def test_strict_cap_of_20_euros(self):
        # Big bankroll 2000 € with edge -> raw stake would be 100 €
        res = calculate_kelly_stake(
            true_prob=0.60,
            odds=2.0,
            bankroll=2000.0,
            kelly_multiplier=0.50,
            min_stake=1.0,
            max_stake=20.0,
        )
        self.assertGreater(res.raw_stake_eur, 20.0)
        self.assertEqual(res.final_stake_eur, 20.0)
        self.assertTrue(res.is_capped)

    def test_floor_of_1_euro_for_positive_ev(self):
        # Small bankroll 20 € with tiny edge -> raw stake would be 0.50 €
        # With positive EV, floor of 1.0 € must be applied
        res = calculate_kelly_stake(
            true_prob=0.52,
            odds=2.0,
            bankroll=20.0,
            kelly_multiplier=0.50,
            min_stake=1.0,
            max_stake=20.0,
        )
        self.assertGreater(res.full_kelly_fraction, 0.0)
        self.assertLess(res.raw_stake_eur, 1.0)
        self.assertEqual(res.final_stake_eur, 1.0)
        self.assertTrue(res.is_floored)


if __name__ == "__main__":
    unittest.main()
