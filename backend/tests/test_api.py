"""
Tests de integración para los endpoints de la API REST de EnchufaTE y frontend estático.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["service"] == "EnchufaTE Backend Engine"


@pytest.mark.asyncio
async def test_api_info_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "EnchufaTE"
        assert "endpoints" in data


@pytest.mark.asyncio
async def test_frontend_static_serving():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "EnchufaTE" in resp.text


@pytest.mark.asyncio
async def test_catalogo_and_presets():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Catálogo
        resp_cat = await client.get("/api/catalogo")
        assert resp_cat.status_code == 200
        catalogo = resp_cat.json()
        assert isinstance(catalogo, list)
        assert len(catalogo) > 5

        # Presets
        resp_pre = await client.get("/api/presets")
        assert resp_pre.status_code == 200
        presets = resp_pre.json()
        assert "vivienda_rural_estandar" in presets
        assert "posta_rural_salud" in presets

        # Regiones
        resp_reg = await client.get("/api/regiones")
        assert resp_reg.status_code == 200
        regiones = resp_reg.json()
        assert len(regiones) >= 16


@pytest.mark.asyncio
async def test_dimensionar_endpoint_full_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "location": {
                "latitude": -35.96,
                "longitude": -72.31,
                "region_id": "maule",
                "locality_name": "Sector Rural Cauquenes"
            },
            "inhabitants": 4,
            "appliances": [
                {
                    "id": "refrigerador_inverter",
                    "name": "Refrigerador Inverter Clase A++",
                    "category": "refrigeracion",
                    "power_w": 120.0,
                    "hours_per_day": 8.0,
                    "quantity": 1,
                    "surge_multiplier": 2.5,
                    "duty_cycle": 0.45,
                    "enabled": True
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
                    "enabled": True
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
                    "enabled": True
                }
            ],
            "custom_psh": 5.2,
            "custom_wind_speed": 3.6
        }

        resp = await client.post("/api/dimensionar", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["success"] is True
        assert "climate" in data
        assert "demand" in data
        assert "solar" in data
        assert "battery" in data
        assert "inverter" in data
        assert "economics" in data
        assert "environmental" in data
        assert "sec_compliance" in data

        # Validaciones de consistencia
        assert data["solar"]["num_panels"] >= 1
        assert data["battery"]["nominal_capacity_kwh"] >= 2.4
        assert data["inverter"]["nominal_power_kva"] >= 1.5
        assert data["economics"]["total_capex_clp"] > 0
        assert data["environmental"]["annual_co2_avoided_tons"] > 0
        assert data["sec_compliance"]["normative_status"] == "VALIDADO_SEC_RIC_09_1"


@pytest.mark.asyncio
async def test_dimensionar_hybrid_magallanes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "location": {
                "latitude": -53.16,
                "longitude": -70.91,
                "region_id": "magallanes",
                "locality_name": "Estancia Rural Porvenir"
            },
            "inhabitants": 3,
            "appliances": [
                {
                    "id": "refrigerador_inverter",
                    "name": "Refrigerador Inverter",
                    "category": "refrigeracion",
                    "power_w": 120.0,
                    "hours_per_day": 8.0,
                    "quantity": 1,
                    "surge_multiplier": 2.5,
                    "duty_cycle": 0.5,
                    "enabled": True
                }
            ],
            "custom_psh": 2.8,
            "custom_wind_speed": 7.8  # > 4.5 m/s -> Híbrido
        }

        resp = await client.post("/api/dimensionar", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["wind"]["is_active"] is True
        assert data["wind"]["turbines_count"] == 1
        assert data["solar"]["system_type"] == "HYBRID_SOLAR_WIND"


@pytest.mark.asyncio
async def test_dimensionar_households_and_options_and_layout():
    """Verifica el escalado por viviendas, la comparativa de 3 opciones y el plano de emplazamiento."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        base_payload = {
            "location": {
                "latitude": -38.43,
                "longitude": -71.36,
                "region_id": "araucania",
                "locality_name": "Curarrehue"
            },
            "inhabitants": 4,
            "appliances": [
                {
                    "id": "refrigerador_inverter",
                    "name": "Refrigerador Inverter",
                    "category": "refrigeracion",
                    "power_w": 120.0,
                    "hours_per_day": 8.0,
                    "quantity": 1,
                    "surge_multiplier": 2.5,
                    "duty_cycle": 0.5,
                    "enabled": True
                }
            ],
            "custom_psh": 4.5,
            "custom_wind_speed": 3.0
        }

        # households=1 vs households=3 debe escalar la demanda y el dimensionamiento
        resp1 = await client.post("/api/dimensionar", json={**base_payload, "households": 1})
        resp3 = await client.post("/api/dimensionar", json={**base_payload, "households": 3})
        assert resp1.status_code == 200 and resp3.status_code == 200
        data1, data3 = resp1.json(), resp3.json()

        assert data3["demand"]["households_count"] == 3
        assert data3["demand"]["total_daily_kwh"] > data1["demand"]["total_daily_kwh"]
        assert data3["solar"]["installed_pv_kwp"] >= data1["solar"]["installed_pv_kwp"]

        # Comparativa: siempre las 3 opciones completas (económica, recomendada, resiliente)
        option_ids = {o["option_id"] for o in data1["options"]}
        assert option_ids == {"economica", "recomendada", "resiliente"}
        for opt in data1["options"]:
            assert opt["total_capex_clp"] > 0
            assert opt["num_panels"] >= 1
            assert len(opt["bom"]) >= 4
            assert all(item["purchase_url"] for item in opt["bom"] if item["category"] != "Servicios de Ingeniería y SEC")
            assert opt["installation_service_url"] == "https://wlhttp.sec.cl/buscadorinstaladores/buscador.do"
            assert opt["sec_installer_registry_url"] == "https://www.sec.cl"
            for item in opt["bom"]:
                if item["purchase_url"]:
                    assert item["purchase_url"].startswith("https://listado.mercadolibre.cl/")

        # Plano de instalación: zonas de emplazamiento coherentes con la(s) vivienda(s)
        layout = data3["site_layout"]
        assert layout["households_count"] == 3
        assert layout["solar_zone"]["bearing_deg"] == 0.0  # Norte geográfico (Hemisferio Sur)
        assert layout["solar_zone"]["area_m2"] > 0
        assert len(layout["general_notes"]) >= 2
        # Radio de cobertura práctico: siempre positivo y dentro del rango de diseño
        assert 0 < layout["coverage_radius_m"] <= 150.0


