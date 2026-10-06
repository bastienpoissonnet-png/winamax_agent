"""Kelly Criterion and risk-adjusted bankroll sizing module.

Implements Fractional Kelly with odds-tier risk capping for Single Bets and Parlays:
- Paris simples :
    * Plage de cotes Sweet Spot : [1.50, 3.00]
    * Palier 1 [1.50, 1.85] : 10 € à 20 € max (haute confiance)
    * Palier 2 [1.86, 2.30] : plafonné à 10.00 € max
    * Palier 3 [2.31, 3.00] : plafonné à 5.00 € max
    * Cotes < 1.50 ou > 3.00 : 0.00 € (rejet)
- Combinés intelligents :
    * Cote combinée cible : [1.80, 4.00]
    * Plafond strict : 10 € à 15 € maximum
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class KellyResult:
    """Detailed staking calculation result."""
    full_kelly_fraction: float
    fractional_kelly: float
    raw_stake_eur: float
    final_stake_eur: float
    is_capped: bool
    is_floored: bool
    is_rejected: bool
    reason: str


def calculate_kelly_stake(
    true_prob: float,
    odds: float,
    bankroll: float = 500.0,
    kelly_multiplier: float = 0.50,       # Demi-Kelly (50%)
    min_odds: float = 1.50,               # Plancher de cote (Sweet Spot 1.50)
    max_odds: float = 3.00,               # Plafond de cote (Sweet Spot 3.00)
    min_prob_threshold: float = 0.40,     # Probabilité minimale requise
    min_prob_low_odds: float = 0.60,      # Probabilité requise pour cotes < 1.70
) -> KellyResult:
    """Calculates risk-adjusted Fractional Kelly stake for single bets in the Sweet Spot [1.50, 3.00]."""
    if odds <= 1.0 or true_prob <= 0.0 or bankroll <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason="Paramètres invalides ou probabilité nulle",
        )

    # 1. Filtre sur la plage de cote [1.50, 3.00]
    if odds < min_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Cote trop basse ({odds:.2f} < {min_odds:.2f}). Marge bookmaker trop forte.",
        )

    if odds > max_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Cote hors plage ({odds:.2f} > {max_odds:.2f}). Rejet des cotes trop incertaines.",
        )

    # 2. Filtre de probabilité minimale
    if true_prob < min_prob_threshold:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Probabilité trop faible ({true_prob*100:.1f}% < {min_prob_threshold*100:.0f}%).",
        )

    if odds < 1.70 and true_prob < min_prob_low_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Probabilité insuffisante pour cote < 1.70 ({true_prob*100:.1f}% < {min_prob_low_odds*100:.0f}%).",
        )

    # 3. Calcul de l'EV
    b = odds - 1.0
    ev = (true_prob * odds) - 1.0

    if ev <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"EV non positive ({ev*100:.2f}% <= 0). Aucun avantage mathématique.",
        )

    # 4. Calcul de Kelly Fractionnaire
    full_kelly = ev / b
    fractional_kelly = max(0.0, full_kelly * kelly_multiplier)
    raw_stake = fractional_kelly * bankroll

    # 5. Paliers de risque selon la cote
    is_capped = False
    is_floored = False

    if 1.50 <= odds <= 1.85:
        # Palier 1 : Haute confiance -> 10 € à 20 €
        tier_floor = 10.0
        tier_cap = 20.0
        stake = max(tier_floor, min(tier_cap, raw_stake))
        if stake >= tier_cap:
            is_capped = True
        elif stake <= tier_floor:
            is_floored = True
        reason = f"Palier haute confiance (cote {odds:.2f}) : sizing calibré entre {tier_floor:.0f} € et {tier_cap:.0f} €."
    elif 1.86 <= odds <= 2.30:
        # Palier 2 : Cote intermédiaire -> plafonné à 10 € max
        tier_floor = 1.0
        tier_cap = 10.0
        stake = max(tier_floor, min(tier_cap, raw_stake))
        if raw_stake > tier_cap:
            is_capped = True
        elif raw_stake < tier_floor:
            is_floored = True
        reason = f"Palier intermédiaire (cote {odds:.2f}) : plafonné à {tier_cap:.0f} € max (sécurisation du capital)."
    else:
        # Palier 3 : Cotes 2.31 à 3.00 -> plafonné à 5 € max
        tier_floor = 1.0
        tier_cap = 5.0
        stake = max(tier_floor, min(tier_cap, raw_stake))
        if raw_stake > tier_cap:
            is_capped = True
        elif raw_stake < tier_floor:
            is_floored = True
        reason = f"Palier prudent (cote {odds:.2f}) : plafonné strictement à {tier_cap:.0f} € max."

    stake = round(stake, 2)

    return KellyResult(
        full_kelly_fraction=round(full_kelly, 4),
        fractional_kelly=round(fractional_kelly, 4),
        raw_stake_eur=round(raw_stake, 2),
        final_stake_eur=stake,
        is_capped=is_capped,
        is_floored=is_floored,
        is_rejected=False,
        reason=reason,
    )


def calculate_parlay_kelly_stake(
    parlay_true_prob: float,
    parlay_odds: float,
    bankroll: float = 500.0,
    kelly_multiplier: float = 0.35,       # Kelly fractionnaire prudent pour combiné
    min_odds: float = 1.80,
    max_odds: float = 4.00,
    max_stake: float = 15.0,              # Plafond strict combiné (15 € max)
    min_stake: float = 1.0,
) -> KellyResult:
    """Calculates risk-adjusted Fractional Kelly stake for intelligent parlays (2-3 legs)."""
    if parlay_odds <= 1.0 or parlay_true_prob <= 0.0 or bankroll <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason="Paramètres combinés invalides",
        )

    if parlay_odds < min_odds or parlay_odds > max_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Cote combinée ({parlay_odds:.2f}) hors de la cible [{min_odds:.2f}, {max_odds:.2f}].",
        )

    b = parlay_odds - 1.0
    ev = (parlay_true_prob * parlay_odds) - 1.0

    if ev <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"EV combinée non positive ({ev*100:.2f}% <= 0). Aucun avantage mathématique.",
        )

    full_kelly = ev / b
    fractional_kelly = max(0.0, full_kelly * kelly_multiplier)
    raw_stake = fractional_kelly * bankroll

    is_capped = False
    is_floored = False

    stake = raw_stake
    if stake > max_stake:
        stake = max_stake
        is_capped = True
    elif stake < min_stake:
        stake = min_stake
        is_floored = True

    stake = round(stake, 2)

    reason = f"Combiné à valeur (EV: {ev*100:+.2f}%, cote {parlay_odds:.2f}) : Kelly combiné ({kelly_multiplier*100:.0f}%), plafonné à {max_stake:.2f} €."

    return KellyResult(
        full_kelly_fraction=round(full_kelly, 4),
        fractional_kelly=round(fractional_kelly, 4),
        raw_stake_eur=round(raw_stake, 2),
        final_stake_eur=stake,
        is_capped=is_capped,
        is_floored=is_floored,
        is_rejected=False,
        reason=reason,
    )


def calculate_micro_kelly_stake(
    true_prob: float,
    odds: float,
    bankroll: float = 500.0,
    kelly_multiplier: float = 0.15,       # Micro-Kelly (15%) pour amortir la variance élevée
    min_odds: float = 4.00,               # Seuil de cote osée (>= 4.00)
    max_odds: float = 15.00,              # Plafond de cote
    max_stake: float = 5.00,              # Plafond strict pour fun bet (5.00 € max)
    min_stake: float = 1.00,              # Plancher de 1.00 € si EV > 0
) -> KellyResult:
    """Calculates ultra-conservative Micro-Kelly stake for high-odds fun bets (odds >= 4.00)."""
    if odds <= 1.0 or true_prob <= 0.0 or bankroll <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason="Paramètres invalides",
        )

    if odds < min_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Cote inférieure au seuil de Cote Osée ({odds:.2f} < {min_odds:.2f}).",
        )

    if odds > max_odds:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"Cote trop extrême ({odds:.2f} > {max_odds:.2f}). Risque démesuré rejeté.",
        )

    b = odds - 1.0
    ev = (true_prob * odds) - 1.0

    if ev <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            is_rejected=True,
            reason=f"EV non positive ({ev*100:.2f}% <= 0). Aucun avantage mathématique sur cette cote élevée.",
        )

    full_kelly = ev / b
    fractional_kelly = max(0.0, full_kelly * kelly_multiplier)
    raw_stake = fractional_kelly * bankroll

    is_capped = False
    is_floored = False

    stake = raw_stake
    if stake > max_stake:
        stake = max_stake
        is_capped = True
    elif stake < min_stake:
        stake = min_stake
        is_floored = True

    stake = round(stake, 2)

    reason = (
        f"Cote Osée à valeur (EV: {ev*100:+.2f}%, cote {odds:.2f}) : "
        f"Micro-Kelly ({kelly_multiplier*100:.0f}%), variance amortie et plafonné à {max_stake:.2f} €."
    )

    return KellyResult(
        full_kelly_fraction=round(full_kelly, 4),
        fractional_kelly=round(fractional_kelly, 4),
        raw_stake_eur=round(raw_stake, 2),
        final_stake_eur=stake,
        is_capped=is_capped,
        is_floored=is_floored,
        is_rejected=False,
        reason=reason,
    )


def calculate_fallback_stake(
    fallback_amount: float = 1.00,
    max_fallback: float = 2.00,
    reason_prefix: str = "Choix de secours",
) -> KellyResult:
    """Calculates symbolic minimal stake for fallback recommendations (capped at 1.00 € to 2.00 € max).

    Used when no selection meets strict value betting criteria (EV > 0) to avoid capital exposure.
    """
    stake = min(max_fallback, max(1.00, fallback_amount))
    stake = round(stake, 2)
    reason = (
        f"Mise symbolique de secours ({stake:.2f} €) : {reason_prefix}. "
        "Risque et exposition limités au strict minimum pour préserver le capital."
    )
    return KellyResult(
        full_kelly_fraction=0.0,
        fractional_kelly=0.0,
        raw_stake_eur=stake,
        final_stake_eur=stake,
        is_capped=True,
        is_floored=True,
        is_rejected=False,
        reason=reason,
    )

