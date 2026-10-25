"""
Motor del demo: el mismo modelo y el mismo flujo que el Space de la API (app/space/app.py).

- Qwen3-VL-2B-Instruct + adaptador LoRA Denisijcu/vertex-math-vision, en ZeroGPU.
- Si ZeroGPU niega la GPU (cuota del visitante agotada, cola llena), responde en CPU con el modelo
  fusionado y en int8: más lento, pero sin cuota.
- Mismos prompts, misma lectura de la respuesta, mismos guardrails y misma verificación con SymPy
  (services/ es una copia de app/backend/services).

VMV_FAKE=1 arranca sin modelo (respuestas de ejemplo). Sirve para probar la interfaz en tu PC sin GPU.
"""
import io
import logging
import os
import threading
import time
from dataclasses import dataclass

from PIL import Image

from config import get_settings
from services import verify
from services.answers import extract_answer
from services.guard import Guard, GuardError
from services.prompts import READ_PROMPT, SYSTEM_PROMPT, build_ask, parse_reading

log = logging.getLogger("core")

BASE = "Qwen/Qwen3-VL-2B-Instruct"
ADAPTER = "Denisijcu/vertex-math-vision"
FAKE = os.getenv("VMV_FAKE") == "1"
FORCE_CPU = os.getenv("FORCE_CPU") == "1"
MAX_SIDE = 896  # suficiente para letra a mano; menos tokens de imagen = más rápido en CPU

settings = get_settings()
guard = Guard(settings)


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------
if FAKE:
    log.warning("VMV_FAKE=1: el demo arranca SIN modelo (respuestas de ejemplo)")

    def generate(image: Image.Image | None, text: str, max_new_tokens: int) -> tuple[str, str]:
        time.sleep(0.4)
        if text in READ_PROMPT.values():
            return "2x + 3 = 7", "fake"
        return ("**What I need to find:** the value of x.\n"
                "**Step 1:** Subtract 3 from both sides: 2x = 7 - 3 = 4.\n"
                "**Step 2:** Divide by 2: x = 4 / 2 = 2.\n"
                "**Check:** 2·2 + 3 = 7 ✓\n"
                "**Answer:** x = 2\n$\\boxed{2}$"), "fake"
