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
    market_type: str             # "Double Chance", "Total Buts (Plus/Moins)", "1X2"
    selection: str               # "Victoire Paris SG ou Nul (1X)", "Plus de 1.5 buts", etc.
    selection_key: str           # "1x", "x2", "over_1.5", "under_3.5", "home", etc.
    odds: float                  # Cote Winamax
    raw_implied_prob: float      # 1 / Cote (avec marge)
    fair_bookmaker_prob: float   # Probabilité implicite Winamax sans marge
    model_true_prob: float       # Probabilité réelle calculée par notre modèle xG/Poisson
    edge: float                  # model_true_prob - fair_bookmaker_prob
    ev: float                    # (model_true_prob * odds) - 1.0 (Expected Value en %)
    recommended_stake: float = 0.0  # Mise recommandée calculée par le critère de Kelly (€)
    is_value: bool = False
    rejection_reason: str = ""
    is_solid_market: bool = False   # True pour Double Chance ou totaux sécurisés
    pitch_dynamic: str = ""         # Explication sportive synthétique de terrain

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
    min_ev_threshold: float = 0.005,
    min_odds: float = 1.50,
    max_odds: float = 3.00,
    min_prob_threshold: float = 0.40,
    min_prob_low_odds: float = 0.60,
    team_streak: str = "",
    wins_l5: Optional[int] = None,
    losses_l5: Optional[int] = None,
    recent_form_points: Optional[float] = None,
    pitch_dynamic: str = "",
) -> ValueOpportunity:
    """Evaluates whether an outcome is a Solid Value Bet meeting strict risk & sports filters.

    Criteria for Solid Value:
        1. Expected Value EV > min_ev_threshold (+0.5%)
        2. Odds strictly within [min_odds, max_odds] (e.g. 1.50 to 3.00)
        3. Model true probability >= min_prob_threshold
        4. If odds < 1.60, model true probability >= min_prob_low_odds (60%)
        5. Filtre de cohérence sportive : Rejette la victoire sèche d'une équipe
           sans victoire récente ou en série de défaites.
    """
    raw_implied = 1.0 / winamax_odds if winamax_odds > 0 else 0.0
    ev = (model_true_prob * winamax_odds) - 1.0
    edge = model_true_prob - fair_bookmaker_prob
    match_title = f"{home_team} vs {away_team}"

    is_solid_market = selection_key in ("1x", "x2", "over_1.5", "under_3.5", "under_2.5", "over_2.5")

    rejection = ""
    is_value = True

    if ev <= min_ev_threshold:
        is_value = False
        rejection = f"EV non positive ({ev*100:.1f}% <= {min_ev_threshold*100:.1f}%)"
    elif winamax_odds < min_odds:
        is_value = False
        rejection = f"Cote trop basse ({winamax_odds:.2f} < {min_odds:.2f})"
    elif winamax_odds > max_odds:
        is_value = False
        rejection = f"Cote trop élevée ({winamax_odds:.2f} > {max_odds:.2f})"
    elif model_true_prob < min_prob_threshold:
        is_value = False
        rejection = f"Probabilité trop faible ({model_true_prob*100:.1f}% < {min_prob_threshold*100:.0f}%)"
    elif winamax_odds < 1.60 and model_true_prob < min_prob_low_odds:
        is_value = False
        rejection = f"Probabilité insuffisante pour cote < 1.60 ({model_true_prob*100:.1f}% < {min_prob_low_odds*100:.0f}%)"

    # 3. Filtre de cohérence sportive (anti-surprise improbable)
    if is_value and selection_key in ("home", "away"):
        backed_team = home_team if selection_key == "home" else away_team
        streak_clean = team_streak.replace(" ", "") if team_streak else ""
        results = [r for r in streak_clean.split("-") if r]

        # Équipe n'ayant remporté aucun match récent
        no_recent_win = (wins_l5 == 0) if wins_l5 is not None else (len(results) > 0 and "V" not in results)

        # Équipe sur une série de défaites (terminant par 2+ défaites ou cumul défavorable)
        consecutive_losses = 0
        for r in reversed(results):
            if r == "D":
                consecutive_losses += 1
            else:
                break

        losing_streak = (
            consecutive_losses >= 2
            or (losses_l5 is not None and losses_l5 >= 3 and (wins_l5 or 0) <= 1)
            or (recent_form_points is not None and recent_form_points <= 4.0 and (wins_l5 or 0) <= 1)
        )

        if no_recent_win or losing_streak:
            is_value = False
            detail = "aucune victoire récente" if no_recent_win else f"série de défaites ({team_streak})"
            rejection = f"Cohérence sportive : victoire sèche de {backed_team} rejetée ({detail})"

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
        rejection_reason=rejection,
        is_solid_market=is_solid_market,
        pitch_dynamic=pitch_dynamic,
    )
