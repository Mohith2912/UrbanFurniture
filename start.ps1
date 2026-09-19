$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Unable to install dependencies.' }
if (Test-Path -LiteralPath "$env:LOCALAPPDATA\UrbanFurniture\PostgreSQL17\pgsql\bin\postgres.exe") {
    & '.\.venv\Scripts\python.exe' scripts\setup_native_postgres.py
    if ($LASTEXITCODE -ne 0) { throw 'Unable to start the native PostgreSQL database.' }
}
& '.\.venv\Scripts\python.exe' serve.py
