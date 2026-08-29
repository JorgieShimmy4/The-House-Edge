import pandas as pd
import pytest

from betting.ledger import parse_history, sample_history, summarise


class TestParsing:
    def test_accepts_a_clean_frame(self):
        df = pd.DataFrame({"odds": [-110, 150], "stake": [50, 50],
                           "result": ["win", "loss"]})
        out = parse_history(df)
        assert len(out) == 2
        assert out["decimal"].iloc[1] == pytest.approx(2.5)

    def test_column_names_are_case_insensitive(self):
        df = pd.DataFrame({"Odds": [-110], "STAKE": [50], "Result": ["W"]})
        assert len(parse_history(df)) == 1

    def test_result_synonyms(self):
        df = pd.DataFrame({"odds": [-110] * 6, "stake": [10] * 6,
                           "result": ["win", "WON", "w", "loss", "L", "push"]})
        out = parse_history(df)
        assert list(out["result"]) == ["win"] * 3 + ["loss"] * 2 + ["push"]

    def test_missing_column_names_it(self):
        df = pd.DataFrame({"odds": [-110], "stake": [50]})
        with pytest.raises(ValueError, match="result"):
            parse_history(df)

    def test_non_numeric_stake_rejected(self):
        df = pd.DataFrame({"odds": [-110], "stake": ["fifty"], "result": ["win"]})
        with pytest.raises(ValueError, match="non-numeric"):
            parse_history(df)

    def test_negative_stake_rejected(self):
        df = pd.DataFrame({"odds": [-110], "stake": [-50], "result": ["win"]})
        with pytest.raises(ValueError, match="positive"):
            parse_history(df)

    def test_unknown_result_rejected(self):
        df = pd.DataFrame({"odds": [-110], "stake": [50], "result": ["maybe"]})
        with pytest.raises(ValueError, match="Unrecognised"):
            parse_history(df)


class TestSummary:
    def test_all_wins_at_even_money_doubles_the_stake(self):
        df = pd.DataFrame({"odds": [100] * 10, "stake": [100] * 10,
                           "result": ["win"] * 10})
        s = summarise(parse_history(df))
        assert s.net_profit == pytest.approx(1000.0)
        assert s.roi == pytest.approx(1.0)
        assert s.win_rate == pytest.approx(1.0)

    def test_pushes_excluded_from_grading(self):
        df = pd.DataFrame({"odds": [-110] * 4, "stake": [50] * 4,
                           "result": ["win", "loss", "push", "push"]})
        s = summarise(parse_history(df))
        assert s.n_bets == 4
        assert s.n_graded == 2

    def test_most_zero_edge_records_span_zero(self):
        """sample_history generates bettors with exactly zero edge.

        Their intervals should usually contain zero. Some will not: that is
        the false positive rate, and it is the reason a good-looking record
        proves so little.
        """
        results = [summarise(parse_history(sample_history(n=150, seed=s)))
                   for s in range(40)]
        spanning = sum(r.interval_spans_zero for r in results)
        assert spanning >= 30, "zero-edge bettors should mostly look inconclusive"

    def test_some_zero_edge_records_look_significant(self):
        """The uncomfortable half of the same fact."""
        results = [summarise(parse_history(sample_history(n=150, seed=s)))
                   for s in range(40)]
        false_positives = [r for r in results if not r.interval_spans_zero]
        assert false_positives, "expected at least one spurious result in 40"
        assert any(r.roi > 0 for r in false_positives)

    def test_interval_narrows_with_more_bets(self):
        short = summarise(parse_history(sample_history(n=100, seed=11)))
        long = summarise(parse_history(sample_history(n=2000, seed=11)))
        assert (long.roi_ci_high - long.roi_ci_low) < \
               (short.roi_ci_high - short.roi_ci_low)

    def test_bets_needed_shrinks_as_roi_grows(self):
        modest = pd.DataFrame({"odds": [100] * 60,
                               "stake": [100] * 60,
                               "result": ["win"] * 32 + ["loss"] * 28})
        strong = pd.DataFrame({"odds": [100] * 60,
                               "stake": [100] * 60,
                               "result": ["win"] * 45 + ["loss"] * 15})
        a = summarise(parse_history(modest))
        b = summarise(parse_history(strong))
        assert b.bets_needed < a.bets_needed

    def test_curve_starts_at_zero_and_ends_at_profit(self):
        df = sample_history(n=40, seed=1)
        s = summarise(parse_history(df))
        assert s.bankroll_curve[0] == pytest.approx(0.0)
        assert s.bankroll_curve[-1] == pytest.approx(s.net_profit)

    def test_too_few_bets_rejected(self):
        df = pd.DataFrame({"odds": [-110], "stake": [50], "result": ["win"]})
        with pytest.raises(ValueError, match="at least two"):
            summarise(parse_history(df))
