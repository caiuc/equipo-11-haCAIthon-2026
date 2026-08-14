"""
Configuración global y constantes técnicas para EnchufaTE.
Normativa chilena SEC (RIC N°09.1, RIC N°06) y parámetros tecno-económicos.
"""
from dataclasses import dataclass
from typing import Dict, Any


# --- Constantes Técnicas de Dimensionamiento ---
SYSTEM_PERFORMANCE_RATIO: float = 0.78  # eta_sys = 78% (pérdidas térmicas, polvo, cableado, MPPT)
DEFAULT_BATTERY_DOD: float = 0.85        # Profundidad de descarga segura LiFePO4 (85%)
DEFAULT_BATTERY_EFFICIENCY: float = 0.95 # Eficiencia round-trip batería LiFePO4 (95%)
DEFAULT_AUTONOMY_DAYS: float = 1.2       # Días de autonomía estándar para off-grid
HYBRID_AUTONOMY_DAYS: float = 1.0        # Autonomía reducida cuando hay aporte eólico continuo
INVERTER_SURGE_FACTOR: float = 1.25      # Factor de sobrecarga para arranque inductivo (RIC N°9.1)
BASE_CONSUMPTION_PER_PERSON_WH: float = 350.0  # Consumo base per cápita (Wh/persona/día)

# --- Umbrales de Factibilidad ---
WIND_SPEED_THRESHOLD_MS: float = 4.5     # Umbral de viabilidad económica eólica (m/s a 10m)
MAX_GROUNDING_RESISTANCE_OHM: float = 20.0 # Resistencia máx. puesta a tierra según SEC RIC N°06

# --- Especificaciones Estándar de Componentes de Mercado ---
MODULE_WATT_PEAK: float = 550.0          # Potencia módulo fotovoltaico estándar monocristalino PERC (Wp)
BATTERY_MODULE_KWH: float = 4.8          # Capacidad nominal módulo rack LiFePO4 48V 100Ah (kWh)
BATTERY_MODULE_SMALL_KWH: float = 2.4    # Capacidad nominal módulo rack LiFePO4 48V 50Ah (kWh)
WIND_TURBINE_NOMINAL_KW: float = 1.0     # Microturbina eólica residencial típica (1 kW a 10 m/s)

# --- Constantes Económicas y de Impacto Ambiental (Chile CLP / Diésel) ---
CLP_PER_USD: float = 950.0               # Tipo de cambio de referencia
COST_PER_KWP_PV_CLP: float = 240_000     # Costo módulo FV por kWp (~132.000 CLP / panel 550W)
COST_PER_KWH_LIFEPO4_CLP: float = 340_000 # Costo almacenamiento LiFePO4 por kWh
COST_PER_KVA_INVERTER_CLP: float = 250_000 # Costo inversor/cargador por kVA
COST_INVERTER_BASE_CLP: float = 150_000   # Costo base equipo inversor
COST_PER_KW_WIND_CLP: float = 980_000    # Costo turbina eólica + mástil abatible + freno
BOS_PERCENTAGE: float = 0.18             # Balance of System: protecciones DC/AC, cables, tableros, estructura (18%)
INSTALLATION_BASE_CLP: float = 650_000   # Mano de obra instalador certificado SEC Clase A/B
INSTALLATION_PER_KWP_CLP: float = 45_000 # Costo adicional montaje por kWp
SEC_TRAMITATION_TE1_CLP: float = 200_000 # Tramitación declaración TE1 SEC y memoria de cálculo
ANNUAL_OPEX_RATIO: float = 0.015         # Operación y Mantenimiento anual (1.5% del CAPEX)

# --- Factores Diésel y CO2 ---
DIESEL_PRICE_CLP_LITER: float = 1_250.0  # Precio litro diésel en zona rural/aislada (CLP/L)
DIESEL_SPECIFIC_CONSUMPTION_L_KWH: float = 0.35 # Consumo específico generador diésel (L/kWh)
DIESEL_MAINTENANCE_FACTOR: float = 1.20  # Factor que incluye lubricantes, filtros y mantención motor diésel
CO2_KG_PER_LITER_DIESEL: float = 2.68    # Factor emisión emisiones CO2 (kg CO2 / L diésel)
TREES_PER_TON_CO2: float = 45.0          # Árboles equivalentes plantados por tonelada de CO2 evitada

# --- Límites Geográficos de Chile Continental e Insular ---
CHILE_LAT_MIN: float = -56.5
CHILE_LAT_MAX: float = -17.5
CHILE_LON_MIN: float = -110.0  # Incluye Rapa Nui
CHILE_LON_MAX: float = -66.0

