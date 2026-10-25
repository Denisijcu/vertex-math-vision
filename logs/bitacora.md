# Bitácora — Vertex-Math-Vision

## 2026-10-21 — Replanteamiento (v0 → v1)

**Diagnóstico de la v0 (smoke test):** ver `DIAGNOSTICO_2026-10-21.md`.
- Se entrenó Qwen2.5-VL-3B (licencia Qwen Research, no comercial) con las 100 primeras muestras del split `test` de MathVision durante 20 épocas: memorizó (pérdida 4,30 → 0,037).
- MathVision es un examen, no un dataset de entrenamiento.
- El LoRA dejó de razonar y sacó 1/12 contra 0/12 de la base.

**Objetivo del proyecto:** un tutor de matemáticas para estudiantes de primaria y secundaria, en español e inglés, que al final sea un agente de estudio.

**Decisiones de Denis:**
- Base: **Qwen3-VL-2B-Instruct** (Apache 2.0, se puede vender). Entrena en la GTX 1660 Ti (6 GB, fp16) y sirve de candidato para la versión Android.
- Datos: **generador propio + GSM8K**. MathVision queda solo para medir.

**Lo construido (`scripts/`):**
- `gen_synth.py`: 16 familias de problemas con imagen, bilingües, con la solución paso a paso y la respuesta exacta. Genera 12.000 de entrenamiento y 600 de examen. Ninguna clave de problema del examen aparece en el entrenamiento.
  - Primaria: contar, relojes, fracciones, barras, precios, recta numérica, operaciones en columna, sucesiones.
  - Secundaria: ángulos, Pitágoras, círculos, ecuaciones, pendiente, pastel, cajas.
  - El 35 % lleva el enunciado dentro de la imagen y el 40 % lleva efecto de foto de celular.
- `prepare_text_problems.py`: 3.000 problemas de GSM8K (train, inglés) convertidos en foto de tarea para entrenar, y el examen fijo de 635 problemas:
  - 300 sintéticos;
  - 100 de MGSM en español y los mismos 100 en inglés;
  - 135 de MathVision testmini, niveles 1–2.
- `answers.py`: un solo extractor y comparador de respuestas (fracciones, π, horas, decimales con coma, letras de opción) para la base y para el LoRA.
- `eval_fixed.py`: examen con generación greedy y 512 tokens. Se puede retomar. Mide exactitud, si responde con `\boxed{}` y si contesta en el idioma del estudiante.
- `train_v1.py`: QLoRA r=16, lr 1e-4, lote efectivo 8, una época, 80 % sintético + 20 % GSM8K. Las imágenes se cargan del disco y guarda un checkpoint cada 200 pasos.

**Problemas encontrados y arreglados:**
- La primera generación dejó pocas muestras de círculos (21) y de Pitágoras (44): el generador no repetía claves y esas familias tienen pocas combinaciones. Se agrandaron los rangos y se permitió repetir problemas dentro del entrenamiento (nunca los del examen). Ahora cada familia tiene entre 519 y 954 muestras.
- En la prueba corta (40 problemas, 40 % de acierto), la base contestaba en español a preguntas en inglés: el prompt de sistema empezaba en español. Se reescribió con una regla explícita de idioma.
- La base se enreda repitiendo frases hasta llenar los 512 tokens, y esas respuestas cuentan como fallo.

**Examen de la base (Qwen3-VL-2B sin afinar), 635 problemas, terminado a las 15:27:**

| Grupo | Aciertos | % | Con \boxed | Idioma correcto |
|---|---|---|---|---|
| TOTAL | 347/635 | 54,6 | 75,7 | 100 |
| Sintético | 217/300 | 72,3 | 93,0 | 100 |
| MGSM inglés | 65/100 | 65,0 | 88,0 | 100 |
| MGSM español | 53/100 | 53,0 | 80,0 | 100 |
| MathVision niveles 1–2 | 12/135 | 8,9 | 25,2 | 100 |

- Familias débiles: contar figuras (11 %), recta numérica (25 %), relojes (30 %), Pitágoras (33 %) y fracciones (59 %). Las fuertes rondan el 90–100 %: círculos, pastel, precios, sucesiones, cajas y ecuaciones.
- El mismo problema sale 12 puntos peor en español que en inglés (MGSM 53 contra 65).
- En MathVision, 3 de cada 4 respuestas no cierran con \boxed: se enreda repitiendo hasta llenar los 512 tokens.
- Tras el arreglo del prompt de sistema, la base contesta siempre en el idioma del estudiante (100 %).

**Entrenamiento v1:**
- Prueba de humo (30 pasos, 200 muestras): OK. Unos 60 s por paso (lote efectivo 8) en la 1660 Ti, con 3,3 GB de VRAM. La pérdida bajó a 0,76.
- A ese ritmo, la época completa de 15.000 muestras (1.875 pasos) tomaría unas 31 h. Se canceló a los 2 minutos y se relanzó con `--max-samples 6000`: 750 pasos, unas 12,5 h, la misma mezcla 80/20 de sintético y GSM8K. Arrancó a las 16:01 del 21-oct.


**21-oct, 20:00 — Extractor y recalificación:**
- `answers.py` ahora reconoce una opción escrita con su texto, por ejemplo `(C) 32%`, cuando la respuesta correcta es la letra C.
- Nuevo `scripts/rescore.py`: recalifica un examen ya corrido sin volver a generar, y compara base contra LoRA con la misma vara.
- La base queda en **348/635 = 54,8 %** (MathVision pasa de 12 a 13).
- Entrenamiento v1: va en el paso 232 de 750 (59 s por paso). `checkpoint-200` guardado. La pérdida bajó de 2,39 a cerca de 0,06: los datos sintéticos tienen formato fijo y se aprenden rápido, así que el examen dirá si aprendió a resolver o solo el formato.

