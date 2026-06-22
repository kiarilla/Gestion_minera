# Forecast 5+7 - Proyeccion de Gastos Mineros

Aplicacion de proyeccion no lineal de gastos operacionales (OPEX) para compania minera. Combina 5 meses de datos reales (Ene-May 2025) con 7 meses de proyeccion (Jun-Dic 2025) usando metodos estadisticos que capturan estacionalidad y tendencia.

## Estructura del Proyecto

```
proyecto-forecast-minera/
├── app.py                  # Entrypoint Streamlit
├── src/
│   ├── data_loader.py      # Carga, limpieza y cruce de datos
│   ├── forecast.py         # Modelos de proyeccion no lineal + backtesting
│   ├── metrics.py          # Metricas de error (MAPE, RMSE, MAE)
│   ├── insights.py         # Calculo de desviaciones y KPIs
│   └── viz.py              # Funciones de graficos Plotly
├── tests/
│   ├── test_data_loader.py # Tests de carga de datos (24 tests)
│   └── test_forecast.py    # Tests de modelos de forecast (36 tests)
├── data/
│   └── 02_Gastos_Proy_Mejor_01-2025.xlsx
├── docs/
│   ├── METODOLOGIA.md      # Metodologia completa
│   └── HALLAZGOS.md        # Hallazgos y propuesta de mejora
├── requirements.txt
└── .gitignore
```

## Instalacion

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd proyecto-forecast-minera

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno (Windows)
venv\Scripts\activate
# o (Linux/Mac)
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Verificar que el archivo de datos existe
ls data/02_Gastos_Proy_Mejor_01-2025.xlsx
```

## Ejecucion

### Aplicacion Streamlit

```bash
streamlit run app.py
```

La app se abrira en `http://localhost:8501` con 7 secciones:
1. **Resumen Ejecutivo** - KPIs y graficos de alto nivel
2. **Analisis por Dimension** - Desglose por VP, Gerencia, Classif, CLASS
3. **Tendencia Mensual** - Serie real + proyeccion vs budget
4. **Forecast 5+7** - Comparacion de metodos y seleccion
5. **Comparaciones** - Forecast vs Budget vs Forecast Oficial
6. **Hallazgos** - Analisis y propuesta de mejora
7. **Exportar** - Descarga en CSV/Excel

### Tests

```bash
pytest tests/ -v
```

Resultado esperado: **60 tests pasan** (24 de data_loader, 36 de forecast).

## Metodo de Proyeccion

El metodo seleccionado es **`budget_scaled`** (perfil presupuestario reescalado con amortiguacion no lineal):

```
Forecast(t) = Budget(t) * f(ratio_ejecucion)
donde f(r) = 1 + (r - 1) * damp_factor
```

**Ventajas:**
- Preserva la estacionalidad del presupuesto (mantenciones, campanas, ciclos)
- Amortigua ratios de ejecucion extremos (evita extrapolaciones ingenuas)
- Robusto con pocos datos reales (usa 12 meses de budget como prior)
- Interpretable para gestion

## Resultados Principales

| Metrica | Valor |
|---|---|
| Budget FY Total | 1,287 MM |
| Forecast 5+7 Total | ~1,016 MM |
| Desviacion vs Budget | -10.1% |
| Real YTD (Ene-May) | ~470 MM |
| % Avance Real | ~36.5% |

**Hallazgo clave:** Power es la unica clasificacion sobre el presupuesto (+4.6%), mientras que S&C muestra la mayor sub-ejecucion (-38.3%).

## Dependencias

- Python 3.12+
- pandas, numpy, openpyxl
- streamlit, plotly
- scikit-learn, statsmodels, scipy
- pytest

Ver `requirements.txt` para versiones exactas.

## Documentacion

- [Metodologia completa](docs/METODOLOGIA.md)
- [Hallazgos y propuesta de mejora](docs/HALLAZGOS.md)
