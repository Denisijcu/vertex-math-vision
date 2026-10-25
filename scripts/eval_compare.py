
# scripts/eval_compare.py
# Comparacion reproducible: Qwen2.5-VL base vs Vertex-Math-Vision LoRA.
# No entrena ni modifica el adaptador.

# Importar Unsloth primero.
from unsloth import FastVisionModel

import csv
import gc
import os
import random
import re
from pathlib import Path

import torch
from datasets import load_dataset
from dotenv import load_dotenv
from peft import PeftModel

load_dotenv()

BASE_MODEL = os.getenv(
    "BASE_MODEL",
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit",
)
LORA_PATH = "models/lora_adapters/vertex-math-vision-smoke"
OUTPUT_CSV = Path("outputs_eval/vertex_math_vision_comparison.csv")

# Mantener la instruccion utilizada durante el entrenamiento.
SYSTEM_PROMPT = (
    "You are Vertex-Math-Vision, an elite multimodal mathematical "
    "reasoning engine developed by Vertex Coders LLC. Analyze the "
    "diagram, provide step-by-step mathematical reasoning, and place "
    "the final answer inside \\boxed{}."
)

# Evaluacion inicial corta para reducir el tiempo de ejecucion.
EVAL_COUNT = 12
RANDOM_SEED = 3407
MAX_NEW_TOKENS = 192
CASTOR_INDEX = 150


def clean_text(value):
    """Convierte una respuesta en texto comparable."""
    text = str(value or "").strip().lower()

    text = text.replace("$$", "").replace("$", "")
    text = text.replace("\\,", "").replace("\\!", "")
    text = text.replace("\\%", "%")
    text = re.sub(r"\\(?:text|mathrm|mathbf)\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\s+", "", text)

    return text.strip(" .,:;。")


def extract_candidate(text):
    """Intenta extraer la respuesta final sin comparar toda la explicacion."""
    text = str(text or "").strip()

    # Preferir la ultima respuesta encerrada en \boxed{...}.
    boxed = re.findall(r"\\boxed\{([^{}]*)\}", text)
    if boxed:
        return boxed[-1].strip()

    # Buscar expresiones explicitas de respuesta final.
    patterns = [
        r"(?i)(?:final\s+answer|answer)\s*(?:is|:|=)\s*(.+)",
        r"(?i)(?:the\s+answer)\s*(?:is|:|=)\s*(.+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            candidate = matches[-1].splitlines()[0].strip()
            candidate = re.sub(r"^[*`\s]+|[*`\s]+$", "", candidate)
            return candidate.rstrip(" .")

    # Si no hay etiqueta, utilizar la ultima linea no vacia.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        return lines[-1]

    return text


def normalize_answer(text):
    """Normaliza formatos comunes de respuestas matematicas."""
    candidate = extract_candidate(text)
    candidate = clean_text(candidate)

    # Retirar delimitadores de respuesta comunes.
    candidate = re.sub(r"^(?:answer|finalanswer)[:=]?", "", candidate)
    candidate = candidate.strip("()[]{}.,;:")

    return candidate


def answers_match(ground_truth, prediction):
    """Comparacion textual normalizada, no equivalencia matematica completa."""
    expected = normalize_answer(ground_truth)
    predicted = normalize_answer(prediction)

    if not expected or not predicted:
        return False

    if expected == predicted:
        return True

    # Comparar formatos sencillos de opcion multiple: A, (A), Option A.
    expected_option = re.fullmatch(
        r"(?:option)?\(?([a-e])\)?",
        expected,
    )
    predicted_option = re.fullmatch(
        r"(?:option)?\(?([a-e])\)?",
        predicted,
    )

    if expected_option and predicted_option:
        return expected_option.group(1) == predicted_option.group(1)

    return False


def build_inputs(processor, sample):
    image = sample.get("decoded_image")
    if image is None:
        raise ValueError("La muestra no contiene una imagen decodificada.")

    image = image.convert("RGB")
    question = str(sample.get("question", "")).strip()

    options = sample.get("options", [])
    if options:
        labels = ["A", "B", "C", "D", "E"]
        formatted_options = [
            f"({labels[i]}) {option}"
            for i, option in enumerate(options[:len(labels)])
        ]
        question += "\n\nOptions:\n" + "\n".join(formatted_options)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{SYSTEM_PROMPT}\n\n{question}",
                },
                {
                    "type": "image",
                    "image": image,
                },
            ],
        }
    ]

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

    return inputs, question


def generate_answer(model, processor, sample):
    inputs, question = build_inputs(processor, sample)

    try:
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                use_cache=True,
            )

        prompt_length = inputs["input_ids"].shape[1]
        new_tokens = outputs[:, prompt_length:]

        answer = processor.decode(
            new_tokens[0],
            skip_special_tokens=True,
        ).strip()

        return question, answer

    finally:
        del inputs
        gc.collect()
        torch.cuda.empty_cache()


