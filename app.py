"""The House Edge — what betting apps actually cost you.

Run: streamlit run app.py
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from betting import (american_to_decimal, analyse_bet, analyse_parlay, hold,
                     pickem_table, remove_vig, simulate_bankroll)
from betting.cost import (PRODUCT_HOLD, compare_products, habit_cost,
                          invested_value, survival_curve)
from betting.ledger import parse_history, sample_history, summarise

st.set_page_config(page_title="The House Edge", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
  .block-container { max-width: 1060px; padding-top: 2.2rem; }
  h1 { font-weight: 600; letter-spacing: -0.02em; }
  h2, h3 { font-weight: 600; letter-spacing: -0.01em; }
  [data-testid="stMetricValue"] { font-size: 1.55rem; }
  .stTabs [data-baseweb="tab"] { padding: 0.5rem 1rem; }
  footer, #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def pct(x: float, places: int = 1) -> str:
    return f"{x:.{places}%}"


def money(x: float) -> str:
    return f"${x:,.0f}"


def md(text: str) -> str:
    """Escape dollar signs for any Streamlit call that renders markdown.

    Streamlit reads text between two $ signs as LaTeX, so a sentence with
    two dollar amounts in it turns into one long italic equation.
    """
    return text.replace("$", r"\$")


AXIS = alt.Axis(labelFontSize=11, titleFontSize=12, grid=True, gridOpacity=0.25)
NAVY, RED, GREEN = "#1f3b57", "#c0392b", "#27ae60"


def line(df, x, y, x_title, y_title, colour=NAVY, money_axis=True):
    """Numeric x axis, sorted properly, no categorical string index."""
    return alt.Chart(df).mark_line(strokeWidth=2.5, color=colour).encode(
        x=alt.X(f"{x}:Q", title=x_title, axis=AXIS),
        y=alt.Y(f"{y}:Q", title=y_title,
                axis=alt.Axis(format="$,.0f" if money_axis else ",.0f",
                              labelFontSize=11, titleFontSize=12,
                              grid=True, gridOpacity=0.25)),
        tooltip=[alt.Tooltip(f"{x}:Q", title=x_title),
                 alt.Tooltip(f"{y}:Q", title=y_title,
                             format="$,.0f" if money_axis else ",.2f")],
    ).properties(height=320)


def bars(df, x, y, x_title, y_title, order=None, colour=NAVY, fmt=",.1f"):
    enc_x = alt.X(f"{x}:N", title=x_title, axis=alt.Axis(labelAngle=0,
                  labelFontSize=11, titleFontSize=12), sort=order)
    return alt.Chart(df).mark_bar(color=colour, cornerRadiusEnd=3).encode(
        x=enc_x,
        y=alt.Y(f"{y}:Q", title=y_title, axis=AXIS),
        tooltip=[alt.Tooltip(f"{x}:N", title=x_title),
                 alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)],
    ).properties(height=300)


st.title("The House Edge")
st.write(
    "Every sportsbook and pick'em app keeps a fixed share of what you wager. "
    "This works out how much, over how long, and whether anyone's record "
    "proves they beat it. No affiliate links, no picks, nothing stored."
)

tabs = st.tabs(["What it costs you", "The products", "How long you last",
                "Check a line", "Your record", "Method"])

# ------------------------------------------------------- what it costs you
with tabs[0]:
    st.subheader("The bill, over time")

    c1, c2 = st.columns([1, 1])
    weekly = c1.slider("What you wager in a typical week", 10, 500, 50, 10,
                       format="$%d")
    product = c2.selectbox("What you bet on", list(PRODUCT_HOLD),
                           index=3)
    h = PRODUCT_HOLD[product]

    cost = habit_cost(weekly, h)

    a, b, c, d = st.columns(4)
    a.metric("Wagered per year", money(cost.annual_wagered))
    b.metric("Expected loss, year one", money(cost.annual_loss))
    c.metric("Over five years", money(cost.five_year_loss))
    d.metric("Over ten years", money(cost.ten_year_loss))

    st.error(md(
        f"**{money(cost.ten_year_loss)} handed to the house in ten years.** "
        f"Put into a broad index fund instead, that same money would have "
        f"grown to about **{money(cost.invested_10y)}**."
    ))

    years = np.arange(0, 11)
    lost = cost.annual_loss * years
    grown = np.array([invested_value(cost.annual_loss / 12, y) for y in years])
    LOST, GROWN = "Lost to the house", "That money, invested"
    paths = pd.DataFrame({
        "Year": np.tile(years, 2),
        "Amount": np.concatenate([grown, lost]),
        "Path": [GROWN] * 11 + [LOST] * 11,
    })
    band = pd.DataFrame({"Year": years, "low": lost, "high": grown})

    x = alt.X("Year:Q", title="Years from now",
              scale=alt.Scale(domain=[0, 10], nice=False),
              axis=alt.Axis(tickCount=11, labelFontSize=11, titleFontSize=12,
                            grid=False))
    gap = alt.Chart(band).mark_area(color=GREEN, opacity=0.12).encode(
        x=x, y="low:Q", y2="high:Q")
    lines = alt.Chart(paths).mark_line(strokeWidth=3, point=alt.OverlayMarkDef(
        size=28, filled=True)).encode(
        x=x,
        y=alt.Y("Amount:Q", title=None,
                axis=alt.Axis(format="$,.0f", labelFontSize=11,
                              grid=True, gridOpacity=.2, domain=False)),
        color=alt.Color("Path:N", title=None,
                        scale=alt.Scale(domain=[GROWN, LOST],
                                        range=[GREEN, RED]),
                        legend=alt.Legend(orient="top-left", labelFontSize=13,
                                          symbolStrokeWidth=4)),
        tooltip=[alt.Tooltip("Path:N", title=" "), alt.Tooltip("Year:Q"),
                 alt.Tooltip("Amount:Q", format="$,.0f")],
    )
    st.altair_chart((gap + lines).properties(height=340)
                    .configure_view(strokeWidth=0),
                    use_container_width=True)

    st.caption(md(
        f"The shaded gap is the growth you give up on top of the loss itself: "
        f"{money(cost.growth_forgone_10y)} over ten years at this level. Only "
        f"the money lost is compared, because the rest of what you wager "
        f"comes back as winnings. Growth assumes 7% a year, compounded "
        f"monthly, a conventional long-run figure for a broad equity index. "
        f"Losses assume you do exactly as well as the market's prices imply, "
        f"which is the best case, not the typical one."
    ))

# ------------------------------------------------------------- the products
with tabs[1]:
    st.subheader("What each product keeps")
    st.write(
        "Hold is the share of every dollar wagered the operator keeps, on "
        "average, no matter who wins. It is the price of playing."
    )

    rows = compare_products(weekly)
    st.dataframe(
        pd.DataFrame({
            "Product": [n for n, _, _ in rows],
            "Operator keeps": [pct(h) for _, h, _ in rows],
            f"Your loss on ${weekly}/week": [money(l) for _, _, l in rows],
            "Versus a -110 line": [f"{h / 0.0455:.0f}x" for _, h, _ in rows],
        }),
        hide_index=True, use_container_width=True,
    )

    labels = [n.replace("Pick'em, ", "").replace(" side or total (-110)", "")
              for n, _, _ in rows]
    st.altair_chart(
        bars(pd.DataFrame({"Product": labels,
                           "Operator keeps": [h * 100 for _, h, _ in rows]}),
             "Product", "Operator keeps", None, "Share of every dollar (%)",
             order=labels, colour=RED, fmt=".1f"),
        use_container_width=True,
    )

    st.warning(
        "For scale: a state lottery keeps roughly 50 cents on the dollar and "
        "is widely understood to be a bad deal. A six-leg pick'em entry keeps "
        "more than that."
    )

    with st.expander("Work it out yourself"):
        st.write(
            "A pick'em entry is a parlay with a fixed payout. Because each "
            "leg is priced near a coin flip, the fair payout for n legs is "
            "close to 2ⁿ. Compare that to what is offered."
        )
        default = pd.DataFrame({"legs": [2, 3, 4, 5, 6],
                                "payout": [3.0, 5.0, 10.0, 20.0, 25.0]})
        edited = st.data_editor(default, hide_index=True, num_rows="dynamic",
                                use_container_width=True)
        try:
            schedule = {int(r.legs): float(r.payout)
                        for r in edited.dropna().itertuples()}
            table = pickem_table(schedule)
        except (ValueError, AttributeError):
            st.info("Enter at least one leg count and payout.")
        else:
            st.dataframe(pd.DataFrame({
                "Legs": [t.legs for t in table],
                "Chance all hit": [pct(t.hit_probability) for t in table],
                "Fair payout": [f"{t.fair_multiplier:.0f}x" for t in table],
                "Offered": [f"{t.offered_multiplier:.0f}x" for t in table],
                "Operator keeps": [pct(t.hold) for t in table],
            }), hide_index=True, use_container_width=True)
        st.caption(
            "Payout schedules vary by operator, state and promotion. Check "
            "the current table before relying on any figure here."
        )

# -------------------------------------------------------- how long you last
with tabs[2]:
    st.subheader("How long the money lasts")
    st.write(
        "Given a starting bankroll and a steady habit, this is the share of "
        "bettors still solvent week by week. Nobody in this simulation is "
        "unlucky. They are all playing an average game."
    )

    c1, c2, c3 = st.columns(3)
    roll = c1.number_input("Starting bankroll", value=1000, step=50,
                           min_value=50)
    per_bet = c2.number_input("Stake per bet", value=50, step=5, min_value=5)
    freq = c3.number_input("Bets per week", 1, 30, 5)

    surv_product = st.selectbox("Product", list(PRODUCT_HOLD), index=3,
                                key="surv_prod")

    if per_bet > roll:
        st.error("Stake is larger than the bankroll.")
    else:
        weeks, surv, median_ruin = survival_curve(
            roll, per_bet, PRODUCT_HOLD[surv_product],
            bets_per_week=int(freq), weeks=104,
        )
        a, b, c = st.columns(3)
        a.metric("Still solvent after 6 months", pct(surv[26]))
        b.metric("After one year", pct(surv[52]))
        c.metric("Half are broke by",
                 f"week {median_ruin}" if median_ruin else "over 2 years")

        curve = pd.DataFrame({"Week": weeks, "Solvent": surv * 100})
        st.altair_chart(
            alt.Chart(curve).mark_area(
                line={"color": NAVY, "strokeWidth": 2.5},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[alt.GradientStop(color="#ffffff", offset=0),
                           alt.GradientStop(color=NAVY, offset=1)],
                    x1=1, x2=1, y1=1, y2=0),
            ).encode(
                x=alt.X("Week:Q", title="Weeks from the first bet",
                        scale=alt.Scale(nice=False, domainMin=0),
                        axis=alt.Axis(labelFontSize=11, titleFontSize=12,
                                      grid=True, gridOpacity=.25)),
                y=alt.Y("Solvent:Q", title="Still solvent (%)",
                        scale=alt.Scale(domain=[0, 100]),
                        axis=alt.Axis(labelFontSize=11, titleFontSize=12,
                                      grid=True, gridOpacity=.25)),
                tooltip=[alt.Tooltip("Week:Q"),
                         alt.Tooltip("Solvent:Q", format=".1f",
                                     title="Still solvent %")],
            ).properties(height=340),
            use_container_width=True,
        )
        if median_ruin:
            st.error(
                f"Half of these bettors have lost the entire bankroll within "
                f"**{median_ruin} weeks**. Not through bad luck. Through "
                f"average luck against a {pct(PRODUCT_HOLD[surv_product])} "
                f"house edge."
            )
        st.caption(
            "5,000 simulated bettors, flat staking, stopping when the "
            "bankroll can no longer cover a bet. Reloading is not modelled, "
            "which makes this the optimistic version."
        )

# ------------------------------------------------------------- check a line
with tabs[3]:
    st.subheader("Check a single line")
    st.write(
        "What a price requires before it returns anything, and how far your "
        "own read would have to be from the market to make it worth taking."
    )

    left, right = st.columns([1, 1.3], gap="large")
    with left:
        american = st.number_input("Odds (American)", value=-110, step=5)
        prob = st.slider("What you think the real chance is", 0.0, 1.0, 0.50,
                         0.005, format="%.3f")
    try:
        r = analyse_bet(prob, american=american)
    except ValueError:
        st.error("Odds cannot be zero.")
        st.stop()

    with right:
        a, b, c = st.columns(3)
        a.metric("Break-even rate", pct(r.breakeven_probability, 2))
        b.metric("Your read", pct(prob, 2))
        c.metric("Expected value", pct(r.ev, 2))

        if r.is_positive_ev:
            st.info(
                f"Positive on paper, but only if {pct(prob, 2)} is correct. "
                f"Market prices are set by people with models, injury feeds "
                f"and money at risk. Being {pct(r.edge, 2)} sharper than that "
                f"consistently is rare enough that most who believe they are "
                f"have simply not played enough hands to find out otherwise."
            )
        else:
            st.warning(md(
                f"Negative. You would have to be right "
                f"{pct(r.breakeven_probability - prob, 2)} more often than you "
                f"think, just to break even. Every ${100:.0f} wagered returns "
                f"${100 * (1 + r.ev):.2f} on average."
            ))

    st.divider()
    st.caption("The margin, made visible")
    v1, v2 = st.columns(2)
    o1 = v1.number_input("Side A", value=-110, step=5, key="va")
    o2 = v2.number_input("Side B", value=-110, step=5, key="vb")
    try:
        book = [american_to_decimal(o1), american_to_decimal(o2)]
        fair = remove_vig(book)
        m1, m2, m3 = st.columns(3)
        m1.metric("Implied chances add to",
                  f"{sum(1 / d for d in book):.1%}")
        m2.metric("True chances, margin removed",
                  f"{fair[0]:.1%} / {fair[1]:.1%}")
        m3.metric("The operator's cut", pct(hold(book), 2))
        st.caption(
            "Both sides cannot be more than certain. The excess above 100% "
            "is the margin, charged whichever way the game goes."
        )
    except ValueError:
        st.error("Both sides need non-zero odds.")

# ------------------------------------------------------------- your record
with tabs[4]:
    st.subheader("Does anyone's record prove anything?")
    st.write(
        "Upload a CSV with columns **odds**, **stake**, **result**. Odds are "
        "American; result is win, loss or push. Parsed in memory, never "
        "stored, gone when you close the tab."
    )

    up = st.file_uploader("Bet history", type="csv")
    use_sample = st.checkbox("Use a sample record instead", value=up is None)

    frame = None
    if up is not None and not use_sample:
        try:
            frame = pd.read_csv(up)
        except Exception:
            st.error("That file could not be read as CSV.")
    elif use_sample:
        frame = sample_history()

    if frame is None:
        st.info("Nothing loaded. Tick the box above to see a worked example.")
    else:
        try:
            history = parse_history(frame)
            summary = summarise(history)
        except ValueError as exc:
            st.error(str(exc))
        else:
            a, b, c, d = st.columns(4)
            a.metric("Graded bets", f"{summary.n_graded:,}")
            b.metric("Net", money(summary.net_profit))
            c.metric("ROI", pct(summary.roi))
            d.metric("Win rate", pct(summary.win_rate))

            lo, hi = summary.roi_ci_low, summary.roi_ci_high
            if summary.interval_spans_zero:
                st.warning(
                    f"The 95% confidence interval on this ROI runs from "
                    f"{pct(lo)} to {pct(hi)}. It contains zero, so this record "
                    f"cannot tell a winning bettor apart from a losing one. "
                    f"Holding this exact ROI, it would take about "
                    f"{summary.bets_needed:,} bets before the interval cleared "
                    f"zero, and ROI does not hold."
                )
            else:
                st.success(
                    f"Interval runs {pct(lo)} to {pct(hi)}, excluding zero. "
                    f"Read the section below before concluding anything from "
                    f"that."
                )

            st.altair_chart(
                line(pd.DataFrame({
                        "Bet": np.arange(len(summary.bankroll_curve)),
                        "Profit": summary.bankroll_curve}),
                     "Bet", "Profit", "Bets placed", "Cumulative profit",
                     colour=GREEN if summary.net_profit > 0 else RED),
                use_container_width=True,
            )

            st.markdown("**What luck alone produces**")
            trials = [summarise(parse_history(sample_history(
                n=min(summary.n_graded, 600), seed=s))) for s in range(150)]
            rois = np.array([t.roi for t in trials])
            spurious = sum(1 for t in trials if not t.interval_spans_zero)
            x, y, z = st.columns(3)
            x.metric("Best record by luck alone", pct(rois.max()))
            y.metric("Looked statistically real",
                     f"{spurious / len(trials):.0%}")
            z.metric("Actual skill involved", "None")
            counts, edges = np.histogram(rois * 100, bins=24)
            centres = (edges[:-1] + edges[1:]) / 2
            width = float(edges[1] - edges[0])
            hist = pd.DataFrame({"ROI": centres, "Bettors": counts})
            st.altair_chart(
                alt.Chart(hist).mark_bar(size=max(6, int(320 / len(centres))),
                                         color=NAVY, opacity=.85).encode(
                    x=alt.X("ROI:Q", title="Realised ROI (%)",
                            axis=alt.Axis(format="+.0f", labelFontSize=11,
                                          titleFontSize=12, grid=False)),
                    y=alt.Y("Bettors:Q", title="Bettors with no edge",
                            axis=alt.Axis(labelFontSize=11, titleFontSize=12,
                                          grid=True, gridOpacity=.25)),
                    tooltip=[alt.Tooltip("ROI:Q", format="+.1f",
                                         title="ROI %"),
                             alt.Tooltip("Bettors:Q")],
                ).properties(height=260),
                use_container_width=True,
            )
            st.caption(
                f"150 simulated bettors with no edge whatsoever, each playing "
                f"{min(summary.n_graded, 600)} bets. The best of them posted "
                f"{pct(rois.max())}. Every screenshot you have seen from a "
                f"tout is drawn from a pool like this one, with the failures "
                f"invisible."
            )

# ------------------------------------------------------------------ method
with tabs[5]:
    st.subheader("Method")
    st.markdown(
        """
