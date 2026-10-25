#requires -Version 5.1
$ErrorActionPreference = "Stop"
$server = Join-Path $PSScriptRoot "pip_server.py"
if (-not (Test-Path $server)) { throw "pip_server.py wurde nicht gefunden." }

if (-not $env:PIP_TOKEN) {
    $env:PIP_TOKEN = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
    Write-Host "Neuer Pip-Token wurde für dieses PowerShell-Fenster erstellt:"
    Write-Host $env:PIP_TOKEN
    Write-Host "Kopiere ihn sicher weg. Er wird beim Schließen des Fensters nicht automatisch gespeichert."
}
if (-not $env:PIP_MODEL) { $env:PIP_MODEL = "qwen3:4b" }
if (-not $env:PIP_COMFYUI_URL) { $env:PIP_COMFYUI_URL = "http://127.0.0.1:8188" }
if (-not $env:PIP_COMFYUI_CHECKPOINT) {
    $env:PIP_COMFYUI_CHECKPOINT = "v1-5-pruned-emaonly-fp16.safetensors"
}
if (-not $env:PIP_IMAGE_WIDTH) { $env:PIP_IMAGE_WIDTH = "512" }
if (-not $env:PIP_IMAGE_HEIGHT) { $env:PIP_IMAGE_HEIGHT = "512" }

Write-Host "Prüfe Ollama lokal..."
try {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    if (-not ($models.models | Where-Object { $_.name -like "qwen3:4b*" })) {
        Write-Warning "qwen3:4b wurde in Ollama nicht gefunden. Prüfe mit 'ollama list'."
    }
} catch {
    throw "Ollama ist unter http://127.0.0.1:11434 nicht erreichbar. Starte Ollama zuerst."
}

try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 5
} catch {
    throw "ComfyUI ist unter http://127.0.0.1:8188 nicht erreichbar. Starte zuerst ComfyUI und prüfe den Browser."
}

Write-Host "Starte Pip-Server. ComfyUI muss lokal unter 127.0.0.1:8188 erreichbar sein."
Write-Host "Bild-Checkpoint: $env:PIP_COMFYUI_CHECKPOINT"
Write-Host "Wichtig: Port 8765/11434/8188 niemals öffentlich freigeben."
python $server
