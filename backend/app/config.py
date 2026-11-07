import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biblionexo.db")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production-biblionexo-2026")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DemoBiblioteca2026!")
