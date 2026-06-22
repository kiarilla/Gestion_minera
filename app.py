import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y CONSTANTES
# ============================================================================
st.set_page_config(
    page_title="Suite de Control de Gestión & Forecast",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

CORPORATE_PALETTE = ["#1F4E79", "#2E75B6", "#5B9BD5", "#8FAADC", "#D9E1F2", "#4472C4", "#A5A5A5", "#ED7D31"]
MESES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
AÑOS_QUINQUENIO = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']

# ============================================================================
# 2. FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS (INTEGRADAS)
# ============================================================================
@st.cache_data(show_spinner=False)
def cargar_y_limpiar_datos(uploaded_file):
    """Carga las pestañas necesarias del Excel maestro y limpia los datos."""
    try:
        # Para el forecast 5+7
        forecast_df = pd.read_excel(uploaded_file, sheet_name="Forecast 5+7")
        budget_df = pd.read_excel(uploaded_file, sheet_name="BUDGET 2024 - 2028")
        
        # Para la planificación estratégica quinquenal
        b24 = pd.read_excel(uploaded_file, sheet_name="BUDGET 2024 - 2028")
        b25 = pd.read_excel(uploaded_file, sheet_name="BUDGET 2025 - 2029")
        b26 = pd.read_excel(uploaded_file, sheet_name="BUDGET 2026 - 2030")
        
        return forecast_df, budget_df, b24, b25, b26
    except Exception as e:
        st.error(f"Error al leer el archivo. Asegúrate de que tenga las pestañas correctas: {e}")
        return None, None, None, None, None

def preparar_datos_estrategicos(b24, b25, b26):
    """Consolida el histórico 2024-2026 para proyectar 2027-2031."""
    columnas_maestras = ['CC', 'VP', 'Gerencia', 'Desc Item', 'Classif']
    cols_existentes = [c for c in columnas_maestras if c in b26.columns]
    
    df_estrat = b26[cols_existentes].copy()
    
    if 'FY24' in b24.columns:
        df_estrat = df_estrat.merge(b24[['CC', 'FY24']], on='CC', how='left')
    if 'FY25' in b25.columns:
        df_estrat = df_estrat.merge(b25[['CC', 'FY25']], on='CC', how='left')
    
    cols_b26_to_merge = ['CC', 'FY26'] + [c for c in b26.columns if any(m in c for m in MESES) and '26' in c]
    df_estrat = df_estrat.merge(b26[cols_b26_to_merge], on='CC', how='left')
    df_estrat.fillna(0, inplace=True)
    
    return df_estrat, cols_existentes

# ============================================================================
# 3. BARRA LATERAL: CARGA DE ARCHIVOS Y MODO DE APLICACIÓN
# ============================================================================
st.sidebar.title("📁 Datos Maestros")
uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel (.xlsx)", type=["xlsx"])

if not uploaded_file:
    st.info("👋 ¡Bienvenido a la Suite de Control de Gestión!")
    st.warning("⚠️ Por favor, carga el archivo Excel en la barra lateral para comenzar.")
    st.stop()

with st.spinner("Procesando motor de datos..."):
    forecast_df, budget_df, b24, b25, b26 = cargar_y_limpiar_datos(uploaded_file)

if forecast_df is None:
    st.stop()

st.sidebar.markdown("---")
st.sidebar.title("🧭 Módulo Operativo")
app_mode = st.sidebar.radio("Seleccione el entorno:", [
    "📊 Forecast Operacional (5+7)",
    "📈 Proyección Estratégica (2027-2031)"
])

# ============================================================================
# 4. MÓDULO 1: FORECAST OPERACIONAL 5+7
# ============================================================================
if app_mode == "📊 Forecast Operacional (5+7)":
    st.title("📊 Resumen Ejecutivo y Control de Forecast 5+7")
    
    # Filtros Operativos
    st.sidebar.markdown("---")
    st.sidebar.title("🔍 Filtros de Visualización")
    
    vps = ["Todas"] + sorted(forecast_df["VP"].dropna().unique().tolist())
    vp_seleccionada = st.sidebar.selectbox("Vicepresidencia (VP)", vps)
    
    classifs = ["Todas"] + sorted(forecast_df["Classif"].dropna().unique().tolist())
    classif_seleccionada = st.sidebar.selectbox("Clasificación", classifs)
    
    # Aplicar Filtros
    df_filtrado = forecast_df.copy()
    if vp_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["VP"] == vp_seleccionada]
    if classif_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Classif"] == classif_seleccionada]
        
    # KPIs Básicos
    if "Forecast FY" in df_filtrado.columns and "Budget FY" in df_filtrado.columns:
        total_forecast = df_filtrado["Forecast FY"].sum()
        total_budget = df_filtrado["Budget FY"].sum()
        variacion = total_forecast - total_budget
        pct_variacion = (variacion / total_budget * 100) if total_budget else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Presupuesto Anual (Budget FY)", f"${total_budget:,.0f}")
        c2.metric("Pronóstico Dinámico (5+7)", f"${total_forecast:,.0f}", f"{pct_variacion:+.2f}% vs Budget", delta_color="inverse")
        if "YTD" in df_filtrado.columns:
            c3.metric("Gasto Real YTD", f"${df_filtrado['YTD'].sum():,.0f}")
            
    # Gráficos Limpios para Forecast
    st.markdown("---")
    st.subheader("Distribución por Clasificación Contable")
    if not df_filtrado.empty:
        df_agrupado = df_filtrado.groupby("Classif")[["Forecast FY", "Budget FY"]].sum().reset_index()
        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(x=df_agrupado["Classif"], y=df_agrupado["Budget FY"], name="Budget FY", marker_color="#A5A5A5"))
        fig_barras.add_trace(go.Bar(x=df_agrupado["Classif"], y=df_agrupado["Forecast FY"], name="Forecast 5+7", marker_color="#1F4E79"))
        fig_barras.update_layout(barmode='group', plot_bgcolor="white", yaxis_tickformat="$,.0f")
        st.plotly_chart(fig_barras, use_container_width=True)

