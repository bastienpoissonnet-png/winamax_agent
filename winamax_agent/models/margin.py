"""Mathematical functions to calculate and remove bookmaker margin (vig / overround).

In sports betting, bookmaker odds include a built-in house margin (vig):
    Overround = sum(1 / Odds_i) - 1.0

To evaluate the true market consensus and compare it to an analytical model,
we remove this margin to retrieve the 'Fair Implied Probability'.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class MarginAnalysis:
    """Detailed margin analysis of a betting market."""
    raw_odds: Dict[str, float]
    raw_implied_probs: Dict[str, float]
    overround_pct: float
    margin_pct: float
    fair_probs_multiplicative: Dict[str, float]
    fair_probs_power: Dict[str, float]


def calculate_overround(odds: List[float]) -> float:
    """Calculates the bookmaker overround (sum(1 / odds) - 1.0).

    Example:
        odds = [2.00, 3.40, 3.80]
        1/2.0 + 1/3.4 + 1/3.8 = 0.50 + 0.2941 + 0.2632 = 1.0573
        Overround = +5.73%
    """
    if not odds or any(o <= 1.0 for o in odds):
        raise ValueError("All odds must be strictly greater than 1.0")
    total_implied = sum(1.0 / o for o in odds)
    return total_implied - 1.0


def remove_margin_multiplicative(odds: Dict[str, float]) -> Dict[str, float]:
    """Removes bookmaker margin proportionally (multiplicative normalization).

    p_i = (1 / O_i) / sum(1 / O_k)
    This guarantees sum(p_i) == 1.0.
    """
    if not odds:
        return {}
    raw_probs = {k: 1.0 / v for k, v in odds.items()}
    total = sum(raw_probs.values())
    if total <= 0:
        raise ValueError("Invalid odds summation")
    return {k: p / total for k, p in raw_probs.items()}


def remove_margin_power(odds: Dict[str, float], tol: float = 1e-6) -> Dict[str, float]:
    """Removes margin using the Power (logarithmic) method.

    Solves for exponent tau such that sum((1 / O_i)^tau) == 1.0.
    This method specifically corrects for the classic 'Favorite-Longshot Bias',
    where bookmakers load higher percentage margins on underdogs than on favorites.
    """
    if not odds:
        return {}
    raw_probs = [1.0 / v for v in odds.values()]
    n = len(raw_probs)
    if n <= 1:
        return {k: 1.0 for k in odds.keys()}

    total = sum(raw_probs)
    if abs(total - 1.0) < tol:
        return {k: 1.0 / v for k, v in odds.items()}

    # Bisection search for tau
    low, high = 1.0, 3.0 if total > 1.0 else 0.1
    if total < 1.0:
        low, high = 0.1, 1.0

    for _ in range(100):
        mid = (low + high) / 2.0
        val = sum(p**mid for p in raw_probs)
        if abs(val - 1.0) < tol:
            break
        if val > 1.0:
            low = mid
        else:
            high = mid

    tau = mid
    keys = list(odds.keys())
    fair_probs = {k: (1.0 / odds[k]) ** tau for k in keys}
    # Final tiny normalization just in case
    sum_fair = sum(fair_probs.values())
    return {k: v / sum_fair for k, v in fair_probs.items()}


def analyze_market_margin(odds: Dict[str, float]) -> MarginAnalysis:
    """Comprehensive analysis of bookmaker margin for a set of odds."""
    odds_values = list(odds.values())
    raw_probs = {k: 1.0 / v for k, v in odds.items()}
    overround = calculate_overround(odds_values)
    margin_pct = overround * 100.0

    fair_mult = remove_margin_multiplicative(odds)
    fair_power = remove_margin_power(odds)

    return MarginAnalysis(
        raw_odds=odds,
        raw_implied_probs=raw_probs,
        overround_pct=overround,
        margin_pct=margin_pct,
        fair_probs_multiplicative=fair_mult,
        fair_probs_power=fair_power,
    )
