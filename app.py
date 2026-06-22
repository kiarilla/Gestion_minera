import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Proyección Budget Minero v1", layout="wide")

def main():
    st.title("🔮 Simulador de Proyección Budget 2027 - 2031 (v1)")
    st.markdown("Proyección inteligente línea por línea basándose en las tendencias históricas.")

    # --- 1. CONTROLES DE SENSIBILIDAD ---
    st.sidebar.header("🎛️ Variables Macroeconómicas")
    slider_dolar = st.sidebar.slider("Dólar (Contratos/Repuestos) %", -30.0, 30.0, 0.0, step=1.0) / 100.0
    slider_fuel = st.sidebar.slider("Precio Combustible (Diésel puro) %", -40.0, 40.0, 0.0, step=1.0) / 100.0
    slider_power = st.sidebar.slider("Costo Energía Eléctrica %", -30.0, 30.0, 0.0, step=1.0) / 100.0

    # --- 2. CARGA DE DATOS ---
    @st.cache_data
    def cargar_datos():
        try:
            # Reemplaza los nombres si difieren ligeramente en tu PC
            b24 = pd.read_csv("Datos Proyecto Mejora  2026 (1).xlsx - BUDGET 2024 - 2028.csv")
            b25 = pd.read_csv("Datos Proyecto Mejora  2026 (1).xlsx - BUDGET 2025 - 2029.csv")
            b26 = pd.read_csv("Datos Proyecto Mejora  2026 (1).xlsx - BUDGET 2026 - 2030.csv")
            return b24, b25, b26
        except Exception as e:
            st.error(f"Error al cargar archivos. Asegúrate de que los CSV estén en la misma carpeta. Detalle: {e}")
            return None, None, None

    b24, b25, b26 = cargar_datos()

    if b24 is not None:
        # --- 3. MERGE Y LÓGICA DE PROYECCIÓN LÍNEA POR LÍNEA ---
        
        # Usamos el presupuesto 2026 como base maestra para obtener las descripciones y el FY26 y FY30 correctos
        df = b26[['CC', 'Resp', 'VP', 'Gerencia', 'Proc', 'Desc Proc', 'Item', 'Desc Item', 'Classif', 'FY26', 'FY30']].copy()
        
        # Cruzamos con B24 y B25 para extraer las columnas que capturan las tendencias y ciclos
        # Usamos 'CC' (Centro de Costo) como llave única
        b25_tendencias = b25[['CC', 'FY26', 'FY27', 'FY28', 'FY29', 'Jan-25', 'Feb-25', 'Mar-25', 'Apr-25', 'May-25', 'Jun-25', 'Jul-25', 'Aug-25', 'Sep-25', 'Oct-25', 'Nov-25', 'Dec-25', 'FY25']]
        b24_tendencias = b24[['CC', 'FY27', 'FY28']]

        df = pd.merge(df, b25_tendencias, on='CC', how='left', suffixes=('', '_b25'))
        df = pd.merge(df, b24_tendencias, on='CC', how='left', suffixes=('', '_b24'))

        # Llenar vacíos con 0 para evitar errores matemáticos
        df.fillna(0, inplace=True)

        # CÁLCULO DE TENDENCIAS (Aumentos/Disminuciones de los presupuestos anteriores)
        # Evitamos divisiones por cero sumando un valor minúsculo (1e-6)
        t_27 = df['FY27'] / (df['FY26_b25'] + 1e-6) 
        t_28 = df['FY28'] / (df['FY27'] + 1e-6)
        t_29 = df['FY29'] / (df['FY28'] + 1e-6)
        
        # Limitar tendencias locas (crecimientos > 200% o caídas fuertes por errores de data)
        t_27 = t_27.clip(0.5, 1.5)
        t_28 = t_28.clip(0.5, 1.5)
        t_29 = t_29.clip(0.5, 1.5)

        # APLICAR TENDENCIA A LA BASE SANA (FY26 de B26)
        df['Proy_FY27'] = df['FY26'] * t_27
        df['Proy_FY28'] = df['Proy_FY27'] * t_28
        df['Proy_FY29'] = df['Proy_FY28'] * t_29
        df['Proy_FY30'] = df['FY30'] # Rescatado directo del Budget 26-30
        df['Proy_FY31'] = df['Proy_FY30'] * ((t_27 + t_28 + t_29) / 3).clip(1.0, 1.05) # Promedio de crecimiento

        # --- 4. SENSIBILIDAD LÍNEA POR LÍNEA (FILTRO POR PALABRAS CLAVE) ---
        def aplicar_sensibilidad(row):
            desc = str(row['Desc Item']).lower()
            proc = str(row['Desc Proc']).lower()
            
            factor = 1.0
            
            # Combustible: Solo si menciona diesel, petroleo o combustible específicamente
            if 'diesel' in desc or 'petroleo' in desc or 'combustible' in desc:
                factor += slider_fuel
                
            # Energía: Solo si menciona energía, eléctrica, o electricidad
            if 'energia' in desc or 'electrica' in desc or 'electricidad' in desc or 'power' in desc:
                factor += slider_power
                
            # Dólar: Repuestos importados, contratistas mayores
            if 'contrato' in desc or 'repuesto' in desc or 'spare' in desc:
                factor += slider_dolar
                
            return factor

        # Aplicar el factor calculado a cada línea
        df['Factor_Sens'] = df.apply(aplicar_sensibilidad, axis=1)

        # Multiplicar las proyecciones por el factor
        anios = ['Proy_FY27', 'Proy_FY28', 'Proy_FY29', 'Proy_FY30', 'Proy_FY31']
        for anio in anios:
            df[anio] = df[anio] * df['Factor_Sens']

        # --- 5. MENSUALIZACIÓN DEL 2027 ---
        # Usamos la distribución estacional del 2025 para prorratear el FY27
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for mes in meses:
            col_mes_25 = f'{mes}-25'
            # % que representa ese mes en el año total
            peso_mensual = df[col_mes_25] / (df['FY25'] + 1e-6)
            df[f'{mes}-27'] = df['Proy_FY27'] * peso_mensual

        # Limpiar columnas temporales
        columnas_finales = ['CC', 'VP', 'Gerencia', 'Desc Proc', 'Desc Item', 'Classif', 'Factor_Sens'] + [f'{m}-27' for m in meses] + anios
        df_final = df[columnas_finales].copy()

        # --- 6. INTERFAZ Y GRÁFICOS ---
        st.subheader("📊 Resultados de la Proyección (Global)")
        
        totales = df_final[anios].sum() / 1e6 # En Millones de USD
        df_totales = pd.DataFrame({"Año": ["2027", "2028", "2029", "2030", "2031"], "MUSD": totales.values})
        
        fig = px.bar(df_totales, x="Año", y="MUSD", title="OPEX Proyectado Total (MUSD)", text_auto='.2f')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🔍 Vista Previa de Datos Calculados Línea a Línea")
        st.dataframe(df_final.head(50))

        # --- 7. EXPORTAR A EXCEL ---
        st.markdown("### 📥 Descargar Resultados")
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_final.to_excel(writer, sheet_name="Proyeccion_2027_2031", index=False)
            
        st.download_button(
            label="💾 Descargar Excel Proyectado v1",
            data=output.getvalue(),
            file_name="Budget_2027_2031_Proyectado_v1.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