# ============================================================================
# 5. MÓDULO 2: PROYECCIÓN ESTRATÉGICA QUINQUENAL (REDESEÑADO)
# ============================================================================
elif app_mode == "📈 Proyección Estratégica (2027-2031)":
    st.title("📈 Modelación y Sensibilidad Quinquenal (2027-2031)")
    
    df_estrat, cols_existentes = preparar_datos_estrategicos(b24, b25, b26)
    
    # ------------------------------------------------------------------------
    # CONTROLES Y FILTROS PERSISTENTES
    # ------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 Filtro de Visualización")
    todas_clasificaciones = sorted(df_estrat['Classif'].dropna().unique().tolist())
    
    classif_seleccionadas = st.sidebar.multiselect(
        "Clasificaciones Contables a Evaluar:",
        options=todas_clasificaciones,
        default=todas_clasificaciones
    )
    
    if not classif_seleccionadas:
        st.warning("Seleccione al menos una clasificación contable.")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Parámetros de Riesgo Macroeconómico (%)")
    slider_fuel = st.sidebar.slider("Impacto Combustible / Diésel", -20.0, 50.0, 5.0, step=0.5)
    slider_power = st.sidebar.slider("Impacto Suministro Eléctrico", -20.0, 50.0, 3.0, step=0.5)
    slider_dolar = st.sidebar.slider("Variación Dólar (USD/CLP)", -20.0, 50.0, 10.0, step=0.5)
    slider_labor = st.sidebar.slider("Variación Mano de Obra", -10.0, 30.0, 8.0, step=0.5)

    # ------------------------------------------------------------------------
    # MOTOR MATEMÁTICO: CAGR Y ESTRÉS
    # ------------------------------------------------------------------------
    f24 = pd.to_numeric(df_estrat['FY24'], errors='coerce').fillna(0)
    f26 = pd.to_numeric(df_estrat['FY26'], errors='coerce').fillna(0)

    # Tasa de crecimiento base acotada
    tasa_cagr = np.where(f24 > 0, (f26 / (f24 + 1e-6)) ** (1/2), 1.0).clip(0.95, 1.12)
    
    df_estrat['Base_FY27'] = f26 * tasa_cagr
    df_estrat['Base_FY28'] = df_estrat['Base_FY27'] * tasa_cagr
    df_estrat['Base_FY29'] = df_estrat['Base_FY28'] * tasa_cagr
    df_estrat['Base_FY30'] = df_estrat['Base_FY29'] * tasa_cagr
    df_estrat['Base_FY31'] = df_estrat['Base_FY30'] * tasa_cagr

    def calcular_estres(row):
        item_text = str(row.get('Desc Item', '')).lower()
        class_text = str(row.get('Classif', '')).lower()
        coef = 1.0
        if 'labor' in class_text or any(k in item_text for k in ['remuneracion', 'sueldo', 'bono', 'dotacion']):
            coef += (slider_labor / 100.0)
        if any(k in item_text for k in ['diesel', 'combustible', 'petroleo', 'lubricante']):
            coef += (slider_fuel / 100.0)
        if any(k in item_text for k in ['energia', 'kwh', 'tarifa', 'electricidad']):
            coef += (slider_power / 100.0)
        if any(k in item_text for k in ['usd', 'importado', 'dolar']):
            coef += (slider_dolar / 100.0)
        return coef

    df_estrat['Factor_Estres'] = df_estrat.apply(calcular_estres, axis=1)

    for a in AÑOS_QUINQUENIO:
        df_estrat[f'Final_{a}'] = df_estrat[f'Base_{a}'] * df_estrat['Factor_Estres']

    # Filtrar dataframe para gráficos
    df_graficos = df_estrat[df_estrat['Classif'].isin(classif_seleccionadas)].copy()

    # KPIs
    tot_base_27 = df_graficos['Base_FY27'].sum()
    tot_final_27 = df_graficos['Final_FY27'].sum()
    delta = tot_final_27 - tot_base_27
    
    st.markdown("### 🎯 Impacto del Estrés Financiero (Perspectiva 2027)")
    k1, k2, k3 = st.columns(3)
    k1.metric("Proyección Orgánica Base (2027)", f"${tot_base_27:,.0f}")
    k2.metric("Proyección con Estrés (2027)", f"${tot_final_27:,.0f}")
    k3.metric("Desviación por Riesgo", f"${delta:,.0f}", f"{(delta/(tot_base_27+1e-6)*100):+.2f}%", delta_color="inverse")
    
    st.markdown("---")
    
    # ------------------------------------------------------------------------
    # NUEVOS GRÁFICOS REDISEÑADOS (REEMPLAZO DE LA FOTO)
    # ------------------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs([
        "📊 Evolución Histórica + Proyectada (Área)", 
        "⚖️ Comparativa Base vs Estrés",
        "💾 Exportar Modelo Excel"
    ])

    with tab1:
        st.subheader("Evolución Integrada del Gasto (2024 - 2031)")
        st.markdown("En lugar de líneas superpuestas, visualiza la composición total del gasto mediante áreas apiladas.")
        
        anios_hist = ['FY24', 'FY25', 'FY26']
        anios_proy = ['Final_FY27', 'Final_FY28', 'Final_FY29', 'Final_FY30', 'Final_FY31']
        
        df_h = df_graficos[['Classif'] + anios_hist].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_h['Año'] = df_h['Año'].str.replace('FY', '20')
        
        df_p = df_graficos[['Classif'] + anios_proy].melt(id_vars=['Classif'], var_name='Año', value_name='Monto')
        df_p['Año'] = df_p['Año'].str.replace('Final_FY', '20')
        
        df_area = pd.concat([df_h, df_p]).groupby(['Año', 'Classif'])['Monto'].sum().reset_index()
        
        fig_area = px.area(
            df_area, 
            x="Año", y="Monto", color="Classif",
            color_discrete_sequence=CORPORATE_PALETTE,
            title="Estructura de Costos Histórica y Proyectada"
        )
        fig_area.add_vline(x="2026", line_dash="dash", line_color="red", annotation_text="  Punto de Proyección")
        fig_area.update_layout(plot_bgcolor="white", yaxis_tickformat="$,.0f", hovermode="x unified")
        st.plotly_chart(fig_area, use_container_width=True)

    with tab2:
        st.subheader("Impacto del Estrés por Clasificación (Proyección Quinquenal)")
        st.markdown("Comparación clara entre la tendencia orgánica sin alterar y el escenario con los riesgos activados.")
        
        v_base = [df_graficos[f'Base_{a}'].sum() for a in AÑOS_QUINQUENIO]
        v_final = [df_graficos[f'Final_{a}'].sum() for a in AÑOS_QUINQUENIO]
        labels = ['2027', '2028', '2029', '2030', '2031']
        
        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(x=labels, y=v_base, name='Base Orgánica', marker_color="#A5A5A5"))
        fig_barras.add_trace(go.Bar(x=labels, y=v_final, name='Escenario Estresado', marker_color="#1F4E79"))
        
        fig_barras.update_layout(
            barmode='group',
            plot_bgcolor="white",
            yaxis_tickformat="$,.0f",
            title="Brecha de Riesgo Financiero por Año",
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    with tab3:
        st.subheader("💾 Exportar Modelo a Excel Dinámico (xlsxwriter)")
        st.markdown("Genera un libro nativo de Excel que incluye los datos simulados y un gráfico insertado.")
        
        output = BytesIO()
        cols_export = cols_existentes + ['FY24', 'FY25', 'FY26'] + [f'Final_{a}' for a in AÑOS_QUINQUENIO]
        df_export = df_estrat[cols_export]

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, sheet_name='Plan_Estrategico', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Plan_Estrategico']
            
            # Formatos
            fmt_dinero = workbook.add_format({'num_format': '$#,##0'})
            fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1F4E79', 'font_color': 'white'})
            
            # Aplicar anchos y formatos
            for col_num, value in enumerate(df_export.columns.values):
                worksheet.write(0, col_num, value, fmt_header)
                if 'FY' in value:
                    worksheet.set_column(col_num, col_num, 15, fmt_dinero)
            
            # Resumen y Gráficos en Excel
            col_pivote = len(df_export.columns) + 2
            worksheet.write(2, col_pivote, "Resumen Quinquenal Simulado", fmt_header)
            
            totales = [df_export[f'Final_{a}'].sum() for a in AÑOS_QUINQUENIO]
            for i, (anio, total) in enumerate(zip(['2027', '2028', '2029', '2030', '2031'], totales)):
                worksheet.write(3+i, col_pivote, anio)
                worksheet.write(3+i, col_pivote+1, total, fmt_dinero)
                
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'categories': ['Plan_Estrategico', 3, col_pivote, 7, col_pivote],
                'values':     ['Plan_Estrategico', 3, col_pivote+1, 7, col_pivote+1],
                'name':       'Evolución Presupuestaria',
                'fill':       {'color': '#1F4E79'}
            })
            chart.set_title({'name': 'Impacto Quinquenal con Estrés'})
            worksheet.insert_chart(10, col_pivote, chart)

        st.download_button(
            label="Descargar Modelo Estratégico (.XLSX)",
            data=output.getvalue(),
            file_name="Planificacion_Quinquenal_Pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
