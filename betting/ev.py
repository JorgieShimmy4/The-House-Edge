"""Expected value, stake sizing, and dispersion for a single wager."""

from __future__ import annotations

from dataclasses import dataclass

from .odds import american_to_decimal, implied_probability


@dataclass(frozen=True)
class BetAnalysis:
    """Everything worth knowing about one bet, per unit staked."""

    probability: float
    decimal_odds: float
    ev: float
    ev_pct: float
    breakeven_probability: float
    edge: float
    variance: float
    std_dev: float
    kelly_fraction: float

    @property
    def is_positive_ev(self) -> bool:
        return self.ev > 0


def analyse_bet(probability: float, *, decimal: float | None = None,
                american: float | None = None) -> BetAnalysis:
    """Analyse a single bet. Supply odds as either decimal or American.

    All returns are expressed per unit staked, so an ev of -0.045 means
    you lose 4.5 cents per dollar risked, on average, over many repetitions.
    """
    if (decimal is None) == (american is None):
        raise ValueError("Supply exactly one of decimal or american")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("Probability must be between 0 and 1")

    d = decimal if decimal is not None else american_to_decimal(american)
    if d <= 1.0:
        raise ValueError("Decimal odds must exceed 1.0")

    p = probability
    q = 1.0 - p
    b = d - 1.0                       # net profit per unit on a win

    ev = p * b - q                    # equivalently p * d - 1
    breakeven = implied_probability(d)

    # Two-outcome payoff: +b with probability p, -1 with probability q.
    # Var = E[X^2] - E[X]^2
    variance = p * b * b + q - ev * ev

    kelly = (p * b - q) / b           # negative means no bet

    return BetAnalysis(
        probability=p,
        decimal_odds=d,
        ev=ev,
        ev_pct=ev * 100.0,
        breakeven_probability=breakeven,
        edge=p - breakeven,
        variance=variance,
        std_dev=variance ** 0.5,
        kelly_fraction=kelly,
    )


def kelly_stake(analysis: BetAnalysis, bankroll: float,
                multiplier: float = 0.25) -> float:
    """Recommended stake in currency units.

    Defaults to quarter Kelly. Full Kelly is optimal only if your probability
    estimate is exactly right; since it never is, betting the full fraction
    routinely overstakes. Returns 0.0 when there is no edge.
    """
    if analysis.kelly_fraction <= 0.0:
        return 0.0
    return bankroll * analysis.kelly_fraction * multiplier
