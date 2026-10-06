"""Kelly Criterion and bankroll sizing module (Fractional Kelly 50%)."""

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
    reason: str


def calculate_kelly_stake(
    true_prob: float,
    odds: float,
    bankroll: float = 500.0,
    kelly_multiplier: float = 0.50,  # Demi-Kelly (50%)
    min_stake: float = 1.0,          # Plancher de 1 €
    max_stake: float = 20.0,         # Plafond strict de 20 €
) -> KellyResult:
    """Calculates the recommended stake using the Fractional Kelly Criterion.

    Formula:
        b = odds - 1.0 (gain net par euro misé)
        f* = (p * b - (1 - p)) / b = ((p * odds) - 1.0) / (odds - 1.0) = EV / (odds - 1.0)
        f_fractional = kelly_multiplier * f*
        raw_stake = f_fractional * bankroll

    Constraints:
        - If EV <= 0: Stake is strictly 0.0 €
        - If EV > 0:
            * Floor of 1.0 € applied
            * Cap of 20.0 € applied
    """
    if odds <= 1.0 or true_prob <= 0.0 or bankroll <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            reason="Invalid input parameters or non-positive odds/probability",
        )

    b = odds - 1.0
    ev = (true_prob * odds) - 1.0

    # Rule: If EV <= 0, recommended stake is strictly 0 €
    if ev <= 0.0:
        return KellyResult(
            full_kelly_fraction=0.0,
            fractional_kelly=0.0,
            raw_stake_eur=0.0,
            final_stake_eur=0.0,
            is_capped=False,
            is_floored=False,
            reason="EV non positive (EV <= 0). Aucun avantage mathématique.",
        )

    # Full Kelly fraction
    full_kelly = ev / b

    # Apply 50% Fractional Kelly
    fractional_kelly = max(0.0, full_kelly * kelly_multiplier)
    raw_stake = fractional_kelly * bankroll

    # Apply floor and cap for positive EV
    is_capped = False
    is_floored = False

    stake = raw_stake
    if stake < min_stake:
        stake = min_stake
        is_floored = True

    if stake > max_stake:
        stake = max_stake
        is_capped = True

    stake = round(stake, 2)

    reason = (
        f"Pari à valeur (EV: {ev*100:.2f}%). Demi-Kelly appliqué ({kelly_multiplier*100:.0f}%). "
    )
    if is_capped:
        reason += f"Plafond strict de {max_stake:.2f} € atteint."
    elif is_floored:
        reason += f"Plancher de {min_stake:.2f} € appliqué."
    else:
        reason += f"Mise optimale: {stake:.2f} €."

    return KellyResult(
        full_kelly_fraction=round(full_kelly, 4),
        fractional_kelly=round(fractional_kelly, 4),
        raw_stake_eur=round(raw_stake, 2),
        final_stake_eur=stake,
        is_capped=is_capped,
        is_floored=is_floored,
        reason=reason,
    )
