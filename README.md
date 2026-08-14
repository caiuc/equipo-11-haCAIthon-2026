# EnchufaTE · Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid en Chile

<p align="left">
  <a href="https://tinyurl.com/Hacaithon" target="_blank"><img src="https://upload.wikimedia.org/wikipedia/commons/1/16/Logo_CAi.png" height="28" alt="Logo CAi UC" align="center" /><img src="https://img.shields.io/badge/CAi-HaCAiThon_2026-FFC72C?style=for-the-badge" alt="CAi Badge" align="center" /></a>
  <img src="https://img.shields.io/badge/SEC-RIC_N%C2%B009.1_%2F_RIC_N%C2%B006-0284c7?style=for-the-badge" alt="SEC Badge" align="center" />
  <img src="https://img.shields.io/badge/Licencia-MIT-10b981?style=for-the-badge" alt="MIT License" align="center" />
</p>

> **Equipo 11 · HaCAiThon 2026**  
> **Temática:** Energía Renovable y Electrificación Rural  
> **Nombre del Proyecto:** EnchufaTE (Plataforma Inteligente de Electrificación y Declaración SEC TE1)

---

## ☀️ ¿Qué es EnchufaTE?

**EnchufaTE** es una plataforma integral tecno-económica diseñada para resolver la brecha de electrificación en zonas rurales, aisladas y desconectadas de Chile. A partir de coordenadas geográficas o selección de presets regionales (vivienda familiar, posta rural de salud, escuela unidocente, predio agrícola o refugio patagónico), el sistema:

1. **Consulta meteorología en tiempo real**: Ingesta de radiación solar global ($GHI \to PSH$ o $HSP$ en $\text{kWh/m}^2/\text{día}$) y velocidad horaria de viento a 10m vía **Open-Meteo API** (con matriz de respaldo offline para las 16 regiones de Chile).
2. **Modela la demanda paramétrica**: Combina carga base per cápita ($350\text{ Wh/persona/día}$) con electrodomésticos de campo (refrigerador inverter, Starlink, bomba de agua, iluminación LED) modelando potencias sincrónicas y picos de arranque inductivos.
3. **Evalúa factibilidad y mix renovable**: Aplica el umbral eólico ($v_{\text{avg}} \ge 4.5\text{ m/s}$) para activar microgeneración eólica complementaria o dimensionar al $100\%$ solar fotovoltaico.
4. **Optimiza la microred aislada**: Calcula potencia solar ($P_{\text{pv}}$ en $\text{kWp}$ con rendimiento $\eta_{\text{sys}} = 78\%$, inclinación óptima $\text{Tilt} = |\text{Latitud}| \times 0.9$ y Azimut $0^\circ$ Norte), banco de baterías $\text{LiFePO}_4$ ($48\text{V}$, $\text{DoD} = 85\%$, autonomía $1.2\text{ días}$) e inversor/cargador de onda pura con factor de sobrecarga de $1.25\times$.
5. **Genera presupuestos reales en CLP y métricas de impacto**: CAPEX desglosado con Balance de Sistema (BOS $18\%$), mano de obra de montaje e ingeniería SEC TE1, costo nivelado LCOE a 20 años, payback simple vs generador diésel ($0.35\text{ L/kWh}$, $\$1.250\text{ CLP/L}$) y toneladas de $CO_2$ evitadas ($2.68\text{ kg } CO_2/\text{L}$).
6. **Valida la normativa chilena SEC**: Cumple y genera el checklist para las instrucciones técnicas **RIC N°09.1/2021** (Sistemas Aislados), **RIC N°06/2021** (Puesta a tierra $\le 20\ \Omega$) y expediente oficial para la declaración **TE1**.

---

## 🖥️ Interfaz de Usuario y Modo Stand (800x480)

