#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Ensure-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "$Name is not installed. $InstallHint"
    }
}

Write-Host "==> OpenRoleRadar bootstrap (Windows)" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
}
Ensure-Command uv "Install uv from https://docs.astral.sh/uv/"

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pnpm via corepack..."
    Ensure-Command node "Install Node.js 22+ from https://nodejs.org/"
    corepack enable
    corepack prepare pnpm@9 --activate
}
Ensure-Command pnpm "Run: corepack enable && corepack prepare pnpm@9 --activate"

Write-Host "==> Python engine" -ForegroundColor Cyan
Push-Location (Join-Path $Root "engine")
uv sync --all-extras --dev
Pop-Location

Write-Host "==> Astro site" -ForegroundColor Cyan
Push-Location (Join-Path $Root "site")
pnpm install
Pop-Location

Write-Host "==> Validate seed sources" -ForegroundColor Cyan
uv run --directory (Join-Path $Root "engine") python (Join-Path $Root "scripts\validate-sources.py")

Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  cd engine && uv run openroleradar sync --sample"
Write-Host "  cd site && pnpm dev"
