# BiblioNexo — Sprint 1 MVP (Arquitectura Desacoplada Backend REST + Frontend Vistas)

Sistema Web de Gestión de Catálogo y Circulación Bibliotecaria (Equipo 57).
Reestructura el **MVP del Sprint 1 completo** (las 11 historias del Release 1 + Autenticación y Autorización por Rol + Servicios de Dominio + Pruebas + Diagramas C4) bajo la **arquitectura de 2 contenedores (`backend/` + `frontend/`)**.

## Estructura del Proyecto
- `backend/`: API REST modular en FastAPI + SQLAlchemy + SQLite (`app/models.py`, `app/services/`, `app/routers/`, `app/seed.py`) y suite de pruebas (`tests/test_sprint1.py`).
- `frontend/`: Interfaz web desacoplada (`src/index.html`, `src/dashboard.html`, `src/app.js`, `src/styles.css`) servida con Nginx o cualquier servidor estático, con las vistas para las **11 historias de usuario del Sprint 1**.
- `docs/c4/`: Diagramas C4 en PlantUML (`c1_contexto.puml`, `c2_contenedores.puml`, `c3_componentes.puml`).

## Historias Implementadas (Release 1 — 11 Historias)
1. **Préstamos:** Consultar disponibilidad (`GET /api/v1/disponibilidad`), Agregar préstamo (`POST /api/v1/prestamos`), Registrar devolución (`POST /api/v1/prestamos/devolver`), Consultar préstamos (`GET /api/v1/prestamos`).
2. **Libros:** Consultar libros (`GET /api/v1/libros`), Agregar libros con ejemplares (`POST /api/v1/libros`).
3. **Usuarios:** Consultar usuario (`GET /api/v1/usuarios`), Agregar usuario (`POST /api/v1/usuarios`).
4. **Sanciones:** Consultar vencimiento (`GET /api/v1/vencimientos`), Consultar sanciones (`GET /api/v1/sanciones`), Agregar sanción (`POST /api/v1/sanciones`).

## Ejecución Local
### 1. Levantar el Backend (Puerto 8000)
```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.seed
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```
*(En Windows PowerShell usa `.\.venv\Scripts\python.exe`)*

### 2. Levantar el Frontend (Puerto 8080)
En otra terminal:
```bash
cd frontend/src
python3 -m http.server 8080
```
Abre `http://127.0.0.1:8080/index.html` e inicia sesión con:
- **Correo:** `biblioteca@demo.local`
- **Contraseña:** `DemoBiblioteca2026!`

### 3. Ejecutar Pruebas Automatizadas
```bash
cd backend
pytest -q
```
