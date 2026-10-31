#requires -Version 5.1
$ErrorActionPreference = "Stop"

# Pip local image generation bootstrap for Windows.
# Does not download a model checkpoint and does not expose ComfyUI to the network.
$root = Join-Path $env:LOCALAPPDATA "Pip\ComfyUI"
$python = Get-Command python -ErrorAction SilentlyContinue
$git = Get-Command git -ErrorAction SilentlyContinue

if (-not $git) {
    throw "Git is missing. Install Git for Windows from https://git-scm.com/download/win, then run this script again."
}
if (-not $python) {
    throw "Python is missing. Install Python 3.11 (64-bit) from https://www.python.org/downloads/release/python-3119/ and enable 'Add python.exe to PATH'."
}

$pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($pyVersion -ne "3.11") {
    throw "Python 3.11 is recommended for this setup; detected Python $pyVersion. Install Python 3.11 and make sure 'python' resolves to it."
}

if (-not (Test-Path (Join-Path $root "main.py"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $root) | Out-Null
    & git clone https://github.com/comfyanonymous/ComfyUI.git $root
    if ($LASTEXITCODE -ne 0) { throw "Could not clone ComfyUI." }
} else {
    Write-Host "ComfyUI already exists at $root; leaving existing files untouched."
}

$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & python -m venv (Join-Path $root "venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python virtual environment." }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

# A CUDA 12.4 wheel is used as a conservative starting point for the GTX 1070 Ti.
# If this PyTorch build does not support the installed driver, stop here and review the README.
& $venvPython -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) { throw "PyTorch CUDA install failed. Do not continue until the GPU/PyTorch compatibility is resolved." }

& $venvPython -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "ComfyUI requirements install failed." }

Write-Host ""
Write-Host "ComfyUI dependencies are installed."
Write-Host "Next: place a legally obtained SD 1.5 checkpoint (.safetensors) in:"
Write-Host "  $(Join-Path $root 'models\checkpoints')"
Write-Host "Then run pc-server\start-comfyui.ps1 from the Pip repository."
Write-Host "No model was downloaded, and ComfyUI has not been started."
