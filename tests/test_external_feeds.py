"""Unit tests for Football-Data.org client, Understat client, and name normalizer."""

import unittest
from winamax_agent.ingestion.football_data_client import FootballDataClient
from winamax_agent.ingestion.name_normalizer import canonicalize_team_name, clean_team_name
from winamax_agent.ingestion.understat_client import UnderstatClient


class TestNameNormalizer(unittest.TestCase):

    def test_canonicalize_french_clubs(self):
        self.assertEqual(canonicalize_team_name("Paris Saint Germain"), "Paris Saint-Germain")
        self.assertEqual(canonicalize_team_name("PSG"), "Paris Saint-Germain")
        self.assertEqual(canonicalize_team_name("Olympique de Marseille"), "Olympique de Marseille")
        self.assertEqual(canonicalize_team_name("OM"), "Olympique de Marseille")
        self.assertEqual(canonicalize_team_name("Olympique Lyonnais"), "Olympique Lyonnais")
        self.assertEqual(canonicalize_team_name("OGC Nice"), "OGC Nice")
        self.assertEqual(canonicalize_team_name("RC Lens"), "RC Lens")

    def test_canonicalize_english_clubs(self):
        self.assertEqual(canonicalize_team_name("Arsenal FC"), "Arsenal")
        self.assertEqual(canonicalize_team_name("Chelsea FC"), "Chelsea")
        self.assertEqual(canonicalize_team_name("Manchester City FC"), "Manchester City")
        self.assertEqual(canonicalize_team_name("Man City"), "Manchester City")
        self.assertEqual(canonicalize_team_name("Tottenham Hotspur FC"), "Tottenham Hotspur")

    def test_clean_team_name_strips_noise(self):
        self.assertEqual(clean_team_name("Paris Saint-Germain FC"), "paris saint germain")
        self.assertEqual(clean_team_name("OGC Nice"), "nice")


    def test_canonicalize_national_teams(self):
        self.assertEqual(canonicalize_team_name("France"), "France")
        self.assertEqual(canonicalize_team_name("Italy"), "Italie")
        self.assertEqual(canonicalize_team_name("Italie"), "Italie")
        self.assertEqual(canonicalize_team_name("Spain"), "Espagne")
        self.assertEqual(canonicalize_team_name("Espagne"), "Espagne")
        self.assertEqual(canonicalize_team_name("Belgium"), "Belgique")
        self.assertEqual(canonicalize_team_name("Belgique"), "Belgique")
        self.assertEqual(canonicalize_team_name("Denmark"), "Danemark")
        self.assertEqual(canonicalize_team_name("Danemark"), "Danemark")
        self.assertEqual(canonicalize_team_name("Germany"), "Allemagne")
        self.assertEqual(canonicalize_team_name("Netherlands"), "Pays-Bas")


class TestFootballDataClient(unittest.TestCase):

    def setUp(self):
        # Client without API key uses fallback calibrated database gracefully
        self.client = FootballDataClient(api_key="")

    def test_get_team_form_returns_real_points_and_streak(self):
        form = self.client.get_team_form("Arsenal")
        self.assertIsNotNone(form)
        self.assertEqual(form.team_name, "Arsenal")
        self.assertGreaterEqual(form.points_l5, 0)
        self.assertLessEqual(form.points_l5, 15)
        self.assertTrue(len(form.streak_l5) >= 5)

    def test_unknown_team_returns_none(self):
        form = self.client.get_team_form("Club Inconnu FC 1890")
        self.assertIsNone(form)


class TestFotmobClient(unittest.TestCase):

    def setUp(self):
        from winamax_agent.ingestion.fotmob_client import FotmobClient
        self.client = FotmobClient()

    def test_nations_league_team_metrics(self):
        france_data = self.client.get_team_metrics("France")
        self.assertIsNotNone(france_data)
        self.assertEqual(france_data.team_name, "France")
        self.assertTrue(france_data.is_national_team)
        self.assertGreater(france_data.xg_for_per_match, 1.8)
        self.assertGreaterEqual(france_data.recent_form_points, 8.0)
        self.assertIn("V", france_data.streak_l5)

        italy_data = self.client.get_team_metrics("Italy")
        self.assertIsNotNone(italy_data)
        self.assertEqual(italy_data.team_name, "Italie")
        self.assertTrue(italy_data.is_national_team)

        spain_data = self.client.get_team_metrics("Espagne")
        self.assertIsNotNone(spain_data)
        self.assertEqual(spain_data.team_name, "Espagne")
        self.assertGreater(spain_data.xg_for_per_match, 2.0)

    def test_unknown_team_returns_none(self):
        unknown = self.client.get_team_metrics("NonExistentTeamXYZ")
        self.assertIsNone(unknown)


class TestUnderstatClient(unittest.TestCase):

    def setUp(self):
        self.client = UnderstatClient()

    def test_get_team_xg_returns_real_metrics(self):
        xg_data = self.client.get_team_xg("Arsenal")
        self.assertIsNotNone(xg_data)
        self.assertEqual(xg_data.team_name, "Arsenal")
        self.assertGreater(xg_data.xg_for_per_match, 1.5)
        self.assertLess(xg_data.xg_against_per_match, 1.2)
        self.assertGreater(xg_data.matches_played, 10)

    def test_psg_xg_metrics(self):
        xg_data = self.client.get_team_xg("Paris Saint Germain")
        self.assertIsNotNone(xg_data)
        self.assertEqual(xg_data.team_name, "Paris Saint-Germain")
        self.assertGreater(xg_data.xg_for_per_match, 2.0)
        self.assertLess(xg_data.xg_against_per_match, 1.0)


if __name__ == "__main__":
    unittest.main()

