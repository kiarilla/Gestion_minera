# Metodologia - Forecast 5+7 Minero

## 1. Definicion del Forecast 5+7

El **Forecast 5+7** es una proyeccion de cierre de ano que combina:

- **5 meses de datos reales** (Enero - Mayo 2025)
- **7 meses de proyeccion** (Junio - Diciembre 2025)

Formalmente:

```
Forecast_5+7(FY) = Σ(real_ene, ..., real_may) + Σ(proy_jun, ..., proy_dic)
```

calculado a nivel de **linea de detalle** (Resp + Item + CC) y luego **agregado** por Total, VP, Gerencia, Classif, CLASS/GRUPOS e Item.

## 2. Origen y Estructura de los Datos

### 2.1 Archivo fuente

`data/02_Gastos_Proy_Mejor_01-2025.xlsx` -- Workbook Excel con 8 hojas.

### 2.2 Hojas utilizadas

| Hoja | Filas | Funcion |
|---|---|---|
| **Gastos** | 2,574 | Forecast detalle con reales Ene-May + proyeccion Jun-Dic + YTD, Forecast FY, Budget FY, Var, BYTD, Forecast Actual |
| **Budget** | 2,574 | Presupuesto mensualizado multi-anio: columnas mensuales Ene-Dic + FY25...FY29 + BYTD |
| **GRUPOS** | 98 | Mapeo RESPONSABILIDAD -> CLASS (RH, OP, OM, SG, SO, AS, PR) y GRUPOS (rangos) |
| **Pivote (2)** | Resumen | Pivote por Classif con Suma de YTD, Forecast FY, Budget FY, BYTD, Forecast Actual |
| **Tabla de Control** | 33 | Resumen por naturaleza de gasto con datos 2024 |
| **Pivot** | Resumen | Pivote por Gerencia/Responsabilidad |
| **Grafico** | Resumen | Totales Forecast FY por clasificacion |
| **Hoja2** | Resumen | Totales por naturaleza de gasto en kUSD |

### 2.3 Columnas clave

**Dimensiones** (comunes a Budget y Gastos):
- `Resp` (codigo), `Desc Resp` (nombre)
- `VP` (Vicepresidencia), `Gerencia`
- `Proc` (codigo proceso), `Desc Proc`
- `Item` (codigo), `Desc Item`
- `Classif` (Labor, Expenses, Contractors, Fuel, S&C, Power, Maintenance, Spare Parts, Rehandling, Water)
- `CC` (centro de costo)

**Mensuales** (12 columnas): `Jan-25` a `Dec-25`
- En hoja **Gastos**: Ene-May = **valores reales**, Jun-Dic = **proyeccion oficial** (forecast existente)
- En hoja **Budget**: Ene-Dic = **presupuesto mensualizado** (distribucion anual del budget)

**Metricas adicionales** (solo en Gastos):
- `YTD` = suma de reales Ene-May (verificado: YTD = Jan + Feb + Mar + Apr + May)
- `Forecast FY` = YTD + proyeccion Jun-Dic oficial
- `Budget FY` = presupuesto anual total
- `Var` = Forecast FY - Budget FY
- `BYTD` = Budget Year-to-Date (suma budget Ene-May)
- `Forecast Actual` = valor del mes de abril (Apr-25)

### 2.4 Verificacion de integridad

- **YTD = Σ(Jan...May)**: verificado con tolerancia < 1.0 por diferencias de redondeo
- **Forecast FY = YTD + Σ(Jun...Dic)**: verificado
- **BYTD (Gastos) = Σ budget Ene-May del Budget sheet**: verificado
- **FY25 (Budget) = Σ mensual Ene-Dic**: verificado
- **Classif validas**: Labor, Expenses, Contractors, Fuel, S&C, Power, Maintenance, Spare Parts, Rehandling, Water

### 2.5 Limpieza aplicada

1. **Strip de espacios** en todas las columnas string (muchos nombres tienen padding)
2. **Conversion a numerico** de columnas mensuales y metricas
3. **Eliminacion de filas total/subtotal**
4. **Manejo de NaN como 0** en operaciones de suma

## 3. Supuestos Fundamentales

### 3.1 Moneda
**Supuesto:** Los valores estan expresados en **USD** (dolares americanos). Esto se infiere de la hoja "Tabla de Control" donde aparece `Units = USD`. No hay confirmacion explicita en todas las hojas.

### 3.2 Valores reales
Los valores en las columnas `Jan-25` a `May-25` de la hoja **Gastos** representan **gastos reales incurridos** (actuals), no presupuesto ni forecast. Esto se verifica porque:
- Su suma coincide exactamente con la columna `YTD` (Year-to-Date)
- Difieren de los valores correspondientes en la hoja **Budget** (que contiene el presupuesto)
- La relacion `YTD/BYTD` (real/budget) varia significativamente por linea (0.0 a >10.0)

### 3.3 Proyeccion oficial
La proyeccion Jun-Dic en la hoja Gastos constituye el **Forecast oficial** de la compania. Se observa que utiliza un metodo de **run-rate** (valores constantes para Jun-Dic en muchas lineas), lo que justifica la necesidad de un modelo no lineal alternativo.

