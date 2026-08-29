"""What a betting habit costs over time.

Expected value per bet is abstract. Annual loss, time to ruin, and the
compounded value of the same money invested are not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Hold figures for common products, as a share of every dollar wagered.
# Sportsbook numbers follow from standard pricing; pick'em figures follow
# from published payout tables and near-coin-flip legs. Verify against
# current offerings before quoting any of them.
PRODUCT_HOLD = {
    "Sportsbook side or total (-110)": 0.0455,
    "Three-leg parlay": 0.125,
    "Pick'em, 2 legs at 3x": 0.25,
    "Pick'em, 3 legs at 5x": 0.375,
    "Pick'em, 4 legs at 10x": 0.375,
    "Pick'em, 6 legs at 25x": 0.609,
}


@dataclass(frozen=True)
class HabitCost:
    weekly_stake: float
    hold: float
    annual_wagered: float
    annual_loss: float
    five_year_loss: float
    ten_year_loss: float
    invested_10y: float
    gap_10y: float


def habit_cost(weekly_stake: float, hold: float,
               annual_return: float = 0.07) -> HabitCost:
    """Expected loss from a steady habit, against investing the same money.

    The investment comparison uses a monthly annuity at annual_return,
    compounded monthly. Seven percent is a conventional long-run figure for
    a broad equity index after inflation; it is an assumption, not a promise.
    """
    if weekly_stake < 0:
        raise ValueError("Weekly stake cannot be negative")
    if not 0.0 <= hold < 1.0:
        raise ValueError("Hold must be between 0 and 1")

    annual_wagered = weekly_stake * 52.0
    annual_loss = annual_wagered * hold

    monthly = weekly_stake * 52.0 / 12.0
    r = annual_return / 12.0
    n = 120
    invested = monthly * (((1.0 + r) ** n - 1.0) / r) if r else monthly * n

    return HabitCost(
        weekly_stake=weekly_stake,
        hold=hold,
        annual_wagered=annual_wagered,
        annual_loss=annual_loss,
        five_year_loss=annual_loss * 5.0,
        ten_year_loss=annual_loss * 10.0,
        invested_10y=invested,
        gap_10y=invested + annual_loss * 10.0,
    )


def survival_curve(bankroll: float, stake: float, hold: float,
                   bets_per_week: int = 5, weeks: int = 104,
                   n_paths: int = 5_000, seed: int | None = 1
                   ) -> tuple[np.ndarray, np.ndarray, float | None]:
    """Fraction of bettors still solvent after each week.

    Each bet is modelled as a two-outcome wager whose expected return is
    -hold, priced near even money. Returns (weeks, survival fraction,
    median week of ruin or None if over half survive).
    """
    if stake <= 0 or bankroll <= 0:
        raise ValueError("Bankroll and stake must be positive")

    rng = np.random.default_rng(seed)
    # Even-money payout, win probability set so that EV per bet is -hold.
    p_win = (1.0 - hold) / 2.0

    rolls = np.full(n_paths, float(bankroll))
    alive = np.ones(n_paths, dtype=bool)
    survival = np.empty(weeks + 1)
    survival[0] = 1.0

    for w in range(1, weeks + 1):
        for _ in range(bets_per_week):
            can_bet = alive & (rolls >= stake)
            alive &= can_bet
            if not alive.any():
                break
            wins = rng.random(n_paths) < p_win
            rolls = np.where(alive, rolls + np.where(wins, stake, -stake), rolls)
        survival[w] = alive.mean()

    week_axis = np.arange(weeks + 1)
    below_half = np.where(survival <= 0.5)[0]
    median_ruin = int(below_half[0]) if below_half.size else None
    return week_axis, survival, median_ruin


def compare_products(weekly_stake: float) -> list[tuple[str, float, float]]:
    """Annual expected loss for the same weekly stake across products."""
    return [
        (name, h, weekly_stake * 52.0 * h)
        for name, h in sorted(PRODUCT_HOLD.items(), key=lambda kv: kv[1])
    ]
