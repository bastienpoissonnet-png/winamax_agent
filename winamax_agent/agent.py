"""Core decision agent orchestrating data ingestion, modeling, staking, and reporting."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional
from winamax_agent.config import AgentConfig
from winamax_agent.ingestion.football_data_client import FootballDataClient
from winamax_agent.ingestion.fotmob_client import FotmobClient
from winamax_agent.ingestion.mock_data import get_mock_fixtures
from winamax_agent.ingestion.odds_client import MatchFixture, TheOddsApiClient
from winamax_agent.ingestion.stats_provider import FootballStatsProvider
from winamax_agent.ingestion.understat_client import UnderstatClient
from winamax_agent.models.margin import analyze_market_margin
from winamax_agent.models.parlays import ParlayLeg, find_best_parlays, find_fallback_parlay
from winamax_agent.models.poisson_xg import XgPoissonEngine
from winamax_agent.models.value_bet import ValueOpportunity, evaluate_bet
from winamax_agent.reporting.reporter import BetRecommendation, DailyReport
from winamax_agent.staking.kelly import calculate_kelly_stake, calculate_micro_kelly_stake, calculate_fallback_stake

logger = logging.getLogger(__name__)


class WinamaxBettingAgent:
    """Autonomous quantitative decision agent for football betting on Winamax."""

    def __init__(self, config: AgentConfig):
        self.config = config
        cache_dir = self.config.output_dir / "cache"
        fotmob_cl = FotmobClient(cache_dir=cache_dir)
        fb_client = FootballDataClient(
            api_key=self.config.football_data_api_key,
            cache_dir=cache_dir,
        )
        us_client = UnderstatClient(cache_dir=cache_dir)
        self.stats_provider = FootballStatsProvider(
            fotmob_client=fotmob_cl,
            football_data_client=fb_client,
            understat_client=us_client,
        )
        self.poisson_engine = XgPoissonEngine()
        self.odds_client: Optional[TheOddsApiClient] = None

        if self.config.odds_api_key and not self.config.simulation_mode:
            self.odds_client = TheOddsApiClient(
                api_key=self.config.odds_api_key,
                preferred_bookmaker=self.config.bookmaker,
            )

        # Lecture prioritaire de la bankroll active depuis reports/bankroll.json
        from pathlib import Path
        bankroll_path = Path("reports/bankroll.json")
        if hasattr(self.config, "bankroll_file") and self.config.bankroll_file:
            bankroll_path = Path(self.config.bankroll_file)
        elif hasattr(self.config, "output_dir") and (self.config.output_dir / "bankroll.json").exists():
            bankroll_path = self.config.output_dir / "bankroll.json"

        try:
            from winamax_agent.bankroll import load_or_init_bankroll
            b_data = load_or_init_bankroll(filepath=bankroll_path, default_initial=self.config.total_bankroll)
            self.config.total_bankroll = float(b_data.get("current_bankroll", self.config.total_bankroll))
            self.bankroll_data = b_data
        except Exception as e:
            logger.warning(f"Impossible de charger bankroll.json: {e}")
            self.bankroll_data = {
                "initial_bankroll": self.config.total_bankroll,
                "current_bankroll": self.config.total_bankroll,
                "total_profit": 0.0,
                "history": [],
            }

    def notify_discord(self, report: DailyReport) -> bool:
        """Sends daily report to Discord webhook if configured."""
        from winamax_agent.reporting.discord_notifier import send_discord_report
        return send_discord_report(report, webhook_url=self.config.discord_webhook_url)

    def _is_solid_winner_pick(self, rec: BetRecommendation) -> bool:
        """Impose une probabilité de réalisation solide pour les sélections majeures (Section 1 et 2):
        - Victoire sèche (1X2, sweet spot 1.50 - 3.00) : P_modèle >= 48%
        - Double chance (1X, X2) : P_modèle >= 60%
        - Autres marchés (Totaux) : P_modèle >= 55%
        """
        label = rec.selection_label
        p_pct = rec.model_true_prob_pct

        is_straight = any(k in label for k in ["(1)", "(2)"]) or ("Victoire" in label and "Nul" not in label)
        is_dc = any(k in label for k in ["(1X)", "(X2)", "(12)", "ou Nul"])

        if is_straight:
            if p_pct < 48.0:
                return False
        elif is_dc:
            if p_pct < 60.0:
                return False
        else:
            if p_pct < 55.0:
                return False

        return True

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
        """Runs the complete quantitative analysis on a single match with market anchor."""
        opportunities: List[ValueOpportunity] = []

        home_metrics = self.stats_provider.get_team_metrics(fixture.home_team, is_home=True)
        away_metrics = self.stats_provider.get_team_metrics(fixture.away_team, is_home=False)

        # 1. Simulation Poisson / Dixon-Coles xG
        match_sim = self.poisson_engine.simulate_match(home_metrics, away_metrics)
        raw_model_probs = match_sim.as_market_dict()

        # 2. Analyse du marché 1X2 (h2h)
        if "h2h" in fixture.winamax_odds:
            h2h_odds = fixture.winamax_odds["h2h"].outcomes
            if all(k in h2h_odds for k in ["home", "draw", "away"]):
                margin_res = analyze_market_margin(h2h_odds)
                fair_probs = margin_res.fair_probs_multiplicative

                # Calibrer les probabilités sur le consensus de marché (Bayesian shrinkage)
                calibrated_probs = self.stats_provider.calibrate_probabilities_with_market_anchor(
                    raw_model_probs=raw_model_probs,
                    fair_bookmaker_probs=fair_probs,
                    home_metrics=home_metrics,
                    away_metrics=away_metrics,
                    max_realistic_edge=self.config.max_realistic_edge,
                )

                # Marché 1X2 standard
                labels_1x2 = {
                    "home": f"Victoire {fixture.home_team} (1)",
                    "draw": f"Match Nul (N)",
                    "away": f"Victoire {fixture.away_team} (2)",
                }

                for outcome_key in ["home", "draw", "away"]:
                    o_val = h2h_odds[outcome_key]
                    if o_val < self.config.absolute_min_odds or o_val > 10.00:
                        continue

                    # Données sportives pour filtre de cohérence anti-surprise
                    t_streak = ""
                    w_l5 = None
                    l_l5 = None
                    pts_l5 = None
                    if outcome_key == "home":
                        t_streak = home_metrics.streak_l5
                        w_l5 = home_metrics.wins_l5
                        l_l5 = home_metrics.losses_l5
                        pts_l5 = home_metrics.recent_form_points
                    elif outcome_key == "away":
                        t_streak = away_metrics.streak_l5
                        w_l5 = away_metrics.wins_l5
                        l_l5 = away_metrics.losses_l5
                        pts_l5 = away_metrics.recent_form_points

                    pitch_dyn = self.stats_provider.generate_pitch_dynamic(
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        home_metrics=home_metrics,
                        away_metrics=away_metrics,
                        market_key="1X2 (Résultat)",
                        selection_key=outcome_key,
                    )

                    opp = evaluate_bet(
                        competition=fixture.competition_name,
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        market_type="1X2 (Résultat)",
                        selection=labels_1x2[outcome_key],
                        selection_key=outcome_key,
                        winamax_odds=o_val,
                        fair_bookmaker_prob=fair_probs[outcome_key],
                        model_true_prob=calibrated_probs[outcome_key],
                        min_ev_threshold=self.config.min_ev_threshold,
                        min_odds=self.config.min_odds,
                        max_odds=self.config.max_odds,
                        min_prob_threshold=self.config.min_prob_threshold,
                        min_prob_low_odds=self.config.min_prob_low_odds,
                        team_streak=t_streak,
                        wins_l5=w_l5,
                        losses_l5=l_l5,
                        recent_form_points=pts_l5,
                        pitch_dynamic=pitch_dyn,
                    )
                    opportunities.append(opp)

                # Marché Double Chance (1X, X2) - Haute sécurité & forte probabilité
                dc_market = fixture.winamax_odds.get("double_chance")
                o_home = h2h_odds["home"]
                o_draw = h2h_odds["draw"]
                o_away = h2h_odds["away"]

                if dc_market and "1x" in dc_market.outcomes:
                    odds_1x = dc_market.outcomes["1x"]
                else:
                    odds_1x = round(1.0 / ((1.0 / o_home) + (1.0 / o_draw)), 2)

                if dc_market and "x2" in dc_market.outcomes:
                    odds_x2 = dc_market.outcomes["x2"]
                else:
                    odds_x2 = round(1.0 / ((1.0 / o_draw) + (1.0 / o_away)), 2)

                fair_prob_1x = fair_probs["home"] + fair_probs["draw"]
                fair_prob_x2 = fair_probs["draw"] + fair_probs["away"]

                true_prob_1x = calibrated_probs.get("1x", fair_prob_1x)
                true_prob_x2 = calibrated_probs.get("x2", fair_prob_x2)

                if self.config.absolute_min_odds <= odds_1x <= 10.00:
                    pitch_dyn_1x = self.stats_provider.generate_pitch_dynamic(
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        home_metrics=home_metrics,
                        away_metrics=away_metrics,
                        market_key="Double Chance (Sécurisation)",
                        selection_key="1x",
                    )
                    opp_1x = evaluate_bet(
                        competition=fixture.competition_name,
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        market_type="Double Chance (Sécurisation)",
                        selection=f"{fixture.home_team} ou Nul (1X)",
                        selection_key="1x",
                        winamax_odds=odds_1x,
                        fair_bookmaker_prob=fair_prob_1x,
                        model_true_prob=true_prob_1x,
                        min_ev_threshold=self.config.min_ev_threshold,
                        min_odds=self.config.min_odds,
                        max_odds=self.config.max_odds,
                        min_prob_threshold=self.config.min_prob_threshold,
                        min_prob_low_odds=self.config.min_prob_low_odds,
                        pitch_dynamic=pitch_dyn_1x,
                    )
                    opportunities.append(opp_1x)

                if self.config.absolute_min_odds <= odds_x2 <= 10.00:
                    pitch_dyn_x2 = self.stats_provider.generate_pitch_dynamic(
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        home_metrics=home_metrics,
                        away_metrics=away_metrics,
                        market_key="Double Chance (Sécurisation)",
                        selection_key="x2",
                    )
                    opp_x2 = evaluate_bet(
                        competition=fixture.competition_name,
                        home_team=fixture.home_team,
                        away_team=fixture.away_team,
                        market_type="Double Chance (Sécurisation)",
                        selection=f"Nul ou {fixture.away_team} (X2)",
                        selection_key="x2",
                        winamax_odds=odds_x2,
                        fair_bookmaker_prob=fair_prob_x2,
                        model_true_prob=true_prob_x2,
                        min_ev_threshold=self.config.min_ev_threshold,
                        min_odds=self.config.min_odds,
                        max_odds=self.config.max_odds,
                        min_prob_threshold=self.config.min_prob_threshold,
                        min_prob_low_odds=self.config.min_prob_low_odds,
                        pitch_dynamic=pitch_dyn_x2,
                    )
                    opportunities.append(opp_x2)

        # 3. Marchés Totaux de Buts analysés par lignes binaires complémentaires (1.5, 2.5, 3.5)
        if "totals" in fixture.winamax_odds:
            totals_odds = fixture.winamax_odds["totals"].outcomes

            # Définition des lignes binaires complémentaires
            total_lines = [
                ("1.5", "over_1.5", "under_1.5", "Total Buts (Sécurisé)", "Plus de 1.5 buts", "Moins de 1.5 buts"),
                ("2.5", "over_2.5", "under_2.5", "Total Buts (Standard)", "Plus de 2.5 buts", "Moins de 2.5 buts"),
                ("3.5", "over_3.5", "under_3.5", "Total Buts (Sécurisé)", "Plus de 3.5 buts", "Moins de 3.5 buts"),
            ]

            for line_label, over_k, under_k, market_name, over_txt, under_txt in total_lines:
                # Si la ligne existe directement chez le bookmaker
                if over_k in totals_odds and under_k in totals_odds:
                    pair_odds = {over_k: totals_odds[over_k], under_k: totals_odds[under_k]}
                    margin_res = analyze_market_margin(pair_odds)
                    fair_pair = margin_res.fair_probs_multiplicative

                    for sel_k, sel_txt in [(over_k, over_txt), (under_k, under_txt)]:
                        o_val = pair_odds[sel_k]
                        if o_val < self.config.absolute_min_odds or o_val > 10.00:
                            continue
                        p_fair = fair_pair[sel_k]
                        p_raw_model = raw_model_probs.get(sel_k, p_fair)

                        # Ancrage et shrinkage
                        w_model = 0.35 if (home_metrics.is_calibrated and away_metrics.is_calibrated) else 0.0
                        p_true = (1.0 - w_model) * p_fair + (w_model * p_raw_model)

                        # Edge réaliste borné
                        edge = min(self.config.max_realistic_edge, max(-self.config.max_realistic_edge, p_true - p_fair))
                        p_calibrated = p_fair + edge

                        pitch_dyn_tot = self.stats_provider.generate_pitch_dynamic(
                            home_team=fixture.home_team,
                            away_team=fixture.away_team,
                            home_metrics=home_metrics,
                            away_metrics=away_metrics,
                            market_key=market_name,
                            selection_key=sel_k,
                        )

                        opp = evaluate_bet(
                            competition=fixture.competition_name,
                            home_team=fixture.home_team,
                            away_team=fixture.away_team,
                            market_type=market_name,
                            selection=f"{sel_txt} ({sel_k.replace('_', ' ').title()})",
                            selection_key=sel_k,
                            winamax_odds=o_val,
                            fair_bookmaker_prob=p_fair,
                            model_true_prob=p_calibrated,
                            min_ev_threshold=self.config.min_ev_threshold,
                            min_odds=self.config.min_odds,
                            max_odds=self.config.max_odds,
                            min_prob_threshold=self.config.min_prob_threshold,
                            min_prob_low_odds=self.config.min_prob_low_odds,
                            pitch_dynamic=pitch_dyn_tot,
                        )
                        opportunities.append(opp)

        return opportunities

    def run_daily_analysis(self) -> DailyReport:
        """Executes full decision-support pipeline and produces structured report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fixtures = self.fetch_fixtures()

        all_opps: List[ValueOpportunity] = []

        # Analyze all fixtures
        for fixture in fixtures:
            opps = self.analyze_fixture(fixture)
            all_opps.extend(opps)

        # Filter strictly for valid Value Bets that passed all risk filters
        value_opps = [o for o in all_opps if o.is_value and o.ev > self.config.min_ev_threshold]

        # Calculate Kelly stakes for value opportunities with risk-adjusted tiers
        for opp in value_opps:
            kelly_res = calculate_kelly_stake(
                true_prob=opp.model_true_prob,
                odds=opp.odds,
                bankroll=self.config.total_bankroll,
                kelly_multiplier=self.config.kelly_fraction,
                min_odds=self.config.min_odds,
                max_odds=self.config.max_odds,
                min_prob_threshold=self.config.min_prob_threshold,
                min_prob_low_odds=self.config.min_prob_low_odds,
            )
            opp.recommended_stake = kelly_res.final_stake_eur

        # Retenir uniquement les opportunités où la mise est > 0 € (non rejetées par le sizing de risque)
        confirmed_value_opps = [o for o in value_opps if o.recommended_stake > 0.0]

        # Fonction de classement priorisant la forte probabilité et les équipes en dynamique positive
        def score_ranking(opp: ValueOpportunity) -> float:
            prob_factor = opp.model_true_prob ** 1.3
            is_home_pick = opp.selection_key in ("home", "1x")
            is_away_pick = opp.selection_key in ("away", "x2")

            backed_metrics = None
            if is_home_pick:
                backed_metrics = self.stats_provider.get_team_metrics(opp.home_team, is_home=True)
            elif is_away_pick:
                backed_metrics = self.stats_provider.get_team_metrics(opp.away_team, is_home=False)

            dynamic_bonus = 1.0
            if backed_metrics:
                dynamic_bonus += (backed_metrics.recent_form_points / 15.0) * 0.25 + (backed_metrics.wins_l5 / 5.0) * 0.15

            solid_bonus = 1.30 if opp.is_solid_market else 1.0
            return prob_factor * (1.0 + opp.ev) * dynamic_bonus * solid_bonus

        confirmed_value_opps.sort(key=score_ranking, reverse=True)

        recommendations: List[BetRecommendation] = []
        for opp in confirmed_value_opps:
            matching_fix = next(
                (f for f in fixtures if f.home_team == opp.home_team and f.away_team == opp.away_team),
                None,
            )
            kickoff = matching_fix.commence_time if matching_fix else "N/A"

            home_metrics = self.stats_provider.get_team_metrics(opp.home_team, is_home=True)
            away_metrics = self.stats_provider.get_team_metrics(opp.away_team, is_home=False)

            # Generate 3-point analytical justification
            context = self.stats_provider.generate_context_justification(
                home_team=opp.home_team,
                away_team=opp.away_team,
                home_metrics=home_metrics,
                away_metrics=away_metrics,
                market_key=opp.market_type,
                selection_key=opp.selection_key,
            )

            # Re-fetch Kelly sizing explanation
            kelly_res = calculate_kelly_stake(
                true_prob=opp.model_true_prob,
                odds=opp.odds,
                bankroll=self.config.total_bankroll,
                kelly_multiplier=self.config.kelly_fraction,
                min_odds=self.config.min_odds,
                max_odds=self.config.max_odds,
                min_prob_threshold=self.config.min_prob_threshold,
                min_prob_low_odds=self.config.min_prob_low_odds,
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
                pitch_dynamic=context.pitch_dynamic,
            )
            recommendations.append(rec)

        # -------------------------------------------------------------
        # Section 1 : Le Match du Jour (Coup d'envoi aujourd'hui)
        # -------------------------------------------------------------
        today_date = datetime.now().date()
        today_str = today_date.strftime("%Y-%m-%d")

        def is_match_today(commence_time_str: str) -> bool:
            if not commence_time_str or commence_time_str == "N/A":
                return False
            if commence_time_str.startswith(today_str):
                return True
            try:
                dt = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
                return dt.astimezone().date() == today_date
            except Exception:
                return False

        today_recs = [
            r for r in recommendations
            if is_match_today(r.kickoff) and r.winamax_odds >= self.config.absolute_min_odds
        ]
        solid_today_recs = [r for r in today_recs if self._is_solid_winner_pick(r)]
        match_of_the_day = solid_today_recs[0] if solid_today_recs else (today_recs[0] if today_recs else None)

        # Mode de secours Section 1 : si aucune EV > 0 aujourd'hui
        if not match_of_the_day:
            today_fixtures = [f for f in fixtures if is_match_today(f.commence_time)]
            if today_fixtures:
                today_opps: List[ValueOpportunity] = []
                for opp in all_opps:
                    if opp.odds < self.config.absolute_min_odds or opp.odds > 10.00:
                        continue
                    matching_fix = next(
                        (f for f in today_fixtures if f.home_team == opp.home_team and f.away_team == opp.away_team),
                        None,
                    )
                    if matching_fix:
                        today_opps.append(opp)

                if today_opps:
                    def today_fallback_score(o: ValueOpportunity) -> float:
                        prob_p = o.model_true_prob
                        if o.selection_key in ("home", "away") and prob_p < 0.48:
                            prob_p *= 0.5
                        elif o.selection_key in ("1x", "x2") and prob_p < 0.60:
                            prob_p *= 0.7
                        solid_bonus = 1.30 if o.is_solid_market else 1.0
                        return (prob_p * 2.0 + (1.0 + o.ev)) * solid_bonus

                    today_opps.sort(key=today_fallback_score, reverse=True)
                    best_today_fb = today_opps[0]

                    matching_fix = next(
                        (f for f in today_fixtures if f.home_team == best_today_fb.home_team and f.away_team == best_today_fb.away_team),
                        None,
                    )
                    kickoff = matching_fix.commence_time if matching_fix else "N/A"
                    home_metrics = self.stats_provider.get_team_metrics(best_today_fb.home_team, is_home=True)
                    away_metrics = self.stats_provider.get_team_metrics(best_today_fb.away_team, is_home=False)
                    context = self.stats_provider.generate_context_justification(
                        home_team=best_today_fb.home_team,
                        away_team=best_today_fb.away_team,
                        home_metrics=home_metrics,
                        away_metrics=away_metrics,
                        market_key=best_today_fb.market_type,
                        selection_key=best_today_fb.selection_key,
                    )

                    fb_stake_res = calculate_fallback_stake(
                        fallback_amount=self.config.fallback_stake,
                        reason_prefix=f"Choix de secours Match du Jour ({best_today_fb.selection})",
                    )

                    warning = (
                        "⚠️ OPTION DE SECOURS — SOUS-OPTIMALE : Aucune opportunité ne valide d'espérance positive "
                        f"(EV: {best_today_fb.ev_pct:+.2f}%) parmi les matchs du jour. "
                        f"Cette sélection retient le résultat le plus robuste et le plus probable ({best_today_fb.selection} avec {best_today_fb.model_true_prob * 100:.1f}%). "
                        f"Mise symbolique minimale ({fb_stake_res.final_stake_eur:.2f} €) pour préserver votre capital."
                    )

                    match_of_the_day = BetRecommendation(
                        competition=best_today_fb.competition,
                        match_title=best_today_fb.match_title,
                        kickoff=kickoff,
                        market_name=best_today_fb.market_type,
                        selection_label=best_today_fb.selection,
                        bookmaker="Winamax",
                        winamax_odds=best_today_fb.odds,
                        raw_implied_prob_pct=best_today_fb.raw_implied_prob * 100.0,
                        fair_bookmaker_prob_pct=best_today_fb.fair_bookmaker_prob * 100.0,
                        model_true_prob_pct=best_today_fb.model_true_prob * 100.0,
                        edge_pct=best_today_fb.edge_pct,
                        ev_pct=best_today_fb.ev_pct,
                        stake_eur=fb_stake_res.final_stake_eur,
                        stake_details=fb_stake_res.reason,
                        point_1_xg=context.xg_justification,
                        point_2_h2h_tactics=context.h2h_tactical_justification,
                        point_3_context_form=context.team_context_justification,
                        pitch_dynamic=context.pitch_dynamic,
                        is_fallback=True,
                        status_badge="🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)",
                        warning_message=warning,
                    )

        # -------------------------------------------------------------
        # Section 2 : Le Meilleur Pari Simple (Sweet spot 1.50 - 3.00 sur la semaine)
        # -------------------------------------------------------------
        sweet_spot_solid = [
            r for r in recommendations
            if self.config.min_odds <= r.winamax_odds <= self.config.max_odds
            and self._is_solid_winner_pick(r)
        ]
        top_rec = sweet_spot_solid[0] if sweet_spot_solid else None

        # Priorité aux sélections validées EV > 0 :
        # Si une opportunité du Sweet Spot a une EV > 0 et passe le filtre anti-surprise,
        # elle DOIT obligatoirement devenir le Pari Simple [VALIDÉ] avant d'envisager le mode [SECOURS].
        if not top_rec:
            sweet_spot_valid = [
                r for r in recommendations
                if self.config.min_odds <= r.winamax_odds <= self.config.max_odds
                and not r.is_fallback
                and r.ev_pct > 0
            ]
            if sweet_spot_valid:
                top_rec = sweet_spot_valid[0]
            else:
                # Vérifier parmi toutes les opportunités calculées (all_opps)
                sweet_spot_ev_pos = [
                    o for o in all_opps
                    if self.config.min_odds <= o.odds <= self.config.max_odds
                    and o.ev > self.config.min_ev_threshold
                    and not (o.selection_key in ("home", "away") and o.rejection_reason and "Cohérence sportive" in o.rejection_reason)
                ]
                if sweet_spot_ev_pos:
                    sweet_spot_ev_pos.sort(key=score_ranking, reverse=True)
                    best_ev_opp = sweet_spot_ev_pos[0]
                    matching_fix = next(
                        (f for f in fixtures if f.home_team == best_ev_opp.home_team and f.away_team == best_ev_opp.away_team),
                        None,
                    )
                    kickoff = matching_fix.commence_time if matching_fix else "N/A"
                    home_metrics = self.stats_provider.get_team_metrics(best_ev_opp.home_team, is_home=True)
                    away_metrics = self.stats_provider.get_team_metrics(best_ev_opp.away_team, is_home=False)
                    context = self.stats_provider.generate_context_justification(
                        home_team=best_ev_opp.home_team,
                        away_team=best_ev_opp.away_team,
                        home_metrics=home_metrics,
                        away_metrics=away_metrics,
                        market_key=best_ev_opp.market_type,
                        selection_key=best_ev_opp.selection_key,
                    )
                    kelly_res = calculate_kelly_stake(
                        true_prob=best_ev_opp.model_true_prob,
                        odds=best_ev_opp.odds,
                        bankroll=self.config.total_bankroll,
                        kelly_multiplier=self.config.kelly_fraction,
                        min_odds=self.config.min_odds,
                        max_odds=self.config.max_odds,
                        min_prob_threshold=self.config.min_prob_threshold,
                        min_prob_low_odds=self.config.min_prob_low_odds,
                    )
                    stake = kelly_res.final_stake_eur if (not kelly_res.is_rejected and kelly_res.final_stake_eur > 0) else self.config.min_stake
                    top_rec = BetRecommendation(
                        competition=best_ev_opp.competition,
                        match_title=best_ev_opp.match_title,
                        kickoff=kickoff,
                        market_name=best_ev_opp.market_type,
                        selection_label=best_ev_opp.selection,
                        bookmaker="Winamax",
                        winamax_odds=best_ev_opp.odds,
                        raw_implied_prob_pct=best_ev_opp.raw_implied_prob * 100.0,
                        fair_bookmaker_prob_pct=best_ev_opp.fair_bookmaker_prob * 100.0,
                        model_true_prob_pct=best_ev_opp.model_true_prob * 100.0,
                        edge_pct=best_ev_opp.edge_pct,
                        ev_pct=best_ev_opp.ev_pct,
                        stake_eur=stake,
                        stake_details=kelly_res.reason if not kelly_res.is_rejected else f"Mise calibrée ({stake:.2f} €) pour sélection Sweet Spot à EV positive.",
                        point_1_xg=context.xg_justification,
                        point_2_h2h_tactics=context.h2h_tactical_justification,
                        point_3_context_form=context.team_context_justification,
                        pitch_dynamic=context.pitch_dynamic,
                        is_fallback=False,
                        status_badge="🟢 OPPORTUNITÉ VALIDÉE (EV > 0)",
                        warning_message="",
                    )

        # Collecter les autres opportunités distinctes validées (EV > 0)
        primary_match_keys = set()
        if top_rec:
            primary_match_keys.add((top_rec.match_title, top_rec.selection_label))
        if match_of_the_day:
            primary_match_keys.add((match_of_the_day.match_title, match_of_the_day.selection_label))

        secondary_recs: List[BetRecommendation] = []
        for r in recommendations:
            key = (r.match_title, r.selection_label)
            if key not in primary_match_keys and not r.is_fallback and r.ev_pct > 0:
                secondary_recs.append(r)
                if len(secondary_recs) >= 6:
                    break

        # Mode de secours Section 2 : si aucun pari simple à EV > 0 sur la semaine
        if not top_rec and all_opps:
            sweet_spot_opps = [o for o in all_opps if self.config.min_odds <= o.odds <= self.config.max_odds]
            pool = sweet_spot_opps if sweet_spot_opps else [
                o for o in all_opps if self.config.absolute_min_odds <= o.odds <= 10.00
            ]

            def simple_fallback_score(o: ValueOpportunity) -> float:
                solid_bonus = 1.25 if o.is_solid_market else 1.0
                return (o.model_true_prob * 1.4 + (1.0 + o.ev)) * solid_bonus

            pool_sorted = sorted(pool, key=simple_fallback_score, reverse=True)
            best_simple_fb = pool_sorted[0]

            matching_fix = next(
                (f for f in fixtures if f.home_team == best_simple_fb.home_team and f.away_team == best_simple_fb.away_team),
                None,
            )
            kickoff = matching_fix.commence_time if matching_fix else "N/A"
            home_metrics = self.stats_provider.get_team_metrics(best_simple_fb.home_team, is_home=True)
            away_metrics = self.stats_provider.get_team_metrics(best_simple_fb.away_team, is_home=False)
            context = self.stats_provider.generate_context_justification(
                home_team=best_simple_fb.home_team,
                away_team=best_simple_fb.away_team,
                home_metrics=home_metrics,
                away_metrics=away_metrics,
                market_key=best_simple_fb.market_type,
                selection_key=best_simple_fb.selection_key,
            )

            fb_stake_res = calculate_fallback_stake(
                fallback_amount=self.config.fallback_stake,
                reason_prefix=f"Pari simple de secours ({best_simple_fb.selection})"
            )

            warning = (
                "⚠️ OPTION DE SECOURS — SOUS-OPTIMALE : Aucun pari simple n'offre d'EV positive "
                f"dans la plage [1.50, 3.00] sur l'ensemble de la semaine (EV: {best_simple_fb.ev_pct:+.2f}%). "
                f"Voici la sélection présentant la meilleure robustesse statistique ({best_simple_fb.selection} @ {best_simple_fb.odds:.2f}). "
                f"Mise symbolique minimale ({fb_stake_res.final_stake_eur:.2f} €) pour préserver votre capital."
            )

            top_rec = BetRecommendation(
                competition=best_simple_fb.competition,
                match_title=best_simple_fb.match_title,
                kickoff=kickoff,
                market_name=best_simple_fb.market_type,
                selection_label=best_simple_fb.selection,
                bookmaker="Winamax",
                winamax_odds=best_simple_fb.odds,
                raw_implied_prob_pct=best_simple_fb.raw_implied_prob * 100.0,
                fair_bookmaker_prob_pct=best_simple_fb.fair_bookmaker_prob * 100.0,
                model_true_prob_pct=best_simple_fb.model_true_prob * 100.0,
                edge_pct=best_simple_fb.edge_pct,
                ev_pct=best_simple_fb.ev_pct,
                stake_eur=fb_stake_res.final_stake_eur,
                stake_details=fb_stake_res.reason,
                point_1_xg=context.xg_justification,
                point_2_h2h_tactics=context.h2h_tactical_justification,
                point_3_context_form=context.team_context_justification,
                pitch_dynamic=context.pitch_dynamic,
                is_fallback=True,
                status_badge="🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)",
                warning_message=warning,
            )

        # -------------------------------------------------------------
        # Section 3 : Générateur de combinés intelligents (2 à 3 sélections indépendantes)
        # -------------------------------------------------------------
        candidate_parlay_legs: List[ParlayLeg] = []
        for opp in all_opps:
            # Sélections sécurisées à haute probabilité (P >= 60%) pour le combiné
            if opp.model_true_prob >= self.config.parlay_min_prob and opp.odds >= 1.15:
                matching_fix = next(
                    (f for f in fixtures if f.home_team == opp.home_team and f.away_team == opp.away_team),
                    None,
                )
                kickoff = matching_fix.commence_time if matching_fix else "N/A"
                candidate_parlay_legs.append(
                    ParlayLeg(
                        match_title=opp.match_title,
                        competition=opp.competition,
                        kickoff=kickoff,
                        market_type=opp.market_type,
                        selection=opp.selection,
                        odds=opp.odds,
                        model_true_prob=opp.model_true_prob,
                        fair_prob=opp.fair_bookmaker_prob,
                    )
                )

        # Trouver et classer les meilleurs combinés
        parlays = find_best_parlays(
            candidate_legs=candidate_parlay_legs,
            bankroll=self.config.total_bankroll,
            parlay_kelly_fraction=self.config.parlay_kelly_fraction,
            min_odds=self.config.parlay_min_odds,
            max_odds=self.config.parlay_max_odds,
            max_stake=self.config.parlay_max_stake,
            min_leg_prob=self.config.parlay_min_prob,
            min_ev=self.config.min_ev_threshold,
        )

        top_parlay = parlays[0] if parlays else None
        secondary_parlays = parlays[1:4] if len(parlays) > 1 else []

        # Mode de secours Section 3 : si aucun combiné à EV > 0
        if not top_parlay and candidate_parlay_legs:
            top_parlay = find_fallback_parlay(candidate_parlay_legs, fallback_stake=self.config.fallback_stake)

        if not top_parlay and len(all_opps) >= 2:
            broader_legs: List[ParlayLeg] = []
            for opp in all_opps:
                if opp.odds < self.config.absolute_min_odds or opp.odds > 10.00:
                    continue
                matching_fix = next(
                    (f for f in fixtures if f.home_team == opp.home_team and f.away_team == opp.away_team),
                    None,
                )
                kickoff = matching_fix.commence_time if matching_fix else "N/A"
                broader_legs.append(
                    ParlayLeg(
                        match_title=opp.match_title,
                        competition=opp.competition,
                        kickoff=kickoff,
                        market_type=opp.market_type,
                        selection=opp.selection,
                        odds=opp.odds,
                        model_true_prob=opp.model_true_prob,
                        fair_prob=opp.fair_bookmaker_prob,
                    )
                )
            top_parlay = find_fallback_parlay(broader_legs, fallback_stake=self.config.fallback_stake)

        # -------------------------------------------------------------
        # Section 4 : La « Cote Osée » (Fun Bet cote >= 4.00, Micro-Kelly)
        # -------------------------------------------------------------
        longshot_candidates: List[ValueOpportunity] = []
        for opp in all_opps:
            if (
                self.config.longshot_min_odds <= opp.odds <= self.config.longshot_max_odds
                and opp.ev > self.config.min_ev_threshold
            ):
                # Filtre de cohérence sportive : exclure victoire sèche d'une équipe en série de défaites ou sans victoire
                if opp.selection_key in ("home", "away") and opp.rejection_reason and "Cohérence sportive" in opp.rejection_reason:
                    continue

                micro_kelly = calculate_micro_kelly_stake(
                    true_prob=opp.model_true_prob,
                    odds=opp.odds,
                    bankroll=self.config.total_bankroll,
                    kelly_multiplier=self.config.longshot_kelly_fraction,
                    min_odds=self.config.longshot_min_odds,
                    max_odds=self.config.longshot_max_odds,
                    max_stake=self.config.longshot_max_stake,
                    min_stake=self.config.longshot_min_stake,
                )
                if not micro_kelly.is_rejected and micro_kelly.final_stake_eur > 0:
                    opp.recommended_stake = micro_kelly.final_stake_eur
                    longshot_candidates.append(opp)

        # Classer par EV la plus élevée
        longshot_candidates.sort(key=lambda o: o.ev, reverse=True)

        longshot_rec: Optional[BetRecommendation] = None
        if longshot_candidates:
            best_ls = longshot_candidates[0]
            matching_fix = next(
                (f for f in fixtures if f.home_team == best_ls.home_team and f.away_team == best_ls.away_team),
                None,
            )
            kickoff = matching_fix.commence_time if matching_fix else "N/A"
            home_metrics = self.stats_provider.get_team_metrics(best_ls.home_team, is_home=True)
            away_metrics = self.stats_provider.get_team_metrics(best_ls.away_team, is_home=False)
            context = self.stats_provider.generate_context_justification(
                home_team=best_ls.home_team,
                away_team=best_ls.away_team,
                home_metrics=home_metrics,
                away_metrics=away_metrics,
                market_key=best_ls.market_type,
                selection_key=best_ls.selection_key,
            )
            micro_kelly = calculate_micro_kelly_stake(
                true_prob=best_ls.model_true_prob,
                odds=best_ls.odds,
                bankroll=self.config.total_bankroll,
                kelly_multiplier=self.config.longshot_kelly_fraction,
                min_odds=self.config.longshot_min_odds,
                max_odds=self.config.longshot_max_odds,
                max_stake=self.config.longshot_max_stake,
                min_stake=self.config.longshot_min_stake,
            )
            longshot_rec = BetRecommendation(
                competition=best_ls.competition,
                match_title=best_ls.match_title,
                kickoff=kickoff,
                market_name=best_ls.market_type,
                selection_label=best_ls.selection,
                bookmaker="Winamax",
                winamax_odds=best_ls.odds,
                raw_implied_prob_pct=best_ls.raw_implied_prob * 100.0,
                fair_bookmaker_prob_pct=best_ls.fair_bookmaker_prob * 100.0,
                model_true_prob_pct=best_ls.model_true_prob * 100.0,
                edge_pct=best_ls.edge_pct,
                ev_pct=best_ls.ev_pct,
                stake_eur=best_ls.recommended_stake,
                stake_details=micro_kelly.reason,
                point_1_xg=context.xg_justification,
                point_2_h2h_tactics=context.h2h_tactical_justification,
                point_3_context_form=context.team_context_justification,
                pitch_dynamic=context.pitch_dynamic,
            )
        elif all_opps:
            # Mode de secours Section 4 : strictement comprise entre 4.00 et 10.00
            high_odds_opps = [
                o for o in all_opps
                if self.config.longshot_min_odds <= o.odds <= self.config.longshot_max_odds
            ]
            if high_odds_opps:
                high_odds_opps.sort(key=lambda o: (o.ev, o.model_true_prob), reverse=True)
                best_high_fb = high_odds_opps[0]

                matching_fix = next(
                    (f for f in fixtures if f.home_team == best_high_fb.home_team and f.away_team == best_high_fb.away_team),
                    None,
                )
                kickoff = matching_fix.commence_time if matching_fix else "N/A"
                home_metrics = self.stats_provider.get_team_metrics(best_high_fb.home_team, is_home=True)
                away_metrics = self.stats_provider.get_team_metrics(best_high_fb.away_team, is_home=False)
                context = self.stats_provider.generate_context_justification(
                    home_team=best_high_fb.home_team,
                    away_team=best_high_fb.away_team,
                    home_metrics=home_metrics,
                    away_metrics=away_metrics,
                    market_key=best_high_fb.market_type,
                    selection_key=best_high_fb.selection_key,
                )

                fb_stake_res = calculate_fallback_stake(
                    fallback_amount=self.config.fallback_stake,
                    reason_prefix=f"Fun Bet de secours ({best_high_fb.selection} @ {best_high_fb.odds:.2f})",
                )

                warning = (
                    f"⚠️ OPTION DE SECOURS — SOUS-OPTIMALE : Aucune cote osée (entre {self.config.longshot_min_odds:.2f} et {self.config.longshot_max_odds:.2f}) ne présente d'EV positive. "
                    f"Sélection de la cote haute la plus proche de l'équilibre mathématique ({best_high_fb.selection} @ {best_high_fb.odds:.2f}, EV: {best_high_fb.ev_pct:+.2f}%). "
                    f"Mise symbolique minimale ({fb_stake_res.final_stake_eur:.2f} €) pour tester la cote sans risquer son capital."
                )

                longshot_rec = BetRecommendation(
                    competition=best_high_fb.competition,
                    match_title=best_high_fb.match_title,
                    kickoff=kickoff,
                    market_name=best_high_fb.market_type,
                    selection_label=best_high_fb.selection,
                    bookmaker="Winamax",
                    winamax_odds=best_high_fb.odds,
                    raw_implied_prob_pct=best_high_fb.raw_implied_prob * 100.0,
                    fair_bookmaker_prob_pct=best_high_fb.fair_bookmaker_prob * 100.0,
                    model_true_prob_pct=best_high_fb.model_true_prob * 100.0,
                    edge_pct=best_high_fb.edge_pct,
                    ev_pct=best_high_fb.ev_pct,
                    stake_eur=fb_stake_res.final_stake_eur,
                    stake_details=fb_stake_res.reason,
                    point_1_xg=context.xg_justification,
                    point_2_h2h_tactics=context.h2h_tactical_justification,
                    point_3_context_form=context.team_context_justification,
                    pitch_dynamic=context.pitch_dynamic,
                    is_fallback=True,
                    status_badge="🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)",
                    warning_message=warning,
                )

        return DailyReport(
            timestamp=timestamp,
            total_matches_analyzed=len(fixtures),
            total_markets_analyzed=len(all_opps),
            positive_ev_count=len(confirmed_value_opps),
            match_of_the_day=match_of_the_day,
            top_recommendation=top_rec,
            secondary_recommendations=secondary_recs,
            top_parlay=top_parlay,
            secondary_parlays=secondary_parlays,
            longshot_recommendation=longshot_rec,
            current_bankroll=self.config.total_bankroll,
            total_profit=float(self.bankroll_data.get("total_profit", 0.0)) if hasattr(self, "bankroll_data") else 0.0,
        )
