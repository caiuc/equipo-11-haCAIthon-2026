"""
Esquemas Pydantic para EnchufaTE.
Tipado fuerte y validación para requests y responses del motor de dimensionamiento.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LocationInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitud en grados decimales")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitud en grados decimales")
    region_id: Optional[str] = Field(default=None, description="Identificador de región chilena si aplica")
    locality_name: Optional[str] = Field(default=None, description="Nombre de localidad o predio rural")


class ApplianceItem(BaseModel):
    id: str = Field(..., description="ID único del artefacto")
    name: str = Field(..., description="Nombre del electrodoméstico o equipo")
    category: str = Field(default="general", description="Categoría (refrigeracion, conectividad, bombeo, etc.)")
    power_w: float = Field(..., gt=0, description="Potencia eléctrica en Watts")
    hours_per_day: float = Field(..., ge=0, le=24, description="Horas de operación al día")
    quantity: int = Field(default=1, ge=1, description="Cantidad de unidades")
    surge_multiplier: float = Field(default=1.0, ge=1.0, description="Multiplicador de potencia de arranque")
    duty_cycle: float = Field(default=1.0, ge=0.01, le=1.0, description="Ciclo de trabajo efectivo")
    enabled: bool = Field(default=True, description="Si el artefacto está habilitado en el cálculo")


class DimensioningRequest(BaseModel):
    location: LocationInput
    inhabitants: int = Field(default=4, ge=1, le=50, description="Número de habitantes por vivienda/unidad")
    households: int = Field(default=1, ge=1, le=200, description="Cantidad de viviendas/unidades a electrificar (no solo personas)")
    appliances: List[ApplianceItem] = Field(default_factory=list, description="Lista de artefactos eléctricos (por vivienda)")
    custom_psh: Optional[float] = Field(default=None, ge=1.0, le=12.0, description="HSP personalizada (kWh/m2/día)")
    custom_wind_speed: Optional[float] = Field(default=None, ge=0.0, le=35.0, description="Velocidad viento personalizada (m/s)")
    force_hybrid: Optional[bool] = Field(default=None, description="Forzar activación de microgenerador eólico")
    force_solar_only: Optional[bool] = Field(default=None, description="Forzar dimensionamiento 100% solar fotovoltaico")
    autonomy_days: Optional[float] = Field(default=None, ge=0.5, le=5.0, description="Días de autonomía de batería")
    battery_dod: Optional[float] = Field(default=None, ge=0.5, le=0.95, description="Profundidad de descarga máx. LiFePO4")
    preferred_option: Optional[str] = Field(
        default=None,
        description="Fuerza qué configuración se devuelve como principal: 'recomendada' (default, decisión automática), 'economica' o 'resiliente'"
    )


class ClimateResource(BaseModel):
    psh: float = Field(..., description="Horas Solares Pico diarias medias (kWh/m2/día)")
    wind_speed_avg_ms: float = Field(..., description="Velocidad media del viento a 10m de altura (m/s)")
    wind_feasible: bool = Field(..., description="Indica si el recurso eólico supera el umbral de 4.5 m/s")
    hourly_ghi_sample: List[float] = Field(default_factory=list, description="Curva horaria de radiación solar (W/m2)")
    hourly_wind_sample: List[float] = Field(default_factory=list, description="Curva horaria de velocidad de viento (m/s)")
    source: str = Field(..., description="Origen de los datos: 'open_meteo' o 'regional_model_fallback'")
    elevation_m: Optional[float] = Field(default=None, description="Elevación sobre el nivel del mar en metros")


class ApplianceEnergyBreakdown(BaseModel):
    id: str
    name: str
    category: str
    power_w: float
    hours_per_day: float
    quantity: int
    daily_wh: float
    percent_of_total: float


class DemandBreakdown(BaseModel):
    inhabitants_count: int
    households_count: int = Field(default=1, description="Cantidad de viviendas/unidades consideradas")
    inhabitants_wh_day: float
    appliances_wh_day: float
    total_daily_wh: float
    total_daily_kwh: float
    total_annual_kwh: float
    peak_synchronous_power_w: float
    peak_surge_power_w: float
    appliances_list: List[ApplianceEnergyBreakdown]


class SolarSizing(BaseModel):
    system_type: str = Field(..., description="SOLAR_ONLY o HYBRID_SOLAR_WIND")
    required_pv_kwp: float = Field(..., description="Potencia fotovoltaica teórica requerida en kWp")
    installed_pv_kwp: float = Field(..., description="Potencia fotovoltaica instalada real comercial en kWp")
    num_panels: int = Field(..., description="Número de paneles fotovoltaicos")
    panel_model_w: float = Field(..., description="Potencia nominal por módulo en Watts")
    optimal_tilt_deg: float = Field(..., description="Ángulo de inclinación óptimo en grados")
    optimal_azimuth_deg: float = Field(..., description="Azimut óptimo (0° Norte en hemisferio sur)")
    daily_solar_generation_kwh: float = Field(..., description="Generación solar diaria estimada en kWh")
    annual_solar_generation_kwh: float = Field(..., description="Generación solar anual estimada en kWh")
    system_performance_ratio: float = Field(..., description="Performance Ratio eta_sys (0.78)")


class WindSizing(BaseModel):
    is_active: bool = Field(..., description="Si el sistema híbrido incluye turbina eólica")
    turbines_count: int = Field(..., description="Cantidad de microturbinas eólicas")
    turbine_nominal_power_kw: float = Field(..., description="Potencia nominal por turbina en kW")
    hub_height_m: float = Field(..., description="Altura de torre recomendada en metros")
    capacity_factor: float = Field(..., description="Factor de planta eólico estimado")
    daily_wind_generation_kwh: float = Field(..., description="Generación eólica diaria estimada en kWh")
    annual_wind_generation_kwh: float = Field(..., description="Generación eólica anual estimada en kWh")
    reasoning: str = Field(..., description="Explicación técnica de la decisión eólica")


class BatterySizing(BaseModel):
    chemistry: str = Field(default="LiFePO4", description="Química de batería")
    nominal_capacity_kwh: float = Field(..., description="Capacidad nominal del banco en kWh")
    usable_capacity_kwh: float = Field(..., description="Capacidad útil neta en kWh")
    num_modules: int = Field(..., description="Cantidad de módulos de batería")
    module_kwh: float = Field(..., description="Capacidad por módulo rack (4.8 kWh o 2.4 kWh)")
    system_voltage_v: int = Field(default=48, description="Voltaje nominal del bus DC")
    autonomy_days: float = Field(..., description="Días de autonomía considerados")
    dod_percent: float = Field(..., description="Profundidad de descarga configurada (%)")
    efficiency_percent: float = Field(..., description="Eficiencia round-trip (%)")


class InverterSizing(BaseModel):
    nominal_power_kva: float = Field(..., description="Potencia nominal comercial del inversor en kVA")
    nominal_power_kw: float = Field(..., description="Potencia nominal en kW")
    inverter_type: str = Field(default="Off-Grid Pure Sine Wave MPPT 48V", description="Tipo de inversor")
    surge_capacity_kva: float = Field(..., description="Capacidad de sobrecarga (pico arranque)")
    mppt_voltage_range_v: str = Field(default="120V - 450V DC", description="Rango de voltaje MPPT")
    system_surge_factor: float = Field(..., description="Factor de sobrecarga aplicado")


class BillOfMaterialsItem(BaseModel):
    category: str = Field(..., description="Categoría (Generación, Almacenamiento, Conversión, BOS, SEC)")
    name: str = Field(..., description="Nombre corto y simple del producto, para mostrar en grande (ej. 'Paneles Solares')")
    description: str = Field(..., description="Descripción técnica detallada, para mostrar en chico debajo del nombre")
    quantity: int = Field(..., description="Cantidad")
    unit: str = Field(..., description="Unidad (unidades, metros, global, etc.)")
    unit_cost_clp: float = Field(..., description="Costo unitario en CLP")
    total_cost_clp: float = Field(..., description="Costo total ítem en CLP")
    purchase_url: str = Field(default="", description="Enlace referencial de búsqueda para cotizar/comprar el ítem")


class EconomicAnalysis(BaseModel):
    equipment_cost_clp: float
    bos_cost_clp: float
    installation_and_te1_cost_clp: float
    total_capex_clp: float
    total_capex_usd: float
    annual_opex_clp: float
    annual_diesel_cost_baseline_clp: float
    net_annual_savings_clp: float
    simple_payback_years: float
    lcoe_clp_per_kwh: float
    currency: str = Field(default="CLP", description="Moneda principal")
    bom: List[BillOfMaterialsItem] = Field(default_factory=list)
    installation_service_url: str = Field(default="", description="Enlace referencial para buscar instaladores certificados")
    sec_installer_registry_url: str = Field(default="", description="Enlace oficial del registro de instaladores SEC")


class EnvironmentalImpact(BaseModel):
    annual_diesel_saved_liters: float = Field(..., description="Litros de diésel ahorrados por año")
    annual_co2_avoided_tons: float = Field(..., description="Toneladas de CO2 evitadas al año")
    equivalent_trees_planted: int = Field(..., description="Equivalente en árboles plantados")
    twenty_year_co2_avoided_tons: float = Field(..., description="CO2 evitado en 20 años de vida útil")


class SecChecklistItem(BaseModel):
    norm: str
    requirement: str
    status: str = Field(default="CUMPLE_DISENO", description="Estado normativo")
    details: str


class SecComplianceReport(BaseModel):
    normative_status: str = Field(default="VALIDADO_SEC_RIC_09_1", description="Estado de validación")
    max_grounding_resistance_ohm: float = Field(default=20.0, description="Resistencia máx. puesta a tierra RIC N°06")
    ric_09_1_isolated_systems: Dict[str, Any] = Field(default_factory=dict)
    te1_requirements: List[str] = Field(default_factory=list)
    checklist: List[SecChecklistItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SystemOption(BaseModel):
    """Configuración técnico-económica evaluada como una de las 3 opciones factibles a elegir."""
    option_id: str = Field(..., description="Identificador de la opción (economica, recomendada, resiliente)")
    label: str = Field(..., description="Nombre corto para mostrar en la UI")
    tagline: str = Field(..., description="Descripción de una línea del enfoque de la opción")
    is_recommended: bool = Field(default=False, description="Si es la opción recomendada por el motor")
    system_type: str = Field(..., description="SOLAR_ONLY o HYBRID_SOLAR_WIND")
    num_panels: int
    installed_pv_kwp: float
    wind_active: bool
    turbines_count: int
    battery_nominal_kwh: float
    autonomy_days: float
    inverter_kva: float
    total_capex_clp: float
    total_capex_usd: float
    simple_payback_years: float
    lcoe_clp_per_kwh: float
    annual_co2_avoided_tons: float
    bom: List[BillOfMaterialsItem] = Field(default_factory=list, description="Desglose de qué comprar y cuánto cuesta")
    installation_service_url: str = Field(default="")
    sec_installer_registry_url: str = Field(default="")


class LayoutZone(BaseModel):
    """Recomendación de emplazamiento físico de un componente respecto a la(s) vivienda(s)."""
    equipment: str = Field(..., description="Solar, Eólico, Baterías/Inversor")
    min_distance_m: float = Field(..., description="Distancia mínima recomendada respecto a la vivienda (m)")
    max_distance_m: float = Field(..., description="Distancia máxima recomendada respecto a la vivienda (m)")
    direction: str = Field(..., description="Orientación cardinal recomendada respecto a la vivienda")
    bearing_deg: float = Field(..., description="Rumbo en grados (0=Norte, 90=Este) usado para graficar en el mapa")
    area_m2: float = Field(..., description="Área aproximada requerida en m2")
    note: str = Field(..., description="Justificación técnica breve")


class SiteLayout(BaseModel):
    households_count: int
    solar_zone: LayoutZone
    wind_zone: Optional[LayoutZone] = None
    battery_zone: LayoutZone
    coverage_radius_m: float = Field(
        ...,
        description="Radio práctico de cobertura de la microrred (AC) desde el gabinete de "
                    "baterías/inversor, sin caídas de tensión significativas en el cableado."
    )
    general_notes: List[str] = Field(default_factory=list)


class DimensioningResponse(BaseModel):
    success: bool = True
    project_name: str = "EnchufaTE Dimensionamiento Off-Grid"
    timestamp: str
    location: LocationInput
    climate: ClimateResource
    demand: DemandBreakdown
    solar: SolarSizing
    wind: WindSizing
    battery: BatterySizing
    inverter: InverterSizing
    economics: EconomicAnalysis
    environmental: EnvironmentalImpact
    sec_compliance: SecComplianceReport
    options: List[SystemOption] = Field(default_factory=list, description="Las 3 configuraciones factibles evaluadas (económica, recomendada, resiliente)")
    site_layout: Optional[SiteLayout] = Field(default=None, description="Recomendación de emplazamiento físico respecto a las viviendas")


class GeocodeResult(BaseModel):
    display_name: Optional[str] = None
    comuna: Optional[str] = None
    region_name: Optional[str] = None
    latitude: float
    longitude: float
