# FIA Core setup for Windows (PowerShell 5.1+).
# Creates .venv inside the project, installs fia-core-full there and runs
# `fia init`. Re-running is safe: nothing is overwritten.
#
# Usage:
#   irm https://raw.githubusercontent.com/mcpedrogm-art/fia-core/main/setup.ps1 | iex
#   .\setup.ps1 [-Dir PATH] [-Modules ui,security]

param(
    [string]$Dir = ".",
    [string[]]$Modules = @()
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: no se encontro 'python' en el PATH." -ForegroundColor Red
    Write-Host "Instala Python 3.8 o superior desde https://www.python.org/downloads/ y reintenta."
    exit 1
}

$project = (Resolve-Path -LiteralPath $Dir).Path
$venv = Join-Path $project ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
$fia = Join-Path $venv "Scripts\fia.exe"

if (Test-Path -LiteralPath $venvPy) {
    Write-Host "[1/3] .venv ya existe, se reutiliza"
} else {
    Write-Host "[1/3] Creando entorno virtual en .venv ..."
    & python -m venv $venv
    if (-not (Test-Path -LiteralPath $venvPy)) {
        Write-Host "ERROR: no se pudo crear el entorno virtual." -ForegroundColor Red
        exit 1
    }
}

Write-Host "[2/3] Instalando fia-core-full dentro del proyecto ..."
& $venvPy -m pip install --disable-pip-version-check --quiet --upgrade fia-core-full
if (-not (Test-Path -LiteralPath $fia)) {
    Write-Host "ERROR: la instalacion no genero el comando fia." -ForegroundColor Red
    exit 1
}

Write-Host "[3/3] Inicializando el proyecto (PROJECT.md, TASK.md, .fia/) ..."
$moduleArg = $Modules -join ","
if ($moduleArg) {
    & $fia init -d $project --modules $moduleArg
} else {
    & $fia init -d $project
}

$gitignore = Join-Path $project ".gitignore"
if (Test-Path -LiteralPath $gitignore) {
    if (-not (Select-String -LiteralPath $gitignore -Pattern '^\.venv/?\s*$' -Quiet)) {
        Add-Content -LiteralPath $gitignore -Value ".venv/"
    }
} else {
    Set-Content -LiteralPath $gitignore -Value ".venv/"
}

Write-Host ""
Write-Host "Listo. Nada se ha instalado fuera de este proyecto." -ForegroundColor Green
Write-Host ""
Write-Host "Para usarlo, desde esta carpeta:"
Write-Host "  .venv\Scripts\fia status"
Write-Host "  .venv\Scripts\fia test -- <tu comando de test>"
Write-Host "  .venv\Scripts\fia verify"
Write-Host ""
Write-Host "O activa el entorno una vez por sesion y usa 'fia' directamente:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
