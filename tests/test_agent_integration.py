"""End-to-end integration tests for the Winamax Betting Agent pipeline."""

import shutil
import tempfile
import unittest
from pathlib import Path
from winamax_agent.agent import WinamaxBettingAgent
from winamax_agent.config import AgentConfig
from winamax_agent.reporting.exporters import export_to_json, export_to_markdown


class TestAgentIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = AgentConfig(
            odds_api_key="",
            simulation_mode=True,
            total_bankroll=500.0,
            kelly_fraction=0.50,
            min_stake=1.0,
            max_stake=20.0,
            min_ev_threshold=0.0,
            output_dir=Path(self.temp_dir),
        )
        self.agent = WinamaxBettingAgent(config=self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_analysis(self):
        report = self.agent.run_daily_analysis()

        # Check report metrics
        self.assertGreater(report.total_matches_analyzed, 0)
        self.assertGreater(report.total_markets_analyzed, 0)

        # Check console rendering does not fail and includes Sections 1, 2, 3, and 4
        console_output = report.render_console()
        self.assertIn("WINAMAX VALUE BETTING AGENT", console_output)
        self.assertIn("SECTION 1 : LE MATCH DU JOUR", console_output)
        self.assertIn("SECTION 2 : LE MEILLEUR PARI SIMPLE", console_output)
        self.assertIn("SECTION 3 : LE MEILLEUR COMBINÉ DU JOUR", console_output)
        self.assertIn("SECTION 4 : LA « COTE OSÉE »", console_output)

        if report.match_of_the_day:
            motd = report.match_of_the_day
            self.assertGreater(motd.stake_eur, 0.0)
            self.assertGreater(motd.ev_pct, 0.0)

        if report.top_recommendation:
            rec = report.top_recommendation
            # Check single bet sweet spot constraints
            self.assertGreaterEqual(rec.stake_eur, 1.0)
            self.assertLessEqual(rec.stake_eur, 20.0)
            self.assertGreaterEqual(rec.winamax_odds, 1.50)
            self.assertLessEqual(rec.winamax_odds, 3.00)
            self.assertGreater(rec.ev_pct, 0.0)

            # Check 3-point analytical justifications are present
            self.assertTrue(len(rec.point_1_xg) > 20)
            self.assertTrue(len(rec.point_2_h2h_tactics) > 20)
            self.assertTrue(len(rec.point_3_context_form) > 20)

        # Check Intelligent Parlay Section 3
        if report.top_parlay:
            parlay = report.top_parlay
            self.assertIn(parlay.legs_count, [2, 3])
            self.assertGreaterEqual(parlay.total_odds, 1.80)
            self.assertLessEqual(parlay.total_odds, 4.00)
            self.assertGreater(parlay.combined_ev, 0.0)
            self.assertGreaterEqual(parlay.recommended_stake, 1.0)
            self.assertLessEqual(parlay.recommended_stake, 15.0)
            self.assertTrue(len(parlay.cross_justification) > 30)

            # Check leg independence (distinct matches)
            match_titles = [leg.match_title for leg in parlay.legs]
            self.assertEqual(len(set(match_titles)), len(match_titles))

        # Check Cote Osée Section 4
        if report.longshot_recommendation:
            ls = report.longshot_recommendation
            self.assertGreaterEqual(ls.winamax_odds, 4.00)
            self.assertGreater(ls.ev_pct, 0.0)
            self.assertGreaterEqual(ls.stake_eur, 1.0)
            self.assertLessEqual(ls.stake_eur, 5.0)

        # Test Markdown and JSON exports
        md_file = Path(self.temp_dir) / "test_report.md"
        json_file = Path(self.temp_dir) / "test_report.json"

        export_to_markdown(report, md_file)
        export_to_json(report, json_file)

        self.assertTrue(md_file.exists())
        self.assertTrue(json_file.exists())
        self.assertGreater(md_file.stat().st_size, 100)
        self.assertGreater(json_file.stat().st_size, 100)

        md_content = md_file.read_text(encoding="utf-8")
        self.assertIn("Section 1 : Le Match du Jour", md_content)
        self.assertIn("Section 2 : Le Meilleur Pari Simple", md_content)
        self.assertIn("Section 3 : Le Meilleur Combiné", md_content)
        self.assertIn("Section 4 : La « Cote Osée »", md_content)
        self.assertIn("OPPORTUNITÉ VALIDÉE", md_content)

    def test_automatic_fallback_when_no_positive_ev(self):
        """Tests that when market is unfavorable (EV > 0 unreachable), all sections produce fallback choices."""
        harsh_config = AgentConfig(
            odds_api_key="",
            simulation_mode=True,
            total_bankroll=500.0,
            kelly_fraction=0.50,
            min_stake=1.0,
            max_stake=20.0,
            min_ev_threshold=0.99,  # Impossible threshold forcing all sections into fallback
            fallback_stake=1.00,
            output_dir=Path(self.temp_dir),
        )
        harsh_agent = WinamaxBettingAgent(config=harsh_config)
        report = harsh_agent.run_daily_analysis()

        # Section 1 : Match du Jour fallback
        self.assertIsNotNone(report.match_of_the_day)
        self.assertTrue(report.match_of_the_day.is_fallback)
        self.assertIn("CHOIX DE SECOURS", report.match_of_the_day.status_badge)
        self.assertEqual(report.match_of_the_day.stake_eur, 1.00)
        self.assertIn("OPTION DE SECOURS", report.match_of_the_day.warning_message)

        # Section 2 : Pari Simple fallback
        self.assertIsNotNone(report.top_recommendation)
        self.assertTrue(report.top_recommendation.is_fallback)
        self.assertIn("CHOIX DE SECOURS", report.top_recommendation.status_badge)
        self.assertEqual(report.top_recommendation.stake_eur, 1.00)
        self.assertIn("OPTION DE SECOURS", report.top_recommendation.warning_message)

        # Section 3 : Combiné fallback
        self.assertIsNotNone(report.top_parlay)
        self.assertTrue(report.top_parlay.is_fallback)
        self.assertIn("CHOIX DE SECOURS", report.top_parlay.status_badge)
        self.assertEqual(report.top_parlay.recommended_stake, 1.00)
        self.assertIn("OPTION DE SECOURS", report.top_parlay.warning_message)

        # Section 4 : Cote Osée fallback
        self.assertIsNotNone(report.longshot_recommendation)
        self.assertTrue(report.longshot_recommendation.is_fallback)
        self.assertIn("CHOIX DE SECOURS", report.longshot_recommendation.status_badge)
        self.assertEqual(report.longshot_recommendation.stake_eur, 1.00)
        self.assertIn("OPTION DE SECOURS", report.longshot_recommendation.warning_message)

        # Verify console output and markdown export
        console_out = report.render_console()
        self.assertIn("CHOIX DE SECOURS", console_out)
        self.assertIn("OPTION DE SECOURS — SOUS-OPTIMALE", console_out)

        fb_md = Path(self.temp_dir) / "harsh_report.md"
        export_to_markdown(report, fb_md)
        fb_content = fb_md.read_text(encoding="utf-8")
        self.assertIn("CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)", fb_content)
        self.assertIn("OPTION DE SECOURS — SOUS-OPTIMALE", fb_content)

    def test_strict_odds_bounds_enforcement(self):
        """Tests that absolute floor (>= 1.05) and daring odds ceiling (<= 10.00) are enforced."""
        # 1. Config defaults
        self.assertEqual(self.config.absolute_min_odds, 1.05)
        self.assertEqual(self.config.longshot_max_odds, 10.00)

        # 2. Run analysis and verify no selection has odds < 1.05
        report = self.agent.run_daily_analysis()
        if report.match_of_the_day:
            self.assertGreaterEqual(report.match_of_the_day.winamax_odds, 1.05)
        if report.top_recommendation:
            self.assertGreaterEqual(report.top_recommendation.winamax_odds, 1.05)
        if report.longshot_recommendation:
            self.assertGreaterEqual(report.longshot_recommendation.winamax_odds, 4.00)
            self.assertLessEqual(report.longshot_recommendation.winamax_odds, 10.00)

        # Verify all secondary recommendations are within [1.05, 10.00] and have EV > 0
        for sec in report.secondary_recommendations:
            self.assertGreaterEqual(sec.winamax_odds, 1.05)
            self.assertLessEqual(sec.winamax_odds, 10.00)
            self.assertGreater(sec.ev_pct, 0.0)

        # 3. If absolute_min_odds is set very high (e.g. 10.00), no match of the day is playable
        high_floor_config = AgentConfig(
            odds_api_key="",
            simulation_mode=True,
            absolute_min_odds=10.00,
            output_dir=Path(self.temp_dir),
        )
        high_floor_agent = WinamaxBettingAgent(config=high_floor_config)
        report_high_floor = high_floor_agent.run_daily_analysis()
        self.assertIsNone(report_high_floor.match_of_the_day)

    def test_env_parsing_of_odds_bounds(self):
        """Tests that from_env parses ABSOLUTE_MIN_ODDS and MAX_DARING_ODDS."""
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"ABSOLUTE_MIN_ODDS": "1.08", "MAX_DARING_ODDS": "9.50"}):
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.absolute_min_odds, 1.08)
            self.assertEqual(cfg.longshot_max_odds, 9.50)


if __name__ == "__main__":
    unittest.main()


