# Tubería v2 de Vertex-Math-Vision: datos -> prueba de humo -> entrenamiento -> examen -> comparación.
Set-Location E:\vertex-math-vision
$env:PYTHONIOENCODING = "utf-8"
$log = "logs\v2_runner.log"
function Note($m) { "[$(Get-Date -Format s)] $m" | Out-File $log -Append -Encoding utf8 }
if ((Test-Path data\synth_v2\train.jsonl) -and (Test-Path data\gsm8k\train_v2.jsonl)) { Note "datos v2 ya generados; se reutilizan" } else {
Note "datos v2"
& venv\Scripts\python.exe -u scripts\gen_synth.py --v2 --train 12000 --forbid data\synth\eval.jsonl --out data\synth_v2 *> logs\v2_datos.log
if ($LASTEXITCODE -ne 0) { Note "FALLO generando datos v2"; exit 1 }
& venv\Scripts\python.exe -u scripts\gsm8k_v2.py *>> logs\v2_datos.log
if ($LASTEXITCODE -ne 0) { Note "FALLO en gsm8k_v2"; exit 1 }
}
# prueba de humo: ya hecha el 22-oct (2 pasos OK, ~80 s/paso, sin falta de memoria)
Note "entrenamiento v2 (6000 muestras, 750 pasos, lr 5e-5)"
$resume = @(); if (Test-Path outputs_v2\checkpoint-*) { $resume = @("--resume") }
& venv\Scripts\python.exe -u scripts\train_v1.py --version v2 --max-samples 6000 --save-steps 100 @resume *>> logs\v2_train.log
for ($i = 0; $i -lt 3 -and -not (Test-Path models\lora_adapters\vertex-math-vision-v2\adapter_config.json); $i++) {
  Note "el entrenamiento se cortó (codigo $LASTEXITCODE); retomo desde el último checkpoint"
  Start-Sleep -Seconds 30
  & venv\Scripts\python.exe -u scripts\train_v1.py --version v2 --max-samples 6000 --save-steps 100 --resume *>> logs\v2_train.log
}
if (-not (Test-Path models\lora_adapters\vertex-math-vision-v2\adapter_config.json)) { Note "FALLO el entrenamiento v2"; exit 1 }
Note "examen del LoRA v2"
& venv\Scripts\python.exe -u scripts\eval_fixed.py --tag lora-v2 --lora models\lora_adapters\vertex-math-vision-v2 *> logs\v2_eval.log
& venv\Scripts\python.exe -u scripts\rescore.py base lora-v2 *> logs\comparacion_base_vs_lora_v2.txt
& venv\Scripts\python.exe -u scripts\rescore.py lora-v1 lora-v2 *> logs\comparacion_v1_vs_v2.txt
Note "v2 terminado; ver logs\comparacion_base_vs_lora_v2.txt y logs\comparacion_v1_vs_v2.txt"

