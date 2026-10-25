"""
Vertex Math Vision — demo en Gradio (Space de Hugging Face con ZeroGPU).

La misma experiencia que la app de Netlify, pero dentro de Hugging Face:
  foto o texto -> "esto es lo que leí" (editable) -> pasos -> respuesta con etiqueta honesta de SymPy.

El modelo y el flujo están en core.py (los mismos del Space de la API). Este archivo es solo la interfaz.
Para probarla sin GPU en tu PC:  set VMV_FAKE=1  y  python app.py
"""
import html
import logging
import os
import re

import gradio as gr

import core
from core import GuardError
from services.guard import MSG

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("demo")

APP_URL = os.getenv("APP_URL", "https://vertex-math-vision.netlify.app")
MODEL_URL = "https://huggingface.co/Denisijcu/vertex-math-vision"
GGUF_URL = "https://huggingface.co/Denisijcu/vertex-math-vision-GGUF"
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")

# ---------------------------------------------------------------------------
# Textos ES / EN
# ---------------------------------------------------------------------------
T = {
    "es": {
        "tagline": "Saca una foto. Entiéndelo paso a paso.",
        "sub": "Tutor de matemáticas para primaria y secundaria, en español o inglés. Lee tu ejercicio, "
               "aunque esté escrito a mano, lo explica paso a paso y comprueba la respuesta con una calculadora "
               "cuando se puede.",
        "app": "Abrir la app", "model": "Modelo", "offline": "Úsalo sin internet (GGUF)",
        "lang": "Idioma de la respuesta",
        "tab_photo": "📷 Foto", "tab_text": "⌨️ Escribir",
        "image": "Foto del ejercicio", "read": "Leer ejercicio",
        "reading": "Esto es lo que leí (corrígelo si hace falta)",
        "pick": "Hay varios ejercicios: elige uno",
        "solve_photo": "Resolver", "text": "Escribe el ejercicio",
        "text_ph": "Ejemplo: 2x + 3 = 7   ·   3/4 + 1/6   ·   Ana tiene 24 caramelos y regala 1/3…",
        "solve_text": "Resolver", "clear": "Nuevo ejercicio",
        "ex_photo": "Prueba con una de estas fotos", "ex_text": "O con uno de estos",
        "result": "Resultado", "answer": "Respuesta", "steps": "Cómo se resuelve", "calc": "La calculadora dice",
        "waiting": "Aquí aparecerá la solución paso a paso.",
        "need_image": "Sube o saca una foto del ejercicio.",
        "need_reading": "Primero pulsa «Leer ejercicio», o escribe el ejercicio en la caja.",
        "not_math": "No veo un ejercicio de matemáticas en esta foto. Prueba con una foto más clara del ejercicio.",
        "busy": "El tutor está despertando o muy ocupado. Prueba otra vez en un minuto.",
        "no_answer": "Sin respuesta final",
        "disclaimer": "Vertex Math Vision es un modelo pequeño y puede equivocarse. Úsalo para aprender, no para "
                      "copiar: revisa siempre los pasos.",
        "privacy": "Las fotos no se guardan: se les quitan los metadatos (EXIF/GPS), se usan para responder y se "
                   "descartan.",
        "how": "**Cómo funciona:** 1) el modelo copia el ejercicio sin resolverlo · 2) tú lo revisas · "
               "3) lo resuelve paso a paso · 4) SymPy comprueba la respuesta, o al menos las cuentas de cada paso. "
               "Si no puede comprobar nada, te lo dice.",
        "gpu": "Respondido en GPU", "cpu": "Respondido en CPU (la cuota de GPU se agotó: más lento)",
        "verify": {
            "verified": "Verificado", "mismatch": "No coincide con la calculadora",
            "ill_posed": "Ejercicio mal planteado", "steps_ok": "Cuentas correctas · planteamiento sin verificar",
            "steps_wrong": "Hay una cuenta mal", "unverified": "Sin verificar", "not_math": "No es un ejercicio",
        },
    },
    "en": {
        "tagline": "Snap a photo. Understand it step by step.",
        "sub": "A math tutor for elementary, middle and high school, in English or Spanish. It reads your exercise, "
               "even handwritten, explains it step by step and checks the answer with a calculator when possible.",
        "app": "Open the app", "model": "Model", "offline": "Use it offline (GGUF)",
        "lang": "Answer language",
        "tab_photo": "📷 Photo", "tab_text": "⌨️ Type",
        "image": "Photo of the exercise", "read": "Read exercise",
        "reading": "This is what I read (fix it if needed)",
        "pick": "There are several exercises: pick one",
        "solve_photo": "Solve", "text": "Type the exercise",
        "text_ph": "Example: 2x + 3 = 7   ·   3/4 + 1/6   ·   Ann has 24 candies and gives away 1/3…",
        "solve_text": "Solve", "clear": "New exercise",
        "ex_photo": "Try one of these photos", "ex_text": "Or one of these",
        "result": "Result", "answer": "Answer", "steps": "How to solve it", "calc": "The calculator says",
        "waiting": "The step-by-step solution will appear here.",
        "need_image": "Upload or take a photo of the exercise.",
        "need_reading": "First press “Read exercise”, or type the exercise in the box.",
        "not_math": "I can't see a math exercise in this photo. Try a clearer photo of the exercise.",
        "busy": "The tutor is waking up or very busy. Please try again in a minute.",
        "no_answer": "No final answer",
        "disclaimer": "Vertex Math Vision is a small model and can make mistakes. Use it to learn, not to copy: "
                      "always check the steps.",
        "privacy": "Photos are never stored: their metadata (EXIF/GPS) is removed, they are used to answer and "
                   "then discarded.",
        "how": "**How it works:** 1) the model copies the exercise without solving it · 2) you review it · "
               "3) it solves it step by step · 4) SymPy checks the answer, or at least the arithmetic in each step. "
               "When it can't check anything, it tells you.",
        "gpu": "Answered on GPU", "cpu": "Answered on CPU (GPU quota used up: slower)",
        "verify": {
            "verified": "Verified", "mismatch": "Doesn’t match the calculator",
            "ill_posed": "Ill-posed exercise", "steps_ok": "Arithmetic correct · setup not verified",
            "steps_wrong": "Arithmetic mistake", "unverified": "Not verified", "not_math": "Not an exercise",
        },
    },
}