La plataforma cuenta con una interfaz web moderna y reactiva de 7 pestañas que incluye:
- **Modo Stand 800x480**: Botón directo para fijar la interfaz en resolución nativa de $800 \times 480\text{ px}$ (pantallas táctiles de feria o displays embebidos) previniendo desajustes visuales o scroll durante la exhibición.
- **Mapa / Ubicación**: selección de coordenadas haciendo clic en un mapa interactivo (Leaflet + OpenStreetMap), con buscador de localidad.
- **Cantidad de viviendas, no solo personas**: además de los habitantes por vivienda, se puede escalar el dimensionamiento a varias viviendas/unidades del mismo predio o caserío.
- **Comparativa de Opciones**: inversión total, paneles, eólica y baterías de la configuración recomendada y **2 alternativas factibles** más, presentadas de forma clara y sin saturar de datos.
- **Diagrama Eléctrico Unilineal SVG interactivo** con identificación de protecciones (Seccionador DC, DPS Tipo II, RCD Tipo B/A Superinmunizado, malla tierra).
- **Expediente Imprimible TE1 SEC**: Vista de exportación formal de memoria de cálculo.
- **Plano de Instalación**: mapa final con la ubicación recomendada de paneles, turbina eólica y baterías respecto a la(s) vivienda(s).

---

## 🚀 Inicio Rápido y Ejecución

### Requisitos
- Python 3.10 o superior.

### 1. Instalación de Dependencias
```bash
pip install -r backend/requirements.txt
```

### 2. Iniciar la Aplicación (Backend + Frontend)
```bash
python backend/run.py
```
O con uvicorn:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

- **Aplicación Web**: Abre [http://localhost:8000](http://localhost:8000) en tu navegador.
- **Documentación Interactiva de la API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Ejecutar Pruebas Automatizadas
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio
```

---

## 📁 Estructura del Código

```text
├── backend/
│   ├── app/
│   │   ├── api/endpoints.py         # Endpoints REST (/dimensionar, /clima, /catalogo, /presets, /regiones)
│   │   ├── core/
│   │   │   ├── weather.py           # Open-Meteo API + fallback 16 regiones de Chile
│   │   │   ├── demand.py            # Balance horario de demanda, habitantes y corrientes de arranque
│   │   │   ├── sizing.py            # Motor físico de dimensionamiento (Solar, Eólico, LiFePO4, Inversor)
│   │   │   ├── economics.py         # Costos CLP, BOS 18%, LCOE, Payback diésel y mitigación CO2
│   │   │   ├── sec_compliance.py   # Validación normativa SEC RIC N°09.1 y RIC N°06
│   │   │   └── layout.py            # Emplazamiento físico (Solar/Eólico/Baterías) vs. vivienda(s)
│   │   ├── models/schemas.py        # Modelos Pydantic fuertemente tipados
│   │   ├── models/catalog.py        # Catálogo de electrodomésticos y presets de campo
│   │   ├── config.py                # Constantes técnicas, de mercado y climáticas
│   │   └── main.py                  # Servidor ASGI FastAPI con montaje estático
│   ├── tests/                       # Suite completa de tests unitarios y de integración
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── index.html                   # GUI interactiva con modo stand 800x480
│   ├── styles.css                   # Sistema de diseño dark slate / amber / cyan
│   └── app.js                       # Lógica reactiva de simulación y gráficos SVG
├── CLAUDE.md                        # Guía de desarrollo y convenciones del proyecto
├── instrucciones_desarrollo_ia.md   # Especificación técnica exhaustiva para agentes
└── LICENSE                          # Licencia Open Source MIT
```

---

## 📜 Bases Oficiales HaCAiThon 2026 (Resumen CAi)

- **Horario de Desarrollo:** 12:40 a 17:10 hrs.
- **Feria de Proyectos:** 17:10 hrs (exhibición en simultáneo ante jurado y público).
- **Criterios de Evaluación:** Innovación y creatividad (15%) · Impacto y relevancia social (25%) · Viabilidad técnica (25%) · Ejecución y funcionamiento (20%) · Comunicación (15%).
- **Licencia:** MIT (Open Source).
- **Contacto CAi:** cai@caiuc.cl · [https://tinyurl.com/Hacaithon](https://tinyurl.com/Hacaithon)
