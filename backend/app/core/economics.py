"""
Módulo de análisis económico y evaluación de impacto ambiental para EnchufaTE.
Costos en Pesos Chilenos (CLP), ahorro de diésel, LCOE y mitigación de CO2.
"""
from typing import List
from urllib.parse import quote_plus
from app.config import (
    CLP_PER_USD,
    COST_PER_KWP_PV_CLP,
    COST_PER_KWH_LIFEPO4_CLP,
    COST_PER_KVA_INVERTER_CLP,
    COST_INVERTER_BASE_CLP,
    COST_PER_KW_WIND_CLP,
    BOS_PERCENTAGE,
    INSTALLATION_BASE_CLP,
    INSTALLATION_PER_KWP_CLP,
    SEC_TRAMITATION_TE1_CLP,
    ANNUAL_OPEX_RATIO,
    DIESEL_PRICE_CLP_LITER,
    DIESEL_SPECIFIC_CONSUMPTION_L_KWH,
    DIESEL_MAINTENANCE_FACTOR,
    CO2_KG_PER_LITER_DIESEL,
    TREES_PER_TON_CO2
)
from app.models.schemas import (
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing,
    DemandBreakdown,
    BillOfMaterialsItem,
    EconomicAnalysis,
    EnvironmentalImpact
)

# Registro oficial de instaladores eléctricos certificados de la Superintendencia de
# Electricidad y Combustibles de Chile.
SEC_INSTALLER_REGISTRY_URL = "https://www.sec.cl"


def _purchase_search_url(query: str) -> str:
    """
    Enlace referencial de búsqueda (no un proveedor específico) para cotizar un ítem del BOM
    en Chile. Se usa una búsqueda web genérica en vez de un enlace directo a un retailer, ya
    que el stock/precio de proveedores puntuales cambia constantemente.
    """
    return f"https://www.google.com/search?q={quote_plus(query + ' precio Chile comprar')}"


def _installation_service_search_url() -> str:
    """Enlace referencial para encontrar instaladores eléctricos certificados SEC en Chile."""
    return f"https://www.google.com/search?q={quote_plus('instalador eléctrico certificado SEC clase A o B fotovoltaico off-grid Chile')}"


