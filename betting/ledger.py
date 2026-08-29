"""Analysis of a bettor's own record, from an uploaded history.

Nothing here persists. A file is parsed, summarised, and discarded when the
session ends.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .odds import american_to_decimal, implied_probability

REQUIRED = ("odds", "stake", "result")
RESULT_VALUES = {"win", "won", "w", "loss", "lost", "l", "push", "void"}


@dataclass(frozen=True)
class LedgerSummary:
    n_bets: int
    n_graded: int
    total_staked: float
    net_profit: float
    roi: float
    win_rate: float
    breakeven_rate: float
    roi_ci_low: float
    roi_ci_high: float
    interval_spans_zero: bool
    bets_needed: int
    per_bet_std: float
    bankroll_curve: np.ndarray


def _normalise_result(value: str) -> str:
    v = str(value).strip().lower()
    if v in ("win", "won", "w"):
        return "win"
    if v in ("loss", "lost", "l"):
        return "loss"
    if v in ("push", "void"):
        return "push"
    raise ValueError(f"Unrecognised result: {value!r}")


def parse_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise an uploaded bet history.

    Expects columns: odds (American), stake, result. Anything else is kept
    but ignored. Pushes are dropped from the returned frame after being
    counted, since they carry no information about accuracy.
    """
    cols = {c.strip().lower(): c for c in frame.columns}
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        raise ValueError(
            f"Missing column(s): {', '.join(missing)}. "
            f"Expected {', '.join(REQUIRED)}."
        )

    out = pd.DataFrame({
        "odds": pd.to_numeric(frame[cols["odds"]], errors="coerce"),
        "stake": pd.to_numeric(frame[cols["stake"]], errors="coerce"),
        "result": frame[cols["result"]].map(_normalise_result),
    })

    bad = out["odds"].isna() | out["stake"].isna()
    if bad.any():
        raise ValueError(f"{int(bad.sum())} row(s) have non-numeric odds or stake")
    if (out["stake"] <= 0).any():
        raise ValueError("Stakes must be positive")

    out["decimal"] = out["odds"].map(american_to_decimal)
    out["breakeven"] = out["decimal"].map(implied_probability)
    return out


def summarise(history: pd.DataFrame) -> LedgerSummary:
    """Produce an honest read on whether a record proves anything."""
    n_total = len(history)
    graded = history[history["result"] != "push"].copy()
    n = len(graded)
    if n < 2:
        raise ValueError("Need at least two graded bets")

    won = graded["result"] == "win"
    graded["profit"] = np.where(
        won, graded["stake"] * (graded["decimal"] - 1.0), -graded["stake"]
    )

    staked = float(graded["stake"].sum())
    profit = float(graded["profit"].sum())
    roi = profit / staked

    # Per-unit returns, so the interval is on ROI rather than raw dollars.
    unit_returns = (graded["profit"] / graded["stake"]).to_numpy()
    per_bet_std = float(unit_returns.std(ddof=1))
    margin = 1.96 * per_bet_std / np.sqrt(n)

    # How many bets would be needed for the interval to exclude zero,
    # holding the observed ROI and dispersion fixed.
    if roi != 0.0:
        needed = int(np.ceil((1.96 * per_bet_std / abs(roi)) ** 2))
    else:
        needed = 0

    return LedgerSummary(
        n_bets=n_total,
        n_graded=n,
        total_staked=staked,
        net_profit=profit,
        roi=roi,
        win_rate=float(won.mean()),
        breakeven_rate=float(graded["breakeven"].mean()),
        roi_ci_low=roi - margin,
        roi_ci_high=roi + margin,
        interval_spans_zero=(roi - margin) < 0.0 < (roi + margin),
        bets_needed=needed,
        per_bet_std=per_bet_std,
        bankroll_curve=np.concatenate([[0.0], graded["profit"].cumsum().to_numpy()]),
    )


def sample_history(n: int = 180, seed: int = 3) -> pd.DataFrame:
    """A plausible break-even record, for the demo tab."""
    rng = np.random.default_rng(seed)
    odds = rng.choice([-110, -115, -105, 120, -140], size=n,
                      p=[.45, .2, .15, .1, .1])
    stake = rng.choice([25, 50, 100], size=n, p=[.5, .35, .15])
    probs = np.array([implied_probability(american_to_decimal(o)) for o in odds])
    won = rng.random(n) < probs
    return pd.DataFrame({
        "odds": odds,
        "stake": stake,
        "result": np.where(won, "win", "loss"),
    })
