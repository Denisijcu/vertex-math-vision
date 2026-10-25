import os
import warnings
import torch
from PIL import Image, ImageFile
from datasets import load_dataset
from dotenv import load_dotenv
from unsloth import FastVisionModel, is_bf16_supported
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

load_dotenv()

# Hardening contra DecompressionBomb
Image.MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", 25000000))
ImageFile.LOAD_TRUNCATED_IMAGES = False
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

MODEL_NAME = os.getenv("BASE_MODEL", "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit")
LORA_RANK = int(os.getenv("LORA_RANK", 16))
LORA_ALPHA = int(os.getenv("LORA_ALPHA", 16))
MAX_DIM = int(os.getenv("MAX_VIEW_DIM", 512))
MAX_PIXELS = MAX_DIM * MAX_DIM  # 512x512 para proteger los 6GB de VRAM
MAX_STEPS = int(os.getenv("MAX_STEPS", 500))  # Smoke-test rápido

SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, an elite multimodal mathematical reasoning engine "
    "developed by Vertex Coders LLC. Analyze the diagram, provide step-by-step "
    "mathematical reasoning, and place the final answer inside \\boxed{}."
)

def verify_gpu():
    if not torch.cuda.is_available():
        raise RuntimeError("CRITICAL: CUDA is not available. Check PyTorch installation.")
    device_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"[+] Hardware Verified: {device_name} ({vram_gb:.2f} GB VRAM)")

def sanitize_image(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if w * h > MAX_PIXELS:
        scale = (MAX_PIXELS / (w * h)) ** 0.5
        new_size = (max(28, int(w * scale)), max(28, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img

def convert_to_vlm_conversation(sample):
    img = sanitize_image(sample["decoded_image"])
    question = str(sample.get("question", "")).strip()
    options = sample.get("options", [])
    solution = str(sample.get("solution") or "").strip()
    answer = str(sample.get("answer", "")).strip()

    if options and len(options) > 0:
        labels = ["A", "B", "C", "D", "E"]
        opts_str = "\n".join([f"({labels[i]}) {opt}" for i, opt in enumerate(options[:len(labels)])])
        question += f"\n\nOptions:\n{opts_str}"

    if solution and solution.lower() != "none":
        response = f"{solution}\n\nFinal Answer: $$\\boxed{{{answer}}}$$"
    else:
        response = f"Final Answer: $$\\boxed{{{answer}}}$$"

    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{SYSTEM_PROMPT}\n\n{question}"},
                    {"type": "image", "image": img}
                ]
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response}]
            }
        ]
    }

def main():
    verify_gpu()
    print(f"[*] Initializing FastVisionModel: {MODEL_NAME}")
    
    model, tokenizer = FastVisionModel.from_pretrained(
        MODEL_NAME,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )

    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers=True,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.0,
        bias="none",
        random_state=3407,
    )

    print("[*] Loading MathLLMs/MathVision dataset for Smoke Test...")
    raw_dataset = load_dataset("MathLLMs/MathVision", split="test")
    
    converted_dataset = []
    for idx in range(min(100, len(raw_dataset))):
        try:
            sample = raw_dataset[idx]
            if sample.get("decoded_image") is not None:
                converted_dataset.append(convert_to_vlm_conversation(sample))
        except Exception:
            continue

    print(f"[+] Prepared {len(converted_dataset)} samples for smoke test.")
    FastVisionModel.for_training(model)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
        train_dataset=converted_dataset,
        args=SFTConfig(
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=MAX_STEPS,  # Límite estricto para validar en local
            learning_rate=2e-4,
            fp16=not is_bf16_supported(),
            bf16=is_bf16_supported(),
            logging_steps=5,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir="outputs_smoke",
            report_to="none",
            remove_unused_columns=False,
            dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            dataset_num_proc=1,
            dataloader_num_workers=0,
            max_seq_length=1536,
        ),
    )

    print(f"[*] Starting Smoke Test ({MAX_STEPS} steps)...")
    trainer_stats = trainer.train()
    print(f"[+] Smoke Test completed successfully in {trainer_stats.metrics['train_runtime']:.2f}s")

    lora_path = "models/lora_adapters/vertex-math-vision-smoke"
    model.save_pretrained(lora_path)
    tokenizer.save_pretrained(lora_path)
    print(f"[+] Smoke adapters saved to: {lora_path}")

if __name__ == "__main__":
    main()