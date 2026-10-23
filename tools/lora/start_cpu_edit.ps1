[CmdletBinding()]
param(
    [string]$ExternalRoot = 'D:\Super Castlevania IV Recomp\tools-external\castlevania-hd',
    [Parameter(Mandatory=$true)][string]$Work
)
$ErrorActionPreference = 'Stop'
$Work = [IO.Path]::GetFullPath($Work)
$ComfyRoot = Join-Path $ExternalRoot 'ComfyUI'
$Python = Join-Path $ExternalRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Use the existing ComfyUI environment.' }
$GpuQueue = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue' -TimeoutSec 5
if ($GpuQueue.queue_running.Count -or $GpuQueue.queue_pending.Count) { throw 'Shared RAM is in use. Leave the GPU job running.' }
$Listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,8189)
try { $Listener.Start() } finally { $Listener.Stop() }
New-Item -ItemType Directory -Path $Work -Force | Out-Null
foreach ($CpuFolder in @('input','output','temp','user')) {
    New-Item -ItemType Directory -Path (Join-Path $Work $CpuFolder) -Force | Out-Null
}
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:DO_NOT_TRACK = '1'
$env:OMP_NUM_THREADS = '24'
$env:MKL_NUM_THREADS = '24'
$CpuArguments = @('-s','-u',(Join-Path $ComfyRoot 'main.py'),
    '--cpu','--bf16-unet','--bf16-text-enc','--fp32-vae','--cpu-vae',
    '--listen','127.0.0.1','--port','8189','--offline','--cache-none',
    '--preview-method','none','--disable-auto-launch','--disable-all-custom-nodes',
    '--input-directory',(Join-Path $Work 'input'),
    '--output-directory',(Join-Path $Work 'output'),
    '--temp-directory',(Join-Path $Work 'temp'),
    '--user-directory',(Join-Path $Work 'user'))
$CpuQuoted = $CpuArguments | ForEach-Object { if ($_ -match '[\s"]') { '"' + $_.Replace('"','\"') + '"' } else { $_ } }
$CpuProcess = Start-Process -FilePath $Python -ArgumentList $CpuQuoted -WorkingDirectory $ComfyRoot `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Work 'stdout.log') `
    -RedirectStandardError (Join-Path $Work 'stderr.log')
@{ launcher_pid=$CpuProcess.Id; port=8189; cpu_only=$true; threads=24;
    executable=$Python; arguments=$CpuArguments } | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $Work 'cpu-server.json') -Encoding utf8
Write-Host "Separate CPU-only edit server starting (PID $($CpuProcess.Id), port 8189)."
