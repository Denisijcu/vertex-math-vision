# Espera a que termine el examen de la base (PID 16984) y lanza el entrenamiento v1.
Set-Location E:\vertex-math-vision
$env:PYTHONIOENCODING = "utf-8"
while (Get-Process -Id 16984 -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 60 }
"[$(Get-Date -Format s)] examen base terminado; prueba de humo" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
& venv\Scripts\python.exe -u scripts\train_v1.py --max-samples 200 --max-steps 30 *> logs\train_v1_smoke.log
if ($LASTEXITCODE -ne 0) { "[$(Get-Date -Format s)] la prueba de humo FALLO (codigo $LASTEXITCODE); no se lanza el entrenamiento" | Out-File logs\train_v1_runner.log -Append -Encoding utf8; exit 1 }
"[$(Get-Date -Format s)] prueba de humo OK; entrenamiento completo" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
& venv\Scripts\python.exe -u scripts\train_v1.py *> logs\train_v1.log
"[$(Get-Date -Format s)] entrenamiento terminado (codigo $LASTEXITCODE)" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
