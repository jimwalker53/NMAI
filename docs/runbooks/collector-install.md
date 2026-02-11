# Windows Collector Installation Runbook

The NMIA Windows Collector is a lightweight service that runs on Windows servers
near Active Directory Certificate Services (ADCS) Certificate Authorities. It
uses `certutil` to extract certificate data and pushes findings to the NMIA API
server.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Operating System | Windows Server 2016 or later |
| Python | 3.11 or later (added to PATH) |
| Network access | Outbound HTTP(S) to the NMIA API server (port 8000 or 443) |
| Network access | Local access to the ADCS CA (certutil must be able to query it) |
| Permissions | The service account must have read access to the CA database via certutil |
| certutil | Installed by default on Windows Server with ADCS role or RSAT tools |

---

## Installation Steps

### 1. Copy the Collector Package

Copy the `collector-windows/` directory to the target Windows server:

```powershell
# Example: copy to C:\nmia-collector
Copy-Item -Recurse \\fileserver\nmia\collector-windows C:\nmia-collector
```

Or download and extract from the release archive:

```powershell
Invoke-WebRequest -Uri "https://releases.example.com/nmia-collector-latest.zip" -OutFile "C:\temp\collector.zip"
Expand-Archive -Path "C:\temp\collector.zip" -DestinationPath "C:\nmia-collector"
```

### 2. Install Python Dependencies

```powershell
cd C:\nmia-collector
pip install .
```

Or using a virtual environment (recommended):

```powershell
cd C:\nmia-collector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install .
```

### 3. Configure the Collector

Set environment variables for the collector. These can be set system-wide, per-user,
or in a `.env` file in the collector directory.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NMIA_SERVER_URL` | Yes | -- | Full URL of the NMIA API server (e.g., `https://nmia.corp.example.com:8000`) |
| `CONNECTOR_INSTANCE_ID` | Yes | -- | UUID of the ADCS connector configured in NMIA (created via the UI or API) |
| `CERTUTIL_PATH` | No | `certutil` | Full path to certutil.exe if not in PATH |
| `COLLECTOR_PORT` | No | `9000` | Port for the collector's local API |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

**Setting environment variables via PowerShell:**

```powershell
[System.Environment]::SetEnvironmentVariable("NMIA_SERVER_URL", "https://nmia.corp.example.com:8000", "Machine")
[System.Environment]::SetEnvironmentVariable("CONNECTOR_INSTANCE_ID", "11111111-2222-3333-4444-555555555555", "Machine")
```

**Using a .env file** (place in `C:\nmia-collector\.env`):

```
NMIA_SERVER_URL=https://nmia.corp.example.com:8000
CONNECTOR_INSTANCE_ID=11111111-2222-3333-4444-555555555555
CERTUTIL_PATH=C:\Windows\System32\certutil.exe
COLLECTOR_PORT=9000
LOG_LEVEL=INFO
```

### 4. Create the Connector in NMIA

Before the collector can push data, you must create an ADCS connector in NMIA:

1. Log in to the NMIA UI.
2. Navigate to Connectors and create a new connector.
3. Select type "ADCS Certificates".
4. Assign it to the appropriate enclave.
5. Set mode to "push".
6. Note the connector ID -- this is the `CONNECTOR_INSTANCE_ID` for the collector.

Or via the API:

```bash
curl -X POST http://nmia-server:8000/api/v1/connectors \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type_code": "adcs_certificate",
    "enclave_id": "<enclave-uuid>",
    "name": "ADCS - Corp CA Server",
    "config": {"mode": "push"}
  }'
```

---

## Testing

### Manual Test Run

Always test the collector manually before installing as a service.

```powershell
cd C:\nmia-collector

# Activate venv if using one
.\.venv\Scripts\Activate.ps1

# Start the collector API server
uvicorn nmia_collector.main:app --host 0.0.0.0 --port 9000
```

In another terminal, trigger a test scan:

```powershell
# Trigger a small test scan
Invoke-RestMethod -Method POST -Uri "http://localhost:9000/collector/v1/adcs/run" `
  -ContentType "application/json" `
  -Body '{"mode": "full", "max_records": 10, "max_san_fetch": 5}'
```

Check the job status:

```powershell
# Replace <job-id> with the ID returned from the run command
Invoke-RestMethod -Uri "http://localhost:9000/collector/v1/jobs/<job-id>"
```

Verify that:

- The collector can query the local CA via certutil.
- Certificate data is parsed correctly (check job result).
- Data is pushed to the NMIA server (if `callback_url` is configured or automatic push is enabled).
- The NMIA server shows new findings for the connector.

### Connectivity Test

```powershell
# Test network connectivity to NMIA server
Test-NetConnection -ComputerName nmia.corp.example.com -Port 8000

# Test certutil access to local CA
certutil -view -restrict "Disposition=20" -out "SerialNumber,CommonName" | Select-Object -First 20
```

---

## Installing as a Windows Service

Use the provided PowerShell script to install the collector as a Windows service.

### Using install-service.ps1

