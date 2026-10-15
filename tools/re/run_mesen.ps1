# Run a Mesen 2 test-runner Lua script headless against the ROM, in the isolated
# portable Mesen copy used by D:\Reverse Engineering\tools\mesen_scripts.
#   powershell -File tools/re/run_mesen.ps1 -Script tools/re/mesen_column_trace.lua -Out build-audit/mesen
# The script gets CONFIG = { out = "<Out>" } prepended and should call emu.stop() when done.
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [string]$Out = "build-audit/mesen",
    [string]$Rom = "$PSScriptRoot\..\..\Super Castlevania IV (USA).sfc",
    [int]$TimeoutSeconds = 600
)
$ErrorActionPreference = 'Stop'
$out = [IO.Path]::GetFullPath($Out)
New-Item -ItemType Directory -Force $out | Out-Null
$portable = Join-Path $env:TEMP 'sc4-mesen-portable'
New-Item -ItemType Directory -Force $portable | Out-Null
$exe = Join-Path $portable 'Mesen.exe'
$src = 'D:\Reverse Engineering\tools\Mesen\Mesen.exe'
if (-not (Test-Path $exe) -or (Get-Item $exe).Length -ne (Get-Item $src).Length) { Copy-Item $src $exe -Force }
Set-Content -Path (Join-Path $portable 'settings.json') -Encoding ascii `
    -Value '{"Debug":{"ScriptWindow":{"AllowIoOsAccess":true}},"Snes":{"Port1":{"Type":"SnesController"}}}'
$run = Join-Path $out 'run.lua'
[IO.File]::WriteAllText($run, "CONFIG = { out = `"$($out -replace '\', '/')`" }`n" + [IO.File]::ReadAllText((Resolve-Path $Script)))
$p = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden -ArgumentList @(
    '--testRunner', "`"$run`"", "`"$((Resolve-Path $Rom).Path)`"", '--doNotSaveSettings')
$null = $p.Handle
if (-not $p.WaitForExit($TimeoutSeconds * 1000)) { $p.Kill(); throw "Mesen timed out after $TimeoutSeconds s" }
Write-Host "exit=$($p.ExitCode); output in $out"
