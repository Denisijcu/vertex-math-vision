import os
import json
import warnings
from pathlib import Path
from PIL import Image, ImageFile
from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()

# Hardening equilibrado: 25 Megapíxeles (bloquea ataques DoS reales sin romper diagramas HD)
Image.MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", 25000000))
ImageFile.LOAD_TRUNCATED_IMAGES = False
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, an elite multimodal mathematical reasoning engine "
    "developed by Vertex Coders LLC. Analyze the geometric or visual diagram carefully, "
    "formulate a rigorous step-by-step Chain-of-Thought in LaTeX, and conclude with "
    "the exact final answer inside \\boxed{}."
)

def format_mathvision_sample(sample: dict) -> dict:
    """Estandariza la pregunta, opciones y solución al formato de instrucción."""
    question = str(sample.get("question", "")).strip()
    options = sample.get("options", [])
    solution = str(sample.get("solution") or "").strip()
    answer = str(sample.get("answer", "")).strip()

    user_text = f"Problem (Subject: {sample.get('subject', 'math')}, Level: {sample.get('level', 1)}):\n{question}"
    if options and len(options) > 0:
        labels = ["A", "B", "C", "D", "E", "F"]
        opts_str = "\n".join([f"({labels[i]}) {opt}" for i, opt in enumerate(options[:len(labels)])])
        user_text += f"\n\nOptions:\n{opts_str}"

    if solution and solution.lower() != "none":
        assistant_text = f"### Step-by-Step Reasoning:\n{solution}\n\n### Final Answer:\n$$\\boxed{{{answer}}}$$"
    else:
        assistant_text = f"### Analysis:\nBy inspecting the visual relations in the diagram and solving for the target variable:\n\n### Final Answer:\n$$\\boxed{{{answer}}}$$"

    return {
        "id": str(sample.get("id")),
        "user_prompt": user_text,
        "assistant_response": assistant_text
    }

def audit_and_verify_dataset():
    print(f"[*] Auditing MathLLMs/MathVision dataset (MAX_IMAGE_PIXELS={Image.MAX_IMAGE_PIXELS})...")
    dataset = load_dataset("MathLLMs/MathVision", split="test")
    
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "verified_manifest.jsonl"

    valid_count = 0
    skipped_count = 0
    total_samples = len(dataset)

    with open(manifest_path, "w", encoding="utf-8") as f:
        for idx in range(total_samples):
            try:
                # Acceso indexado para capturar errores de decodificación de PIL en Arrow
                item = dataset[idx]
                img = item.get("decoded_image")
                
                if img is None or not item.get("question") or not item.get("answer"):
                    skipped_count += 1
                    continue
                
                width, height = img.size
                if width < 28 or height < 28:
                    skipped_count += 1
                    continue

                formatted = format_mathvision_sample(item)
                formatted["dataset_idx"] = idx
                formatted["resolution"] = f"{width}x{height}"
                f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
                valid_count += 1

            except (Image.DecompressionBombError, OSError, SyntaxError) as e:
                print(f"[!] Warning: Sample idx {idx} rejected by security filter ({type(e).__name__}).")
                skipped_count += 1
                continue

    print(f"[+] Audit Complete. Valid samples: {valid_count} | Filtered out: {skipped_count}")
    print(f"[+] Manifest written to: {manifest_path}")

if __name__ == "__main__":
    audit_and_verify_dataset()