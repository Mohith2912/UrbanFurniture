$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$backendListener = Get-NetTCPConnection -State Listen -LocalPort 5050 -ErrorAction SilentlyContinue
if (-not $backendListener) {
    $backend = Start-Process -FilePath 'python' -ArgumentList 'serve.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot\data\server.log" -RedirectStandardError "$PSScriptRoot\data\server-error.log" -PassThru
    $backend.Id | Set-Content -LiteralPath "$PSScriptRoot\data\server.pid"
    Start-Sleep -Seconds 2
}

Set-Location -LiteralPath "$PSScriptRoot\Frontend"
if (-not (Test-Path -LiteralPath 'node_modules\next')) {
    npm install
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install the Next.js frontend dependencies.' }
}
npm run dev