else:
    import spaces
    import torch
    from peft import PeftModel
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    processor = AutoProcessor.from_pretrained(ADAPTER)  # el procesador y la plantilla con los que se entrenó
    model = Qwen3VLForConditionalGeneration.from_pretrained(BASE, dtype=torch.bfloat16)
    # torch_device="cpu": PEFT cargaría los pesos en "cuda" y fuera de @spaces.GPU no hay GPU real.
    model = PeftModel.from_pretrained(model, ADAPTER, torch_device="cpu")

    def _check_adapter(m) -> None:
        """Si los nombres de las capas no coinciden, PEFT solo avisa y el adaptador queda sin aplicar.
        Aquí se comprueba de verdad: sin LoRA el Space no arranca."""
        lora_b = [p for n, p in m.named_parameters() if "lora_B" in n]
        if not lora_b or all(float(p.detach().abs().sum()) == 0.0 for p in lora_b):
            raise RuntimeError("El adaptador vertex-math-vision no se aplicó (capas LoRA vacías o ausentes).")
        log.info("Adaptador aplicado: %d matrices LoRA cargadas", len(lora_b))

    _check_adapter(model)
    model.to("cuda").eval()
    _GEN_LOCK = threading.Lock()

    def _messages(image: Image.Image | None, text: str) -> list[dict]:
        content = ([{"type": "image", "image": image}] if image is not None else []) + [{"type": "text", "text": text}]
        return [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": content}]

    def _run(m, image: Image.Image | None, text: str, max_new_tokens: int, device: str) -> str:
        inputs = processor.apply_chat_template(_messages(image, text), tokenize=True, add_generation_prompt=True,
                                               return_dict=True, return_tensors="pt").to(device)
        with torch.no_grad():
            out = m.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.2, top_p=0.9,
                             repetition_penalty=1.05)
        return processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()

    @spaces.GPU(duration=60)
    def generate_gpu(image: Image.Image | None, text: str, max_new_tokens: int) -> str:
        with _GEN_LOCK:
            return _run(model, image, text, max_new_tokens, "cuda")

    # Respaldo en CPU: el mismo modelo, fusionado y en int8 dinámico.
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    _CPU: dict = {}
    _CPU_LOCK = threading.Lock()

    def cpu_model():
        if "m" not in _CPU:
            t0 = time.perf_counter()
            m = Qwen3VLForConditionalGeneration.from_pretrained(BASE, dtype=torch.float32)
            m = PeftModel.from_pretrained(m, ADAPTER, torch_device="cpu")
            _check_adapter(m)
            m = m.merge_and_unload().eval()
            try:
                m = torch.ao.quantization.quantize_dynamic(m, {torch.nn.Linear}, dtype=torch.qint8)
            except Exception as e:  # noqa: BLE001  si int8 falla, queda en float32
                log.warning("int8 no disponible, respaldo CPU en float32 -> %s", e)
            _CPU["m"] = m
            log.info("Respaldo CPU listo en %.1f s", time.perf_counter() - t0)
        return _CPU["m"]

    def generate_cpu(image: Image.Image | None, text: str, max_new_tokens: int) -> str:
        with _CPU_LOCK:
            return _run(cpu_model(), image, text, max_new_tokens, "cpu")

    def _warm_cpu():
        try:
            with _CPU_LOCK:
                cpu_model()
        except Exception as e:  # noqa: BLE001
            log.warning("Respaldo CPU no disponible -> %s", e)

    threading.Thread(target=_warm_cpu, daemon=True).start()

    def generate(image: Image.Image | None, text: str, max_new_tokens: int) -> tuple[str, str]:
        """GPU si se puede; si ZeroGPU la niega, la copia en CPU. Devuelve (texto, dispositivo)."""
        if not FORCE_CPU:
            try:
                return generate_gpu(image, text, max_new_tokens), "gpu"
            except Exception as e:  # noqa: BLE001
                log.warning("GPU no disponible: %s -> respaldo CPU", str(e)[:200])
        return generate_cpu(image, text, max_new_tokens), "cpu"


# ---------------------------------------------------------------------------
# Flujo: limpiar foto -> leer -> resolver -> verificar
# ---------------------------------------------------------------------------
@dataclass
class Solution:
    reading: str
    steps: str
    answer: str | None
    status: str          # verified | mismatch | ill_posed | steps_ok | steps_wrong | unverified | not_math
    sympy_answer: str | None
    note: str | None
    device: str


def clean_image(image: Image.Image, lang: str) -> Image.Image:
    """Valida la foto, la gira según EXIF, quita los metadatos y la reduce. Lanza GuardError si no sirve."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    jpeg = guard.image(buf.getvalue(), lang)
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return img


def read(image: Image.Image, lang: str) -> tuple[str, bool, list[str]]:
    """Transcribe el ejercicio sin resolverlo: (lectura, es_matemática, lista de ejercicios)."""
    raw, device = generate(image, READ_PROMPT[lang], 300)
    reading, is_math, problems = parse_reading(raw)
    log.info("read en %s: %d caracteres", device, len(reading))
    return reading, is_math, problems


def solve(image: Image.Image | None, text: str, reading: str, lang: str) -> Solution:
    """Resuelve paso a paso (conversación nueva, mismo system prompt del entrenamiento) y verifica con SymPy."""
    steps, device = generate(image, build_ask(text, reading, lang), settings.LLM_MAX_TOKENS)
    answer = extract_answer(steps)
    problem = reading or text
    result = verify.check(problem, answer, lang, steps)
    log.info("solve en %s: %s", device, result.status)
    return Solution(problem, steps, answer, result.status, result.sympy_answer, result.note, device)


__all__ = ["FAKE", "GuardError", "Solution", "clean_image", "guard", "read", "solve"]
