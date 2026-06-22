"""
app.py -- Aplicacion Streamlit para visualizacion y gestion del Forecast 5+7.

Entrypoint principal. La logica de negocio reside en src/.
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Asegurar que src este en el path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data_loader import (
    load_forecast_detail,
    load_budget_detail,
    load_grupos_mapping,
    load_pivot_summary,
    get_merged_data,
)
from src.forecast import (
    run_backtesting,
    select_best_method,
    project_full_forecast,
    aggregate_forecast,
    apply_method,
)
from src.insights import (
    compute_deviations,
    compute_kpis,
    top_deviations,
    compare_with_official,
)
from src.model_store import (
    cache_exists,
    load_backtesting_results,
    load_forecast,
    load_metadata,
    save_backtesting_results,
    save_forecast,
    save_metadata,
    clear_cache,
)
from src.viz import (
    format_currency,
    plot_monthly_trend,
    plot_waterfall,
    plot_treemap,
    plot_method_comparison,
    plot_bar_comparison,
    plot_top_deviations,
    MONTH_COLS,
    MONTH_NAMES,
)

st.set_page_config(
    page_title="Forecast 5+7 - Minera",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 1. SISTEMA DE CARGA DE ARCHIVOS Y RUTEO DE DATOS
# ============================================================================
st.sidebar.title("Datos Maestros")
uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel de presupuestos", type=["xlsx", "xls"])

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
# Ruta donde el programa espera leer el archivo base
file_path = data_dir / "02_Gastos_Proy_Mejor_01-2025.xlsx"

if uploaded_file is not None:
    if "last_uploaded_name" not in st.session_state or st.session_state.last_uploaded_name != uploaded_file.name:
        st.session_state.last_uploaded_name = uploaded_file.name
        st.cache_data.clear()
        clear_cache()
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("Archivo cargado y procesado exitosamente.")

if not file_path.exists():
    st.info("Bienvenido a la Plataforma. Por favor, sube el archivo Excel maestro en la barra lateral para comenzar.")
    st.stop()

# ============================================================================
# 2. NAVEGACIÓN PRINCIPAL
# ============================================================================
st.sidebar.markdown("---")
st.sidebar.title("Navegacion")
app_mode = st.sidebar.radio("Selecciona un Modulo:", [
    "Forecast Operacional (5+7)",
    "Proyeccion Estrategica (2027-2031)"
])
st.sidebar.markdown("---")

# ============================================================================
# Carga de datos (cacheada)
# ============================================================================
@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    forecast_df = load_forecast_detail()
    budget_df = load_budget_detail()
    grupos_df = load_grupos_mapping()
    pivot_df = load_pivot_summary()
    forecast_merged, budget_merged = get_merged_data()
    return forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged

with st.spinner("Cargando datos del workbook..."):
    forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged = cargar_datos()

if "modelos_ejecutados" not in st.session_state:
    st.session_state.modelos_ejecutados = False
if "resultados_backtesting" not in st.session_state:
    st.session_state.resultados_backtesting = None
if "forecast_lines" not in st.session_state:
    st.session_state.forecast_lines = None
if "metodo_ganador" not in st.session_state:
    st.session_state.metodo_ganador = None
if "kpis" not in st.session_state:
    st.session_state.kpis = None

if cache_exists() and not st.session_state.modelos_ejecutados:
    cached_bt = load_backtesting_results()
    cached_fc = load_forecast()
    cached_meta = load_metadata()
    if cached_bt is not None and cached_fc is not None and cached_meta is not None:
        st.session_state.resultados_backtesting = cached_bt
        st.session_state.forecast_lines = cached_fc
        st.session_state.metodo_ganador = cached_meta.get("best_method", "budget_scaled")
        st.session_state.kpis = cached_meta.get("kpis", {})
        st.session_state.modelos_ejecutados = True

# ============================================================================
# ============================================================================
# MÓDULO 1: FORECAST OPERACIONAL 5+7
# ============================================================================
# ============================================================================
if app_mode == "Forecast Operacional (5+7)":

    if not st.session_state.modelos_ejecutados:
        st.warning(
            "No se encontraron modelos previamente ejecutados. "
            "Haga clic en el boton para ejecutar el backtesting y generar el Forecast 5+7."
        )
        if st.button("Ejecutar Modelos (Backtesting + Forecast)", type="primary", use_container_width=True):
            with st.spinner("Ejecutando backtesting de metodos..."):
                st.session_state.resultados_backtesting = run_backtesting(forecast_df, budget_df)

            st.session_state.metodo_ganador = select_best_method(
                st.session_state.resultados_backtesting, "rmse_mean"
            )

            with st.spinner(f"Generando Forecast 5+7 con metodo: {st.session_state.metodo_ganador}..."):
                st.session_state.forecast_lines = project_full_forecast(
                    forecast_df, budget_df, method=st.session_state.metodo_ganador
                )

            st.session_state.kpis = compute_kpis(st.session_state.forecast_lines, forecast_df)

            save_backtesting_results(st.session_state.resultados_backtesting)
            save_forecast(st.session_state.forecast_lines)
            save_metadata(st.session_state.metodo_ganador, st.session_state.kpis)
            st.session_state.modelos_ejecutados = True
            st.rerun()
        st.stop()

    resultados_backtesting = st.session_state.resultados_backtesting
    forecast_lines = st.session_state.forecast_lines
    metodo_ganador = st.session_state.metodo_ganador
    kpis = st.session_state.kpis

    deviation_df = compute_deviations(forecast_lines, compare_vs_official=True)
    agg_vp = aggregate_forecast(forecast_lines, ["VP"])
    agg_classif = aggregate_forecast(forecast_lines, ["Classif"])
    agg_gerencia = aggregate_forecast(forecast_lines, ["Gerencia"])

    st.sidebar.title("Filtros Globales")
    
    vps = ["Todas"] + sorted(forecast_merged["VP"].dropna().unique().tolist())
    vp_seleccionada = st.sidebar.selectbox("Vicepresidencia (VP)", vps)

    classifs = ["Todas"] + sorted(forecast_merged["Classif"].dropna().unique().tolist())
    classif_seleccionada = st.sidebar.selectbox("Clasificacion", classifs)

    if "CLASS" in forecast_merged.columns:
        classes = ["Todas"] + sorted(forecast_merged["CLASS"].dropna().unique().tolist())
        class_seleccionada = st.sidebar.selectbox("CLASS (Grupos)", classes)
    else:
        class_seleccionada = "Todas"

    st.sidebar.markdown("---")
    metodo_seleccionado = st.sidebar.selectbox(
        "Metodo de proyeccion",
        ["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"],
        index=["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"].index(metodo_ganador),
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Metodo optimizado actual: **{metodo_ganador}**")

    if st.sidebar.button("Re-ejecutar Modelos", use_container_width=True):
        clear_cache()
        st.session_state.modelos_ejecutados = False
        st.rerun()

    def filtrar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        if vp_seleccionada != "Todas" and "VP" in df.columns:
            df = df[df["VP"] == vp_seleccionada]
        if classif_seleccionada != "Todas" and "Classif" in df.columns:
            df = df[df["Classif"] == classif_seleccionada]
        if class_seleccionada != "Todas" and "CLASS" in df.columns:
            df = df[df["CLASS"] == class_seleccionada]
        return df

    forecast_lines_f = filtrar_dataframe(forecast_lines)
    deviation_df_f = filtrar_dataframe(deviation_df)
    agg_classif_f = filtrar_dataframe(agg_classif) if "Classif" in agg_classif.columns else agg_classif
    agg_gerencia_f = filtrar_dataframe(agg_gerencia) if "Gerencia" in agg_gerencia.columns else agg_gerencia

    if vp_seleccionada != "Todas" or classif_seleccionada != "Todas":
        kpis_f = compute_kpis(forecast_lines_f, forecast_df)
    else:
        kpis_f = kpis

    tabs = st.tabs([
        "1. Resumen Ejecutivo",
        "2. Analisis por Dimension",
        "3. Tendencia Mensual",
        "4. Forecast 5+7",
        "5. Comparaciones",
        "6. Hallazgos",
        "7. Exportar",
    ])

    with tabs[0]:
        st.title("Resumen Ejecutivo - Forecast 5+7")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Budget FY", format_currency(kpis_f["Budget_FY_Total"]))
        with col2:
            st.metric("Forecast 5+7", format_currency(kpis_f["Forecast_5plus7_Total"]), delta=f"{kpis_f['Var_vs_Budget_Pct']:+.1f}% vs Budget", delta_color="inverse")
        with col3:
            st.metric("Real YTD (Ene-May)", format_currency(kpis_f["Real_YTD_Total"]), delta=f"{kpis_f['Pct_Avance_Real']:.1f}% del Budget")
        with col4:
            oficial_val = kpis_f.get("Forecast_Oficial_Total", 0) or 0
            var_vs_oficial = kpis_f.get("Var_vs_Oficial_Pct", 0) or 0
            st.metric("Forecast Oficial", format_currency(oficial_val), delta=f"{var_vs_oficial:+.1f}% vs 5+7", delta_color="off")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Composicion por Clasificacion")
            st.plotly_chart(plot_treemap(agg_classif_f, path=["Classif"], value_col="Forecast_5+7", title="", color_col="Var_Pct"), use_container_width=True)
        with col_b:
            st.subheader("Forecast 5+7 vs Budget por VP")
            st.plotly_chart(plot_bar_comparison(agg_vp, x_col="VP", budget_col="Budget_FY", forecast_col="Forecast_5+7", title="", top_n=10), use_container_width=True)

        st.markdown("---")
        st.subheader("Waterfall: Budget FY a Forecast 5+7")
        devs = {str(row["Classif"]): row["Var_Abs"] for _, row in agg_classif_f.iterrows()}
        st.plotly_chart(plot_waterfall(kpis_f["Budget_FY_Total"], kpis_f["Forecast_5plus7_Total"], deviations=devs), use_container_width=True)

    with tabs[1]:
        st.title("Analisis por Dimension")
        dim_tabs = st.tabs(["Por VP", "Por Gerencia", "Por Classif", "Por CLASS", "Top Items"])
        with dim_tabs[0]:
            st.plotly_chart(plot_bar_comparison(agg_vp, "VP", title=""), use_container_width=True)
            st.dataframe(agg_vp[["VP", "Forecast_5+7", "Budget_FY", "Var_Abs", "Var_Pct"]].sort_values("Forecast_5+7", ascending=False), use_container_width=True, hide_index=True)
        with dim_tabs[1]:
            top_ger = agg_gerencia_f.nlargest(15, "Forecast_5+7").sort_values("Forecast_5+7")
            st.plotly_chart(plot_bar_comparison(top_ger, "Gerencia", title=""), use_container_width=True)
            st.dataframe(agg_gerencia_f.sort_values("Forecast_5+7", ascending=False), use_container_width=True, hide_index=True)
        with dim_tabs[2]:
            st.plotly_chart(plot_bar_comparison(agg_classif_f, "Classif", title=""), use_container_width=True)
            st.dataframe(agg_classif_f[["Classif", "Forecast_5+7", "Budget_FY", "Var_Abs", "Var_Pct"]].sort_values("Forecast_5+7", ascending=False), use_container_width=True, hide_index=True)
        with dim_tabs[3]:
            if "CLASS" in forecast_lines_f.columns:
                agg_class_group = aggregate_forecast(forecast_lines_f, ["CLASS"])
                st.plotly_chart(plot_bar_comparison(agg_class_group, "CLASS", title=""), use_container_width=True)
            else:
                st.info("Columna CLASS no disponible.")
        with dim_tabs[4]:
            top_dev = top_deviations(deviation_df_f, by="Var_vs_Budget_Abs", n=20)
            st.plotly_chart(plot_top_deviations(top_dev, label_col="Desc Item", deviation_col="Var_vs_Budget_Abs", pct_col="Var_vs_Budget_Pct", title="", n=20), use_container_width=True)

    with tabs[2]:
        st.title("Tendencia Mensual")
        if not forecast_lines_f.empty:
            forecast_monthly = forecast_lines_f[MONTH_COLS].sum().values
            budget_monthly = np.zeros(12)
            official_monthly = np.zeros(12)
            dim_cols_merge = ["Resp", "Desc Resp", "VP", "Gerencia", "Proc", "Desc Proc", "Item", "Desc Item", "Classif", "CC"]
            budget_for_merge = budget_df[dim_cols_merge + MONTH_COLS].rename(columns={c: c + "_b" for c in MONTH_COLS})
            forecast_for_merge = forecast_df[dim_cols_merge + MONTH_COLS].rename(columns={c: c + "_o" for c in MONTH_COLS})
            merged_m = forecast_lines_f[dim_cols_merge].merge(budget_for_merge, on=dim_cols_merge, how="inner").merge(forecast_for_merge, on=dim_cols_merge, how="inner")
            if not merged_m.empty:
                for i, col in enumerate(MONTH_COLS):
                    budget_monthly[i] = merged_m[f"{col}_b"].sum()
                    official_monthly[i] = merged_m[f"{col}_o"].sum()
            st.plotly_chart(plot_monthly_trend(forecast_monthly, budget_monthly, official_series=official_monthly, title=""), use_container_width=True)
            
            df_mensual = pd.DataFrame({
                "Mes": MONTH_NAMES,
                "Real / Proyeccion": forecast_monthly,
                "Budget Mensual": budget_monthly,
                "Forecast Oficial": official_monthly,
            })
            df_mensual["Var vs Budget"] = df_mensual["Real / Proyeccion"] - df_mensual["Budget Mensual"]
            st.dataframe(df_mensual, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay datos para mostrar.")

    with tabs[3]:
        st.title("Forecast 5+7 - Metodo y Comparacion")
        st.dataframe(resultados_backtesting.set_index("method"), use_container_width=True)
        metrica_viz = st.selectbox("Metrica", ["rmse_mean", "mape_median", "mae_mean"])
        st.plotly_chart(plot_method_comparison(resultados_backtesting, metric=metrica_viz), use_container_width=True)
        st.markdown("---")
        st.dataframe(forecast_lines_f.sort_values("Forecast_5+7", ascending=False), use_container_width=True, hide_index=True)

    with tabs[4]:
        st.title("Comparaciones")
        comp_df = compare_with_official(forecast_lines_f, group_cols=["Classif"])
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Budget_FY", forecast_col="Forecast_5plus7", title=""), use_container_width=True)
        with col_c2:
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Forecast_Oficial", forecast_col="Forecast_5plus7", title=""), use_container_width=True)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.title("Hallazgos y Propuesta de Mejora")
        st.markdown("""
        ## Principales Hallazgos

        ### 1. Ejecucion por debajo del presupuesto en la mayoria de las partidas
        El Forecast 5+7 proyecta un cierre de ano aproximadamente un 10% por debajo
        del Budget FY a nivel agregado. Esto es consistente con un patron de
        sub-ejecucion presupuestaria observado en los primeros 5 meses del ano.

        ### 2. Energia (Power) es la unica partida sobre el presupuesto
        El gasto en energia electrica muestra una ejecucion superior al budget,
        reflejando posiblemente tarifas electricas mayores o mayor consumo operacional.

        ## Propuesta de Mejora
        1. **Revision de supuestos de ejecucion**: Ajustar el factor de amortiguacion por VP.
        2. **Forecast movil mensual**: Actualizar la proyeccion cada mes incorporando el nuevo dato real.
        3. **Incorporar variables exogenas**: Precio del cobre, tipo de cambio, etc.
        """)

    with tabs[6]:
        st.title("Exportar Datos")
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            st.download_button("Descargar CSV", data=forecast_lines_f.to_csv(index=False), file_name="forecast_5plus7.csv", mime="text/csv", use_container_width=True)
        with col_x2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                forecast_lines_f.to_excel(writer, sheet_name="Forecast_5plus7", index=False)
                agg_classif_f.to_excel(writer, sheet_name="Por_Classif", index=False)
                agg_vp.to_excel(writer, sheet_name="Por_VP", index=False)
                resultados_backtesting.to_excel(writer, sheet_name="Metodos", index=False)
            st.download_button("Descargar Excel", data=output.getvalue(), file_name="forecast_5plus7.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


# ============================================================================
# ============================================================================
# MÓDULO 2: PROYECCIÓN ESTRATÉGICA 2027-2031
# ============================================================================
# ============================================================================

elif app_mode == "Proyeccion Estrategica (2027-2031)":
    st.title("Laboratorio de Proyeccion Estrategica (2027 - 2031)")
    st.markdown("Aislamiento de tendencias macro de los presupuestos historicos para generar un modelo proyectivo a 5 anos, sensible a variables macroeconomicas.")

    st.sidebar.subheader("Laboratorio de Escenarios")
    slider_fuel = st.sidebar.slider("Ajuste Precio Diesel (%)", -40.0, 40.0, 0.0) / 100.0
    slider_power = st.sidebar.slider("Ajuste Costo Energia (%)", -30.0, 30.0, 0.0) / 100.0
    slider_dolar = st.sidebar.slider("Ajuste Tipo de Cambio (%)", -30.0, 30.0, 0.0) / 100.0

    @st.cache_data(show_spinner="Calculando vectores proyectivos 2027-2031...")
    def load_strategic_budgets(path):
        b24 = pd.read_excel(path, sheet_name="BUDGET 2024 - 2028")
        b25 = pd.read_excel(path, sheet_name="BUDGET 2025 - 2029")
        b26 = pd.read_excel(path, sheet_name="BUDGET 2026 - 2030")
        return b24, b25, b26
    
    try:
        b24, b25, b26 = load_strategic_budgets(file_path)
    except Exception as e:
        st.error(f"Error cargando las hojas de Presupuestos (Budgets). Detalle: {e}")
        st.stop()

    try:
        # 1. Extraer data base principal de b26 de forma segura (ignorando si falta Desc Proc)
        base_cols = ['CC', 'VP', 'Gerencia', 'Desc Proc', 'Desc Item', 'Classif']
        cols_in_b26 = [c for c in base_cols if c in b26.columns]
        df = b26[cols_in_b26].copy()
        
        # 2. Definir meses y forzar busqueda de columnas
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        req_24 = ['CC', 'FY24', 'FY27', 'FY28'] + [f'{m}-24' for m in meses]
        req_25 = ['CC', 'FY25', 'FY27', 'FY28', 'FY29'] + [f'{m}-25' for m in meses]
        req_26 = ['CC', 'FY26', 'FY30'] + [f'{m}-26' for m in meses]

        df24 = b24[[c for c in req_24 if c in b24.columns]]
        df25 = b25[[c for c in req_25 if c in b25.columns]]
        df26 = b26[[c for c in req_26 if c in b26.columns]]

        # 3. Merges progresivos
        df = df.merge(df24, on='CC', how='left')
        df = df.merge(df25, on='CC', how='left', suffixes=('_b24', '_b25'))
        df = df.merge(df26, on='CC', how='left')
        df.fillna(0, inplace=True)

        # 4. Forzar conversion numerica en operaciones matematicas
        fy24_val = pd.to_numeric(df.get('FY24', 0), errors='coerce').fillna(0)
        fy25_val = pd.to_numeric(df.get('FY25', 0), errors='coerce').fillna(0)
        fy26_val = pd.to_numeric(df.get('FY26', 0), errors='coerce').fillna(0)
        
        fy27_b24 = pd.to_numeric(df.get('FY27_b24', 0), errors='coerce').fillna(0)
        fy27_b25 = pd.to_numeric(df.get('FY27_b25', 0), errors='coerce').fillna(0)
        
        fy28_b24 = pd.to_numeric(df.get('FY28_b24', 0), errors='coerce').fillna(0)
        fy28_b25 = pd.to_numeric(df.get('FY28_b25', 0), errors='coerce').fillna(0)
        
        fy29_val = pd.to_numeric(df.get('FY29', 0), errors='coerce').fillna(0)
        fy30_val = pd.to_numeric(df.get('FY30', 0), errors='coerce').fillna(0)

        tasa_crecimiento = ((fy25_val + 1e-6) / (fy24_val + 1e-6)).clip(0.9, 1.1)
        
        df['Proj_FY27'] = ((fy27_b24 + fy27_b25) / 2.0) * tasa_crecimiento
        df['Proj_FY28'] = ((fy28_b24 + fy28_b25) / 2.0) * tasa_crecimiento
        df['Proj_FY29'] = fy29_val * tasa_crecimiento
        df['Proj_FY30'] = fy30_val * tasa_crecimiento
        
        df['Proj_FY31'] = df['Proj_FY30'] * ((df['Proj_FY30'] + 1e-6) / (df['Proj_FY27'] + 1e-6)) ** (1/3)
        df['Proj_FY31'] = df['Proj_FY31'].fillna(df['Proj_FY30']).clip(df['Proj_FY30'] * 0.95, df['Proj_FY30'] * 1.05)

        # 5. Aplicar sensibilidades
        def factor_sens(row):
            desc = str(row.get('Desc Item', '')).lower()
            f = 1.0
            if any(p in desc for p in ['diesel', 'petroleo', 'combustible']): f += slider_fuel
            if any(p in desc for p in ['energia', 'electrica', 'power']): f += slider_power
            if any(p in desc for p in ['contrato', 'repuesto', 'spare']): f += slider_dolar
            return f

        df['Factor_Sensibilidad'] = df.apply(factor_sens, axis=1)

        anios_proy = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']
        for a in anios_proy: 
            df[f'Final_{a}'] = df[f'Proj_{a}'] * df['Factor_Sensibilidad']

        # 6. Mensualizacion
        for m in meses:
            m24 = pd.to_numeric(df.get(f'{m}-24', 0), errors='coerce').fillna(0)
            m25 = pd.to_numeric(df.get(f'{m}-25', 0), errors='coerce').fillna(0)
            m26 = pd.to_numeric(df.get(f'{m}-26', 0), errors='coerce').fillna(0)
            
            peso = ((m24 / (fy24_val + 1e-6)) + (m25 / (fy25_val + 1e-6)) + (m26 / (fy26_val + 1e-6))) / 3.0
            df[f'{m}-27'] = df['Final_FY27'] * peso

        cols_final_base = ['CC', 'VP', 'Gerencia', 'Desc Item', 'Classif']
        cols_final = [c for c in cols_final_base if c in df.columns] + [f'{m}-27' for m in meses] + [f'Final_{a}' for a in anios_proy]
        df_f = df[cols_final].copy()

    except Exception as e:
        st.error(f"Error procesando la data para la proyeccion. Verifica la estructura de las columnas. Detalle tecnico: {e}")
        st.stop()

    # --- INDICADORES ---
    total_fy27_base = df['Proj_FY27'].sum()
    total_fy27_final = df['Final_FY27'].sum()
    impacto_sliders = total_fy27_final - total_fy27_base
    total_fy31_final = df['Final_FY31'].sum()
    cagr = ((total_fy31_final / (total_fy27_final + 1e-6)) ** (1/4) - 1) * 100 if total_fy27_final > 0 else 0

    st.markdown("### Tarjetas de Impacto Financiero")
    kp1, kp2, kp3 = st.columns(3)
    kp1.metric("Gasto Proyectado (Ano 2027)", format_currency(total_fy27_final), delta=f"Impacto Sliders: {format_currency(impacto_sliders, abs_val=False)}", delta_color="inverse")
    kp2.metric("Gasto Proyectado Final (Ano 2031)", format_currency(total_fy31_final))
    kp3.metric("CAGR (Tasa de Crecimiento Anual)", f"{cagr:.2f}%", delta="Aceleracion de OPEX a largo plazo", delta_color="off")

    st.markdown("---")

    # --- GRAFICOS ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Estacionalidad: 2026 vs Proyeccion 2027")
        totales_26 = [pd.to_numeric(df.get(f'{m}-26', 0), errors='coerce').sum() / 1e6 for m in meses]
        totales_27 = [df_f[f'{m}-27'].sum() / 1e6 for m in meses]
        
        df_mensual_comp = pd.DataFrame({
            "Mes": meses * 2,
            "MUSD": totales_26 + totales_27,
            "Ano": ["2026 (Base)"] * 12 + ["2027 (Proyectado)"] * 12
        })
        
        fig_mensual = px.line(df_mensual_comp, x="Mes", y="MUSD", color="Ano", markers=True, color_discrete_sequence=['#ff7f0e', '#1f77b4'])
        st.plotly_chart(fig_mensual, use_container_width=True)

    with col_chart2:
        st.subheader("Evolucion Quinquenal por Clasificacion")
        if 'Classif' in df_f.columns:
            df_anios = df_f[['Classif'] + [f'Final_{a}' for a in anios_proy]].copy()
            df_melted = df_anios.melt(id_vars=['Classif'], value_vars=[f'Final_{a}' for a in anios_proy], var_name='Ano', value_name='MUSD')
            df_melted['Ano'] = df_melted['Ano'].str.replace('Final_FY', '20')
            df_melted['MUSD'] = df_melted['MUSD'] / 1e6
            
            df_agrupado = df_melted.groupby(['Ano', 'Classif'])['MUSD'].sum().reset_index()
            fig_apilado = px.bar(df_agrupado, x="Ano", y="MUSD", color="Classif", text_auto='.1f', color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_apilado, use_container_width=True)
        else:
            st.warning("Columna de clasificacion no encontrada para graficar la evolucion.")

    st.markdown("---")
    st.subheader("Centro de Exportacion de Escenarios (Data Linea a Linea)")
    st.dataframe(df_f.head(100), use_container_width=True)
    
    from io import BytesIO
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w: 
        df_f.to_excel(w, index=False)
    
    st.download_button(
        label="Descargar Modelo Estrategico (2027-2031) en Excel", 
        data=out.getvalue(), 
        file_name="Modelo_Estrategico_2027_2031.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
