"""
Catálogo de artefactos rurales, presets de casos de uso y regiones de Chile para EnchufaTE.
"""
from typing import List, Dict, Any
from app.config import REGIONAL_CLIMATE_DEFAULTS


DEFAULT_RURAL_APPLIANCES: List[Dict[str, Any]] = [
    {
        "id": "refrigerador_inverter",
        "name": "Refrigerador Inverter Clase A++",
        "category": "refrigeracion",
        "power_w": 120.0,
        "hours_per_day": 8.0,
        "quantity": 1,
        "surge_multiplier": 2.5,
        "duty_cycle": 0.45,
        "enabled": True,
        "description": "Refrigerador rural eficiente con compresor inverter y bajo consumo continuo"
    },
    {
        "id": "starlink_internet",
        "name": "Conectividad Satelital Starlink",
        "category": "conectividad",
        "power_w": 50.0,
        "hours_per_day": 14.0,
        "quantity": 1,
        "surge_multiplier": 1.1,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Antena y router satelital para conectividad de alta velocidad en zonas aisladas"
    },
    {
        "id": "bomba_agua_05hp",
        "name": "Bomba de Agua Pozo (0.5 HP)",
        "category": "bombeo",
        "power_w": 370.0,
        "hours_per_day": 2.0,
        "quantity": 1,
        "surge_multiplier": 3.0,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Bomba periférica o sumergible para extracción y llenado de estanque acumulador"
    },
    {
        "id": "bomba_agua_1hp",
        "name": "Bomba de Riego / Pozo (1.0 HP)",
        "category": "bombeo",
        "power_w": 750.0,
        "hours_per_day": 1.5,
        "quantity": 1,
        "surge_multiplier": 3.5,
        "duty_cycle": 1.0,
        "enabled": False,
        "description": "Bomba de mayor caudal para predios agrícolas o extracción profunda"
    },
    {
        "id": "iluminacion_led_rural",
        "name": "Iluminación LED (6 Luminarias 10W)",
        "category": "iluminacion",
        "power_w": 60.0,
        "hours_per_day": 5.0,
        "quantity": 1,
        "surge_multiplier": 1.0,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Luminarias LED para interiores, cocina, baño y exterior de seguridad"
    },
    {
        "id": "cargadores_dispositivos",
        "name": "Carga Móviles / Tablets / Notebook",
        "category": "electronica",
        "power_w": 90.0,
        "hours_per_day": 4.0,
        "quantity": 1,
        "surge_multiplier": 1.1,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Carga simultánea de smartphones, computadores portátiles y linternas"
    },
    {
        "id": "televisor_smart_led",
        "name": "Smart TV LED 43 Pulgadas",
        "category": "entretenimiento",
        "power_w": 75.0,
        "hours_per_day": 4.0,
        "quantity": 1,
        "surge_multiplier": 1.1,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Información, entretenimiento y noticias en zona rural"
    },
    {
        "id": "lavadora_inverter",
        "name": "Lavadora Automática Inverter",
        "category": "linea_blanca",
        "power_w": 400.0,
        "hours_per_day": 1.0,
        "quantity": 1,
        "surge_multiplier": 2.0,
        "duty_cycle": 1.0,
        "enabled": True,
        "description": "Lavadora de carga superior o frontal con motor inverter de alta eficiencia"
    },
    {
        "id": "radio_comunicaciones_vhf",
        "name": "Radio Base VHF / Emergencias",
        "category": "comunicaciones",
        "power_w": 25.0,
        "hours_per_day": 8.0,
        "quantity": 1,
        "surge_multiplier": 1.2,
        "duty_cycle": 1.0,
        "enabled": False,
        "description": "Equipo de radiocomunicación VHF/UHF para emergencias y coordinación vecinal"
    },
    {
        "id": "cerco_electrico",
        "name": "Energizador Cerco Eléctrico Ganadero",
        "category": "agricola",
        "power_w": 15.0,
        "hours_per_day": 24.0,
        "quantity": 1,
        "surge_multiplier": 1.2,
        "duty_cycle": 1.0,
        "enabled": False,
        "description": "Protección y control de ganado ovino/bovino en parcelas y predios"
    },
    {
        "id": "herramientas_taller",
        "name": "Herramientas de Taller (Taladro / Esmeril)",
        "category": "herramientas",
        "power_w": 650.0,
        "hours_per_day": 0.5,
        "quantity": 1,
        "surge_multiplier": 2.8,
        "duty_cycle": 1.0,
        "enabled": False,
        "description": "Uso intermitente de herramientas eléctricas para reparaciones de campo"
    }
]


