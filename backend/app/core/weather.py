"""
Módulo de ingesta y modelado de recursos meteorológicos para EnchufaTE.
Integración con Open-Meteo API y fallback climatológico robusto para Chile.
"""
import math
import logging
from typing import Tuple, List, Optional, Dict, Any
import httpx

from app.config import (
    WIND_SPEED_THRESHOLD_MS,
    REGIONAL_CLIMATE_DEFAULTS,
    CHILE_LAT_MIN,
    CHILE_LAT_MAX,
    CHILE_LON_MIN,
    CHILE_LON_MAX
)
from app.models.schemas import ClimateResource

logger = logging.getLogger("enchufate.weather")


def find_nearest_chilean_region(lat: float, lon: float) -> Tuple[str, Dict[str, Any]]:
    """Encuentra la región de referencia chilena más cercana por distancia euclidiana."""
    best_key = "metropolitana"
    min_dist_sq = float("inf")
    
    for key, data in REGIONAL_CLIMATE_DEFAULTS.items():
        d_lat = lat - data["lat"]
        d_lon = lon - data["lon"]
        dist_sq = d_lat * d_lat + d_lon * d_lon
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_key = key
            
    return best_key, REGIONAL_CLIMATE_DEFAULTS[best_key]


def generate_synthetic_radiation_curve(psh: float) -> List[float]:
    """Genera una curva horaria sintética de 24 horas de radiación global (W/m2)."""
    curve = [0.0] * 24
    # Curva sinusoidal típica de 7:00 a 19:00 (12h de sol)
    peak_w_m2 = (psh * 1000.0) / (12.0 * (2.0 / math.pi))
    for h in range(24):
        if 7 <= h <= 18:
            angle = (h - 7 + 0.5) / 12.0 * math.pi
            curve[h] = round(max(0.0, peak_w_m2 * math.sin(angle)), 1)
        else:
            curve[h] = 0.0
    return curve


def generate_synthetic_wind_curve(v_avg: float) -> List[float]:
    """Genera una curva horaria sintética de 24 horas de velocidad de viento (m/s)."""
    curve = []
    # Variación térmica diurna típica: viento más intenso en la tarde (14:00 - 18:00)
    for h in range(24):
        diurnal_factor = 1.0 + 0.3 * math.sin((h - 8) / 24.0 * 2.0 * math.pi)
        curve.append(round(max(0.5, v_avg * diurnal_factor), 2))
    return curve


async def fetch_climate_data(
    lat: float,
    lon: float,
    custom_psh: Optional[float] = None,
    custom_wind_speed: Optional[float] = None,
    timeout_sec: float = 6.0
) -> ClimateResource:
    """
    Obtiene recursos solares y eólicos para una coordenada geográfica.
    Intenta consultar Open-Meteo API en tiempo real.
    Si falla o no hay conexión, utiliza el modelo regional de respaldo de Chile.
    """
    # Si el usuario suministró valores manuales explícitos, utilizarlos directamente
    if custom_psh is not None and custom_wind_speed is not None:
        psh = float(custom_psh)
        wind_avg = float(custom_wind_speed)
        return ClimateResource(
            psh=round(psh, 2),
            wind_speed_avg_ms=round(wind_avg, 2),
            wind_feasible=wind_avg >= WIND_SPEED_THRESHOLD_MS,
            hourly_ghi_sample=generate_synthetic_radiation_curve(psh),
            hourly_wind_sample=generate_synthetic_wind_curve(wind_avg),
            source="user_override",
            elevation_m=500.0
        )

    # Intentar llamada a Open-Meteo API
    open_meteo_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=shortwave_radiation,direct_normal_irradiance,wind_speed_10m"
        f"&timezone=America%2FSantiago&forecast_days=7"
    )

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(open_meteo_url, headers={"User-Agent": "EnchufaTE-Sizing-Engine/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                radiation_list = hourly.get("shortwave_radiation", [])
                wind_list = hourly.get("wind_speed_10m", [])
                elevation = data.get("elevation", 0.0)

                # Calcular Horas Solares Pico (PSH) promedio diario
                # Suma de Wh/m2 por día dividida entre 1000 W/m2
                if radiation_list and len(radiation_list) >= 24:
                    num_days = len(radiation_list) // 24
                    daily_integrations = []
                    for d in range(num_days):
                        day_chunk = radiation_list[d * 24 : (d + 1) * 24]
                        daily_wh = sum(day_chunk)
                        daily_integrations.append(daily_wh / 1000.0)
                    computed_psh = sum(daily_integrations) / len(daily_integrations)
                else:
                    computed_psh = 5.0

                # Calcular velocidad promedio de viento
                if wind_list and len(wind_list) > 0:
                    computed_wind = sum(wind_list) / len(wind_list)
                else:
                    computed_wind = 3.5

                # Usar curva de las primeras 24 horas como muestra diurna
                sample_ghi = [round(x, 1) for x in radiation_list[:24]] if len(radiation_list) >= 24 else generate_synthetic_radiation_curve(computed_psh)
                sample_wind = [round(x, 2) for x in wind_list[:24]] if len(wind_list) >= 24 else generate_synthetic_wind_curve(computed_wind)

                final_psh = custom_psh if custom_psh is not None else max(1.8, computed_psh)
                final_wind = custom_wind_speed if custom_wind_speed is not None else max(0.2, computed_wind)

                return ClimateResource(
                    psh=round(final_psh, 2),
                    wind_speed_avg_ms=round(final_wind, 2),
                    wind_feasible=final_wind >= WIND_SPEED_THRESHOLD_MS,
                    hourly_ghi_sample=sample_ghi,
                    hourly_wind_sample=sample_wind,
                    source="open_meteo",
                    elevation_m=round(elevation, 1) if elevation else None
                )
    except Exception as exc:
        logger.warning(f"Error consultando Open-Meteo ({lat}, {lon}): {exc}. Activando fallback regional.")

    # Fallback regional inteligente para Chile
    reg_key, reg_data = find_nearest_chilean_region(lat, lon)
    base_psh = reg_data["psh_avg"]
    base_wind = reg_data["wind_speed_avg"]

    final_psh = custom_psh if custom_psh is not None else base_psh
    final_wind = custom_wind_speed if custom_wind_speed is not None else base_wind

    return ClimateResource(
        psh=round(final_psh, 2),
        wind_speed_avg_ms=round(final_wind, 2),
        wind_feasible=final_wind >= WIND_SPEED_THRESHOLD_MS,
        hourly_ghi_sample=generate_synthetic_radiation_curve(final_psh),
        hourly_wind_sample=generate_synthetic_wind_curve(final_wind),
        source=f"regional_model_fallback ({reg_data['region_name']})",
        elevation_m=450.0
    )
