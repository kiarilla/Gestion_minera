"""Tests para forecast.py."""

import numpy as np
import pandas as pd
import pytest

from src.forecast import (
    forecast_linear,
    forecast_budget_scaled,
    forecast_polynomial,
    forecast_holt_damped,
    forecast_spline_damped,
    forecast_arima,
    apply_method,
    select_best_method,
    aggregate_forecast,
)


@pytest.fixture
def actual_5m():
    return np.array([100, 120, 110, 130, 140], dtype=float)


@pytest.fixture
def budget_12m():
    return np.array([90, 95, 100, 105, 115, 120, 120, 120, 125, 125, 130, 130],
                    dtype=float)


@pytest.fixture
def actual_3m():
    return np.array([100, 120, 110], dtype=float)


class TestForecastLinear:
    def test_returns_12_elements(self, actual_5m):
        result = forecast_linear(actual_5m)
        assert len(result) == 12

    def test_first_5_match_input(self, actual_5m):
        result = forecast_linear(actual_5m)
        np.testing.assert_array_equal(result[:5], actual_5m)

    def test_future_months_are_constant(self, actual_5m):
        result = forecast_linear(actual_5m)
        future = result[5:]
        assert np.allclose(future, future[0])

    def test_no_negative_values(self, actual_5m):
        result = forecast_linear(actual_5m)
        assert (result >= 0).all()

    def test_works_with_variable_length(self, actual_3m):
        result = forecast_linear(actual_3m)
        assert len(result) == 12
        np.testing.assert_array_equal(result[:3], actual_3m)

    def test_total_gt_zero(self, actual_5m):
        result = forecast_linear(actual_5m)
        assert np.sum(result) > 0


class TestForecastBudgetScaled:
    def test_returns_12_elements(self, actual_5m, budget_12m):
        result = forecast_budget_scaled(actual_5m, budget_12m)
        assert len(result) == 12

    def test_first_5_match_input(self, actual_5m, budget_12m):
        result = forecast_budget_scaled(actual_5m, budget_12m)
        np.testing.assert_array_equal(result[:5], actual_5m)

    def test_no_negative_values(self, actual_5m, budget_12m):
        result = forecast_budget_scaled(actual_5m, budget_12m)
        assert (result >= 0).all()

    def test_damp_factor_zero_uses_budget(self, actual_5m, budget_12m):
        result = forecast_budget_scaled(actual_5m, budget_12m, damp_factor=0.0)
        np.testing.assert_array_equal(result[:5], actual_5m)
        # With damp=0, future months should match budget shape
        assert np.allclose(result[5:] / budget_12m[5:],
                          result[5] / budget_12m[5])

    def test_falls_back_on_zero_budget(self, actual_5m):
        zero_budget = np.zeros(12)
        result = forecast_budget_scaled(actual_5m, zero_budget)
        assert len(result) == 12

    def test_works_with_variable_length(self, actual_3m, budget_12m):
        result = forecast_budget_scaled(actual_3m, budget_12m)
        assert len(result) == 12
        np.testing.assert_array_equal(result[:3], actual_3m)

    def test_with_sanity_limit(self, actual_5m, budget_12m):
        huge = np.array([1e8, 1e8, 1e8, 1e8, 1e8], dtype=float)
        result = forecast_budget_scaled(huge, budget_12m, budget_fy=1000)
        assert result is not None
        assert len(result) == 12


class TestForecastPolynomial:
    def test_returns_12_elements(self, actual_5m):
        result = forecast_polynomial(actual_5m)
        assert len(result) == 12

    def test_first_5_match_input(self, actual_5m):
        result = forecast_polynomial(actual_5m)
        np.testing.assert_array_almost_equal(result[:5], actual_5m)

    def test_no_negative_values(self, actual_5m):
        result = forecast_polynomial(actual_5m)
        assert (result >= 0).all()

    def test_falls_back_with_few_points(self):
        result = forecast_polynomial(np.array([100.0]))
        assert len(result) == 12

    def test_works_with_variable_length(self, actual_3m):
        result = forecast_polynomial(actual_3m)
        assert len(result) == 12
        np.testing.assert_array_almost_equal(result[:3], actual_3m)


