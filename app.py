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

# Asegurar que src este en el path para las importaciones
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

# Configuracion inicial de la pagina
st.set_page_config(
    page_title="Plataforma de Control de Gestion - Forecast Operacional",
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

# Ruta donde el programa espera leer el archivo base para los calculos
file_path = data_dir / "02_Gastos_Proy_Mejor_01-2025.xlsx"

if uploaded_file is not None:
    # Validacion para evitar reprocesamiento innecesario si es el mismo archivo
    if "last_uploaded_name" not in st.session_state or st.session_state.last_uploaded_name != uploaded_file.name:
        st.session_state.last_uploaded_name = uploaded_file.name
        st.cache_data.clear()
        clear_cache()
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("Archivo cargado y procesado exitosamente en el sistema.")

if not file_path.exists():
    st.info("Bienvenido a la Plataforma. Por favor, sube el archivo Excel maestro en la barra lateral para inicializar los modulos.")
    st.stop()

# ============================================================================
# 2. NAVEGACION PRINCIPAL
# ============================================================================
st.sidebar.markdown("---")
st.sidebar.title("Navegacion")
app_mode = st.sidebar.radio("Selecciona un Modulo de Trabajo:", [
    "Forecast Operacional (5+7)",
    "Proyeccion Estrategica (2027-2031)"
])
st.sidebar.markdown("---")

# ============================================================================
# Carga de datos (optimizada y cacheada)
# ============================================================================
@st.cache_data(show_spinner="Cargando y estructurando datos base...")
def cargar_datos():
    """Carga y prepara todos los DataFrames necesarios para los modulos."""
    forecast_df = load_forecast_detail()
    budget_df = load_budget_detail()
    grupos_df = load_grupos_mapping()
    pivot_df = load_pivot_summary()
    forecast_merged, budget_merged = get_merged_data()
    return forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged

with st.spinner("Inicializando modelos de datos..."):
    forecast_df, budget_df, grupos_df, pivot_df, forecast_merged, budget_merged = cargar_datos()

# Inicializacion de variables de estado de sesion
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

# Verificacion de existencia de cache en disco para evitar reejecucion
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
# MODULO 1: FORECAST OPERACIONAL 5+7
# ============================================================================
# ============================================================================
if app_mode == "Forecast Operacional (5+7)":

    # Validacion de ejecucion de modelos
    if not st.session_state.modelos_ejecutados:
        st.warning(
            "No se encontraron modelos predictivos ejecutados previamente en cache. "
            "Proceda a ejecutar el backtesting para generar el Forecast 5+7."
        )
        if st.button("Ejecutar Modelos (Backtesting + Forecast)", type="primary", use_container_width=True):
            with st.spinner("Ejecutando proceso de validacion cruzada (Backtesting)..."):
                st.session_state.resultados_backtesting = run_backtesting(forecast_df, budget_df)

            st.session_state.metodo_ganador = select_best_method(
                st.session_state.resultados_backtesting, "rmse_mean"
            )

            with st.spinner(f"Generando Forecast 5+7 utilizando algoritmo: {st.session_state.metodo_ganador}..."):
                st.session_state.forecast_lines = project_full_forecast(
                    forecast_df, budget_df, method=st.session_state.metodo_ganador
                )

            st.session_state.kpis = compute_kpis(st.session_state.forecast_lines, forecast_df)

            # Guardado en disco para persistencia
            save_backtesting_results(st.session_state.resultados_backtesting)
            save_forecast(st.session_state.forecast_lines)
            save_metadata(st.session_state.metodo_ganador, st.session_state.kpis)
            st.session_state.modelos_ejecutados = True
            st.rerun()
        st.stop()

    # Asignacion de variables de entorno para la vista
    resultados_backtesting = st.session_state.resultados_backtesting
    forecast_lines = st.session_state.forecast_lines
    metodo_ganador = st.session_state.metodo_ganador
    kpis = st.session_state.kpis

    # Calculos de agregaciones de alto nivel
    deviation_df = compute_deviations(forecast_lines, compare_vs_official=True)
    agg_vp = aggregate_forecast(forecast_lines, ["VP"])
    agg_classif = aggregate_forecast(forecast_lines, ["Classif"])
    agg_gerencia = aggregate_forecast(forecast_lines, ["Gerencia"])

    # ---------------------------------------------------------
    # Sidebar - Configuracion de Filtros Globales
    # ---------------------------------------------------------
    st.sidebar.title("Filtros Analiticos")
    
    vps_list = ["Todas"] + sorted(forecast_merged["VP"].dropna().unique().tolist())
    vp_seleccionada = st.sidebar.selectbox("Vicepresidencia (VP)", vps_list)

    classifs_list = ["Todas"] + sorted(forecast_merged["Classif"].dropna().unique().tolist())
    classif_seleccionada = st.sidebar.selectbox("Clasificacion de Gasto", classifs_list)

    if "CLASS" in forecast_merged.columns:
        classes_list = ["Todas"] + sorted(forecast_merged["CLASS"].dropna().unique().tolist())
        class_seleccionada = st.sidebar.selectbox("Grupo (CLASS)", classes_list)
    else:
        class_seleccionada = "Todas"

    st.sidebar.markdown("---")
    st.sidebar.caption("Configuracion de Algoritmo")
    metodos_disponibles = ["linear", "budget_scaled", "polynomial", "holt_damped", "spline_damped", "arima"]
    metodo_seleccionado = st.sidebar.selectbox(
        "Metodo de Proyeccion Activo",
        metodos_disponibles,
        index=metodos_disponibles.index(metodo_ganador) if metodo_ganador in metodos_disponibles else 1,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"El sistema ha optimizado automaticamente hacia: **{metodo_ganador}**")

    if st.sidebar.button("Re-ejecutar Modelos Completos", use_container_width=True):
        clear_cache()
        st.session_state.modelos_ejecutados = False
        st.rerun()

    # ---------------------------------------------------------
    # Aplicacion de Filtros a Estructuras de Datos
    # ---------------------------------------------------------
    def filtrar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Aplica la logica de filtrado global del sidebar a cualquier DataFrame compatible."""
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

    # Recalcular KPIs si hay filtros activos
    if vp_seleccionada != "Todas" or classif_seleccionada != "Todas":
        kpis_f = compute_kpis(forecast_lines_f, forecast_df)
    else:
        kpis_f = kpis

    # ---------------------------------------------------------
    # Estructuracion de Tabs de Navegacion
    # ---------------------------------------------------------
    tabs = st.tabs([
        "1. Resumen Ejecutivo",
        "2. Analisis por Dimension",
        "3. Tendencia Mensual",
        "4. Forecast 5+7",
        "5. Comparaciones",
        "6. Hallazgos",
        "7. Exportar",
    ])

    # --- TAB 1: Resumen Ejecutivo ---
    with tabs[0]:
        st.title("Resumen Ejecutivo de Proyeccion - Forecast 5+7")
        st.markdown("Proyeccion financiera de gastos operacionales (OPEX) consolidando 5 meses de ejecucion real mas 7 meses modelados.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Presupuesto Anual (Budget FY)", format_currency(kpis_f["Budget_FY_Total"]))
        with col2:
            st.metric("Proyeccion (Forecast 5+7)", format_currency(kpis_f["Forecast_5plus7_Total"]), 
                      delta=f"{kpis_f['Var_vs_Budget_Pct']:+.1f}% vs Presupuesto", delta_color="inverse")
        with col3:
            st.metric("Ejecucion Real YTD", format_currency(kpis_f["Real_YTD_Total"]), 
                      delta=f"{kpis_f['Pct_Avance_Real']:.1f}% consumido del Presupuesto")
        with col4:
            oficial_val = kpis_f.get("Forecast_Oficial_Total", 0) or 0
            var_vs_oficial = kpis_f.get("Var_vs_Oficial_Pct", 0) or 0
            st.metric("Forecast Oficial Vigente", format_currency(oficial_val), 
                      delta=f"{var_vs_oficial:+.1f}% vs Modelo 5+7", delta_color="off")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Distribucion de OPEX por Clasificacion")
            fig_treemap = plot_treemap(agg_classif_f, path=["Classif"], value_col="Forecast_5+7", title="", color_col="Var_Pct")
            st.plotly_chart(fig_treemap, use_container_width=True)
            
        with col_b:
            st.subheader("Comparativo Forecast vs Budget por Vicepresidencia")
            fig_vp_bar = plot_bar_comparison(agg_vp, x_col="VP", budget_col="Budget_FY", forecast_col="Forecast_5+7", title="", top_n=10)
            st.plotly_chart(fig_vp_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("Evolucion de Desviaciones (Waterfall)")
        st.markdown("Analisis de brechas desde el presupuesto aprobado (Budget FY) hasta el cierre estimado (Forecast 5+7).")
        devs = {str(row["Classif"]): row["Var_Abs"] for _, row in agg_classif_f.iterrows()}
        fig_waterfall_chart = plot_waterfall(kpis_f["Budget_FY_Total"], kpis_f["Forecast_5plus7_Total"], deviations=devs)
        st.plotly_chart(fig_waterfall_chart, use_container_width=True)

    # --- TAB 2: Análisis por Dimensión ---
    with tabs[1]:
        st.title("Analisis Financiero por Dimensiones")
        st.markdown("Desglose pormenorizado del comportamiento proyectado segmentado por jerarquias de negocio.")
        
        dim_tabs = st.tabs(["Por Vicepresidencia", "Por Gerencia", "Por Clasificacion", "Por Agrupacion CLASS", "Top Desviaciones Totales"])
        
        with dim_tabs[0]:
            st.subheader("Perspectiva de Vicepresidencia")
            st.plotly_chart(plot_bar_comparison(agg_vp, "VP", title=""), use_container_width=True)
            st.dataframe(
                agg_vp[["VP", "Forecast_5+7", "Budget_FY", "Var_Abs", "Var_Pct"]].sort_values("Forecast_5+7", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Forecast_5+7": st.column_config.NumberColumn("Forecast 5+7", format="%.0f"),
                    "Budget_FY": st.column_config.NumberColumn("Presupuesto Anual", format="%.0f"),
                    "Var_Abs": st.column_config.NumberColumn("Variacion Absoluta", format="%.0f"),
                    "Var_Pct": st.column_config.NumberColumn("Variacion %", format="%.1f%%"),
                }
            )
            
        with dim_tabs[1]:
            st.subheader("Perspectiva de Gerencia (Top 15 Mayor Volumen)")
            top_ger = agg_gerencia_f.nlargest(15, "Forecast_5+7").sort_values("Forecast_5+7")
            st.plotly_chart(plot_bar_comparison(top_ger, "Gerencia", title=""), use_container_width=True)
            st.dataframe(
                agg_gerencia_f.sort_values("Forecast_5+7", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Forecast_5+7": st.column_config.NumberColumn("Forecast 5+7", format="%.0f"),
                    "Budget_FY": st.column_config.NumberColumn("Presupuesto Anual", format="%.0f"),
                    "Var_Abs": st.column_config.NumberColumn("Variacion Absoluta", format="%.0f"),
                    "Var_Pct": st.column_config.NumberColumn("Variacion %", format="%.1f%%"),
                }
            )
            
        with dim_tabs[2]:
            st.subheader("Perspectiva por Naturaleza del Gasto (Clasificacion)")
            st.plotly_chart(plot_bar_comparison(agg_classif_f, "Classif", title=""), use_container_width=True)
            st.dataframe(
                agg_classif_f[["Classif", "Forecast_5+7", "Budget_FY", "Var_Abs", "Var_Pct"]].sort_values("Forecast_5+7", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Forecast_5+7": st.column_config.NumberColumn("Forecast 5+7", format="%.0f"),
                    "Budget_FY": st.column_config.NumberColumn("Presupuesto Anual", format="%.0f"),
                    "Var_Abs": st.column_config.NumberColumn("Variacion Absoluta", format="%.0f"),
                    "Var_Pct": st.column_config.NumberColumn("Variacion %", format="%.1f%%"),
                }
            )
            
        with dim_tabs[3]:
            st.subheader("Perspectiva por Agrupacion Contable (CLASS)")
            if "CLASS" in forecast_lines_f.columns:
                agg_class_group = aggregate_forecast(forecast_lines_f, ["CLASS"])
                st.plotly_chart(plot_bar_comparison(agg_class_group, "CLASS", title=""), use_container_width=True)
            else:
                st.info("La dimension 'CLASS' no se encuentra disponible o no aplica a la segmentacion actual.")
                
        with dim_tabs[4]:
            st.subheader("Analisis de Partidas Criticas")
            st.markdown("Top 20 items de gasto con mayor desviacion absoluta contra el presupuesto.")
            top_dev = top_deviations(deviation_df_f, by="Var_vs_Budget_Abs", n=20)
            st.plotly_chart(
                plot_top_deviations(top_dev, label_col="Desc Item", deviation_col="Var_vs_Budget_Abs", pct_col="Var_vs_Budget_Pct", title="", n=20),
                use_container_width=True
            )

    # --- TAB 3: Tendencia Mensual ---
    with tabs[2]:
        st.title("Comportamiento y Tendencia Mensual")
        st.markdown("Visualizacion de la ejecucion en base a linea de tiempo (Serie cronologica consolidada).")
        
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
            
            st.markdown("### Tabla de Desarrollo Mensual")
            df_mensual = pd.DataFrame({
                "Mes Calendario": MONTH_NAMES,
                "Flujo Real / Proyectado": forecast_monthly,
                "Flujo Presupuestado": budget_monthly,
                "Flujo Forecast Oficial": official_monthly,
            })
            df_mensual["Desviacion Mensual"] = df_mensual["Flujo Real / Proyectado"] - df_mensual["Flujo Presupuestado"]
            st.dataframe(
                df_mensual,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Flujo Real / Proyectado": st.column_config.NumberColumn(format="%.0f"),
                    "Flujo Presupuestado": st.column_config.NumberColumn(format="%.0f"),
                    "Flujo Forecast Oficial": st.column_config.NumberColumn(format="%.0f"),
                    "Desviacion Mensual": st.column_config.NumberColumn(format="%.0f"),
                }
            )
        else:
            st.warning("El set de datos se encuentra vacio para los parametros seleccionados.")

    # --- TAB 4: Forecast 5+7 y Métodos ---
    with tabs[3]:
        st.title("Metodologia Analitica Aplicada")
        st.markdown("Evaluacion de rendimiento de los algoritmos predictivos ejecutados durante la fase de backtesting.")
        
        st.dataframe(
            resultados_backtesting.set_index("method"),
            use_container_width=True,
            column_config={
                "mape_mean": st.column_config.NumberColumn("Error MAPE (Promedio)", format="%.2f"),
                "mape_median": st.column_config.NumberColumn("Error MAPE (Mediana)", format="%.2f"),
                "rmse_mean": st.column_config.NumberColumn("Error RMSE (Promedio)", format="%.0f"),
                "rmse_median": st.column_config.NumberColumn("Error RMSE (Mediana)", format="%.0f"),
                "mae_mean": st.column_config.NumberColumn("Error MAE (Promedio)", format="%.0f"),
                "n_lines": st.column_config.NumberColumn("Volumen de Lineas Evaluadas"),
            }
        )
        
        st.markdown("### Rendimiento Grafico por Metrica")
        metrica_viz = st.selectbox("Seleccione Metrica de Error para Visualizacion:", ["rmse_mean", "mape_median", "mae_mean"])
        st.plotly_chart(plot_method_comparison(resultados_backtesting, metric=metrica_viz), use_container_width=True)
        
        st.markdown("---")
        st.markdown(f"""
        ### Fundamentos Tecnicos de la Optimizacion
        
        **Algoritmo seleccionado por el motor de inferencia: `{metodo_ganador}`**

        La plataforma ha evaluado multiples enfoques predictivos utilizando un proceso riguroso de *Backtesting Temporal*.
        Con 5 meses de historia real (Ene-May), el motor ocultó los ultimos periodos para medir la capacidad de
        cada algoritmo de predecir el futuro, comparando finalmente la proyeccion con la realidad ocultada.
        
        **Criterios de validacion subyacentes:**
        1. **Minimizacion de la varianza del error:** El metodo seleccionado presento el valor minimo en el Root Mean Square Error (RMSE), demostrando mayor precision para capturar volumenes reales de operacion.
        2. **Incorporacion de comportamiento base (Priors):** Metodos que escalan el presupuesto (ej. `budget_scaled`) son altamente efectivos en mineria, dado que heredan la estacionalidad operacional (como paradas de planta o mantenciones programadas) que los modelos estadisticos puros (como ARIMA o Holt) no pueden deducir con solo 5 datos iniciales.
        3. **Control de Outliers:** Se aplica una funcion de amortiguacion (damping factor) para evitar extrapolaciones exponenciales cuando un mes en particular presenta ejecuciones altamente atipicas.
        """)
        
        st.markdown("---")
        st.markdown("### Tabla Maestra de Salida (Itemizado Final)")
        st.dataframe(
            forecast_lines_f.sort_values("Forecast_5+7", ascending=False).head(500),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Forecast_5+7": st.column_config.NumberColumn("Proyeccion 5+7 Final", format="%.0f"),
                "Budget_FY": st.column_config.NumberColumn("Presupuesto Anual", format="%.0f"),
                "Var_Abs": st.column_config.NumberColumn("Variacion", format="%.0f"),
                "Var_Pct": st.column_config.NumberColumn("Desviacion Porcentual", format="%.1f%%"),
            }
        )

    # --- TAB 5: Comparaciones ---
    with tabs[4]:
        st.title("Ecosistema de Comparacion Estrategica")
        st.markdown("Contraste simultaneo entre el Modelo Estadistico (5+7), el Presupuesto Inicial (Budget FY) y la Declaracion Oficial (Forecast Oficial).")
        
        comp_df = compare_with_official(forecast_lines_f, group_cols=["Classif"])
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### Evaluacion 1: Modelo vs Presupuesto Base")
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Budget_FY", forecast_col="Forecast_5plus7", title=""), use_container_width=True)
        with col_c2:
            st.markdown("### Evaluacion 2: Modelo vs Cifra Oficial Declarada")
            st.plotly_chart(plot_bar_comparison(comp_df, x_col="Classif", budget_col="Forecast_Oficial", forecast_col="Forecast_5plus7", title=""), use_container_width=True)
            
        st.markdown("### Matriz Cruzada de Desempeno")
        st.dataframe(
            comp_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Budget_FY": st.column_config.NumberColumn("Presupuesto", format="%.0f"),
                "Forecast_Oficial": st.column_config.NumberColumn("Cifra Oficial", format="%.0f"),
                "Forecast_5plus7": st.column_config.NumberColumn("Proyeccion Modelo", format="%.0f"),
                "Var_5plus7_vs_Budget": st.column_config.NumberColumn("Delta vs PPto Abs", format="%.0f"),
                "Var_5plus7_vs_Budget_Pct": st.column_config.NumberColumn("Delta vs PPto %", format="%.1f%%"),
                "Var_5plus7_vs_Oficial": st.column_config.NumberColumn("Delta vs Oficial Abs", format="%.0f"),
                "Var_5plus7_vs_Oficial_Pct": st.column_config.NumberColumn("Delta vs Oficial %", format="%.1f%%"),
            }
        )

    # --- TAB 6: Hallazgos ---
    with tabs[5]:
        st.title("Informe Analitico y Recomendaciones de Gestion")
        
        st.markdown("""
        ### Diagnostico de Desempeno Operacional

        **1. Analisis General de Sub-ejecucion Financiera**
        La proyeccion inferida para el cierre del ano fiscal indica una desviacion consolidada negativa respecto del presupuesto aprobado. Esta tendencia se solidifica en los datos historicos reales del primer pentamestre (Enero a Mayo), donde un gran porcentaje de los centros de costo reportan atrasos en consumos de servicios de terceros y adjudicacion de repuestos.

        **2. Zonas de Riesgo Presupuestario (Sobregiros Identificados)**
        En contraste con la tendencia general, la partida contable relacionada al consumo de Energia (Power/Utilities) manifiesta una trayectoria acelerada. Los factores explicativos preliminares que la operacion debe auditar incluyen:
        * Descalces tarifarios de contratos de suministro de largo plazo.
        * Cambios no planificados en el perfil de carga o consumo de planta (potencia contratada vs demandada).

        **3. Comportamiento en Bienes e Insumos (Spares & Consumables)**
        Las variaciones hacia la baja (saving teorico) en insumos criticos no representan necesariamente un ahorro estructural. Es imperativo que control de gestion valide con mantenimiento si existen retrasos de inventario, dado que este gasto se trasladara inminentemente a meses posteriores (efecto rebote en el Q3/Q4).

        ---

        ### Plan de Accion y Propuesta de Mejora Estructural

        **Acciones de Corto Plazo (Proximo Ciclo Contable)**
        1. **Auditoria de Partidas Extremas**: Someter a revision de las gerencias operativas cualquier centro de costo o Item que, en la proyeccion 5+7, arroje una desviacion superior al +/- 20% respecto a su presupuesto original.
        2. **Regularizacion de 'Sandbagging'**: Mitigar practicas de proteccion presupuestaria en partidas como *Contractors*, donde tradicionalmente se exige presupuesto excesivo a inicio de ano que posteriormente no es ejecutado.

        **Mejoras al Modelo de Datos (Mediano Plazo)**
        3. **Enriquecimiento del Pool de Variables**: Integrar directamente variables de produccion (volumen de mineral tratado, ley de cabeza, precio de commodities, variaciones de tipo de cambio) dentro de un motor de regresion multiple para independizar la proyeccion de la variabilidad estacional pura.
        4. **Estratificacion del Factor de Ajuste**: Asignar perfiles algoritmicos dispares dependiendo de la fijeza del costo (Ej: Costo Laboral en modelo Lineal, Costo Contratistas en modelo Escalonado o Polinomial).
        """)

    # --- TAB 7: Exportar ---
    with tabs[6]:
        st.title("Modulo de Extraccion de Datos")
        st.markdown("Exporte el volumen de datos filtrado hacia plataformas secundarias de inteligencia de negocios o manejo de hojas de calculo.")
        
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            csv_data = forecast_lines_f.to_csv(index=False)
            st.download_button(
                label="Extraer Base de Datos (Formato CSV)", 
                data=csv_data, 
                file_name="Dataset_Proyecciones_Forecast.csv", 
                mime="text/csv", 
                use_container_width=True
            )
            
        with col_x2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                forecast_lines_f.to_excel(writer, sheet_name="Forecast_5plus7", index=False)
                agg_classif_f.to_excel(writer, sheet_name="Resumen_Clasificacion", index=False)
                agg_vp.to_excel(writer, sheet_name="Resumen_VP", index=False)
                resultados_backtesting.to_excel(writer, sheet_name="Evaluacion_Modelos", index=False)
                
            st.download_button(
                label="Extraer Libro Completo (Formato Excel)", 
                data=output.getvalue(), 
                file_name="Reporte_Consolidado_Forecast.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("### Pre-visualizacion de Datos Exportables")
        st.dataframe(forecast_lines_f.head(30), use_container_width=True, hide_index=True)


# ============================================================================
# ============================================================================
# MODULO 2: PROYECCION ESTRATEGICA 2027-2031
# ============================================================================
# ============================================================================

elif app_mode == "Proyeccion Estrategica (2027-2031)":
    st.title("Laboratorio de Proyeccion Estrategica y Largo Plazo (2027 - 2031)")
    st.markdown("Este motor algoritmico aísla las tendencias macroeconómicas de los presupuestos históricos aprobados, generando un modelo de proyección de gastos a 5 años. Se ha diseñado como una herramienta de simulación de escritorio para la planificación corporativa a largo plazo.")

    st.sidebar.subheader("Panel de Sensibilidad Macroeconomica")
    st.sidebar.markdown("Desplace los controles para inyectar choques macroeconomicos al modelo base proyectado:")
    
    slider_fuel = st.sidebar.slider("Ajuste Tasa Precio Diesel (%)", -40.0, 40.0, 0.0) / 100.0
    slider_power = st.sidebar.slider("Ajuste Tasa Costo Energia (%)", -30.0, 30.0, 0.0) / 100.0
    slider_dolar = st.sidebar.slider("Ajuste Volatilidad Tipo de Cambio (%)", -30.0, 30.0, 0.0) / 100.0

    @st.cache_data(show_spinner="Ejecutando motores de calculo para vectores quinquenales...")
    def load_strategic_budgets(path):
        """Carga las bases de datos correspondientes a planificaciones plurianuales anteriores."""
        b24 = pd.read_excel(path, sheet_name="BUDGET 2024 - 2028")
        b25 = pd.read_excel(path, sheet_name="BUDGET 2025 - 2029")
        b26 = pd.read_excel(path, sheet_name="BUDGET 2026 - 2030")
        return b24, b25, b26
    
    try:
        b24, b25, b26 = load_strategic_budgets(file_path)
    except Exception as e:
        st.error(f"Error critico de entrada/salida. Verifique que el archivo fuente contenga las hojas presupuestarias necesarias. Codigo de sistema: {e}")
        st.stop()

    try:
        # Extraccion flexible de descriptores jerarquicos base
        columnas_jerarquicas_base = ['CC', 'VP', 'Gerencia', 'Desc Proc', 'Desc Item', 'Classif']
        columnas_disponibles_en_b26 = [col for col in columnas_jerarquicas_base if col in b26.columns]
        df_modelo = b26[columnas_disponibles_en_b26].copy()
        
        # Definicion cronologica estandarizada
        meses_calendario = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Estructuracion de demandas por dataset historico
        columnas_req_b24 = ['CC', 'FY24', 'FY27', 'FY28'] + [f'{m}-24' for m in meses_calendario]
        columnas_req_b25 = ['CC', 'FY25', 'FY27', 'FY28', 'FY29'] + [f'{m}-25' for m in meses_calendario]
        columnas_req_b26 = ['CC', 'FY26', 'FY30'] + [f'{m}-26' for m in meses_calendario]

        # Inyeccion segura de dependencias (solo cruza lo que efectivamente existe en los excels)
        df24_valido = b24[[c for c in columnas_req_b24 if c in b24.columns]]
        df25_valido = b25[[c for c in columnas_req_b25 if c in b25.columns]]
        df26_valido = b26[[c for c in columnas_req_b26 if c in b26.columns]]

        # Ensamblaje progresivo (Left Join para mantener la cardinalidad de los centros de costo vivos en 2026)
        df_modelo = df_modelo.merge(df24_valido, on='CC', how='left')
        df_modelo = df_modelo.merge(df25_valido, on='CC', how='left', suffixes=('_b24', '_b25'))
        df_modelo = df_modelo.merge(df26_valido, on='CC', how='left')
        df_modelo.fillna(0, inplace=True)

        # Conversiones de tipo rigurosas para evadir fallos aritmeticos por tipos de datos 'Object'
        fy24_numerico = pd.to_numeric(df_modelo.get('FY24', 0), errors='coerce').fillna(0)
        fy25_numerico = pd.to_numeric(df_modelo.get('FY25', 0), errors='coerce').fillna(0)
        fy26_numerico = pd.to_numeric(df_modelo.get('FY26', 0), errors='coerce').fillna(0)
        
        fy27_b24_numerico = pd.to_numeric(df_modelo.get('FY27_b24', 0), errors='coerce').fillna(0)
        fy27_b25_numerico = pd.to_numeric(df_modelo.get('FY27_b25', 0), errors='coerce').fillna(0)
        
        fy28_b24_numerico = pd.to_numeric(df_modelo.get('FY28_b24', 0), errors='coerce').fillna(0)
        fy28_b25_numerico = pd.to_numeric(df_modelo.get('FY28_b25', 0), errors='coerce').fillna(0)
        
        fy29_numerico = pd.to_numeric(df_modelo.get('FY29', 0), errors='coerce').fillna(0)
        fy30_numerico = pd.to_numeric(df_modelo.get('FY30', 0), errors='coerce').fillna(0)

        # Modulo de inferencia de crecimiento tendencial y generacion de base extrapolada
        tasa_crecimiento_historica = ((fy25_numerico + 1e-6) / (fy24_numerico + 1e-6)).clip(0.9, 1.1)
        
        df_modelo['Proj_FY27'] = ((fy27_b24_numerico + fy27_b25_numerico) / 2.0) * tasa_crecimiento_historica
        df_modelo['Proj_FY28'] = ((fy28_b24_numerico + fy28_b25_numerico) / 2.0) * tasa_crecimiento_historica
        df_modelo['Proj_FY29'] = fy29_numerico * tasa_crecimiento_historica
        df_modelo['Proj_FY30'] = fy30_numerico * tasa_crecimiento_historica
        
        # Extrapolacion no lineal final hacia 2031 usando formula de valor futuro amortizado
        df_modelo['Proj_FY31'] = df_modelo['Proj_FY30'] * ((df_modelo['Proj_FY30'] + 1e-6) / (df_modelo['Proj_FY27'] + 1e-6)) ** (1/3)
        df_modelo['Proj_FY31'] = df_modelo['Proj_FY31'].fillna(df_modelo['Proj_FY30']).clip(df_modelo['Proj_FY30'] * 0.95, df_modelo['Proj_FY30'] * 1.05)

        # Inyeccion de matriz de sensibilidades basadas en keywords de cuentas
        def calcular_factor_estres_macro(row):
            desc_cuenta = str(row.get('Desc Item', '')).lower()
            factor_ajuste = 1.0
            if any(palabra in desc_cuenta for palabra in ['diesel', 'petroleo', 'combustible', 'fuel']): 
                factor_ajuste += slider_fuel
            if any(palabra in desc_cuenta for palabra in ['energia', 'electrica', 'power', 'suministro electrico']): 
                factor_ajuste += slider_power
            if any(palabra in desc_cuenta for palabra in ['contrato', 'repuesto', 'spare', 'licencia']): 
                factor_ajuste += slider_dolar
            return factor_ajuste

        df_modelo['Multiplicador_Estres'] = df_modelo.apply(calcular_factor_estres_macro, axis=1)

        # Multiplicacion final sobre vectores
        vectores_quinquenales = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']
        for anio_proyectado in vectores_quinquenales: 
            df_modelo[f'Final_{anio_proyectado}'] = df_modelo[f'Proj_{anio_proyectado}'] * df_modelo['Multiplicador_Estres']

        # Reparticion de estacionalidad para el primer año proyectado (2027) basandose en el mix historico trimestral
        for mes in meses_calendario:
            mes_24_num = pd.to_numeric(df_modelo.get(f'{mes}-24', 0), errors='coerce').fillna(0)
            mes_25_num = pd.to_numeric(df_modelo.get(f'{mes}-25', 0), errors='coerce').fillna(0)
            mes_26_num = pd.to_numeric(df_modelo.get(f'{mes}-26', 0), errors='coerce').fillna(0)
            
            ponderacion_mensual_historica = ((mes_24_num / (fy24_numerico + 1e-6)) + 
                                             (mes_25_num / (fy25_numerico + 1e-6)) + 
                                             (mes_26_num / (fy26_numerico + 1e-6))) / 3.0
            
            df_modelo[f'{mes}-27'] = df_modelo['Final_FY27'] * ponderacion_mensual_historica

        # Recorte de Dataframe para vista final de usuario
        columnas_estructurales = ['CC', 'VP', 'Gerencia', 'Desc Item', 'Classif']
        columnas_salida_final = [col for col in columnas_estructurales if col in df_modelo.columns] + [f'{mes}-27' for mes in meses_calendario] + [f'Final_{a}' for a in vectores_quinquenales]
        df_vista_final = df_modelo[columnas_salida_final].copy()

    except Exception as e:
        st.error(f"Falla tecnica en la conformacion matematica del dataframe predictivo. Mensaje del compilador: {e}")
        st.stop()

    # --- KPIs Y METRICAS DE SALIDA ---
    volumen_fy27_base = df_modelo['Proj_FY27'].sum()
    volumen_fy27_estresado = df_modelo['Final_FY27'].sum()
    diferencial_por_sliders = volumen_fy27_estresado - volumen_fy27_base
    volumen_fy31_cierre = df_modelo['Final_FY31'].sum()
    
    tasa_cagr = ((volumen_fy31_cierre / (volumen_fy27_estresado + 1e-6)) ** (1/4) - 1) * 100 if volumen_fy27_estresado > 0 else 0

    st.markdown("### Indicadores Macro de Impacto Financiero")
    st.markdown("Evaluacion global del comportamiento del gasto dadas las sensibilidades configuradas.")
    
    kp_col1, kp_col2, kp_col3 = st.columns(3)
    kp_col1.metric("Gasto OPEX Consolidado (Año 2027)", format_currency(volumen_fy27_estresado), 
                   delta=f"Efecto Simulacion: {format_currency(diferencial_por_sliders, abs_val=False)}", delta_color="inverse")
    kp_col2.metric("Gasto OPEX Estimado Cierre Quinquenal (Año 2031)", format_currency(volumen_fy31_cierre))
    kp_col3.metric("Tasa de Crecimiento Anual Compuesta (CAGR)", f"{tasa_cagr:.2f}%", 
                   delta="Velocidad de aceleracion del gasto", delta_color="off")

    st.markdown("---")

    # --- ENTORNO GRAFICO ESTUDIO LARGO PLAZO ---
    grafico_col1, grafico_col2 = st.columns(2)

    with grafico_col1:
        st.subheader("Estudio de Estacionalidad: Año Base vs Año 1 Proyectado")
        
        # Procesamiento numerico seguro para la grafica
        totales_mensuales_26 = [pd.to_numeric(df_modelo.get(f'{m}-26', 0), errors='coerce').sum() / 1e6 for m in meses_calendario]
        totales_mensuales_27 = [df_vista_final[f'{m}-27'].sum() / 1e6 for m in meses_calendario]
        
        df_grafica_estacional = pd.DataFrame({
            "Mes Operativo": meses_calendario * 2,
            "Monto Acumulado (MUSD)": totales_mensuales_26 + totales_mensuales_27,
            "Ciclo Financiero": ["2026 (Base de Partida)"] * 12 + ["2027 (Estimado Modelado)"] * 12
        })
        
        figura_estacionalidad = px.line(df_grafica_estacional, x="Mes Operativo", y="Monto Acumulado (MUSD)", color="Ciclo Financiero", 
                                        markers=True, color_discrete_sequence=['#ff7f0e', '#1f77b4'])
        st.plotly_chart(figura_estacionalidad, use_container_width=True)

    with grafico_col2:
        st.subheader("Estructura Quinquenal Acumulada por Segmento")
        
        if 'Classif' in df_vista_final.columns:
            df_tendencia_anual = df_vista_final[['Classif'] + [f'Final_{a}' for a in vectores_quinquenales]].copy()
            df_tendencia_pivotada = df_tendencia_anual.melt(id_vars=['Classif'], value_vars=[f'Final_{a}' for a in vectores_quinquenales], 
                                                            var_name='Ejercicio Fiscal', value_name='Inyeccion de Capital (MUSD)')
            
            # Normalizacion de los textos del eje x para presentacion ejecutiva
            df_tendencia_pivotada['Ejercicio Fiscal'] = df_tendencia_pivotada['Ejercicio Fiscal'].str.replace('Final_FY', '20')
            df_tendencia_pivotada['Inyeccion de Capital (MUSD)'] = df_tendencia_pivotada['Inyeccion de Capital (MUSD)'] / 1e6
            
            df_tendencia_agrupada = df_tendencia_pivotada.groupby(['Ejercicio Fiscal', 'Classif'])['Inyeccion de Capital (MUSD)'].sum().reset_index()
            
            figura_tendencia_barras = px.bar(df_tendencia_agrupada, x="Ejercicio Fiscal", y="Inyeccion de Capital (MUSD)", 
                                             color="Classif", text_auto='.1f', color_discrete_sequence=px.colors.qualitative.Pastel)
            
            st.plotly_chart(figura_tendencia_barras, use_container_width=True)
        else:
            st.info("La parametrizacion de la clasificacion ('Classif') no se encuentra estructurada en el archivo subido.")

    st.markdown("---")
    st.subheader("Bandeja de Extraccion Completa de Escenarios")
    st.markdown("Tabla de base de datos consolidada conteniendo la descomposicion linea a linea desde los centros de costo hacia el año 2031.")
    
    st.dataframe(df_vista_final.head(100), use_container_width=True)
    
    from io import BytesIO
    salida_buffer_memoria = BytesIO()
    with pd.ExcelWriter(salida_buffer_memoria, engine="openpyxl") as generador_excel: 
        df_vista_final.to_excel(generador_excel, sheet_name="Modelo Estrategico Base", index=False)
    
    st.download_button(
        label="Exportar Estructura Completa del Modelo a Excel", 
        data=salida_buffer_memoria.getvalue(), 
        file_name="Planificacion_Estrategica_Largo_Plazo_2027_2031.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
