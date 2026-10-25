Set-Location E:\vertex-math-vision
$env:PYTHONIOENCODING = "utf-8"
& venv\Scripts\python.exe -u scripts\train_v1.py --max-samples 6000 --resume --save-steps 100 *> logs\train_v1.log
"[$(Get-Date -Format s)] entrenamiento terminado (codigo $LASTEXITCODE)" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
