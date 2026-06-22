"""
insights.py -- Calculo de desviaciones, KPIs y hallazgos.

Compara el Forecast 5+7 generado contra el Budget FY y el Forecast FY
oficial, generando tablas de desviacion y KPIs agregados.
"""

from typing import Optional

import numpy as np
import pandas as pd

from src.data_loader import load_forecast_detail, load_budget_detail, load_grupos_mapping
from src.forecast import project_full_forecast, aggregate_forecast


def compute_deviations(
    forecast_lines: pd.DataFrame,
    compare_vs_official: bool = True,
) -> pd.DataFrame:
    """
    Calcula desviaciones absolutas y porcentuales del Forecast 5+7
    contra el Budget FY y, si se solicita, contra el Forecast FY oficial.

    Parameters
    ----------
    forecast_lines : pd.DataFrame
        Resultado de project_full_forecast().
    compare_vs_official : bool
        Si es True, carga el Forecast FY oficial y lo agrega.

    Returns
    -------
    pd.DataFrame
        Incluye columnas Var_vs_Budget_Abs, Var_vs_Budget_Pct, y si
        corresponde, Var_vs_Official_Abs, Var_vs_Official_Pct.
    """
    df = forecast_lines.copy()

    df["Var_vs_Budget_Abs"] = df["Forecast_5+7"] - df["Budget_FY"]
    df["Var_vs_Budget_Pct"] = np.where(
        df["Budget_FY"].abs() > 0.01,
        df["Var_vs_Budget_Abs"] / df["Budget_FY"].abs() * 100,
        0.0,
    )

    if compare_vs_official:
        official = load_forecast_detail()
        official_dev = (
            official[["Resp", "Desc Resp", "VP", "Gerencia", "Proc",
                       "Desc Proc", "Item", "Desc Item", "Classif", "CC",
                       "Forecast FY"]]
            .rename(columns={"Forecast FY": "Forecast_FY_Oficial"})
        )
        df = df.merge(official_dev, on=[
            "Resp", "Desc Resp", "VP", "Gerencia", "Proc",
            "Desc Proc", "Item", "Desc Item", "Classif", "CC",
        ], how="left")

        df["Var_vs_Official_Abs"] = (
            df["Forecast_5+7"] - df["Forecast_FY_Oficial"]
        )
        df["Var_vs_Official_Pct"] = np.where(
            df["Forecast_FY_Oficial"].abs() > 0.01,
            df["Var_vs_Official_Abs"] / df["Forecast_FY_Oficial"].abs() * 100,
            0.0,
        )

    return df


def top_deviations(
    deviations_df: pd.DataFrame,
    by: str = "Var_vs_Budget_Abs",
    n: int = 20,
    ascending: bool = True,
) -> pd.DataFrame:
    """
    Retorna las N lineas con las mayores desviaciones (positivas o negativas).

    Parameters
    ----------
    deviations_df : pd.DataFrame
        Resultado de compute_deviations().
    by : str
        Columna por la cual ordenar.
    n : int
        Numero de lineas a retornar.
    ascending : bool
        True para las mas negativas, False para las mas positivas.

    Returns
    -------
    pd.DataFrame
    """
    return deviations_df.nsmallest(n, by) if ascending else deviations_df.nlargest(n, by)


def compute_kpis(
    forecast_lines: pd.DataFrame,
    forecast_df_official: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Calcula KPIs agregados del Forecast 5+7.

    Parameters
    ----------
    forecast_lines : pd.DataFrame
        Resultado de project_full_forecast().
    forecast_df_official : pd.DataFrame, optional
        DataFrame de forecast oficial (hoja Gastos) para comparar.

    Returns
    -------
    dict
        Diccionario con KPIs clave:
        - Budget_FY_Total
        - Forecast_5plus7_Total
        - Real_YTD_Total (suma de reales Ene-May)
        - Pct_Avance_Real (Real_YTD / Budget_FY * 100)
        - Var_vs_Budget_Abs
        - Var_vs_Budget_Pct
        - Forecast_Oficial_Total (si hay official)
        - Var_vs_Oficial_Abs
        - Var_vs_Oficial_Pct
    """
    total_budget = forecast_lines["Budget_FY"].sum()
    total_forecast = forecast_lines["Forecast_5+7"].sum()

    real_months = ["Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25"]
    total_real_ytd = forecast_lines[real_months].sum().sum()

    kpis = {
        "Budget_FY_Total": total_budget,
        "Forecast_5plus7_Total": total_forecast,
        "Real_YTD_Total": total_real_ytd,
        "Pct_Avance_Real": (total_real_ytd / total_budget * 100)
        if total_budget != 0 else 0.0,
        "Var_vs_Budget_Abs": total_forecast - total_budget,
        "Var_vs_Budget_Pct": ((total_forecast - total_budget) / total_budget * 100)
        if total_budget != 0 else 0.0,
    }

    if forecast_df_official is not None:
        total_official = forecast_df_official["Forecast FY"].sum()
        kpis["Forecast_Oficial_Total"] = total_official
        kpis["Var_vs_Oficial_Abs"] = total_forecast - total_official
        kpis["Var_vs_Oficial_Pct"] = (
            (total_forecast - total_official) / total_official * 100
            if total_official != 0 else 0.0
        )

    return kpis


def compare_with_official(
    forecast_lines: pd.DataFrame,
    group_cols: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Compara el Forecast 5+7 contra el Forecast FY oficial y el Budget FY.

    Parameters
    ----------
    forecast_lines : pd.DataFrame
        Debe incluir columna 'Forecast_FY_Oficial' (via compute_deviations).
    group_cols : list[str], optional
        Columnas de agrupacion.

    Returns
    -------
    pd.DataFrame
        Tabla comparativa con Budget, Forecast Oficial y Forecast 5+7.
    """
    if group_cols is None:
        group_cols = ["Classif"]

    df = forecast_lines.copy()

    if "Forecast_FY_Oficial" not in df.columns:
        official = load_forecast_detail()
        df = df.merge(
            official[["Resp", "Desc Resp", "VP", "Gerencia", "Proc",
                       "Desc Proc", "Item", "Desc Item", "Classif", "CC",
                       "Forecast FY"]]
            .rename(columns={"Forecast FY": "Forecast_FY_Oficial"}),
            on=["Resp", "Desc Resp", "VP", "Gerencia", "Proc",
                "Desc Proc", "Item", "Desc Item", "Classif", "CC"],
            how="left",
        )

    agg = df.groupby(group_cols, dropna=False).agg(
        Budget_FY=("Budget_FY", "sum"),
        Forecast_Oficial=("Forecast_FY_Oficial", "sum"),
        Forecast_5plus7=("Forecast_5+7", "sum"),
    ).reset_index()

    # Calcular Real_YTD desde las columnas mensuales
    real_cols = ["Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25"]
    real_agg = df.groupby(group_cols, dropna=False)[real_cols].sum().sum(axis=1)
    agg["Real_YTD"] = real_agg.values

    agg["Var_Oficial_vs_Budget"] = agg["Forecast_Oficial"] - agg["Budget_FY"]
    agg["Var_5plus7_vs_Budget"] = agg["Forecast_5plus7"] - agg["Budget_FY"]
    agg["Var_5plus7_vs_Oficial"] = agg["Forecast_5plus7"] - agg["Forecast_Oficial"]

    return agg
