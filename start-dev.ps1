# Development Startup Script
# This script starts both the Python agent backend and React frontend

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "AI Receptionist - Development Mode" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] Warning: Virtual environment not found at venv\" -ForegroundColor Yellow
    Write-Host "    Continuing without virtual environment..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/4] Checking Python dependencies..." -ForegroundColor Green
python -c "import livekit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] LiveKit not installed. Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "[3/4] Starting Python Agent Backend..." -ForegroundColor Green
Write-Host "    This will run in the background" -ForegroundColor Gray
Write-Host ""

# Start Python agent in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; if (Test-Path 'venv\Scripts\Activate.ps1') { & 'venv\Scripts\Activate.ps1' }; Write-Host 'Starting Agent Backend...' -ForegroundColor Cyan; python main.py dev"

# Wait a bit for agent to start
Write-Host "    Waiting for agent to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "[4/4] Starting React Frontend..." -ForegroundColor Green
Write-Host "    This will run in a new window" -ForegroundColor Gray
Write-Host ""

# Check if node_modules exists in frontend
if (-not (Test-Path "frontend\agent-starter-react\node_modules")) {
    Write-Host "[!] Installing frontend dependencies (first time only)..." -ForegroundColor Yellow
    Set-Location "frontend\agent-starter-react"
    npm install
    Set-Location "..\..\"
}

# Start frontend in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend\agent-starter-react'; Write-Host 'Starting Frontend...' -ForegroundColor Cyan; npm run dev"

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "✓ Development servers starting!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend Agent: Running in separate window" -ForegroundColor Cyan
Write-Host "Frontend UI:   http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop the servers" -ForegroundColor Yellow
Write-Host ""
