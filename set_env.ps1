# Script per impostare le variabili d'ambiente
# (eseguire con `.\set_env.ps1` su Windows)

$env:GOOGLE_CLOUD_PROJECT="sistemi-distribuiti-nuovo"
$env:GOOGLE_APPLICATION_CREDENTIALS="$PSScriptRoot\credentials.json"
$env:USE_PUBSUB="false"

Write-Host "Variabili d'ambiente impostate:" -ForegroundColor Green
Write-Host "  GOOGLE_CLOUD_PROJECT=$env:GOOGLE_CLOUD_PROJECT"
Write-Host "  GOOGLE_APPLICATION_CREDENTIALS=$env:GOOGLE_APPLICATION_CREDENTIALS"
Write-Host "  USE_PUBSUB=$env:USE_PUBSUB"

if (-not (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS)) {
    Write-Host ""
    Write-Host "ATTENZIONE: Il file delle credenziali NON esiste in: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Yellow
    Write-Host ""
}
