"""Odds conversion and vig removal."""

from __future__ import annotations


def american_to_decimal(american: float) -> float:
    """Convert American odds to decimal (total return per unit staked)."""
    if american == 0:
        raise ValueError("American odds cannot be zero")
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def decimal_to_american(decimal: float) -> float:
    """Convert decimal odds to American."""
    if decimal <= 1.0:
        raise ValueError("Decimal odds must exceed 1.0")
    if decimal >= 2.0:
        return (decimal - 1.0) * 100.0
    return -100.0 / (decimal - 1.0)


def implied_probability(decimal: float) -> float:
    """Break-even win rate at these odds. Includes the vig."""
    if decimal <= 1.0:
        raise ValueError("Decimal odds must exceed 1.0")
    return 1.0 / decimal


def remove_vig(decimals: list[float]) -> list[float]:
    """Strip the bookmaker margin from a set of mutually exclusive outcomes.

    Uses multiplicative normalisation: divide each implied probability by
    their sum. This assumes the margin is spread proportionally across
    outcomes, which is close enough for two-way markets and is what most
    public de-vig tools do. It understates the favourite's true probability
    on lopsided markets, where a power or Shin method fits better.
    """
    if not decimals:
        raise ValueError("Need at least one outcome")
    raw = [implied_probability(d) for d in decimals]
    total = sum(raw)
    return [p / total for p in raw]


def hold(decimals: list[float]) -> float:
    """Bookmaker margin as a fraction of total handle."""
    overround = sum(implied_probability(d) for d in decimals)
    return (overround - 1.0) / overround
