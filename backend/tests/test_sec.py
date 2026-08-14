"""
Tests unitarios para validación de cumplimiento SEC RIC N°09.1 y RIC N°06.
"""
from app.models.schemas import (
    DemandBreakdown,
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing
)
from app.core.sec_compliance import generate_sec_compliance_report


def test_generate_sec_compliance_report():
    demand = DemandBreakdown(
        inhabitants_count=4,
        inhabitants_wh_day=1400.0,
        appliances_wh_day=3000.0,
        total_daily_wh=4400.0,
        total_daily_kwh=4.4,
        total_annual_kwh=1606.0,
        peak_synchronous_power_w=1200.0,
        peak_surge_power_w=2000.0,
        appliances_list=[]
    )
    solar = SolarSizing(
        system_type="SOLAR_ONLY",
        required_pv_kwp=1.0,
        installed_pv_kwp=1.1,
        num_panels=2,
        panel_model_w=550.0,
        optimal_tilt_deg=30.0,
        optimal_azimuth_deg=0.0,
        daily_solar_generation_kwh=5.0,
        annual_solar_generation_kwh=1825.0,
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
        nominal_capacity_kwh=4.8,
        usable_capacity_kwh=4.08,
        num_modules=1,
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

    report = generate_sec_compliance_report(
        demand=demand,
        solar=solar,
        wind=wind,
        battery=battery,
        inverter=inverter
    )

    assert report.normative_status == "VALIDADO_SEC_RIC_09_1"
    assert report.max_grounding_resistance_ohm == 20.0
    assert len(report.checklist) == 6
    assert len(report.te1_requirements) >= 4
    assert len(report.recommendations) >= 3
    # Check that each checklist item has CUMPLE_DISENO
    for item in report.checklist:
        assert item.status == "CUMPLE_DISENO"
