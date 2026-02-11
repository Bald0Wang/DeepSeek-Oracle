[CmdletBinding()]
param(
  [ValidateSet("up", "down", "restart", "logs", "ps")]
  [string]$Action = "up",
  [string]$EnvFile = ".env.docker",
  [switch]$NoBuild,
  [int]$HealthTimeoutSec = 150
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Write-Step {
  param([string]$Message)
  Write-Host "[docker] $Message"
}

function Ensure-Docker {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Please install Docker Desktop first."
  }
  docker compose version | Out-Null
}

function Ensure-EnvFile {
  if (Test-Path $EnvFile) {
    return
  }

  $exampleFile = ".env.docker.example"
  if (-not (Test-Path $exampleFile)) {
    throw "Missing $EnvFile and $exampleFile."
  }

  Copy-Item $exampleFile $EnvFile
  Write-Step "Created $EnvFile from $exampleFile. Please review API keys and ports if needed."
}

function Get-EnvValue {
  param([string]$Key)

  if (-not (Test-Path $EnvFile)) {
    return $null
  }

  $line = Get-Content $EnvFile |
    Where-Object { $_ -match "^\s*$Key\s*=" } |
    Select-Object -Last 1

  if (-not $line) {
    return $null
  }

  return ($line -replace "^\s*$Key\s*=\s*", "").Trim()
}

function Resolve-HostPath {
  param([string]$PathValue)

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return $null
  }
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return $PathValue
  }
  return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
}

function Ensure-IzthonPath {
  $rawPath = Get-EnvValue "IZTHON_SRC_PATH_HOST"
  if ([string]::IsNullOrWhiteSpace($rawPath)) {
    $rawPath = "../izthon/src"
  }

  $resolvedPath = Resolve-HostPath $rawPath
  if (-not (Test-Path $resolvedPath)) {
    throw "IZTHON_SRC_PATH_HOST not found: '$rawPath' -> '$resolvedPath'. Update $EnvFile and retry."
  }
}

function Wait-ContainerReady {
  param(
    [string]$ContainerName,
    [int]$TimeoutSec
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    $status = docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $ContainerName 2>$null
    if ($LASTEXITCODE -eq 0) {
      $status = "$status".Trim().ToLowerInvariant()
      if ($status -eq "healthy" -or $status -eq "running") {
        return
      }
    }
    Start-Sleep -Seconds 2
  }

  throw "Container '$ContainerName' was not ready within ${TimeoutSec}s."
}

function Compose {
  param([string[]]$ComposeArgs)

  & docker compose --env-file $EnvFile @ComposeArgs
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose $($ComposeArgs -join ' ') failed."
  }
}

function Print-AccessInfo {
  $frontendPort = Get-EnvValue "FRONTEND_PORT"
  $backendPort = Get-EnvValue "BACKEND_PORT"
  if ([string]::IsNullOrWhiteSpace($frontendPort)) { $frontendPort = "8080" }
  if ([string]::IsNullOrWhiteSpace($backendPort)) { $backendPort = "5000" }

  Write-Host ""
  Write-Host "Ready:"
  Write-Host "  Frontend: http://localhost:$frontendPort"
  Write-Host "  Backend : http://localhost:$backendPort/healthz"
  Write-Host ""
  Write-Host "Common commands:"
  Write-Host "  .\docker.ps1 logs"
  Write-Host "  .\docker.ps1 ps"
  Write-Host "  .\docker.ps1 down"
}

Ensure-Docker
Ensure-EnvFile

switch ($Action) {
  "up" {
    Ensure-IzthonPath
    $composeArgs = @("up", "-d")
    if (-not $NoBuild) {
      $composeArgs += "--build"
    }
    Write-Step "Starting services..."
    Compose $composeArgs
    Write-Step "Waiting for backend health..."
    Wait-ContainerReady -ContainerName "deepseek-oracle-backend" -TimeoutSec $HealthTimeoutSec
    Write-Step "Waiting for frontend status..."
    Wait-ContainerReady -ContainerName "deepseek-oracle-frontend" -TimeoutSec $HealthTimeoutSec
    Compose @("ps")
    Print-AccessInfo
  }
  "down" {
    Write-Step "Stopping services..."
    Compose @("down")
  }
  "restart" {
    Write-Step "Restarting services..."
    Compose @("down")
    $composeArgs = @("up", "-d")
    if (-not $NoBuild) {
      $composeArgs += "--build"
    }
    Compose $composeArgs
    Wait-ContainerReady -ContainerName "deepseek-oracle-backend" -TimeoutSec $HealthTimeoutSec
    Wait-ContainerReady -ContainerName "deepseek-oracle-frontend" -TimeoutSec $HealthTimeoutSec
    Compose @("ps")
    Print-AccessInfo
  }
  "logs" {
    Compose @("logs", "-f", "--tail", "200")
  }
  "ps" {
    Compose @("ps")
  }
}
