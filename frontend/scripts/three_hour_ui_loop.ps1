param(
  [double]$DurationHours = 3,
  [int]$PauseSeconds = 10,
  [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$frontendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $frontendRoot

$logDir = Join-Path $frontendRoot 'output\ui-loop-audit'
if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$endTime = (Get-Date).AddHours($DurationHours)
$cycle = 0

Write-Host "[UI-LOOP] Starting loop until $endTime"

$devServer = Start-Process -FilePath 'powershell' -ArgumentList '-NoLogo','-NoProfile','-Command',"Set-Location '$frontendRoot'; npm run dev -- --host 127.0.0.1 --port 3001" -PassThru
Start-Sleep -Seconds 12

try {
  do {
    $cycle += 1
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $cycleLog = Join-Path $logDir "cycle-$cycle-$timestamp.log"

    "`n===== Cycle $cycle ($timestamp) =====" | Tee-Object -FilePath $cycleLog -Append

    $commands = @(
      'npm run lint'
      'npx playwright test tests/health.spec.ts --project=chromium'
      'npx playwright test tests/qa_audit_refined.spec.ts --project=chromium'
    )

    if (-not $SkipBuild.IsPresent) {
      $commands = @('npm run build') + $commands
    }

    foreach ($cmd in $commands) {
      "[RUN] $cmd" | Tee-Object -FilePath $cycleLog -Append
      cmd /c $cmd *>&1 | Tee-Object -FilePath $cycleLog -Append
      if ($LASTEXITCODE -ne 0) {
        "[FAIL] command failed with exit code $LASTEXITCODE" | Tee-Object -FilePath $cycleLog -Append
        throw "Loop stopped at cycle $cycle because '$cmd' failed."
      }
      "[PASS] $cmd" | Tee-Object -FilePath $cycleLog -Append
    }

    "[CYCLE PASS] $cycle" | Tee-Object -FilePath $cycleLog -Append

    if ((Get-Date) -lt $endTime) {
      Start-Sleep -Seconds $PauseSeconds
    }
  } while ((Get-Date) -lt $endTime)

  Write-Host "[UI-LOOP] Completed successfully."
}
finally {
  if ($devServer -and !$devServer.HasExited) {
    Stop-Process -Id $devServer.Id -Force
  }
}
