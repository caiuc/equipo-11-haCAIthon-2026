# CLAUDE.md · Guía de Desarrollo para EnchufaTE

Bienvenido al repositorio de **EnchufaTE**, el motor inteligente de dimensionamiento tecno-económico para microrredes y electrificación rural off-grid en Chile (HaCAiThon 2026).

---

## 1. Estructura del Repositorio

```text
equipo-11-haCAIthon-2026/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Aplicación FastAPI, middleware CORS y configuración
│   │   ├── config.py                # Constantes técnicas, económicas (CLP) y fallback regional
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── weather.py           # Ingesta Open-Meteo API y curvas sintéticas
│   │   │   ├── demand.py            # Modelación de cargas, artefactos y corrientes de arranque
│   │   │   ├── sizing.py            # Motor de dimensionamiento solar, eólico, batería LiFePO4 e inversor
│   │   │   ├── economics.py         # Costos en CLP, BOM, Payback vs Diésel, LCOE y mitigación CO2
│   │   │   ├── sec_compliance.py   # Validación normativa SEC RIC N°09.1, RIC N°06 y memoria TE1
│   │   │   └── layout.py            # Recomendación de emplazamiento físico (Solar/Eólico/Baterías) vs. vivienda(s)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py           # Esquemas Pydantic para requests y responses
│   │   │   └── catalog.py           # Catálogo de electrodomésticos rurales y presets
│   │   └── api/
│   │       ├── __init__.py
│   │       └── endpoints.py         # Rutas REST (/dimensionar, /clima, /catalogo, /presets, /regiones)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py              # Tests de integración de endpoints REST
│   │   ├── test_demand.py           # Tests de demanda per cápita y artefactos
│   │   ├── test_economics.py        # Tests de costos CLP, Payback, LCOE y CO2
│   │   ├── test_sec.py              # Tests de reglas y validaciones SEC
│   │   ├── test_sizing.py           # Tests de fórmulas fotovoltaicas, eólicas y baterías
│   │   └── test_weather.py          # Tests de fallback y curvas meteorológicas
│   ├── requirements.txt             # Dependencias Python
│   └── run.py                       # Script de inicio del servidor backend
├── frontend/
│   ├── index.html                   # Interfaz interactiva con selector y diagramas
│   ├── styles.css                   # Sistema de diseño dark slate y modo stand 800x480
│   └── app.js                       # Lógica de cálculo reactivo y gráficos SVG
├── pytest.ini                       # Configuración de pytest
├── explicacion_producto.md          # Documento de visión y especificación inicial
├── instrucciones_desarrollo_ia.md   # Especificaciones técnicas completas para agentes
├── CLAUDE.md                        # Esta guía de desarrollo
└── README.md                        # Bases y contexto de la HaCAiThon 2026
```

---

## 2. Comandos Clave de Desarrollo

### 2.1. Instalación de Dependencias
```bash
pip install -r backend/requirements.txt
```

### 2.2. Ejecutar el Servidor Backend (FastAPI + Uvicorn)
```bash
python backend/run.py
```
O directamente con Uvicorn:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
- **Aplicación Web**: `http://localhost:8000`
- **Documentación Interactiva Swagger**: `http://localhost:8000/docs`
- **Documentación ReDoc**: `http://localhost:8000/redoc`

### 2.3. Ejecutar la Suite de Pruebas (Pytest)
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio
```
O de forma detallada:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v -p asyncio backend/tests
```

---

## 3. Principios de Ingeniería y Convenciones de Dominio

1. **Unidades de Energía y Potencia**:
   - Energía: $\text{Wh/día}$ para cargas individuales, $\text{kWh/día}$ y $\text{kWh/año}$ para balances globales.
   - Potencia: $\text{W}$ y $\text{kW}$ para consumo activo; $\text{kWp}$ para potencia pico de módulos solares; $\text{kVA}$ para inversores.
   - Radiación solar: $\text{GHI}$ en $\text{W/m}^2$ e integradas en Horas Solares Pico ($\text{HSP}$ o $\text{PSH}$ en $\text{kWh/m}^2/\text{día}$).
   - Viento: Velocidad a 10m en $\text{m/s}$.

