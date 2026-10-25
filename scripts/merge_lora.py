
from pathlib import Path
import torch

from transformers import (
    AutoProcessor,
    Qwen2_5_VLForConditionalGeneration,
)
from peft import PeftModel

BASE_DIR = Path("models/base/Qwen2.5-VL-3B-Instruct")
LORA_DIR = Path("models/lora_adapters/vertex-math-vision-smoke")
OUTPUT_DIR = Path("models/merged/vertex-math-vision")


def main():
    if not (BASE_DIR / "model.safetensors.index.json").exists():
        raise FileNotFoundError(f"No se encuentra el índice del modelo: {BASE_DIR}")

    if not (BASE_DIR / "model-00001-of-00002.safetensors").exists():
        raise FileNotFoundError("Falta el primer archivo de pesos del modelo base.")

    if not (BASE_DIR / "model-00002-of-00002.safetensors").exists():
        raise FileNotFoundError("Falta el segundo archivo de pesos del modelo base.")

    if not (LORA_DIR / "adapter_model.safetensors").exists():
        raise FileNotFoundError(f"No se encuentra el adaptador LoRA: {LORA_DIR}")

    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise FileExistsError(
            f"El destino ya contiene archivos: {OUTPUT_DIR}. "
            "No se sobrescribirá."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/4] Cargando Qwen2.5-VL-3B original en CPU...")

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(BASE_DIR),
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        attn_implementation="eager",
    )

    print("[2/4] Aplicando el adaptador Vertex LoRA...")

    model = PeftModel.from_pretrained(
        model,
        str(LORA_DIR),
        is_trainable=False,
    )

    print("[3/4] Fusionando los pesos...")

    model = model.merge_and_unload(safe_merge=True)
    model.eval()

    print("[4/4] Guardando modelo fusionado y procesador...")

    model.save_pretrained(
        str(OUTPUT_DIR),
        safe_serialization=True,
        max_shard_size="4GB",
    )

    processor = AutoProcessor.from_pretrained(str(BASE_DIR))
    processor.save_pretrained(str(OUTPUT_DIR))

    print(f"\nFusión completada: {OUTPUT_DIR.resolve()}")
    print("El adaptador original no se ha modificado.")


if __name__ == "__main__":
    main()