# Verde solo para "verificado". Ámbar: hay un problema. Azul: información (no comprobado del todo).
BADGE = {
    "verified": ("ok", "✔"), "mismatch": ("warn", "⚠"), "ill_posed": ("warn", "⚠"), "steps_wrong": ("warn", "⚠"),
    "steps_ok": ("info", "ℹ"), "unverified": ("info", "ℹ"), "not_math": ("muted", "⊘"),
}

TEXT_EXAMPLES = {
    "es": ["2x + 3 = 7", "3/4 + 1/6", "x^2 - 5x + 6 = 0",
           "Ana tiene 24 caramelos y regala la tercera parte a sus amigos. ¿Cuántos caramelos le quedan?"],
    "en": ["2x + 3 = 7", "3/4 + 1/6", "x^2 - 5x + 6 = 0",
           "Ann has 24 candies and gives a third of them to her friends. How many candies does she have left?"],
}

LATEX = [
    {"left": "$$", "right": "$$", "display": True},
    {"left": "\\[", "right": "\\]", "display": True},
    {"left": "$", "right": "$", "display": False},
    {"left": "\\(", "right": "\\)", "display": False},
]


# ---------------------------------------------------------------------------
# Presentación de la respuesta
# ---------------------------------------------------------------------------
_INLINE_LABEL = re.compile(r"[ \t]+(\*\*[^*\n]{1,40}?:\*\*|\*\*[^*\n]{1,40}?\*\*:)")
_LABEL = re.compile(r"^\s*\*\*([^*]{1,40}?):?\*\*:?\s*(.*)$")
_ANSWER_LABEL = re.compile(r"^(respuesta|answer|respuesta final|final answer|boxed answer|respuesta en caja)", re.I)


def steps_markdown(raw: str) -> str:
    """Los pasos del modelo como Markdown: una etiqueta por párrafo, sin la respuesta final (va aparte).
    Es la misma regla que frontend/src/app/shared/steps.ts."""
    out: list[str] = []
    skipping = False
    for line in _INLINE_LABEL.sub(r"\n\1", raw or "").split("\n"):
        m = _LABEL.match(line)
        if m:
            label, body = m.group(1).strip(), m.group(2).strip()
            if _ANSWER_LABEL.match(label):
                skipping = True
                continue
            skipping = False
            out.append(f"**{label}:** {body}")
            continue
        if skipping or not line.strip():
            continue
        if re.search(r"\\boxed\s*\{", line) and out:
            continue  # "$\boxed{5}$" suelto al final
        if out:
            out[-1] += "  \n" + line.strip()
        else:
            out.append(line.strip())
    return "\n\n".join(out) if out else (raw or "")