```powershell
cd C:\nmia-collector\scripts

# Install the service
.\install-service.ps1 -Install `
  -PythonPath "C:\nmia-collector\.venv\Scripts\python.exe" `
  -AppPath "C:\nmia-collector" `
  -ServiceAccount "CORP\svc-nmia-collector" `
  -ServicePassword (Read-Host -AsSecureString "Service account password")
```

The script will:

1. Create a Windows service named "NMIACollector".
2. Set the service to start automatically.
3. Configure it to run under the specified service account.
4. Start the service.

### Manual Service Management

```powershell
# Start the service
Start-Service NMIACollector

# Stop the service
Stop-Service NMIACollector

# Restart the service
Restart-Service NMIACollector

# Check service status
Get-Service NMIACollector
```

---

## Monitoring

### Check Job Status via Collector API

```powershell
# List recent jobs (the collector API must be running)
Invoke-RestMethod -Uri "http://localhost:9000/collector/v1/jobs/<job-id>"
```

### Check from NMIA Server

```bash
# List jobs for the connector from the NMIA API
curl -H "Authorization: Bearer <token>" \
  "http://nmia-server:8000/api/v1/connectors/<connector-id>/jobs?limit=5"
```

### Log Files

| Log Source | Location |
|------------|----------|
| Collector application logs | `C:\nmia-collector\logs\collector.log` (if file logging configured) |
| Windows Event Log | Event Viewer > Application > Source: NMIACollector |
| Service stdout/stderr | Captured by the service wrapper |

---

## Troubleshooting

### certutil Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'certutil' is not recognized` | certutil not in PATH | Set `CERTUTIL_PATH` to full path, e.g., `C:\Windows\System32\certutil.exe` |
| `Access denied` | Service account lacks CA read permissions | Grant the service account "Read" permissions on the CA via `certsrv.msc` |
| `RPC server unavailable` | CA service not running or unreachable | Verify the CA service is running: `Get-Service CertSvc` |
| `No matching records` | Query filter too restrictive or CA is empty | Test manually: `certutil -view -restrict "Disposition=20"` |

### Network Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Connection refused to NMIA server` | Wrong URL or port, firewall blocking | Verify `NMIA_SERVER_URL`, test with `Test-NetConnection` |
| `401 Unauthorized` | Invalid or expired auth token | Verify the connector exists in NMIA and auth is configured |
| `Connection timeout` | Network latency or firewall | Check firewall rules, increase timeout settings |

### Service Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Service fails to start | Missing dependencies or bad config | Check Event Viewer for error details, run manually first |
| Service stops unexpectedly | Unhandled exception | Check collector logs, run in debug mode: `LOG_LEVEL=DEBUG` |
| Port 9000 already in use | Another process on the port | Change `COLLECTOR_PORT` or stop the conflicting process |

---

## Uninstallation

### Remove the Service

```powershell
cd C:\nmia-collector\scripts

# Uninstall the service
.\install-service.ps1 -Uninstall
```

Or manually:

```powershell
Stop-Service NMIACollector
sc.exe delete NMIACollector
```

### Remove the Collector Files

```powershell
# Remove the installation directory
Remove-Item -Recurse -Force C:\nmia-collector

# Remove environment variables (if set at machine level)
[System.Environment]::SetEnvironmentVariable("NMIA_SERVER_URL", $null, "Machine")
[System.Environment]::SetEnvironmentVariable("CONNECTOR_INSTANCE_ID", $null, "Machine")
```

### Clean Up in NMIA

1. Disable or delete the ADCS connector in the NMIA UI.
2. Identities discovered by this connector will remain in the database.

---

## Security Considerations

### Least-Privilege Service Account

The collector service should run under a dedicated service account with minimal
permissions:

- **Local permissions:** Read and execute access to `C:\nmia-collector`. No admin rights.
- **CA permissions:** Read-only access to the CA database (certutil view only).
- **Network permissions:** Outbound HTTP(S) to the NMIA server only.
- **No interactive logon:** The service account should be configured to deny interactive logon.

```powershell
# Deny interactive logon via Group Policy or local security policy
# Computer Configuration > Policies > Windows Settings > Security Settings >
# Local Policies > User Rights Assignment > Deny log on locally
```

### Firewall Rules

Configure the Windows Firewall to allow only necessary traffic:

```powershell
# Allow outbound to NMIA server
New-NetFirewallRule -DisplayName "NMIA Collector - Outbound to API" `
  -Direction Outbound `
  -Protocol TCP `
  -RemotePort 8000 `
  -RemoteAddress "nmia-server-ip" `
  -Action Allow

# Allow inbound on collector port (only if remote management is needed)
New-NetFirewallRule -DisplayName "NMIA Collector - Inbound API" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 9000 `
  -RemoteAddress "nmia-server-ip" `
  -Action Allow

# Block all other inbound on port 9000
New-NetFirewallRule -DisplayName "NMIA Collector - Block Other Inbound" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 9000 `
  -Action Block
```

### Additional Hardening

- **TLS:** Configure the NMIA server with TLS and use `https://` in `NMIA_SERVER_URL`.
- **API keys:** When API key authentication is implemented, configure a unique key
  per collector instance and rotate regularly.
- **Audit:** Enable Windows audit logging for the service account to track certutil
  usage and network connections.
- **Updates:** Keep Python and the collector package updated. Subscribe to NMIA
  release notifications.
