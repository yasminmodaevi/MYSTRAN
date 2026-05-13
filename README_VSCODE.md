# AeroPLM VS Code Execution Guide

This guide describes how to run and debug the AeroPLM system within VS Code.

## Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Docker & Docker Compose** (Recommended for Database)
- **VS Code Extensions:**
  - Python (Microsoft)
  - ES7+ React/Redux/React-Native snippets (optional)
  - Docker (optional)

---

## Method 1: Hybrid (Docker for DB, Local for App) - Recommended
This method is best for development as it allows for fast hot-reloading.

### 1. Start the Database
Open a terminal in VS Code and run:
```bash
docker-compose up -d db
```

### 2. Run the Backend (FastAPI)
1. Open a new terminal.
2. `cd backend`
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the app:
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/aeroplm
   export VAULT_PATH=./vault
   uvicorn app.main:app --reload
   ```

### 3. Run the Frontend (React)
1. Open a new terminal.
2. `cd frontend`
3. Install dependencies:
   ```bash
   npm install
   ```
4. Start the development server:
   ```bash
   npm start
   ```
   The UI will open at `http://localhost:3000`.

---

## Method 2: Full Docker
To run everything exactly as it would be on-premise:
1. Open a terminal.
2. Run:
   ```bash
   docker-compose up --build
   ```
3. Access the API at `http://localhost:8000` and the UI (if configured in compose) at the respective port.

---

## Method 3: VS Code Debugging (Backend)
1. Go to the **Run and Debug** view in VS Code (`Ctrl+Shift+D`).
2. Select **"FastAPI: Run AeroPLM"**.
3. Press **F5**.
   - *Note: This requires you to have created the virtual environment in Method 1.*

---

## Quick Testing (Toolkit)
To test the FEA integration:
1. Ensure the backend is running.
2. `cd toolkit`
3. Create a dummy result file: `echo "MAXIMUM STRESS = 350.0" > results.f06`
4. Run the connector:
   ```bash
   python nastran_connector.py PART_001 results.f06
   ```
