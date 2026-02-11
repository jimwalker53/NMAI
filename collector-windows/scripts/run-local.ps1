# Run NMIA Collector locally for development
param(
    [int]$Port = 9000,
    [string]$NmiaServer = "http://localhost:8000"
)
$env:NMIA_SERVER_URL = $NmiaServer
$env:LOG_LEVEL = "DEBUG"
Write-Host "Starting NMIA Collector on port $Port..."
Write-Host "NMIA Server: $NmiaServer"
python -m uvicorn nmia_collector.main:app --host 0.0.0.0 --port $Port --reload
