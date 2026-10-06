"""Realistic fixture and odds simulation data for testing and offline runs."""

from __future__ import annotations
from typing import List
from winamax_agent.ingestion.odds_client import MatchFixture, MarketOdds


def get_mock_fixtures() -> List[MatchFixture]:
    """Generates realistic football fixtures and Winamax odds for Nations League, L1, PL, and UCL."""
    return [
        # UEFA Nations League: France vs Italie (Choc international au Parc des Princes / Stade de France)
        MatchFixture(
            id="mock_unl_fra_ita",
            sport_key="soccer_uefa_nations_league",
            competition_name="UEFA Nations League",
            commence_time="2026-10-06T20:45:00Z",
            home_team="France",
            away_team="Italie",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.68, "draw": 3.75, "away": 5.20},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.20, "x2": 2.20, "12": 1.26},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.28,
                        "under_1.5": 3.60,
                        "over_2.5": 1.90,
                        "under_2.5": 1.92,
                        "under_3.5": 1.36,
                        "over_3.5": 3.10,
                    },
                ),
            },
        ),
        # UEFA Nations League: Espagne vs Danemark (Maîtrise technique ibérique)
        MatchFixture(
            id="mock_unl_esp_den",
            sport_key="soccer_uefa_nations_league",
            competition_name="UEFA Nations League",
            commence_time="2026-10-07T20:45:00Z",
            home_team="Espagne",
            away_team="Danemark",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.52, "draw": 4.20, "away": 6.40},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.13, "x2": 2.50, "12": 1.22},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.24,
                        "under_1.5": 3.90,
                        "over_2.5": 1.78,
                        "under_2.5": 2.05,
                        "under_3.5": 1.40,
                        "over_3.5": 2.90,
                    },
                ),
            },
        ),
        # UEFA Nations League: Belgique vs Israël
        MatchFixture(
            id="mock_unl_bel_isr",
            sport_key="soccer_uefa_nations_league",
            competition_name="UEFA Nations League",
            commence_time="2026-10-06T20:45:00Z",
            home_team="Belgique",
            away_team="Israël",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.30, "draw": 5.60, "away": 9.50},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.07, "x2": 3.45, "12": 1.14},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.18,
                        "under_1.5": 4.70,
                        "over_2.5": 1.55,
                        "under_2.5": 2.45,
                        "under_3.5": 1.50,
                        "over_3.5": 2.55,
                    },
                ),
            },
        ),
        # Premier League: Arsenal vs Chelsea (Arsenal ultra-solide à l'Emirates)
        MatchFixture(
            id="mock_pl_ars_che",
            sport_key="soccer_epl",
            competition_name="Premier League",
            commence_time="2026-10-07T17:30:00Z",
            home_team="Arsenal",
            away_team="Chelsea",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.82, "draw": 3.80, "away": 4.20},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.35, "x2": 1.95, "12": 1.25},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.28,
                        "under_1.5": 3.60,
                        "over_2.5": 1.78,
                        "under_2.5": 2.05,
                        "under_3.5": 1.44,
                        "over_3.5": 2.70,
                    },
                ),
            },
        ),
        # Ligue 1: Marseille vs Lyon (Marseille favori au Vélodrome)
        MatchFixture(
            id="mock_l1_om_ol",
            sport_key="soccer_france_ligue_one",
            competition_name="Ligue 1 McDonald's",
            commence_time="2026-10-06T20:45:00Z",
            home_team="Marseille",
            away_team="Lyon",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 2.05, "draw": 3.65, "away": 3.50},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.38, "x2": 1.75, "12": 1.28},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.30,
                        "under_1.5": 3.40,
                        "over_2.5": 1.70,
                        "under_2.5": 2.15,
                        "under_3.5": 1.45,
                        "over_3.5": 2.65,
                    },
                ),
            },
        ),
        # Ligue 1: Paris SG vs Nice (Nice = bloc hermétique, profil Under)
        MatchFixture(
            id="mock_l1_psg_nice",
            sport_key="soccer_france_ligue_one",
            competition_name="Ligue 1 McDonald's",
            commence_time="2026-10-06T20:45:00Z",
            home_team="Paris Saint Germain",
            away_team="Nice",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.48, "draw": 4.60, "away": 6.80},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.15, "x2": 2.60, "12": 1.18},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.22,
                        "under_1.5": 4.10,
                        "over_2.5": 1.62,
                        "under_2.5": 2.25,
                        "under_3.5": 1.55,
                        "over_3.5": 2.40,
                    },
                ),
            },
        ),
        # Champions League: Real Madrid vs Bayern Munich (Grand choc européen)
        MatchFixture(
            id="mock_ucl_rma_bay",
            sport_key="soccer_uefa_champs_league",
            competition_name="UEFA Champions League",
            commence_time="2026-10-08T21:00:00Z",
            home_team="Real Madrid",
            away_team="Bayern Munich",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 2.20, "draw": 3.75, "away": 3.00},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.40, "x2": 1.68, "12": 1.28},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.24,
                        "under_1.5": 3.90,
                        "over_2.5": 1.58,
                        "under_2.5": 2.35,
                        "under_3.5": 1.50,
                        "over_3.5": 2.50,
                    },
                ),
            },
        ),
        # Match test d'anomalie : Paris SG vs Le Mans FC (Outsider extrême à 21.00 - doit être REJETÉ)
        MatchFixture(
            id="mock_cup_psg_lemans",
            sport_key="soccer_france_ligue_one",
            competition_name="Coupe de France",
            commence_time="2026-10-09T21:00:00Z",
            home_team="Paris Saint Germain",
            away_team="Le Mans FC",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.08, "draw": 10.50, "away": 21.00},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.12,
                        "under_1.5": 5.80,
                        "over_2.5": 1.38,
                        "under_2.5": 2.90,
                    },
                ),
            },
        ),
        # Ligue 2 : Paris FC vs Rodez (Vérification de distinction stricte Paris FC vs PSG)
        MatchFixture(
            id="mock_l2_pfc_rod",
            sport_key="soccer_france_ligue_two",
            competition_name="Ligue 2 BKT",
            commence_time="2026-10-10T19:00:00Z",
            home_team="Paris FC",
            away_team="Rodez",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.95, "draw": 3.40, "away": 3.90},
                ),
                "double_chance": MarketOdds(
                    bookmaker="winamax",
                    market_key="double_chance",
                    outcomes={"1x": 1.25, "x2": 1.80, "12": 1.30},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={
                        "over_1.5": 1.32,
                        "under_1.5": 3.25,
                        "over_2.5": 1.95,
                        "under_2.5": 1.85,
                    },
                ),
            },
        ),
    ]
