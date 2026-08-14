# PROJECT_OVERVIEW.md

# EnchufaTE: Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid

## Resumen Ejecutivo
EnchufaTE es una plataforma de dimensionamiento tecno-económico diseñada para acelerar la electrificación limpia y autónoma en zonas rurales y aisladas de Chile. A partir de la selección de cualquier coordenada geográfica en el territorio nacional, el sistema consulta datos climáticos en tiempo real (radiación solar y velocidad de viento), modela la demanda energética horaria de la vivienda o instalación, y calcula una configuración óptima de costo mínimo (paneles fotovoltaicos, microturbinas eólicas y banco de baterías LiFePO4). El sistema entrega costos reales en moneda local (CLP) y garantiza la validación normativa ante la Superintendencia de Electricidad y Combustibles (SEC).

---

## Arquitectura y Pipeline de Procesamiento del Backend

```text
┌─────────────────────────┐
│   Coordenadas (Lat/Lng) │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Extracción de Recursos  │ ──> Open-Meteo API (Radiación GHI + Viento a 10m)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Modelación de Demanda   │ ──> Carga base por habitante + Catálogo de artefactos (Wh/día)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Factibilidad y Mix      │ ──> Evaluación umbral eólico (v >= 4.5 m/s) vs. Solar Fotovoltaico
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Optimización y Costo    │ ──> Minimización CAPEX: Paneles (kWp), Baterías (kWh), Inversor (kVA)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Impacto y Cumplimiento  │ ──> Ahorro Diésel, Toneladas CO2 evitadas y Normativa SEC (RIC N°9.1 / TE1)
└─────────────────────────┘
```

### Detalle de Etapas de Procesamiento

1. **Ingesta de Recursos Climatológicos**:
   - **Radiación Solar**: Ingesta de la radiación global horizontal instantánea ($GHI$ en $W/m^2$) para integrar la curva diaria y calcular las Horas Solares Pico ($HSP$ o $PSH$, $kWh/m^2/\text{día}$).
   - **Recurso Eólico**: Consulta de velocidad horaria de viento a 10 metros de altura ($m/s$) para estimar la velocidad media ($v_{\text{avg}}$).

2. **Modelación Paramétrica de Demanda y GUI**:
   - **Cálculo de Consumo**: Sin depender de APIs externas para la carga, se combina un consumo per cápita base ($350\ Wh/\text{persona}/\text{día}$) con el ciclo de trabajo de electrodomésticos comunes en zonas rurales (refrigerador inverter, conectividad satelital Starlink, bomba de agua, iluminación LED).
   - **Demanda Diaria Total ($E_{\text{daily}}$)**: Integración del consumo energético diario en $Wh/\text{día}$ y cálculo de potencia sincrónica de punta ($W$).
   - **Interfaz Visual**: Para la correcta presentación en la Feria de Proyectos, la GUI de la plataforma cuenta con una vista optimizada fijada a exactamente 800x480 de resolución, previniendo cualquier desajuste o estiramiento de pantalla durante el uso interactivo.

3. **Evaluación de Factibilidad Renovable**:
   - **Filtro Eólico**: Si $v_{\text{avg}} < 4.5\ m/s$, el recurso eólico se descarta por inviabilidad económica y el sistema se dimensiona al 100% fotovoltaico.
   - **Modelo Híbrido**: Si $v_{\text{avg}} \ge 4.5\ m/s$, se activa el módulo de microgeneración eólica para complementar la curva nocturna y reducir el tamaño del banco de baterías.

4. **Motor de Optimización y Dimensionamiento**:
   - **Generación Solar ($P_{\text{pv}}$)**: Cálculo de potencia fotovoltaica necesaria ajustada por un factor de rendimiento del sistema ($\eta_{\text{sys}} = 78\%$) para cubrir pérdidas térmicas e inversión.
   - **Almacenamiento ($C_{\text{bat}}$)**: Dimensionamiento de banco de baterías de Litio Ferro-Fosfato ($\text{LiFePO}_4$) considerando una autonomía de 1.2 días y una profundidad de descarga segura ($\text{DoD} = 85\%$).
   - **Inversor Off-Grid ($P_{\text{inv}}$)**: Determinación de la potencia nominal del inversor/cargador con factor de sobrecarga de 1.25 para tolerar corrientes de arranque inductivas.
   - **Orientación Física**: Cálculo automático del ángulo de inclinación óptimo ($\text{Tilt} \approx \vert{}\text{Latitud}\vert{} \times 0.9$) y azimut orientado al Norte geográfico ($0^\circ$).

5. **Impacto Económico, Ambiental y Regulatorio**:
   - **Desplazamiento de Fósiles**: Estimación de litros anuales de combustible ahorrados en comparación con un generador diésel convencional y cálculo de toneladas de $CO_2$ evitadas al año.
   - **Cumplimiento SEC**: Incorporación de lineamientos de seguridad bajo la Instrucción Técnica General RIC N°9.1/2021 para Sistemas Aislados, valor máximo de puesta a tierra de $20\ \Omega$ según RIC N°06/2021, y los requerimientos para la declaración oficial TE1 (instalaciones off-grid sin inyección a la red).
