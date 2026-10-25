"""
Vertex Math Vision — backend en un Space de Hugging Face con ZeroGPU.

Mismo comportamiento que el backend local (app/backend): mismos prompts, misma lectura de la respuesta,
mismos guardrails y la misma verificación con SymPy (services/ es una copia de app/backend/services).
Lo único que cambia es quién genera el texto: aquí transformers + el adaptador LoRA en la GPU de ZeroGPU;
en casa, LM Studio con el GGUF.

Si ZeroGPU niega la GPU al visitante (cuota diaria agotada, cola llena), la respuesta se genera en CPU
con el mismo modelo fusionado y cuantizado a int8: más lenta, pero sin cuota.

Endpoints (Gradio API, el frontend Angular los llama con @gradio/client):
  /health  -> estado (sin GPU)
  /read    -> transcribe la foto sin resolverla
  /solve   -> resuelve paso a paso y verifica con SymPy
  /report  -> reporte de error del tutor (solo texto; nunca la foto)
"""
import base64
import io
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
import spaces
import torch
from peft import PeftModel
from PIL import Image
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

from config import get_settings
from services import verify
from services.answers import extract_answer
from services.guard import MSG, Guard, GuardError, clean_text
from services.prompts import READ_PROMPT, SYSTEM_PROMPT, build_ask, parse_reading

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("space")

BASE = "Qwen/Qwen3-VL-2B-Instruct"
ADAPTER = "Denisijcu/vertex-math-vision"
APP_URL = os.getenv("APP_URL", "")
FORCE_CPU = os.getenv("FORCE_CPU") == "1"
REPORTS = Path(os.getenv("REPORT_LOG_PATH", "/data/reports.jsonl" if Path("/data").is_dir() else "reports.jsonl"))
MAX_SIDE = 896  # suficiente para letra a mano; menos tokens de imagen = más rápido en CPU

settings = get_settings()
guard = Guard(settings)

# ---------------------------------------------------------------------------
# Modelo en "cuda" al arrancar (ZeroGPU lo emula fuera de @spaces.GPU)
# ---------------------------------------------------------------------------
processor = AutoProcessor.from_pretrained(ADAPTER)  # el procesador y la plantilla con los que se entrenó
model = Qwen3VLForConditionalGeneration.from_pretrained(BASE, dtype=torch.bfloat16)
# torch_device="cpu": PEFT cargaría los pesos en "cuda" y fuera de @spaces.GPU no hay GPU real.
model = PeftModel.from_pretrained(model, ADAPTER, torch_device="cpu")


def _check_adapter(m) -> None:
    """Si los nombres de las capas no coinciden, PEFT solo avisa y el adaptador queda sin aplicar:
    el Space respondería con el modelo base sin que nadie se entere. Aquí se comprueba de verdad."""
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


@spaces.GPU(duration=60)  # leer + resolver tarda unos segundos; 60 s de margen para respuestas largas
def generate_gpu(image: Image.Image | None, text: str, max_new_tokens: int) -> str:
    with _GEN_LOCK:
        return _run(model, image, text, max_new_tokens, "cuda")


# ---------------------------------------------------------------------------
# Respaldo en CPU: el mismo modelo, fusionado y en int8 dinámico (como en el Space del ajedrez)
# ---------------------------------------------------------------------------
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
        except Exception as e:  # noqa: BLE001  si int8 falla, queda en float32 (más lento, pero responde)
            log.warning("int8 no disponible, respaldo CPU en float32 -> %s", e)
        _CPU["m"] = m
        log.info("Respaldo CPU listo en %.1f s (%s núcleos)", time.perf_counter() - t0, os.cpu_count())
    return _CPU["m"]


def generate_cpu(image: Image.Image | None, text: str, max_new_tokens: int) -> str:
    with _CPU_LOCK:
        m = cpu_model()
        t0 = time.perf_counter()
        out = _run(m, image, text, max_new_tokens, "cpu")
        log.info("CPU: %.1f s", time.perf_counter() - t0)
        return out


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
# Utilidades
# ---------------------------------------------------------------------------
def fail(code: str, message: str):
    """Error que el frontend reconoce: el mensaje empieza por el código."""
    raise gr.Error(f"{code}: {message}", print_exception=False)


def _lang(lang: str) -> str:
    return lang if lang in ("es", "en") else "es"


def _ip(request: gr.Request | None) -> str:
    if request is None:
        return "unknown"
    fwd = request.headers.get("x-forwarded-for", "") if request.headers else ""
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


def _image(image_b64: str, lang: str) -> Image.Image | None:
    if not image_b64:
        return None
    if "," in image_b64[:80]:
        image_b64 = image_b64.split(",", 1)[1]  # quita "data:image/jpeg;base64,"
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except Exception:  # noqa: BLE001
        fail("IMAGE_UNSUPPORTED", MSG[lang]["image_bad"])
    try:
        jpeg = guard.image(raw, lang)  # valida, gira, quita EXIF y limita el tamaño
    except GuardError as e:
        fail(e.code, e.message)
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return img