# --- Perfiles Climáticos de Referencia por Región de Chile (Fallback Offline Robusto) ---
REGIONAL_CLIMATE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "arica": {
        "region_name": "Arica y Parinacota",
        "lat": -18.47, "lon": -70.31,
        "psh_avg": 6.8, "wind_speed_avg": 3.8, "solar_factor": 1.15
    },
    "tarapaca": {
        "region_name": "Tarapacá (Iquique / Pica)",
        "lat": -20.21, "lon": -70.15,
        "psh_avg": 7.1, "wind_speed_avg": 4.1, "solar_factor": 1.20
    },
    "antofagasta": {
        "region_name": "Antofagasta (San Pedro de Atacama / Calama)",
        "lat": -22.91, "lon": -68.20,
        "psh_avg": 7.4, "wind_speed_avg": 4.8, "solar_factor": 1.25
    },
    "atacama": {
        "region_name": "Atacama (Copiapó / Vallenar)",
        "lat": -27.36, "lon": -70.33,
        "psh_avg": 6.9, "wind_speed_avg": 4.4, "solar_factor": 1.18
    },
    "coquimbo": {
        "region_name": "Coquimbo (Valle del Elqui / Vicuña)",
        "lat": -30.03, "lon": -70.70,
        "psh_avg": 6.5, "wind_speed_avg": 4.6, "solar_factor": 1.12
    },
    "valparaiso": {
        "region_name": "Valparaíso (Petorca / Putaendo)",
        "lat": -32.42, "lon": -70.93,
        "psh_avg": 5.6, "wind_speed_avg": 3.9, "solar_factor": 1.00
    },
    "metropolitana": {
        "region_name": "Metropolitana (Melipilla / Paine / Curacaví)",
        "lat": -33.68, "lon": -71.21,
        "psh_avg": 5.4, "wind_speed_avg": 3.2, "solar_factor": 0.98
    },
    "ohiggins": {
        "region_name": "O'Higgins (Marchigüe / Pichilemu / Colchagua)",
        "lat": -34.40, "lon": -71.62,
        "psh_avg": 5.2, "wind_speed_avg": 4.7, "solar_factor": 0.95
    },
    "maule": {
        "region_name": "Maule (Cauquenes / San Clemente)",
        "lat": -35.96, "lon": -72.31,
        "psh_avg": 5.0, "wind_speed_avg": 3.6, "solar_factor": 0.92
    },
    "nuble": {
        "region_name": "Ñuble (Cobquecura / San Fabián)",
        "lat": -36.60, "lon": -72.10,
        "psh_avg": 4.8, "wind_speed_avg": 3.7, "solar_factor": 0.88
    },
    "biobio": {
        "region_name": "Biobío (Alto Biobío / Santa Bárbara)",
        "lat": -37.89, "lon": -71.32,
        "psh_avg": 4.6, "wind_speed_avg": 4.2, "solar_factor": 0.85
    },
    "araucania": {
        "region_name": "La Araucanía (Curarrehue / Lonquimay)",
        "lat": -38.43, "lon": -71.36,
        "psh_avg": 4.2, "wind_speed_avg": 4.0, "solar_factor": 0.80
    },
    "los_rios": {
        "region_name": "Los Ríos (Panguipulli / La Unión)",
        "lat": -39.64, "lon": -72.33,
        "psh_avg": 3.9, "wind_speed_avg": 4.1, "solar_factor": 0.75
    },
    "los_lagos": {
        "region_name": "Los Lagos (Chiloé - Ancud / Quellón)",
        "lat": -42.48, "lon": -73.77,
        "psh_avg": 3.6, "wind_speed_avg": 5.2, "solar_factor": 0.70
    },
    "aysen": {
        "region_name": "Aysén (Puerto Cisnes / Cochrane)",
        "lat": -45.57, "lon": -72.06,
        "psh_avg": 3.2, "wind_speed_avg": 5.8, "solar_factor": 0.65
    },
    "magallanes": {
        "region_name": "Magallanes (Porvenir / Puerto Williams / Punta Arenas)",
        "lat": -53.16, "lon": -70.91,
        "psh_avg": 2.8, "wind_speed_avg": 7.6, "solar_factor": 0.60
    },
    "rapanui": {
        "region_name": "Isla de Pascua (Rapa Nui - Hanga Roa)",
        "lat": -27.15, "lon": -109.43,
        "psh_avg": 5.5, "wind_speed_avg": 6.2, "solar_factor": 1.02
    }
}