### 3.4 Perfil presupuestario como estacionalidad
El perfil mensual del **Budget** (hoja Budget, columnas Ene-Dic) se utiliza como informacion exogena de **estacionalidad operacional**. Refleja mantenciones programadas, campañas, ciclos productivos y contratos que el forecast debe respetar.

### 3.5 Corte temporal
Han transcurrido **5 meses** (Ene-May 2025). Restan 7 meses por proyectar.

## 4. Metodos de Proyeccion

### 4.1 Lineal / Run-rate (BENCHMARK)
```
Proy(t) = YTD / 5, para t = 6...12
```
Metodo ingenuo de referencia. No captura estacionalidad.

### 4.2 Perfil Presupuestario Reescalado (METODO SELECCIONADO)
```
r = Σ(real_1:5) / Σ(budget_1:5)           # ratio de ejecucion
r_damped = 1 + (r - 1) * damp_factor       # amortiguacion no lineal
Proy(t) = budget(t) * r_damped, t = 6...12
```

**Ventajas:**
- Preserva la forma estacional del presupuesto
- La amortiguacion evita extrapolar extremos (ej. un 200% de ejecucion en Ene-May no se proyecta linealmente a todo el ano)
- Interpretable: cada proyeccion se explica como "presupuesto ajustado por ejecucion observada"
- Robustez con pocos datos (usa 12 puntos del budget como prior)

**Parametro `damp_factor`**: por defecto 0.3 (conservador). Controla que tan fuerte se transmite el ratio de ejecucion a la proyeccion.
- 0.0 = ignora los reales, proyecta el budget puro
- 1.0 = scaling completo (riesgoso si el ratio es extremo)
- 0.3 = compromiso conservador (70% budget, 30% ajuste por ejecucion)

### 4.3 Regresion Polinomica (grado 2)
Ajusta un polinomio cuadratico a los 5 puntos reales y extrapola. **Problema:** con solo 5 puntos, el polinomio puede sobre-ajustar y producir extrapolaciones irreales (explosiones o colapsos). Se limita a valores >= 0.

### 4.4 Holt con Tendencia Amortiguada (Damped)
Suavizamiento exponencial de Holt (statsmodels) con `damped_trend=True`. Modela solo tendencia, sin estacionalidad (5 puntos son insuficientes). La tendencia amortiguada converge a una constante, evitando proyecciones lineales indefinidas.

### 4.5 Spline Cubico + Extrapolacion Amortiguada
Interpolacion por spline cubico natural sobre los 5 puntos, con extrapolacion amortiguada exponencialmente hacia la media observada para evitar divergencia (efecto Runge).

### 4.6 ARIMA(0,1,1)
Modelo ARIMA simple con una diferencia y una media movil. **Advertencia:** con solo 5 puntos, ARIMA no puede estimar componentes estacionales ni capturar patrones complejos. Se incluye con fines comparativos.

## 5. Backtesting y Seleccion

### 5.1 Procedimiento

Para cada linea de gasto y cada metodo:
1. **Entrenamiento:** meses 1-3 (Ene-Mar)
2. **Prediccion:** meses 4-5 (Abr-May)
3. **Evaluacion:** comparar prediccion vs valor real observado
4. **Metricas:** MAPE, RMSE, MAE

Se agregan las metricas por metodo (media y mediana).

### 5.2 Resultados

| Metodo | RMSE medio | MAPE mediano | Lineas |
|---|---|---|---|
| **budget_scaled** | **15,767** | 44.5% | 2,066 |
| linear | 16,208 | 33.3% | 2,066 |
| arima | 20,457 | 44.9% | 2,066 |
| holt_damped | 27,214 | 90.4% | 2,066 |
| spline_damped | 35,714 | 78.0% | 2,066 |
| polynomial | 137,739 | 100.0% | 2,066 |

### 5.3 Metodo seleccionado

**`budget_scaled`** -- menor RMSE global. Aunque `linear` tiene mejor MAPE mediano, el MAPE es volatil con montos pequenos y el RMSE es mas relevante para el error absoluto agregado (que es lo que importa en gestion presupuestaria).

### 5.4 Criterio de seleccion

- **RMSE** como metrica primaria (penaliza errores grandes, relevante para el total)
- **No linealidad** como requisito funcional (descarta linear)
- **Incorporacion de estacionalidad** como ventaja metodologica
- **Robustez** con datos limitados (descarta ARIMA, polynomial)

## 6. Agregacion

El Forecast 5+7 se calcula linea a linea y luego se agrega por:
- **Total** (suma de todas las lineas)
- **VP** (Vicepresidencia)
- **Gerencia**
- **Classif** (Labor, Expenses, etc.)
- **CLASS** (RH, OP, OM, SG, SO, AS, PR)
- **Item**

La agregacion es aritmetica (suma de proyecciones individuales).

## 7. Tecnologia

- **Python 3.12** con venv
- **pandas**: manipulacion de datos
- **numpy**: operaciones numericas
- **scipy**: interpolacion spline
- **scikit-learn**: regresion polinomica
- **statsmodels**: Holt-Winters, ARIMA
- **plotly**: graficos interactivos
- **streamlit**: aplicacion web
- **pytest**: testing
- **openpyxl**: lectura/escritura Excel
