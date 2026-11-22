"""Configuración centralizada. Los valores variables o sensibles se leen desde
variables de entorno (archivo .env), nunca desde el código fuente."""

import os
from pathlib import Path

try:  # python-dotenv es opcional: si no está, se usan las variables del sistema
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # pragma: no cover
    pass

RAIZ_PROYECTO = Path(__file__).resolve().parent


def _entero(nombre, defecto, minimo, maximo):
    try:
        valor = int(os.environ.get(nombre, defecto))
    except ValueError:
        return defecto
    return max(minimo, min(maximo, valor))


DB_RUTA = os.environ.get("VIAJES_DB", str(RAIZ_PROYECTO / "viajes_aventura.db"))
LOG_RUTA = os.environ.get("VIAJES_LOG", str(RAIZ_PROYECTO / "viajes.log"))
MAX_INTENTOS_LOGIN = _entero("VIAJES_MAX_INTENTOS", 3, 1, 10)
BLOQUEO_LOGIN_SEG = _entero("VIAJES_BLOQUEO_SEG", 60, 10, 3600)
