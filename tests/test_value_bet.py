"""Unit tests for Value Bet evaluation."""

import unittest
from winamax_agent.models.value_bet import evaluate_bet


class TestValueBetEvaluation(unittest.TestCase):

    def test_positive_ev_detection(self):
        # Odds 2.50, fair prob 0.40, model true prob 0.48
        # EV = (0.48 * 2.50) - 1.0 = 1.20 - 1.0 = +20.0%
        # Edge = 0.48 - 0.40 = +8.0%
        opp = evaluate_bet(
            competition="Ligue 1",
            home_team="Marseille",
            away_team="Lyon",
            market_type="1X2",
            selection="Victoire Marseille",
            selection_key="home",
            winamax_odds=2.50,
            fair_bookmaker_prob=0.40,
            model_true_prob=0.48,
            min_ev_threshold=0.0,
        )
        self.assertTrue(opp.is_value)
        self.assertAlmostEqual(opp.ev_pct, 20.0, places=2)
        self.assertAlmostEqual(opp.edge_pct, 8.0, places=2)

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
        self.assertAlmostEqual(opp.ev_pct, -10.0, places=2)


if __name__ == "__main__":
    unittest.main()
