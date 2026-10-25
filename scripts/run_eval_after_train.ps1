Set-Location E:\vertex-math-vision
$env:PYTHONIOENCODING = "utf-8"
while (Get-Process -Id 27512 -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 60 }
if (-not (Test-Path models\lora_adapters\vertex-math-vision-v1\adapter_config.json)) { "[$(Get-Date -Format s)] no hay adaptador v1; no se corre el examen" | Out-File logs\train_v1_runner.log -Append -Encoding utf8; exit 1 }
"[$(Get-Date -Format s)] examen del LoRA v1" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
& venv\Scripts\python.exe -u scripts\eval_fixed.py --tag lora-v1 --lora models\lora_adapters\vertex-math-vision-v1 *> logs\eval_lora_v1.log
& venv\Scripts\python.exe -u scripts\rescore.py base lora-v1 *> logs\comparacion_base_vs_lora_v1.txt
"[$(Get-Date -Format s)] examen del LoRA v1 terminado; ver logs\comparacion_base_vs_lora_v1.txt" | Out-File logs\train_v1_runner.log -Append -Encoding utf8
