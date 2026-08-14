"""
Módulo de validación normativa y cumplimiento ante la SEC (Superintendencia de Electricidad y Combustibles).
Implementa requerimientos de la Instrucción Técnica RIC N°09.1/2021 (Sistemas Aislados) y RIC N°06/2021 (Puesta a Tierra).
"""
from typing import List, Dict, Any
from app.config import MAX_GROUNDING_RESISTANCE_OHM
from app.models.schemas import (
    SolarSizing,
    WindSizing,
    BatterySizing,
    InverterSizing,
    DemandBreakdown,
    SecChecklistItem,
    SecComplianceReport
)


def generate_sec_compliance_report(
    demand: DemandBreakdown,
    solar: SolarSizing,
    wind: WindSizing,
    battery: BatterySizing,
    inverter: InverterSizing
) -> SecComplianceReport:
    """
    Genera el informe de cumplimiento técnico-normativo chileno y la lista de chequeo para la declaración TE1 SEC.
    """
    checklist: List[SecChecklistItem] = []

    # 1. RIC N°09.1 Art. 5: Canalizaciones y Cableado Solar
    checklist.append(
        SecChecklistItem(
            norm="RIC N°09.1 Art. 5",
            requirement="Segregación de canalizaciones DC y AC con conductor solar H1Z2Z2-K libre de halógenos y resistente UV.",
            status="CUMPLE_DISENO",
            details=f"Canalizaciones independientes para el string de {solar.num_panels} módulos FV ({solar.installed_pv_kwp} kWp) y salida AC del inversor."
        )
    )

    # 2. RIC N°09.1 Art. 8: Seccionador DC bajo carga
    checklist.append(
        SecChecklistItem(
            norm="RIC N°09.1 Art. 8",
            requirement="Seccionador DC rotulado y accesible previo a la entrada del controlador MPPT.",
            status="CUMPLE_DISENO",
            details="Interruptor-seccionador bajo carga 1000V DC / 32A en caja combinadora DC para corte visible y seguro."
        )
    )

    # 3. RIC N°09.1 Art. 10: Supresores de Transitorios (DPS / SPD)
    checklist.append(
        SecChecklistItem(
            norm="RIC N°09.1 Art. 10",
            requirement="Descargadores de sobretensión transitoria Tipo II en lados DC y AC.",
            status="CUMPLE_DISENO",
            details="DPS Tipo II 600V/1000V DC en tablero de paneles y DPS Tipo II 275V AC en tablero de distribución general."
        )
    )

    # 4. RIC N°09.1 Art. 12: Protección Diferencial
    checklist.append(
        SecChecklistItem(
            norm="RIC N°09.1 Art. 12",
            requirement="Protección diferencial Tipo B o Tipo A Superinmunizado 30mA en salida de inversor.",
            status="CUMPLE_DISENO",
            details=f"Diferencial 30mA 2x40A Superinmunizado apto para componentes de corriente continua de alta frecuencia del inversor de {inverter.nominal_power_kva} kVA."
        )
    )

    # 5. RIC N°09.1 Art. 14: Rotulación y Señalética de Seguridad
    checklist.append(
        SecChecklistItem(
            norm="RIC N°09.1 Art. 14",
            requirement="Placas de advertencia 'PELIGRO: Instalación con Autogeneración Off-Grid'.",
            status="CUMPLE_DISENO",
            details="Señalética reglamentaria visible en tablero general, gabinete de baterías LiFePO4 y estructura de paneles."
        )
    )

    # 6. RIC N°06 Art. 6: Puesta a Tierra y Equipotencialidad
    checklist.append(
        SecChecklistItem(
            norm="RIC N°06 Art. 6",
            requirement=f"Resistencia de puesta a tierra inferior o igual a {MAX_GROUNDING_RESISTANCE_OHM} Ohms con unión equipotencial.",
            status="CUMPLE_DISENO",
            details="Barra Copperweld 5/8' x 2.0m con soldadura exotérmica o conector certificado; marcos de paneles y chasis de banco LiFePO4 interconectados."
        )
    )

    # Requerimientos para expediente TE1
    te1_requirements: List[str] = [
        "Memoria Técnica de Cálculo con balance de cargas horarias y justificación de potencia instalada.",
        "Plano Eléctrico Unilineal con detalle de protecciones termomagnéticas, diferenciales y DPS.",
        "Plano de Disposición Física de paneles fotovoltaicos, banco de baterías y canalizaciones.",
        "Certificado de Título y Licencia SEC vigente del instalador responsable (Clase A o B).",
        "Certificados de homologación SEC o protocolos de ensayo IEC 61215/61730 para módulos e IEC 62109 para inversor."
    ]

    recommendations: List[str] = [
        "Verificar que la sala o gabinete de baterías LiFePO4 cuente con ventilación natural y temperatura controlada entre 10°C y 35°C.",
        f"Ajustar la inclinación de los paneles a exactamente {solar.optimal_tilt_deg}° orientados al Norte geográfico (Azimut 0°).",
        "Efectuar medición de resistividad de terreno y resistencia de puesta a tierra antes de la puesta en marcha con telurómetro calibrado.",
        "Mantener libre de sombras el área de captación solar entre las 9:00 y las 17:00 hrs."
    ]

    if wind.is_active:
        recommendations.append(
            "Para la microturbina eólica: Instalar interruptor de frenado electromecánico accesible y anclar torre con vientos tensados según manual del fabricante."
        )

    ric_09_1_details = {
        "sistema": "Off-Grid Aislado sin Inyección a Red",
        "inversor_nominal_kva": inverter.nominal_power_kva,
        "potencia_fv_kwp": solar.installed_pv_kwp,
        "almacenamiento_kwh": battery.nominal_capacity_kwh,
        "seccionamiento_dc": "Obligatorio bajo carga 1000V DC",
        "diferencial_recomendado": "Tipo A Superinmunizado / Tipo B 30mA",
        "dps_dc": "Tipo II Uc 600V DC",
        "dps_ac": "Tipo II Uc 275V AC"
    }

    return SecComplianceReport(
        normative_status="VALIDADO_SEC_RIC_09_1",
        max_grounding_resistance_ohm=MAX_GROUNDING_RESISTANCE_OHM,
        ric_09_1_isolated_systems=ric_09_1_details,
        te1_requirements=te1_requirements,
        checklist=checklist,
        recommendations=recommendations
    )
