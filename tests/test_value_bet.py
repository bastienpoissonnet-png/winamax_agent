"""Unit tests for Solid Value Bet evaluation."""

import unittest
from winamax_agent.models.value_bet import evaluate_bet


class TestValueBetEvaluation(unittest.TestCase):

    def test_solid_positive_ev_detection(self):
        # Cote 1.75, fair prob 0.58, model true prob 0.64
        # EV = (0.64 * 1.75) - 1.0 = 1.12 - 1.0 = +12.0%
        # Edge = 0.64 - 0.58 = +6.0%
        # Répond à tous les critères : cote dans [1.30, 2.30], probabilité >= 55%
        opp = evaluate_bet(
            competition="Ligue 1",
            home_team="Marseille",
            away_team="Lyon",
            market_type="1X2",
            selection="Victoire Marseille",
            selection_key="home",
            winamax_odds=1.75,
            fair_bookmaker_prob=0.58,
            model_true_prob=0.64,
            min_ev_threshold=0.0,
            min_odds=1.30,
            max_odds=2.30,
            min_prob_threshold=0.55,
        )
        self.assertTrue(opp.is_value)
        self.assertAlmostEqual(opp.ev_pct, 12.0, places=2)
        self.assertAlmostEqual(opp.edge_pct, 6.0, places=2)

    def test_negative_ev_rejection(self):
        # Odds 1.80, model true prob 0.50
        # EV = (0.50 * 1.80) - 1.0 = -10.0%
        opp = evaluate_bet(
            competition="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            market_type="1X2",
            selection="Victoire Arsenal",
            selection_key="home",
            winamax_odds=1.80,
            fair_bookmaker_prob=0.55,
            model_true_prob=0.50,
            min_ev_threshold=0.0,
        )
        self.assertFalse(opp.is_value)
        self.assertIn("EV non positive", opp.rejection_reason)

    def test_rejection_of_low_probability_despite_positive_ev(self):
        # Cote 2.20, probabilité 0.50 < 0.55 -> EV = +10%, mais rejeté car probabilité trop faible
        opp = evaluate_bet(
            competition="Ligue 1",
            home_team="Rennes",
            away_team="Strasbourg",
            market_type="1X2",
            selection="Victoire Rennes",
            selection_key="home",
            winamax_odds=2.20,
            fair_bookmaker_prob=0.45,
            model_true_prob=0.50,
            min_ev_threshold=0.0,
            min_prob_threshold=0.55,
        )
        self.assertFalse(opp.is_value)
        self.assertIn("Probabilité trop faible", opp.rejection_reason)

    def test_rejection_of_excessive_odds_outsider(self):
        # Cote 4.50 ou 21.00 (Outsider) rejeté catégoriquement
        opp = evaluate_bet(
            competition="Coupe de France",
            home_team="Paris Saint Germain",
            away_team="Le Mans FC",
            market_type="1X2",
            selection="Victoire Le Mans FC",
            selection_key="away",
            winamax_odds=21.00,
            fair_bookmaker_prob=0.04,
            model_true_prob=0.55,
            min_ev_threshold=0.0,
            max_odds=2.30,
        )
        self.assertFalse(opp.is_value)
        self.assertIn("Cote trop élevée", opp.rejection_reason)


if __name__ == "__main__":
    unittest.main()