PRESET_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "vivienda_rural_estandar": {
        "id": "vivienda_rural_estandar",
        "name": "Vivienda Familiar Rural",
        "description": "Hogar rural típico de 4 personas con refrigerador, Starlink, bomba de agua, iluminación y TV",
        "inhabitants": 4,
        "region_id": "maule",
        "appliances": [
            {"id": "refrigerador_inverter", "power_w": 120.0, "hours_per_day": 8.0, "quantity": 1, "enabled": True},
            {"id": "starlink_internet", "power_w": 50.0, "hours_per_day": 14.0, "quantity": 1, "enabled": True},
            {"id": "bomba_agua_05hp", "power_w": 370.0, "hours_per_day": 2.0, "quantity": 1, "enabled": True},
            {"id": "iluminacion_led_rural", "power_w": 60.0, "hours_per_day": 5.0, "quantity": 1, "enabled": True},
            {"id": "cargadores_dispositivos", "power_w": 90.0, "hours_per_day": 4.0, "quantity": 1, "enabled": True},
            {"id": "televisor_smart_led", "power_w": 75.0, "hours_per_day": 4.0, "quantity": 1, "enabled": True},
            {"id": "lavadora_inverter", "power_w": 400.0, "hours_per_day": 1.0, "quantity": 1, "enabled": True}
        ]
    },
    "posta_rural_salud": {
        "id": "posta_rural_salud",
        "name": "Posta Rural de Salud / Vacunatorio",
        "description": "Centro de atención médica aislada con cadena de frío para vacunas y respaldo crítico",
        "inhabitants": 3,
        "region_id": "los_lagos",
        "appliances": [
            {"id": "refrig_clinico", "name": "Refrigerador Clínico Vacunas Grado Médico", "category": "salud", "power_w": 150.0, "hours_per_day": 10.0, "quantity": 1, "surge_multiplier": 2.2, "duty_cycle": 0.5, "enabled": True},
            {"id": "starlink_internet", "power_w": 50.0, "hours_per_day": 24.0, "quantity": 1, "enabled": True},
            {"id": "iluminacion_led_rural", "name": "Iluminación Boxes Clínicos (12x10W)", "category": "iluminacion", "power_w": 120.0, "hours_per_day": 8.0, "quantity": 1, "enabled": True},
            {"id": "bomba_agua_05hp", "power_w": 370.0, "hours_per_day": 2.5, "quantity": 1, "enabled": True},
            {"id": "cargadores_dispositivos", "name": "Equipos Médicos Portátiles y PC", "category": "salud", "power_w": 180.0, "hours_per_day": 6.0, "quantity": 1, "enabled": True},
            {"id": "radio_comunicaciones_vhf", "power_w": 30.0, "hours_per_day": 24.0, "quantity": 1, "enabled": True}
        ]
    },
    "escuela_rural_conectada": {
        "id": "escuela_rural_conectada",
        "name": "Escuela Rural Unidocente Conectada",
        "description": "Colegio rural para 12 estudiantes con laboratorio digital, conectividad Starlink y cocina",
        "inhabitants": 12,
        "region_id": "araucania",
        "appliances": [
            {"id": "starlink_internet", "power_w": 60.0, "hours_per_day": 10.0, "quantity": 1, "enabled": True},
            {"id": "tablets_pcs", "name": "Laboratorio Móvil (12 Tablets/Notebooks)", "category": "educacion", "power_w": 240.0, "hours_per_day": 5.0, "quantity": 1, "enabled": True},
            {"id": "iluminacion_led_rural", "name": "Iluminación Salas y Comedor (10x10W)", "category": "iluminacion", "power_w": 100.0, "hours_per_day": 6.0, "quantity": 1, "enabled": True},
            {"id": "refrigerador_inverter", "power_w": 120.0, "hours_per_day": 8.0, "quantity": 1, "enabled": True},
            {"id": "bomba_agua_1hp", "power_w": 750.0, "hours_per_day": 1.5, "quantity": 1, "enabled": True}
        ]
    },
    "predio_agricola_riego": {
        "id": "predio_agricola_riego",
        "name": "Predio Agrícola / Estación de Riego",
        "description": "Instalación silvoagropecuaria con bombeo solar directo, cerco eléctrico y telemetría",
        "inhabitants": 2,
        "region_id": "coquimbo",
        "appliances": [
            {"id": "bomba_agua_1hp", "power_w": 750.0, "hours_per_day": 4.0, "quantity": 1, "surge_multiplier": 3.5, "enabled": True},
            {"id": "cerco_electrico", "power_w": 15.0, "hours_per_day": 24.0, "quantity": 2, "enabled": True},
            {"id": "starlink_internet", "power_w": 50.0, "hours_per_day": 12.0, "quantity": 1, "enabled": True},
            {"id": "iluminacion_led_rural", "power_w": 50.0, "hours_per_day": 4.0, "quantity": 1, "enabled": True},
            {"id": "herramientas_taller", "power_w": 650.0, "hours_per_day": 0.8, "quantity": 1, "enabled": True}
        ]
    },
    "refugio_patagonia_austral": {
        "id": "refugio_patagonia_austral",
        "name": "Refugio Austral Patagonia / Magallanes",
        "description": "Instalación off-grid en clima austral con fuerte recurso eólico y baja radiación invernal",
        "inhabitants": 3,
        "region_id": "magallanes",
        "appliances": [
            {"id": "refrigerador_inverter", "power_w": 120.0, "hours_per_day": 8.0, "quantity": 1, "enabled": True},
            {"id": "starlink_internet", "power_w": 50.0, "hours_per_day": 18.0, "quantity": 1, "enabled": True},
            {"id": "bomba_agua_05hp", "power_w": 370.0, "hours_per_day": 1.5, "quantity": 1, "enabled": True},
            {"id": "iluminacion_led_rural", "power_w": 80.0, "hours_per_day": 7.0, "quantity": 1, "enabled": True},
            {"id": "radio_comunicaciones_vhf", "power_w": 25.0, "hours_per_day": 12.0, "quantity": 1, "enabled": True},
            {"id": "cargadores_dispositivos", "power_w": 80.0, "hours_per_day": 4.0, "quantity": 1, "enabled": True}
        ]
    }
}


def get_all_regions_metadata() -> List[Dict[str, Any]]:
    """Devuelve la lista ordenada de regiones de Chile con sus coordenadas y recursos típicos."""
    result = []
    for key, data in REGIONAL_CLIMATE_DEFAULTS.items():
        result.append({
            "region_id": key,
            "region_name": data["region_name"],
            "latitude": data["lat"],
            "longitude": data["lon"],
            "psh_avg": data["psh_avg"],
            "wind_speed_avg": data["wind_speed_avg"],
            "wind_feasible": data["wind_speed_avg"] >= 4.5
        })
    return result
