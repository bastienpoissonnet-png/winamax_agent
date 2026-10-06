"""Bivariate Poisson and Dixon-Coles statistical model based on Expected Goals (xG).

Calculates true probability distribution for football match outcomes:
- 1X2 (Home Win, Draw, Away Win)
- Over / Under 2.5 Goals
- Both Teams to Score (BTTS)
- Exact score matrix
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class TeamMetrics:
    """Statistical and advanced metrics for a football club."""
    name: str
    xg_for_per_match: float       # Rolling xG generated per game (last 5-10 matches)
    xg_against_per_match: float   # Rolling xG conceded per game
    recent_form_points: float     # Points in last 5 matches (0 to 15)
    key_absences_impact: float = 0.0  # Percentage penalty on strength (-0.15 to 0.0)
    fatigue_index: float = 0.0    # 0.0 (rested) to 1.0 (midweek European travel)


@dataclass
class MatchProbabilities:
    """Calculated true probabilities for all standard betting markets."""
    home_team: str
    away_team: str
    lambda_home: float            # Expected goals for home team
    mu_away: float                # Expected goals for away team
    prob_home_win: float          # P(Home Win)
    prob_draw: float              # P(Draw)
    prob_away_win: float          # P(Away Win)
    prob_over_2_5: float          # P(Total goals > 2.5)
    prob_under_2_5: float         # P(Total goals < 2.5)
    prob_btts_yes: float          # P(Both Teams To Score - Yes)
    prob_btts_no: float           # P(Both Teams To Score - No)
    score_matrix: Dict[Tuple[int, int], float] = field(default_factory=dict)

    def as_market_dict(self) -> Dict[str, float]:
        """Maps market outcome keys to modeled true probabilities."""
        return {
            "home": self.prob_home_win,
            "draw": self.prob_draw,
            "away": self.prob_away_win,
            "over_2.5": self.prob_over_2_5,
            "under_2.5": self.prob_under_2_5,
            "btts_yes": self.prob_btts_yes,
            "btts_no": self.prob_btts_no,
        }


def _poisson_pmf(k: int, lambda_: float) -> float:
    """Poisson probability mass function P(X = k; lambda)."""
    if lambda_ <= 0:
        return 1.0 if k == 0 else 0.0
    return (lambda_ ** k) * math.exp(-lambda_) / math.factorial(k)


def _dixon_coles_tau(x: int, y: int, lambda_: float, mu: float, rho: float) -> float:
    """Dixon-Coles correlation factor for low scorelines (0-0, 1-0, 0-1, 1-1).

    Corrects for the well-known independence limitation of classic Poisson.
    """
    if x == 0 and y == 0:
        return 1.0 - lambda_ * mu * rho
    elif x == 0 and y == 1:
        return 1.0 + lambda_ * rho
    elif x == 1 and y == 0:
        return 1.0 + mu * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


class XgPoissonEngine:
    """Quantitative football model integrating xG, Dixon-Coles and team context."""

    def __init__(
        self,
        league_avg_goals: float = 2.70,
        home_advantage: float = 1.18,
        dixon_coles_rho: float = -0.06,
        max_goals: int = 8,
    ):
        self.league_avg_goals = league_avg_goals
        self.home_avg = league_avg_goals / 2.0
        self.home_advantage = home_advantage
        self.rho = dixon_coles_rho
        self.max_goals = max_goals

    def calculate_expected_goals(
        self, home_metrics: TeamMetrics, away_metrics: TeamMetrics
    ) -> Tuple[float, float]:
        """Calculates lambda (home expected goals) and mu (away expected goals).

        Considers:
        - Relative attack and defense indices vs league average
        - Home field advantage
        - Key absences and recent form adjustments
        """
        # Baseline per-team average
        base_goal = self.home_avg

        # Attack and defense strength ratios
        home_att = home_metrics.xg_for_per_match / base_goal
        home_def = home_metrics.xg_against_per_match / base_goal

        away_att = away_metrics.xg_for_per_match / base_goal
        away_def = away_metrics.xg_against_per_match / base_goal

        # Context adjustments (absences: e.g. -0.10, fatigue: -0.05)
        home_ctx = 1.0 + home_metrics.key_absences_impact - (0.05 * home_metrics.fatigue_index)
        away_ctx = 1.0 + away_metrics.key_absences_impact - (0.05 * away_metrics.fatigue_index)

        # Expected goals
        lambda_home = home_att * away_def * self.home_advantage * base_goal * max(0.5, home_ctx)
        mu_away = away_att * home_def * base_goal * max(0.5, away_ctx)

        # Realistic safety bounds for 90 minutes
        lambda_home = max(0.2, min(5.0, lambda_home))
        mu_away = max(0.2, min(5.0, mu_away))

        return lambda_home, mu_away

    def simulate_match(
        self, home_metrics: TeamMetrics, away_metrics: TeamMetrics
    ) -> MatchProbabilities:
        """Simulates full scoreline matrix and aggregates betting market probabilities."""
        lambda_h, mu_a = self.calculate_expected_goals(home_metrics, away_metrics)

        score_matrix: Dict[Tuple[int, int], float] = {}
        total_p = 0.0

        for x in range(self.max_goals):
            p_x = _poisson_pmf(x, lambda_h)
            for y in range(self.max_goals):
                p_y = _poisson_pmf(y, mu_a)
                tau = _dixon_coles_tau(x, y, lambda_h, mu_a, self.rho)
                p_xy = p_x * p_y * max(0.0, tau)
                score_matrix[(x, y)] = p_xy
                total_p += p_xy

        # Re-normalize for tail cutoff beyond max_goals
        if total_p > 0:
            for k in score_matrix:
                score_matrix[k] /= total_p

        p_home_win = sum(p for (x, y), p in score_matrix.items() if x > y)
        p_draw = sum(p for (x, y), p in score_matrix.items() if x == y)
        p_away_win = sum(p for (x, y), p in score_matrix.items() if x < y)

        p_over_2_5 = sum(p for (x, y), p in score_matrix.items() if x + y > 2)
        p_under_2_5 = sum(p for (x, y), p in score_matrix.items() if x + y <= 2)

        p_btts_yes = sum(p for (x, y), p in score_matrix.items() if x > 0 and y > 0)
        p_btts_no = 1.0 - p_btts_yes

        return MatchProbabilities(
            home_team=home_metrics.name,
            away_team=away_metrics.name,
            lambda_home=lambda_h,
            mu_away=mu_a,
            prob_home_win=p_home_win,
            prob_draw=p_draw,
            prob_away_win=p_away_win,
            prob_over_2_5=p_over_2_5,
            prob_under_2_5=p_under_2_5,
            prob_btts_yes=p_btts_yes,
            prob_btts_no=p_btts_no,
            score_matrix=score_matrix,
        )
