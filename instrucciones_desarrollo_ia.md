# Instrucciones de Desarrollo para Agentes IA · EnchufaTE

> **Proyecto**: EnchufaTE — Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid en Chile  
> **Evento**: HaCAiThon 2026 · Centro de Alumnos de Ingeniería UC (CAi)  
> **Temática**: Energía Renovable y Electrificación Rural  
> **Moneda y Normativa**: Pesos Chilenos (CLP) · Normativa SEC (RIC N°09.1 / RIC N°06 / Declaración TE1)

---

## 1. Visión General del Producto

**EnchufaTE** es una plataforma tecno-económica para acelerar la electrificación limpia, autónoma y confiable en sectores rurales y aislados de Chile (viviendas familiares, postas de salud, escuelas rurales, predios agrícolas y refugios patagónicos).

A partir de cualquier coordenada geográfica en el territorio nacional o de una localidad seleccionada, el sistema:
1. Consulta datos climáticos en tiempo real vía **Open-Meteo API** (radiación solar $GHI$ y velocidad de viento a 10m).
2. Modela paramétricamente la demanda horaria y picos de arranque inductivo de la instalación.
3. Evalúa la factibilidad y sinergia solar-eólica.
4. Dimensiona de forma óptima los paneles solares fotovoltaicos, microturbina eólica, banco de baterías $\text{LiFePO}_4$ e inversor/cargador 48V.
5. Calcula los costos reales en **CLP**, el ahorro de combustible diésel, mitigación de $CO_2$, payback y LCOE.
6. Valida y genera el expediente normativo para la declaración **TE1** ante la **Superintendencia de Electricidad y Combustibles (SEC)** bajo las normas **RIC N°09.1** y **RIC N°06**.

---

## 2. Arquitectura del Backend y Pipeline de Procesamiento

```text
┌───────────────────────────────────────────────────────────────┐
│                    1. Coordenadas (Lat / Lng)                 │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│              2. Ingesta de Recursos Climatológicos            │
│  Open-Meteo API (Radiación GHI -> HSP/PSH + Viento a 10m)     │
│  Fallback: Matriz climática regional de las 16 regiones Chile │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│             3. Modelación Paramétrica de Demanda              │
│  - Carga per cápita base: 350 Wh/persona/día                  │
│  - Catálogo de artefactos rurales (Refrig., Starlink, Bomba)  │
│  - Cálculo de Energía Diaria Total (Edaily) y Potencia Pico   │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│           4. Evaluación de Factibilidad y Mix Renovable       │
│  - Si Viento medio < 4.5 m/s -> Sistema 100% Fotovoltaico     │
│  - Si Viento medio >= 4.5 m/s -> Híbrido Solar + Eólico       │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│      5. Motor de Optimización y Dimensionamiento Físico       │
│  - Paneles FV: Ppv = Edaily / (HSP * 0.78), Inclinación/Azimut│
│  - Baterías LiFePO4: DoD 85%, Autonomía 1.2 días, Efic. 95%   │
│  - Inversor Off-Grid 48V: Factor sobrecarga 1.25 s/pico       │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│        6. Análisis Económico (CLP) e Impacto Ambiental        │
│  - CAPEX (Equipos + 18% BOS + Montaje e Ingeniería SEC TE1)   │
│  - Ahorro Diésel (0.35 L/kWh, $1.250 CLP/L) y Payback         │
│  - Toneladas CO2 evitadas (2.68 kg CO2/L diésel) y LCOE 20a   │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│            7. Validación Normativa SEC (RIC N°09.1 / RIC N°06)│
│  Checklist técnico: Seccionador DC, DPS Tipo II, RCD Tipo B,  │
│  Puesta a tierra <= 20 Ohm y requisitos memoria TE1           │
└───────────────────────────────┘
```

---

## 3. Fórmulas Matemáticas y Criterios Técnicos

### 3.1. Recurso Solar (Horas Solares Pico - HSP / PSH)
$$\text{PSH} = \frac{\sum_{h=1}^{24} GHI_h}{1000\ \text{W/m}^2} \quad [\text{kWh/m}^2/\text{día}]$$

### 3.2. Orientación Física de Paneles
- **Inclinación Óptima**: $\text{Tilt} = |\text{Latitud}| \times 0.9\ (^\circ)$
- **Azimut**: $0^\circ$ (Norte geográfico para el Hemisferio Sur en Chile).

### 3.3. Dimensionamiento Fotovoltaico ($P_{\text{pv}}$)
$$P_{\text{pv\_req\_kWp}} = \frac{E_{\text{daily\_solar\_kWh}}}{\text{PSH} \times \eta_{\text{sys}}}$$
- $\eta_{\text{sys}} = 0.78$ ($78\%$ rendimiento global considerando temperatura, suciedad, pérdidas de cableado $\le 3\%$ y eficiencia MPPT).
- **Módulo estándar**: $550\text{ Wp}$ Monocristalino PERC ($0.55\text{ kWp}$).
- **Número de paneles**: $N_{\text{paneles}} = \lceil P_{\text{pv\_req\_kWp}} / 0.55 \rceil$.
- **Potencia instalada**: $P_{\text{pv\_inst}} = N_{\text{paneles}} \times 0.55\text{ kWp}$.

