"""
Motor de optimización y dimensionamiento tecno-económico para EnchufaTE.
Calcula la potencia fotovoltaica (kWp), almacenamiento LiFePO4 (kWh), inversor (kVA) y microgenerador eólico.
"""
import math
from typing import Optional

from app.config import (
    SYSTEM_PERFORMANCE_RATIO,
    DEFAULT_BATTERY_DOD,
    DEFAULT_BATTERY_EFFICIENCY,
    DEFAULT_AUTONOMY_DAYS,
    HYBRID_AUTONOMY_DAYS,
    INVERTER_SURGE_FACTOR,
    WIND_SPEED_THRESHOLD_MS,
    MODULE_WATT_PEAK,
    BATTERY_MODULE_KWH,
    BATTERY_MODULE_SMALL_KWH,
    WIND_TURBINE_NOMINAL_KW
)
from app.models.schemas import (
    ClimateResource,
    DemandBreakdown,
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing
)


def calculate_optimal_tilt(latitude: float) -> float:
    """Calcula el ángulo de inclinación óptimo para paneles solares: Tilt = |Latitud| * 0.9."""
    abs_lat = abs(latitude)
    return round(abs_lat * 0.9, 1)


def size_system(
    latitude: float,
    climate: ClimateResource,
    demand: DemandBreakdown,
    force_hybrid: Optional[bool] = None,
    force_solar_only: Optional[bool] = None,
    custom_autonomy_days: Optional[float] = None,
    custom_dod: Optional[float] = None
) -> tuple[SolarSizing, WindSizing, BatterySizing, InverterSizing]:
    """
    Ejecuta el dimensionamiento integral optimizado del sistema de generación y almacenamiento.
    """
    # 1. Decisión de Factibilidad y Mix Renovable
    wind_active = False
    if force_solar_only:
        wind_active = False
        wind_reasoning = "Configuración 100% solar fotovoltaica forzada por el usuario."
    elif force_hybrid:
        wind_active = True
        wind_reasoning = "Microgenerador eólico activado manualmente por el usuario."
    elif climate.wind_feasible:
        wind_active = True
        wind_reasoning = (
            f"Velocidad de viento media ({climate.wind_speed_avg_ms} m/s) supera el umbral de viabilidad "
            f"económica ({WIND_SPEED_THRESHOLD_MS} m/s). Se activa sistema híbrido Solar-Eólico."
        )
    else:
        wind_active = False
        wind_reasoning = (
            f"Velocidad de viento media ({climate.wind_speed_avg_ms} m/s) es inferior al umbral mínimo "
            f"de viabilidad ({WIND_SPEED_THRESHOLD_MS} m/s). Se dimensiona 100% fotovoltaico para minimizar CAPEX."
        )

    # 2. Dimensionamiento Eólico (si aplica)
    turbines_count = 1 if wind_active else 0
    turbine_kw = WIND_TURBINE_NOMINAL_KW if wind_active else 0.0
    hub_height = 12.0 if wind_active else 0.0

    if wind_active:
        # Estimación de factor de planta eólico en función del recurso
        capacity_factor = min(0.42, max(0.15, (climate.wind_speed_avg_ms - 2.5) / 12.0))
        daily_wind_kwh = turbine_kw * 24.0 * capacity_factor
        annual_wind_kwh = daily_wind_kwh * 365.0
    else:
        capacity_factor = 0.0
        daily_wind_kwh = 0.0
        annual_wind_kwh = 0.0

    wind_sizing = WindSizing(
        is_active=wind_active,
        turbines_count=turbines_count,
        turbine_nominal_power_kw=turbine_kw,
        hub_height_m=hub_height,
        capacity_factor=round(capacity_factor, 3),
        daily_wind_generation_kwh=round(daily_wind_kwh, 2),
        annual_wind_generation_kwh=round(annual_wind_kwh, 1),
        reasoning=wind_reasoning
    )

    # 3. Dimensionamiento Solar Fotovoltaico
    # Si hay eólica, el solar cubre la demanda neta restante (dejando un margen de seguridad)
    if wind_active:
        solar_demand_target_kwh = max(demand.total_daily_kwh * 0.50, demand.total_daily_kwh - (daily_wind_kwh * 0.70))
        system_type = "HYBRID_SOLAR_WIND"
    else:
        solar_demand_target_kwh = demand.total_daily_kwh
        system_type = "SOLAR_ONLY"

    psh = max(1.8, climate.psh)
    eta_sys = SYSTEM_PERFORMANCE_RATIO  # 0.78
    
    # Potencia requerida en kWp
    required_pv_kwp = solar_demand_target_kwh / (psh * eta_sys)
    
    # Cantidad de módulos fotovoltaicos comerciales (550 Wp = 0.55 kWp)
    panel_rating_kwp = MODULE_WATT_PEAK / 1000.0  # 0.55 kWp
    num_panels = max(1, math.ceil(required_pv_kwp / panel_rating_kwp))
    installed_pv_kwp = num_panels * panel_rating_kwp

    # Estimación de generación fotovoltaica real
    daily_solar_gen_kwh = installed_pv_kwp * psh * eta_sys
    annual_solar_gen_kwh = daily_solar_gen_kwh * 365.0

    optimal_tilt = calculate_optimal_tilt(latitude)
    optimal_azimuth = 0.0  # 0° Norte en Hemisferio Sur

    solar_sizing = SolarSizing(
        system_type=system_type,
        required_pv_kwp=round(required_pv_kwp, 3),
        installed_pv_kwp=round(installed_pv_kwp, 2),
        num_panels=num_panels,
        panel_model_w=MODULE_WATT_PEAK,
        optimal_tilt_deg=optimal_tilt,
        optimal_azimuth_deg=optimal_azimuth,
        daily_solar_generation_kwh=round(daily_solar_gen_kwh, 2),
        annual_solar_generation_kwh=round(annual_solar_gen_kwh, 1),
        system_performance_ratio=eta_sys
    )

    # 4. Dimensionamiento de Baterías LiFePO4
    autonomy_days = (
        custom_autonomy_days
        if custom_autonomy_days is not None
        else (HYBRID_AUTONOMY_DAYS if wind_active else DEFAULT_AUTONOMY_DAYS)
    )
    dod = custom_dod if custom_dod is not None else DEFAULT_BATTERY_DOD
    eta_bat = DEFAULT_BATTERY_EFFICIENCY

    required_battery_capacity_kwh = (demand.total_daily_kwh * autonomy_days) / (dod * eta_bat)

    # Selección modular comercial (rack 48V de 4.8 kWh o 2.4 kWh para demandas pequeñas)
    if required_battery_capacity_kwh <= 3.6:
        module_unit_kwh = BATTERY_MODULE_SMALL_KWH  # 2.4 kWh
        num_battery_modules = max(1, math.ceil(required_battery_capacity_kwh / module_unit_kwh))
    else:
        module_unit_kwh = BATTERY_MODULE_KWH        # 4.8 kWh
        num_battery_modules = max(1, math.ceil(required_battery_capacity_kwh / module_unit_kwh))

    installed_battery_nominal_kwh = num_battery_modules * module_unit_kwh
    installed_battery_usable_kwh = installed_battery_nominal_kwh * dod

    battery_sizing = BatterySizing(
        chemistry="LiFePO4",
        nominal_capacity_kwh=round(installed_battery_nominal_kwh, 2),
        usable_capacity_kwh=round(installed_battery_usable_kwh, 2),
        num_modules=num_battery_modules,
        module_kwh=module_unit_kwh,
        system_voltage_v=48,
        autonomy_days=round(autonomy_days, 1),
        dod_percent=round(dod * 100.0, 1),
        efficiency_percent=round(eta_bat * 100.0, 1)
    )

    # 5. Dimensionamiento del Inversor/Cargador Off-Grid (kVA)
    # Potencia requerida con factor de sobrecarga de 1.25 para tolerar corrientes de arranque
    peak_kw = demand.peak_synchronous_power_w / 1000.0
    required_inverter_kva = peak_kw * INVERTER_SURGE_FACTOR

    # Pasos de potencia comerciales estándar (kVA)
    commercial_inverter_steps = [1.5, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0]
    selected_kva = commercial_inverter_steps[-1]
    for step in commercial_inverter_steps:
        if step >= required_inverter_kva:
            selected_kva = step
            break

    inverter_sizing = InverterSizing(
        nominal_power_kva=selected_kva,
        nominal_power_kw=round(selected_kva * 1.0, 1),  # Factor de potencia unitario en inversores modernos
        inverter_type="Off-Grid Pure Sine Wave MPPT 48V",
        surge_capacity_kva=round(selected_kva * 2.0, 1),
        mppt_voltage_range_v="120V - 450V DC",
        system_surge_factor=INVERTER_SURGE_FACTOR
    )

    return solar_sizing, wind_sizing, battery_sizing, inverter_sizing
