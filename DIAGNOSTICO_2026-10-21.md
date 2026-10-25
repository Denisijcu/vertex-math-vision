# Diagnóstico inicial — vertex-math-vision (21-oct-2026, madrugada)

Revisión rápida, sin tocar nada del proyecto. Para hablarlo mañana.

## Lo que hay
- Base real que se entrena: `unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit` (`scripts/train_vision.py`, `BASE_MODEL`).
- Entrenamiento: **smoke test** de 500 pasos sobre las **100 primeras** muestras del split `test` de MathLLMs/MathVision; lote efectivo 4, lr 2e-4. Son **20 épocas** sobre 100 ejemplos: la pérdida pasa de 4,30 a 0,037 → memorizado.
- `data/processed/verified_manifest.jsonl` tiene **3.040** muestras preparadas que el entrenamiento todavía **no usa**.
- Exportado a GGUF (Q4_K_M + mmproj f16) y fusionado en `models/merged`.

## Evaluación actual (`outputs_eval/vertex_math_vision_comparison.csv`)
- 12 problemas, índices ≥100 (bien: no se solapan con los 100 de entrenamiento).
- **Base 0/12, LoRA 1/12.** Muestra demasiado pequeña para concluir nada.
- El LoRA aprendió a contestar solo `Final Answer: $$\boxed{…}$$`, sin razonamiento; la base sí razona paso a paso.

## Problemas a resolver
1. **Licencia:** el README dice Apache 2.0 y "Qwen2.5-VL-7B", pero se entrenó el **3B**, que es **Qwen Research (no comercial)**. El 7B sí es Apache 2.0.
2. **MathVision es un benchmark** (solo trae `test` y `testmini`). Entrenar con él invalida cualquier cifra que se mida después en MathVision. Hace falta un dataset de entrenamiento distinto (o separar un trozo fijo de MathVision solo para evaluar y no tocarlo nunca).
3. **Sobreajuste:** 20 épocas sobre 100 ejemplos.
4. **Formato de salida:** si se entrena solo con la respuesta final, el modelo deja de razonar. Para problemas de matemáticas conviene entrenar con soluciones razonadas.
5. **Evaluación:** 12 problemas no bastan; mínimo unos cientos, con el mismo extractor de respuesta para base y LoRA.

## Propuesta para mañana
Decidir base (3B no comercial vs 7B Apache 2.0, que no cabe para entrenar en 6 GB), dataset de entrenamiento y un conjunto de evaluación fijo; luego entrenar de verdad con el manifiesto completo.
