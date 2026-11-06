$ErrorActionPreference = "Stop"

python -m pip install -e ".[dev]"
python -m PyInstaller --clean Sam.spec
Write-Host "Built dist\Sam.exe"
