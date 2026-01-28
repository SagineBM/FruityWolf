# FruityWolf - Run Script
# Run this to start the application

# Activate venv if it exists
if (Test-Path "venv") {
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    
    Write-Host "Installing dependencies..."
    pip install -r requirements.txt
}

# Run the app
Write-Host "Starting FruityWolf..."
python -m FruityWolf
