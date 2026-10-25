
# Import Unsloth first so its optimizations are applied.
from unsloth import FastVisionModel

import torch
from datasets import load_dataset
from dotenv import load_dotenv
import os

load_dotenv()

LORA_PATH = "models/lora_adapters/vertex-math-vision-smoke"
BASE_MODEL = os.getenv(
    "BASE_MODEL",
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit",
)


def test_inference(sample_idx: int = 150):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Check the PyTorch installation.")

    if not os.path.isdir(LORA_PATH):
        raise FileNotFoundError(f"LoRA adapter not found: {LORA_PATH}")

    print(f"[*] Base model: {BASE_MODEL}")
    print(f"[*] LoRA adapter: {LORA_PATH}")

    # Load the base model, then attach the trained adapter.
    model, processor = FastVisionModel.from_pretrained(
        model_name=BASE_MODEL,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )

    from peft import PeftModel

    model = PeftModel.from_pretrained(model, LORA_PATH)
    FastVisionModel.for_inference(model)

    dataset = load_dataset("MathLLMs/MathVision", split="test")

    if sample_idx < 0 or sample_idx >= len(dataset):
        raise IndexError(
            f"Sample index {sample_idx} is invalid; "
            f"dataset contains {len(dataset)} samples."
        )

    sample = dataset[sample_idx]
    image = sample["decoded_image"]

    if image is None:
        raise ValueError(f"Sample {sample_idx} has no decoded image.")

    image = image.convert("RGB")
    question = str(sample.get("question", "")).strip()

    options = sample.get("options", [])
    if options:
        labels = ["A", "B", "C", "D", "E"]
        question += "\n\nOptions:\n" + "\n".join(
            f"({labels[i]}) {option}"
            for i, option in enumerate(options[:len(labels)])
        )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {
                    "type": "text",
                    "text": (
                        "Solve this mathematical problem carefully. "
                        "Give the final answer inside \\boxed{}.\n\n"
                        f"{question}"
                    ),
                },
            ],
        }
    ]

    # Let the multimodal processor handle both image and text.
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )

    inputs = {
        key: value.to("cuda") if isinstance(value, torch.Tensor) else value
        for key, value in inputs.items()
    }

    print(f"\n[Sample index]: {sample_idx}")
    print(f"[Question]: {question}")
    print(f"[Ground truth]: {sample.get('answer', 'Not available')}")
    print("---\n[Model output]:")

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            use_cache=True,
        )

    # Decode generated tokens only, excluding the input prompt.
    prompt_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[:, prompt_length:]

    print(processor.decode(generated_tokens[0], skip_special_tokens=True))


if __name__ == "__main__":
    test_inference()
