"""Configuración centralizada del backend de BiblioNexo.

Cada valor se lee de una variable de entorno y, si no existe, se usa un valor
por defecto pensado solo para desarrollo local. En producción deben definirse
explícitamente (ver ``.env.example`` y ``docker-compose.yml``).
"""
import os

# Cadena de conexión SQLAlchemy. Por defecto, un archivo SQLite en el
# directorio desde el que se ejecuta el proceso (normalmente backend/).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biblionexo.db")
# Clave secreta usada para firmar los tokens de acceso (HMAC-SHA256) y la
# cookie de sesión de Starlette. Debe ser larga, aleatoria y privada.
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production-biblionexo-2026")
# Contraseña asignada a los usuarios de demostración creados por app.seed.
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DemoBiblioteca2026!")