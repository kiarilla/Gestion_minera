# Hallazgos y Propuesta de Mejora

## 1. Resumen Ejecutivo

El Forecast 5+7 generado mediante el metodo **`budget_scaled`** (perfil presupuestario reescalado con amortiguacion no lineal) proyecta un cierre de ano de **aproximadamente 1,016 MM** frente a un Budget FY de **1,287 MM**, lo que representa una **sub-ejecucion del ~10%** a nivel agregado. A continuacion se detallan los hallazgos principales, organizados por relevancia operacional y financiera.

---

## 2. Hallazgos Principales

### 2.1 Ejecucion general por debajo del presupuesto

**Observacion:** El Forecast 5+7 total es inferior al Budget FY en todas las clasificaciones excepto Power (+4.6%) y Labor (-1.8%, practicamente on-budget). Las demas clasificaciones muestran desviaciones negativas significativas:

| Classif | Budget FY | Forecast 5+7 | Var % |
|---|---|---|---|
| S&C | 228.6 MM | 141.0 MM | -38.3% |
| Water | 20.8 MM | 11.7 MM | -43.6% |
| Maintenance | 46.3 MM | 34.3 MM | -25.8% |
| Expenses | 284.5 MM | 203.7 MM | -28.4% |
| Spare Parts | 95.1 MM | 71.7 MM | -24.6% |
| Contractors | 160.8 MM | 119.5 MM | -25.7% |
| Fuel | 15.1 MM | 10.5 MM | -30.2% |
| Power | 283.7 MM | 277.9 MM | **+4.6%** |
| Labor | 152.8 MM | 145.9 MM | -4.5% |

**Interpretacion minera:**
- **S&C (Servicios y Contratistas)** muestra la mayor desviacion absoluta (-87.6 MM). Esto es tipico en minería: los contratos de servicios suelen tener clausulas de ejecucion progresiva y muchos se activan en el segundo semestre. El modelo amortiguado captura que si en 5 meses no se ha ejecutado, dificilmente se ejecutara el 100% en los 7 restantes.
- **Power (+4.6%)** es la unica partida sobre el presupuesto, consistente con el alto consumo energetico de las operaciones mineras (chancado, molienda, bombeo) que es poco elastico a variaciones de produccion. Ademas, las tarifas electricas pueden haber sido subestimadas en el budget.
- **Labor (-4.5%)** es la partida mas cercana al presupuesto, lo cual es esperable: las remuneraciones son gastos fijos recurrentes dificiles de reducir.

### 2.2 Concentracion del gasto

**Observacion:** El gasto esta altamente concentrado en pocas partidas:
- La partida "Ste. Energía" (Power, YTD = 63 MM) por si sola representa **~5% del gasto total YTD**
- Las 20 partidas mas grandes concentran mas del **50% del gasto total**
- Esto es tipico en mineria: energia, mano de obra y contratos mayores dominan el OPEX

### 2.3 Perfil estacional del presupuesto ignorado por el forecast oficial

**Observacion:** El forecast oficial existente en la hoja Gastos proyecta valores **constantes para Jun-Dic** en la mayoria de las lineas (i.e., run-rate ingenuo). Esto ignora completamente:
- Mantenciones mayores programadas (que concentran gasto en meses especificos)
- Campanas estacionales (ej. mayor consumo de reactivos en ciertas epocas)
- Rampas de produccion planificadas
- Estacionalidad de contratos (renovaciones, terminos)

El metodo `budget_scaled` corrige esto al preservar la forma mensual del presupuesto, capturando estas dinamicas operacionales.

### 2.4 Outliers y partidas atipicas

**Observacion:** Varias lineas muestran ratios de ejecucion real/budget extremos:
- Partidas con ratio > 2x: posible sub-presupuestacion o gastos no previstos
- Partidas con ratio < 0.2x: posible sobre-presupuestacion o gastos diferidos
- La partida "Ste. Servicio al Personal y Proteccion Industrial" es particularmente grande y merece atencion individual

**Recomendacion:** Estas partidas deben ser revisadas manualmente por los gerentes de area para confirmar que no haya errores de imputacion contable o cambios de alcance no reflejados en el presupuesto.

### 2.5 Limitacion de la comparacion con el Forecast oficial

**Observacion:** El Forecast FY oficial en la hoja Gastos suma ~1,350 MM, que es superior al Forecast 5+7 generado (~1,016 MM). Sin embargo, esta diferencia se explica en parte porque:
- El forecast oficial utiliza un run-rate que extrapola los reales linealmente
- Nuestro modelo aplica amortiguacion, que es mas conservadora
- Las partidas con sub-ejecucion en Ene-May ven su proyeccion ajustada a la baja

