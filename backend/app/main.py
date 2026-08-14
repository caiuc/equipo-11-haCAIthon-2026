"""
Aplicación principal FastAPI para EnchufaTE.
Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid.
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.api.endpoints import router as api_router

app = FastAPI(
    title="EnchufaTE API - Motor de Dimensionamiento Renovable Off-Grid",
    description=(
        "API tecno-económica para electrificación limpia y autónoma en zonas rurales y aisladas de Chile. "
        "Calcula dimensionamiento fotovoltaico, eólico y almacenamiento LiFePO4 bajo normativa SEC RIC N°09.1 y RIC N°06."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS: la API es de solo lectura/cálculo público (sin login, sesiones ni
# cookies), por lo que se permite cualquier origen para facilitar pruebas y desarrollo. No se
# habilita allow_credentials porque nunca se usan cookies/credenciales, y combinarlo con
# allow_origins=["*"] es una mala práctica de seguridad (además de que los navegadores lo
# ignoran por especificación CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rutas de API
app.include_router(api_router)


@app.get("/api/info", summary="Información de la API")
async def api_info():
    return {
        "app": "EnchufaTE",
        "description": "Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid en Chile",
        "documentation": "/docs",
        "endpoints": {
            "dimensionar": "/api/dimensionar (POST)",
            "clima": "/api/clima (GET)",
            "catalogo": "/api/catalogo (GET)",
            "presets": "/api/presets (GET)",
            "regiones": "/api/regiones (GET)",
            "health": "/api/health (GET)"
        }
    }


# Servir Frontend Estático si existe el directorio
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    @app.get("/", summary="Ruta raíz")
    async def root():
        return await api_info()
