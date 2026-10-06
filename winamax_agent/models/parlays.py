"""Intelligent Accumulator / Parlay Generator module for 2-3 independent selections."""

from __future__ import annotations
import itertools
from dataclasses import dataclass, field
from typing import List, Optional
from winamax_agent.staking.kelly import calculate_parlay_kelly_stake


@dataclass
class ParlayLeg:
    """A single selection within a parlay."""
    match_title: str
    competition: str
    kickoff: str
    market_type: str
    selection: str
    odds: float
    model_true_prob: float
    fair_prob: float

    @property
    def prob_pct(self) -> float:
        return self.model_true_prob * 100.0


@dataclass
class ParlayOpportunity:
    """An evaluated multi-match accumulator meeting strict risk and odds criteria."""
    legs: List[ParlayLeg]
    total_odds: float
    combined_true_prob: float
    combined_fair_prob: float
    combined_ev: float
    recommended_stake: float = 0.0
    stake_details: str = ""
    cross_justification: str = ""
    is_fallback: bool = False
    status_badge: str = "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)"
    warning_message: str = ""

    def __post_init__(self):
        if self.is_fallback:
            if not self.status_badge or self.status_badge == "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)":
                self.status_badge = "🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)"
        else:
            if not self.status_badge:
                self.status_badge = "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)"

    @property
    def legs_count(self) -> int:
        return len(self.legs)

    @property
    def combined_ev_pct(self) -> float:
        return self.combined_ev * 100.0

    @property
    def combined_prob_pct(self) -> float:
        return self.combined_true_prob * 100.0


def generate_cross_justification(legs: List[ParlayLeg], is_fallback: bool = False) -> str:
    """Generates an analytical cross-justification explaining statistical independence."""
    parts = []
    for i, leg in enumerate(legs, 1):
        parts.append(
            f"Jambe {i} : {leg.match_title} ({leg.competition}) -> {leg.selection} @ {leg.odds:.2f} "
            f"(P_modèle: {leg.prob_pct:.1f}%)"
        )
    if is_fallback:
        synthesis = (
            f"Sécurisation de secours : Les {len(legs)} sélections portent sur des rencontres 100% distinctes (indépendance aléatoire). "
            f"Ces sélections maximisent la probabilité individuelle de succès, même si l'EV combinée reste légèrement négative face à la marge du bookmaker. "
            f"Mise symbolique minimale recommandée (1.00 €) pour ne pas exposer le capital."
        )
    else:
        synthesis = (
            f"Sécurisation croisée : Les {len(legs)} sélections portent sur des rencontres 100% distinctes (indépendance aléatoire). "
            f"Chaque jambe a été sélectionnée pour sa haute probabilité individuelle (>= 60%), produisant une espérance combinée positive "
            f"tout en maintenant un risque maîtrisé sur la cote globale."
        )
    return " | ".join(parts) + "\n   " + synthesis


