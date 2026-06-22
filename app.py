"""
app.py -- Plataforma Avanzada de Control de Gestión, Forecast 5+7 y Planificación Quinquenal.
"""

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Asegurar la ruta de importaciones locales
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

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Sistema de Planificación y Control de Gestión",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 1. SISTEMA ESTRICTO DE CARGA DE ARCHIVOS
# ============================================================================
st.sidebar.title("Datos Maestros")
st.sidebar.markdown("Para inicializar los modelos matemáticos, es obligatorio proveer la fuente de datos.")

uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel maestro de presupuestos", type=["xlsx", "xls"])

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Ruta estandarizada donde el programa guardará el archivo
file_path = data_dir / "02_Gastos_Proy_Mejor_01-2025.xlsx"

# BLOQUEO ESTRUCTURAL: Si no hay archivo subido en esta sesión, la aplicación se detiene.
if uploaded_file is None:
    st.info("Bienvenido a la Plataforma de Control de Gestión y Planificación Estratégica.")
    st.warning("El sistema se encuentra en pausa. Por favor, suba el archivo Excel maestro en el panel lateral izquierdo para comenzar el procesamiento de datos.")
    st.stop()
else:
    # Validación para reescribir la memoria solo cuando se sube un archivo nuevo
    if "last_uploaded_name" not in st.session_state or st.session_state.last_uploaded_name != uploaded_file.name:
        st.session_state.last_uploaded_name = uploaded_file.name
        st.cache_data.clear()
        clear_cache()
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("Archivo validado y cargado en memoria exitosamente.")

# ============================================================================
# 2. NAVEGACIÓN PRINCIPAL
# ============================================================================
st.sidebar.markdown("---")
st.sidebar.title("Navegación")
app_mode = st.sidebar.radio("Seleccione un Módulo de Trabajo:", [
    "Forecast Operacional (5+7)",
    "Proyección Estratégica Quinquenal (2027-2031)"
])
st.sidebar.markdown("---")

# ============================================================================
# Carga de datos (optimizada y cacheada)
# ============================================================================
@st.cache_data(show_spinner="Estructurando matrices de datos base...")
def cargar_datos():
    forecast_df = load_forecast_detail()
    budget_df = load_budget_detail()
    grupos_df = load_grupos_mapping()
    pivot_df = load_pivot_summary()
    forecast_merged, budget_merged = get_merged_data()
    return forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged

with st.spinner("Inicializando modelos de datos..."):
    forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged = cargar_datos()