**22-oct, 02:00 — Caída del entrenamiento y reanudación:**
- El proceso murió en el paso 595 de 750. A las 02:00:33 el Visor de eventos registra un reinicio del driver de NVIDIA (`nvlddmkm`, evento 153), al mismo tiempo que se actualizaba la app de Claude (instalación de servicio). El último checkpoint era el de 400: se perdieron 195 pasos, unas 3 h.
- A las 04:52 se retomó desde `checkpoint-400` con `--resume`. Ahora guarda un checkpoint cada 100 pasos (`--save-steps 100`).
- `scripts/run_eval_after_train.ps1` espera a que termine el entrenamiento y corre solo el examen del LoRA y la comparación con la base, que queda en `logs/comparacion_base_vs_lora_v1.txt`.

## 2026-10-22 — Resultado del LoRA v1: no se publica

Entrenamiento terminado a las 10:38 (750 pasos, pérdida final 0,031). Examen terminado a las 13:25. El LoRA tarda unos 12 s por problema; la base, unos 25.

| Grupo | Base | LoRA v1 | Diferencia |
|---|---|---|---|
| TOTAL | 348/635 (54,8 %) | 371/635 (58,4 %) | +3,6 |
| Sintético | 72,3 % | 85,3 % | +13,0 |
| MathVision niveles 1–2 | 9,6 % | 20,0 % | +10,4 |
| MGSM inglés | 65,0 % | 50,0 % | **−15,0** |
| MGSM español | 53,0 % | 38,0 % | **−15,0** |

**Lo que mejoró:**
- Relojes (+55), recta numérica (+38), contar (+33), Pitágoras (+29) y fracciones (+24).
- En MathVision ya no se enreda: el uso de `\boxed` sube del 25 % al 42 %. Ganó 16 problemas y perdió 3.

**Lo que empeoró:**
- Problemas de enunciado (MGSM): en inglés ganó 11 y perdió 26; en español ganó 8 y perdió 23.
- Cajas (−31) y operaciones en columna (−12,5).

**Diagnóstico:** el LoRA contesta con prisa. En MGSM sus respuestas miden la mitad que las de la base (305 contra 680–850 caracteres). Se salta el paso de entender el problema y comete errores de lectura. Ejemplo: en el problema de Janet escribe "16 − 3 = 13 huevos en el desayuno". También falla cuentas al comprimir los pasos (2 × 116 = 224). Lo aprendió de los datos: las plantillas del generador y las soluciones de GSM8K son muy escuetas.

**Veredicto:** no se publica. Aplicando la regla de Denis, el total sube, pero pierde 15 puntos en los dos idiomas de MGSM.

## 2026-10-22 — v2: soluciones que enseñan a entender el problema

Denis eligió el camino 1 ("métele con todo y lo mejor").

**Datos v2 (`gen_synth.py --v2`, carpeta `data/synth_v2`):**
- Cada solución ahora tiene cinco partes:
  - **Lo que me piden:** se reescribe la pregunta. Así el modelo aprende a leer el enunciado aunque venga dentro de la imagen.
  - **Lo que veo / Lo que sé:** los datos del dibujo o del enunciado.
  - **Pasos con las cuentas intermedias explícitas.** Ejemplos: 35 + 50 = 85; 85 + 70 = 155; 2 × 155 = 310. Las multiplicaciones se descomponen por cifras. Las horas se suman separando horas y minutos.
  - **Comprobación real**, calculada con los mismos datos: operación inversa, otra forma de resolverlo o sustituir en la ecuación.
  - **Respuesta** en `\boxed{}`.
- Familia nueva **word**: problemas de enunciado de varios pasos en español e inglés (descuento, ahorro, reparto con resto, viaje, duración de una película, receta proporcional, cajas, edades, porcentaje de la clase), escritos como hoja de tareas. Son 2.053 de las 12.000 muestras. Esto cubre el hueco en español: GSM8K solo existe en inglés.
- El examen no cambia: el train v2 se genera con `--forbid data/synth/eval.jsonl` y ninguna clave del examen aparece en él. Se comprobó que el código nuevo reproduce el examen idéntico.
- Autoconsistencia: 600/600 en la prueba local.

**GSM8K v2 (`gsm8k_v2.py`):** las mismas 3.000 imágenes, con la respuesta reescrita en tres partes: lo que piden (la última oración), lo que sé (el resto del enunciado) y los pasos. No se agregó comprobación: GSM8K no trae una, y una frase de relleno enseñaría a "comprobar" sin comprobar nada.

**Entrenamiento v2 (`train_v1.py --version v2`):** igual que la v1 (6.000 muestras, 750 pasos, 80 % sintético y 20 % GSM8K), pero con **la tasa de aprendizaje a la mitad (5e-5)** para no borrar el razonamiento de la base. Guarda un checkpoint cada 100 pasos y se retoma solo hasta 3 veces si se corta. Salida en `outputs_v2` y `models/lora_adapters/vertex-math-vision-v2`.

**Tubería automática (`scripts/run_v2.ps1`):** datos → prueba de humo (10 pasos) → entrenamiento → examen del LoRA v2 → comparaciones `logs/comparacion_base_vs_lora_v2.txt` y `logs/comparacion_v1_vs_v2.txt`. Arrancó el 22-oct a las 14:25.
