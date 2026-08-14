#!/usr/bin/env python3
"""
Script de ejecución para el servidor backend de EnchufaTE.
"""
import sys
import os
from pathlib import Path
import uvicorn

# Asegurar que backend está en el PYTHONPATH
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Iniciando EnchufaTE Backend en http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
