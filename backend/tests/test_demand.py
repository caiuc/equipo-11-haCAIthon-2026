"""
Tests unitarios para modelación de demanda y artefactos en EnchufaTE.
"""
import pytest
from app.models.schemas import ApplianceItem
from app.core.demand import calculate_demand


def test_calculate_demand_basic():
    appliances = [
        ApplianceItem(
            id="refrig",
            name="Refrigerador",
            category="refrigeracion",
            power_w=120.0,
            hours_per_day=8.0,
            quantity=1,
            duty_cycle=0.5,
            surge_multiplier=2.5,
            enabled=True
        ),
        ApplianceItem(
            id="starlink",
            name="Starlink",
            category="conectividad",
            power_w=50.0,
            hours_per_day=10.0,
            quantity=1,
            duty_cycle=1.0,
            surge_multiplier=1.0,
            enabled=True
        ),
        ApplianceItem(
            id="bomba_off",
            name="Bomba Deshabilitada",
            category="bombeo",
            power_w=750.0,
            hours_per_day=2.0,
            quantity=1,
            enabled=False
        )
    ]

    # Inhabitants = 3 -> 3 * 350 = 1050 Wh/day
    # Refrig: 120 * 8 * 1 * 0.5 = 480 Wh/day
    # Starlink: 50 * 10 * 1 * 1.0 = 500 Wh/day
    # Total daily = 1050 + 480 + 500 = 2030 Wh/day = 2.03 kWh/day
    demand = calculate_demand(inhabitants=3, appliances=appliances)

    assert demand.inhabitants_count == 3
    assert demand.inhabitants_wh_day == 1050.0
    assert demand.appliances_wh_day == 980.0
    assert demand.total_daily_wh == 2030.0
    assert demand.total_daily_kwh == 2.03
    assert len(demand.appliances_list) == 2  # Solo habilitados
    assert demand.peak_synchronous_power_w > 0
    assert demand.peak_surge_power_w >= demand.peak_synchronous_power_w
    assert demand.households_count == 1


def test_calculate_demand_scales_with_households():
    """La cantidad de viviendas escala la energía diaria total, no solo la cantidad de personas."""
    appliances = [
        ApplianceItem(
            id="refrig",
            name="Refrigerador",
            category="refrigeracion",
            power_w=120.0,
            hours_per_day=8.0,
            quantity=1,
            duty_cycle=0.5,
            surge_multiplier=2.5,
            enabled=True
        )
    ]

    single = calculate_demand(inhabitants=3, appliances=appliances, households=1)
    triple = calculate_demand(inhabitants=3, appliances=appliances, households=3)

    assert triple.households_count == 3
    assert triple.total_daily_wh == pytest.approx(single.total_daily_wh * 3)
    assert triple.inhabitants_wh_day == pytest.approx(single.inhabitants_wh_day * 3)
    # El pico de arranque de un solo artefacto no se multiplica: es estadísticamente
    # improbable que todas las viviendas arranquen el mismo motor en el mismo instante.
    assert triple.peak_surge_power_w - triple.peak_synchronous_power_w == pytest.approx(
        single.peak_surge_power_w - single.peak_synchronous_power_w
    )
