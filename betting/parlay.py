"""Parlays and DFS pick'em entries.

The pick'em products sold by PrizePicks, Underdog and Sleeper are parlays
with a fixed payout table. Because each leg is priced near a coin flip, the
fair payout for an n-leg entry is close to 2**n. The offered payout is
materially lower, and the gap widens with leg count.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import prod


@dataclass(frozen=True)
class ParlayAnalysis:
    legs: int
    hit_probability: float
    fair_multiplier: float
    offered_multiplier: float
    ev: float
    ev_pct: float
    hold: float

    @property
    def hold_pct(self) -> float:
        return self.hold * 100.0


def analyse_parlay(leg_probabilities: list[float],
                   offered_multiplier: float) -> ParlayAnalysis:
    """Analyse an all-or-nothing parlay.

    offered_multiplier is total return per unit staked, so 3.0 means a $50
    entry returns $150 including the stake.

    Legs are assumed independent. That is wrong whenever legs share a game
    or a player, and the error is not symmetric: correlated legs raise the
    variance and usually raise the true hit probability above the product,
    which is exactly why books restrict same-game combinations.
    """
    if not leg_probabilities:
        raise ValueError("Need at least one leg")
    if any(not 0.0 <= p <= 1.0 for p in leg_probabilities):
        raise ValueError("Probabilities must be between 0 and 1")
    if offered_multiplier <= 0.0:
        raise ValueError("Offered multiplier must be positive")

    hit = prod(leg_probabilities)
    fair = 1.0 / hit if hit > 0.0 else float("inf")

    ev = hit * offered_multiplier - 1.0
    house_hold = 1.0 - offered_multiplier * hit

    return ParlayAnalysis(
        legs=len(leg_probabilities),
        hit_probability=hit,
        fair_multiplier=fair,
        offered_multiplier=offered_multiplier,
        ev=ev,
        ev_pct=ev * 100.0,
        hold=house_hold,
    )


def pickem_table(payouts: dict[int, float],
                 leg_probability: float = 0.5) -> list[ParlayAnalysis]:
    """Build the hold-by-leg-count table from a payout schedule.

    payouts maps leg count to offered multiplier, e.g. {2: 3.0, 3: 5.0}.
    Verify the schedule against the operator before publishing anything:
    payouts vary by state, by promotion, and over time.
    """
    return [
        analyse_parlay([leg_probability] * legs, mult)
        for legs, mult in sorted(payouts.items())
    ]
