# The House Edge

Sports betting apps keep a fixed share of everything wagered through them.
This works out how much, over how long, and whether anyone's winning record
actually demonstrates skill.

No picks. No affiliate links. No relationship with any operator. Nothing
stored.

## Run it

    pip install -r requirements.txt
    streamlit run app.py

Library on its own:

    python demo.py
    python -m pytest tests/

No API keys, no accounts, no network calls.

## The numbers

Someone wagering $50 a week on three-leg pick'em entries:

| | |
| --- | --- |
| Wagered per year | $2,600 |
| Expected loss, year one | $975 |
| Expected loss over ten years | $9,750 |
| Same money in an index fund | $37,502 |
| **Difference between the two paths** | **$47,252** |

With a $1,000 bankroll and five bets a week at that product, half of all
bettors are broke within **eleven weeks**. None of them is unlucky. They are
all playing an average game against a 37.5% house edge.

## What each product keeps

| Product | Operator keeps | Versus a −110 line |
| --- | --- | --- |
| Sportsbook side or total (−110) | 4.6% | 1x |
| Three-leg parlay | 12.5% | 3x |
| Pick'em, 2 legs at 3x | 25.0% | 5x |
| Pick'em, 3 legs at 5x | 37.5% | 8x |
| Pick'em, 6 legs at 25x | 60.9% | 13x |

A state lottery keeps roughly 50 cents on the dollar and is widely
understood to be a bad deal. A six-leg pick'em entry keeps more than that.

Payout schedules vary by operator, state and promotion. Verify current
tables before relying on any figure.

## Why winning records prove nothing

Simulate 200 bettors with exactly zero edge and give each 150 bets. Around
8% finish with a confidence interval that excludes zero. The luckiest posts
a **+25.7% ROI**. None of them has any skill at all.

Every screenshot posted by a tout is drawn from a pool like that, with the
failures invisible. The app makes this concrete: upload a record and it
shows you the distribution of results produced by pure noise over the same
number of bets.

## Library

| module | contents |
| --- | --- |
| `odds` | American/decimal conversion, implied probability, margin removal |
| `ev` | expected value, edge, variance for a single wager |
| `parlay` | parlays and pick'em entries, hold by leg count |
| `cost` | annual and lifetime cost of a habit, survival curves |
| `simulate` | Monte Carlo bankroll paths, ROI confidence intervals |
| `ledger` | parsing and analysis of an uploaded bet history |

67 tests. Several encode facts rather than behaviour: that −110 implies
52.38%, that a confidence interval halves when the sample quadruples, that
a six-leg pick'em keeps more than a lottery.

## Assumptions

**Margin removal is multiplicative** - implied probabilities divided by
their sum. Standard, slightly off on lopsided lines where a power or Shin
method fits better.

**Parlay legs are treated as independent.** Legs sharing a game or player
are not, and correlation moves both variance and the true hit rate.

**Survival curves assume flat staking and no reloading.** Bettors who
deposit again last longer and lose more, so this is the optimistic version.

**The investment comparison assumes 7% annually**, compounded monthly. A
convention for a broad equity index, not a promise, and returns are not
smooth.

## Responsible use

Informational and educational only. Not betting advice. If gambling is
causing harm, the National Problem Gambling Helpline is **1-800-522-4700** -
free, confidential, 24 hours. Text or chat at 1800gamblerchat.org.
