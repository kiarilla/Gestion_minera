"""
app.py -- Plataforma Definitiva de Control de Gestión, Forecast 5+7 y Planificación Quinquenal.
Versión Completa Enterprise Pro - Integración Total de Modelos Matemáticos y Análisis de Sensibilidad Estratégica.
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Asegurar la ruta de importaciones de módulos del ecosistema local
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

# Configuración estructural de interfaz Streamlit de alta densidad corporativa
st.set_page_config(
    page_title="Forecast 5+7 & Planificación Estratégica - Control de Gestión",
    page_icon="⛏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# PALETA DE COLORES CORPORATIVA UNIFICADA Y CONSTANTES VISUALES
# ============================================================================
CORPORATE_PALETTE = ["#1F4E79", "#2E75B6", "#5B9BD5", "#8FAADC", "#D9E1F2", "#4472C4", "#A5A5A5", "#ED7D31"]
STRESS_LINE_COLOR = "#C00000"
BASE_LINE_COLOR = "#7F7F7F"

# Constantes de Meses y Mapeos Estructurales
MESES_ESTRAT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
AÑOS_QUINQUENIO = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']

# ============================================================================
# 1. CONTROLADOR DE FLUJO Y CARGA DE DATOS MAESTROS
# ============================================================================
st.sidebar.title("📁 Datos Maestros")
st.sidebar.markdown("Para inicializar las matrices de cálculo del Forecast y Quinquenal, provea el archivo base.")

uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel maestro de presupuestos", type=["xlsx", "xls"])

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
file_path = data_dir / "02_Gastos_Proy_Mejor_01-2025.xlsx"

if uploaded_file is None:
    st.info("👋 ¡Bienvenido a la Suite de Inteligencia de Negocios y Planificación Financiera!")
    st.warning("⚠️ Sistema en espera. Por favor, cargue el archivo maestro `.xlsx` en el panel izquierdo para desplegar las simulaciones.")
    st.stop()
else:
    if "last_uploaded_name" not in st.session_state or st.session_state.last_uploaded_name != uploaded_file.name:
        st.session_state.last_uploaded_name = uploaded_file.name
        st.cache_data.clear()
        clear_cache()
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ Archivo maestro validado y mapeado con éxito.")

# ============================================================================
# 2. ENTRADAS DE CONTROL PRINCIPAL Y FILTROS GLOBALES DE DISEÑO
# ============================================================================
st.sidebar.markdown("---")
st.sidebar.title("🧭 Módulo Operativo")
app_mode = st.sidebar.radio("Seleccione el entorno de análisis:", [
    "📊 Forecast Operacional (5+7)",
    "📈 Proyección Estratégica (2027-2031)"
])
st.sidebar.markdown("---")

# Carga e inicialización optimizada de memoria intermedia (Caché)
@st.cache_data(show_spinner="Estructurando matrices de datos base...")
def cargar_datos_base():
    forecast_df = load_forecast_detail()
    budget_df = load_budget_detail()
    grupos_df = load_grupos_mapping()
    pivot_df = load_pivot_summary()
    forecast_merged, budget_merged = get_merged_data()
    return forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged

with st.spinner("Conectando con el motor de datos..."):
    forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged = cargar_datos_base()

# Control de inicialización de los estados de sesión de Streamlit
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

# Carga automática de modelos si existen registros en el disco local
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
# ENTREGABLE MÓDULO 1: ENTORNO FORECAST OPERACIONAL (5+7)
# ============================================================================
if app_mode == "📊 Forecast Operacional (5+7)":
    
    if not st.session_state.modelos_ejecutados:
        st.subheader("⚙️ Inicialización de Algoritmos Predictivos")
        st.markdown(
            "El sistema no registra modelos entrenados para el Forecast 5+7 actual. "
            "Presione el botón inferior para disparar el cálculo matricial distributivo."
        )
        if st.button("Ejecutar Modelos Matemáticos (Backtesting + Proyección)", type="primary", use_container_width=True):
            with st.spinner("Fase 1: Ejecutando Backtesting Multi-método sobre datos históricos (~60s)..."):
                st.session_state.resultados_backtesting = run_backtesting(forecast_df, budget_df)

            st.session_state.metodo_ganador = select_best_method(
                st.session_state.resultados_backtesting, "rmse_mean"
            )

            with st.spinner(f"Fase 2: Proyectando Forecast 5+7 óptimo vía [{st.session_state.metodo_ganador}]..."):
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

    # Recuperación de objetos del estado de sesión
    resultados_backtesting = st.session_state.resultados_backtesting
    forecast_lines = st.session_state.forecast_lines
    metodo_ganador = st.session_state.metodo_ganador
    kpis = st.session_state.kpis

    # Métricas de Desviación analítica general
    deviation_df = compute_deviations(forecast_lines, compare_vs_official=True)
    agg_vp = aggregate_forecast(forecast_lines, ["VP"])
    agg_classif = aggregate_forecast(forecast_lines, ["Classif"])
    agg_gerencia = aggregate_forecast(forecast_lines, ["Gerencia"])

    # Controles de segmentación en barra lateral operativa
    st.sidebar.title("🔍 Segmentación Operativa")
    st.sidebar.markdown("---")

    vps = ["Todas"] + sorted(forecast_merged["VP"].dropna().unique().tolist())
    vp_seleccionada = st.sidebar.selectbox("Vicepresidencia Responsable (VP)", vps)

    classifs = ["Todas"] + sorted(forecast_merged["Classif"].dropna().unique().tolist())
    classif_seleccionada = st.sidebar.selectbox("Clasificación Contable", classifs)

    if "CLASS" in forecast_merged.columns:
        classes = ["Todas"] + sorted(forecast_merged["CLASS"].dropna().unique().tolist())
        class_seleccionada = st.sidebar.selectbox("Agrupador Corporativo (CLASS)", classes)
    else:
        class_seleccionada = "Todas"

    st.sidebar.markdown("---")
    metodo_seleccionado = st.sidebar.selectbox(
        "Alternar Algoritmo Predictivo",
        ["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"],
        index=["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"].index(metodo_ganador),
    )

    if metodo_seleccionado != metodo_ganador:
        with st.spinner(f"Recalculando matriz operacional mediante método alternativo [{metodo_seleccionado}]..."):
            forecast_lines = project_full_forecast(forecast_df, budget_df, method=metodo_seleccionado)
            deviation_df = compute_deviations(forecast_lines, compare_vs_official=True)
            agg_vp = aggregate_forecast(forecast_lines, ["VP"])
            agg_classif = aggregate_forecast(forecast_lines, ["Classif"])
            agg_gerencia = aggregate_forecast(forecast_lines, ["Gerencia"])
            kpis = compute_kpis(forecast_lines, forecast_df)
            st.session_state.forecast_lines = forecast_lines
            st.session_state.metodo_ganador = metodo_seleccionado
            st.session_state.kpis = kpis

    if st.sidebar.button("Forzar Recálculo General"):
        clear_cache()
        st.session_state.modelos_ejecutados = False
        st.rerun()

    # Función interna de filtrado transaccional
    def filtrar_matriz_operativa(df: pd.DataFrame) -> pd.DataFrame:
        if vp_seleccionada != "Todas" and "VP" in df.columns:
            df = df[df["VP"] == vp_seleccionada]
        if classif_seleccionada != "Todas" and "Classif" in df.columns:
            df = df[df["Classif"] == classif_seleccionada]
        if class_seleccionada != "Todas" and "CLASS" in df.columns:
            df = df[df["CLASS"] == class_seleccionada]
        return df

    forecast_lines_f = filtrar_matriz_operativa(forecast_lines)
    deviation_df_f = filtrar_matriz_operativa(deviation_df)
    agg_vp_f = filtrar_matriz_operativa(agg_vp)
    agg_classif_f = filtrar_matriz_operativa(agg_classif)
    agg_gerencia_f = filtrar_matriz_operativa(agg_gerencia)

    kpis_f = compute_kpis(forecast_lines_f, forecast_df) if (vp_seleccionada != "Todas" or classif_seleccionada != "Todas" or class_seleccionada != "Todas") else kpis

    # Estructura modular de pestañas operativas
    tabs_op = st.tabs([
        "1. Resumen Ejecutivo",
        "2. Análisis por Dimensión",
        "3. Tendencia Mensual",
        "4. Matriz de Backtesting",
        "5. Comparativas Avanzadas",
        "6. Reporte de Exportación"
    ])

    with tabs_op[0]:
        st.title("📊 Resumen Ejecutivo Financiero - Forecast 5+7")
        st.markdown("Visualización analítica del cierre proyectado del año fiscal en curso (5 meses reales + 7 proyectados).")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Presupuesto Anual (Budget FY)", format_currency(kpis_f["Budget_FY_Total"]))
        col2.metric("Pronóstico Dinámico (5+7)", format_currency(kpis_f["Forecast_5plus7_Total"]), f"{kpis_f['Var_vs_Budget_Pct']:+.1f}% vs Budget", delta_color="inverse")
        col3.metric("Ejecutado Real YTD (Ene-May)", format_currency(kpis_f["Real_YTD_Total"]), f"{kpis_f['Pct_Avance_Real']:.1f}% Consumido")
        
        oficial_val = kpis_f.get("Forecast_Oficial_Total", 0) or 0
        var_vs_oficial = kpis_f.get("Var_vs_Oficial_Pct", 0) or 0
        col4.metric("Forecast Oficial Corporativo", format_currency(oficial_val), f"{var_vs_oficial:+.1f}% vs Modelo", delta_color="off")

        st.markdown("---")
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("Estructura de Gastos por Clasificación Contable")
            if not agg_classif_f.empty and "Forecast_5+7" in agg_classif_f.columns:
                fig_t = plot_treemap(agg_classif_f, path=["Classif"], value_col="Forecast_5+7", title="", color_col="Var_Pct")
                fig_t.update_layout(colorway=CORPORATE_PALETTE)
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("Sin registros aplicables para construir mapa conceptual.")
        with c_right:
            st.subheader("Desviación Presupuestaria por Vicepresidencia")
            if not agg_vp_f.empty:
                fig_b = plot_bar_comparison(agg_vp_f, x_col="VP", budget_col="Budget_FY", forecast_col="Forecast_5+7", title="", top_n=10)
                fig_b.update_layout(colorway=CORPORATE_PALETTE)
                st.plotly_chart(fig_b, use_container_width=True)
            else:
                st.info("Sin registros aplicables para construir gráficos de barra.")

        st.markdown("---")
        st.subheader("Puente de Variaciones (Waterfall Chart): Presupuesto Original a Pronóstico 5+7")
        if not agg_classif_f.empty and "Var_Abs" in agg_classif_f.columns:
            desv_dict = {str(row["Classif"]): row["Var_Abs"] for _, row in agg_classif_f.iterrows()}
            fig_w = plot_waterfall(kpis_f["Budget_FY_Total"], kpis_f["Forecast_5plus7_Total"], deviations=desv_dict)
            st.plotly_chart(fig_w, use_container_width=True)
        else:
            st.info("No se registran variaciones aplicables para confeccionar el puente de cascada.")

    with tabs_op[1]:
        st.title("🔍 Desglose Multidimensional de Desviaciones")
        d_tabs = st.tabs(["Por Vicepresidencia", "Por Línea de Gerencia", "Por Clasificación Contable", "Top Desviaciones Críticas"])
        
        with d_tabs[0]:
            if not agg_vp_f.empty:
                st.plotly_chart(plot_bar_comparison(agg_vp_f, "VP", title=""), use_container_width=True)
            else:
                st.info("Filtro excluye líneas de VP.")
        with d_tabs[1]:
            if not agg_gerencia_f.empty and "Forecast_5+7" in agg_gerencia_f.columns:
                top_g = agg_gerencia_f.nlargest(15, "Forecast_5+7").sort_values("Forecast_5+7")
                st.plotly_chart(plot_bar_comparison(top_g, "Gerencia", title=""), use_container_width=True)
            else:
                st.info("Filtro excluye líneas de Gerencia.")
        with d_tabs[2]:
            if not agg_classif_f.empty:
                st.plotly_chart(plot_bar_comparison(agg_classif_f, "Classif", title=""), use_container_width=True)
            else:
                st.info("Filtro excluye líneas de Clasificación Contable.")
        with d_tabs[3]:
            st.subheader("Ítems Específicos con Mayor Impacto Presupuestario")
            if not deviation_df_f.empty and "Var_vs_Budget_Abs" in deviation_df_f.columns:
                t_dev = top_deviations(deviation_df_f, by="Var_vs_Budget_Abs", n=20)
                st.plotly_chart(plot_top_deviations(t_dev, "Desc Item", "Var_vs_Budget_Abs", "Var_vs_Budget_Pct", title="", n=20), use_container_width=True)
            else:
                st.info("Sin registros transaccionales desviados.")

    with tabs_op[2]:
        st.title("📈 Comportamiento y Tendencia Mensual Real vs Proyectada")
        if not forecast_lines_f.empty:
            fc_m = forecast_lines_f[MONTH_COLS].sum().values
            bg_m, of_m = np.zeros(12), np.zeros(12)
            d_cols = ["Resp", "Desc Resp", "VP", "Gerencia", "Proc", "Desc Proc", "Item", "Desc Item", "Classif", "CC"]
            b_mrg = budget_df[d_cols + MONTH_COLS].rename(columns={c: c + "_b" for c in MONTH_COLS})
            f_mrg = forecast_df[d_cols + MONTH_COLS].rename(columns={c: c + "_o" for c in MONTH_COLS})
            m_all = forecast_lines_f[d_cols].merge(b_mrg, on=d_cols, how="inner").merge(f_mrg, on=d_cols, how="inner")
            if not m_all.empty:
                for idx, col in enumerate(MONTH_COLS):
                    bg_m[idx] = m_all[f"{col}_b"].sum()
                    of_m[idx] = m_all[f"{col}_o"].sum()
            st.plotly_chart(plot_monthly_trend(fc_m, bg_m, official_series=of_m, title=""), use_container_width=True)
        else:
            st.warning("Sin datos bajo los criterios de filtrado seleccionados.")

    with tabs_op[3]:
        st.title("🧮 Auditoría Matemática de Modelos Predictivos")
        st.markdown("Estadísticos de error y precisión de desviaciones absolutas calculados durante la fase de backtesting histórico por línea operativa.")
        if resultados_backtesting is not None:
            st.dataframe(resultados_backtesting.set_index("method"), use_container_width=True)
        else:
            st.info("Matriz de Backtesting no inicializada.")

    with tabs_op[4]:
        st.title("⚖️ Cuadro Comparativo de Escenarios de Pronóstico")
        if not forecast_lines_f.empty:
            c_df = compare_with_official(forecast_lines_f, group_cols=["Classif"])
            col_ca, col_cb = st.columns(2)
            with col_ca:
                st.plotly_chart(plot_bar_comparison(c_df, x_col="Classif", budget_col="Budget_FY", forecast_col="Forecast_5plus7", title="Modelo 5+7 vs Presupuesto Base"), use_container_width=True)
            with col_cb:
                st.plotly_chart(plot_bar_comparison(c_df, x_col="Classif", budget_col="Forecast_Oficial", forecast_col="Forecast_5plus7", title="Modelo 5+7 vs Proyección Oficial Corporativa"), use_container_width=True)
        else:
            st.info("Sin registros para contrastar escenarios.")

    with tabs_op[5]:
        st.title("💾 Descarga de Información Operativa")
        st.markdown("Exporte el dataframe procesado completo bajo los filtros operacionales vigentes para auditorías externas.")
        csv_data = forecast_lines_f.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Detalle Forecast 5+7 (.CSV)", data=csv_data, file_name="Forecast_Operacional_5mas7.csv", mime="text/csv", use_container_width=True)


# ============================================================================
# ENTREGABLE MÓDULO 2: ENTORNO DE PROYECCIÓN ESTRATÉGICA QUINQUENAL (2027-2031)
# ============================================================================
elif app_mode == "📈 Proyección Estratégica (2027-2031)":
    st.title("📈 Modelación Financiera y Análisis de Sensibilidad Quinquenal")
    st.markdown("Cálculo y simulación de estrés paramétrico sobre el crecimiento orgánico proyectado (Períodos 2027 al 2031).")

    # Carga estricta y estructurada de las pestañas plurianuales del archivo maestro
    @st.cache_data
    def cargar_hojas_estrategicas(path):
        return (
            pd.read_excel(path, sheet_name="BUDGET 2024 - 2028"),
            pd.read_excel(path, sheet_name="BUDGET 2025 - 2029"),
            pd.read_excel(path, sheet_name="BUDGET 2026 - 2030")
        )

    try:
        b24, b25, b26 = cargar_hojas_estrategicas(file_path)
    except Exception as e:
        st.error(f"❌ Error de Estructura de Libro: Faltan hojas indispensables de horizontes históricos en el archivo Excel cargado. Detalle del error: {e}")
        st.stop()

    columnas_maestras = ['CC', 'VP', 'Gerencia', 'Desc Item', 'Classif']
    cols_existentes = [c for c in columnas_maestras if c in b26.columns]
    
    # Consolidación de información desde los horizontes pasados (2024-2026)
    df_estrat = b26[cols_existentes].copy()
    df_estrat = df_estrat.merge(b24[['CC', 'FY24']], on='CC', how='left')
    df_estrat = df_estrat.merge(b25[['CC', 'FY25']], on='CC', how='left')
    
    df_estrat = df_estrat.merge(b26[['CC', 'FY26'] + [f'{m}-26' for m in MESES_ESTRAT]], on='CC', how='left')
    df_estrat.fillna(0, inplace=True)

    # ------------------------------------------------------------------------
    # SOLUCIÓN DE FILTRADO PERSISTENTE (EVITA RESETEO AL MOVER SLIDERS)
    # ------------------------------------------------------------------------
    st.sidebar.subheader("🔎 Filtro de Visualización Persistente")
    todas_clasificaciones = sorted(df_estrat['Classif'].dropna().unique().tolist())
    
    # Anclaje del estado del filtro multiselección para preservar la vista del usuario
    classif_seleccionadas = st.sidebar.multiselect(
        "Clasificaciones Contables a Evaluar:",
        options=todas_clasificaciones,
        default=todas_clasificaciones,
        help="Al interactuar con los sliders inferiores, el filtro se mantendrá inalterado."
    )
    
    if not classif_seleccionadas:
        st.warning("⚠️ Seleccione al menos una clasificación contable en el panel lateral para iniciar la proyección financiera.")
        st.stop()

    # Modelación de Escenarios Estructurales de Riesgo Macroeconómico
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎬 Escenarios Macroeconómicos")
    escenario = st.sidebar.selectbox("Cargar Configuración de Riesgo:", [
        "Manual / Personalizado",
        "Crisis Global (+Combustible y Dólar)",
        "Negociación Sindical (+Mano de Obra)",
        "Eficiencia Operativa (-Costos Generales)"
    ])

    v_fuel, v_power, v_dolar, v_labor = 0.0, 0.0, 0.0, 0.0
    if escenario == "Crisis Global (+Combustible y Dólar)":
        v_fuel, v_power, v_dolar, v_labor = 25.0, 10.0, 15.0, 5.0
    elif escenario == "Negociación Sindical (+Mano de Obra)":
        v_fuel, v_power, v_dolar, v_labor = 5.0, 2.0, 2.0, 18.0
    elif escenario == "Eficiencia Operativa (-Costos Generales)":
        v_fuel, v_power, v_dolar, v_labor = -10.0, -5.0, -8.0, -5.0

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Parámetros de Sensibilidad (%)")
    slider_fuel_pct = st.sidebar.slider("Variación Indexación Diésel / Carbón", -50.0, 100.0, v_fuel, step=0.5)
    slider_power_pct = st.sidebar.slider("Variación Suministro Eléctrico / PPA", -50.0, 100.0, v_power, step=0.5)
    slider_dolar_pct = st.sidebar.slider("Variación Tipo de Cambio (USD/CLP)", -50.0, 100.0, v_dolar, step=0.5)
    slider_labor_pct = st.sidebar.slider("Impacto en Costo de Mano de Obra", -50.0, 100.0, v_labor, step=0.5)

    # Conversión estricta de series de datos para neutralizar strings corruptos
    f24 = pd.to_numeric(df_estrat['FY24'], errors='coerce').fillna(0)
    f26 = pd.to_numeric(df_estrat['FY26'], errors='coerce').fillna(0)

    # Motor Matemático Quinquenal: Tasa de Crecimiento Compuesto Anualizada (CAGR) Acotada de Estabilidad
    tasa_cagr = np.where(f24 > 0, (f26 / (f24 + 1e-6)) ** (1/2), 1.0).clip(0.95, 1.12)
    
    df_estrat['Base_FY27'] = f26 * tasa_cagr
    df_estrat['Base_FY28'] = df_estrat['Base_FY27'] * tasa_cagr
    df_estrat['Base_FY29'] = df_estrat['Base_FY28'] * tasa_cagr
    df_estrat['Base_FY30'] = df_estrat['Base_FY29'] * tasa_cagr
    df_estrat['Base_FY31'] = df_estrat['Base_FY30'] * tasa_cagr

    # Evaluación Semántica Transaccional e Inyección del Vector de Estrés
    def calcular_multiplicador_estres(row):
        item_text = str(row.get('Desc Item', '')).lower()
        class_text = str(row.get('Classif', '')).lower()
        coef = 1.0
        if 'labor' in class_text or any(token in item_text for token in ['remuneracion', 'sueldo', 'honorario', 'mano de obra', 'bono', 'dotacion', 'sindical', 'gratificacion']):
            coef += (slider_labor_pct / 100.0)
        if any(token in item_text for token in ['diesel', 'combustible', 'petroleo', 'gasoil', 'lubricante', 'carbón']):
            coef += (slider_fuel_pct / 100.0)
        if any(token in item_text for token in ['energia', 'kwh', 'tarifa electrica', 'potencia', 'electricity', 'electricidad']):
            coef += (slider_power_pct / 100.0)
        if any(token in item_text for token in ['usd', 'foreign', 'importado', 'licencia', 'flete internacional', 'tasa de cambio', 'dolar']):
            coef += (slider_dolar_pct / 100.0)
        return coef

    df_estrat['Factor_Estrés_Fila'] = df_estrat.apply(calcular_multiplicador_estres, axis=1)

    for a in AÑOS_QUINQUENIO:
        df_estrat[f'Final_{a}'] = df_estrat[f'Base_{a}'] * df_estrat['Factor_Estrés_Fila']

    # Distribución y estacionalidad mensual indexada con base histórica 2026
    for m in MESES_ESTRAT:
        m_26 = pd.to_numeric(df_estrat.get(f'{m}-26', 0), errors='coerce').fillna(0)
        df_estrat[f'peso_{m}'] = m_26 / (f26 + 1e-6)
        
    suma_pesos = df_estrat[[f'peso_{m}' for m in MESES_ESTRAT]].sum(axis=1)
    
    for m in MESES_ESTRAT:
        peso_normalizado = np.where(suma_pesos > 0, df_estrat[f'peso_{m}'] / (suma_pesos + 1e-6), 1.0 / 12.0)
        df_estrat[f'Base_{m}-27'] = df_estrat['Base_FY27'] * peso_normalizado
        df_estrat[f'{m}-27'] = df_estrat['Final_FY27'] * peso_normalizado

    # Segmentación cruzada estricta para visualización gráfica basada en el filtro lateral persistente
    df_graficos = df_estrat[df_estrat['Classif'].isin(classif_seleccionadas)].copy()

    # Cálculo y agregación de indicadores KPI de Control de Gestión Estratégica
    tot_fy27_base = df_graficos['Base_FY27'].sum()
    tot_fy27_estres = df_graficos['Final_FY27'].sum()
    delta_financiero = tot_fy27_estres - tot_fy27_base
    pct_variacion_impacto = (delta_financiero / tot_fy27_base * 100) if tot_fy27_base != 0 else 0

    st.markdown("### 📊 Indicadores Clave de Riesgo Estratégico (Perspectiva Año 2027)")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("Proyección Orgánica Base FY27", f"${tot_fy27_base:,.0f}")
    kpi_col2.metric("Proyección con Simulación de Estrés", f"${tot_fy27_estres:,.0f}")
    kpi_col3.metric("Desviación Presupuestaria Neta", f"${delta_financiero:,.0f}", f"{pct_variacion_impacto:+.2f}% de Brecha", delta_color="inverse")
    kpi_col4.metric("Escenario Macroeconómico Activo", escenario)

    st.markdown("---")
    
    # Organización de pestañas estratégicas mejoradas
    tab_est_0, tab_est_1, tab_est_2, tab_est_3, tab_est_4 = st.tabs([
        "📈 Histórico + Proyección (2024-2031)",
        "📉 Gráficos Comparativos (Líneas)",
        "📊 Composición Anual Quinquenal",
        "🔍 Detalle de Filas Impactadas",
        "💾 Generar Excel Dinámico"
    ])

    with tab_est_0:
        st.subheader("Evolución Integrada del Gasto: Datos Históricos Reales vs Proyecciones Futuras")
        st.markdown("Visualice la tendencia consolidada desde el año 2024 para identificar quiebres de tendencia.")
        
        anios_hist = ['FY24', 'FY25', 'FY26']
        anios_proy = ['Final_FY27', 'Final_FY28', 'Final_FY29', 'Final_FY30', 'Final_FY31']
        
        df_h_melt = df_graficos[['Classif'] + anios_hist].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_h_melt['Año'] = df_h_melt['Año'].str.replace('FY', '20')
        
        df_p_melt = df_graficos[['Classif'] + anios_proy].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_p_melt['Año'] = df_p_melt['Año'].str.replace('Final_FY', '20')
        
        df_unificado_lineas = pd.concat([df_h_melt, df_p_melt])
        df_g_lineas_grouped = df_unificado_lineas.groupby(['Año', 'Classif'])['Monto'].sum().reset_index()

        fig_full_trend = px.line(
            df_g_lineas_grouped, 
            x="Año", y="Monto", color="Classif", 
            markers=True,
            color_discrete_sequence=CORPORATE_PALETTE,
            title="Línea de Tendencia Multianual Completa (Historial Real + Proyecciones con Estrés)"
        )
        fig_full_trend.add_vline(x="2026", line_dash="dash", line_color="#C00000", annotation_text="  Umbral de Simulación Plan Quinquenal")
        fig_full_trend.update_layout(
            yaxis_tickformat="$,.0f",
            hovermode="x unified",
            legend_title_text="Clasificación Contable",
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_full_trend, use_container_width=True)

    with tab_est_1:
        st.subheader("Análisis Comparativo del Impacto de Estrés (Curvas Base vs Escenario Estresado)")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Proyección Mensualizada del Gasto (Año 2027)**")
            cols_b_m = [f'Base_{m}-27' for m in MESES_ESTRAT]
            cols_f_m = [f'{m}-27' for m in MESES_ESTRAT]
            
            v_base_m = df_graficos[cols_b_m].sum().values
            v_final_m = df_graficos[cols_f_m].sum().values
            
            fig_l_mensual = go.Figure()
            fig_l_mensual.add_trace(go.Scatter(x=MONTH_NAMES, y=v_base_m, mode='lines+markers', name='Proyección Base Original', line=dict(color=BASE_LINE_COLOR, dash='dash', width=2)))
            fig_l_mensual.add_trace(go.Scatter(x=MONTH_NAMES, y=v_final_m, mode='lines+markers', name='Escenario Simulación Estresado', line=dict(color=STRESS_LINE_COLOR, width=3.5)))
            fig_l_mensual.update_layout(
                yaxis_tickformat="$,.0f", 
                hovermode="x unified", 
                title="Curva Mensual Base vs Estrés (2027)",
                legend=dict(orientation="h", y=1.1),
                plot_bgcolor="white"
            )
            st.plotly_chart(fig_l_mensual, use_container_width=True)
            
        with c2:
            st.markdown("**Curva Macroeconómica del Quinquenio (2027-2031)**")
            cols_b_a = [f'Base_{a}' for a in AÑOS_QUINQUENIO]
            cols_f_a = [f'Final_{a}' for a in AÑOS_QUINQUENIO]
            
            v_base_a = df_graficos[cols_b_a].sum().values
            v_final_a = df_graficos[cols_f_a].sum().values
            labels_quinquenio_eje = ['2027', '2028', '2029', '2030', '2031']
            
            fig_l_anual = go.Figure()
            fig_l_anual.add_trace(go.Scatter(x=labels_quinquenio_eje, y=v_base_a, mode='lines+markers', name='Tendencia Orgánica Base', line=dict(color=BASE_LINE_COLOR, dash='dash', width=2)))
            fig_l_anual.add_trace(go.Scatter(x=labels_quinquenio_eje, y=v_final_a, mode='lines+markers', name='Tendencia con Estrés Aplicado', line=dict(color="#1F4E79", width=3.5)))
            fig_l_anual.update_layout(
                yaxis_tickformat="$,.0f", 
                hovermode="x unified", 
                title="Proyección Anual Quinquenal (2027-2031)",
                legend=dict(orientation="h", y=1.1),
                plot_bgcolor="white"
            )
            st.plotly_chart(fig_l_anual, use_container_width=True)

    with tab_est_2:
        st.subheader("Distribución Presupuestaria Quinquenal Estresada por Clasificación Contable")
        cols_final_a = [f'Final_{a}' for a in AÑOS_QUINQUENIO]
        df_m_barras = df_graficos[['Classif'] + cols_final_a].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_m_barras['Año'] = df_m_barras['Año'].str.replace('Final_FY', '20')
        df_g_barras_grouped = df_m_barras.groupby(['Año', 'Classif'])['Monto'].sum().reset_index()

        fig_b_quinquenal = px.bar(
            df_g_barras_grouped, 
            x="Año", y="Monto", color="Classif", 
            title="Estructura de Costos del Plan de Negocios Simulado (2027-2031)", 
            color_discrete_sequence=CORPORATE_PALETTE
        )
        fig_b_quinquenal.update_layout(yaxis_tickformat="$,.0f", barmode="stack", plot_bgcolor="white")
        st.plotly_chart(fig_b_quinquenal, use_container_width=True)

    with tab_est_3:
        st.markdown("### 🔍 Auditoría Transaccional Interna de Líneas Afectadas")
        st.markdown("Mapeo semántico detallado de los registros modificados por los multiplicadores activos basados en las variables de entrada:")
        
        df_auditoria = df_graficos[cols_existentes + ['Factor_Estrés_Fila', 'Base_FY27', 'Final_FY27']].copy()
        df_auditoria = df_auditoria[df_auditoria['Factor_Estrés_Fila'] != 1.0]
        
        if df_auditoria.empty:
            st.info("Ningún registro financiero dentro de los filtros cruzó con las palabras clave de los multiplicadores activos.")
        else:
            st.dataframe(
                df_auditoria.head(400), 
                use_container_width=True,
                column_config={
                    "Base_FY27": st.column_config.NumberColumn("Presupuesto Base FY27", format="$%,.0f"),
                    "Final_FY27": st.column_config.NumberColumn("Presupuesto Estresado FY27", format="$%,.0f"),
                    "Factor_Estrés_Fila": st.column_config.NumberColumn("Multiplicador Aplicado", format="%.3f")
                }
            )

    with tab_est_4:
        st.subheader("💾 Motor de Exportación de Informes Financieros Planeación Quinquenal")
        st.markdown("Genera un libro contable completo parametrizado en Excel, incluyendo tablas de sensibilidad estáticas y gráficos nativos.")
        
        cols_salida_quinquenio = cols_existentes + ['FY24', 'FY25', 'FY26'] + [f'{m}-27' for m in MESES_ESTRAT] + [f'Final_{a}' for a in AÑOS_QUINQUENIO]
        df_excel_salida = df_estrat[cols_salida_quinquenio].copy()

        from io import BytesIO
        output_stream = BytesIO()
        
        with pd.ExcelWriter(output_stream, engine="xlsxwriter") as writer:
            df_excel_salida.to_excel(writer, sheet_name="Plan_Quinquenal_2027_2031", index=False)
            
            workbook = writer.book
            worksheet = writer.sheets["Plan_Quinquenal_2027_2031"]
            
            fmt_dinero = workbook.add_format({'num_format': '$#,##0'})
            fmt_negrita = workbook.add_format({'bold': True})
            fmt_encabezado = workbook.add_format({'bold': True, 'bg_color': '#1F4E79', 'font_color': 'white', 'border': 1})
            
            for col_idx in range(5, len(df_excel_salida.columns)):
                worksheet.set_column(col_idx, col_idx, 16, fmt_dinero)
            
            columna_pivote_interfaz = len(df_excel_salida.columns) + 2
            
            worksheet.write(1, columna_pivote_interfaz, "Matriz de Sensibilidad de Riesgos", fmt_encabezado)
            worksheet.write(1, columna_pivote_interfaz+1, "Porcentaje", fmt_encabezado)
            
            worksheet.write(2, columna_pivote_interfaz, "Precio Diésel / Combustibles", fmt_negrita)
            worksheet.write(2, columna_pivote_interfaz+1, f"{slider_fuel_pct}%")
            worksheet.write(3, columna_pivote_interfaz, "Tarifa de Suministro Eléctrico", fmt_negrita)
            worksheet.write(3, columna_pivote_interfaz+1, f"{slider_power_pct}%")
            worksheet.write(4, columna_pivote_interfaz, "Evolución Cambiaria Dólar (USD)", fmt_negrita)
            worksheet.write(4, columna_pivote_interfaz+1, f"{slider_dolar_pct}%")
            worksheet.write(5, columna_pivote_interfaz, "Mano de Obra / Dotación", fmt_negrita)
            worksheet.write(5, columna_pivote_interfaz+1, f"{slider_labor_pct}%")

            worksheet.write(8, columna_pivote_interfaz, "Período Fiscal", fmt_encabezado)
            worksheet.write(8, columna_pivote_interfaz+1, "Monto Proyectado (USD)", fmt_encabezado)
            
            sumas_totales_quinquenales = [df_excel_salida[f'Final_{a}'].sum() for a in AÑOS_QUINQUENIO]
            for pos, (nombre_anio, total_monto) in enumerate(zip(['2027', '2028', '2029', '2030', '2031'], sumas_totales_quinquenales)):
                worksheet.write(9+pos, columna_pivote_interfaz, nombre_anio)
                worksheet.write(9+pos, columna_pivote_interfaz+1, total_monto, fmt_dinero)

            grafico_excel = workbook.add_chart({'type': 'column'})
            grafico_excel.add_series({
                'name': 'Plan Quinquenal Simulado',
                'categories': ['Plan_Quinquenal_2027_2031', 9, columna_pivote_interfaz, 13, columna_pivote_interfaz],
                'values':     ['Plan_Quinquenal_2027_2031', 9, columna_pivote_interfaz+1, 13, columna_pivote_interfaz+1],
                'data_labels': {'value': True},
                'fill':   {'color': '#1F4E79'}
            })
            grafico_excel.set_title({'name': 'Curva Presupuestaria Quinquenal Estresada'})
            grafico_excel.set_x_axis({'name': 'Año Fiscal'})
            grafico_excel.set_y_axis({'name': 'Monto Operativo (USD)', 'num_format': '$#,##0'})
            grafico_excel.set_size({'width': 580, 'height': 380})
            
            worksheet.insert_chart(16, columna_pivote_interfaz, grafico_excel)
            
        st.download_button(
            label="Descargar Modelo Estratégico Quinquenal Corporativo (.XLSX)",
            data=output_stream.getvalue(),
            file_name="Planificacion_Estrategica_Simulada_Pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
