"""
Módulo de recomendación de emplazamiento físico para EnchufaTE.
Determina dónde deberían ubicarse los paneles solares, la microturbina eólica y el
banco de baterías/inversor respecto a la(s) vivienda(s), en base a criterios técnicos
básicos (sombras, ruido/seguridad eólica, longitud de cableado) y la orientación
óptima para el Hemisferio Sur (Norte geográfico, Azimut 0°).
"""
from typing import Optional

from app.models.schemas import SolarSizing, WindSizing, BatterySizing, InverterSizing, LayoutZone, SiteLayout

# Área aproximada de un panel monocristalino PERC de 550 Wp (m2)
PANEL_AREA_M2 = 2.7
# Huella aproximada de un módulo/rack de batería LiFePO4 + gabinete inversor (m2)
BATTERY_MODULE_AREA_M2 = 0.3
BATTERY_CABINET_BASE_AREA_M2 = 1.5

# Radio práctico de cobertura de la red de distribución AC (230V) desde el gabinete de
# baterías/inversor: heurística de planificación (no un cálculo de caída de tensión por
# tramo), donde inversores de mayor capacidad justifican económicamente cableado de
# mayor sección y por lo tanto tendidos más largos sin pérdidas significativas.
COVERAGE_BASE_RADIUS_M = 40.0
COVERAGE_RADIUS_PER_KVA_M = 6.0
COVERAGE_MAX_RADIUS_M = 150.0


def generate_site_layout(
    solar: SolarSizing,
    wind: WindSizing,
    battery: BatterySizing,
    inverter: InverterSizing,
    households: int = 1
) -> SiteLayout:
    """
    Genera la recomendación de emplazamiento físico de los tres componentes principales
    respecto a la(s) vivienda(s), pensada para dibujarse sobre un mapa (distancia + rumbo).
    """
    households = max(1, households)

    # --- Zona Solar: orientada al Norte geográfico (Azimut 0°), libre de sombras 9-17h ---
    solar_area = round(solar.num_panels * PANEL_AREA_M2, 1)
    solar_zone = LayoutZone(
        equipment="Arreglo Fotovoltaico",
        min_distance_m=2.0,
        max_distance_m=15.0,
        direction="Norte (fachada o patio orientado al Norte geográfico)",
        bearing_deg=0.0,
        area_m2=solar_area,
        note=(
            f"Ubicar en techumbre o estructura de suelo orientada al Norte con Tilt "
            f"{solar.optimal_tilt_deg}°, libre de sombras de árboles o construcciones "
            f"entre 9:00 y 17:00 hrs. Requiere ≈{solar_area} m² de superficie útil."
        )
    )

    # --- Zona Eólica: retiro de seguridad por ruido/derribo, en el punto más despejado ---
    wind_zone: Optional[LayoutZone] = None
    if wind.is_active and wind.turbines_count > 0:
        setback = max(20.0, wind.hub_height_m * 2.0)
        wind_zone = LayoutZone(
            equipment="Microturbina Eólica",
            min_distance_m=round(setback, 1),
            max_distance_m=round(setback + 25.0, 1),
            direction="Noroeste (punto más alto y despejado del predio, sin obstáculos en 360°)",
            bearing_deg=315.0,
            area_m2=round(9.0 * wind.turbines_count, 1),
            note=(
                f"Retiro mínimo de {round(setback,1)} m respecto a la vivienda por ruido y radio "
                f"de derribo de la torre de {wind.hub_height_m:.0f} m. Instalar en el punto más "
                "alto y despejado del predio, libre de turbulencia generada por árboles o techos."
            )
        )

    # --- Zona Baterías/Inversor: lo más cerca posible de la vivienda para minimizar cableado ---
    battery_area = round(battery.num_modules * BATTERY_MODULE_AREA_M2 + BATTERY_CABINET_BASE_AREA_M2, 1)
    battery_zone = LayoutZone(
        equipment="Banco de Baterías + Inversor",
        min_distance_m=0.0,
        max_distance_m=8.0,
        direction="Adosado a la vivienda (muro exterior o bodega/pieza técnica ventilada)",
        bearing_deg=0.0,
        area_m2=battery_area,
        note=(
            "Instalar en gabinete o pieza técnica ventilada, temperatura 10-35°C, lo más cerca "
            "posible del tablero de la vivienda para minimizar caída de tensión en el cableado AC."
        )
    )

    # --- Radio práctico de cobertura de la microrred desde el gabinete de baterías/inversor ---
    coverage_radius_m = round(
        min(COVERAGE_MAX_RADIUS_M, COVERAGE_BASE_RADIUS_M + inverter.nominal_power_kva * COVERAGE_RADIUS_PER_KVA_M),
        1
    )

    general_notes = [
        "Mantener segregación física entre canalizaciones DC (paneles) y AC (inversor-vivienda) según RIC N°09.1.",
        "Todas las estructuras metálicas (paneles, torre eólica, gabinete de baterías) deben unirse a la "
        "misma malla de puesta a tierra (≤ 20 Ω, RIC N°06).",
        f"Radio práctico de cobertura estimado: ≈{coverage_radius_m:.0f} m desde el gabinete de baterías/inversor "
        "(heurística de planificación según capacidad del inversor, no un cálculo de caída de tensión detallado). "
        "Viviendas más allá de este radio pueden sufrir caída de tensión relevante y requieren cableado de mayor "
        "sección, un segundo hub de generación, o un sistema propio."
    ]

    if households > 1:
        general_notes.append(
            f"Con {households} viviendas conectadas, se recomienda un hub de generación centralizado "
            "ubicado en el punto equidistante entre las viviendas (minimiza el largo total de "
            "alimentadores) o, alternativamente, sistemas individuales replicados por vivienda si "
            "la dispersión geográfica supera el radio de cobertura estimado."
        )
    else:
        general_notes.append(
            "Diseño para una vivienda: priorizar el emplazamiento sobre el mismo techo o patio "
            "inmediato para minimizar pérdidas de cableado."
        )

    return SiteLayout(
        households_count=households,
        solar_zone=solar_zone,
        wind_zone=wind_zone,
        battery_zone=battery_zone,
        coverage_radius_m=coverage_radius_m,
        general_notes=general_notes
    )
