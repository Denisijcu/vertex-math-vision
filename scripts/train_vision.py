import os
import torch
from PIL import Image
from datasets import load_dataset
from dotenv import load_dotenv
from unsloth import FastVisionModel, is_bf16_supported
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

load_dotenv()

MODEL_NAME = os.getenv("BASE_MODEL", "unsloth/Qwen2.5-VL-7B-Instruct-bnb-4bit")
LORA_RANK = int(os.getenv("LORA_RANK", 16))
LORA_ALPHA = int(os.getenv("LORA_ALPHA", 16))
MAX_PIXELS = 768 * 768  # Cap de resolución para evitar picos de VRAM (OOM Defense)

SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, an elite multimodal mathematical reasoning engine "
    "developed by Vertex Coders LLC. Analyze the diagram, provide step-by-step "
    "mathematical reasoning, and place the final answer inside \\boxed{}."
)

def sanitize_image(img: Image.Image) -> Image.Image:
    """Convierte a RGB puro y limita la resolución para proteger la VRAM."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if w * h > MAX_PIXELS:
        scale = (MAX_PIXELS / (w * h)) ** 0.5
        new_size = (max(28, int(w * scale)), max(28, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img

def convert_to_vlm_conversation(sample):
    """Estructura el registro en el esquema multimodal nativo de Unsloth."""
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

    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"{SYSTEM_PROMPT}\n\n{question}"},
                {"type": "image", "image": img}
            ]
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": response}
            ]
        }
    ]
    return {"messages": conversation}

def main():
    print(f"[*] Initializing FastVisionModel: {MODEL_NAME}")
    model, tokenizer = FastVisionModel.from_pretrained(
        MODEL_NAME,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )

    # Inyección de QLoRA en las capas multimodales (Visión + Lenguaje + Proyector)
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
        use_rslora=False,
        loftq_config=None,
    )

    print("[*] Loading and transforming MathLLMs/MathVision dataset...")
    raw_dataset = load_dataset("MathLLMs/MathVision", split="test")
    # Filtramos muestras sin imagen decodificada
    raw_dataset = raw_dataset.filter(lambda x: x["decoded_image"] is not None)
    
    # Transformación lazy en memoria para alimentar el UnslothVisionDataCollator
    converted_dataset = [convert_to_vlm_conversation(sample) for sample in raw_dataset]

    FastVisionModel.for_training(model)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
        train_dataset=converted_dataset,
        args=SFTConfig(
            per_device_train_batch_size=int(os.getenv("BATCH_SIZE", 2)),
            gradient_accumulation_steps=int(os.getenv("GRAD_ACCUMULATION", 4)),
            warmup_steps=15,
            num_train_epochs=int(os.getenv("EPOCHS", 3)),
            learning_rate=float(os.getenv("LEARNING_RATE", 2e-4)),
            fp16=not is_bf16_supported(),
            bf16=is_bf16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir="outputs",
            report_to="none",
            # Parámetros obligatorios para Vision Fine-Tuning en TRL
            remove_unused_columns=False,
            dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            dataset_num_proc=2,
            max_seq_length=2048,
        ),
    )

    print("[*] Starting Multimodal QLoRA Training...")
    trainer_stats = trainer.train()
    print(f"[+] Training completed in {trainer_stats.metrics['train_runtime']:.2f}s")

    # Guardado seguro de los adaptadores LoRA
    lora_path = "models/lora_adapters/vertex-math-vision-lora"
    model.save_pretrained(lora_path)
    tokenizer.save_pretrained(lora_path)
    print(f"[+] LoRA adapters securely saved to: {lora_path}")

if __name__ == "__main__":
    main()