### 3.4. Factibilidad y Generación Eólica
- **Umbral de viabilidad**: Si $v_{\text{avg}} \ge 4.5\text{ m/s}$ a 10m de altura, se activa la microturbina eólica ($1.0\text{ kW}$ nominal).
- **Factor de planta eólico**: $C_f = \min(0.42, \max(0.15, (v_{\text{avg}} - 2.5) / 12.0))$.
- **Aporte eólico diario**: $E_{\text{wind\_daily}} = 1.0\text{ kW} \times 24\text{ h} \times C_f\ (\text{kWh/día})$.

### 3.5. Almacenamiento $\text{LiFePO}_4$ ($C_{\text{bat}}$)
$$C_{\text{bat\_nom\_kWh}} = \frac{E_{\text{daily\_kWh}} \times N_{\text{autonomía}}}{\text{DoD} \times \eta_{\text{bat}}}$$
- **Química**: Fosfato de Hierro y Litio ($\text{LiFePO}_4$), vida útil $> 6.000$ ciclos.
- **Autonomía ($N_{\text{autonomía}}$)**: $1.2\text{ días}$ (100% solar) o $1.0\text{ día}$ (híbrido solar-eólico).
- **Profundidad de descarga ($\text{DoD}$)**: $85\%$ ($0.85$).
- **Eficiencia ($\eta_{\text{bat}}$)**: $95\%$ ($0.95$).
- **Módulos comerciales en rack 48V**: Módulos de $4.8\text{ kWh}$ (100Ah 48V) o $2.4\text{ kWh}$ (50Ah 48V).

### 3.6. Inversor/Cargador Off-Grid ($P_{\text{inv}}$)
- **Potencia de diseño**: $P_{\text{inv\_req}} = P_{\text{punta}} \times 1.25$ (sobrecarga de 1.25 para tolerar corrientes de arranque inductivo de bombas y compresores).
- **Pasos comerciales**: $[1.5, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0]\text{ kVA}$.

### 3.7. Finanzas y Desplazamiento Diésel (CLP)
- **Costo Diésel**: $1.250\text{ CLP/Litro}$.
- **Consumo específico diésel**: $0.35\text{ L/kWh}$ generado.
- **Factor mantención motogenerador**: $1.20 \times$ (lubricantes, filtros, overhaul cada 3.000 hrs).
- **Factor de emisión $CO_2$**: $2.68\text{ kg } CO_2 / \text{L diésel}$.
- **CAPEX**: Equipos + Balance de Sistema (BOS $18\%$) + Montaje e Ingeniería SEC TE1 ($650.000\text{ base} + 45.000/\text{kWp} + 200.000\text{ TE1}$).
- **OPEX Anual**: $1.5\%$ del CAPEX.
- **LCOE a 20 años**: Tasa de descuento $6\%$, degradación anual $0.5\%$.

---

## 4. Normativa SEC y Requisitos TE1

### 4.1. RIC N°09.1 / 2021 (Sistemas de Autogeneración y Aislados)
- **Art. 5**: Segregación obligatoria de canalizaciones de Corriente Continua (DC) y Corriente Alterna (AC). Conductor solar fotovoltaico H1Z2Z2-K libre de halógenos y resistente a radiación UV.
- **Art. 8**: Interruptor-seccionador bajo carga rotulado y visible previo a la entrada MPPT del inversor.
- **Art. 10**: Descargadores de sobretensión transitoria (DPS / SPD) Tipo II en lado DC ($600\text{V}/1000\text{V DC}$) y lado AC ($275\text{V AC}$).
- **Art. 12**: Interruptor diferencial Tipo A Superinmunizado o Tipo B de $30\text{ mA}$ en la salida del inversor para evitar cegamiento ante fugas DC.
- **Art. 14**: Placas de advertencia normalizadas: *"PELIGRO: Instalación con Sistema de Autogeneración Aislada Off-Grid sin Inyección a Red"*.

### 4.2. RIC N°06 / 2021 (Puesta a Tierra)
- **Art. 6**: Resistencia de puesta a tierra medida $\le 20\ \Omega$.
- Unión equipotencial de todas las estructuras de aluminio de paneles, chasis de inversor y gabinetes de baterías a la barra Copperweld.

### 4.3. Expediente de Declaración TE1 SEC
1. Memoria técnica de cálculo y balance de cargas.
2. Diagrama unilineal de potencia y protecciones.
3. Plano de disposición general de paneles y banco de baterías.
4. Certificado de instalador autorizado SEC Clase A o B.
5. Certificados de homologación SEC/IEC de módulos FV e inversor.

---

