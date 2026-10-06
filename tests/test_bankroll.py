"""Unit tests for the Bankroll Tracker module, CLI, and configuration priority."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from winamax_agent.bankroll import load_or_init_bankroll, record_bet, save_bankroll
from winamax_agent.config import AgentConfig
from winamax_agent.reporting.discord_notifier import generate_github_issue_url, format_discord_embed
from winamax_agent.reporting.reporter import BetRecommendation, DailyReport


class TestBankrollTracker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bankroll_file = Path(self.temp_dir.name) / "bankroll.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_missing_bankroll_file(self):
        """Initializes default bankroll JSON structure if file does not exist."""
        self.assertFalse(self.bankroll_file.exists())
        data = load_or_init_bankroll(filepath=self.bankroll_file, default_initial=50.0)

        self.assertTrue(self.bankroll_file.exists())
        self.assertEqual(data["initial_bankroll"], 50.0)
        self.assertEqual(data["current_bankroll"], 50.0)
        self.assertEqual(data["total_profit"], 0.0)
        self.assertEqual(data["history"], [])

    def test_record_bet_win(self):
        """Recording a winning bet increases balance and calculates net profit."""
        load_or_init_bankroll(filepath=self.bankroll_file, default_initial=50.0)

        # Record a winning bet of 10.0 € @ 2.10 -> net profit = 10 * 1.10 = 11.00 €
        data = record_bet(
            selection="Atlético Madrid",
            stake=10.0,
            odds=2.10,
            status="win",
            filepath=self.bankroll_file,
        )

        self.assertEqual(data["current_bankroll"], 61.0)
        self.assertEqual(data["total_profit"], 11.0)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["selection"], "Atlético Madrid")
        self.assertEqual(data["history"][0]["net_profit"], 11.0)
        self.assertEqual(data["history"][0]["status"], "win")

    def test_record_bet_loss(self):
        """Recording a losing bet decreases balance and updates total profit."""
        load_or_init_bankroll(filepath=self.bankroll_file, default_initial=50.0)

        # Record a lost bet of 10.0 €
        data = record_bet(
            selection="Liverpool",
            stake=10.0,
            odds=1.85,
            status="loss",
            filepath=self.bankroll_file,
        )

        self.assertEqual(data["current_bankroll"], 40.0)
        self.assertEqual(data["total_profit"], -10.0)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["net_profit"], -10.0)
        self.assertEqual(data["history"][0]["status"], "loss")

    def test_record_bet_pending(self):
        """Recording a pending bet archives the entry without altering balance."""
        load_or_init_bankroll(filepath=self.bankroll_file, default_initial=50.0)

        data = record_bet(
            selection="Arsenal",
            stake=10.0,
            odds=1.65,
            status="pending",
            filepath=self.bankroll_file,
        )

        self.assertEqual(data["current_bankroll"], 50.0)
        self.assertEqual(data["total_profit"], 0.0)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["net_profit"], 0.0)
        self.assertEqual(data["history"][0]["status"], "pending")

    def test_record_bet_invalid_status_raises(self):
        """Invalid bet status raises ValueError."""
        load_or_init_bankroll(filepath=self.bankroll_file, default_initial=50.0)
        with self.assertRaises(ValueError):
            record_bet(
                selection="Arsenal",
                stake=10.0,
                odds=1.50,
                status="cancelled",
                filepath=self.bankroll_file,
            )

    def test_config_priority_reads_bankroll_json(self):
        """AgentConfig reads active bankroll from bankroll.json in priority over TOTAL_BANKROLL."""
        save_bankroll(
            {"initial_bankroll": 50.0, "current_bankroll": 73.5, "total_profit": 23.5, "history": []},
            filepath=self.bankroll_file,
        )

        os.environ["BANKROLL_FILE"] = str(self.bankroll_file)
        os.environ["TOTAL_BANKROLL"] = "500.0"

        try:
            cfg = AgentConfig.from_env()
            self.assertEqual(cfg.total_bankroll, 73.5)
        finally:
            os.environ.pop("BANKROLL_FILE", None)
            os.environ.pop("TOTAL_BANKROLL", None)

    def test_github_issue_url_format(self):
        """generate_github_issue_url formats the issue URL as expected."""
        url = generate_github_issue_url(
            match="Paris Saint Germain vs Nice",
            selection="Moins de 3.5 buts",
            stake=10.0,
            odds=1.55,
            repo_owner="bastienpoissonnet-png",
            repo_name="winamax_agent",
        )
        expected_prefix = "https://github.com/bastienpoissonnet-png/winamax_agent/issues/new?title=[PARI]+Paris+Saint+Germain+vs+Nice+Moins+de+3.5+buts"
        expected_body = "&body=Mise:+10.00€+|+Cote:+1.55"

        self.assertEqual(url, expected_prefix + expected_body)

    def test_discord_header_displays_bankroll(self):
        """Header embed displays current bankroll and profit."""
        rec = BetRecommendation(
            competition="Ligue 1",
            match_title="Marseille vs Lyon",
            kickoff="2026-10-06T20:45:00Z",
            market_name="Double Chance",
            selection_label="Marseille ou Nul (1X)",
            bookmaker="Winamax",
            winamax_odds=1.38,
            raw_implied_prob_pct=72.4,
            fair_bookmaker_prob_pct=70.0,
            model_true_prob_pct=74.0,
            edge_pct=4.0,
            ev_pct=2.1,
            stake_eur=10.0,
            stake_details="Palier 2",
            point_1_xg="",
            point_2_h2h_tactics="",
            point_3_context_form="",
        )
        report = DailyReport(
            timestamp="2026-10-07 10:00:00",
            total_matches_analyzed=5,
            total_markets_analyzed=50,
            positive_ev_count=3,
            match_of_the_day=rec,
            top_recommendation=rec,
            current_bankroll=65.50,
            total_profit=15.50,
        )
        payload = format_discord_embed(report)
        header = payload["embeds"][0]
        self.assertIn("💼 **Solde :** 65.50 € (+15.50 €)", header["description"])

        # Check GitHub issue links on MOTD and Pari Simple
        motd = payload["embeds"][1]
        self.assertIn("🔗 [Enregistrer ce pari sur GitHub](https://github.com/", motd["description"])
        single = payload["embeds"][2]
        self.assertIn("🔗 [Enregistrer ce pari sur GitHub](https://github.com/", single["description"])


if __name__ == "__main__":
    unittest.main()

