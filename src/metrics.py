"""
metrics.py -- Metricas de error para evaluar modelos de forecast.

Implementa MAPE, RMSE y MAE con manejo de casos borde
(division por cero, arrays vacios, etc.).
"""

import numpy as np
from typing import Optional


def mape(y_true: np.ndarray, y_pred: np.ndarray,
         epsilon: float = 1e-8) -> float:
    """
    Mean Absolute Percentage Error (MAPE).

    Ignora observaciones donde y_true == 0 para evitar division por cero.
    Retorna NaN si no hay observaciones validas.

    Parameters
    ----------
    y_true : np.ndarray
        Valores reales.
    y_pred : np.ndarray
        Valores predichos.
    epsilon : float
        Umbral minimo para considerar un valor distinto de cero.

    Returns
    -------
    float
        MAPE como porcentaje (0-100).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.abs(y_true) > epsilon
    if not mask.any():
        return np.nan

    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Root Mean Squared Error.

    Parameters
    ----------
    y_true : np.ndarray
        Valores reales.
    y_pred : np.ndarray
        Valores predichos.

    Returns
    -------
    float
        RMSE en las mismas unidades que los datos.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.nanmean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Mean Absolute Error.

    Parameters
    ----------
    y_true : np.ndarray
        Valores reales.
    y_pred : np.ndarray
        Valores predichos.

    Returns
    -------
    float
        MAE en las mismas unidades que los datos.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.nanmean(np.abs(y_true - y_pred)))


def evaluate_all(y_true: np.ndarray, y_pred: np.ndarray
                 ) -> dict[str, Optional[float]]:
    """
    Calcula todas las metricas para un par de series.

    Parameters
    ----------
    y_true : np.ndarray
        Valores reales.
    y_pred : np.ndarray
        Valores predichos.

    Returns
    -------
    dict
        Diccionario con keys 'mape', 'rmse', 'mae'.
    """
    return {
        "mape": mape(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mae": mae(y_true, y_pred),
    }
