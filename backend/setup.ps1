# -----------------------------------------------------------
# File: C:\Users\DELL\Desktop\LAMINEFAYE\backend\setup.ps1
# -----------------------------------------------------------
# 1️⃣  Activate (or create) a virtual environment
if (-Not (Test-Path "./venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}
# Activate the venv
& "./venv/Scripts/Activate.ps1"

# 2️⃣  Install dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3️⃣  Verify DATABASE_URL is set in .env
if (-Not (Select-String -Path ".env" -Pattern "DATABASE_URL")) {
    Write-Error "⚠️  DATABASE_URL not found in .env. Please edit .env with your Neon connection string before proceeding."
    exit 1
}

# 4️⃣  Apply Alembic migrations (creates tables in Neon)
Write-Host "Applying Alembic migrations..." -ForegroundColor Cyan
python -m alembic -c migrations/alembic.ini upgrade head

# 5️⃣  Start FastAPI server (development mode)
Write-Host "Starting FastAPI server - visit http://127.0.0.1:8000/api/health" -ForegroundColor Green
python -m uvicorn main:app --reload
# -----------------------------------------------------------
