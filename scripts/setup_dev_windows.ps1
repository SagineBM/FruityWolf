# Setup Development Environment on Windows

Write-Host "Setting up FruityWolf Dev Environment..." -ForegroundColor Cyan

# Check Python
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "3.11") {
    Write-Host "Found Python 3.11: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "WARNING: Python 3.11 recommended. Found: $pythonVersion" -ForegroundColor Yellow
}

# Create venv if not exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate
Write-Host "Activating venv..."
.\venv\Scripts\Activate.ps1

# Install requirements
Write-Host "Installing dependencies..."
pip install -r requirements.txt

# Run verification
Write-Host "Verifying environment..."
python scripts/verify_env.py

Write-Host "Done! To run the app:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\activate"
Write-Host "  python -m FruityWolf"