2. **Criterios Físicos de Dimensionamiento**:
   - **Factor de Rendimiento Solar ($\eta_{\text{sys}}$)**: $0.78$ ($78\%$), considera coeficiente de temperatura de módulos, pérdidas óhmicas $\le 3\%$, suciedad y eficiencia MPPT.
   - **Inclinación Óptima**: $\text{Tilt} = |\text{Latitud}| \times 0.9\ (^\circ)$, **Azimut**: $0^\circ$ (Norte geográfico para Chile).
   - **Umbral Eólico**: Si velocidad media $v \ge 4.5\text{ m/s}$, se activa sistema híbrido solar-eólico con microturbina de $1.0\text{ kW}$.
   - **Batería $\text{LiFePO}_4$**: $\text{DoD} = 85\%$, $\eta_{\text{bat}} = 95\%$, autonomía $1.2\text{ días}$ (solar) o $1.0\text{ día}$ (híbrido).
   - **Inversor/Cargador**: Factor de sobrecarga mínimo $1.25 \times P_{\text{punta}}$.

3. **Contexto Económico y Normativo Chileno**:
   - Moneda principal: **Pesos Chilenos (CLP)** (tipo de cambio referencia: $950\text{ CLP/USD}$).
   - Generador Diésel de referencia: Consumo específico $0.35\text{ L/kWh}$, precio $1.250\text{ CLP/L}$, factor de mantenimiento $1.20\times$.
   - Factor de emisión: $2.68\text{ kg } CO_2/\text{L diésel}$, $45\text{ árboles/ton } CO_2$.
   - Normas SEC obligatorias:
     * **RIC N°09.1**: Canalizaciones DC/AC segregadas, seccionador DC bajo carga, descargadores de sobretensión Tipo II en DC y AC, diferencial Tipo A superinmunizado o Tipo B 30mA, rotulación de advertencia off-grid.
     * **RIC N°06**: Puesta a tierra $\le 20\ \Omega$ con unión equipotencial.
     * **Declaración TE1**: Memoria de cálculo, plano unilineal, licencia instalador SEC Clase A/B.

4. **Resiliencia ante Fallos de Conectividad**:
   - Siempre mantener la capacidad de operar offline utilizando la tabla de fallback regional chilena (`REGIONAL_CLIMATE_DEFAULTS` en `backend/app/config.py`).

5. **Escalado por Viviendas (no solo personas)**:
   - `DimensioningRequest.households` (1-200) escala la demanda, generación y BOM a un conjunto de
     viviendas/unidades idénticas, no solo a la cantidad de habitantes de una vivienda (`backend/app/core/demand.py`).

6. **Comparativa de 3 Configuraciones**:
   - El endpoint `/api/dimensionar` siempre calcula 3 configuraciones canónicas ("recomendada",
     "economica", "resiliente") vía `_compute_all_options` en `backend/app/api/endpoints.py`.
     `preferred_option` en el request decide cuál se devuelve como principal (BOM, SEC, TE1 incluidos);
     las otras dos se devuelven condensadas en `alternatives` (`SystemOption`).

7. **Emplazamiento Físico (`site_layout`)**:
   - `backend/app/core/layout.py` recomienda distancia, rumbo y área para el arreglo solar, la
     microturbina eólica y el banco de baterías respecto a la(s) vivienda(s), pensado para dibujarse
     sobre un mapa (Leaflet/OpenStreetMap en el frontend, tab "Plano de Instalación").

5. **Regla de la GUI (Frontend)**:
   - Para la exhibición en la Feria de Proyectos de la Hackathon, la interfaz cuenta con soporte/vista fijada internamente a **800x480** para pantallas táctiles de stand sin desajustes ni scroll lateral.

---

## 4. Reglas de Calidad y Estilo de Código

- **Tipado estricto**: Usar anotaciones de tipo completas en Python con modelos Pydantic (`backend/app/models/schemas.py`).
- **Inmutabilidad y validación**: Validar rangos geográficos (latitudes y longitudes dentro de Chile), potencias positivas y multiplicadores de arranque consistentes.
- **Asincronía**: Usar `async/await` y `httpx.AsyncClient` para llamadas de red externas.
- **Pruebas Continuas**: Cualquier cambio en fórmulas físicas o reglas SEC debe acompañarse de sus respectivos tests en `backend/tests/`.
