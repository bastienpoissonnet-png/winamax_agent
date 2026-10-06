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

        # Check console rendering does not fail
        console_output = report.render_console()
        self.assertIn("WINAMAX VALUE BETTING AGENT", console_output)

        if report.top_recommendation:
            rec = report.top_recommendation
            # Check staking constraints
            self.assertGreaterEqual(rec.stake_eur, 1.0)
            self.assertLessEqual(rec.stake_eur, 20.0)
            self.assertGreater(rec.ev_pct, 0.0)

            # Check 3-point analytical justifications are present
            self.assertTrue(len(rec.point_1_xg) > 20)
            self.assertTrue(len(rec.point_2_h2h_tactics) > 20)
            self.assertTrue(len(rec.point_3_context_form) > 20)

        # Test Markdown and JSON exports
        md_file = Path(self.temp_dir) / "test_report.md"
        json_file = Path(self.temp_dir) / "test_report.json"

        export_to_markdown(report, md_file)
        export_to_json(report, json_file)

        self.assertTrue(md_file.exists())
        self.assertTrue(json_file.exists())
        self.assertGreater(md_file.stat().st_size, 100)
        self.assertGreater(json_file.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
