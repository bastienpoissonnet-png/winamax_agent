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

    def test_anti_surprise_filter_rejects_losing_streak(self):
        # Équipe sur une série de défaites : victoire sèche rejetée malgré EV > 0
        opp = evaluate_bet(
            competition="Ligue 1",
            home_team="Nantes",
            away_team="Reims",
            market_type="1X2 (Résultat)",
            selection="Victoire Nantes (1)",
            selection_key="home",
            winamax_odds=2.10,
            fair_bookmaker_prob=0.45,
            model_true_prob=0.58,  # EV = +21.8%
            min_ev_threshold=0.0,
            min_odds=1.50,
            max_odds=3.00,
            min_prob_threshold=0.40,
            team_streak="N-V-N-D-D",  # se termine par 2 défaites consécutives
            wins_l5=1,
            losses_l5=2,
            recent_form_points=5.0,
        )
        self.assertFalse(opp.is_value)
        self.assertIn("Cohérence sportive", opp.rejection_reason)
        self.assertIn("série de défaites", opp.rejection_reason)

    def test_anti_surprise_filter_rejects_zero_recent_wins(self):
        # Équipe sans aucune victoire récente : victoire sèche rejetée malgré EV > 0
        opp = evaluate_bet(
            competition="Premier League",
            home_team="Everton",
            away_team="Wolves",
            market_type="1X2 (Résultat)",
            selection="Victoire Everton (1)",
            selection_key="home",
            winamax_odds=2.00,
            fair_bookmaker_prob=0.48,
            model_true_prob=0.56,
            min_ev_threshold=0.0,
            min_odds=1.50,
            max_odds=3.00,
            min_prob_threshold=0.40,
            team_streak="N-D-N-D-N",
            wins_l5=0,
            losses_l5=2,
            recent_form_points=3.0,
        )
        self.assertFalse(opp.is_value)
        self.assertIn("Cohérence sportive", opp.rejection_reason)
        self.assertIn("aucune victoire récente", opp.rejection_reason)

    def test_anti_surprise_filter_accepts_positive_momentum(self):
        # Équipe en dynamique positive : victoire sèche acceptée
        opp = evaluate_bet(
            competition="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            market_type="1X2 (Résultat)",
            selection="Victoire Arsenal (1)",
            selection_key="home",
            winamax_odds=1.80,
            fair_bookmaker_prob=0.52,
            model_true_prob=0.62,
            min_ev_threshold=0.0,
            min_odds=1.50,
            max_odds=3.00,
            min_prob_threshold=0.40,
            team_streak="V-V-V-V-D",
            wins_l5=4,
            losses_l5=1,
            recent_form_points=12.0,
        )
        self.assertTrue(opp.is_value)
        self.assertEqual(opp.rejection_reason, "")

    def test_anti_surprise_filter_does_not_block_double_chance(self):
        # Double Chance n'est pas une victoire sèche : non rejetée par l'anti-surprise
        opp = evaluate_bet(
            competition="Ligue 1",
            home_team="Nantes",
            away_team="Reims",
            market_type="Double Chance (Sécurisation)",
            selection="Nantes ou Nul (1X)",
            selection_key="1x",
            winamax_odds=1.40,
            fair_bookmaker_prob=0.68,
            model_true_prob=0.75,
            min_ev_threshold=0.0,
            min_odds=1.30,
            max_odds=3.00,
            min_prob_threshold=0.40,
            team_streak="D-D-D-N-D",
            wins_l5=0,
            losses_l5=4,
            recent_form_points=1.0,
        )
        self.assertTrue(opp.is_value)


if __name__ == "__main__":
    unittest.main()

