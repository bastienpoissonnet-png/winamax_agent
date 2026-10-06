"""Unit tests for xG Poisson and Dixon-Coles simulation model."""

import unittest
from winamax_agent.models.poisson_xg import (
    TeamMetrics,
    XgPoissonEngine,
    _poisson_pmf,
    _dixon_coles_tau,
)


class TestPoissonXgEngine(unittest.TestCase):

    def setUp(self):
        self.engine = XgPoissonEngine(league_avg_goals=2.70, home_advantage=1.18)

    def test_poisson_pmf(self):
        # Lambda = 2.0, k = 2 -> (4 * exp(-2)) / 2 = 2 * 0.135335 = 0.27067
        p = _poisson_pmf(2, 2.0)
        self.assertAlmostEqual(p, 0.27067, places=4)

    def test_dixon_coles_tau(self):
        # 0-0 adjustment with rho = -0.06
        tau_00 = _dixon_coles_tau(0, 0, 1.5, 1.0, -0.06)
        self.assertAlmostEqual(tau_00, 1.0 - (1.5 * 1.0 * -0.06), places=4)
        # 2-1 adjustment should be 1.0 (unaffected)
        self.assertEqual(_dixon_coles_tau(2, 1, 1.5, 1.0, -0.06), 1.0)

    def test_simulate_match_probabilities_sum_to_one(self):
        home = TeamMetrics(
            name="Paris Saint-Germain",
            xg_for_per_match=2.25,
            xg_against_per_match=0.85,
            recent_form_points=13,
        )
        away = TeamMetrics(
            name="Nice",
            xg_for_per_match=1.35,
            xg_against_per_match=0.92,
            recent_form_points=7,
        )

        sim = self.engine.simulate_match(home, away)

        # 1X2 probabilities must sum to 1.0
        sum_1x2 = sim.prob_home_win + sim.prob_draw + sim.prob_away_win
        self.assertAlmostEqual(sum_1x2, 1.0, places=4)

        # Over + Under 2.5 must sum to 1.0
        sum_totals = sim.prob_over_2_5 + sim.prob_under_2_5
        self.assertAlmostEqual(sum_totals, 1.0, places=4)

        # BTTS Yes + No must sum to 1.0
        sum_btts = sim.prob_btts_yes + sim.prob_btts_no
        self.assertAlmostEqual(sum_btts, 1.0, places=4)

        # Strong home team should have higher win probability
        self.assertGreater(sim.prob_home_win, sim.prob_away_win)


if __name__ == "__main__":
    unittest.main()
