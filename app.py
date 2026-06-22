import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

def render_tab_budget_2027_2031():
    st.title("🔮 Simulador y Proyección de Budget 2027 - 2031")
    st.markdown("""
    Esta pestaña calcula la proyección del OPEX minero para el quinquenio **2027-2031**, aplicando 
    sensibilidad macroeconómica en tiempo real y aislando los errores detectados en el Budget 2026-2030.
    """)

    # --- 1. SIDEBAR O CONTROLES DE SENSIBILIDAD ---
    st.sidebar.header("🎛️ Variables de Sensibilidad")
    slider_dolar = st.sidebar.slider("Precio del Dólar (USD/CLP) - % Variación", -30.0, 30.0, 0.0, step=0.5) / 100.0
    slider_combustible = st.sidebar.slider("Precio del Combustible (Diésel) - % Variación", -40.0, 40.0, 0.0, step=1.0) / 100.0
    slider_energia = st.sidebar.slider("Costo de la Energía (Power) - % Variación", -30.0, 30.0, 0.0, step=1.0) / 100.0

    # --- 2. CARGA DE DATOS HISTÓRICOS ---
    @st.cache_data
    def load_clean_base_data():
        # En tu app real, usa tus funciones de data_loader, ej: load_budget_detail()
        # Aquí simulamos el cruce limpio de tus CSVs subidos usando la llave 'CC' (Centro de Costo)
        try:
            b24 = pd.read_csv("Datos Proyecto Mejora  2026 (1).xlsx - BUDGET 2024 - 2028.csv")
            b25 = pd.read_csv("Datos Proyecto Mejora  2025 - 2029.csv") # Nombres ajustados a tus archivos
            b26 = pd.read_csv("Datos Proyecto Mejora  2026 (1).xlsx - BUDGET 2026 - 2030.csv")
            return b24, b25, b26
        except:
            # Fallback en caso de rutas relativas locales en la app instalada
            st.warning("Asegúrate de que las rutas a las bases de datos de presupuestos estén correctamente enlazadas.")
            return None, None, None

    b24, b25, b26 = load_clean_base_data()

    if b24 is not None:
        # --- 3. FILTROS DINÁMICOS DE LA INTERFAZ ---
        st.subheader("🔍 Filtros de la Base de Datos (2,500+ Filas)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            lista_vp = ["Todos"] + list(b24['VP'].dropna().unique())
            filtro_vp = st.selectbox("Vicepresidencia (VP)", lista_vp)
        with col2:
            lista_gerencia = ["Todos"] + list(b24['Gerencia'].dropna().unique())
            filtro_gerencia = st.selectbox("Gerencia", lista_gerencia)
        with col3:
            lista_classif = ["Todos"] + list(b24['Classif'].dropna().unique())
            filtro_classif = st.selectbox("Clasificación Gasto (Classif)", lista_classif)

        # --- 4. ALGORITMO DE PROYECCIÓN INTERACTIVO (LÓGICA CORE) ---
        # Duplicamos la estructura base para proyectar
        df_proy = b24[['Resp', 'Desc Resp', 'VP', 'Gerencia', 'Proc', 'Desc Proc', 'Item', 'Desc Item', 'Classif', 'CC']].copy()
        
        # Mapeamos los factores de sensibilidad según la clasificación de cada fila
        def determinar_factor(row):
            factor = 1.0
            # Sensibilidad a Combustibles
            if "Fuel" in str(row['Classif']):
                factor += slider_combustible
            # Sensibilidad a Energía
            if "Power" in str(row['Classif']):
                factor += slider_energia
            # Sensibilidad general al Dólar (Afecta contratos y repuestos importados de forma estimada)
            if "Contractors" in str(row['Classif']) or "Spare Parts" in str(row['Classif']):
                factor += slider_dolar
            return factor

        df_proy['Factor_Sens'] = df_proy.apply(determinar_factor, axis=1)

        # Realizamos las estimaciones para el Budget 2027-2031 basándonos en las tendencias estables de B24 y B25
        # Nota: Multiplicamos por el 'Factor_Sens' dinámico proveniente de los sliders de la UI
        
        # Proyecciones Anuales Base aplicando factores de crecimiento históricos extraídos de tus tendencias estables
        df_proy['FY28'] = b24['FY28'] * df_proy['Factor_Sens'] * 1.03  # Ejemplo indexando crecimiento base + inflación minera
        df_proy['FY29'] = b25['FY29'] * df_proy['Factor_Sens'] * 1.03
        df_proy['FY30'] = b26['FY30'] * df_proy['Factor_Sens'] # Rescate de columna FY30 correcta de B26
        df_proy['FY31'] = df_proy['FY30'] * 1.03 * df_proy['Factor_Sens'] # Extrapolación matemática para año 2031

        # Proyección Mensualizada de 2027 (Año 1 del nuevo Budget)
        # Calculamos el anual de 2027 base
        df_proy['FY27'] = b25['FY27'] * df_proy['Factor_Sens']

        # Extraemos la curva estacional promedio de los meses de los años anteriores (Jan-Dec)
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for mes in meses:
            # Replicamos el patrón de distribución de la curva estacional real sobre el nuevo FY27
            df_proy[f'{mes}-27'] = df_proy['FY27'] * (b24[f'{mes}-24'] / b24['FY24'].replace(0, 1))

        # --- 5. APLICACIÓN DE FILTROS SELECCIONADOS POR EL USUARIO ---
        df_filtrado = df_proy.copy()
        if filtro_vp != "Todos":
            df_filtrado = df_filtrado[df_filtrado['VP'] == filtro_vp]
        if filtro_gerencia != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Gerencia'] == filtro_gerencia]
        if filtro_classif != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Classif'] == filtro_classif]

        # --- 6. VISUALIZACIONES GRÁFICAS EN TIEMPO REAL ---
        st.subheader("📊 Gráficos de Proyección Interactivos")
        
        # Gráfico 1: Tendencia Anual Agregada 2027-2031
        totales_anuales = {
            "Año": ["2027", "2028", "2029", "2030", "2031"],
            "Presupuesto Proyectado (MUSD)": [
                df_filtrado['FY27'].sum() / 1e6,
                df_filtrado['FY28'].sum() / 1e6,
                df_filtrado['FY29'].sum() / 1e6,
                df_filtrado['FY30'].sum() / 1e6,
                df_filtrado['FY31'].sum() / 1e6
            ]
        }
        df_totales = pd.DataFrame(totales_anuales)
        fig_anual = px.bar(df_totales, x="Año", y="Presupuesto Proyectado (MUSD)", 
                           title="Evolución del Presupuesto Plurianual Proyectado (2027 - 2031)",
                           text_auto='.2f', color_discrete_sequence=['#2E7D32'])
        st.plotly_chart(fig_anual, use_container_width=True)

        # Gráfico 2: Apertura Mensual del Año 2027
        columnas_meses_27 = [f'{m}-27' for m in meses]
        totales_mensuales_27 = df_filtrado[columnas_meses_27].sum() / 1e6
        df_mensual = pd.DataFrame({"Mes": meses, "Presupuesto 2027 (MUSD)": totales_mensuales_27.values})
        
        fig_mes = px.line(df_mensual, x="Mes", y="Presupuesto 2027 (MUSD)", 
                          title="Distribución Mensual Detallada - Año 2027", 
                          markers=True, color_discrete_sequence=['#1565C0'])
        st.plotly_chart(fig_mes, use_container_width=True)

        # --- 7. BOTÓN DE DESCARGA CON XLSXWRITER ---
        st.subheader("📥 Exportar Datos Calculados")
        st.markdown("Descarga el Excel completo con las 2,500+ líneas recalculadas según los parámetros seleccionados.")

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Guardamos la data detallada filtrada
            df_filtrado.to_excel(writer, sheet_name="Data_Detallada_2027_2031", index=False)
            
            # Guardamos un resumen ejecutivo listo para gráficos en Excel
            df_totales.to_excel(writer, sheet_name="Resumen_Ejecutivo", index=False)
            
            # Obtener objetos nativos de xlsxwriter para aplicar formatos corporativos
            workbook  = writer.book
            worksheet = writer.sheets['Data_Detallada_2027_2031']
            
            # Formato de dinero
            currency_format = workbook.add_format({'num_format': '$#,##0', 'align': 'right'})
            # Aplicar formato a las columnas numéricas de las 2500 filas en el excel descargable
            worksheet.set_column('K:Z', 15, currency_format)

        st.download_button(
            label="💾 Descargar Nuevo Budget 2027-2031 (.xlsx)",
            data=output.getvalue(),
            file_name="PROYECCION_BUDGET_2027_2031.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.dataframe(df_filtrado.head(100)) # Vista previa de las primeras 100 líneas del cálculo
