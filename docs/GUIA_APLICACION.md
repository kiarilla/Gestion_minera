# Guía Completa de la Aplicación - Forecast 5+7 Minero

## Índice

1. [Visión General](#1-visión-general)
2. [Origen y Procesamiento de Datos](#2-origen-y-procesamiento-de-datos)
3. [Estructura de la Aplicación](#3-estructura-de-la-aplicación)
4. [Tab 1: Resumen Ejecutivo](#4-tab-1-resumen-ejecutivo)
5. [Tab 2: Análisis por Dimensión](#5-tab-2-análisis-por-dimensión)
6. [Tab 3: Tendencia Mensual](#6-tab-3-tendencia-mensual)
7. [Tab 4: Forecast 5+7](#7-tab-4-forecast-5+7)
8. [Tab 5: Comparaciones](#8-tab-5-comparaciones)
9. [Tab 6: Hallazgos y Propuesta de Mejora](#9-tab-6-hallazgos-y-propuesta-de-mejora)
10. [Tab 7: Exportar Datos](#10-tab-7-exportar-datos)
11. [Sidebar: Filtros y Controles](#11-sidebar-filtros-y-controles)
12. [Modelos de Proyección Explicados](#12-modelos-de-proyección-explicados)

---

## 1. Visión General

### ¿Qué es esta aplicación?

Una herramienta interactiva de **proyección financiera** para los gastos operacionales (OPEX)
de una compañía minera. Permite visualizar, analizar y exportar el **Forecast 5+7**:
una proyección de cierre de año que combina **5 meses de datos reales** (Enero a Mayo 2025)
con una **proyección no lineal de 7 meses** (Junio a Diciembre 2025).

### ¿Para qué sirve?

- **Gestión presupuestaria**: identificar desviaciones entre lo gastado y lo presupuestado
- **Toma de decisiones**: detectar partidas con sub-ejecución o sobre-ejecución tempranamente
- **Re-forecast**: ajustar las proyecciones de cierre de año con datos reales
- **Rendición de cuentas**: generar reportes comparativos Budget vs Real vs Forecast

### ¿Cómo se navega?

La aplicación se organiza en **7 pestañas (tabs)** horizontales en la parte superior,
más una **barra lateral (sidebar)** a la izquierda con filtros y controles.

```
+------------------------------------------------------------------+
|  [1.Resumen] [2.Análisis] [3.Tendencia] [4.Forecast] ... [7.Exportar] |
+------------------------------------------------------------------+
| Sidebar  |                                                       |
| Filtros  |         CONTENIDO DE LA PESTAÑA ACTIVA                |
| VP       |                                                       |
| Classif  |                                                       |
| CLASS    |                                                       |
| Método   |                                                       |
| Botones  |                                                       |
+----------+-------------------------------------------------------+
```

---

## 2. Origen y Procesamiento de Datos

### 2.1 Archivo fuente

**`data/02_Gastos_Proy_Mejor_01-2025.xlsx`** — Workbook Excel de 8 hojas
con los gastos operacionales de una compañía minera (presumiblemente Pucobre).

### 2.2 Hojas del workbook y qué contiene cada una

| Hoja | Filas | Función | ¿Usada por la app? |
|---|---|---|---|
| **Gastos** | 2,574 | **Forecast detalle** con valores reales (Ene–May) y proyección oficial (Jun–Dic). Incluye YTD, Forecast FY, Budget FY, Var, BYTD y Forecast Actual. | **Sí — datos principales** |
| **Budget** | 2,574 | **Presupuesto mensualizado multi-año**. Contiene el perfil mensual del presupuesto (Ene–Dic) y los totales anuales FY25 a FY29. | **Sí — perfil estacional** |
| **GRUPOS** | 98 | **Mapeo de dimensiones**. Cruza cada `RESPONSABILIDAD` con `CLASS` (RH, OP, OM, SG, SO, AS, PR) y `GRUPOS` (rangos como "1 - 6", "5 - 10"). | **Sí — enriquecimiento de datos** |
| **Pivote (2)** | 15 | Tabla dinámica resumen por clasificación (`Classif`), filtrada a `Classif = Expenses`. Muestra YTD, Forecast FY, Budget FY, BYTD. | Sí — referencia |
| **Tabla de Control** | 33 | Resumen de gastos por naturaleza con datos de 2024 y comparativa. | No |
| **Pivot** | 11 | Otra tabla dinámica resumen por responsabilidad/gerencia. | No |
| **Grafico** | ~12 | Resumen Forecast FY por clasificación. | No |
| **Hoja2** | ~12 | Resumen por naturaleza de gasto en kUSD. | No |

### 2.3 Columnas principales de la hoja "Gastos" (forecast)

#### Columnas dimensionales (describen cada línea de gasto)
| Columna | Descripción | Ejemplo |
|---|---|---|
| `Resp` | Código de responsabilidad | `1000` |
| `Desc Resp` | Nombre de la responsabilidad | `Presidencia Ejecutiva` |
| `VP` | Vicepresidencia | `CEO`, `VP - Operaciones Planta` |
| `Gerencia` | Gerencia | `Gerente Contralor` |
| `Proc` | Código de proceso | `1001` |
| `Desc Proc` | Nombre del proceso | `Dpto. Dirección Compañía` |
| `Item` | Código de ítem de gasto | `3101` |
| `Desc Item` | Nombre del ítem | `Remuneraciones Supervisión` |
| `Classif` | Clasificación del gasto | `Labor`, `Expenses`, `Power`… |
| `CC` | Centro de costo | `100010013101` |

#### Clasificaciones (`Classif`) existentes

| Classif | Descripción | Ejemplos en minería |
|---|---|---|
| **Labor** | Mano de obra | Remuneraciones, beneficios |
| **Expenses** | Gastos generales | Pasajes, hoteles, representación |
| **Contractors** | Contratistas | Servicios externalizados |
| **Fuel** | Combustibles | Petróleo, gas, lubricantes |
| **S&C** | Servicios y Contratistas | Mantención, aseo, seguridad |
| **Power** | Energía eléctrica | Consumo eléctrico de la planta |
| **Maintenance** | Mantención | Repuestos, reparaciones mayores |
| **Spare Parts** | Repuestos | Componentes de desgaste |
| **Rehandling** | Remanejo | Movimiento de materiales |
| **Water** | Agua | Suministro y tratamiento |

#### Columnas mensuales y de métricas
| Columna | Significado | ¿Real o Proyectado? |
|---|---|---|
| `Jan-25` a `May-25` | Gasto mensual | **Real** (incurrido) |
| `Jun-25` a `Dec-25` | Gasto mensual | **Proyectado** (forecast oficial existente) |
| `YTD` (Year-to-Date) | Suma de reales Ene–May | **Real** (verificado: = suma de los 5 meses) |
| `Forecast FY` | Forecast del año completo | Proyección oficial de la compañía |
| `Budget FY` | Presupuesto anual | Presupuesto original aprobado |
| `Var` | Variación | `Forecast FY - Budget FY` (aprox) |
| `BYTD` | Budget Year-to-Date | Presupuesto acumulado Ene–May |
| `Forecast Actual` | Valor de abril | `Apr-25` (valor del último mes con dato real completo) |

### 2.4 La hoja "Budget" (presupuesto mensualizado)

Contiene las mismas columnas dimensionales que "Gastos", pero sus columnas mensuales
representan el **presupuesto aprobado distribuido por mes** (no los valores reales).

| Columna | Significado |
|---|---|
| `Jan-25` a `Dec-25` | Presupuesto mensualizado para cada mes |
| `FY25` a `FY29` | Presupuesto anual total para cada año fiscal |
| `BYTD` | Budget Year-to-Date = suma del presupuesto Ene–May |

**Diferencia clave con "Gastos"**: en "Budget", los valores de Ene–May son el **presupuesto**,
mientras que en "Gastos" los valores de Ene–May son el **gasto real**.

### 2.5 La hoja "GRUPOS" (mapeo de dimensiones)

Mapea cada responsabilidad a dos categorías adicionales:

| Columna | Valores posibles | Significado |
|---|---|---|
| `RESPONSABILIDAD` | `VP - RRHH`, `VP - Operaciones Planta`, … | Nombre de la responsabilidad (clave de cruce) |
| `CLASS` | `RH`, `OP`, `OM`, `SG`, `SO`, `AS`, `PR` | Clase organizacional |
| `GRUPOS` | `"1 - 6"`, `"5 - 10"`, `"13"`, … | Rango (probablemente dotación de personal) |

**Significado de CLASS**:
- `RH`: Recursos Humanos
- `OP`: Operaciones Planta
- `OM`: Operaciones Mina
- `SG`: Legal, Asuntos Corporativos
- `SO`: Gestión de Activos / Servicios
- `AS`: Administración y Servicios
- `PR`: Proyectos y Desarrollo

### 2.6 Procesamiento aplicado a los datos

Antes de ser usados por la aplicación, los datos pasan por el siguiente pipeline (`src/data_loader.py`):

#### Paso 1: Carga desde Excel
```python
df = pd.read_excel(path, sheet_name="Gastos")   # o "Budget" o "GRUPOS"
```

#### Paso 2: Limpieza de strings
Se eliminan **espacios sobrantes** en todas las columnas de texto. Los nombres de
responsabilidades y gerencias en el archivo original tienen padding con espacios
que dificultan los cruces y búsquedas. Ejemplo:

```
Antes: "VP - RRHH                               "
Después: "VP - RRHH"
```

#### Paso 3: Conversión a numérico
Todas las columnas mensuales (`Jan-25`, `Feb-25`, …) y de métricas (`YTD`, `Forecast FY`, …)
se convierten a tipo numérico. Valores no convertibles se reemplazan por `NaN`.

#### Paso 4: Eliminación de filas total/subtotal
Se remueven filas sin código de responsabilidad (`Resp` nulo) o que contengan "TOTAL".

#### Paso 5: Cruce con GRUPOS
Las hojas "Gastos" y "Budget" se cruzan con la hoja "GRUPOS" usando `Desc Resp` ↔ `RESPONSABILIDAD`.
Esto agrega las columnas `CLASS` y `GRUPOS` a cada línea de gasto, permitiendo análisis
por estas dimensiones organizacionales adicionales.

#### Paso 6: Verificación de integridad
El módulo de tests (`tests/test_data_loader.py`) verifica automáticamente:
- `YTD = suma de Jan-25 a May-25` (24 tests confirman esto)
- `Forecast FY = YTD + suma de Jun-25 a Dec-25`
- `FY25 (Budget) = suma de los 12 meses`
- `BYTD (Budget) = suma de Jan-25 a May-25 (Budget)`
- No hay CLASS nulos después del merge
- Las clasificaciones (`Classif`) solo toman valores válidos

---

## 3. Estructura de la Aplicación

### 3.1 Flujo de carga

Al iniciar la aplicación, ocurre lo siguiente:

```
┌─────────────────────────────────────────────────────────────┐
│  1. Verificar si existe caché en data/cache/                │
│     ┌──────────────┐     ┌──────────────────────────┐      │
│     │  SÍ hay caché │────▶│ Cargar resultados desde  │      │
│     │               │     │ disco (Parquet/JSON)     │      │
│     └──────────────┘     │ • Resultados backtesting  │      │
│                          │ • Forecast 5+7 completo   │      │
│     ┌──────────────┐     │ • Metadatos (KPIs, etc.)  │      │
│     │ NO hay caché  │     └──────────────────────────┘      │
│     │               │                                       │
│     └──────┬────────┘     ┌──────────────────────────┐      │
│            └──────────────▶│ Mostrar botón            │      │
│                            │ "Ejecutar Modelos"       │      │
│                            └──────┬───────────────────┘      │
│                                   │ Clic                     │
│                                   ▼                          │
│                            ┌──────────────────────────┐      │
│                            │ Ejecutar backtesting y    │      │
│                            │ generar forecast.         │      │
│                            │ Guardar a data/cache/.    │      │
│                            └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Datos cacheados en memoria

Streamlit usa `@st.cache_data` para que los datos del workbook y los resultados
de backtesting no se recalculen en cada interacción. Sin embargo, el backtesting
completo (6 métodos × 2,066 líneas) tarda ~60 segundos, por lo que también se
persiste a disco con `model_store.py`.

---

## 4. Tab 1: Resumen Ejecutivo

### Propósito
Vista de alto nivel para la gerencia. Muestra los KPIs principales y gráficos
agregados que resumen la situación financiera proyectada.

### Elementos

#### 4.1 Tarjetas de KPIs (4 métricas principales)

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Budget FY      │ │  Forecast 5+7    │ │  Real YTD        │ │ Forecast Oficial │
│                  │ │                  │ │  (Ene-May)       │ │                  │
│  1,287,497,204   │ │  1,157,527,220   │ │  469,847,232     │ │  1,349,715,611   │
│                  │ │  -10.1% vs Budg  │ │  36.5% del Budg  │ │  -14.2% vs 5+7   │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘
```

| KPI | Cálculo | Interpretación |
|---|---|---|
| **Budget FY** | Suma de `Budget FY` de todas las líneas | Presupuesto anual aprobado |
| **Forecast 5+7** | Suma del forecast generado por el modelo | Proyección de cierre de año |
| **Real YTD (Ene-May)** | Suma de `Jan-25` a `May-25` en hoja Gastos | Gasto real incurrido |
| **Forecast Oficial** | Suma de `Forecast FY` en hoja Gastos | Forecast original de la compañía |

El **delta** (número verde/rojo abajo) indica:
- **Rojo (negativo)**: el Forecast 5+7 es menor que el Budget (sub-ejecución = ahorro potencial)
- **Verde (positivo)**: el Forecast 5+7 supera el Budget (sobre-ejecución = riesgo)

#### 4.2 Treemap: Composición por Clasificación

```
┌───────────────────────────────────────────────────────────┐
│                  COMPOSICIÓN POR CLASIFICACIÓN             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                                                     │  │
│  │   ┌──────────────┐  ┌────────────┐                  │  │
│  │   │              │  │            │                  │  │
│  │   │    Power     │  │  Expenses  │  ┌────────────┐  │  │
│  │   │   296.7 MM   │  │  238.8 MM  │  │   S&C      │  │  │
│  │   │              │  │            │  │   182.7 MM │  │  │
│  │   └──────────────┘  └────────────┘  │            │  │  │
│  │                                      └────────────┘  │  │
│  │   ┌──────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │   │   Labor      │  │Contractors │  │ Spare Parts│  │  │
│  │   │   150.1 MM   │  │  138.1 MM  │  │   82.7 MM  │  │  │
│  │   └──────────────┘  └────────────┘  └────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

**Qué muestra**: cada rectángulo representa una clasificación de gasto. El área
es proporcional al monto del Forecast 5+7. El color indica la desviación
porcentual vs Budget:
- **Azul**: sobre el presupuesto (más gasto del esperado)
- **Rojo**: bajo el presupuesto (menos gasto del esperado)
- **Blanco**: cercano al presupuesto

**Cómo leerlo**:
- Power ocupa el área más grande → es la partida más significativa
- Power está azul → está sobre el presupuesto (+4.6%)
- S&C está muy rojo → alta sub-ejecución (-38.3%)

#### 4.3 Barras agrupadas: Forecast 5+7 vs Budget por VP

```
┌───────────────────────────────────────────────────────────┐
│           FORECAST 5+7 VS BUDGET POR VP                    │
│                                                            │
│  VP - Operaciones Planta  ████████████████                 │
│                            ░░░░░░░░░░░░░░░░░░              │
│                                                            │
│  VP - Operaciones Mina     ██████████                      │
│                             ░░░░░░░░░░░░░                  │
│                                                            │
│  VP - Gestion de Activos   ████████                        │
│                              ░░░░░░░░░░                    │
│       ...                                                  │
│                                                            │
│  ██ = Forecast 5+7    ░░ = Budget FY                       │
└───────────────────────────────────────────────────────────┘
```

**Qué muestra**: comparación directa entre el Forecast 5+7 (barras azules)
y el Budget FY (barras celestes) para las 10 Vicepresidencias con mayor presupuesto.

**Cómo leerlo**: si la barra Forecast es más corta que Budget = VP está gastando
menos de lo presupuestado (ahorro). Si es más larga = sobre-ejecución.

#### 4.4 Waterfall: Budget FY → Forecast 5+7

```
┌───────────────────────────────────────────────────────────┐
│             WATERFALL: BUDGET FY A FORECAST 5+7            │
│                                                            │
│  1,287 MM ──┐                                              │
│             │  ┌── -87.6 MM (S&C)                          │
│             ├──┤  ┌── -80.7 MM (Expenses)                  │
│             │  ├──┤  ┌── -45.7 MM (Spare Parts)            │
│             │  │  ├──┤  ┌── -43.1 MM (Contractors)         │
│             │  │  │  ├──┤  ┌── +13.1 MM (Power) ◀── único↑│
│             │  │  │  │  └──┤                                │
│             │  │  │  │     └─── 1,016 MM ─── Forecast 5+7  │
│             ▼  ▼  ▼  ▼     ▼                               │
│  Verde = sub-ejecución    Rojo = sobre-ejecución           │
└───────────────────────────────────────────────────────────┘
```

**Qué muestra**: cómo se pasa del Budget FY (barra inicial) al Forecast 5+7
(barra final), desglosando las variaciones por clasificación.

**Cómo leerlo**:
- Barras **verdes hacia abajo** = clasificaciones donde se proyecta gastar
  **menos** que el presupuesto (sub-ejecución = ahorro)
- Barras **rojas hacia arriba** = clasificaciones donde se proyecta gastar
  **más** que el presupuesto (sobre-ejecución = mayor costo)
- La barra final azul = Forecast 5+7 total
- **Power es la única que sube** (única sobre el presupuesto)

---

## 5. Tab 2: Análisis por Dimensión

### Propósito
Desglose detallado del Forecast 5+7 por múltiples dimensiones organizacionales,
permitiendo identificar qué áreas, gerencias o tipos de gasto están impulsando
las desviaciones.

### Sub-pestañas

#### 5.1 "Por VP" — Desglose por Vicepresidencia

**Gráfico**: Barras agrupadas (Forecast 5+7 vs Budget FY) para cada VP.

**Tabla**: Columnas con valores exactos:
| VP | Forecast 5+7 | Budget FY | Var Abs | Var % |
|---|---|---|---|---|
| VP - Operaciones Planta | 450 MM | 500 MM | -50 MM | -10.0% |

**Interpretación**: Permite ver a nivel de VP cuál está más lejos del presupuesto.

#### 5.2 "Por Gerencia" — Top 15 Gerencias

**Gráfico**: Barras horizontales de las 15 gerencias con mayor Forecast 5+7.

**Tabla**: Todas las gerencias ordenadas por Forecast 5+7 descendente.

**Interpretación**: Identifica qué gerencias concentran el mayor gasto y cuáles
tienen las mayores desviaciones.

#### 5.3 "Por Classif" — Desglose por Clasificación

**Gráfico**: Barras agrupadas por tipo de gasto (Labor, Expenses, Power, etc.).

**Interpretación**: Muestra la composición del gasto por naturaleza. En minería,
es esperable que Power y Labor dominen el OPEX.

#### 5.4 "Por CLASS" — Desglose por Clase Organizacional

**Gráfico**: Barras agrupadas por CLASS (OP, OM, AS, etc.).

**Interpretación**: Agrupa por función organizacional (Operaciones Planta,
Operaciones Mina, Administración, etc.), permitiendo ver qué área funcional
tiene mayor peso en el gasto.

#### 5.5 "Top Items" — 20 Ítems con Mayor Desviación

**Gráfico**: Barras horizontales mostrando los 20 ítems de gasto con la mayor
diferencia absoluta entre Forecast 5+7 y Budget FY.

**Colores**:
- **Rojo**: el ítem proyecta un gasto menor al presupuesto (sub-ejecución)
- **Verde**: el ítem proyecta un gasto mayor al presupuesto (sobre-ejecución)

**Etiquetas**: cada barra muestra el porcentaje de desviación (ej. `-35.2%`).

**Interpretación**: Aquí se identifican las partidas específicas que requieren
atención gerencial. Por ejemplo, si "Ste. Servicio al Personal y Protección
Industrial" aparece como la mayor desviación negativa, puede indicar que un
contrato de servicios no se ha ejecutado al ritmo presupuestado.

---

## 6. Tab 3: Tendencia Mensual

### Propósito
Visualizar la serie temporal mes a mes: cómo se han comportado los gastos reales
en los primeros 5 meses y cómo se proyectan para los 7 meses restantes.

### Gráfico de líneas

```
┌───────────────────────────────────────────────────────────┐
│              TENDENCIA MENSUAL                             │
│                                                            │
│  Monto │                                                   │
│        │  ●──●──●                                         │
│        │  │   │  │  ●──●──●──●──●──●──●  (Forecast 5+7)  │
│        │  │   │  │                                      │ │
│        │  ●──●──●  │                                      │
│        │            ●──●──●──●──●──●──●  (Budget FY)      │
│        │                                                   │
│        │  ●──●──●──●──● │                                  │
│        │                 ●──●──●──●──●──●──●  (Oficial)   │
│        │                                                   │
│        │  ┊                                                │
│        │  ┊  Línea vertical = fin de datos reales (Mayo)   │
│        │  ┊                                                │
│        └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──▶ Mes         │
│          Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic   │
│          ├──────────────┼────────────────────────┤        │
│          │  5 REALES    │  7 PROYECTADOS         │        │
└───────────────────────────────────────────────────────────┘
```

**Tres líneas**:
1. **Forecast 5+7 (azul)**: valores reales Ene–May + proyección del modelo Jun–Dic del método seleccionado
2. **Budget FY (celeste punteado)**: presupuesto mensualizado de la hoja Budget
3. **Forecast Oficial (naranja punteado)**: forecast original de la compañía

**Línea vertical en Mayo**: separa visualmente los meses reales de los proyectados.

**Cómo leerlo**:
- La forma de la línea después de Mayo es la "firma" del modelo
- Si la línea azul sube en meses específicos (ej. Septiembre), refleja mantenciones programadas
- Si la línea azul es plana, es una proyección run-rate (poco informativa)
- La comparación con el Budget muestra si la estacionalidad esperada se está cumpliendo

### Tabla de detalle mensual

Incluye los valores numéricos de cada serie para cada mes, permitiendo
inspeccionar las diferencias mes a mes:

| Mes | Real / Proyección | Budget Mensual | Forecast Oficial | Var vs Budget |
|---|---|---|---|---|
| Ene | 185,400,000 | 178,200,000 | 185,400,000 | +7,200,000 |
| Feb | 152,300,000 | 165,100,000 | 152,300,000 | -12,800,000 |
| ... | ... | ... | ... | ... |

---

## 7. Tab 4: Forecast 5+7 (Métodos y Selección)

### Propósito
Mostrar la comparación cuantitativa de los 6 métodos de proyección evaluados,
justificar la elección del método ganador, y presentar el forecast línea por línea.

### Elementos

#### 7.1 Método ganador

Muestra el nombre del método seleccionado automáticamente por menor RMSE en backtesting.
Típicamente: **`budget_scaled`** (Perfil Presupuestario Reescalado con Amortiguación No Lineal).

#### 7.2 Tabla Comparativa de Métodos

| Método | MAPE Media | MAPE Mediana | RMSE Media | RMSE Mediana | MAE Media | Líneas |
|---|---|---|---|---|---|---|
| linear | 306.9% | 33.3% | 16,208 | 902 | 13,899 | 2,066 |
| **budget_scaled** | 314.2% | 44.5% | **15,767** | 1,154 | 14,104 | 2,066 |
| polynomial | 942.3% | 100.0% | 137,739 | 4,910 | 126,234 | 2,066 |
| holt_damped | 383.2% | 90.4% | 27,214 | 1,959 | 25,124 | 2,066 |
| spline_damped | 318.9% | 78.0% | 35,714 | 1,950 | 31,017 | 2,066 |
| arima | 376.0% | 44.9% | 20,457 | 1,276 | 18,596 | 2,066 |

**Qué significan las métricas**:

| Métrica | Nombre completo | Interpretación |
|---|---|---|
| **MAPE** | Mean Absolute Percentage Error | Error porcentual promedio. 44% significa que en promedio el modelo se equivoca en un 44% del valor real. Muy sensible a valores pequeños. |
| **RMSE** | Root Mean Squared Error | Error cuadrático medio. Penaliza errores grandes. Mejor métrica para el agregado total. **Métrica primaria de selección.** |
| **MAE** | Mean Absolute Error | Error absoluto promedio. Fácil de interpretar en las mismas unidades que los datos. |

**¿Por qué MAPE tiene valores tan altos (300-900%)?** Muchas líneas de gasto
tienen montos pequeños (ej. $100 de pasajes). Si el modelo predice $50, el error
porcentual es 50%. Si predice $200, es 100%. Al promediar todos estos errores,
los porcentajes se disparan. Por eso **RMSE es la métrica principal de selección**:
pondera más los ítems con montos grandes, que son los que realmente importan
para el total agregado.

#### 7.3 Comparación Visual de Métodos

Gráfico de barras horizontales que permite elegir qué métrica visualizar
(selector desplegable: RMSE, MAPE mediano, MAE).

**Cómo leerlo**: barras más cortas = mejor método para esa métrica.

#### 7.4 Justificación de la Elección

Texto explicativo detallando por qué se eligió `budget_scaled`:

1. **Menor RMSE global**: es la métrica más relevante porque el error absoluto
   en el total agregado es lo que importa para la gestión presupuestaria.

2. **No lineal**: a diferencia del método lineal (run-rate) que simplemente
   promedia los meses pasados, `budget_scaled` preserva la estacionalidad del
   presupuesto, capturando mantenciones programadas, campañas y ciclos operacionales.

3. **Robustez**: con solo 5 meses de datos reales, los métodos estadísticos
   tradicionales (ARIMA, Holt-Winters) no tienen suficientes observaciones
   para estimar componentes estacionales. `budget_scaled` compensa esto usando
   los 12 meses del presupuesto como información exógena.

4. **Interpretabilidad**: cada proyección se puede explicar con una fórmula simple:
   `Proyección = Presupuesto_restante × f(ratio_ejecución)`, donde `f` amortigua
   ratios extremos hacia 1.0.

#### 7.5 Forecast por Línea

Tabla interactiva con todas las líneas de gasto, mostrando:

| Desc Item | Classif | Ene | Feb | … | Dic | Forecast 5+7 | Budget FY | Var Abs | Var % |
|---|---|---|---|---|---|---|---|---|---|
| Remuneraciones Supervisión | Labor | 37,029 | 32,159 | … | 35,881 | 425,997 | 425,997 | 0 | 0.0% |
| Pasajes Nacionales | Expenses | 2,424 | 3,465 | … | 2,116 | 25,396 | 36,000 | -10,604 | -29.5% |

La tabla está ordenada por Forecast 5+7 descendente. Es completamente desplazable
y permite inspeccionar cualquier línea de gasto en detalle.

---

## 8. Tab 5: Comparaciones

### Propósito
Comparar el Forecast 5+7 generado por nuestro modelo contra:
- El Budget FY (presupuesto original)
- El Forecast Oficial (proyección de la compañía)

identificando dónde nuestro modelo difiere de ambas referencias.

### Elementos

#### 8.1 Comparación por Clasificación (gráficos lado a lado)

```
┌─────────────────────────────┐ ┌─────────────────────────────┐
│  Forecast 5+7 vs Budget FY  │ │ Forecast 5+7 vs Oficial     │
│                             │ │                             │
│  Power  ████████░░░░░░      │ │  Power  ████████░░░░░░      │
│  Labor  ████████░░░░░░      │ │  Labor  ████████░░░░░░      │
│  S&C    ████████░░░░░░░░    │ │  S&C    ████████░░░░░░      │
│                             │ │                             │
│  ██ = Forecast 5+7          │ │  ██ = Forecast 5+7          │
│  ░░ = Budget FY             │ │  ░░ = Forecast Oficial      │
└─────────────────────────────┘ └─────────────────────────────┘
```

**Izquierda**: nuestro modelo vs presupuesto.
**Derecha**: nuestro modelo vs forecast oficial de la compañía.

Si las barras izquierdas son más cortas = nuestro modelo es más conservador que
el presupuesto. Si las derechas son diferentes = nuestro modelo difiere del oficial.

#### 8.2 Tabla Comparativa

Incluye columnas calculadas:

| Classif | Budget FY | Forecast Oficial | Forecast 5+7 | Var 5+7 vs Budget | Var 5+7 vs Oficial |
|---|---|---|---|---|---|
| Power | 283.7 MM | 296.7 MM | 296.7 MM | +13.0 MM (+4.6%) | 0.0 MM (0.0%) |
| S&C | 228.6 MM | 182.7 MM | 141.0 MM | -87.6 MM (-38.3%) | -41.7 MM (-22.8%) |

**Columnas de variación**:
- `Var 5+7 vs Budget`: diferencia entre nuestro modelo y el presupuesto. Negativo = ahorro.
- `Var 5+7 vs Oficial`: diferencia entre nuestro modelo y el forecast de la compañía.

#### 8.3 Top Desviaciones vs Budget (por Ítem)

Gráfico de barras horizontales con los 20 ítems de mayor desviación absoluta
entre Forecast 5+7 y Budget FY. Complementa la vista similar del Tab 2,
pero aquí en el contexto de la comparación global.

---

## 9. Tab 6: Hallazgos y Propuesta de Mejora

### Propósito
Documentar los hallazgos clave del análisis y proponer mejoras accionables,
alimentando la presentación ejecutiva y la toma de decisiones.

### Contenido

#### 9.1 Hallazgos Principales (5 hallazgos)

1. **Ejecución por debajo del presupuesto**: el Forecast 5+7 proyecta un cierre
   ~10% bajo el Budget FY. Power es la única clasificación sobre el presupuesto (+4.6%).

2. **Concentración del gasto**: pocas partidas concentran la mayor parte del OPEX.
   "Ste. Energía" por sí sola representa ~5% del gasto total YTD.

3. **Estacionalidad ignorada por el forecast oficial**: el forecast de la compañía
   usa valores constantes para Jun–Dic (run-rate). Nuestro modelo captura la
   forma mensual del presupuesto.

4. **Outliers**: partidas con ratios de ejecución real/budget extremos (>2x o <0.2x)
   que requieren revisión manual por posible error de imputación o cambio de alcance.

5. **Limitación de datos**: con 5 meses de reales, los métodos estadísticos clásicos
   tienen poca capacidad predictiva. El enfoque híbrido es el más robusto.

#### 9.2 Propuesta de Mejora (9 propuestas organizadas por plazo)

**Corto plazo** (3 propuestas):
- Segmentar el factor de amortiguación por clasificación
- Revisar manualmente las 50 partidas con mayor desviación
- Incorporar datos de 2024 para calibrar el modelo

**Mediano plazo** (3 propuestas):
- Implementar modelo campeón por segmento (distinto método por Classif)
- Incorporar variables exógenas (precio del cobre, tipo de cambio, producción)
- Backtesting multi-período con datos históricos

**Largo plazo** (3 propuestas):
- Pipeline automatizado de forecast mensual
- Sistema de alertas tempranas por desviación
- Integración con CAPEX

---

## 10. Tab 7: Exportar Datos

### Propósito
Permitir la descarga de los resultados en formatos utilizables fuera de la aplicación.

### Opciones de descarga

| Formato | Contenido | Uso típico |
|---|---|---|
| **CSV** | Forecast 5+7 línea por línea | Análisis en Excel, Python, etc. |
| **Excel** | 4 hojas: Forecast 5+7, Por Classif, Por VP, Métodos | Reporte completo para compartir |

**Hojas del Excel**:
1. `Forecast_5plus7`: todas las líneas con proyección mensual y anual
2. `Por_Classif`: agregado por clasificación de gasto
3. `Por_VP`: agregado por vicepresidencia
4. `Metodos`: tabla comparativa de los 6 métodos con métricas

### Vista previa

Antes de descargar, la tabla muestra las primeras 100 líneas del forecast
ordenadas por monto, permitiendo verificar que los datos son los esperados.

---

## 11. Sidebar: Filtros y Controles

### Filtros disponibles

```
┌─────────────────────────────┐
│  ⛏ Forecast 5+7             │
│  ─────────────────────────  │
│  Vicepresidencia (VP)       │
│  ┌───────────────────────┐  │
│  │ Todas              ▼ │  │
│  └───────────────────────┘  │
│                             │
│  Clasificación (Classif)    │
│  ┌───────────────────────┐  │
│  │ Todas              ▼ │  │
│  └───────────────────────┘  │
│                             │
│  CLASS (Grupos)             │
│  ┌───────────────────────┐  │
│  │ Todas              ▼ │  │
│  └───────────────────────┘  │
│  ─────────────────────────  │
│  Método de proyección       │
│  ┌───────────────────────┐  │
│  │ budget_scaled      ▼ │  │
│  └───────────────────────┘  │
│  ─────────────────────────  │
│  Método ganador (RMSE):     │
│  budget_scaled              │
│  ─────────────────────────  │
│  [ Re-ejecutar Modelos ]    │
└─────────────────────────────┘
```

#### Filtro: Vicepresidencia (VP)
Filtra TODOS los datos mostrados en la aplicación a una VP específica.
Útil para que cada VP vea solo sus números.

**Ejemplo**: seleccionar "VP - Operaciones Mina" muestra solo las líneas
de gasto de esa vicepresidencia. Los KPIs, gráficos y tablas se recalculan.

#### Filtro: Clasificación (Classif)
Filtra por tipo de gasto: Labor, Expenses, Contractors, Fuel, S&C, Power, etc.

**Ejemplo**: seleccionar "Power" para analizar exclusivamente el gasto energético.

#### Filtro: CLASS (Grupos)
Filtra por clase organizacional: RH, OP, OM, SG, SO, AS, PR.

**Ejemplo**: seleccionar "OP" para ver solo Operaciones Planta.

#### Selector: Método de proyección
Permite cambiar el método usado para generar el Forecast 5+7 **sin re-ejecutar
el backtesting**. Cambia instantáneamente los resultados en todas las pestañas.

**Ejemplo**: cambiar de `budget_scaled` a `holt_damped` para ver cómo cambiaría
el forecast con otro método.

#### Botón: Re-ejecutar Modelos
Borra la caché en disco y vuelve a ejecutar el backtesting completo con los 6 métodos.
Se usa cuando:
- Los datos de entrada cambiaron (se actualizó el Excel)
- Se quiere regenerar la caché desde cero
- Hubo un error en la ejecución anterior

---

## 12. Modelos de Proyección Explicados

### 12.1 ¿Por qué 6 métodos?

Para el Forecast 5+7 se implementan 6 métodos de proyección distintos. El
objetivo es **compararlos cuantitativamente** (mediante backtesting) y
**seleccionar el mejor** según métricas de error. El método ganador
es el que se usa para generar el forecast final.

### 12.2 Descripción de cada método

#### 1. Lineal / Run-rate (BENCHMARK)

```
Proy(jun-dic) = promedio(real_ene, ..., real_may)
```

**Cómo funciona**: toma el promedio de los 5 meses reales y lo repite
para los 7 meses restantes. Es el método más simple posible.

**Ventaja**: rápido, nunca falla.
**Desventaja**: ignora completamente la estacionalidad. Si en Marzo hubo una
mantención mayor (gasto alto), ese pico "contamina" todos los meses futuros.

**Rol en la app**: **solo como referencia**. No se usa como forecast final.

---

#### 2. Perfil Presupuestario Reescalado (budget_scaled) ⭐ GANADOR

```
Paso 1: ratio = real_EneMay / budget_EneMay
        (¿qué % del presupuesto se ejecutó realmente?)

Paso 2: ratio_amortiguado = 1.0 + (ratio - 1.0) × 0.3
        (amortiguar el ratio hacia 1.0 para no extrapolar extremos)

Paso 3: proy(jun-dic) = budget(jun-dic) × ratio_amortiguado
        (multiplicar el presupuesto restante por el ratio ajustado)
```

**Cómo funciona**: usa el perfil mensual del presupuesto como "molde estacional"
y lo escala según qué tan rápido se ha ejecutado el gasto en los primeros 5 meses.

**Ejemplo concreto**:
- Presupuesto Ene–May: $100,000
- Gasto real Ene–May: $80,000 (solo el 80% del presupuesto)
- Ratio de ejecución: 80,000 / 100,000 = 0.80
- Ratio amortiguado: 1.0 + (0.80 - 1.0) × 0.3 = 0.94
- Si el presupuesto para Junio es $20,000 → proyección Junio = $20,000 × 0.94 = $18,800

**Por qué 0.3**: el factor de amortiguación (`damp_factor = 0.3`) evita que
un ratio extremo (ej. 200% de ejecución) se extrapole ingenuamente. Con 0.3,
el ratio se "acerca" a 1.0 en un 70%. Es conservador y adecuado para minería.

**Ventajas**:
- Captura la **estacionalidad del presupuesto** (mantenciones, campañas, ciclos)
- **Robusto** con pocos datos (usa 12 meses del presupuesto como información adicional)
- **Interpretable**: se puede explicar cada proyección
- **No lineal**: la amortiguación es una transformación no lineal del ratio

**Por qué gana**: tiene el menor RMSE en backtesting. Al predecir los meses 4-5
usando solo meses 1-3, es el método que comete el menor error absoluto promedio.

---

#### 3. Regresión Polinómica (grado 2)

```
y = ax² + bx + c  (ajustado a los 5 puntos reales)
proy(mes_t) = a·t² + b·t + c
```

**Cómo funciona**: ajusta una parábola a los 5 puntos reales y la extrapola.

**Problema**: con solo 5 puntos, la parábola puede "explotar" hacia arriba o abajo.
Es el peor método en backtesting (RMSE 137,739). Solo se incluye con fines
comparativos.

---

#### 4. Holt con Tendencia Amortiguada

```
Nivel(t) = α·real(t) + (1-α)·[Nivel(t-1) + Tendencia(t-1)]
Tendencia(t) = β·[Nivel(t) - Nivel(t-1)] + (1-β)·φ·Tendencia(t-1)
Proy(t+h) = Nivel(t) + (φ + φ² + ... + φʰ)·Tendencia(t)
```

**Cómo funciona**: suavizamiento exponencial que modela nivel y tendencia.
La tendencia se "amortigua" (φ < 1), por lo que las proyecciones convergen a
una constante en lugar de crecer/decrecer indefinidamente.

**Limitación**: sin componente estacional (5 puntos son insuficientes para
estimar estacionalidad). Solo captura tendencia.

---

#### 5. Spline Cúbico + Extrapolación Amortiguada

```
Spline: curva suave que pasa exactamente por los 5 puntos reales
Extrapolación: se amortigua exponencialmente hacia la media observada
```

**Cómo funciona**: dibuja una curva cúbica suave a través de los 5 puntos reales
y la extiende hacia el futuro. La extrapolación se "frena" amortiguándola hacia
el promedio de los valores reales para evitar divergencia.

**Problema**: la extrapolación de splines sin datos que la anclen puede producir
oscilaciones (efecto Runge). La amortiguación ayuda pero no elimina el problema.

---

#### 6. ARIMA(0,1,1)

```
Δy(t) = y(t) - y(t-1)              (diferencia de primer orden)
Δy(t) = ε(t) + θ·ε(t-1)            (media móvil de orden 1)
```

**Cómo funciona**: modela las diferencias entre meses consecutivos como una
media móvil de los errores de predicción.

**Advertencia**: con solo 5 puntos, ARIMA no puede estimar estacionalidad (necesita
al menos 2 ciclos completos = 24 meses). Se incluye solo con fines comparativos
y se documenta su limitación.

---

### 12.3 Backtesting: ¿cómo se evalúa cada método?

```
┌─────────────────────────────────────────────────────┐
│              PROCEDIMIENTO DE BACKTESTING            │
│                                                      │
│  Datos disponibles: Ene  Feb  Mar  Abr  May          │
│                     [───Train───][─Test─]            │
│                                                      │
│  Para cada línea de gasto:                           │
│    1. Entrenar modelo con Ene, Feb, Mar              │
│    2. Predecir Abr, May                              │
│    3. Comparar predicción vs valor real de Abr y May │
│    4. Calcular MAPE, RMSE, MAE                       │
│                                                      │
│  Agregar métricas de las 2,066 líneas por método     │
│  Seleccionar el método con menor RMSE                │
└─────────────────────────────────────────────────────┘
```

Esto simula la situación real: si estuviéramos en Marzo, ¿qué método habría
predicho mejor Abril y Mayo? El que mejor predijo el pasado cercano es el
que usamos para predecir el futuro (Jun–Dic).

---

## Apéndice A: Glosario de Términos

| Término | Significado |
|---|---|
| **OPEX** | Gastos operacionales (Operating Expenses). Costos recurrentes de la operación minera. |
| **CAPEX** | Gastos de capital (Capital Expenditures). Inversiones en activos fijos. |
| **Forecast 5+7** | Proyección que combina 5 meses de datos reales con 7 meses proyectados. |
| **YTD** | Year-to-Date. Acumulado del año hasta la fecha. |
| **BYTD** | Budget Year-to-Date. Presupuesto acumulado hasta la fecha. |
| **Run-rate** | Proyección lineal ingenua: "lo gastado hasta ahora, multiplicado por 12/5". |
| **MAPE** | Mean Absolute Percentage Error. Error porcentual absoluto medio. |
| **RMSE** | Root Mean Squared Error. Raíz del error cuadrático medio. |
| **MAE** | Mean Absolute Error. Error absoluto medio. |
| **Backtesting** | Evaluación de un modelo predictivo usando datos históricos. |
| **Damping / Amortiguación** | Técnica que reduce el impacto de valores extremos en la proyección. |
| **VP** | Vicepresidencia. Unidad organizacional de alto nivel. |
| **Classif** | Clasificación del gasto (Labor, Expenses, Power, etc.). |
| **CLASS** | Clase organizacional desde el mapeo GRUPOS (OP, OM, AS, etc.). |
| **Estacionalidad** | Patrón que se repite en los mismos meses cada año (ej. mantenciones en Septiembre). |

## Apéndice B: Archivos del Proyecto

| Archivo | Función |
|---|---|
| `app.py` | Punto de entrada de la aplicación Streamlit |
| `src/data_loader.py` | Carga, limpieza y cruce de datos del Excel |
| `src/forecast.py` | 6 métodos de proyección + backtesting + selección |
| `src/metrics.py` | Métricas de error (MAPE, RMSE, MAE) |
| `src/insights.py` | Cálculo de desviaciones, KPIs y comparaciones |
| `src/viz.py` | Funciones de gráficos Plotly |
| `src/model_store.py` | Persistencia de resultados en disco (caché) |
| `tests/test_data_loader.py` | 24 tests de carga de datos |
| `tests/test_forecast.py` | 36 tests de modelos de forecast |
| `data/cache/` | Resultados cacheados (backtesting, forecast, metadatos) |
| `docs/METODOLOGIA.md` | Metodología detallada del modelo |
| `docs/HALLAZGOS.md` | Hallazgos y propuesta de mejora |
| `docs/GUIA_APLICACION.md` | Este documento |
| `requirements.txt` | Dependencias Python con versiones fijadas |
| `README.md` | Resumen del proyecto e instrucciones de instalación |
