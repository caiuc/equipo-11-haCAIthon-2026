"""
Endpoints de la API REST de EnchufaTE.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    DimensioningRequest,
    DimensioningResponse,
    ClimateResource,
    ApplianceItem,
    DemandBreakdown,
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing,
    EconomicAnalysis,
    EnvironmentalImpact,
    SystemOption
)
from app.models.catalog import (
    DEFAULT_RURAL_APPLIANCES,
    PRESET_SCENARIOS,
    get_all_regions_metadata
)
from app.core.weather import fetch_climate_data
from app.core.demand import calculate_demand
from app.core.sizing import size_system
from app.core.economics import calculate_economics_and_impact
from app.core.sec_compliance import generate_sec_compliance_report
from app.core.layout import generate_site_layout
from app.core.geocoding import reverse_geocode, search_locality

router = APIRouter(prefix="/api", tags=["Dimensionamiento y Recursos"])


_OPTION_ORDER = ["economica", "recomendada", "resiliente"]


def _compute_option(
    option_id: str,
    label: str,
    tagline: str,
    latitude: float,
    climate: ClimateResource,
    demand: DemandBreakdown,
    is_recommended: bool = False,
    force_hybrid: Optional[bool] = None,
    force_solar_only: Optional[bool] = None,
    autonomy_days: Optional[float] = None,
    battery_dod: Optional[float] = None
):
    """Dimensiona y costea una configuración completa, devolviendo el detalle técnico y su resumen comparable."""
    solar, wind, battery, inverter = size_system(
        latitude=latitude,
        climate=climate,
        demand=demand,
        force_hybrid=force_hybrid,
        force_solar_only=force_solar_only,
        custom_autonomy_days=autonomy_days,
        custom_dod=battery_dod
    )
    economics, environmental = calculate_economics_and_impact(demand, solar, wind, battery, inverter)
    option = SystemOption(
        option_id=option_id,
        label=label,
        tagline=tagline,
        is_recommended=is_recommended,
        system_type=solar.system_type,
        num_panels=solar.num_panels,
        installed_pv_kwp=solar.installed_pv_kwp,
        wind_active=wind.is_active,
        turbines_count=wind.turbines_count,
        battery_nominal_kwh=battery.nominal_capacity_kwh,
        autonomy_days=battery.autonomy_days,
        inverter_kva=inverter.nominal_power_kva,
        total_capex_clp=economics.total_capex_clp,
        total_capex_usd=economics.total_capex_usd,
        simple_payback_years=economics.simple_payback_years,
        lcoe_clp_per_kwh=economics.lcoe_clp_per_kwh,
        annual_co2_avoided_tons=environmental.annual_co2_avoided_tons,
        bom=economics.bom,
        installation_service_url=economics.installation_service_url,
        sec_installer_registry_url=economics.sec_installer_registry_url
    )
    return solar, wind, battery, inverter, economics, environmental, option


def _compute_all_options(
    request: DimensioningRequest,
    climate: ClimateResource,
    demand: DemandBreakdown
) -> Dict[str, Any]:
    """
    Calcula las tres configuraciones canónicas que la plataforma siempre evalúa y compara:
    - "recomendada": decisión automática del motor (respeta overrides manuales del request).
    - "economica": 100% solar, autonomía mínima responsable -> menor CAPEX.
    - "resiliente": híbrida (si hay recurso eólico aprovechable) o autonomía extendida -> mayor
      seguridad de suministro ante días nublados consecutivos.
    """
    latitude = request.location.latitude

    recomendada = _compute_option(
        "recomendada", "Configuración Recomendada",
        "Decisión automática del motor según el recurso solar/eólico disponible en el sitio.",
        latitude, climate, demand, is_recommended=True,
        force_hybrid=request.force_hybrid, force_solar_only=request.force_solar_only,
        autonomy_days=request.autonomy_days, battery_dod=request.battery_dod
    )

    economica = _compute_option(
        "economica", "Plan Económico",
        "100% solar con autonomía mínima responsable: la menor inversión inicial.",
        latitude, climate, demand,
        force_solar_only=True, autonomy_days=1.0, battery_dod=0.9
    )

    if climate.wind_speed_avg_ms >= 3.2:
        resiliente = _compute_option(
            "resiliente", "Plan Resiliente",
            "Híbrida Solar + Eólica: complementa la curva nocturna y reduce el banco de baterías.",
            latitude, climate, demand,
            force_hybrid=True, autonomy_days=1.2
        )
    else:
        resiliente = _compute_option(
            "resiliente", "Plan Resiliente",
            "100% solar con autonomía extendida (2 días): mayor resguardo ante días nublados.",
            latitude, climate, demand,
            force_solar_only=True, autonomy_days=2.0, battery_dod=0.8
        )

    return {"recomendada": recomendada, "economica": economica, "resiliente": resiliente}


@router.get("/health", summary="Estado del servicio")
async def health_check() -> Dict[str, Any]:
    """Retorna el estado operativo del backend de EnchufaTE."""
    return {
        "status": "online",
        "service": "EnchufaTE Backend Engine",
        "version": "1.0.0",
        "region": "Chile",
        "sec_norm": "RIC N°09.1 / RIC N°06",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/dimensionar", response_model=DimensioningResponse, summary="Dimensionamiento integral off-grid")
async def dimensionar_sistema(request: DimensioningRequest) -> DimensioningResponse:
    """
    Ejecuta el pipeline completo de dimensionamiento tecno-económico:
    1. Ingesta de recursos climáticos (Open-Meteo o Fallback regional).
    2. Modelación horaria de demanda y corrientes de arranque.
    3. Evaluación de factibilidad y mix de generación (Solar + Eólica).
    4. Dimensionamiento óptimo de módulos FV, banco LiFePO4 e inversor 48V.
    5. Análisis económico en CLP, cálculo de Payback y LCOE vs Diésel.
    6. Mitigación de CO2 y validación normativa SEC RIC N°09.1 / RIC N°06.
    """
    try:
        # 1. Obtención de recurso solar y eólico
        climate = await fetch_climate_data(
            lat=request.location.latitude,
            lon=request.location.longitude,
            custom_psh=request.custom_psh,
            custom_wind_speed=request.custom_wind_speed
        )

        # 2. Modelación de demanda (escalada por cantidad de viviendas/unidades)
        demand = calculate_demand(
            inhabitants=request.inhabitants,
            appliances=request.appliances,
            households=request.households
        )

        # 3. Dimensionamiento tecno-económico: se evalúan siempre las 3 configuraciones
        #    canónicas (recomendada, económica, resiliente) para poder compararlas.
        computed_options = _compute_all_options(request, climate, demand)

        primary_key = request.preferred_option if request.preferred_option in computed_options else "recomendada"
        solar, wind, battery, inverter, economics, environmental, _primary_summary = computed_options[primary_key]

        # 6. Las 3 opciones factibles completas (económica, recomendada, resiliente) para elegir
        options = [computed_options[key][6] for key in _OPTION_ORDER]

        # 5. Reporte Normativo SEC (sobre la configuración principal seleccionada)
        sec_report = generate_sec_compliance_report(
            demand=demand,
            solar=solar,
            wind=wind,
            battery=battery,
            inverter=inverter
        )

        # 7. Recomendación de emplazamiento físico respecto a la(s) vivienda(s)
        site_layout = generate_site_layout(
            solar=solar,
            wind=wind,
            battery=battery,
            inverter=inverter,
            households=request.households
        )

        return DimensioningResponse(
            success=True,
            project_name="EnchufaTE Dimensionamiento Off-Grid",
            timestamp=datetime.now(timezone.utc).isoformat(),
            location=request.location,
            climate=climate,
            demand=demand,
            solar=solar,
            wind=wind,
            battery=battery,
            inverter=inverter,
            economics=economics,
            environmental=environmental,
            sec_compliance=sec_report,
            options=options,
            site_layout=site_layout
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el motor de dimensionamiento: {str(exc)}"
        )


@router.get("/clima", response_model=ClimateResource, summary="Consulta de recurso solar y eólico")
async def consultar_clima(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitud"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitud"),
    custom_psh: Optional[float] = Query(None, description="HSP manual"),
    custom_wind: Optional[float] = Query(None, description="Viento manual (m/s)")
) -> ClimateResource:
    """Consulta radiación solar (GHI/PSH) y velocidad de viento para cualquier coordenada."""
    return await fetch_climate_data(
        lat=lat,
        lon=lon,
        custom_psh=custom_psh,
        custom_wind_speed=custom_wind
    )


@router.get("/catalogo", summary="Catálogo de artefactos rurales")
async def obtener_catalogo() -> List[Dict[str, Any]]:
    """Retorna la lista de artefactos y cargas rurales estándar preconfiguradas."""
    return DEFAULT_RURAL_APPLIANCES


@router.get("/presets", summary="Casos de uso y presets rurales")
async def obtener_presets() -> Dict[str, Any]:
    """Retorna los escenarios preconfigurados (Vivienda, Posta de Salud, Escuela, Riego, Patagonia)."""
    return PRESET_SCENARIOS


@router.get("/regiones", summary="Regiones de Chile y datos climáticos típicos")
async def obtener_regiones() -> List[Dict[str, Any]]:
    """Retorna las 16 regiones de Chile con coordenadas y promedios solares/eólicos de referencia."""
    return get_all_regions_metadata()


@router.get("/geocode/reverse", summary="Geocodificación inversa (coordenada -> comuna/región)")
async def geocode_reverse(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0)
) -> Dict[str, Any]:
    """
    Convierte una coordenada en comuna/región legible. Se ejecuta en el backend (no en el
    navegador) con un User-Agent identificable para cumplir la política de uso de Nominatim
    y evitar el error 'referer is required' que ocurre al llamar a OpenStreetMap directamente
    desde el cliente.
    """
    return await reverse_geocode(lat, lon)


@router.get("/geocode/search", summary="Búsqueda de localidad/dirección en Chile")
async def geocode_search(
    q: str = Query(..., min_length=2, description="Texto de búsqueda: dirección, localidad o comuna"),
    limit: int = Query(5, ge=1, le=10)
) -> List[Dict[str, Any]]:
    """Busca direcciones/localidades dentro de Chile (proxy backend hacia Nominatim/OpenStreetMap)."""
    return await search_locality(q, limit=limit)