def answer_markdown(answer: str | None, t: dict) -> str:
    if not answer:
        return f"*{t['no_answer']}*"
    a = answer.strip()
    if a.startswith("$"):
        return f"## {a}"
    if re.search(r"\\[a-zA-Z]|\^|_\{|=|/", a):
        return f"## ${a}$"
    return f"## {html.escape(a)}"


def badge_html(status: str, note: str | None, sympy_answer: str | None, device: str, t: dict) -> str:
    kind, icon = BADGE.get(status, ("info", "ℹ"))
    label = t["verify"].get(status, status)
    parts = [f'<div class="vmv-badge vmv-{kind}"><span class="vmv-pill">{icon} {html.escape(label)}</span>']
    if note:
        parts.append(f'<span class="vmv-note">{html.escape(note)}</span>')
    parts.append("</div>")
    if sympy_answer and status in ("verified", "mismatch"):
        parts.append(f'<div class="vmv-calc">{html.escape(t["calc"])}: <code>{html.escape(sympy_answer)}</code></div>')
    if device in ("gpu", "cpu"):
        parts.append(f'<div class="vmv-device">{html.escape(t[device])}</div>')
    return "".join(parts)


def empty_result(t: dict):
    return (f'<div class="vmv-placeholder">{html.escape(t["waiting"])}</div>', "", "")


# ---------------------------------------------------------------------------
# Acciones
# ---------------------------------------------------------------------------
def _ip(request: gr.Request | None) -> str:
    if request is None:
        return "unknown"
    fwd = request.headers.get("x-forwarded-for", "") if request.headers else ""
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


def _guard_rate(request: gr.Request | None, lang: str) -> None:
    try:
        core.guard.rate(_ip(request), lang)
    except GuardError as e:
        raise gr.Error(e.message, print_exception=False)


def on_read(image, lang: str, request: gr.Request):
    t = T[lang]
    if image is None:
        raise gr.Error(t["need_image"], print_exception=False)
    _guard_rate(request, lang)
    try:
        img = core.clean_image(image, lang)
        reading, is_math, problems = core.read(img, lang)
    except GuardError as e:
        raise gr.Error(e.message, print_exception=False)
    except Exception:  # noqa: BLE001
        log.exception("Fallo al leer")
        raise gr.Error(t["busy"], print_exception=False)
    if not is_math:
        gr.Warning(t["not_math"])
        return (gr.update(value="", visible=True), gr.update(choices=[], value=None, visible=False),
                gr.update(visible=True))
    if problems:
        return (gr.update(value=problems[0], visible=True),
                gr.update(choices=problems, value=problems[0], visible=True), gr.update(visible=True))
    return (gr.update(value=reading, visible=True), gr.update(choices=[], value=None, visible=False),
            gr.update(visible=True))


async def _solve(image, text: str, reading: str, lang: str, request: gr.Request | None):
    t = T[lang]
    _guard_rate(request, lang)
    try:
        text = await core.guard.text(text, lang)
        reading = await core.guard.text(reading, lang)
        img = core.clean_image(image, lang) if image is not None else None
    except GuardError as e:
        raise gr.Error(e.message, print_exception=False)
    if img is None and not text and not reading:
        raise gr.Error(MSG[lang]["empty"], print_exception=False)
    try:
        sol = core.solve(img, text, reading, lang)
    except Exception:  # noqa: BLE001
        log.exception("Fallo al resolver")
        raise gr.Error(t["busy"], print_exception=False)
    return (badge_html(sol.status, sol.note, sol.sympy_answer, sol.device, t),
            answer_markdown(sol.answer, t), steps_markdown(sol.steps))


async def on_solve_photo(image, reading: str, lang: str, request: gr.Request):
    t = T[lang]
    if image is None:
        raise gr.Error(t["need_image"], print_exception=False)
    if not (reading or "").strip():
        raise gr.Error(t["need_reading"], print_exception=False)
    return await _solve(image, "", reading, lang, request)


async def on_solve_text(text: str, lang: str, request: gr.Request):
    if not (text or "").strip():
        raise gr.Error(MSG[lang]["empty"], print_exception=False)
    return await _solve(None, text, "", lang, request)


def on_clear(lang: str):
    t = T[lang]
    return (None, gr.update(value="", visible=False), gr.update(choices=[], value=None, visible=False),
            gr.update(visible=False), "", *empty_result(t))