def calculate_economics_and_impact(
    demand: DemandBreakdown,
    solar: SolarSizing,
    wind: WindSizing,
    battery: BatterySizing,
    inverter: InverterSizing
) -> tuple[EconomicAnalysis, EnvironmentalImpact]:
    """
    Calcula los costos de inversión (CAPEX), costos operativos (OPEX), retorno de inversión (Payback),
    costo nivelado de la energía (LCOE) y beneficios ambientales (Diésel y CO2 evitados).
    """
    bom: List[BillOfMaterialsItem] = []

    # 1. Costo de Módulos Fotovoltaicos
    solar_unit_cost = int(COST_PER_KWP_PV_CLP * (solar.panel_model_w / 1000.0))
    solar_total_cost = solar_unit_cost * solar.num_panels
    bom.append(
        BillOfMaterialsItem(
            category="Generación Solar",
            description=f"Paneles Fotovoltaicos Monocristalinos PERC {solar.panel_model_w:.0f}Wp Tier-1",
            quantity=solar.num_panels,
            unit="paneles",
            unit_cost_clp=solar_unit_cost,
            total_cost_clp=solar_total_cost,
            purchase_url=_purchase_search_url(f"panel solar fotovoltaico {solar.panel_model_w:.0f}W monocristalino")
        )
    )

    # 2. Costo de Turbina Eólica (si aplica)
    wind_total_cost = 0.0
    if wind.is_active and wind.turbines_count > 0:
        wind_unit_cost = int(COST_PER_KW_WIND_CLP * wind.turbine_nominal_power_kw)
        wind_total_cost = wind_unit_cost * wind.turbines_count
        bom.append(
            BillOfMaterialsItem(
                category="Generación Eólica",
                description=f"Microturbina Eólica {wind.turbine_nominal_power_kw:.1f} kW con mástil de 12m y controlador de freno",
                quantity=wind.turbines_count,
                unit="kit eólico",
                unit_cost_clp=wind_unit_cost,
                total_cost_clp=wind_total_cost,
                purchase_url=_purchase_search_url(f"microturbina eólica {wind.turbine_nominal_power_kw:.1f}kW mástil abatible")
            )
        )

    # 3. Costo de Almacenamiento LiFePO4
    bat_unit_cost = int(COST_PER_KWH_LIFEPO4_CLP * battery.module_kwh)
    bat_total_cost = bat_unit_cost * battery.num_modules
    bom.append(
        BillOfMaterialsItem(
            category="Almacenamiento",
            description=f"Módulos Rack Batería Litio Ferro-Fosfato (LiFePO4) 48V {battery.module_kwh:.1f} kWh (>6000 ciclos)",
            quantity=battery.num_modules,
            unit="módulos",
            unit_cost_clp=bat_unit_cost,
            total_cost_clp=bat_total_cost,
            purchase_url=_purchase_search_url(f"batería LiFePO4 48V {battery.module_kwh:.1f}kWh rack")
        )
    )

    # 4. Costo de Inversor/Cargador Off-Grid
    inverter_total_cost = int(COST_INVERTER_BASE_CLP + (inverter.nominal_power_kva * COST_PER_KVA_INVERTER_CLP))
    bom.append(
        BillOfMaterialsItem(
            category="Conversión de Potencia",
            description=f"Inversor/Cargador Off-Grid Onda Pura {inverter.nominal_power_kva:.1f} kVA 48V con controlador MPPT integrado",
            quantity=1,
            unit="unidad",
            unit_cost_clp=inverter_total_cost,
            total_cost_clp=inverter_total_cost,
            purchase_url=_purchase_search_url(f"inversor cargador off-grid {inverter.nominal_power_kva:.1f}kVA 48V onda pura MPPT")
        )
    )

    equipment_cost_clp = solar_total_cost + wind_total_cost + bat_total_cost + inverter_total_cost

    # 5. Balance de Sistema (BOS) - Protecciones y Estructuras SEC
    bos_cost_clp = int(equipment_cost_clp * BOS_PERCENTAGE)
    bom.append(
        BillOfMaterialsItem(
            category="Balance de Sistema (BOS)",
            description="Estructuras de aluminio anodizado, cable solar 6mm² UV, canalizaciones, tableros DC/AC, protecciones y puesta a tierra SEC",
            quantity=1,
            unit="sistema global",
            unit_cost_clp=bos_cost_clp,
            total_cost_clp=bos_cost_clp,
            purchase_url=_purchase_search_url("kit estructura montaje solar cable protecciones DC AC tablero")
        )
    )

    # 6. Instalación, Puesta en Marcha y Declaración SEC TE1
    installation_labor_cost = int(INSTALLATION_BASE_CLP + (solar.installed_pv_kwp * INSTALLATION_PER_KWP_CLP))
    installation_and_sec_cost = installation_labor_cost + int(SEC_TRAMITATION_TE1_CLP)
    bom.append(
        BillOfMaterialsItem(
            category="Servicios de Ingeniería y SEC",
            description="Montaje electromecánico SEC Clase A/B, conexionado, pruebas de aislamiento, memoria de cálculo y declaración oficial TE1",
            quantity=1,
            unit="servicio llave en mano",
            unit_cost_clp=installation_and_sec_cost,
            total_cost_clp=installation_and_sec_cost
        )
    )

    # Totales CAPEX
    total_capex_clp = equipment_cost_clp + bos_cost_clp + installation_and_sec_cost
    total_capex_usd = total_capex_clp / CLP_PER_USD

    # Costo Operativo Anual (OPEX)
    annual_opex_clp = total_capex_clp * ANNUAL_OPEX_RATIO

    # 7. Modelo Diésel de Referencia para Payback
    # Demanda anual cubierta
    annual_demand_kwh = demand.total_annual_kwh
    annual_diesel_liters = annual_demand_kwh * DIESEL_SPECIFIC_CONSUMPTION_L_KWH
    # Costo anual diésel incluyendo combustible + lubricantes/mantención
    annual_diesel_cost_clp = annual_diesel_liters * DIESEL_PRICE_CLP_LITER * DIESEL_MAINTENANCE_FACTOR

    net_annual_savings_clp = max(100_000.0, annual_diesel_cost_clp - annual_opex_clp)
    simple_payback_years = round(total_capex_clp / net_annual_savings_clp, 1)

    # 8. Cálculo de Costo Nivelado de la Energía (LCOE) a 20 años
    # Tasa de descuento = 6%, Degradación anual = 0.5%
    discount_rate = 0.06
    annual_degradation = 0.005
    life_years = 20

    discounted_costs = total_capex_clp
    discounted_generation = 0.0

    total_annual_generation_kwh = solar.annual_solar_generation_kwh + wind.annual_wind_generation_kwh

    for t in range(1, life_years + 1):
        discount_factor = 1.0 / ((1.0 + discount_rate) ** t)
        discounted_costs += annual_opex_clp * discount_factor
        discounted_generation += (total_annual_generation_kwh * ((1.0 - annual_degradation) ** (t - 1))) * discount_factor

    lcoe_clp_kwh = round(discounted_costs / max(1.0, discounted_generation), 1)

    economic_analysis = EconomicAnalysis(
        equipment_cost_clp=round(equipment_cost_clp, 0),
        bos_cost_clp=round(bos_cost_clp, 0),
        installation_and_te1_cost_clp=round(installation_and_sec_cost, 0),
        total_capex_clp=round(total_capex_clp, 0),
        total_capex_usd=round(total_capex_usd, 2),
        annual_opex_clp=round(annual_opex_clp, 0),
        annual_diesel_cost_baseline_clp=round(annual_diesel_cost_clp, 0),
        net_annual_savings_clp=round(net_annual_savings_clp, 0),
        simple_payback_years=simple_payback_years,
        lcoe_clp_per_kwh=lcoe_clp_kwh,
        currency="CLP",
        bom=bom,
        installation_service_url=_installation_service_search_url(),
        sec_installer_registry_url=SEC_INSTALLER_REGISTRY_URL
    )

    # 9. Evaluación de Impacto Ambiental
    annual_co2_tons = (annual_diesel_liters * CO2_KG_PER_LITER_DIESEL) / 1000.0
    trees_equivalent = int(annual_co2_tons * TREES_PER_TON_CO2)
    twenty_year_co2_tons = round(annual_co2_tons * 20.0, 1)

    environmental_impact = EnvironmentalImpact(
        annual_diesel_saved_liters=round(annual_diesel_liters, 1),
        annual_co2_avoided_tons=round(annual_co2_tons, 2),
        equivalent_trees_planted=trees_equivalent,
        twenty_year_co2_avoided_tons=twenty_year_co2_tons
    )

    return economic_analysis, environmental_impact