class TestForecastHoltDamped:
    def test_returns_12_elements(self, actual_5m):
        result = forecast_holt_damped(actual_5m)
        assert len(result) == 12

    def test_no_negative_values(self, actual_5m):
        result = forecast_holt_damped(actual_5m)
        assert (result >= 0).all()

    def test_falls_back_with_few_points(self):
        result = forecast_holt_damped(np.array([100.0]))
        assert len(result) == 12

    def test_works_with_variable_length(self, actual_3m):
        result = forecast_holt_damped(actual_3m)
        assert len(result) == 12

    def test_total_gt_zero(self, actual_5m):
        result = forecast_holt_damped(actual_5m)
        assert np.sum(result) > 0


class TestForecastSplineDamped:
    def test_returns_12_elements(self, actual_5m):
        result = forecast_spline_damped(actual_5m)
        assert len(result) == 12

    def test_no_negative_values(self, actual_5m):
        result = forecast_spline_damped(actual_5m)
        assert (result >= 0).all()

    def test_falls_back_with_few_points(self):
        result = forecast_spline_damped(np.array([100.0, 120.0]))
        assert len(result) == 12

    def test_works_with_variable_length(self, actual_3m):
        result = forecast_spline_damped(actual_3m)
        assert len(result) == 12


class TestForecastARIMA:
    def test_returns_12_elements(self, actual_5m):
        result = forecast_arima(actual_5m)
        assert len(result) == 12

    def test_no_negative_values(self, actual_5m):
        result = forecast_arima(actual_5m)
        assert (result >= 0).all()

    def test_falls_back_with_few_points(self):
        result = forecast_arima(np.array([100.0]))
        assert len(result) == 12

    def test_works_with_variable_length(self, actual_3m):
        result = forecast_arima(actual_3m)
        assert len(result) == 12


class TestApplyMethod:
    def test_valid_methods(self, actual_5m, budget_12m):
        for method in ["linear", "budget_scaled", "polynomial",
                       "holt_damped", "spline_damped", "arima"]:
            result = apply_method(actual_5m, budget_12m, 1500, method)
            assert len(result) == 12, f"{method} failed"

    def test_invalid_method_raises(self, actual_5m, budget_12m):
        with pytest.raises(ValueError):
            apply_method(actual_5m, budget_12m, 1500, "nonexistent")


class TestSelectBestMethod:
    def test_selects_min_rmse(self):
        df = pd.DataFrame({
            "method": ["a", "b", "c"],
            "rmse_mean": [10.0, 5.0, 8.0],
        })
        best = select_best_method(df, "rmse_mean")
        assert best == "b"

    def test_empty_returns_default(self):
        df = pd.DataFrame()
        best = select_best_method(df)
        assert best == "budget_scaled"


class TestAggregateForecast:
    def test_aggregates_by_dimension(self):
        df = pd.DataFrame({
            "Classif": ["Labor", "Labor", "Expenses"],
            "Jan-25": [100, 200, 50],
            "Feb-25": [110, 210, 55],
            "Mar-25": [120, 220, 60],
            "Apr-25": [130, 230, 65],
            "May-25": [140, 240, 70],
            "Jun-25": [150, 250, 75],
            "Jul-25": [160, 260, 80],
            "Aug-25": [170, 270, 85],
            "Sep-25": [180, 280, 90],
            "Oct-25": [190, 290, 95],
            "Nov-25": [200, 300, 100],
            "Dec-25": [210, 310, 105],
            "Forecast_5+7": [1860, 3060, 930],
            "Budget_FY": [2000, 3200, 1000],
        })
        result = aggregate_forecast(df, ["Classif"])
        assert len(result) == 2
        labor = result[result["Classif"] == "Labor"]
        assert labor["Forecast_5+7"].iloc[0] == 1860 + 3060
        assert labor["Budget_FY"].iloc[0] == 2000 + 3200
        assert "Var_Abs" in result.columns
        assert "Var_Pct" in result.columns
