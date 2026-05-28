Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$spec = Join-Path $root "FluxoDeCaixaDiario.spec"

if (-not (Test-Path $python)) {
    throw "Python da virtualenv não encontrado em $python"
}

& $python -m PyInstaller --noconfirm --clean $spec

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar o executável."
}

$distDir = Join-Path $root "dist"
$exePath = Join-Path $distDir "Fluxo de caixa diário.exe"

if (Test-Path $exePath) {
    Write-Host ""
    Write-Host "Executável gerado com sucesso:"
    Write-Host $exePath
}
