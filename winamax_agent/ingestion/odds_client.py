"""Client for fetching sports odds from The Odds API with Winamax focus."""

from __future__ import annotations
import json
import logging
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketOdds:
    """Standardized representation of odds for a match market."""
    bookmaker: str
    market_key: str          # "h2h" or "totals"
    outcomes: Dict[str, float]  # e.g. {"home": 2.10, "draw": 3.40, "away": 3.60} or {"over_2.5": 1.85, "under_2.5": 1.95}


@dataclass
class MatchFixture:
    """Fixture with bookmaker odds."""
    id: str
    sport_key: str
    competition_name: str
    commence_time: str
    home_team: str
    away_team: str
    winamax_odds: Dict[str, MarketOdds]


class TheOddsApiClient:
    """HTTP client for The Odds API supporting European markets and Winamax."""

    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def __init__(
        self,
        api_key: str,
        preferred_bookmaker: str = "winamax",
        cache_ttl_seconds: int = 1800,
    ):
        self.api_key = api_key
        self.preferred_bookmaker = preferred_bookmaker.lower()
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def fetch_odds_for_sport(
        self,
        sport_key: str,
        regions: str = "eu",
        markets: str = "h2h,totals",
    ) -> List[MatchFixture]:
        """Fetches upcoming fixtures and odds for a specific sport/league."""
        if not self.api_key:
            raise ValueError("The Odds API key is not configured.")

        cache_key = f"{sport_key}_{regions}_{markets}"
        now = time.time()
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            if now - timestamp < self.cache_ttl:
                logger.info(f"Using cached odds for {sport_key}")
                return self._parse_fixtures(data, sport_key)

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/{sport_key}/odds/?{query_string}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "WinamaxBettingAgent/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                remaining_requests = response.headers.get("x-requests-remaining")
                if remaining_requests:
                    logger.info(f"The Odds API quota remaining: {remaining_requests}")
                payload = json.loads(response.read().decode("utf-8"))
                self._cache[cache_key] = (now, payload)
                return self._parse_fixtures(payload, sport_key)
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code} querying The Odds API: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch odds from The Odds API: {e}")
            raise

    def _parse_fixtures(self, raw_events: List[Dict[str, Any]], sport_key: str) -> List[MatchFixture]:
        """Transforms raw API response into standardized MatchFixture objects."""
        fixtures: List[MatchFixture] = []

        comp_name_map = {
            "soccer_uefa_nations_league": "UEFA Nations League",
            "soccer_france_ligue_one": "Ligue 1 McDonald's",
            "soccer_epl": "Premier League",
            "soccer_spain_la_liga": "La Liga",
            "soccer_italy_serie_a": "Serie A",
            "soccer_germany_bundesliga": "Bundesliga",
            "soccer_uefa_champs_league": "UEFA Champions League",
            "soccer_uefa_europa_league": "UEFA Europa League",
        }
        comp_title = comp_name_map.get(sport_key, sport_key)

        for event in raw_events:
            event_id = event.get("id", "")
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            commence_time = event.get("commence_time", "")
            bookmakers_list = event.get("bookmakers", [])

            # Look for preferred bookmaker first (Winamax), or fall back to any FR/EU bookmaker
            chosen_bm = None
            for bm in bookmakers_list:
                if bm.get("key", "").lower() == self.preferred_bookmaker:
                    chosen_bm = bm
                    break

            # Fallback to betclic, unibet_fr, or first available if Winamax not present
            if not chosen_bm and bookmakers_list:
                for candidate in ["betclic", "unibet_fr", "bwin", "pinnacle"]:
                    for bm in bookmakers_list:
                        if bm.get("key", "").lower() == candidate:
                            chosen_bm = bm
                            break
                    if chosen_bm:
                        break
                if not chosen_bm:
                    chosen_bm = bookmakers_list[0]

            if not chosen_bm:
                continue

            parsed_markets: Dict[str, MarketOdds] = {}
            for market in chosen_bm.get("markets", []):
                m_key = market.get("key")
                outcomes: Dict[str, float] = {}

                if m_key == "h2h":
                    for out in market.get("outcomes", []):
                        name = out.get("name")
                        price = float(out.get("price", 0.0))
                        if name == home_team:
                            outcomes["home"] = price
                        elif name == away_team:
                            outcomes["away"] = price
                        elif name.lower() in ("draw", "nul", "match nul"):
                            outcomes["draw"] = price

                elif m_key == "totals":
                    for out in market.get("outcomes", []):
                        name = out.get("name", "").lower()
                        point = out.get("point", 2.5)
                        price = float(out.get("price", 0.0))
                        if point == 2.5:
                            if name == "over":
                                outcomes["over_2.5"] = price
                            elif name == "under":
                                outcomes["under_2.5"] = price

                if outcomes:
                    parsed_markets[m_key] = MarketOdds(
                        bookmaker=chosen_bm.get("key"),
                        market_key=m_key,
                        outcomes=outcomes,
                    )

            if parsed_markets:
                fixtures.append(
                    MatchFixture(
                        id=event_id,
                        sport_key=sport_key,
                        competition_name=comp_title,
                        commence_time=commence_time,
                        home_team=home_team,
                        away_team=away_team,
                        winamax_odds=parsed_markets,
                    )
                )

        return fixtures

