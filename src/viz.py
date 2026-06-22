"""
viz.py -- Funciones de visualizacion con Plotly para la app Streamlit.

Genera graficos interactivos: tendencia mensual, waterfall, treemap,
barras comparativas, tabla de metodos, y top desviaciones.
"""

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLOR_PALETTE = px.colors.qualitative.Plotly
MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MONTH_COLS = [
    "Jan-25", "Feb-25", "Mar-25", "Apr-25", "May-25",
    "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25",
]


# ---------------------------------------------------------------------------
# Tendencia mensual
# ---------------------------------------------------------------------------

def plot_monthly_trend(
    forecast_series: np.ndarray,
    budget_series: np.ndarray,
    official_series: Optional[np.ndarray] = None,
    title: str = "Tendencia Mensual: Real + Proyeccion",
    n_real: int = 5,
) -> go.Figure:
    """
    Grafico de lineas: reales (Ene-May) + proyeccion (Jun-Dic) + budget.

    Parameters
    ----------
    forecast_series : np.ndarray shape (12,)
        Proyeccion mensual (primeros n_real = reales).
    budget_series : np.ndarray shape (12,)
        Presupuesto mensualizado.
    official_series : np.ndarray shape (12,), optional
        Forecast oficial para comparar.
    title : str
        Titulo del grafico.
    n_real : int
        Numero de meses reales (default 5).

    Returns
    -------
    go.Figure
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=MONTH_NAMES,
        y=forecast_series,
        mode="lines+markers",
        name="Forecast 5+7",
        line=dict(color=COLOR_PALETTE[0], width=3),
        marker=dict(size=6),
    ))

    fig.add_trace(go.Scatter(
        x=MONTH_NAMES,
        y=budget_series,
        mode="lines+markers",
        name="Budget FY",
        line=dict(color=COLOR_PALETTE[1], width=2, dash="dash"),
        marker=dict(size=4),
    ))

    if official_series is not None:
        fig.add_trace(go.Scatter(
            x=MONTH_NAMES,
            y=official_series,
            mode="lines+markers",
            name="Forecast Oficial",
            line=dict(color=COLOR_PALETTE[2], width=2, dash="dot"),
            marker=dict(size=4),
        ))

    # Linea vertical en mes 5 (fin de reales)
    fig.add_vline(
        x=n_real - 0.5, line_width=1, line_dash="solid",
        line_color="gray", opacity=0.5,
        annotation_text="Fin reales (May)",
        annotation_position="top left",
    )

    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis_title="Monto",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# ---------------------------------------------------------------------------
# Waterfall: Budget -> Desviaciones -> Forecast 5+7
# ---------------------------------------------------------------------------

def plot_waterfall(
    budget_total: float,
    forecast_total: float,
    deviations: Optional[dict[str, float]] = None,
    title: str = "Waterfall: Budget FY a Forecast 5+7",
) -> go.Figure:
    """
    Grafico waterfall que muestra como se pasa del Budget al Forecast 5+7.

    Parameters
    ----------
    budget_total : float
        Total Budget FY.
    forecast_total : float
        Total Forecast 5+7.
    deviations : dict[str, float], optional
        Desviaciones por categoria (ej. {"Labor": 5000, "Expenses": -8000}).
    title : str
        Titulo del grafico.

    Returns
    -------
    go.Figure
    """
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + (["relative"] * len(deviations) if deviations else []) + ["total"],
        x=["Budget FY"] + (list(deviations.keys()) if deviations else []) + ["Forecast 5+7"],
        y=[budget_total] + (list(deviations.values()) if deviations else []) + [forecast_total],
        connector={"mode": "spanning", "line": {"width": 1}},
        decreasing={"marker": {"color": "#EF553B"}},
        increasing={"marker": {"color": "#00CC96"}},
        totals={"marker": {"color": "#636EFA"}},
    ))

    fig.update_layout(
        title=title,
        template="plotly_white",
        showlegend=False,
        yaxis_title="Monto",
    )

    return fig


# ---------------------------------------------------------------------------
# Treemap por dimension
# ---------------------------------------------------------------------------

def plot_treemap(
    df: pd.DataFrame,
    path: list[str],
    value_col: str,
    title: str = "Composicion del Gasto",
    color_col: Optional[str] = None,
) -> go.Figure:
    """
    Treemap jerarquico del gasto por dimensiones.

    Parameters
    ----------
    df : pd.DataFrame
        Datos con columnas de jerarquia.
    path : list[str]
        Columnas que definen la jerarquia del treemap (ej. ['VP', 'Gerencia']).
    value_col : str
        Columna con los valores a graficar.
    title : str
        Titulo del grafico.
    color_col : str, optional
        Columna para colorear (ej. variacion porcentual).

    Returns
    -------
    go.Figure
    """
    fig = px.treemap(
        df.dropna(subset=path + [value_col]),
        path=path,
        values=value_col,
        color=color_col,
        color_continuous_scale="RdBu" if color_col else None,
        color_continuous_midpoint=0 if color_col else None,
        title=title,
    )

    fig.update_layout(template="plotly_white", margin=dict(l=0, r=0, t=40, b=0))

    return fig


# ---------------------------------------------------------------------------
# Barras comparativas de metodos
# ---------------------------------------------------------------------------

def plot_method_comparison(
    results_df: pd.DataFrame,
    metric: str = "rmse_mean",
    title: str = "Comparacion de Metodos de Proyeccion",
) -> go.Figure:
    """
    Grafico de barras horizontales comparando metodos por metrica.

    Parameters
    ----------
    results_df : pd.DataFrame
        Resultado de run_backtesting().
    metric : str
        Metrica a graficar.
    title : str
        Titulo del grafico.

    Returns
    -------
    go.Figure
    """
    df = results_df.sort_values(metric, ascending=True)

    fig = px.bar(
        df,
        y="method",
        x=metric,
        orientation="h",
        title=title,
        color="method",
        color_discrete_sequence=COLOR_PALETTE,
        text=df[metric].apply(lambda x: f"{x:,.0f}"),
    )

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        xaxis_title=metric.upper(),
        yaxis_title="",
    )

    return fig


# ---------------------------------------------------------------------------
# Barras comparativas por dimension
# ---------------------------------------------------------------------------

def plot_bar_comparison(
    df: pd.DataFrame,
    x_col: str,
    budget_col: str = "Budget_FY",
    forecast_col: str = "Forecast_5+7",
    title: str = "Forecast 5+7 vs Budget FY",
    top_n: int = 15,
) -> go.Figure:
    """
    Grafico de barras agrupadas comparando Forecast vs Budget por dimension.

    Parameters
    ----------
    df : pd.DataFrame
        Datos agregados por dimension.
    x_col : str
        Columna del eje X (categoria).
    budget_col : str
        Columna con el Budget.
    forecast_col : str
        Columna con el Forecast.
    title : str
        Titulo.
    top_n : int
        Numero maximo de categorias a mostrar.

    Returns
    -------
    go.Figure
    """
    df_plot = df.copy()
    if len(df_plot) > top_n:
        df_plot["_abs"] = df_plot[budget_col].abs()
        df_plot = df_plot.nlargest(top_n, "_abs")
        df_plot = df_plot.sort_values(budget_col, ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_plot[x_col].astype(str),
        x=df_plot[budget_col],
        name=budget_col.replace("_", " "),
        orientation="h",
        marker=dict(color=COLOR_PALETTE[0], opacity=0.7),
    ))

    fig.add_trace(go.Bar(
        y=df_plot[x_col].astype(str),
        x=df_plot[forecast_col],
        name=forecast_col.replace("_", " "),
        orientation="h",
        marker=dict(color=COLOR_PALETTE[1], opacity=0.7),
    ))

    fig.update_layout(
        title=title,
        barmode="group",
        template="plotly_white",
        xaxis_title="Monto",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# ---------------------------------------------------------------------------
# Top desviaciones
# ---------------------------------------------------------------------------

def plot_top_deviations(
    df: pd.DataFrame,
    label_col: str = "Desc Item",
    deviation_col: str = "Var_vs_Budget_Abs",
    pct_col: str = "Var_vs_Budget_Pct",
    title: str = "Top Desviaciones vs Budget",
    n: int = 20,
) -> go.Figure:
    """
    Grafico de barras horizontales con las N mayores desviaciones.

    Parameters
    ----------
    df : pd.DataFrame
        Datos con desviaciones.
    label_col : str
        Columna para etiquetas.
    deviation_col : str
        Columna con desviacion absoluta.
    pct_col : str
        Columna con desviacion porcentual.
    title : str
        Titulo.
    n : int
        Numero de items.

    Returns
    -------
    go.Figure
    """
    df_plot = df.copy()
    df_plot = df_plot.nlargest(n, deviation_col).sort_values(deviation_col)

    colors = [
        "#EF553B" if v < 0 else "#00CC96"
        for v in df_plot[deviation_col]
    ]

    fig = go.Figure(go.Bar(
        y=df_plot[label_col].astype(str),
        x=df_plot[deviation_col],
        orientation="h",
        marker_color=colors,
        text=df_plot[pct_col].apply(lambda x: f"{x:+.1f}%"),
        textposition="outside",
    ))

    fig.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Desviacion Absoluta",
        yaxis_title="",
    )

    return fig


# ---------------------------------------------------------------------------
# KPIs en tarjetas (uso directo en Streamlit)
# ---------------------------------------------------------------------------

def format_currency(value: float, decimals: int = 0) -> str:
    """Formatea un monto con separadores de miles."""
    if abs(value) >= 1e9:
        return f"{value / 1e9:,.{decimals}f} MM"
    elif abs(value) >= 1e6:
        return f"{value / 1e6:,.{decimals}f} M"
    elif abs(value) >= 1e3:
        return f"{value / 1e3:,.{decimals}f} K"
    return f"{value:,.{decimals}f}"
