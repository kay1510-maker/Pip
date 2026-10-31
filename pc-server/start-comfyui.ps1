#requires -Version 5.1
$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "Pip\ComfyUI"
$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path (Join-Path $root "main.py")) -or -not (Test-Path $python)) {
    throw "ComfyUI is not installed yet. Run pc-server\setup-comfyui.ps1 first."
}
$checkpointDir = Join-Path $root "models\checkpoints"
$checkpoints = @(Get-ChildItem -Path $checkpointDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in ".safetensors", ".ckpt" })
if ($checkpoints.Count -eq 0) {
    throw "No checkpoint found. Add a legally obtained SD 1.5 checkpoint to $checkpointDir, then run this script again."
}
Write-Host "Starting ComfyUI on 127.0.0.1 only. Do not expose port 8188 publicly."
& $python (Join-Path $root "main.py") --listen 127.0.0.1 --port 8188 --lowvram
