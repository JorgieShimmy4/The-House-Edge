import math

import pytest

from betting import (american_to_decimal, analyse_bet, analyse_parlay,
                     decimal_to_american, hold, implied_probability,
                     kelly_stake, pickem_table, remove_vig,
                     interval_coverage, roi_confidence_interval,
                     simulate_bankroll, z_score)


class TestOddsConversion:
    def test_underdog_american_to_decimal(self):
        assert american_to_decimal(150) == pytest.approx(2.5)

    def test_favourite_american_to_decimal(self):
        assert american_to_decimal(-110) == pytest.approx(1.909091, abs=1e-6)

    def test_even_money_is_two(self):
        assert american_to_decimal(100) == pytest.approx(2.0)
        assert american_to_decimal(-100) == pytest.approx(2.0)

    def test_roundtrip(self):
        for a in (-350, -110, -101, 100, 175, 900):
            assert decimal_to_american(american_to_decimal(a)) == pytest.approx(a)

    def test_zero_rejected(self):
        with pytest.raises(ValueError):
            american_to_decimal(0)

    def test_implied_probability_of_minus_110(self):
        # the number every bettor should know: 52.38%
        p = implied_probability(american_to_decimal(-110))
        assert p == pytest.approx(0.523810, abs=1e-6)


class TestVig:
    def test_standard_two_way_hold(self):
        both = [american_to_decimal(-110)] * 2
        assert hold(both) == pytest.approx(0.04545, abs=1e-5)

    def test_devig_symmetric_market_is_fifty_fifty(self):
        both = [american_to_decimal(-110)] * 2
        assert remove_vig(both) == pytest.approx([0.5, 0.5])

    def test_devigged_probabilities_sum_to_one(self):
        legs = [american_to_decimal(x) for x in (-200, 165)]
        assert sum(remove_vig(legs)) == pytest.approx(1.0)

    def test_fair_market_has_no_hold(self):
        assert hold([2.0, 2.0]) == pytest.approx(0.0)


class TestSingleBet:
    def test_fair_coin_at_even_money_is_zero_ev(self):
        r = analyse_bet(0.5, decimal=2.0)
        assert r.ev == pytest.approx(0.0)
        assert r.kelly_fraction == pytest.approx(0.0)

    def test_coin_flip_at_minus_110_loses_the_vig(self):
        r = analyse_bet(0.5, american=-110)
        assert r.ev == pytest.approx(-0.045455, abs=1e-6)
        assert not r.is_positive_ev

    def test_edge_is_probability_over_breakeven(self):
        r = analyse_bet(0.55, american=-110)
        assert r.breakeven_probability == pytest.approx(0.523810, abs=1e-6)
        assert r.edge == pytest.approx(0.026190, abs=1e-6)
        assert r.is_positive_ev

    def test_variance_matches_manual_calculation(self):
        p, d = 0.55, 2.0
        r = analyse_bet(p, decimal=d)
        b = d - 1.0
        expected = p * b * b + (1 - p) - (p * b - (1 - p)) ** 2
        assert r.variance == pytest.approx(expected)

    def test_certain_win_has_no_variance(self):
        r = analyse_bet(1.0, decimal=2.0)
        assert r.variance == pytest.approx(0.0)
        assert r.std_dev == pytest.approx(0.0)

    def test_kelly_on_a_known_case(self):
        # p=0.6 at even money -> risk 20% of bankroll at full Kelly
        r = analyse_bet(0.6, decimal=2.0)
        assert r.kelly_fraction == pytest.approx(0.2)

    def test_quarter_kelly_is_default(self):
        r = analyse_bet(0.6, decimal=2.0)
        assert kelly_stake(r, bankroll=1000.0) == pytest.approx(50.0)

    def test_no_stake_without_edge(self):
        r = analyse_bet(0.5, american=-110)
        assert kelly_stake(r, bankroll=1000.0) == 0.0

    def test_requires_exactly_one_odds_format(self):
        with pytest.raises(ValueError):
            analyse_bet(0.5)
        with pytest.raises(ValueError):
            analyse_bet(0.5, decimal=2.0, american=100)

    def test_probability_bounds_enforced(self):
        with pytest.raises(ValueError):
            analyse_bet(1.5, decimal=2.0)


class TestParlay:
    def test_two_leg_pickem_at_three_times(self):
        """The worked example: two coin flips, 3x payout on a $50 entry."""
        r = analyse_parlay([0.5, 0.5], 3.0)
        assert r.hit_probability == pytest.approx(0.25)
        assert r.fair_multiplier == pytest.approx(4.0)
        assert r.ev == pytest.approx(-0.25)
        assert r.hold == pytest.approx(0.25)
        # $50 entry: expected return $37.50, so -$12.50
        assert 50.0 * r.ev == pytest.approx(-12.5)

    def test_fair_payout_is_zero_ev(self):
        r = analyse_parlay([0.5, 0.5], 4.0)
        assert r.ev == pytest.approx(0.0)
        assert r.hold == pytest.approx(0.0)

    def test_hold_worsens_with_more_legs(self):
        table = pickem_table({2: 3.0, 3: 5.0, 4: 10.0, 6: 25.0})
        holds = [row.hold for row in table]
        assert holds[0] < holds[1]
        assert holds[-1] > 0.6
        assert all(row.ev < 0 for row in table)

    def test_single_leg_reduces_to_straight_bet(self):
        r = analyse_parlay([0.5], 2.0)
        assert r.ev == pytest.approx(0.0)

    def test_empty_parlay_rejected(self):
        with pytest.raises(ValueError):
            analyse_parlay([], 3.0)


