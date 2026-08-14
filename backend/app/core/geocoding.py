"""
Proxy de geocodificación para EnchufaTE.
Todas las consultas a Nominatim/OpenStreetMap se hacen desde el backend (servidor a servidor)
con un User-Agent identificable, tal como exige la política de uso de Nominatim
(https://operations.osmfoundation.org/policies/nominatim/). Esto evita el error
"referer is required" que ocurre al llamar a Nominatim directamente desde el navegador,
donde el header Referer no siempre está disponible o es válido.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("enchufate.geocoding")

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "EnchufaTE-HaCAiThon2026/1.0 (contacto: martin.castro@gmail.com)"


def _extract_region_comuna(address: Dict[str, Any]) -> Dict[str, Optional[str]]:
    comuna = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
    region = address.get("state") or address.get("region")
    return {"comuna": comuna, "region_name": region}


async def reverse_geocode(lat: float, lon: float, timeout_sec: float = 6.0) -> Dict[str, Any]:
    """Convierte una coordenada en un nombre de localidad, comuna y región legible."""
    params = {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 12, "addressdetails": 1, "accept-language": "es"}
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                f"{NOMINATIM_BASE_URL}/reverse",
                params=params,
                headers={"User-Agent": USER_AGENT}
            )
            if resp.status_code == 200:
                data = resp.json()
                address = data.get("address", {})
                extracted = _extract_region_comuna(address)
                return {
                    "display_name": data.get("display_name"),
                    "comuna": extracted["comuna"],
                    "region_name": extracted["region_name"],
                    "latitude": lat,
                    "longitude": lon
                }
    except Exception as exc:
        logger.warning(f"Error en geocodificación inversa ({lat},{lon}): {exc}")

    return {"display_name": None, "comuna": None, "region_name": None, "latitude": lat, "longitude": lon}


async def search_locality(query: str, limit: int = 5, timeout_sec: float = 6.0) -> List[Dict[str, Any]]:
    """Busca localidades/direcciones dentro de Chile por texto libre."""
    params = {
        "format": "jsonv2",
        "q": query,
        "countrycodes": "cl",
        "limit": limit,
        "addressdetails": 1,
        "accept-language": "es"
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                f"{NOMINATIM_BASE_URL}/search",
                params=params,
                headers={"User-Agent": USER_AGENT}
            )
            if resp.status_code == 200:
                results = resp.json()
                output = []
                for r in results:
                    address = r.get("address", {})
                    extracted = _extract_region_comuna(address)
                    output.append({
                        "display_name": r.get("display_name"),
                        "latitude": float(r["lat"]),
                        "longitude": float(r["lon"]),
                        "comuna": extracted["comuna"],
                        "region_name": extracted["region_name"]
                    })
                return output
    except Exception as exc:
        logger.warning(f"Error buscando localidad '{query}': {exc}")

    return []
