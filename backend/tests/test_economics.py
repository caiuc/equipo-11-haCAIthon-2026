"""
Tests unitarios para el análisis económico y ambiental de EnchufaTE.
"""
import pytest
from app.models.schemas import (
    DemandBreakdown,
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing
)
from app.core.economics import calculate_economics_and_impact


def test_economics_and_impact():
    demand = DemandBreakdown(
        inhabitants_count=4,
        inhabitants_wh_day=1400.0,
        appliances_wh_day=3600.0,
        total_daily_wh=5000.0,
        total_daily_kwh=5.0,
        total_annual_kwh=1825.0,
        peak_synchronous_power_w=1500.0,
        peak_surge_power_w=2500.0,
        appliances_list=[]
    )
    solar = SolarSizing(
        system_type="SOLAR_ONLY",
        required_pv_kwp=1.2,
        installed_pv_kwp=1.65,
        num_panels=3,
        panel_model_w=550.0,
        optimal_tilt_deg=30.0,
        optimal_azimuth_deg=0.0,
        daily_solar_generation_kwh=7.0,
        annual_solar_generation_kwh=2555.0,
        system_performance_ratio=0.78
    )
    wind = WindSizing(
        is_active=False,
        turbines_count=0,
        turbine_nominal_power_kw=0.0,
        hub_height_m=0.0,
        capacity_factor=0.0,
        daily_wind_generation_kwh=0.0,
        annual_wind_generation_kwh=0.0,
        reasoning="Solar only"
    )
    battery = BatterySizing(
        chemistry="LiFePO4",
        nominal_capacity_kwh=9.6,
        usable_capacity_kwh=8.16,
        num_modules=2,
        module_kwh=4.8,
        system_voltage_v=48,
        autonomy_days=1.2,
        dod_percent=85.0,
        efficiency_percent=95.0
    )
    inverter = InverterSizing(
        nominal_power_kva=3.0,
        nominal_power_kw=3.0,
        inverter_type="Off-Grid 48V",
        surge_capacity_kva=6.0,
        mppt_voltage_range_v="120V-450V",
        system_surge_factor=1.25
    )

    economics, env = calculate_economics_and_impact(
        demand=demand,
        solar=solar,
        wind=wind,
        battery=battery,
        inverter=inverter
    )

    assert economics.currency == "CLP"
    assert economics.total_capex_clp > 0
    assert economics.total_capex_usd > 0
    assert economics.annual_opex_clp > 0
    assert economics.annual_diesel_cost_baseline_clp > 0
    assert economics.simple_payback_years > 0
    assert economics.lcoe_clp_per_kwh > 0
    assert len(economics.bom) >= 4

    # Environmental Impact:
    # 1825 kWh * 0.35 L/kWh = 638.75 Liters diesel
    assert env.annual_diesel_saved_liters == pytest.approx(638.75, rel=0.1)
    # CO2: 638.75 * 2.68 / 1000 = ~1.71 tons CO2
    assert env.annual_co2_avoided_tons > 1.0
    assert env.equivalent_trees_planted > 0
    assert env.twenty_year_co2_avoided_tons > env.annual_co2_avoided_tons