## 5. Especificaciones de la Interfaz Visual (GUI / Frontend)

> [!IMPORTANT]
> **Requisito de Exhibición en Feria de Proyectos**:  
> La interfaz gráfica interactiva cuenta con una vista optimizada y fijada internamente a **800x480 píxeles** (o relación de aspecto 5:3 / touch display embebido), de modo que funcione perfectamente en pantallas táctiles de stand sin desbordamientos, scrolls molestos ni pérdidas de controles clave.

### Módulos Principales de la UI (7 pestañas):
1. **Selector Geográfico y Climático (Dimensionador)**:
   - Selector rápido de presets regionales (San Pedro, Valle del Elqui, Maule, Los Lagos, Magallanes, Rapa Nui, etc.).
   - Visualización de radiación solar (HSP) y velocidad de viento (m/s) con badge de factibilidad eólica.
2. **Mapa / Ubicación**: mapa interactivo (Leaflet + OpenStreetMap, sin API key) para hacer clic o
   arrastrar un marcador y fijar automáticamente latitud/longitud, con buscador de localidad y
   geocodificación inversa best-effort (Nominatim).
3. **Configurador de Demanda Rural**:
   - Selector de número de habitantes **por vivienda** y de **cantidad de viviendas/unidades** a
     electrificar (no solo personas), escalando toda la demanda y el dimensionamiento.
   - Lista interactiva de electrodomésticos rurales con switches on/off, cantidad y horas de uso
     (Refrigerador inverter, Starlink, bomba de agua, iluminación LED, etc.) con estimaciones
     estáticas de consumo realistas (Wh/día por potencia x horas x ciclo de trabajo).
   - Métricas de distribución de carga y potencia pico.
4. **Panel de Resultados Técnicos**:
   - Tarjeta Solar: Potencia en kWp, número de paneles 550W, inclinación óptima ($^\circ$), azimut Norte.
   - Tarjeta Eólica: Estado de activación, microturbina 1 kW, generación diaria.
   - Tarjeta Batería: Capacidad nominal y útil en kWh, química $\text{LiFePO}_4$, módulos rack 48V, días de autonomía.
   - Tarjeta Inversor: Potencia en kVA, onda pura 48V con protección de arranque.
5. **Comparativa de Opciones**: presenta de forma clara y sin saturar de datos la inversión total
   estimada, cantidad de paneles/eólica/baterías de la configuración recomendada **y 2 alternativas
   más factibles** ("Plan Económico" y "Plan Resiliente"), con botón para aplicar cualquiera de ellas
   al resto de la plataforma (BOM, SEC, TE1).
6. **Resumen Económico y Ecológico (Finanzas & BOM)**:
   - CAPEX total en CLP (y USD), desglose BOM detallado.
   - Payback simple y LCOE en CLP/kWh.
   - Litros de diésel ahorrados al año y toneladas de $CO_2$ evitadas con equivalencia en árboles plantados.
7. **Sello y Checklist Normativo SEC**:
   - Badge "Validado Normativa SEC RIC N°09.1 / RIC N°06".
   - Checklist interactivo de requisitos de seguridad y expediente TE1.
8. **Plano de Instalación**: mapa final (Leaflet) centrado en la ubicación seleccionada, mostrando
   la(s) vivienda(s) y las zonas recomendadas para el arreglo solar, la microturbina eólica y el
   banco de baterías/inversor, con distancia, rumbo y justificación técnica de cada emplazamiento.

---

## 6. Endpoints de la API REST del Backend

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Estado del servicio y versión. |
| `POST` | `/api/dimensionar` | **Pipeline integral de dimensionamiento**, recibe ubicación, habitantes, cantidad de viviendas (`households`) y artefactos; devuelve cálculo técnico, económico, ambiental, reporte SEC, 2 configuraciones **alternativas** factibles (`alternatives`) y la recomendación de **emplazamiento físico** (`site_layout`) respecto a la(s) vivienda(s). El campo opcional `preferred_option` ("recomendada" / "economica" / "resiliente") fuerza cuál configuración se devuelve como principal. |
| `GET` | `/api/clima?lat=-33.45&lon=-70.66` | Consulta en tiempo real de radiación solar y viento vía Open-Meteo o fallback chileno. |
| `GET` | `/api/catalogo` | Catálogo de electrodomésticos y equipos rurales estándar con potencias y ciclos de trabajo. |
| `GET` | `/api/presets` | Casos de uso preconfigurados (Vivienda Rural, Posta de Salud, Escuela, Riego, Patagonia). |
| `GET` | `/api/regiones` | Metadatos de las 16 regiones de Chile con coordenadas y recursos medios. |

---

## 7. Ejecución y Verificación

```bash
# Instalar dependencias
pip install -r backend/requirements.txt

# Iniciar servidor backend FastAPI (puerto 8000)
python backend/run.py
# O con uvicorn directo:
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# Ejecutar suite de pruebas unitarias e integración
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio
```
