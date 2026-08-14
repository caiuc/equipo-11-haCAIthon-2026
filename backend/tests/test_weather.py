"""
Tests unitarios para el módulo meteorológico de EnchufaTE.
"""
import pytest
from app.core.weather import (
    find_nearest_chilean_region,
    generate_synthetic_radiation_curve,
    generate_synthetic_wind_curve,
    fetch_climate_data
)


def test_find_nearest_chilean_region():
    # Coordenadas cercanas a San Pedro de Atacama (-22.9, -68.2)
    key, data = find_nearest_chilean_region(-22.9, -68.1)
    assert key == "antofagasta"
    assert "San Pedro de Atacama" in data["region_name"]

    # Coordenadas cercanas a Punta Arenas (-53.1, -70.9)
    key_mag, data_mag = find_nearest_chilean_region(-53.0, -71.0)
    assert key_mag == "magallanes"


def test_synthetic_curves():
    rad_curve = generate_synthetic_radiation_curve(6.0)
    assert len(rad_curve) == 24
    # Noche (0:00 - 6:00) debe ser 0.0
    assert rad_curve[0] == 0.0
    assert rad_curve[23] == 0.0
    # Mediodía (12:00) debe tener valor pico positivo
    assert rad_curve[12] > 0.0

    wind_curve = generate_synthetic_wind_curve(5.0)
    assert len(wind_curve) == 24
    assert all(w > 0.0 for w in wind_curve)


@pytest.mark.asyncio
async def test_fetch_climate_data_user_override():
    climate = await fetch_climate_data(
        lat=-33.45,
        lon=-70.66,
        custom_psh=6.2,
        custom_wind_speed=5.1
    )
    assert climate.psh == 6.2
    assert climate.wind_speed_avg_ms == 5.1
    assert climate.wind_feasible is True
    assert climate.source == "user_override"
