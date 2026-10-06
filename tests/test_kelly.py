"""Unit tests for risk-adjusted Fractional Kelly staking calculations, bounds, and rules."""

import unittest
from winamax_agent.staking.kelly import calculate_kelly_stake


class TestKellyStaking(unittest.TestCase):

    def test_ev_negative_or_zero_returns_zero_stake(self):
        # Odds 1.80, true prob 0.50 -> EV = (0.50 * 1.80) - 1.0 = -0.10 <= 0
        res = calculate_kelly_stake(
            true_prob=0.50,
            odds=1.80,
            bankroll=500.0,
            kelly_multiplier=0.50,
        )
        self.assertEqual(res.final_stake_eur, 0.0)
        self.assertTrue(res.is_rejected)

    def test_rejection_of_odds_out_of_bounds(self):
        # Cote > 3.00 (ex: Le Mans à 21.00 ou Bratislava à 7.70)
        res_21 = calculate_kelly_stake(true_prob=0.60, odds=21.00, bankroll=500.0)
        self.assertEqual(res_21.final_stake_eur, 0.0)
        self.assertTrue(res_21.is_rejected)

        res_7 = calculate_kelly_stake(true_prob=0.60, odds=7.70, bankroll=500.0)
        self.assertEqual(res_7.final_stake_eur, 0.0)
        self.assertTrue(res_7.is_rejected)

        # Cote < 1.50 (hors sweet spot [1.50, 3.00])
        res_low = calculate_kelly_stake(true_prob=0.85, odds=1.35, bankroll=500.0)
        self.assertEqual(res_low.final_stake_eur, 0.0)
        self.assertTrue(res_low.is_rejected)

    def test_rejection_of_low_probability(self):
        # Cote 2.20 mais probabilité 0.35 < 0.40 requis
        res = calculate_kelly_stake(true_prob=0.35, odds=2.20, bankroll=500.0)
        self.assertEqual(res.final_stake_eur, 0.0)
        self.assertTrue(res.is_rejected)

        # Cote < 1.70 (ex: 1.55) mais probabilité 0.55 < 0.60 requis
        res_low_odds = calculate_kelly_stake(true_prob=0.55, odds=1.55, bankroll=500.0)
        self.assertEqual(res_low_odds.final_stake_eur, 0.0)
        self.assertTrue(res_low_odds.is_rejected)

    def test_tier_1_high_confidence_bracket(self):
        # Cote 1.65 (dans [1.50, 1.85]), probabilité 0.72 >= 0.60
        # Autorisé entre 10 € et 20 €
        res = calculate_kelly_stake(
            true_prob=0.72,
            odds=1.65,
            bankroll=500.0,
            kelly_multiplier=0.50,
        )
        self.assertFalse(res.is_rejected)
        self.assertGreaterEqual(res.final_stake_eur, 10.0)
        self.assertLessEqual(res.final_stake_eur, 20.0)

    def test_tier_2_cap_at_10_euros(self):
        # Cote 2.00 (dans [1.86, 2.30]), probabilité 0.62 >= 0.40
        # Plafonné strictement à 10 € max
        res = calculate_kelly_stake(
            true_prob=0.62,
            odds=2.00,
            bankroll=1000.0,
            kelly_multiplier=0.50,
        )
        self.assertFalse(res.is_rejected)
        self.assertEqual(res.final_stake_eur, 10.00)
        self.assertTrue(res.is_capped)

    def test_tier_3_cap_at_5_euros(self):
        # Cote 2.60 (dans [2.31, 3.00]), probabilité 0.48 >= 0.40
        # Plafonné strictement à 5 € max
        res = calculate_kelly_stake(
            true_prob=0.48,
            odds=2.60,
            bankroll=1000.0,
            kelly_multiplier=0.50,
        )
        self.assertFalse(res.is_rejected)
        self.assertEqual(res.final_stake_eur, 5.00)
        self.assertTrue(res.is_capped)

    def test_parlay_kelly_staking(self):
        from winamax_agent.staking.kelly import calculate_parlay_kelly_stake
        # Combiné cote 2.40, probabilité 0.52 -> EV = (0.52 * 2.40) - 1.0 = +24.8%
        res = calculate_parlay_kelly_stake(
            parlay_true_prob=0.52,
            parlay_odds=2.40,
            bankroll=500.0,
            max_stake=15.0,
        )
        self.assertFalse(res.is_rejected)
        self.assertGreaterEqual(res.final_stake_eur, 1.0)
        self.assertLessEqual(res.final_stake_eur, 15.0)

        # Combiné hors plage (cote 4.50 > 4.00) rejeté
        res_high = calculate_parlay_kelly_stake(
            parlay_true_prob=0.30,
            parlay_odds=4.50,
            bankroll=500.0,
        )
        self.assertTrue(res_high.is_rejected)
        self.assertEqual(res_high.final_stake_eur, 0.0)

    def test_micro_kelly_staking(self):
        from winamax_agent.staking.kelly import calculate_micro_kelly_stake
        # Cote osée 4.60, probabilité 0.23 -> EV = (0.23 * 4.60) - 1.0 = +5.8%
        res = calculate_micro_kelly_stake(
            true_prob=0.23,
            odds=4.60,
            bankroll=500.0,
            kelly_multiplier=0.15,
            max_stake=5.00,
        )
        self.assertFalse(res.is_rejected)
        self.assertGreaterEqual(res.final_stake_eur, 1.0)
        self.assertLessEqual(res.final_stake_eur, 5.0)

        # Cote < 4.00 rejetée
        res_low = calculate_micro_kelly_stake(
            true_prob=0.35,
            odds=3.20,
            bankroll=500.0,
        )
        self.assertTrue(res_low.is_rejected)
        self.assertEqual(res_low.final_stake_eur, 0.0)

        # Cote trop extrême (> 10.00 max, ex: 10.50, 13.50, 21.00) rejetée
        res_extreme = calculate_micro_kelly_stake(
            true_prob=0.10,
            odds=13.50,
            bankroll=500.0,
        )
        self.assertTrue(res_extreme.is_rejected)
        self.assertEqual(res_extreme.final_stake_eur, 0.0)

        res_21 = calculate_micro_kelly_stake(
            true_prob=0.10,
            odds=21.00,
            bankroll=500.0,
        )
        self.assertTrue(res_21.is_rejected)
        self.assertEqual(res_21.final_stake_eur, 0.0)

    def test_fallback_staking(self):
        from winamax_agent.staking.kelly import calculate_fallback_stake
        res = calculate_fallback_stake(fallback_amount=1.00, max_fallback=2.00, reason_prefix="Secours test")
        self.assertFalse(res.is_rejected)
        self.assertEqual(res.final_stake_eur, 1.00)
        self.assertTrue(res.is_capped)
        self.assertIn("Mise symbolique de secours", res.reason)

        # Capped at max_fallback (2.00 €)
        res_capped = calculate_fallback_stake(fallback_amount=5.00, max_fallback=2.00)
        self.assertEqual(res_capped.final_stake_eur, 2.00)


if __name__ == "__main__":
    unittest.main()