def find_best_parlays(
    candidate_legs: List[ParlayLeg],
    bankroll: float = 500.0,
    parlay_kelly_fraction: float = 0.35,
    min_odds: float = 1.80,
    max_odds: float = 4.00,
    max_stake: float = 15.0,
    min_leg_prob: float = 0.60,
    min_ev: float = 0.005,
) -> List[ParlayOpportunity]:
    """Generates and ranks intelligent 2-3 leg parlays from high-probability candidate selections.

    Rules:
        - Individual legs must have model true probability >= min_leg_prob (60%)
        - Strict match independence (each leg from a distinct fixture)
        - Total combined odds within [min_odds, max_odds] (1.80 - 4.00)
        - Combined EV strictly positive (> min_ev)
        - Kelly staking capped at max_stake (15.0 € max)
    """
    # Filter candidate legs for high confidence and strict odds cap (<= 10.00)
    valid_legs = [
        leg for leg in candidate_legs
        if leg.model_true_prob >= min_leg_prob and 1.15 <= leg.odds <= 10.00
    ]

    if len(valid_legs) < 2:
        return []

    parlay_results: List[ParlayOpportunity] = []

    # Explore 2-leg and 3-leg combinations
    for combo_size in [2, 3]:
        for combo in itertools.combinations(valid_legs, combo_size):
            # Check distinct matches
            matches = [leg.match_title for leg in combo]
            if len(set(matches)) != len(matches):
                continue

            # Calculate total combined odds
            total_odds = 1.0
            for leg in combo:
                total_odds *= leg.odds
            total_odds = round(total_odds, 2)

            # Check target odds range [min_odds, max_odds] and strict ceiling (<= 10.00)
            if total_odds < min_odds or total_odds > max_odds or total_odds > 10.00:
                continue

            # Calculate combined true probability (product of independent probabilities)
            p_combo_true = 1.0
            p_combo_fair = 1.0
            for leg in combo:
                p_combo_true *= leg.model_true_prob
                p_combo_fair *= leg.fair_prob

            # Calculate combined EV
            combined_ev = (p_combo_true * total_odds) - 1.0

            # Must have positive EV
            if combined_ev < min_ev:
                continue

            # Staking calculation
            kelly_res = calculate_parlay_kelly_stake(
                parlay_true_prob=p_combo_true,
                parlay_odds=total_odds,
                bankroll=bankroll,
                kelly_multiplier=parlay_kelly_fraction,
                min_odds=min_odds,
                max_odds=max_odds,
                max_stake=max_stake,
            )

            if kelly_res.is_rejected or kelly_res.final_stake_eur <= 0.0:
                continue

            cross_justif = generate_cross_justification(list(combo))

            parlay_opp = ParlayOpportunity(
                legs=list(combo),
                total_odds=total_odds,
                combined_true_prob=p_combo_true,
                combined_fair_prob=p_combo_fair,
                combined_ev=combined_ev,
                recommended_stake=kelly_res.final_stake_eur,
                stake_details=kelly_res.reason,
                cross_justification=cross_justif,
            )
            parlay_results.append(parlay_opp)

    # Rank parlays: higher combined probability * (1 + EV)
    def parlay_score(p: ParlayOpportunity) -> float:
        return p.combined_true_prob * (1.0 + p.combined_ev)

    parlay_results.sort(key=parlay_score, reverse=True)
    return parlay_results


def find_fallback_parlay(
    candidate_legs: List[ParlayLeg],
    fallback_stake: float = 1.00,
    min_odds: float = 1.40,
    max_odds: float = 5.00,
) -> Optional[ParlayOpportunity]:
    """Builds a fallback 2-leg parlay using the two highest probability selections from distinct matches.

    Used when no parlay satisfies all strict value criteria (EV > 0).
    Categorically rejects any leg with odds > 10.00 (e.g. Viking FK @ 15.00).
    """
    # Strict filter on legs: reject any odds < 1.05 or > 10.00
    valid_legs = [leg for leg in candidate_legs if 1.05 <= leg.odds <= 10.00]
    if len(valid_legs) < 2:
        return None

    # Sort legs by model true probability descending
    sorted_legs = sorted(valid_legs, key=lambda l: l.model_true_prob, reverse=True)

    # Find the top 2 legs from distinct matches with combined total odds <= 10.00
    leg1 = sorted_legs[0]
    leg2: Optional[ParlayLeg] = None
    for leg in sorted_legs[1:]:
        if leg.match_title != leg1.match_title and round(leg1.odds * leg.odds, 2) <= 10.00:
            leg2 = leg
            break

    if not leg2:
        return None

    selected_legs = [leg1, leg2]
    total_odds = round(leg1.odds * leg2.odds, 2)
    p_combo_true = leg1.model_true_prob * leg2.model_true_prob
    p_combo_fair = leg1.fair_prob * leg2.fair_prob
    combined_ev = (p_combo_true * total_odds) - 1.0

    cross_justif = generate_cross_justification(selected_legs, is_fallback=True)
    warning = (
        "⚠️ OPTION DE SECOURS — SOUS-OPTIMALE : L'espérance mathématique combinée est sous l'équilibre "
        f"({combined_ev * 100.0:+.2f}%). Ce combiné assemble les deux sélections les plus fiables "
        "de rencontres distinctes. Mise symbolique bridée à 1.00 € pour préserver votre capital."
    )
    stake_reason = (
        f"Mise symbolique de secours ({fallback_stake:.2f} €) : EV combinée ({combined_ev * 100.0:+.2f}%) "
        "sous le seuil d'espérance positive. Risque et exposition limités au strict minimum."
    )

    return ParlayOpportunity(
        legs=selected_legs,
        total_odds=total_odds,
        combined_true_prob=p_combo_true,
        combined_fair_prob=p_combo_fair,
        combined_ev=combined_ev,
        recommended_stake=fallback_stake,
        stake_details=stake_reason,
        cross_justification=cross_justif,
        is_fallback=True,
        status_badge="🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)",
        warning_message=warning,
    )


