# Start EcomAI admin + portal APIs
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "ecom-api")
& (Join-Path $root "venv\Scripts\python.exe") run.py
