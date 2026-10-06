"""Realistic fixture and odds simulation data for testing and offline runs."""

from __future__ import annotations
from typing import List
from winamax_agent.ingestion.odds_client import MatchFixture, MarketOdds


def get_mock_fixtures() -> List[MatchFixture]:
    """Generates realistic football fixtures and Winamax odds for L1, PL, and UCL."""
    return [
        # Ligue 1: Paris SG vs Nice (Winamax odds)
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
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={"over_2.5": 1.62, "under_2.5": 2.25},
                ),
            },
        ),
        # Ligue 1: Marseille vs Lyon
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
                    # Marseille quoted slightly generous at 2.10
                    outcomes={"home": 2.10, "draw": 3.65, "away": 3.45},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={"over_2.5": 1.70, "under_2.5": 2.15},
                ),
            },
        ),
        # Premier League: Arsenal vs Chelsea
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
                    outcomes={"home": 1.88, "draw": 3.80, "away": 4.10},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={"over_2.5": 1.82, "under_2.5": 2.00},
                ),
            },
        ),
        # Premier League: Manchester City vs Tottenham
        MatchFixture(
            id="mock_pl_mci_tot",
            sport_key="soccer_epl",
            competition_name="Premier League",
            commence_time="2026-10-07T20:00:00Z",
            home_team="Manchester City",
            away_team="Tottenham Hotspur",
            winamax_odds={
                "h2h": MarketOdds(
                    bookmaker="winamax",
                    market_key="h2h",
                    outcomes={"home": 1.36, "draw": 5.40, "away": 7.50},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    # High probability over 2.5 on high-line clash
                    outcomes={"over_2.5": 1.45, "under_2.5": 2.70},
                ),
            },
        ),
        # Champions League: Real Madrid vs Bayern Munich
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
                    outcomes={"home": 2.25, "draw": 3.75, "away": 2.95},
                ),
                "totals": MarketOdds(
                    bookmaker="winamax",
                    market_key="totals",
                    outcomes={"over_2.5": 1.58, "under_2.5": 2.35},
                ),
            },
        ),
    ]
