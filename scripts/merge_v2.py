"""Fusiona el adaptador LoRA v2 con Qwen3-VL-2B-Instruct en precisión completa (no la base de 4 bits),
para convertirlo después a GGUF y usarlo en LM Studio.

- La base completa (unos 4.3 GB) se descarga a E:\\vertex-math-vision\\.cache, porque en C: no hay espacio.
- Todo corre en CPU: no hace falta la GPU y no toca el adaptador original.
- Guarda en models/merged/vertex-math-vision-v2 (bf16) con el tokenizer y el procesador.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\merge_v2.py
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))  # antes de importar transformers

import torch  # noqa: E402
from peft import PeftModel  # noqa: E402
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration  # noqa: E402

BASE = "Qwen/Qwen3-VL-2B-Instruct"
LORA_DIR = ROOT / "models" / "lora_adapters" / "vertex-math-vision-v2"
OUTPUT_DIR = ROOT / "models" / "merged" / "vertex-math-vision-v2"


def main():
    if not (LORA_DIR / "adapter_model.safetensors").exists():
        raise FileNotFoundError(f"No se encuentra el adaptador: {LORA_DIR}")
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise FileExistsError(f"El destino ya tiene archivos: {OUTPUT_DIR}. No se sobrescribe.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[i] Caché de Hugging Face: {os.environ['HF_HOME']}")

    print(f"[1/4] Cargando {BASE} en CPU (float32 para fusionar sin perder precisión)...")
    model = Qwen3VLForConditionalGeneration.from_pretrained(BASE, torch_dtype=torch.float32, low_cpu_mem_usage=True)

    print("[2/4] Aplicando el adaptador v2...")
    model = PeftModel.from_pretrained(model, str(LORA_DIR), is_trainable=False)

    print("[3/4] Fusionando los pesos...")
    model = model.merge_and_unload(safe_merge=True).eval()

    print("[4/4] Guardando en bf16 con el tokenizer y el procesador...")
    model.to(torch.bfloat16).save_pretrained(str(OUTPUT_DIR), safe_serialization=True, max_shard_size="4GB")
    # El procesador y la plantilla de chat salen del adaptador: son los mismos con los que se entrenó.
    AutoProcessor.from_pretrained(str(LORA_DIR)).save_pretrained(str(OUTPUT_DIR))

    print(f"\n[+] Fusión completada: {OUTPUT_DIR}")
    print("    El adaptador original no se ha modificado.")


if __name__ == "__main__":
    main()
