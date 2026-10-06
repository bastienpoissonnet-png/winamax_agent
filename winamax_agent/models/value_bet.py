"""Evaluation of betting opportunities, Edge, and Expected Value (EV)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValueOpportunity:
    """Represents an evaluated betting opportunity on Winamax."""
    competition: str
    match_title: str
    home_team: str
    away_team: str
    market_type: str             # "1X2" or "Over/Under 2.5"
    selection: str               # "Victoire Paris SG", "Match Nul", "Plus de 2.5 buts", etc.
    selection_key: str           # "home", "draw", "away", "over_2.5", "under_2.5"
    odds: float                  # Cote Winamax
    raw_implied_prob: float      # 1 / Cote (avec marge)
    fair_bookmaker_prob: float   # Probabilité implicite Winamax sans marge
    model_true_prob: float       # Probabilité réelle calculée par notre modèle xG/Poisson
    edge: float                  # model_true_prob - fair_bookmaker_prob
    ev: float                    # (model_true_prob * odds) - 1.0 (Expected Value en %)
    recommended_stake: float = 0.0  # Mise recommandée calculée par le critère de Kelly (€)
    is_value: bool = False

    @property
    def ev_pct(self) -> float:
        """EV in percentage points."""
        return self.ev * 100.0

    @property
    def edge_pct(self) -> float:
        """Edge in percentage points."""
        return self.edge * 100.0


def evaluate_bet(
    competition: str,
    home_team: str,
    away_team: str,
    market_type: str,
    selection: str,
    selection_key: str,
    winamax_odds: float,
    fair_bookmaker_prob: float,
    model_true_prob: float,
    min_ev_threshold: float = 0.0,
) -> ValueOpportunity:
    """Evaluates whether an outcome is a Value Bet with positive Expected Value.

    Expected Value Formula:
        EV = (P_true * Odds) - 1.0
        EV > 0 signifies a mathematically profitable long-term expectation.
    """
    raw_implied = 1.0 / winamax_odds if winamax_odds > 0 else 0.0
    ev = (model_true_prob * winamax_odds) - 1.0
    edge = model_true_prob - fair_bookmaker_prob
    is_value = ev > min_ev_threshold

    match_title = f"{home_team} vs {away_team}"

    return ValueOpportunity(
        competition=competition,
        match_title=match_title,
        home_team=home_team,
        away_team=away_team,
        market_type=market_type,
        selection=selection,
        selection_key=selection_key,
        odds=winamax_odds,
        raw_implied_prob=raw_implied,
        fair_bookmaker_prob=fair_bookmaker_prob,
        model_true_prob=model_true_prob,
        edge=edge,
        ev=ev,
        is_value=is_value,
    )
