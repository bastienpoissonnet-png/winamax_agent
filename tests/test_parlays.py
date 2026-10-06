"""Unit tests for the Intelligent Accumulator / Parlay Generator module."""

import unittest
from winamax_agent.models.parlays import (
    ParlayLeg,
    ParlayOpportunity,
    find_best_parlays,
    generate_cross_justification,
)


class TestParlaysGenerator(unittest.TestCase):

    def setUp(self):
        self.leg_fra = ParlayLeg(
            match_title="France vs Italie",
            competition="UEFA Nations League",
            kickoff="2026-10-06T20:45:00Z",
            market_type="Double Chance",
            selection="France ou Nul (1X)",
            odds=1.20,
            model_true_prob=0.88,
            fair_prob=0.85,
        )
        self.leg_esp = ParlayLeg(
            match_title="Espagne vs Danemark",
            competition="UEFA Nations League",
            kickoff="2026-10-07T20:45:00Z",
            market_type="1X2",
            selection="Victoire Espagne (1)",
            odds=1.52,
            model_true_prob=0.70,
            fair_prob=0.64,
        )
        self.leg_ars = ParlayLeg(
            match_title="Arsenal vs Chelsea",
            competition="Premier League",
            kickoff="2026-10-07T17:30:00Z",
            market_type="Total Buts",
            selection="Plus de 1.5 buts",
            odds=1.28,
            model_true_prob=0.82,
            fair_prob=0.78,
        )
        self.leg_same_match_esp = ParlayLeg(
            match_title="Espagne vs Danemark",
            competition="UEFA Nations League",
            kickoff="2026-10-07T20:45:00Z",
            market_type="Double Chance",
            selection="Espagne ou Nul (1X)",
            odds=1.13,
            model_true_prob=0.92,
            fair_prob=0.89,
        )
        self.leg_low_prob = ParlayLeg(
            match_title="Marseille vs Lyon",
            competition="Ligue 1",
            kickoff="2026-10-06T20:45:00Z",
            market_type="1X2",
            selection="Victoire Lyon (2)",
            odds=3.50,
            model_true_prob=0.28,
            fair_prob=0.26,
        )

    def test_parlay_combination_generation(self):
        candidate_legs = [self.leg_fra, self.leg_esp, self.leg_ars]
        parlays = find_best_parlays(
            candidate_legs=candidate_legs,
            bankroll=500.0,
            min_odds=1.80,
            max_odds=4.00,
            max_stake=15.0,
            min_leg_prob=0.60,
        )

        self.assertGreater(len(parlays), 0)
        top = parlays[0]

        # Verify odds target [1.80, 4.00]
        self.assertGreaterEqual(top.total_odds, 1.80)
        self.assertLessEqual(top.total_odds, 4.00)

        # Verify EV positive
        self.assertGreater(top.combined_ev, 0.0)

        # Verify stake capped at 15.00 €
        self.assertGreaterEqual(top.recommended_stake, 1.0)
        self.assertLessEqual(top.recommended_stake, 15.0)

        # Verify cross justification
        self.assertIn("Sécurisation croisée", top.cross_justification)

    def test_strict_match_independence(self):
        # Two legs from the exact same fixture (Espagne vs Danemark) must never be combined together
        candidate_legs = [self.leg_esp, self.leg_same_match_esp]
        parlays = find_best_parlays(candidate_legs=candidate_legs)
        self.assertEqual(len(parlays), 0)

    def test_rejection_of_low_probability_legs(self):
        # Lyon win @ 3.50 has prob 0.28 < 0.60 and should be rejected
        candidate_legs = [self.leg_fra, self.leg_low_prob]
        parlays = find_best_parlays(candidate_legs=candidate_legs, min_leg_prob=0.60)
        self.assertEqual(len(parlays), 0)

    def test_find_fallback_parlay(self):
        from winamax_agent.models.parlays import find_fallback_parlay
        candidate_legs = [self.leg_fra, self.leg_esp, self.leg_low_prob]
        fb = find_fallback_parlay(candidate_legs, fallback_stake=1.00)
        self.assertIsNotNone(fb)
        self.assertTrue(fb.is_fallback)
        self.assertEqual(fb.recommended_stake, 1.00)
        self.assertIn("CHOIX DE SECOURS", fb.status_badge)
        self.assertIn("OPTION DE SECOURS", fb.warning_message)
        self.assertEqual(fb.legs_count, 2)
        # Should pick the 2 highest probability legs from distinct matches: leg_fra (0.88) and leg_esp (0.70)
        self.assertEqual(fb.legs[0].match_title, "France vs Italie")
        self.assertEqual(fb.legs[1].match_title, "Espagne vs Danemark")


if __name__ == "__main__":
    unittest.main()