@pytest.mark.asyncio
async def test_dimensionar_preferred_option_overrides_primary():
    """El campo preferred_option debe cambiar la configuración principal devuelta (BOM, SEC, etc)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "location": {"latitude": -35.96, "longitude": -72.31, "region_id": "maule", "locality_name": "Cauquenes"},
            "inhabitants": 4,
            "appliances": [
                {
                    "id": "refrigerador_inverter",
                    "name": "Refrigerador Inverter",
                    "category": "refrigeracion",
                    "power_w": 120.0,
                    "hours_per_day": 8.0,
                    "quantity": 1,
                    "enabled": True
                }
            ],
            "custom_psh": 5.0,
            "custom_wind_speed": 3.5,
            "preferred_option": "economica"
        }

        resp = await client.post("/api/dimensionar", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["solar"]["system_type"] == "SOLAR_ONLY"
        assert data["wind"]["is_active"] is False
        option_ids = {o["option_id"] for o in data["options"]}
        assert option_ids == {"economica", "recomendada", "resiliente"}


@pytest.mark.asyncio
async def test_geocode_endpoints_proxy_nominatim():
    """Los endpoints de geocodificación deben responder desde el backend (evita el error de referer del navegador)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_rev = await client.get("/api/geocode/reverse", params={"lat": -33.45, "lon": -70.66})
        assert resp_rev.status_code == 200
        assert "latitude" in resp_rev.json()

        resp_search = await client.get("/api/geocode/search", params={"q": "Santiago, Chile"})
        assert resp_search.status_code == 200
        assert isinstance(resp_search.json(), list)
