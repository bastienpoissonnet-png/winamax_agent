"""Unit tests for the Discord Webhook notification module."""

import unittest
from unittest.mock import MagicMock, patch
from winamax_agent.models.parlays import ParlayLeg, ParlayOpportunity
from winamax_agent.reporting.discord_notifier import (
    DISCORD_COLOR_GRAY,
    DISCORD_COLOR_GREEN,
    DISCORD_COLOR_YELLOW,
    format_compact_selection,
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
            pitch_dynamic="Nice concède très peu d'occasions franches à l'extérieur.",
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
            cross_justification="Indépendance garantie entre Premier League et Ligue 1.",
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
        # 5 distinct embeds: Header, MOTD, Top Rec, Parlay, Longshot
        self.assertEqual(len(payload["embeds"]), 5)

        # Embed 0: Header compact
        header = payload["embeds"][0]
        self.assertEqual(header["color"], DISCORD_COLOR_GREEN)
        self.assertIn("2026-10-06", header["title"])
        self.assertIn("Marchés scannés :", header["description"])
        self.assertIn("Opportunités EV > 0 :", header["description"])
        self.assertIn("Solde :", header["description"])

        # Embed 1: Match du Jour
        motd = payload["embeds"][1]
        self.assertEqual(motd["color"], DISCORD_COLOR_GREEN)
        self.assertEqual(motd["title"], "MATCH DU JOUR [VALIDÉ]")
        self.assertIn("Paris Saint Germain vs Nice", motd["description"])
        self.assertIn("SELECTION", motd["description"])
        self.assertIn("COTE", motd["description"])
        self.assertIn("EV", motd["description"])
        self.assertIn("PROB", motd["description"])
        self.assertIn("Moins de 3.5 buts", motd["description"])
        self.assertIn("1.55", motd["description"])
        self.assertIn("💰 **Mise : 10.00 €**", motd["description"])
        self.assertIn("issues/new?title=[PARI]", motd["description"])
        self.assertIn("Enregistrer ce pari sur GitHub", motd["description"])
        self.assertIn("🏟️ *Nice concède très peu d'occasions", motd["description"])

        # Embed 2: Meilleur Pari Simple
        single = payload["embeds"][2]
        self.assertEqual(single["color"], DISCORD_COLOR_GREEN)
        self.assertEqual(single["title"], "PARI SIMPLE [VALIDÉ]")
        self.assertIn("Paris Saint Germain vs Nice", single["description"])
        self.assertIn("💰 **Mise : 10.00 €**", single["description"])
        self.assertIn("issues/new?title=[PARI]", single["description"])
        self.assertIn("Enregistrer ce pari sur GitHub", single["description"])

        # Embed 3: Combiné
        parlay = payload["embeds"][3]
        self.assertEqual(parlay["color"], DISCORD_COLOR_GREEN)
        self.assertEqual(parlay["title"], "COMBINÉ [VALIDÉ]")
        self.assertIn("MATCH", parlay["description"])
        self.assertIn("PARI", parlay["description"])
        self.assertIn("COTE", parlay["description"])
        self.assertIn("Arsenal vs Chelsea", parlay["description"])
        self.assertIn("Marseille vs Lyon", parlay["description"])
        self.assertIn("COTE TOTALE : 1.86 | EV : +11.2%", parlay["description"])
        self.assertIn("💰 **Mise conseillée : 15.00 €**", parlay["description"])

        # Embed 4: Cote Osée
        longshot = payload["embeds"][4]
        self.assertEqual(longshot["color"], DISCORD_COLOR_GREEN)
        self.assertEqual(longshot["title"], "COTE OSÉE [VALIDÉ]")
        self.assertIn("Paris Saint Germain vs Nice", longshot["description"])
        self.assertIn("💰 **Mise : 10.00 €**", longshot["description"])

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
        self.assertEqual(len(payload["embeds"]), 5)

        # Header embed is yellow due to fallback
        self.assertEqual(payload["embeds"][0]["color"], DISCORD_COLOR_YELLOW)

        # MOTD embed has fallback status and yellow color
        self.assertEqual(payload["embeds"][1]["title"], "MATCH DU JOUR [SECOURS]")
        self.assertEqual(payload["embeds"][1]["color"], DISCORD_COLOR_YELLOW)
        self.assertIn("💰 **Mise : 1.00 €** *(Option de secours)*", payload["embeds"][1]["description"])

        # Parlay embed is gray (no parlay)
        self.assertEqual(payload["embeds"][3]["title"], "COMBINÉ [AUCUN COMBINÉ]")
        self.assertEqual(payload["embeds"][3]["color"], DISCORD_COLOR_GRAY)
        self.assertIn("💰 **Mise : 0.00 €**", payload["embeds"][3]["description"])

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
        motd_embed = payload["embeds"][1]
        self.assertEqual(motd_embed["title"], "MATCH DU JOUR [AUCUN PARI JOUABLE]")
        self.assertEqual(motd_embed["color"], DISCORD_COLOR_GRAY)
        self.assertIn("cotes < 1.05 ou calendrier vide", motd_embed["description"])
        self.assertIn("💰 **Mise : 0.00 €**", motd_embed["description"])

    def test_format_compact_selection(self):
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
        # 6 distinct embeds when secondary recommendations exist
        self.assertEqual(len(payload["embeds"]), 6)

        sec_embed = payload["embeds"][5]
        self.assertEqual(sec_embed["title"], "AUTRES OPPORTUNITÉS (EV > 0)")
        self.assertEqual(sec_embed["color"], DISCORD_COLOR_GREEN)
        self.assertIn("MATCH", sec_embed["description"])
        self.assertIn("PARI", sec_embed["description"])
        self.assertIn("COTE", sec_embed["description"])
        self.assertIn("EV", sec_embed["description"])
        self.assertIn("Lyon vs Nice", sec_embed["description"])
        self.assertIn("Alavés vs Atl. Madrid", sec_embed["description"])
        self.assertIn("1.99", sec_embed["description"])
        self.assertIn("+3.3%", sec_embed["description"])

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
