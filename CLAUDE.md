# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EnergIA** is a web platform for managing electricity consumption. Users upload CFE (Mexican electricity utility) PDF receipts, which are validated and analyzed via OpenAI GPT-4 Vision to extract consumption data, support future prediction, and generate savings recommendations.

## Running the Application

There is no build step. Start the Flask backend, then open the HTML files directly in a browser.

```bash
# Install dependencies (once)
pip install flask flask-cors mysql-connector-python pdfplumber pandas openai

# Start the backend API (port 5000)
python app.py
```

Frontend pages are served as static files:
- `login.html` → `signup.html` → `dashboard.html`

## Database Setup

Requires MySQL running via XAMPP. Execute the SQL script in `README.md` to create the `ControlRecibos` database with all 8 tables. Then insert the initial role:

```sql
INSERT INTO Rol (Id, Nombre) VALUES (1, 'Usuario Estándar');
```

MySQL connection config is hardcoded in `app.py` (host, user, password, database).

## Roles y seguridad

Existen dos roles en la tabla `Rol`:
- `Id=1` → Usuario estándar → redirige a `dashboard.html`
- `Id=2` → Administrador → redirige a `admin.html`

El login devuelve `rol` y el frontend lo guarda en `localStorage('userRol')`. Cada página verifica el rol y redirige si no corresponde. Los endpoints `/api/admin/*` verifican en base de datos que el `adminId` recibido tenga `Rol=2` antes de responder.

Para crear un administrador ejecutar en MySQL:
```sql
INSERT INTO Rol (Id, Nombre) VALUES (2, 'Administrador');
UPDATE Usuario SET Rol = 2 WHERE Correo = 'correo@admin.com';
```

## Architecture

### Backend (`app.py`)
Flask REST API on `http://127.0.0.1:5000`. All endpoints are prefixed with `/api/`:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/registro` | POST | User registration (hashed password via werkzeug) |
| `/api/login` | POST | Authentication |
| `/api/upload` | POST | PDF upload + validation + OpenAI extraction |
| `/api/recibos/<user_id>` | GET | List user's receipts |
| `/api/recibos/<recibo_id>` | DELETE | Delete a receipt |
| `/api/uploads/<filename>` | GET | Serve uploaded PDF files |
| `/api/admin/usuarios` | GET | List all standard users (requires `adminId` query param) |
| `/api/admin/usuarios/<id>` | DELETE | Delete user + cascade (requires `adminId` in body) |
| `/api/admin/tickets` | GET | List all error tickets with user email (requires `adminId`) |
| `/api/admin/tickets/<id>` | DELETE | Delete ticket (requires `adminId` in body) |

### PDF Processing Pipeline (`validar_pdf.py`)
Two-stage process called during upload:
1. `validar_recibo_cfe(path)` — uses `pdfplumber` to check for CFE keywords in the PDF text
2. `extraer_datos_recibo_openai(path)` — converts PDF pages to images and sends them to OpenAI GPT-4 Vision to extract structured data (consumption kWh, cost, billing period, 12-month history)
3. `guardar_dataset(data)` — appends extracted data to `dataset_consumo.csv` for historical tracking

### Frontend
Three HTML pages with vanilla JS using the Fetch API to communicate with the Flask backend. No framework or bundler.

- `dashboard.html` has three tabs: Predictions (mock bar chart), Upload (drag-and-drop PDF zone), and View Files (receipt list)
- User ID is stored in `localStorage` after login

### Database Schema Key Relationships
`Rol` ← `Usuario` ← `Recibos` ← `Prediccion`  
`Usuario` ← `Analisis`, `Notificacion`, `Errores`

## Configuration

The OpenAI API key is hardcoded in `validar_pdf.py` and MySQL credentials are hardcoded in `app.py`. Move these to environment variables (`.env` + `python-dotenv`) before any deployment.

## In-Progress / Partial Features

- **AI Predictions:** DB table `Prediccion` exists; frontend shows a mock chart — not yet connected to real predictions
- **Telegram Notifications:** `TelegramChatId` field on `Usuario`, `Notificacion` table, and signup UI field exist — backend logic not yet implemented
- **Analysis/Recommendations:** `Analisis` table exists — generation logic not yet implemented
- **Error Logging:** `Errores` table exists — not yet wired up