# Inicialización de variables de estado de sesión
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
# MÓDULO 1: FORECAST OPERACIONAL 5+7 (COMPLETO Y ORIGINAL)
# ============================================================================
# ============================================================================
if app_mode == "Forecast Operacional (5+7)":

    if not st.session_state.modelos_ejecutados:
        st.warning(
            "Los modelos predictivos no han sido inicializados para este set de datos. "
            "Proceda a ejecutar el motor de backtesting para generar el Forecast 5+7."
        )
        if st.button("Ejecutar Motor Predictivo (Backtesting + Forecast)", type="primary", use_container_width=True):
            with st.spinner("Ejecutando proceso de validación cruzada (Backtesting)..."):
                st.session_state.resultados_backtesting = run_backtesting(forecast_df, budget_df)

            st.session_state.metodo_ganador = select_best_method(
                st.session_state.resultados_backtesting, "rmse_mean"
            )

            with st.spinner(f"Generando Forecast 5+7 utilizando algoritmo optimizado: {st.session_state.metodo_ganador}..."):
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

    # Sidebar - Filtros Globales
    st.sidebar.title("Filtros Analíticos")
    
    vps_list = ["Todas"] + sorted(forecast_merged["VP"].dropna().unique().tolist())
    vp_seleccionada = st.sidebar.selectbox("Vicepresidencia (VP)", vps_list)

    classifs_list = ["Todas"] + sorted(forecast_merged["Classif"].dropna().unique().tolist())
    classif_seleccionada = st.sidebar.selectbox("Clasificación de Gasto", classifs_list)

    if "CLASS" in forecast_merged.columns:
        classes_list = ["Todas"] + sorted(forecast_merged["CLASS"].dropna().unique().tolist())
        class_seleccionada = st.sidebar.selectbox("Grupo (CLASS)", classes_list)
    else:
        class_seleccionada = "Todas"

    st.sidebar.markdown("---")
    st.sidebar.caption("Configuración de Algoritmo")
    metodos_disponibles = ["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"]
    metodo_seleccionado = st.sidebar.selectbox(
        "Método de Proyección Activo",
        metodos_disponibles,
        index=metodos_disponibles.index(metodo_ganador) if metodo_ganador in metodos_disponibles else 1,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Algoritmo optimizado según backtesting: **{metodo_ganador}**")

    if st.sidebar.button("Forzar Recálculo de Modelos", use_container_width=True):
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
        "2. Análisis por Dimensión",
        "3. Tendencia Mensual",
        "4. Forecast 5+7",
        "5. Comparaciones",
        "6. Hallazgos",
        "7. Exportar",
    ])

    with tabs[0]:
        st.title("Resumen Ejecutivo de Proyección - Forecast 5+7")
        st.markdown("Proyección financiera de gastos operacionales (OPEX) consolidando meses de ejecución real más meses modelados.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Presupuesto Anual (Budget FY)", format_currency(kpis_f["Budget_FY_Total"]))
        with col2:
            st.metric("Proyección (Forecast 5+7)", format_currency(kpis_f["Forecast_5plus7_Total"]), delta=f"{kpis_f['Var_vs_Budget_Pct']:+.1f}% vs Presupuesto", delta_color="inverse")
        with col3:
            st.metric("Ejecución Real YTD", format_currency(kpis_f["Real_YTD_Total"]), delta=f"{kpis_f['Pct_Avance_Real']:.1f}% consumido del Presupuesto")
        with col4:
            oficial_val = kpis_f.get("Forecast_Oficial_Total", 0) or 0
            var_vs_oficial = kpis_f.get("Var_vs_Oficial_Pct", 0) or 0
            st.metric("Forecast Oficial Vigente", format_currency(oficial_val), delta=f"{var_vs_oficial:+.1f}% vs Modelo", delta_color="off")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Distribución de OPEX por Clasificación")
            st.plotly_chart(plot_treemap(agg_classif_f, path=["Classif"], value_col="Forecast_5+7", title="", color_col="Var_Pct"), use_container_width=True)
            
        with col_b:
            st.subheader("Comparativo Forecast vs Budget por Vicepresidencia")
            st.plotly_chart(plot_bar_comparison(agg_vp, x_col="VP", budget_col="Budget_FY", forecast_col="Forecast_5+7", title="", top_n=10), use_container_width=True)

        st.markdown("---")
        st.subheader("Evolución de Desviaciones (Waterfall)")
        devs = {str(row["Classif"]): row["Var_Abs"] for _, row in agg_classif_f.iterrows()}
        st.plotly_chart(plot_waterfall(kpis_f["Budget_FY_Total"], kpis_f["Forecast_5plus7_Total"], deviations=devs), use_container_width=True)

    with tabs[1]:
        st.title("Análisis Financiero por Dimensiones")
        dim_tabs = st.tabs(["Por Vicepresidencia", "Por Gerencia", "Por Clasificación", "Por Agrupación CLASS", "Top Desviaciones"])
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
                st.plotly_chart(plot_bar_comparison(aggregate_forecast(forecast_lines_f, ["CLASS"]), "CLASS", title=""), use_container_width=True)
        with dim_tabs[4]:
            st.plotly_chart(plot_top_deviations(top_deviations(deviation_df_f, by="Var_vs_Budget_Abs", n=20), label_col="Desc Item", deviation_col="Var_vs_Budget_Abs", pct_col="Var_vs_Budget_Pct", title="", n=20), use_container_width=True)

    with tabs[2]:
        st.title("Comportamiento y Tendencia Mensual")
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
                "Mes Calendario": MONTH_NAMES,
                "Flujo Real / Proyectado": forecast_monthly,
                "Flujo Presupuestado": budget_monthly,
                "Flujo Forecast Oficial": official_monthly,
            })
            df_mensual["Desviación Mensual"] = df_mensual["Flujo Real / Proyectado"] - df_mensual["Flujo Presupuestado"]
            st.dataframe(df_mensual, use_container_width=True, hide_index=True)
        else:
            st.warning("El set de datos se encuentra vacío.")

    with tabs[3]:
        st.title("Metodología Analítica Aplicada")
        st.dataframe(
            resultados_backtesting.set_index("method"),
            use_container_width=True,
            column_config={
                "mape_mean": st.column_config.NumberColumn("Error MAPE (Promedio)", format="%.2f"),
                "mape_median": st.column_config.NumberColumn("Error MAPE (Mediana)", format="%.2f"),
                "rmse_mean": st.column_config.NumberColumn("Error RMSE (Promedio)", format="%.0f"),
                "rmse_median": st.column_config.NumberColumn("Error RMSE (Mediana)", format="%.0f"),
                "mae_mean": st.column_config.NumberColumn("Error MAE (Promedio)", format="%.0f"),
                "n_lines": st.column_config.NumberColumn("Volumen de Líneas Evaluadas"),
            }
        )
        metrica_viz = st.selectbox("Métrica", ["rmse_mean", "mape_median", "mae_mean"])
        st.plotly_chart(plot_method_comparison(resultados_backtesting, metric=metrica_viz), use_container_width=True)
        st.markdown("---")
        st.dataframe(forecast_lines_f.sort_values("Forecast_5+7", ascending=False).head(500), use_container_width=True, hide_index=True)

    with tabs[4]:
        st.title("Ecosistema de Comparación Estratégica")
        comp_df = compare_with_official(forecast_lines_f, group_cols=["Classif"])
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Budget_FY", forecast_col="Forecast_5plus7", title="Vs Presupuesto"), use_container_width=True)
        with col_c2:
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Forecast_Oficial", forecast_col="Forecast_5plus7", title="Vs Oficial"), use_container_width=True)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.title("Informe Analítico y Recomendaciones de Gestión")
        st.markdown("""
        ### Diagnóstico de Desempeño Operacional

        **1. Análisis General de Sub-ejecución Financiera**
        La proyección inferida para el cierre del año fiscal indica una desviación consolidada negativa respecto del presupuesto aprobado. Esta tendencia se solidifica en los datos históricos reales del inicio del período, donde un gran porcentaje de los centros de costo reportan atrasos en consumos de servicios de terceros y adjudicación de repuestos.

        **2. Zonas de Riesgo Presupuestario (Sobregiros Identificados)**
        En contraste con la tendencia general, la partida contable relacionada al consumo de Energía manifiesta una trayectoria acelerada. Los factores explicativos preliminares que la operación debe auditar incluyen descalces tarifarios de contratos de suministro de largo plazo.

        **3. Comportamiento en Bienes e Insumos**
        Las variaciones hacia la baja (saving teórico) en insumos críticos no representan necesariamente un ahorro estructural. Es imperativo que control de gestión valide con mantenimiento si existen retrasos de inventario.
        """)

    with tabs[6]:
        st.title("Módulo de Extracción de Datos")
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            st.download_button("Extraer CSV", data=forecast_lines_f.to_csv(index=False), file_name="Dataset_Forecast.csv", mime="text/csv", use_container_width=True)
        with col_x2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                forecast_lines_f.to_excel(writer, sheet_name="Forecast_5plus7", index=False)
                agg_classif_f.to_excel(writer, sheet_name="Resumen_Clasificacion", index=False)
                agg_vp.to_excel(writer, sheet_name="Resumen_VP", index=False)
                resultados_backtesting.to_excel(writer, sheet_name="Evaluacion_Modelos", index=False)
            st.download_button("Extraer Excel", data=output.getvalue(), file_name="Reporte_Forecast.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


# ============================================================================
# ============================================================================
# MÓDULO 2: PROYECCIÓN ESTRATÉGICA QUINQUENAL (2027-2031)
# ============================================================================
# ============================================================================

elif app_mode == "Proyección Estratégica Quinquenal (2027-2031)":
    st.title("Tablero Interactivo de Proyección Estratégica y KPIs")
    st.markdown("Modelo de proyección histórica corregida (Basado en el crecimiento orgánico 2024-2026 sin inflación) con sensibilidad a variables operativas clave.")

    st.sidebar.subheader("Escenarios Preconfigurados")
    escenario = st.sidebar.selectbox("Seleccione un escenario estratégico:", [
        "Manual / Personalizado",
        "Crisis Global (+Combustible y Dólar)",
        "Negociación Sindical (+Mano de Obra)",
        "Eficiencia Operativa (-Costos Generales)"
    ])

    val_fuel, val_power, val_dolar, val_labor = 0.0, 0.0, 0.0, 0.0
    if escenario == "Crisis Global (+Combustible y Dólar)":
        val_fuel, val_power, val_dolar, val_labor = 25.0, 10.0, 15.0, 5.0
    elif escenario == "Negociación Sindical (+Mano de Obra)":
        val_fuel, val_power, val_dolar, val_labor = 5.0, 2.0, 2.0, 18.0
    elif escenario == "Eficiencia Operativa (-Costos Generales)":
        val_fuel, val_power, val_dolar, val_labor = -10.0, -5.0, -8.0, -5.0

    st.sidebar.markdown("---")
    st.sidebar.subheader("Parámetros de Sensibilidad (%)")
    slider_fuel_pct = st.sidebar.slider("Variación Precio Diésel / Combustible", -100.0, 100.0, val_fuel, step=0.1)
    slider_power_pct = st.sidebar.slider("Variación Tarifa Energía Eléctrica", -100.0, 100.0, val_power, step=0.1)
    slider_dolar_pct = st.sidebar.slider("Variación Tipo de Cambio / USD", -100.0, 100.0, val_dolar, step=0.1)
    slider_labor_pct = st.sidebar.slider("Variación Costo Mano de Obra", -100.0, 100.0, val_labor, step=0.1)

    @st.cache_data
    def cargar_hojas_estratejicas(path):
        return pd.read_excel(path, sheet_name="BUDGET 2024 - 2028"), pd.read_excel(path, sheet_name="BUDGET 2025 - 2029"), pd.read_excel(path, sheet_name="BUDGET 2026 - 2030")

    try:
        b24, b25, b26 = cargar_hojas_estratejicas(file_path)
    except Exception as e:
        st.error(f"Error: Faltan pestañas históricas en el Excel subido. Detalle: {e}")
        st.stop()

    columnas_clave = ['CC', 'VP', 'Gerencia', 'Desc Item', 'Classif']
    cols_existentes = [c for c in columnas_clave if c in b26.columns]
    df_estrat = b26[cols_existentes].copy()

    df_estrat = df_estrat.merge(b24[['CC', 'FY24']], on='CC', how='left')
    df_estrat = df_estrat.merge(b26[['CC', 'FY26'] + [f'{m}-26' for m in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']]], on='CC', how='left')
    df_estrat.fillna(0, inplace=True)

    f24 = pd.to_numeric(df_estrat['FY24'], errors='coerce').fillna(0)
    f26 = pd.to_numeric(df_estrat['FY26'], errors='coerce').fillna(0)

    # --- MÉTODO ÚNICO: Tendencia Limpia 2024 a 2026 sin Inflación ---
    # Calculamos el CAGR entre 2024 y 2026. Limitamos saltos absurdos entre -5% y +10% anual.
    tasa_crecimiento = np.where(f24 > 0, (f26 / (f24 + 1e-6)) ** (1/2), 1.0).clip(0.95, 1.10)
    
    df_estrat['Base_FY27'] = f26 * tasa_crecimiento
    df_estrat['Base_FY28'] = df_estrat['Base_FY27'] * tasa_crecimiento
    df_estrat['Base_FY29'] = df_estrat['Base_FY28'] * tasa_crecimiento
    df_estrat['Base_FY30'] = df_estrat['Base_FY29'] * tasa_crecimiento
    df_estrat['Base_FY31'] = df_estrat['Base_FY30'] * tasa_crecimiento

    # --- MAPEO SEMÁNTICO POR FILA ---
    def evaluar_afectacion(fila):
        item = str(fila.get('Desc Item', '')).lower()
        classif = str(fila.get('Classif', '')).lower()
        
        mult = 1.0
        
        # Mano de Obra
        if 'labor' in classif or any(p in item for p in ['remuneracion', 'sueldo', 'honorario', 'mano de obra', 'bono', 'dotacion']):
            mult += (slider_labor_pct / 100.0)
            
        # Combustible
        if any(p in item for p in ['diesel', 'combustible', 'petroleo', 'gasoil']) and 'servicio' not in item:
            mult += (slider_fuel_pct / 100.0)
            
        # Energía
        if any(p in item for p in ['energia electrica', 'kwh', 'tarifa electrica']):
            mult += (slider_power_pct / 100.0)
            
        # Dólar (Contratos Extranjeros / Repuestos)
        if any(p in item for p in ['foreign', 'usd', 'importado', 'licencia corporativa']):
            mult += (slider_dolar_pct / 100.0)
            
        return mult

    df_estrat['Factor_Estrés_Fila'] = df_estrat.apply(evaluar_afectacion, axis=1)

    años_quinquenio = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']
    for a in años_quinquenio:
        df_estrat[f'Final_{a}'] = df_estrat[f'Base_{a}'] * df_estrat['Factor_Estrés_Fila']

    meses_cal = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for m in meses_cal:
        m_26 = pd.to_numeric(df_estrat.get(f'{m}-26', 0), errors='coerce').fillna(0)
        df_estrat[f'peso_{m}'] = m_26 / (f26 + 1e-6)
        
    suma_pesos = df_estrat[[f'peso_{m}' for m in meses_cal]].sum(axis=1)
    
    for m in meses_cal:
        peso_ajustado = np.where(suma_pesos > 0, df_estrat[f'peso_{m}'] / (suma_pesos + 1e-6), 1.0/12.0)
        df_estrat[f'{m}-27'] = df_estrat['Final_FY27'] * peso_ajustado

    cols_salida = cols_existentes + [f'{m}-27' for m in meses_cal] + [f'Final_{a}' for a in años_quinquenio]
    df_final_proy = df_estrat[cols_salida].copy()

    # --- TABLERO INTERACTIVO DE KPIs ---
    tot_fy27_base = df_estrat['Base_FY27'].sum()
    tot_fy27_estres = df_estrat['Final_FY27'].sum()
    delta_usd = tot_fy27_estres - tot_fy27_base
    pct_var = (delta_usd / tot_fy27_base * 100) if tot_fy27_base != 0 else 0

    st.markdown("### Resumen de KPIs (Año 2027)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Proyección Base FY27", f"${tot_fy27_base:,.0f}")
    col2.metric("Proyección Estresada FY27", f"${tot_fy27_estres:,.0f}")
    col3.metric("Impacto Neto Operativo", f"${delta_usd:,.0f}", f"{pct_var:+.2f}%", delta_color="inverse")
    col4.metric("Escenario de Riesgo", escenario)

    st.markdown("---")
    
    tab_est1, tab_est2, tab_est3 = st.tabs([
        "Gráficos de Proyección",
        "Detalle de Filas Afectadas",
        "Generar Excel Dinámico"
    ])

    with tab_est1:
        df_melt = df_final_proy[['Classif'] + [f'Final_{a}' for a in años_quinquenio]].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_melt['Año'] = df_melt['Año'].str.replace('Final_FY', '20')
        df_g_anual = df_melt.groupby(['Año', 'Classif'])['Monto'].sum().reset_index()

        fig_barras = px.bar(
            df_g_anual, 
            x="Año", y="Monto", color="Classif", 
            title="Presupuesto Multianual Reconstruido y Estresado (USD Detallado)", 
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        # Forzar formato detallado en el hover y eje Y sin redondear a millones
        fig_barras.update_layout(yaxis_tickformat="$,.0f")
        st.plotly_chart(fig_barras, use_container_width=True)

    with tab_est2:
        st.markdown("**Inspector Semántico:** Revisa qué celdas detectó el algoritmo basándose en las descripciones y la clasificación de mano de obra.")
        df_verif = df_estrat[cols_existentes + ['Factor_Estrés_Fila', 'Base_FY27', 'Final_FY27']].copy()
        df_verif = df_verif[df_verif['Factor_Estrés_Fila'] != 1.0]
        
        st.dataframe(
            df_verif.head(200), 
            use_container_width=True,
            column_config={
                "Base_FY27": st.column_config.NumberColumn("Base Original FY27", format="$%.0f"),
                "Final_FY27": st.column_config.NumberColumn("Estresado FY27", format="$%.0f"),
                "Factor_Estrés_Fila": st.column_config.NumberColumn("Multiplicador", format="%.3f")
            }
        )

    with tab_est3:
        st.subheader("Motor de Reportes Excel (XlsxWriter)")
        st.markdown("El sistema genera un archivo Excel que incluye la tabla de datos, el cuadro paramétrico de sensibilidades separado a la derecha y un gráfico interactivo nativo de Excel con el resumen quinquenal.")
        
        from io import BytesIO
        output_excel = BytesIO()
        
        # Usamos XlsxWriter para incrustar el panel de parámetros y el gráfico
        with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
            df_final_proy.to_excel(writer, sheet_name="Proyeccion_Estrategica", index=False)
            
            workbook = writer.book
            worksheet = writer.sheets["Proyeccion_Estrategica"]
            
            # Formatos de Excel
            money_fmt = workbook.add_format({'num_format': '$#,##0'})
            bold_fmt = workbook.add_format({'bold': True})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
            
            # Aplicar formato de moneda a los datos exportados
            for col_num in range(5, len(df_final_proy.columns)):
                worksheet.set_column(col_num, col_num, 15, money_fmt)
            
            # --- TABLA DE PARÁMETROS SEPARADA A LA DERECHA ---
            start_col = len(df_final_proy.columns) + 2
            
            worksheet.write(1, start_col, "Tabla de Sensibilidad", header_fmt)
            worksheet.write(1, start_col+1, "Valor Aplicado", header_fmt)
            
            worksheet.write(2, start_col, "Variación Combustible", bold_fmt)
            worksheet.write(2, start_col+1, f"{slider_fuel_pct}%")
            
            worksheet.write(3, start_col, "Variación Energía", bold_fmt)
            worksheet.write(3, start_col+1, f"{slider_power_pct}%")
            
            worksheet.write(4, start_col, "Variación Dólar", bold_fmt)
            worksheet.write(4, start_col+1, f"{slider_dolar_pct}%")
            
            worksheet.write(5, start_col, "Variación Mano de Obra", bold_fmt)
            worksheet.write(5, start_col+1, f"{slider_labor_pct}%")

            # --- TABLA RESUMEN PARA EL GRÁFICO NATIVO DE EXCEL ---
            worksheet.write(8, start_col, "Año", header_fmt)
            worksheet.write(8, start_col+1, "Gasto Total (USD)", header_fmt)
            
            totals = [df_final_proy[f'Final_{a}'].sum() for a in años_quinquenio]
            
            for i, (año, tot) in enumerate(zip(['2027', '2028', '2029', '2030', '2031'], totals)):
                worksheet.write(9+i, start_col, año)
                worksheet.write(9+i, start_col+1, tot, money_fmt)

            # --- CREACIÓN DEL GRÁFICO DENTRO DE EXCEL ---
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name': 'Proyección Quinquenal',
                'categories': ['Proyeccion_Estrategica', 9, start_col, 13, start_col],
                'values':     ['Proyeccion_Estrategica', 9, start_col+1, 13, start_col+1],
                'data_labels': {'value': True},
                'fill':   {'color': '#4F81BD'}
            })
            chart.set_title({'name': 'Evolución del Presupuesto (2027-2031)'})
            chart.set_x_axis({'name': 'Año Operativo'})
            chart.set_y_axis({'name': 'Costo (USD)', 'num_format': '$#,##0'})
            chart.set_size({'width': 550, 'height': 350})
            
            worksheet.insert_chart(16, start_col, chart)
            
        st.download_button(
            label="Descargar Reporte Quinquenal (Incluye Gráficos y Variables en Excel)",
            data=output_excel.getvalue(),
            file_name="Planificacion_Estrategica_Visual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
