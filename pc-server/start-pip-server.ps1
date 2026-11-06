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
# Text-only setup: no ComfyUI required.
if (-not $env:PIP_NUM_GPU) { $env:PIP_NUM_GPU = "0" }
if (-not $env:PIP_NUM_CTX) { $env:PIP_NUM_CTX = "4096" }
if (-not $env:PIP_NUM_PREDICT) { $env:PIP_NUM_PREDICT = "256" }

Write-Host "Prüfe Ollama lokal..."
try {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    if (-not ($models.models | Where-Object { $_.name -like "qwen3:4b*" })) {
        Write-Warning "qwen3:4b wurde in Ollama nicht gefunden. Prüfe mit 'ollama list'."
    }
} catch {
    throw "Ollama ist unter http://127.0.0.1:11434 nicht erreichbar. Starte Ollama zuerst."
}

Write-Host "Starte Pip-Server ohne Bildgenerierung."
Write-Host "Ollama-Einstellungen: CPU=$env:PIP_NUM_GPU, Kontext=$env:PIP_NUM_CTX, Antwortlimit=$env:PIP_NUM_PREDICT"
python $server
