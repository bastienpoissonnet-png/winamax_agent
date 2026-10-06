"""Unit tests for the Discord Webhook notification module."""

import unittest
from unittest.mock import MagicMock, patch
from winamax_agent.models.parlays import ParlayLeg, ParlayOpportunity
from winamax_agent.reporting.discord_notifier import (
    DISCORD_COLOR_GREEN,
    DISCORD_COLOR_YELLOW,
    format_discord_embed,
    send_discord_report,
)
from winamax_agent.reporting.reporter import BetRecommendation, DailyReport


class TestDiscordNotifier(unittest.TestCase):

    def setUp(self):
        self.sample_rec = BetRecommendation(
            competition="Ligue 1",
            match_title="Paris Saint Germain vs Nice",
            kickoff="2026-10-06T20:45:00Z",
            market_name="Total Buts (Sécurisé)",
            selection_label="Moins de 3.5 buts",
            bookmaker="Winamax",
            winamax_odds=1.55,
            raw_implied_prob_pct=64.5,
            fair_bookmaker_prob_pct=60.8,
            model_true_prob_pct=65.1,
            edge_pct=4.3,
            ev_pct=0.87,
            stake_eur=10.0,
            stake_details="Palier haute confiance",
            point_1_xg="xG justification",
            point_2_h2h_tactics="H2H justification",
            point_3_context_form="Form justification",
            is_fallback=False,
        )

        self.sample_parlay = ParlayOpportunity(
            legs=[
                ParlayLeg(
                    match_title="Arsenal vs Chelsea",
                    competition="Premier League",
                    kickoff="2026-10-07T17:30:00Z",
                    market_type="Double Chance",
                    selection="Arsenal ou Nul (1X)",
                    odds=1.35,
                    model_true_prob=0.80,
                    fair_prob=0.75,
                ),
                ParlayLeg(
                    match_title="Marseille vs Lyon",
                    competition="Ligue 1",
                    kickoff="2026-10-06T20:45:00Z",
                    market_type="Double Chance",
                    selection="Marseille ou Nul (1X)",
                    odds=1.38,
                    model_true_prob=0.74,
                    fair_prob=0.70,
                ),
            ],
            total_odds=1.86,
            combined_true_prob=0.598,
            combined_fair_prob=0.525,
            combined_ev=0.112,
            recommended_stake=15.0,
            stake_details="Kelly combiné",
            cross_justification="Indépendance garantie",
            is_fallback=False,
        )

        self.sample_report = DailyReport(
            timestamp="2026-10-06 12:00:00",
            total_matches_analyzed=8,
            total_markets_analyzed=86,
            positive_ev_count=10,
            match_of_the_day=self.sample_rec,
            top_recommendation=self.sample_rec,
            top_parlay=self.sample_parlay,
            longshot_recommendation=self.sample_rec,
        )

    def test_format_discord_embed_all_validated(self):
        payload = format_discord_embed(self.sample_report)
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)

        embed = payload["embeds"][0]
        self.assertEqual(embed["color"], DISCORD_COLOR_GREEN)
        self.assertIn("2026-10-06", embed["title"])
        self.assertEqual(len(embed["fields"]), 4)

        # Check fields content
        motd_field = embed["fields"][0]
        self.assertIn("1. LE MATCH DU JOUR", motd_field["name"])
        self.assertIn("🟢 [VALIDÉ]", motd_field["name"])
        self.assertIn("Paris Saint Germain vs Nice", motd_field["value"])
        self.assertIn("10.00 €", motd_field["value"])

        parlay_field = embed["fields"][2]
        self.assertIn("3. LE MEILLEUR COMBINÉ", parlay_field["name"])
        self.assertIn("1.86", parlay_field["value"])
        self.assertIn("15.00 €", parlay_field["value"])

    def test_format_discord_embed_with_fallback(self):
        # Create a report with a fallback selection
        fallback_rec = BetRecommendation(
            competition="Ligue 1",
            match_title="Paris Saint Germain vs Nice",
            kickoff="2026-10-06T20:45:00Z",
            market_name="1X2",
            selection_label="Match Nul",
            bookmaker="Winamax",
            winamax_odds=4.60,
            raw_implied_prob_pct=21.7,
            fair_bookmaker_prob_pct=20.9,
            model_true_prob_pct=20.5,
            edge_pct=-0.4,
            ev_pct=-5.7,
            stake_eur=1.00,
            stake_details="Mise symbolique",
            point_1_xg="xG",
            point_2_h2h_tactics="Tactics",
            point_3_context_form="Form",
            is_fallback=True,
            warning_message="⚠️ Option de secours sous-optimale",
        )
        report_with_fb = DailyReport(
            timestamp="2026-10-06 12:00:00",
            total_matches_analyzed=8,
            total_markets_analyzed=86,
            positive_ev_count=0,
            match_of_the_day=fallback_rec,
            top_recommendation=fallback_rec,
            top_parlay=None,
            longshot_recommendation=fallback_rec,
        )

        payload = format_discord_embed(report_with_fb)
        embed = payload["embeds"][0]
        self.assertEqual(embed["color"], DISCORD_COLOR_YELLOW)
        self.assertIn("🟡 [SECOURS]", embed["fields"][0]["name"])
        self.assertIn("Choix de secours", embed["fields"][0]["value"])

    def test_send_discord_report_empty_url(self):
        # Empty or placeholder URL returns False without making network request
        self.assertFalse(send_discord_report(self.sample_report, webhook_url=""))
        self.assertFalse(send_discord_report(self.sample_report, webhook_url=None))
        self.assertFalse(send_discord_report(self.sample_report, webhook_url="https://discord.com/api/webhooks/votre_webhook_ici"))

    @patch("urllib.request.urlopen")
    def test_send_discord_report_success_urllib(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = send_discord_report(self.sample_report, webhook_url="https://discord.com/api/webhooks/123/abc")
        self.assertTrue(res)
        mock_urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()

