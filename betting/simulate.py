"""Monte Carlo over a sequence of bets."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

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
    margin = z_score(confidence) * bet_std_dev / (n_bets ** 0.5)
    return observed_roi - margin, observed_roi + margin


def z_score(confidence: float) -> float:
    """Two-sided critical value: 0.95 -> 1.960, 0.99 -> 2.576."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("Confidence must be between 0 and 1")
    return NormalDist().inv_cdf(0.5 + confidence / 2.0)


@dataclass(frozen=True)
class CoverageResult:
    confidence: float
    n_bets: int
    true_roi: float
    observed_roi: np.ndarray
    low: np.ndarray
    high: np.ndarray
    covers: np.ndarray
    excludes_zero: np.ndarray

    @property
    def coverage(self) -> float:
        return float(self.covers.mean())


def interval_coverage(probability: float, decimal_odds: float, n_bets: int,
                      confidence: float = 0.95, n_bettors: int = 100,
                      seed: int | None = None) -> CoverageResult:
    """Give many bettors the same true edge and build each one's interval.

    Every bettor plays n_bets at the same price with the same true win
    probability, so they share one true ROI. Each computes a normal
    interval from their own record using their own sample standard
    deviation, exactly as they would in real life. The share of intervals
    that contain the true ROI should land near the confidence level.
    """
    if n_bets <= 1 or n_bettors <= 0:
        raise ValueError("Need more than one bet and at least one bettor")
    if not 0.0 < probability < 1.0:
        raise ValueError("Probability must be between 0 and 1")
    z = z_score(confidence)
    b = decimal_odds - 1.0
    true_roi = probability * b - (1.0 - probability)

    rng = np.random.default_rng(seed)
    wins = rng.random((n_bettors, n_bets)) < probability
    returns = np.where(wins, b, -1.0)
    roi = returns.mean(axis=1)
    margin = z * returns.std(axis=1, ddof=1) / np.sqrt(n_bets)
    low, high = roi - margin, roi + margin

    return CoverageResult(
        confidence=confidence, n_bets=n_bets, true_roi=true_roi,
        observed_roi=roi, low=low, high=high,
        covers=(low <= true_roi) & (true_roi <= high),
        excludes_zero=(low > 0) | (high < 0),
    )