class TestSimulation:
    def test_negative_ev_grinds_the_bankroll_down(self):
        r = simulate_bankroll(1000.0, 0.5, american_to_decimal(-110),
                              stake=50.0, n_bets=200, n_paths=2000, seed=7)
        assert r.median_final < 1000.0
        assert r.profitable_rate < 0.5

    def test_positive_ev_grows_it(self):
        r = simulate_bankroll(1000.0, 0.58, american_to_decimal(-110),
                              stake=20.0, n_bets=500, n_paths=2000, seed=7)
        assert r.median_final > 1000.0

    def test_oversized_stake_produces_ruin(self):
        r = simulate_bankroll(200.0, 0.5, 2.0, stake=100.0,
                              n_bets=100, n_paths=2000, seed=7)
        assert r.ruin_rate > 0.5

    def test_reproducible_under_seed(self):
        kw = dict(probability=0.5, decimal_odds=2.0, stake=10.0,
                  n_bets=50, n_paths=500, seed=42)
        a = simulate_bankroll(1000.0, **kw)
        b = simulate_bankroll(1000.0, **kw)
        assert a.median_final == b.median_final

    def test_percentiles_are_ordered(self):
        r = simulate_bankroll(1000.0, 0.52, 2.0, stake=25.0,
                              n_bets=300, n_paths=2000, seed=7)
        assert r.percentile_5 < r.median_final < r.percentile_95


class TestConfidenceInterval:
    def test_small_sample_cannot_distinguish_winner_from_loser(self):
        lo, hi = roi_confidence_interval(0.04, bet_std_dev=1.0, n_bets=200)
        assert lo < 0.0 < hi

    def test_interval_narrows_with_sample_size(self):
        small = roi_confidence_interval(0.04, 1.0, 200)
        large = roi_confidence_interval(0.04, 1.0, 5000)
        assert (large[1] - large[0]) < (small[1] - small[0])

    def test_scales_as_inverse_root_n(self):
        a = roi_confidence_interval(0.0, 1.0, 100)
        b = roi_confidence_interval(0.0, 1.0, 400)
        assert (a[1] - a[0]) / (b[1] - b[0]) == pytest.approx(2.0)

    @pytest.mark.parametrize("bad", [0.0, 1.0, 1.5, -0.95])
    def test_impossible_confidence_rejected(self, bad):
        with pytest.raises(ValueError):
            roi_confidence_interval(0.04, 1.0, 200, confidence=bad)

    def test_any_level_between_zero_and_one_works(self):
        lo, hi = roi_confidence_interval(0.0, 1.0, 100, confidence=0.80)
        assert hi == pytest.approx(1.2816 / 10, abs=1e-4)


class TestZScore:
    @pytest.mark.parametrize("level, z", [(0.80, 1.2816), (0.90, 1.6449),
                                          (0.95, 1.9600), (0.99, 2.5758),
                                          (0.999, 3.2905)])
    def test_textbook_values(self, level, z):
        assert z_score(level) == pytest.approx(z, abs=1e-4)

    def test_more_confidence_means_wider(self):
        levels = [0.80, 0.90, 0.95, 0.98, 0.99, 0.999]
        zs = [z_score(c) for c in levels]
        assert zs == sorted(zs)


class TestIntervalCoverage:
    """The definition of a confidence level, checked by brute force."""

    @pytest.mark.parametrize("level", [0.80, 0.90, 0.95, 0.99])
    def test_coverage_matches_the_label(self, level):
        r = interval_coverage(0.5, 1.909, n_bets=400, confidence=level,
                              n_bettors=4000, seed=11)
        assert r.coverage == pytest.approx(level, abs=0.02)

    def test_true_roi_at_minus_110_coin_flip(self):
        r = interval_coverage(0.5, 1.909, n_bets=50, n_bettors=10, seed=1)
        assert r.true_roi == pytest.approx(-0.0455, abs=1e-3)

    def test_quadrupling_bets_halves_width(self):
        a = interval_coverage(0.5, 1.909, 200, n_bettors=3000, seed=2)
        b = interval_coverage(0.5, 1.909, 800, n_bettors=3000, seed=2)
        ratio = (a.high - a.low).mean() / (b.high - b.low).mean()
        assert ratio == pytest.approx(2.0, abs=0.05)

    def test_same_seed_same_intervals(self):
        a = interval_coverage(0.5, 1.909, 100, seed=5)
        b = interval_coverage(0.5, 1.909, 100, seed=5)
        assert (a.low == b.low).all()

    def test_bad_inputs_rejected(self):
        with pytest.raises(ValueError):
            interval_coverage(1.2, 1.909, 100)
        with pytest.raises(ValueError):
            interval_coverage(0.5, 1.909, 1)