async def _text(text: str, lang: str) -> str:
    try:
        return await guard.text(text, lang)
    except GuardError as e:
        fail(e.code, e.message)


def _rate(request: gr.Request | None, lang: str) -> None:
    try:
        guard.rate(_ip(request), lang)
    except GuardError as e:
        fail(e.code, e.message)


FALLBACK = {
    "es": "El tutor está despertando o muy ocupado. Prueba otra vez en un minuto.",
    "en": "The tutor is waking up or very busy. Please try again in a minute.",
}
NOT_MATH = {
    "es": "No veo un ejercicio de matemáticas en esta foto. Prueba con una foto más clara del ejercicio.",
    "en": "I can't see a math exercise in this photo. Try a clearer photo of the exercise.",
}


# ---------------------------------------------------------------------------
# API (mismos contratos que app/backend/models.py)
# ---------------------------------------------------------------------------
def health() -> dict:
    return {"status": "ok", "llm": "up"}


async def read(image_b64: str, lang: str = "es", request: gr.Request = None) -> dict:
    lang = _lang(lang)
    _rate(request, lang)
    img = _image(image_b64, lang)
    if img is None:
        fail("EMPTY_INPUT", MSG[lang]["empty"])
    try:
        raw, device = generate(img, READ_PROMPT[lang], 300)
    except Exception:  # noqa: BLE001
        log.exception("Fallo al leer")
        return {"reading": "", "is_math": False, "problems": [], "lang": lang, "source": "fallback"}
    reading, is_math, problems = parse_reading(raw)
    log.info("read en %s: %d caracteres", device, len(reading))
    return {"reading": reading, "is_math": is_math, "problems": problems, "lang": lang, "source": "llm"}


async def solve(image_b64: str = "", text: str = "", reading: str = "", lang: str = "es",
                request: gr.Request = None) -> dict:
    lang = _lang(lang)
    _rate(request, lang)
    text = await _text(text, lang)
    reading = await _text(reading, lang)
    img = _image(image_b64, lang)
    if img is None and not text and not reading:
        fail("EMPTY_INPUT", MSG[lang]["empty"])
    try:
        if img is not None and not reading:
            reading, is_math, _ = parse_reading(generate(img, READ_PROMPT[lang], 300)[0])
            if not is_math and not text:
                return {"reading": "", "steps": NOT_MATH[lang], "answer": None, "verification": "not_math",
                        "sympy_answer": None, "note": NOT_MATH[lang], "lang": lang, "source": "llm"}
        steps, device = generate(img, build_ask(text, reading, lang), settings.LLM_MAX_TOKENS)
    except Exception:  # noqa: BLE001
        log.exception("Fallo al resolver")
        return {"reading": reading, "steps": FALLBACK[lang], "answer": None, "verification": "unverified",
                "sympy_answer": None, "note": FALLBACK[lang], "lang": lang, "source": "fallback"}
    answer = extract_answer(steps)
    problem = reading or text
    result = verify.check(problem, answer, lang, steps)
    log.info("solve en %s: %s", device, result.status)
    return {"reading": problem, "steps": steps, "answer": answer, "verification": result.status,
            "sympy_answer": result.sympy_answer, "note": result.note, "lang": lang, "source": "llm"}


def report(message: str, reading: str = "", answer: str = "", email: str = "", website: str = "",
           request: gr.Request = None) -> dict:
    if website:  # honeypot
        return {"ok": True}
    _rate(request, "es")
    message = clean_text(message)[:2000]
    if len(message) < 3:
        fail("INVALID_REQUEST", "Escribe qué salió mal. / Tell us what went wrong.")
    email = clean_text(email)[:200]
    if email and ("@" not in email or " " in email):
        email = ""
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "message": message,
             "reading": clean_text(reading)[:1000] or None, "answer": clean_text(answer)[:300] or None,
             "email": email or None}
    REPORTS.parent.mkdir(parents=True, exist_ok=True)
    with REPORTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("Reporte recibido (%d caracteres)", len(message))
    return {"ok": True}


with gr.Blocks(title="Vertex Math Vision — API") as demo:
    gr.Markdown(
        "# Vertex Math Vision — API\n"
        "Backend del tutor de matemáticas de Vertex Coders: Qwen3-VL-2B afinado con QLoRA "
        "([Denisijcu/vertex-math-vision](https://huggingface.co/Denisijcu/vertex-math-vision)), "
        "con verificación de las respuestas con SymPy.\n\n"
        + (f"**Para usar el tutor, abre la app:** {APP_URL}\n\n" if APP_URL else "")
        + "Las fotos no se guardan."
    )
    gr.api(health, api_name="health")
    gr.api(read, api_name="read")
    gr.api(solve, api_name="solve")
    gr.api(report, api_name="report")

demo.queue(default_concurrency_limit=2).launch()
