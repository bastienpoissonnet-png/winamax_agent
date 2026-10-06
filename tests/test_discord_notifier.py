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

        # Check fields content - minimaliste et sobre
        motd_field = embed["fields"][0]
        self.assertEqual(motd_field["name"], "MATCH DU JOUR [VALIDÉ]")
        self.assertIn("Paris Saint Germain vs Nice", motd_field["value"])
        self.assertIn("• Pari : Moins de 3.5 buts @ 1.55", motd_field["value"])
        self.assertIn("• Mise : 10.00 € | EV : +0.9%", motd_field["value"])

        single_field = embed["fields"][1]
        self.assertEqual(single_field["name"], "PARI SIMPLE [VALIDÉ]")

        parlay_field = embed["fields"][2]
        self.assertEqual(parlay_field["name"], "COMBINÉ [VALIDÉ]")
        self.assertIn("Cote totale : 1.86 | Prob : 59.8%", parlay_field["value"])
        self.assertIn("• Arsenal ou Nul (1X) @ 1.35", parlay_field["value"])
        self.assertIn("• Marseille ou Nul (1X) @ 1.38", parlay_field["value"])
        self.assertIn("• Mise : 15.00 € | EV : +11.2%", parlay_field["value"])

        longshot_field = embed["fields"][3]
        self.assertEqual(longshot_field["name"], "COTE OSÉE [VALIDÉ]")

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
        self.assertEqual(embed["fields"][0]["name"], "MATCH DU JOUR [SECOURS]")
        self.assertIn("• Mise : 1.00 € (Option de secours)", embed["fields"][0]["value"])
        self.assertEqual(embed["fields"][2]["name"], "COMBINÉ [AUCUN COMBINÉ]")

    def test_format_discord_embed_empty_match_today(self):
        # When no match today or odds < 1.05
        report_no_today = DailyReport(
            timestamp="2026-10-06 12:00:00",
            total_matches_analyzed=8,
            total_markets_analyzed=86,
            positive_ev_count=2,
            match_of_the_day=None,
            top_recommendation=self.sample_rec,
            top_parlay=self.sample_parlay,
            longshot_recommendation=self.sample_rec,
        )
        payload = format_discord_embed(report_no_today)
        embed = payload["embeds"][0]
        motd_field = embed["fields"][0]
        self.assertEqual(motd_field["name"], "MATCH DU JOUR [AUCUN PARI JOUABLE]")
        self.assertIn("cotes < 1.05 ou calendrier vide", motd_field["value"])
        self.assertIn("• Mise : 0.00 €", motd_field["value"])

    def test_format_compact_selection(self):
        from winamax_agent.reporting.discord_notifier import format_compact_selection
        self.assertEqual(format_compact_selection("Nul ou Nice (X2)"), "X2")
        self.assertEqual(format_compact_selection("Alavés ou Nul (1X)"), "1X")
        self.assertEqual(format_compact_selection("Victoire Atl. Madrid (1)"), "1")
        self.assertEqual(format_compact_selection("Victoire Liverpool (2)"), "2")
        self.assertEqual(format_compact_selection("Match Nul (N)"), "N")
        self.assertEqual(format_compact_selection("Plus de 2.5 buts (Over 2.5)"), "+2.5 buts")
        self.assertEqual(format_compact_selection("Moins de 3.5 buts (Under 3.5)"), "-3.5 buts")

    def test_format_discord_embed_with_secondary_opportunities(self):
        sec1 = BetRecommendation(
            competition="Ligue 1",
            match_title="Lyon vs Nice",
            kickoff="2026-10-07T21:00:00Z",
            market_name="Double Chance",
            selection_label="Nul ou Nice (X2)",
            bookmaker="Winamax",
            winamax_odds=1.99,
            raw_implied_prob_pct=50.2,
            fair_bookmaker_prob_pct=48.0,
            model_true_prob_pct=52.0,
            edge_pct=4.0,
            ev_pct=3.3,
            stake_eur=10.0,
            stake_details="Palier 2",
            point_1_xg="xG",
            point_2_h2h_tactics="H2H",
            point_3_context_form="Form",
            is_fallback=False,
        )
        sec2 = BetRecommendation(
            competition="La Liga",
            match_title="Alavés vs Atl. Madrid",
            kickoff="2026-10-07T19:00:00Z",
            market_name="Double Chance",
            selection_label="Alavés ou Nul (1X)",
            bookmaker="Winamax",
            winamax_odds=2.02,
            raw_implied_prob_pct=49.5,
            fair_bookmaker_prob_pct=47.0,
            model_true_prob_pct=51.0,
            edge_pct=4.0,
            ev_pct=1.7,
            stake_eur=10.0,
            stake_details="Palier 2",
            point_1_xg="xG",
            point_2_h2h_tactics="H2H",
            point_3_context_form="Form",
            is_fallback=False,
        )
        report_with_sec = DailyReport(
            timestamp="2026-10-06 12:00:00",
            total_matches_analyzed=8,
            total_markets_analyzed=86,
            positive_ev_count=12,
            match_of_the_day=self.sample_rec,
            top_recommendation=self.sample_rec,
            secondary_recommendations=[sec1, sec2],
            top_parlay=self.sample_parlay,
            longshot_recommendation=self.sample_rec,
        )
        payload = format_discord_embed(report_with_sec)
        embed = payload["embeds"][0]
        self.assertEqual(len(embed["fields"]), 5)

        sec_field = embed["fields"][4]
        self.assertEqual(sec_field["name"], "AUTRES OPPORTUNITÉS (EV > 0)")
        self.assertIn("• Lyon vs Nice : X2 @ 1.99 (+3.3% EV)", sec_field["value"])
        self.assertIn("• Alavés vs Atl. Madrid : 1X @ 2.02 (+1.7% EV)", sec_field["value"])

    def test_send_discord_report_empty_url(self):
        # Empty or placeholder URL returns False without making network request
        self.assertFalse(send_discord_report(self.sample_report, webhook_url=""))
        self.assertFalse(send_discord_report(self.sample_report, webhook_url=None))
        self.assertFalse(send_discord_report(self.sample_report, webhook_url="https://discord.com/api/webhooks/votre_webhook_ici"))

    @patch.dict("sys.modules", {"requests": None})
    @patch("urllib.request.urlopen")
    def test_send_discord_report_success_urllib(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = send_discord_report(self.sample_report, webhook_url="https://discord.com/api/webhooks/123/abc")
        self.assertTrue(res)
        mock_urlopen.assert_called_once()

    @patch("requests.post")
    def test_send_discord_report_success_requests(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_post.return_value = mock_resp

        res = send_discord_report(self.sample_report, webhook_url="https://discord.com/api/webhooks/123/abc")
        self.assertTrue(res)
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()