def header_html(lang: str) -> str:
    t = T[lang]
    return f"""
<div class="vmv-hero">
  <div class="vmv-brand">
    <svg viewBox="0 0 32 32" width="40" height="40" aria-hidden="true"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
      <rect width="32" height="32" rx="8" fill="url(#g)"/><path d="M9 16.5l4.5 4.5L23 11" stroke="#fff" stroke-width="3"
      fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <span>Vertex <b>Math Vision</b></span>
  </div>
  <h1>{html.escape(t["tagline"])}</h1>
  <p>{html.escape(t["sub"])}</p>
  <div class="vmv-links">
    <a class="vmv-cta" href="{html.escape(APP_URL)}" target="_blank" rel="noopener">{html.escape(t["app"])} ↗</a>
    <a href="{MODEL_URL}" target="_blank" rel="noopener">🤗 {html.escape(t["model"])}</a>
    <a href="{GGUF_URL}" target="_blank" rel="noopener">💻 {html.escape(t["offline"])}</a>
  </div>
</div>"""


def footer_md(lang: str) -> str:
    t = T[lang]
    return (f"{t['how']}\n\n🔒 {t['privacy']}\n\n⚠️ {t['disclaimer']}\n\n"
            "Made by **Vertex Coders LLC** · Qwen3-VL-2B-Instruct + QLoRA · Apache 2.0")


def on_lang(lang: str):
    t = T[lang]
    return (
        header_html(lang),
        gr.update(label=t["tab_photo"]), gr.update(label=t["tab_text"]),
        gr.update(label=t["image"]), gr.update(value=t["read"]),
        gr.update(label=t["reading"]), gr.update(label=t["pick"]), gr.update(value=t["solve_photo"]),
        gr.update(label=t["text"], placeholder=t["text_ph"]), gr.update(value=t["solve_text"]),
        gr.update(value=t["clear"]),
        gr.update(value=f"### {t['result']}"), gr.update(value=f"#### {t['steps']}"),
        gr.Dataset(samples=[[x] for x in TEXT_EXAMPLES[lang]], label=t["ex_text"]),
        footer_md(lang),
    )


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
CSS = """
.gradio-container { max-width: 1180px !important; margin: auto; }
.vmv-hero { padding: 28px 8px 8px; }
.vmv-brand { display:flex; align-items:center; gap:10px; font-size:1.15rem; font-weight:600; }
.vmv-brand b { background: linear-gradient(90deg,#22d3ee,#a855f7); -webkit-background-clip:text; background-clip:text; color:transparent; }
.vmv-hero h1 { font-size: clamp(1.8rem, 4vw, 2.8rem); line-height:1.1; margin: 18px 0 10px; font-weight: 800;
  background: linear-gradient(90deg,#0f172a 0%,#0891b2 45%,#9333ea 100%); -webkit-background-clip:text; background-clip:text; color:transparent; }
.dark .vmv-hero h1 { background-image: linear-gradient(90deg,#f8fafc 0%,#22d3ee 45%,#a855f7 100%); }
.vmv-hero p { max-width: 760px; opacity:.85; font-size:1.02rem; }
.vmv-links { display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }
.vmv-links a { padding:8px 14px; border-radius:999px; border:1px solid rgba(148,163,184,.35); text-decoration:none !important; font-weight:600; font-size:.92rem; }
.vmv-links a.vmv-cta { background:#22d3ee; color:#05202a !important; border-color:#22d3ee; }
.vmv-badge { display:flex; flex-wrap:wrap; align-items:center; gap:10px; }
.vmv-pill { padding:5px 12px; border-radius:999px; font-weight:700; font-size:.9rem; border:1px solid; white-space:nowrap; }
.vmv-ok .vmv-pill { color:#34d399; border-color:#34d39966; background:#34d3991a; }
.vmv-warn .vmv-pill { color:#fbbf24; border-color:#fbbf2466; background:#fbbf241a; }
.vmv-info .vmv-pill { color:#38bdf8; border-color:#38bdf866; background:#38bdf81a; }
.vmv-muted .vmv-pill { color:#94a3b8; border-color:#94a3b866; background:#94a3b81a; }
.vmv-note { font-size:.92rem; opacity:.85; flex:1; min-width:200px; }
.vmv-calc, .vmv-device { margin-top:8px; font-size:.85rem; opacity:.7; }
.vmv-placeholder { padding:28px; text-align:center; opacity:.6; border:1px dashed rgba(148,163,184,.4); border-radius:12px; }
#vmv-answer { border-radius:12px; padding:4px 14px; background: linear-gradient(135deg, rgba(34,211,238,.10), rgba(168,85,247,.12)); }
#vmv-steps p { margin: 0 0 10px; padding: 10px 14px; border-radius: 10px; background: rgba(148,163,184,.08); border-left: 3px solid #22d3ee; }
footer { display:none !important; }
"""

