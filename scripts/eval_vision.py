import torch
from datasets import load_dataset
from unsloth import FastVisionModel

LORA_PATH = "models/lora_adapters/vertex-math-vision-lora"

def test_inference(sample_idx: int = 0):
    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=LORA_PATH,
        load_in_4bit=True,
    )
    FastVisionModel.for_inference(model)

    dataset = load_dataset("MathLLMs/MathVision", split="test")
    sample = dataset[sample_idx]
    image = sample["decoded_image"].convert("RGB")
    question = sample["question"]

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": f"Solve step-by-step and put the final result in \\boxed{{}}:\n{question}"}
            ]
        }
    ]

    input_text = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    inputs = tokenizer(
        image,
        input_text,
        add_special_tokens=False,
        return_tensors="pt",
    ).to("cuda")

    print(f"\n[Question]: {question}")
    print(f"[Ground Truth]: {sample['answer']}\n---\n[Model Output]:")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            use_cache=True,
            temperature=0.2,
            min_p=0.1
        )
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

if __name__ == "__main__":
    test_inference(0)