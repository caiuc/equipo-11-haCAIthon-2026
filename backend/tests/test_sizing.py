"""
Tests unitarios para el motor de dimensionamiento tecno-económico de EnchufaTE.
"""
import pytest
from app.models.schemas import ClimateResource, DemandBreakdown
from app.core.sizing import size_system, calculate_optimal_tilt


def test_calculate_optimal_tilt():
    # Maule (-35.96) -> round(35.96 * 0.9, 1) = 32.4°
    assert calculate_optimal_tilt(-35.96) == 32.4
    # San Pedro de Atacama (-22.91) -> round(22.91 * 0.9, 1) = 20.6°
    assert calculate_optimal_tilt(-22.91) == 20.6
    # Magallanes (-53.16) -> round(53.16 * 0.9, 1) = 47.8°
    assert calculate_optimal_tilt(-53.16) == 47.8


def test_size_system_solar_only():
    climate = ClimateResource(
        psh=5.5,
        wind_speed_avg_ms=3.2,  # < 4.5 m/s -> Solar only
        wind_feasible=False,
        source="test"
    )
    demand = DemandBreakdown(
        inhabitants_count=4,
        inhabitants_wh_day=1400.0,
        appliances_wh_day=3600.0,
        total_daily_wh=5000.0,
        total_daily_kwh=5.0,
        total_annual_kwh=1825.0,
        peak_synchronous_power_w=1200.0,
        peak_surge_power_w=2200.0,
        appliances_list=[]
    )

    solar, wind, battery, inverter = size_system(
        latitude=-33.5,
        climate=climate,
        demand=demand
    )

    assert solar.system_type == "SOLAR_ONLY"
    assert wind.is_active is False
    assert wind.turbines_count == 0
    # Required PV = 5.0 kWh / (5.5 PSH * 0.78 eta) = 1.165 kWp
    assert solar.required_pv_kwp > 1.0
    # Panel count (550W modules): ceil(1.165 / 0.55) = 3 panels (1.65 kWp)
    assert solar.num_panels == 3
    assert solar.installed_pv_kwp == 1.65
    assert solar.optimal_azimuth_deg == 0.0

    # LiFePO4 Battery sizing: (5.0 kWh * 1.2 days) / (0.85 DoD * 0.95 eff) = 7.43 kWh
    # Modules of 4.8 kWh: ceil(7.43 / 4.8) = 2 modules = 9.6 kWh nominal
    assert battery.chemistry == "LiFePO4"
    assert battery.nominal_capacity_kwh == 9.6
    assert battery.usable_capacity_kwh == round(9.6 * 0.85, 2)
    assert battery.num_modules == 2

    # Inverter sizing: Peak 1.2 kW * 1.25 surge factor = 1.5 kVA
    assert inverter.nominal_power_kva >= 1.5


def test_size_system_hybrid_wind():
    climate = ClimateResource(
        psh=3.2,
        wind_speed_avg_ms=6.5,  # >= 4.5 m/s -> Híbrido Solar + Eólico
        wind_feasible=True,
        source="test"
    )
    demand = DemandBreakdown(
        inhabitants_count=4,
        inhabitants_wh_day=1400.0,
        appliances_wh_day=4600.0,
        total_daily_wh=6000.0,
        total_daily_kwh=6.0,
        total_annual_kwh=2190.0,
        peak_synchronous_power_w=2000.0,
        peak_surge_power_w=3500.0,
        appliances_list=[]
    )

    solar, wind, battery, inverter = size_system(
        latitude=-53.0,
        climate=climate,
        demand=demand
    )

    assert solar.system_type == "HYBRID_SOLAR_WIND"
    assert wind.is_active is True
    assert wind.turbines_count == 1
    assert wind.daily_wind_generation_kwh > 0
    assert battery.autonomy_days == 1.0  # Reducción por complementariedad eólica
