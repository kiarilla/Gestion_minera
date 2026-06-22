"""Tests para data_loader.py."""

import pandas as pd
import pytest

from src.data_loader import (
    DATA_FILE,
    load_budget_detail,
    load_forecast_detail,
    load_grupos_mapping,
    load_pivot_summary,
    get_merged_data,
    MONTH_COLS,
    REAL_MONTHS,
    PROJ_MONTHS,
    DIM_COLS,
)


class TestLoadForecastDetail:
    """Pruebas para la carga de la hoja Gastos (forecast detalle)."""

    def test_loads_without_error(self):
        df = load_forecast_detail()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_has_required_columns(self):
        df = load_forecast_detail()
        for col in DIM_COLS:
            assert col in df.columns, f"Falta columna dimensional: {col}"
        for col in MONTH_COLS:
            assert col in df.columns, f"Falta columna mensual: {col}"
        for col in ["YTD", "Forecast FY", "Budget FY", "BYTD"]:
            assert col in df.columns, f"Falta columna extra: {col}"

    def test_ytd_matches_real_months_sum(self):
        df = load_forecast_detail()
        real_sum = df[REAL_MONTHS].sum(axis=1)
        diff = (real_sum - df["YTD"]).abs()
        # Allow small floating point differences
        assert (diff < 1.0).all(), (
            f"YTD no coincide con suma de reales. Max diff: {diff.max()}"
        )

    def test_forecast_fy_matches_ytd_plus_proj(self):
        df = load_forecast_detail()
        proj_sum = df[PROJ_MONTHS].sum(axis=1)
        expected = df["YTD"] + proj_sum
        diff = (expected - df["Forecast FY"]).abs()
        assert (diff < 1.0).all(), (
            f"Forecast FY no coincide con YTD + proyeccion. Max diff: {diff.max()}"
        )

    def test_no_total_rows(self):
        df = load_forecast_detail()
        if "Resp" in df.columns:
            bad = df[df["Resp"].astype(str).str.upper().str.contains("TOTAL")]
            assert len(bad) == 0, "Hay filas de total sin filtrar"

    def test_numeric_columns_are_float(self):
        df = load_forecast_detail()
        for col in MONTH_COLS + ["YTD", "Forecast FY", "Budget FY", "BYTD"]:
            assert pd.api.types.is_numeric_dtype(df[col]), (
                f"Columna {col} no es numerica"
            )

    def test_classif_values_valid(self):
        df = load_forecast_detail()
        valid = {"Labor", "Expenses", "Contractors", "Fuel", "S&C", "Power",
                 "Maintenance", "Spare Parts", "Rehandling", "Water"}
        actual = set(df["Classif"].unique())
        unknown = actual - valid
        assert len(unknown) == 0, f"Classif desconocidas: {unknown}"

    def test_derived_columns_exist(self):
        df = load_forecast_detail()
        assert "REAL_MONTHS_SUM" in df.columns
        assert "PROJ_MONTHS_SUM" in df.columns


class TestLoadBudgetDetail:
    """Pruebas para la carga de la hoja Budget (presupuesto multi-anio)."""

    def test_loads_without_error(self):
        df = load_budget_detail()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_has_required_columns(self):
        df = load_budget_detail()
        for col in DIM_COLS:
            assert col in df.columns
        for col in MONTH_COLS:
            assert col in df.columns
        for col in ["FY25", "FY26", "FY27", "FY28", "FY29", "BYTD"]:
            assert col in df.columns

    def test_fy25_matches_monthly_sum(self):
        df = load_budget_detail()
        monthly_sum = df[MONTH_COLS].sum(axis=1)
        diff = (monthly_sum - df["FY25"]).abs()
        assert (diff < 1.0).all(), (
            f"FY25 no coincide con suma mensual. Max diff: {diff.max()}"
        )

    def test_bytd_matches_first_5_months(self):
        df = load_budget_detail()
        bytd_calc = df[REAL_MONTHS].sum(axis=1)
        diff = (bytd_calc - df["BYTD"]).abs()
        assert (diff < 1.0).all(), (
            f"BYTD no coincide con suma Ene-May. Max diff: {diff.max()}"
        )

    def test_derived_columns_exist(self):
        df = load_budget_detail()
        assert "BUDGET_REAL_MONTHS" in df.columns
        assert "BUDGET_PROJ_MONTHS" in df.columns

    def test_no_total_rows(self):
        df = load_budget_detail()
        if "Resp" in df.columns:
            bad = df[df["Resp"].astype(str).str.upper().str.contains("TOTAL")]
            assert len(bad) == 0


class TestLoadGruposMapping:
    """Pruebas para la carga de la hoja GRUPOS."""

    def test_loads_without_error(self):
        df = load_grupos_mapping()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 98

    def test_has_required_columns(self):
        df = load_grupos_mapping()
        assert "RESPONSABILIDAD" in df.columns
        assert "CLASS" in df.columns
        assert "GRUPOS" in df.columns

    def test_class_values_valid(self):
        df = load_grupos_mapping()
        valid = {"RH", "OP", "OM", "SG", "SO", "AS", "PR"}
        actual = set(df["CLASS"].unique())
        unknown = actual - valid
        assert len(unknown) == 0, f"CLASS desconocidas: {unknown}"

    def test_no_empty_strings_after_clean(self):
        df = load_grupos_mapping()
        for col in df.select_dtypes(include=["object"]).columns:
            empty = df[df[col] == ""]
            assert len(empty) == 0, f"Strings vacios en columna {col}"


class TestGetMergedData:
    """Pruebas para la union de datos."""

    def test_returns_two_dataframes(self):
        forecast, budget = get_merged_data()
        assert isinstance(forecast, pd.DataFrame)
        assert isinstance(budget, pd.DataFrame)
        assert len(forecast) > 0
        assert len(budget) > 0

    def test_merged_has_grupos_columns(self):
        forecast, budget = get_merged_data()
        for col in ["CLASS", "GRUPOS", "RESPONSABILIDAD"]:
            assert col in forecast.columns, f"Falta {col} en forecast"
            assert col in budget.columns, f"Falta {col} en budget"

    def test_forecast_has_no_null_class(self):
        forecast, _ = get_merged_data()
        assert forecast["CLASS"].isna().sum() == 0, "Hay CLASS nulos en forecast"

    def test_grupos_columns_not_empty(self):
        forecast, budget = get_merged_data()
        assert not forecast["CLASS"].isna().all()
        assert not forecast["GRUPOS"].isna().all()


class TestLoadPivotSummary:
    """Pruebas para la carga del pivote resumen."""

    def test_loads_without_error(self):
        df = load_pivot_summary()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_has_expected_metric_columns(self):
        df = load_pivot_summary()
        expected = ["Suma de YTD", "Suma de Forecast FY", "Suma de Budget FY"]
        for col in expected:
            assert col in df.columns, f"Falta columna {col}"