Four formulas produce everything here.

**Break-even rate** is the reciprocal of decimal odds. A −110 line needs
52.38% to return anything at all.

**Hold** is the operator's share of every dollar wagered: implied
probabilities sum to more than one, and the excess divided by that sum is
the margin.

**Expected value** per unit staked is `p·(d − 1) − (1 − p)`.

**Confidence interval** on a realised ROI is `±1.96σ/√n`. This is the
formula the whole industry depends on you not knowing.

#### Where this is wrong

Margin removal is multiplicative, dividing implied probabilities by their
sum. Standard, and slightly off on lopsided lines.

Parlay legs are treated as independent. Legs from one game are correlated,
which moves both variance and the true hit rate.

Hold figures for pick'em products follow from published payout tables and
near-coin-flip legs. Schedules change; verify before quoting.

The investment comparison assumes 7% annually. That is a convention, not a
guarantee, and returns are not smooth.

#### What this is not

No picks, no affiliate links, no relationship with any operator, no stored
data, no accounts. Every number can be reproduced from the formulas above
and the code is public.
        """
    )

st.divider()
st.caption(
    "Informational and educational. Not betting advice. If gambling is "
    "causing harm, the National Problem Gambling Helpline is 1-800-522-4700, "
    "free and confidential, 24 hours a day. Text or chat at 1800gamblerchat.org."
)
