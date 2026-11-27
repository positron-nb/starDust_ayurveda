# Start the full PRAMAAN demo (live AyurParam) on the team laptop and publish its tunnel link.
#
#   powershell -ExecutionPolicy Bypass -File scripts\start_live_demo.ps1          # start
#   powershell -ExecutionPolicy Bypass -File scripts\start_live_demo.ps1 -Stop    # stop everything
#
# Starts the AyurParam model server (:8601, localhost only), the read-only public-demo API (:8600) and a
# Cloudflare quick tunnel to :8600. It writes the tunnel URL to deploy/live_link.json and pushes it, so
# the always-on Vercel demo shows a "Live AyurParam demo is up now" button while this machine runs.
param([switch]$Stop)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$Logs = Join-Path $Root "data\runtime\live_demo"
New-Item -ItemType Directory -Force $Logs | Out-Null
$PidFile = Join-Path $Logs "pids.json"

function Stop-Demo {
    if (Test-Path $PidFile) {
        foreach ($id in (Get-Content $PidFile | ConvertFrom-Json)) {
            try { Stop-Process -Id $id -Force -ErrorAction Stop; "stopped pid $id" } catch {}
        }
        Remove-Item $PidFile
    }
}

if ($Stop) { Stop-Demo; exit 0 }
Stop-Demo

Push-Location $Root
try {
    $model = Start-Process $Py -ArgumentList "-X utf8 -W ignore model_server/server.py" -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\model.out.log" -RedirectStandardError "$Logs\model.err.log"
    $api = Start-Process $Py -ArgumentList "-X utf8 -W ignore scripts/run_public_demo.py" -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\api.out.log" -RedirectStandardError "$Logs\api.err.log"
    $tun = Start-Process $Cf -ArgumentList "tunnel --no-autoupdate --url http://127.0.0.1:8600" -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\tunnel.out.log" -RedirectStandardError "$Logs\tunnel.err.log"
    @($model.Id, $api.Id, $tun.Id) | ConvertTo-Json | Set-Content $PidFile

    "Waiting for AyurParam to load (about 30 s)..."
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        Start-Sleep 5
        try { $ready = (Invoke-RestMethod http://127.0.0.1:8601/health -TimeoutSec 3).loaded } catch {}
    }
    if (-not $ready) { throw "AyurParam did not load; see $Logs\model.err.log" }

    $url = $null
    for ($i = 0; $i -lt 30 -and -not $url; $i++) {
        Start-Sleep 2
        $m = Select-String -Path "$Logs\tunnel.err.log", "$Logs\tunnel.out.log" -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
    if (-not $url) { throw "No tunnel URL; see $Logs\tunnel.err.log" }

    $json = @{ url = $url; updated = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText((Join-Path $Root "deploy\live_link.json"), $json + "`n")
    git add deploy/live_link.json
    git commit -m "Live demo link: $url" | Out-Null
    git push origin pramaan-prototype

    ""
    "Live AyurParam demo: $url"
    "Always-on demo (shows a button to it): https://stardustayurveda-kappa.vercel.app/"
    "Stop with: powershell -ExecutionPolicy Bypass -File scripts\start_live_demo.ps1 -Stop"
}
finally { Pop-Location }
