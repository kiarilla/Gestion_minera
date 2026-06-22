"""
forecast.py -- Modelos de proyeccion NO lineal Forecast 5+7.

Implementa 6 metodos de proyeccion para los 7 meses restantes (Jun-Dic)
basados en los 5 meses reales (Ene-May):

1. Lineal / run-rate (benchmark)
2. Perfil presupuestario reescalado con amortiguacion
3. Regresion polinomica (grado 2)
4. Suavizamiento Holt con tendencia amortiguada (damped)
5. Interpolacion spline + extrapolacion amortiguada
6. ARIMA simple (con advertencia de pocos datos)

Incluye backtesting y seleccion del mejor metodo por metrica.
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

from src.metrics import mape, rmse, mae, evaluate_all

MONTHS = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], dtype=float)


# ---------------------------------------------------------------------------
# 1. Lineal / run-rate (benchmark)
# ---------------------------------------------------------------------------

def forecast_linear(actual_months: np.ndarray) -> np.ndarray:
    """
    Proyeccion lineal: cada mes futuro = promedio de los meses reales.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos (ej. 5 para Ene-May).

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion para los 12 meses (los primeros n son los reales).
    """
    actual_months = np.asarray(actual_months, dtype=float)
    n = len(actual_months)
    monthly_avg = np.nanmean(actual_months)
    forecast = np.full(12, monthly_avg)
    forecast[:n] = actual_months
    return forecast


# ---------------------------------------------------------------------------
# 2. Perfil presupuestario reescalado (seasonal-naive ajustado)
# ---------------------------------------------------------------------------

def forecast_budget_scaled(
    actual_months: np.ndarray,
    budget_12m: np.ndarray,
    budget_fy: float = 0.0,
    damp_factor: float = 0.3,
) -> np.ndarray:
    """
    Proyeccion basada en el perfil mensual del presupuesto, reescalado
    con amortiguacion no lineal del ratio de ejecucion observado.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos.
    budget_12m : np.ndarray shape (12,)
        Perfil mensual del presupuesto.
    budget_fy : float
        Presupuesto anual total (FY25).
    damp_factor : float
        Factor de amortiguacion (0 = sin ajuste, 1 = ajuste completo).

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion 12 meses (primeros n = reales).
    """
    actual_months = np.asarray(actual_months, dtype=float)
    budget_12m = np.asarray(budget_12m, dtype=float)
    n = len(actual_months)

    if len(budget_12m) != 12:
        return forecast_linear(actual_months)

    budget_past = budget_12m[:n]
    budget_future = budget_12m[n:]

    sum_actual = np.nansum(actual_months)
    sum_budget_past = np.nansum(budget_past)
    sum_budget_future = np.nansum(budget_future)

    if sum_budget_past < 1.0 or sum_budget_future < 1.0:
        return forecast_linear(actual_months)

    r_exec = sum_actual / sum_budget_past
    r_damped = 1.0 + (r_exec - 1.0) * damp_factor

    proj_future = budget_future * r_damped

    if budget_fy > 0:
        total_projected = sum_actual + np.nansum(proj_future)
        max_allowed = budget_fy * 3
        if total_projected > max_allowed:
            scale = (max_allowed - sum_actual) / np.nansum(proj_future)
            proj_future *= max(0.01, scale)

    forecast = np.concatenate([actual_months, proj_future])
    return forecast


# ---------------------------------------------------------------------------
# 3. Regresion polinomica (grado 2)
# ---------------------------------------------------------------------------

def forecast_polynomial(
    actual_months: np.ndarray, degree: int = 2
) -> np.ndarray:
    """
    Ajusta un polinomio de grado `degree` a los puntos reales
    y extrapola a los 12 meses.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos.
    degree : int
        Grado del polinomio (default 2).

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion 12 meses.
    """
    actual_months = np.asarray(actual_months, dtype=float)
    n = len(actual_months)
    x_train = MONTHS[:n].reshape(-1, 1)
    y_train = actual_months.copy()

    valid = ~np.isnan(y_train) & (y_train >= 0)
    if valid.sum() < 2:
        return forecast_linear(actual_months)

    x_valid = x_train[valid]
    y_valid = y_train[valid]

    actual_degree = min(degree, len(y_valid) - 1)

    poly = PolynomialFeatures(degree=actual_degree)
    x_poly = poly.fit_transform(x_valid)

    model = LinearRegression()
    model.fit(x_poly, y_valid)

    x_all = MONTHS.reshape(-1, 1)
    x_all_poly = poly.transform(x_all)
    y_all = model.predict(x_all_poly)

    y_all = np.maximum(y_all, 0)
    y_all[:n] = actual_months  # Mantener reales exactos

    return y_all


# ---------------------------------------------------------------------------
# 4. Suavizamiento Holt con tendencia amortiguada (damped)
# ---------------------------------------------------------------------------

def forecast_holt_damped(actual_months: np.ndarray) -> np.ndarray:
    """
    Suavizamiento exponencial de Holt con tendencia amortiguada.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos.

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion 12 meses.
    """
    actual_months = np.asarray(actual_months, dtype=float)
    n = len(actual_months)
    y_clean = actual_months.copy()
    y_clean[np.isnan(y_clean)] = 0.0

    if np.all(y_clean == 0) or n < 3:
        return forecast_linear(actual_months)

    steps_ahead = 12 - n

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            model = ExponentialSmoothing(
                y_clean,
                trend="add",
                damped_trend=True,
                initialization_method="estimated",
            )
            fitted = model.fit()
            pred = fitted.forecast(steps_ahead)
    except (ValueError, RuntimeError, np.linalg.LinAlgError):
        return forecast_polynomial(actual_months, degree=2)

    forecast = np.concatenate([actual_months, pred])
    forecast = np.maximum(forecast, 0)
    return forecast


# ---------------------------------------------------------------------------
# 5. Interpolacion spline + extrapolacion amortiguada
# ---------------------------------------------------------------------------

def forecast_spline_damped(actual_months: np.ndarray) -> np.ndarray:
    """
    Interpolacion por spline cubico con extrapolacion amortiguada.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos.

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion 12 meses.
    """
    actual_months = np.asarray(actual_months, dtype=float)
    n = len(actual_months)
    y_clean = actual_months.copy()
    y_clean[np.isnan(y_clean)] = 0.0

    x_known = np.arange(n, dtype=float)

    if np.all(y_clean == 0) or len(np.unique(y_clean)) < 3:
        return forecast_linear(actual_months)

    try:
        cs = CubicSpline(x_known, y_clean, bc_type="natural")
    except ValueError:
        return forecast_polynomial(actual_months, degree=2)

    x_ext = np.arange(n, 12, dtype=float)
    spline_ext = cs(x_ext)

    avg_real = np.nanmean(y_clean)
    n_future = 12 - n
    alpha = np.exp(-0.5 * np.arange(n_future))
    damped_ext = alpha * spline_ext + (1 - alpha) * avg_real
    damped_ext = np.maximum(damped_ext, 0)

    return np.concatenate([actual_months, damped_ext])


# ---------------------------------------------------------------------------
# 6. ARIMA simple
# ---------------------------------------------------------------------------

def forecast_arima(actual_months: np.ndarray) -> np.ndarray:
    """
    ARIMA(0,1,1) simple.

    ADVERTENCIA METODOLOGICA: Con pocos puntos, ARIMA no puede
    capturar estacionalidad ni estimar parametros de forma fiable.

    Parameters
    ----------
    actual_months : np.ndarray shape (n,)
        Valores reales de los meses transcurridos.

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion 12 meses.
    """
    actual_months = np.asarray(actual_months, dtype=float)
    n = len(actual_months)
    y_clean = actual_months.copy()
    y_clean[np.isnan(y_clean)] = 0.0

    if np.all(y_clean == 0) or n < 3:
        return forecast_linear(actual_months)

    steps_ahead = 12 - n

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            model = ARIMA(y_clean, order=(0, 1, 1))
            fitted = model.fit()
            pred = fitted.forecast(steps=steps_ahead)
    except (ValueError, RuntimeError, np.linalg.LinAlgError):
        return forecast_polynomial(actual_months, degree=2)

    forecast = np.concatenate([actual_months, pred])
    forecast = np.maximum(forecast, 0)
    return forecast


# ---------------------------------------------------------------------------
# Funcion maestra: aplica un metodo dado a una fila
# ---------------------------------------------------------------------------

def apply_method(
    actual_5m: np.ndarray,
    budget_12m: np.ndarray,
    budget_fy: float,
    method: str,
) -> np.ndarray:
    """
    Aplica el metodo de proyeccion especificado a una linea de gasto.

    Parameters
    ----------
    actual_5m : np.ndarray shape (5,)
        Valores reales Ene-May.
    budget_12m : np.ndarray shape (12,)
        Perfil mensual del presupuesto.
    budget_fy : float
        Presupuesto anual FY25.
    method : str
        Nombre del metodo: 'linear', 'budget_scaled', 'polynomial',
        'holt_damped', 'spline_damped', 'arima'.

    Returns
    -------
    np.ndarray shape (12,)
        Proyeccion mensual (primeros 5 = reales).
    """
    methods = {
        "linear": lambda a, b, bfy: forecast_linear(a),
        "budget_scaled": lambda a, b, bfy: forecast_budget_scaled(a, b, bfy),
        "polynomial": lambda a, b, bfy: forecast_polynomial(a),
        "holt_damped": lambda a, b, bfy: forecast_holt_damped(a),
        "spline_damped": lambda a, b, bfy: forecast_spline_damped(a),
        "arima": lambda a, b, bfy: forecast_arima(a),
    }

    if method not in methods:
        raise ValueError(
            f"Metodo desconocido: {method}. Opciones: {list(methods.keys())}"
        )

    actual_5m = np.asarray(actual_5m, dtype=float)
    budget_12m = np.asarray(budget_12m, dtype=float)

    return methods[method](actual_5m, budget_12m, budget_fy)


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------

def run_backtesting(
    forecast_df: pd.DataFrame,
    budget_df: pd.DataFrame,
    methods: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Ejecuta backtesting walk-forward sobre todas las lineas de gasto.

    Procedimiento:
      - Train en meses 1-3, predecir meses 4-5
      - Comparar predicciones vs reales (meses 4-5)
      - Calcular MAPE, RMSE, MAE para cada metodo

    Se calculan metricas por linea y se agregan por metodo.

    Parameters
    ----------
    forecast_df : pd.DataFrame
        DataFrame de forecast (hoja Gastos) con columnas mensuales Jan-25...May-25.
    budget_df : pd.DataFrame
        DataFrame de budget (hoja Budget) con columnas mensuales Jan-25...Dec-25
        y columna FY25.
    methods : list[str] or None
        Lista de metodos a evaluar. Si es None, usa todos.

    Returns
    -------
    pd.DataFrame
        Resultados agregados por metodo: MAPE, RMSE, MAE promedio.
    """
    if methods is None:
        methods = [
            "linear", "budget_scaled", "polynomial",
            "holt_damped", "spline_damped", "arima",
        ]

    month_cols_f = ["Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25"]
    month_cols_b = [
        "Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25",
        "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25",
    ]

    # Alinear por dimensiones usando merge con suffixes y manejar
    # los meses 6-12 del budget que NO reciben suffix (no colisionan)
    common_cols = ["Resp", "Desc Resp", "VP", "Gerencia", "Proc",
                   "Desc Proc", "Item", "Desc Item", "Classif", "CC"]

    budget_renamed = budget_df[common_cols + month_cols_b + ["FY25"]].rename(
        columns={c: c + "_budget" for c in month_cols_b}
    )
    merged = forecast_df[common_cols + month_cols_f].merge(
        budget_renamed, on=common_cols, how="inner",
    )

    month_cols_b_renamed = [f"{c}_budget" for c in month_cols_b]

    all_metrics: list[dict] = []

    for method in methods:
        errors_m = []  # metricas por linea

        for _, row in merged.iterrows():
            actual_all = np.array([row[c] for c in month_cols_f], dtype=float)
            budget_all = np.array([row[c] for c in month_cols_b_renamed], dtype=float)
            budget_fy = float(row.get("FY25", 0) or 0)

            # Train en meses 1-3, test en 4-5
            train_actual = actual_all[:3]
            test_actual = actual_all[3:]

            if np.all(np.isnan(train_actual)) or np.all(np.isnan(test_actual)):
                continue
            if np.nansum(train_actual) < 0.01 and np.nansum(test_actual) < 0.01:
                continue

            # Ajustar budget_12m al entrenamiento: budget de 3 meses + 9 restantes
            budget_12m = np.concatenate([budget_all[:3], budget_all[3:]])

            try:
                pred_12m = apply_method(train_actual, budget_12m, budget_fy, method)
            except Exception:
                continue

            pred_test = pred_12m[3:5]

            m = evaluate_all(test_actual, pred_test)
            m["method"] = method
            errors_m.append(m)

        if errors_m:
            df_err = pd.DataFrame(errors_m)
            agg = {
                "method": method,
                "mape_mean": df_err["mape"].mean(),
                "mape_median": df_err["mape"].median(),
                "rmse_mean": df_err["rmse"].mean(),
                "rmse_median": df_err["rmse"].median(),
                "mae_mean": df_err["mae"].mean(),
                "mae_median": df_err["mae"].median(),
                "n_lines": len(df_err),
            }
            all_metrics.append(agg)

    return pd.DataFrame(all_metrics)


