"""Entrenamiento v1 de Vertex-Math-Vision sobre Qwen3-VL-2B-Instruct (Apache 2.0).

Datos: generador sintético bilingüe (data/synth/train.jsonl) + GSM8K renderizado (data/gsm8k/train.jsonl).
MathVision NO se usa para entrenar: es parte del examen.

Pensado para una GTX 1660 Ti (6 GB, sin bf16 -> fp16). Las imágenes se cargan del disco
en cada lote, así la RAM no se llena. Guarda un checkpoint cada SAVE_STEPS pasos y se puede retomar.

Uso (desde E:\\vertex-math-vision):
    venv\\Scripts\\python.exe scripts\\train_v1.py --max-samples 200 --max-steps 30   (prueba de humo)
    venv\\Scripts\\python.exe scripts\\train_v1.py                                     (entrenamiento completo)
    venv\\Scripts\\python.exe scripts\\train_v1.py --resume                            (retomar el último checkpoint)
"""
from unsloth import FastVisionModel, is_bf16_supported  # Unsloth primero
from unsloth.trainer import UnslothVisionDataCollator

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

import torch
from dotenv import load_dotenv
from PIL import Image
from trl import SFTConfig, SFTTrainer

sys.path.insert(0, str(Path(__file__).parent))
from gen_synth import SYSTEM_PROMPT  # noqa: E402

load_dotenv()
BASE_MODEL = os.getenv("BASE_MODEL", "unsloth/Qwen3-VL-2B-Instruct-unsloth-bnb-4bit")
MAX_DIM = int(os.getenv("MAX_VIEW_DIM", 640))
LORA_RANK = int(os.getenv("LORA_RANK", 16))
LORA_ALPHA = int(os.getenv("LORA_ALPHA", 16))
FINETUNE_VISION = os.getenv("FINETUNE_VISION", "0") == "1"
# Cada versión: datos, tasa de aprendizaje y carpetas propias. La v1 queda exactamente como se entrenó.
VERSIONS = {
    "v1": dict(synth="data/synth/train.jsonl", gsm8k="data/gsm8k/train.jsonl", lr=1e-4),
    # v2: soluciones con "qué piden / qué veo / pasos / comprobación", problemas de enunciado bilingües
    # y tasa de aprendizaje a la mitad para no borrar el razonamiento de la base (la v1 perdió 15 puntos en MGSM).
    "v2": dict(synth="data/synth_v2/train.jsonl", gsm8k="data/gsm8k/train_v2.jsonl", lr=5e-5),
}


def load_rows(max_samples, gsm8k_share, cfg):
    synth = [dict(json.loads(l), root=str(Path(cfg["synth"]).parent)) for l in open(cfg["synth"], encoding="utf-8")]
    gsm = [dict(json.loads(l), root=str(Path(cfg["gsm8k"]).parent)) for l in open(cfg["gsm8k"], encoding="utf-8")]
    r = random.Random(3407)
    n_gsm = min(len(gsm), int(len(synth) * gsm8k_share / (1 - gsm8k_share)))
    rows = synth + r.sample(gsm, n_gsm)
    r.shuffle(rows)
    if max_samples:
        rows = rows[:max_samples]
    return rows


class LazyImageCollator:
    """Abre la imagen de cada fila al armar el lote y se lo pasa al colador de Unsloth."""

    def __init__(self, model, tokenizer):
        self.inner = UnslothVisionDataCollator(model, tokenizer)

    def __call__(self, rows):
        convs = []
        for row in rows:
            img = Image.open(Path(row["root"]) / row["image"]).convert("RGB")
            img.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
            convs.append({"messages": [
                {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": row["prompt"]}]},
                {"role": "assistant", "content": [{"type": "text", "text": row["response"]}]},
            ]})
        return self.inner(convs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1", choices=sorted(VERSIONS))
    ap.add_argument("--max-samples", type=int, default=0, help="0 = todas")
    ap.add_argument("--max-steps", type=int, default=-1, help="-1 = una época completa")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--gsm8k-share", type=float, default=0.2, help="fracción del total que viene de GSM8K")
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    cfg = VERSIONS[args.version]
    OUT_DIR = f"outputs_{args.version}"
    ADAPTER_DIR = f"models/lora_adapters/vertex-math-vision-{args.version}"
    print(f"[+] Versión {args.version}: {cfg}")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no está disponible.")
    p = torch.cuda.get_device_properties(0)
    print(f"[+] GPU: {p.name} ({p.total_memory / 1024 ** 3:.1f} GB) | bf16={is_bf16_supported()}")

    rows = load_rows(args.max_samples, args.gsm8k_share, cfg)
    print(f"[+] {len(rows)} muestras | fuentes {dict(Counter(r['source'] for r in rows))} | idiomas {dict(Counter(r['lang'] for r in rows))}")

    model, tokenizer = FastVisionModel.from_pretrained(BASE_MODEL, load_in_4bit=True, use_gradient_checkpointing="unsloth")
    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers=FINETUNE_VISION,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.0,
        bias="none",
        random_state=3407,
    )
    FastVisionModel.for_training(model)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=LazyImageCollator(model, tokenizer),
        train_dataset=rows,
        args=SFTConfig(
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            warmup_ratio=0.03,
            learning_rate=cfg["lr"],
            lr_scheduler_type="cosine",
            weight_decay=0.01,
            optim="adamw_8bit",
            fp16=not is_bf16_supported(),
            bf16=is_bf16_supported(),
            logging_steps=10,
            save_strategy="steps",
            save_steps=args.save_steps,
            save_total_limit=3,
            output_dir=OUT_DIR,
            report_to="none",
            seed=3407,
            remove_unused_columns=False,
            dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            dataset_num_proc=1,
            dataloader_num_workers=0,
            max_length=2048,
        ),
    )
    resume = args.resume and any(Path(OUT_DIR).glob("checkpoint-*"))
    stats = trainer.train(resume_from_checkpoint=True if resume else None)
    print(f"[+] Entrenamiento terminado en {stats.metrics['train_runtime'] / 3600:.2f} h | pérdida final {stats.metrics.get('train_loss'):.4f}")
    # una prueba de humo (--max-steps) nunca pisa el adaptador de verdad
    out_dir = ADAPTER_DIR + ("-smoke" if args.max_steps > 0 else "")
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"[+] Adaptador guardado en {out_dir}")


if __name__ == "__main__":
    main()
