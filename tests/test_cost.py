import pytest

from betting.cost import (PRODUCT_HOLD, compare_products, habit_cost,
                          invested_value, survival_curve)


class TestHabitCost:
    def test_annual_wagered_is_weekly_times_52(self):
        c = habit_cost(50, 0.375)
        assert c.annual_wagered == pytest.approx(2600.0)

    def test_annual_loss_is_wagered_times_hold(self):
        c = habit_cost(50, 0.375)
        assert c.annual_loss == pytest.approx(975.0)

    def test_multi_year_losses_are_linear(self):
        c = habit_cost(100, 0.25)
        assert c.five_year_loss == pytest.approx(c.annual_loss * 5)
        assert c.ten_year_loss == pytest.approx(c.annual_loss * 10)

    def test_zero_hold_costs_nothing(self):
        """A bettor who loses nothing has nothing to have invested."""
        c = habit_cost(50, 0.0)
        assert c.annual_loss == pytest.approx(0.0)
        assert c.invested_10y == pytest.approx(0.0)
        assert c.growth_forgone_10y == pytest.approx(0.0)

    def test_only_the_loss_is_invested(self):
        """$975 a year lost, invested monthly at 7% for ten years."""
        c = habit_cost(50, 0.375)
        assert c.invested_10y == pytest.approx(14_063.14, abs=0.01)

    def test_invested_loss_beats_the_loss_itself(self):
        c = habit_cost(50, 0.375)
        assert c.invested_10y > c.ten_year_loss
        assert c.growth_forgone_10y == pytest.approx(
            c.invested_10y - c.ten_year_loss)

    def test_invested_value_never_exceeds_whole_handle(self):
        """Guards the old double count: the comparison can't outgrow the handle."""
        c = habit_cost(50, 0.609)
        assert c.invested_10y < invested_value(50 * 52 / 12, 10)

    def test_zero_return_is_plain_sum(self):
        assert invested_value(100, 10, annual_return=0.0) == pytest.approx(12_000)

    def test_worse_product_costs_more(self):
        cheap = habit_cost(50, PRODUCT_HOLD["Sportsbook side or total (-110)"])
        dear = habit_cost(50, PRODUCT_HOLD["Pick'em, 6 legs at 25x"])
        assert dear.annual_loss > cheap.annual_loss * 10

    def test_invalid_hold_rejected(self):
        with pytest.raises(ValueError):
            habit_cost(50, 1.5)

    def test_negative_stake_rejected(self):
        with pytest.raises(ValueError):
            habit_cost(-10, 0.25)


class TestProductComparison:
    def test_sorted_cheapest_first(self):
        rows = compare_products(50)
        holds = [h for _, h, _ in rows]
        assert holds == sorted(holds)

    def test_sportsbook_is_the_cheapest_listed(self):
        assert compare_products(50)[0][0].startswith("Sportsbook")

    def test_six_leg_pickem_exceeds_a_lottery(self):
        # state lotteries keep roughly half
        assert PRODUCT_HOLD["Pick'em, 6 legs at 25x"] > 0.50


class TestSurvival:
    def test_survival_only_decreases(self):
        _, surv, _ = survival_curve(1000, 50, 0.25, weeks=52, n_paths=800)
        assert all(surv[i] >= surv[i + 1] for i in range(len(surv) - 1))

    def test_starts_fully_solvent(self):
        _, surv, _ = survival_curve(1000, 50, 0.25, weeks=10, n_paths=500)
        assert surv[0] == pytest.approx(1.0)

    def test_higher_hold_kills_faster(self):
        _, low, _ = survival_curve(1000, 50, 0.045, weeks=52, n_paths=1500, seed=4)
        _, high, _ = survival_curve(1000, 50, 0.609, weeks=52, n_paths=1500, seed=4)
        assert high[52] < low[52]

    def test_median_ruin_reported_when_most_bust(self):
        _, _, median = survival_curve(500, 100, 0.375, weeks=104, n_paths=1500)
        assert median is not None and median < 30

    def test_tiny_stake_survives_longer(self):
        _, _, fast = survival_curve(1000, 200, 0.375, weeks=104, n_paths=1200)
        _, _, slow = survival_curve(1000, 10, 0.375, weeks=104, n_paths=1200)
        assert fast is not None
        assert slow is None or slow > fast

    def test_zero_stake_rejected(self):
        with pytest.raises(ValueError):
            survival_curve(1000, 0, 0.25)