def select_best_method(results_df: pd.DataFrame,
                       metric: str = "rmse_mean") -> str:
    """
    Selecciona el mejor metodo segun la metrica indicada (menor = mejor).

    Por defecto usa RMSE (rmse_mean) que es mas robusto que MAPE
    cuando hay partidas con montos cercanos a cero.

    Parameters
    ----------
    results_df : pd.DataFrame
        Resultado de run_backtesting().
    metric : str
        Columna de metrica a usar.

    Returns
    -------
    str
        Nombre del mejor metodo.
    """
    if results_df.empty:
        return "budget_scaled"

    best_row = results_df.loc[results_df[metric].idxmin()]
    return str(best_row["method"])


# ---------------------------------------------------------------------------
# Proyeccion completa (Forecast 5+7) sobre todas las lineas
# ---------------------------------------------------------------------------

def project_full_forecast(
    forecast_df: pd.DataFrame,
    budget_df: pd.DataFrame,
    method: str = "budget_scaled",
) -> pd.DataFrame:
    """
    Genera la proyeccion Forecast 5+7 completa para todas las lineas
    usando el metodo especificado.

    Parameters
    ----------
    forecast_df : pd.DataFrame
        DataFrame de forecast (hoja Gastos).
    budget_df : pd.DataFrame
        DataFrame de budget (hoja Budget).
    method : str
        Metodo de proyeccion a usar.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas dimensionales + proyeccion mensual (12 cols)
        + Forecast_5+7 (anual) + Budget_FY + var_abs + var_pct.
    """
    month_cols_f = ["Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25"]
    month_cols_b = [
        "Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25",
        "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25",
    ]
    dim_cols = ["Resp", "Desc Resp", "VP", "Gerencia", "Proc",
                "Desc Proc", "Item", "Desc Item", "Classif", "CC"]

    budget_renamed = budget_df[dim_cols + month_cols_b + ["FY25"]].rename(
        columns={c: c + "_budget" for c in month_cols_b}
    )
    merged = forecast_df[dim_cols + month_cols_f].merge(
        budget_renamed, on=dim_cols, how="inner",
    )
    month_cols_b_renamed = [f"{c}_budget" for c in month_cols_b]

    results = []
    for _, row in merged.iterrows():
        actual_5m = np.array([row[c] for c in month_cols_f], dtype=float)
        budget_12m = np.array([row[c] for c in month_cols_b_renamed], dtype=float)
        budget_fy = float(row.get("FY25", 0) or 0)

        proj = apply_method(actual_5m, budget_12m, budget_fy, method)

        record = {
            **{c: row[c] for c in dim_cols},
            **{month_cols_f[i]: proj[i] for i in range(5)},
            **{month_cols_b[5 + i]: proj[5 + i] for i in range(7)},
            "Forecast_5+7": float(np.nansum(proj)),
            "Budget_FY": budget_fy,
        }
        record["Var_Abs"] = record["Forecast_5+7"] - record["Budget_FY"]
        record["Var_Pct"] = (
            (record["Var_Abs"] / record["Budget_FY"] * 100)
            if record["Budget_FY"] != 0 else 0.0
        )
        results.append(record)

    return pd.DataFrame(results)


def aggregate_forecast(
    forecast_lines: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    """
    Agrega la proyeccion Forecast 5+7 por dimensiones.

    Parameters
    ----------
    forecast_lines : pd.DataFrame
        Resultado de project_full_forecast().
    group_cols : list[str]
        Columnas por las cuales agrupar (ej. ['VP'], ['Classif']).

    Returns
    -------
    pd.DataFrame
        Proyeccion agregada con Forecast_5+7, Budget_FY, Var_Abs, Var_Pct.
    """
    month_cols_b = [
        "Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25",
        "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25",
    ]

    agg = forecast_lines.groupby(group_cols, dropna=False).agg(
        **{
            **{c: (c, "sum") for c in month_cols_b},
            "Forecast_5+7": ("Forecast_5+7", "sum"),
            "Budget_FY": ("Budget_FY", "sum"),
        }
    ).reset_index()

    agg.columns = [c[0] if isinstance(c, tuple) else c for c in agg.columns]
    agg["Var_Abs"] = agg["Forecast_5+7"] - agg["Budget_FY"]
    agg["Var_Pct"] = (
        (agg["Var_Abs"] / agg["Budget_FY"].replace(0, np.nan) * 100)
    ).fillna(0)

    return agg
