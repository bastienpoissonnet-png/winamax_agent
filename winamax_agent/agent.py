"""Core decision agent orchestrating data ingestion, modeling, staking, and reporting."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional
from winamax_agent.config import AgentConfig
from winamax_agent.ingestion.mock_data import get_mock_fixtures
from winamax_agent.ingestion.odds_client import MatchFixture, TheOddsApiClient
from winamax_agent.ingestion.stats_provider import FootballStatsProvider
from winamax_agent.models.margin import analyze_market_margin
from winamax_agent.models.poisson_xg import XgPoissonEngine
from winamax_agent.models.value_bet import ValueOpportunity, evaluate_bet
from winamax_agent.reporting.reporter import BetRecommendation, DailyReport
from winamax_agent.staking.kelly import calculate_kelly_stake

logger = logging.getLogger(__name__)


class WinamaxBettingAgent:
    """Autonomous quantitative decision agent for football betting on Winamax."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.stats_provider = FootballStatsProvider()
        self.poisson_engine = XgPoissonEngine()
        self.odds_client: Optional[TheOddsApiClient] = None

        if self.config.odds_api_key and not self.config.simulation_mode:
            self.odds_client = TheOddsApiClient(
                api_key=self.config.odds_api_key,
                preferred_bookmaker=self.config.bookmaker,
            )

    def fetch_fixtures(self) -> List[MatchFixture]:
        """Fetches upcoming fixtures from The Odds API or mock simulation source."""
        if self.config.simulation_mode or not self.odds_client:
            logger.info("Running in SIMULATION / DEMO mode with realistic fixtures.")
            return get_mock_fixtures()

        fixtures: List[MatchFixture] = []
        for sport in self.config.competitions:
            try:
                sport_fixtures = self.odds_client.fetch_odds_for_sport(
                    sport_key=sport,
                    regions="eu",
                    markets=",".join(self.config.markets),
                )
                fixtures.extend(sport_fixtures)
                logger.info(f"Loaded {len(sport_fixtures)} fixtures for {sport}")
            except Exception as e:
                logger.warning(f"Could not load live odds for {sport}: {e}. Fallback to mock data if empty.")

        if not fixtures:
            logger.warning("No live fixtures returned from API. Using demonstration fixtures.")
            return get_mock_fixtures()

        return fixtures

    def analyze_fixture(self, fixture: MatchFixture) -> List[ValueOpportunity]:
        """Runs the complete quantitative analysis on a single match."""
        opportunities: List[ValueOpportunity] = []

        home_metrics = self.stats_provider.get_team_metrics(fixture.home_team)
        away_metrics = self.stats_provider.get_team_metrics(fixture.away_team)

        # Run xG Poisson Dixon-Coles simulation
        match_sim = self.poisson_engine.simulate_match(home_metrics, away_metrics)
        model_probs = match_sim.as_market_dict()

        # 1. 1X2 Market (h2h)
        if "h2h" in fixture.winamax_odds:
            h2h_odds = fixture.winamax_odds["h2h"].outcomes
            if all(k in h2h_odds for k in ["home", "draw", "away"]):
                margin_res = analyze_market_margin(h2h_odds)
                fair_probs = margin_res.fair_probs_multiplicative

                labels = {
                    "home": f"Victoire {fixture.home_team} (1)",
                    "draw": f"Match Nul (N)",
                    "away": f"Victoire {fixture.away_team} (2)",
                }

                for outcome_key in ["home", "draw", "away"]:
                    opp = evaluate_bet(
                        competition=fixture.competition_name,
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        market_type="1X2 (Résultat)",
                        selection=labels[outcome_key],
                        selection_key=outcome_key,
                        winamax_odds=h2h_odds[outcome_key],
                        fair_bookmaker_prob=fair_probs[outcome_key],
                        model_true_prob=model_probs[outcome_key],
                        min_ev_threshold=self.config.min_ev_threshold,
                    )
                    opportunities.append(opp)

        # 2. Over/Under 2.5 Market (totals)
        if "totals" in fixture.winamax_odds:
            totals_odds = fixture.winamax_odds["totals"].outcomes
            if all(k in totals_odds for k in ["over_2.5", "under_2.5"]):
                margin_res = analyze_market_margin(totals_odds)
                fair_probs = margin_res.fair_probs_multiplicative

                labels = {
                    "over_2.5": "Plus de 2.5 buts (Over 2.5)",
                    "under_2.5": "Moins de 2.5 buts (Under 2.5)",
                }

                for outcome_key in ["over_2.5", "under_2.5"]:
                    opp = evaluate_bet(
                        competition=fixture.competition_name,
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        market_type="Total Buts (Plus/Moins 2.5)",
                        selection=labels[outcome_key],
                        selection_key=outcome_key,
                        winamax_odds=totals_odds[outcome_key],
                        fair_bookmaker_prob=fair_probs[outcome_key],
                        model_true_prob=model_probs[outcome_key],
                        min_ev_threshold=self.config.min_ev_threshold,
                    )
                    opportunities.append(opp)

        return opportunities

    def run_daily_analysis(self) -> DailyReport:
        """Executes full decision-support pipeline and produces structured report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fixtures = self.fetch_fixtures()

        all_opps: List[ValueOpportunity] = []
        fixture_map = {f.id: f for f in fixtures}

        # Analyze all fixtures
        for fixture in fixtures:
            opps = self.analyze_fixture(fixture)
            all_opps.extend(opps)

        # Filter strictly for positive EV (EV > min_ev_threshold)
        value_opps = [o for o in all_opps if o.is_value and o.ev > self.config.min_ev_threshold]

        # Calculate Kelly stakes for value opportunities
        for opp in value_opps:
            kelly_res = calculate_kelly_stake(
                true_prob=opp.model_true_prob,
                odds=opp.odds,
                bankroll=self.config.total_bankroll,
                kelly_multiplier=self.config.kelly_fraction,
                min_stake=self.config.min_stake,
                max_stake=self.config.max_stake,
            )
            opp.recommended_stake = kelly_res.final_stake_eur

        # Sort descending by EV (highest expected value first)
        value_opps.sort(key=lambda x: x.ev, reverse=True)

        recommendations: List[BetRecommendation] = []
        for opp in value_opps:
            # Find matching fixture
            matching_fix = next(
                (f for f in fixtures if f.home_team == opp.home_team and f.away_team == opp.away_team),
                None,
            )
            kickoff = matching_fix.commence_time if matching_fix else "N/A"

            home_metrics = self.stats_provider.get_team_metrics(opp.home_team)
            away_metrics = self.stats_provider.get_team_metrics(opp.away_team)

            # Generate 3-point analytical justification
            context = self.stats_provider.generate_context_justification(
                home_team=opp.home_team,
                away_team=opp.away_team,
                home_metrics=home_metrics,
                away_metrics=away_metrics,
                market_key=opp.market_type,
                selection_key=opp.selection_key,
            )

            # Recalculate Kelly details for display
            kelly_res = calculate_kelly_stake(
                true_prob=opp.model_true_prob,
                odds=opp.odds,
                bankroll=self.config.total_bankroll,
                kelly_multiplier=self.config.kelly_fraction,
                min_stake=self.config.min_stake,
                max_stake=self.config.max_stake,
            )

            rec = BetRecommendation(
                competition=opp.competition,
                match_title=opp.match_title,
                kickoff=kickoff,
                market_name=opp.market_type,
                selection_label=opp.selection,
                bookmaker="Winamax",
                winamax_odds=opp.odds,
                raw_implied_prob_pct=opp.raw_implied_prob * 100.0,
                fair_bookmaker_prob_pct=opp.fair_bookmaker_prob * 100.0,
                model_true_prob_pct=opp.model_true_prob * 100.0,
                edge_pct=opp.edge_pct,
                ev_pct=opp.ev_pct,
                stake_eur=opp.recommended_stake,
                stake_details=kelly_res.reason,
                point_1_xg=context.xg_justification,
                point_2_h2h_tactics=context.h2h_tactical_justification,
                point_3_context_form=context.team_context_justification,
            )
            recommendations.append(rec)

        top_rec = recommendations[0] if recommendations else None
        secondary_recs = recommendations[1:5] if len(recommendations) > 1 else []

        return DailyReport(
            timestamp=timestamp,
            total_matches_analyzed=len(fixtures),
            total_markets_analyzed=len(all_opps),
            positive_ev_count=len(value_opps),
            top_recommendation=top_rec,
            secondary_recommendations=secondary_recs,
        )