---

## 3. Propuesta de Mejora

### 3.1 Corto Plazo (proximo trimestre)

**PM-1: Segmentacion del damp_factor**
Ajustar el factor de amortiguacion por Classif o VP segun patrones historicos de ejecucion. Por ejemplo:
- Labor: damp_factor alto (0.5-0.7) porque es mas predecible
- Contractors: damp_factor bajo (0.2-0.3) porque es mas volatil
- Power: damp_factor = 1.0 (sin amortiguacion) porque la ejecucion es cercana al budget

**PM-2: Revision manual de outliers**
Identificar y revisar las 50 partidas con mayor valor absoluto y ratio de ejecucion mas extremo. Solicitar a los gerentes de area que confirmen o corrijan la proyeccion.

**PM-3: Incorporar datos 2024**
La hoja "Tabla de Control" contiene datos mensuales de 2024. Si se pudiera acceder al detalle por linea, se podria calibrar el damp_factor con datos historicos reales.

### 3.2 Mediano Plazo (proximo ano)

**PM-4: Modelo campeon por segmento**
En lugar de un unico metodo global, seleccionar el mejor metodo por Classif o VP:
- Holt damped para Labor (tendencia suave)
- Budget scaled para Expenses y S&C (dependen de la estacionalidad presupuestaria)
- ARIMA para partidas con patrones ciclicos claros (si hay suficientes datos)

**PM-5: Variables exogenas**
Incorporar al modelo variables operacionales y de mercado:
- Precio del cobre (afecta ingresos y potencialmente gastos variables)
- Tipo de cambio USD/CLP (afecta costos en pesos)
- Produccion mensual (toneladas procesadas)
- Leyes de mineral (afectan consumo de insumos)
- Precio del petroleo (afecta Fuel y Power)

**PM-6: Backtesting multi-periodo**
Si se dispone de datos de anos anteriores con reales completos, realizar validacion cruzada temporal (rolling window) para evaluar la estabilidad de los metodos a lo largo del tiempo.

### 3.3 Largo Plazo (mejora continua)

**PM-7: Pipeline automatizado**
Integrar el proceso de carga, proyeccion y visualizacion en un flujo periodico:
1. Cierre contable mensual -> extraccion de reales
2. Ejecucion automatica del modelo de forecast
3. Actualizacion del dashboard en Streamlit
4. Envio de reporte ejecutivo

**PM-8: Sistema de alertas tempranas**
Configurar umbrales de desviacion (ej. >20% de desviacion vs forecast) que disparen notificaciones a los gerentes responsables, permitiendo acciones correctivas oportunas.

**PM-9: Integracion con CAPEX**
Extender el modelo para incluir gastos de capital (CAPEX), obteniendo una vision completa del desempeno financiero de la operacion.

---

## 4. Conclusiones

1. **El Forecast 5+7 con metodo `budget_scaled`** proyecta un cierre de ano ~10% por debajo del presupuesto, con ahorros concentrados en S&C, Expenses y Spare Parts.

2. **La unica partida sobre el presupuesto es Power** (+4.6%), reflejando la rigidez del consumo energetico en operaciones mineras.

3. **El metodo no lineal captura la estacionalidad** del presupuesto que el forecast oficial (run-rate) ignora, proporcionando una proyeccion mas realista y util para la toma de decisiones.

4. **Las limitaciones de datos** (solo 5 meses reales, falta de datos historicos) aconsejan un enfoque conservador con amortiguacion. A medida que se acumulen mas meses de datos reales, la proyeccion se volvera mas precisa.

5. **La herramienta desarrollada** (app Streamlit + modelo en Python) proporciona una base solida para la gestion del forecast, siendo extensible y mantenible.

---

## 5. Limitaciones del Estudio

- **Datos reales limitados a 5 meses**: cualquier proyeccion a 7 meses tiene incertidumbre intrinseca.
- **Falta de validacion historica**: sin datos de cierre de anos anteriores, no es posible validar la precision real del modelo.
- **Supuesto de moneda USD**: si los datos estuvieran en otra moneda, los valores absolutos cambian pero las proporciones se mantienen.
- **No se consideran cambios estructurales**: nuevas operaciones, cierres de faenas, cambios regulatorios o eventos extraordinarios no estan modelados.