def select_samples(dataset):
    """Selecciona 12 indices posteriores a los 100 usados en entrenamiento."""
    if len(dataset) <= 100:
        raise RuntimeError("El dataset no contiene suficientes muestras.")

    rng = random.Random(RANDOM_SEED)

    # Reservar un puesto para el caso del castor.
    candidates = [
        idx
        for idx in range(100, len(dataset))
        if idx != CASTOR_INDEX
    ]
    rng.shuffle(candidates)

    selected_indices = [CASTOR_INDEX]
    samples = []

    # Incluir el castor si existe y contiene imagen.
    if CASTOR_INDEX < len(dataset):
        sample = dataset[CASTOR_INDEX]
        if sample.get("decoded_image") is not None:
            samples.append((CASTOR_INDEX, sample))

    # Buscar muestras validas hasta alcanzar el objetivo.
    for idx in candidates:
        if len(samples) >= EVAL_COUNT:
            break

        sample = dataset[idx]
        if sample.get("decoded_image") is not None:
            samples.append((idx, sample))

    if not samples:
        raise RuntimeError("No se encontraron imagenes validas para evaluar.")

    # Orden estable para facilitar la comparacion de ejecuciones.
    samples.sort(key=lambda item: item[0])
    return samples


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no esta disponible.")

    if not os.path.isdir(LORA_PATH):
        raise FileNotFoundError(
            f"No se encontro el adaptador: {LORA_PATH}"
        )

    print(f"Modelo base: {BASE_MODEL}")
    print(f"Adaptador: {LORA_PATH}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    print("\n[CARGA] Cargando MathVision...")
    dataset = load_dataset("MathLLMs/MathVision", split="test")
    samples = select_samples(dataset)

    print(f"Muestras seleccionadas: {len(samples)}")
    print(f"Indice del castor incluido: {any(idx == CASTOR_INDEX for idx, _ in samples)}")
    print(f"Maximo de tokens nuevos por respuesta: {MAX_NEW_TOKENS}")

    print("\n[CARGA] Cargando modelo base...")
    model, processor = FastVisionModel.from_pretrained(
        model_name=BASE_MODEL,
        load_in_4bit=True,
        use_gradient_checkpointing="unsloth",
    )
    FastVisionModel.for_inference(model)

    results = []

    print("\n========== EVALUACION DEL MODELO BASE ==========")

    for position, (idx, sample) in enumerate(samples, start=1):
        question, answer = generate_answer(model, processor, sample)

        results.append({
            "index": idx,
            "id": str(sample.get("id", "")),
            "question": question,
            "ground_truth": str(sample.get("answer", "")).strip(),
            "base_output": answer,
            "lora_output": "",
            "base_match": False,
            "lora_match": False,
        })

        print(f"[BASE {position}/{len(samples)}] idx={idx}: {answer}")

    print("\n[CARGA] Adjuntando el adaptador LoRA...")
    model = PeftModel.from_pretrained(
        model,
        LORA_PATH,
        is_trainable=False,
    )
    FastVisionModel.for_inference(model)

    print("\n========== EVALUACION DEL MODELO CON LORA ==========")

    for position, ((idx, sample), result) in enumerate(
        zip(samples, results),
        start=1,
    ):
        _, answer = generate_answer(model, processor, sample)
        result["lora_output"] = answer

        print(f"[LORA {position}/{len(samples)}] idx={idx}: {answer}")

    for result in results:
        result["base_match"] = answers_match(
            result["ground_truth"],
            result["base_output"],
        )
        result["lora_match"] = answers_match(
            result["ground_truth"],
            result["lora_output"],
        )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "index",
        "id",
        "question",
        "ground_truth",
        "base_output",
        "lora_output",
        "base_match",
        "lora_match",
    ]

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    total = len(results)
    base_correct = sum(row["base_match"] for row in results)
    lora_correct = sum(row["lora_match"] for row in results)

    print("\n========== RESULTADOS ==========")
    print(
        f"Modelo base: {base_correct}/{total} "
        f"({100 * base_correct / total:.1f}%)"
    )
    print(
        f"Base + LoRA: {lora_correct}/{total} "
        f"({100 * lora_correct / total:.1f}%)"
    )
    print(f"CSV guardado en: {OUTPUT_CSV.resolve()}")

    print("\n========== CASO DEL CASTOR ==========")
    castor_found = False

    for row in results:
        if row["index"] == CASTOR_INDEX:
            castor_found = True
            print(f"Respuesta correcta: {row['ground_truth']}")
            print(f"Base: {row['base_output']}")
            print(f"LoRA: {row['lora_output']}")
            print(f"Base correcta: {row['base_match']}")
            print(f"LoRA correcta: {row['lora_match']}")
            break

    if not castor_found:
        print("El indice 150 no tenia una imagen valida y fue omitido.")

    print(
        "\nNOTA: evaluacion experimental sobre muestras posteriores "
        "a los primeros 100 indices. La coincidencia normalizada no "
        "demuestra equivalencia matematica completa ni sustituye "
        "una evaluacion independiente."
    )


if __name__ == "__main__":
    main()
