"""
Módulo de modelación paramétrica de demanda eléctrica para EnchufaTE.
Calcula la energía diaria (Wh/día), potencia de punta y corrientes de arranque.
"""
from typing import List
from app.config import BASE_CONSUMPTION_PER_PERSON_WH
from app.models.schemas import ApplianceItem, DemandBreakdown, ApplianceEnergyBreakdown


def calculate_demand(
    inhabitants: int,
    appliances: List[ApplianceItem],
    households: int = 1
) -> DemandBreakdown:
    """
    Calcula el balance de carga diario y la potencia máxima sincrónica.

    - Consumo base per cápita: 350 Wh/persona/día.
    - Cargas de artefactos: Potencia * Horas * Cantidad * Ciclo de trabajo.
    - Potencia de punta: Cargas coincidentes.
    - Potencia de sobrecarga: Pico de arranque inductivo de motores.
    - `households` permite escalar el dimensionamiento a un conjunto de viviendas/unidades
      idénticas (no solo la cantidad de personas de una vivienda), útil para pequeños
      caseríos o predios con varias construcciones alimentadas por la misma microrred.
    """
    households = max(1, households)

    # 1. Consumo per cápita base (multiplicado por cantidad de viviendas)
    inhabitant_wh = inhabitants * BASE_CONSUMPTION_PER_PERSON_WH * households

    # 2. Consumo por artefactos (cada vivienda repite el mismo set de artefactos habilitados)
    appliances_wh = 0.0
    items_breakdown: List[ApplianceEnergyBreakdown] = []

    max_surge_delta_w = 0.0
    active_power_total_w = 0.0

    for item in appliances:
        if not item.enabled:
            continue

        # Consumo diario en Wh (escalado por cantidad de viviendas)
        item_daily_wh = item.power_w * item.hours_per_day * item.quantity * item.duty_cycle * households
        appliances_wh += item_daily_wh

        # Potencia activa total
        item_total_power = item.power_w * item.quantity * households
        active_power_total_w += item_total_power

        # Pico de arranque adicional del artefacto con mayor transitorio (por unidad, no se multiplica
        # por vivienda ya que el arranque simultáneo entre viviendas es estadísticamente improbable)
        surge_delta = item.power_w * (item.surge_multiplier - 1.0)
        if surge_delta > max_surge_delta_w:
            max_surge_delta_w = surge_delta

    total_daily_wh = inhabitant_wh + appliances_wh
    total_daily_kwh = total_daily_wh / 1000.0
    total_annual_kwh = total_daily_kwh * 365.0

    # Construir desglose de porcentaje para cada artefacto
    for item in appliances:
        if not item.enabled:
            continue
        item_daily_wh = item.power_w * item.hours_per_day * item.quantity * item.duty_cycle * households
        percent = (item_daily_wh / total_daily_wh * 100.0) if total_daily_wh > 0 else 0.0
        items_breakdown.append(
            ApplianceEnergyBreakdown(
                id=item.id,
                name=item.name,
                category=item.category,
                power_w=item.power_w,
                hours_per_day=item.hours_per_day,
                quantity=item.quantity * households,
                daily_wh=round(item_daily_wh, 1),
                percent_of_total=round(percent, 1)
            )
        )

    # 3. Modelación de potencia de punta simultánea
    # Factor de simultaneidad típico en viviendas rurales: 0.70 a 0.85
    coincidence_factor = 0.75
    peak_synchronous_w = max(
        max([item.power_w * item.quantity for item in appliances if item.enabled], default=300.0),
        active_power_total_w * coincidence_factor + (inhabitants * households * 40.0)
    )

    # Potencia con transitorio de arranque
    peak_surge_w = peak_synchronous_w + max_surge_delta_w

    return DemandBreakdown(
        inhabitants_count=inhabitants,
        households_count=households,
        inhabitants_wh_day=round(inhabitant_wh, 1),
        appliances_wh_day=round(appliances_wh, 1),
        total_daily_wh=round(total_daily_wh, 1),
        total_daily_kwh=round(total_daily_kwh, 3),
        total_annual_kwh=round(total_annual_kwh, 1),
        peak_synchronous_power_w=round(peak_synchronous_w, 1),
        peak_surge_power_w=round(peak_surge_w, 1),
        appliances_list=items_breakdown
    )