THEME = gr.themes.Soft(primary_hue="cyan", secondary_hue="purple", neutral_hue="slate",
                       font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"])

with gr.Blocks(title="Vertex Math Vision") as demo:
    lang = gr.Radio(choices=[("Español", "es"), ("English", "en")], value="es", label=T["es"]["lang"],
                    container=False, elem_id="vmv-lang")
    header = gr.HTML(header_html("es"))

    with gr.Row(equal_height=False):
        with gr.Column(scale=5):
            with gr.Tabs():
                with gr.Tab(T["es"]["tab_photo"]) as tab_photo:
                    image = gr.Image(type="pil", label=T["es"]["image"], sources=["upload", "webcam", "clipboard"],
                                     height=320, image_mode="RGB")
                    read_btn = gr.Button(T["es"]["read"], variant="secondary")
                    pick = gr.Dropdown(choices=[], label=T["es"]["pick"], visible=False, interactive=True)
                    reading = gr.Textbox(label=T["es"]["reading"], lines=2, visible=False, max_length=1000)
                    solve_photo_btn = gr.Button(T["es"]["solve_photo"], variant="primary", visible=False)
                    examples_photo = [os.path.join(EXAMPLES_DIR, f) for f in sorted(os.listdir(EXAMPLES_DIR))
                                      if f.lower().endswith((".png", ".jpg", ".jpeg"))] if os.path.isdir(EXAMPLES_DIR) else []
                    if examples_photo:
                        gr.Examples(examples=[[p] for p in examples_photo], inputs=[image], label=T["es"]["ex_photo"])
                with gr.Tab(T["es"]["tab_text"]) as tab_text:
                    text = gr.Textbox(label=T["es"]["text"], placeholder=T["es"]["text_ph"], lines=3, max_length=1000)
                    solve_text_btn = gr.Button(T["es"]["solve_text"], variant="primary")
                    ex_text = gr.Examples(examples=[[x] for x in TEXT_EXAMPLES["es"]], inputs=[text],
                                          label=T["es"]["ex_text"])
            clear_btn = gr.Button(T["es"]["clear"], variant="secondary", size="sm")

        with gr.Column(scale=6):
            result_title = gr.Markdown(f"### {T['es']['result']}")
            status = gr.HTML(empty_result(T["es"])[0])
            answer = gr.Markdown("", elem_id="vmv-answer", latex_delimiters=LATEX)
            steps_title = gr.Markdown(f"#### {T['es']['steps']}")
            steps = gr.Markdown("", elem_id="vmv-steps", latex_delimiters=LATEX)

    footer = gr.Markdown(footer_md("es"))

    # Eventos
    pick.change(lambda p: p or "", inputs=pick, outputs=reading)
    image.change(lambda: (gr.update(value="", visible=False), gr.update(choices=[], value=None, visible=False),
                          gr.update(visible=False)),
                 outputs=[reading, pick, solve_photo_btn])
    read_btn.click(on_read, inputs=[image, lang], outputs=[reading, pick, solve_photo_btn],
                   concurrency_limit=2, api_name=False)
    solve_photo_btn.click(on_solve_photo, inputs=[image, reading, lang], outputs=[status, answer, steps],
                          concurrency_limit=2, api_name=False)
    solve_text_btn.click(on_solve_text, inputs=[text, lang], outputs=[status, answer, steps],
                         concurrency_limit=2, api_name=False)
    text.submit(on_solve_text, inputs=[text, lang], outputs=[status, answer, steps],
                concurrency_limit=2, api_name=False)
    clear_btn.click(on_clear, inputs=lang, outputs=[image, reading, pick, solve_photo_btn, text, status, answer, steps],
                    api_name=False)
    lang.change(on_lang, inputs=lang,
                outputs=[header, tab_photo, tab_text, image, read_btn, reading, pick, solve_photo_btn, text,
                         solve_text_btn, clear_btn, result_title, steps_title, ex_text.dataset, footer],
                api_name=False)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch(theme=THEME, css=CSS)
