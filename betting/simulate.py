"""Monte Carlo over a sequence of bets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SimulationResult:
    paths: int
    bets_per_path: int
    final_bankrolls: np.ndarray
    ruin_rate: float
    median_final: float
    mean_final: float
    percentile_5: float
    percentile_95: float
    profitable_rate: float


def simulate_bankroll(starting_bankroll: float, probability: float,
                      decimal_odds: float, stake: float, n_bets: int,
                      n_paths: int = 10_000, ruin_threshold: float = 0.0,
                      seed: int | None = None) -> SimulationResult:
    """Simulate flat-staking the same bet repeatedly.

    Stops a path once the bankroll can no longer cover the stake, so ruin
    is absorbing rather than something a path recovers from by going
    negative. Flat staking is assumed; Kelly staking would compound and
    needs a different loop.
    """
    if stake <= 0.0:
        raise ValueError("Stake must be positive")
    if n_bets <= 0 or n_paths <= 0:
        raise ValueError("Need at least one bet and one path")

    rng = np.random.default_rng(seed)
    b = decimal_odds - 1.0

    bankrolls = np.full(n_paths, float(starting_bankroll))
    alive = np.ones(n_paths, dtype=bool)
    ever_ruined = np.zeros(n_paths, dtype=bool)

    for _ in range(n_bets):
        alive &= bankrolls >= stake
        if not alive.any():
            break
        wins = rng.random(n_paths) < probability
        delta = np.where(wins, stake * b, -stake)
        bankrolls = np.where(alive, bankrolls + delta, bankrolls)
        ever_ruined |= bankrolls <= ruin_threshold

    return SimulationResult(
        paths=n_paths,
        bets_per_path=n_bets,
        final_bankrolls=bankrolls,
        ruin_rate=float(ever_ruined.mean()),
        median_final=float(np.median(bankrolls)),
        mean_final=float(bankrolls.mean()),
        percentile_5=float(np.percentile(bankrolls, 5)),
        percentile_95=float(np.percentile(bankrolls, 95)),
        profitable_rate=float((bankrolls > starting_bankroll).mean()),
    )


def roi_confidence_interval(observed_roi: float, bet_std_dev: float,
                            n_bets: int, confidence: float = 0.95
                            ) -> tuple[float, float]:
    """Confidence interval around an observed ROI.

    This is the number most bettors have never seen. With a few hundred
    bets the interval is wide enough that a winning record and a losing
    one are not distinguishable, which is the honest answer to "am I good
    at this".
    """
    if n_bets <= 1:
        raise ValueError("Need more than one bet")
    z = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}.get(confidence)
    if z is None:
        raise ValueError("Supported confidence levels: 0.90, 0.95, 0.99")
    margin = z * bet_std_dev / (n_bets ** 0.5)
    return observed_roi - margin, observed_roi + margin
