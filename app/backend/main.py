"""API de Vertex Math Vision (FastAPI).

Rutas:
  GET  /health   estado de la API y del modelo
  POST /read     transcribe la foto sin resolverla (paso de confirmación)
  POST /solve    resuelve paso a paso y verifica con SymPy
  POST /report   "reportar un error del tutor" (solo texto; nunca se guarda la foto)
"""
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from models import ErrorResponse, Health, ReadResponse, ReportRequest, ReportResponse, SolveResponse
from services import verify
from services.guard import MSG, Guard, GuardError
from services.llm import LLMClient, LLMUnavailable

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

settings = get_settings()
guard = Guard(settings)

FALLBACK = {
    "es": "El tutor está despertando o muy ocupado. Prueba otra vez en un minuto.",
    "en": "The tutor is waking up or very busy. Please try again in a minute.",
}
NOT_MATH = {
    "es": "No veo un ejercicio de matemáticas en esta foto. Prueba con una foto más clara del ejercicio.",
    "en": "I can't see a math exercise in this photo. Try a clearer photo of the exercise.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = LLMClient(settings)
    yield
    await app.state.llm.close()


app = FastAPI(title="Vertex Math Vision API", version="1.0.0", lifespan=lifespan,
              responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse},
                         415: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(GuardError)
async def guard_error(_: Request, exc: GuardError):
    return _error(exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    log.info("Petición inválida: %s", exc.errors()[:2])
    return _error(422, "INVALID_REQUEST", "Datos de la petición no válidos. / Invalid request data.")


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Error no controlado")
    return _error(500, "INTERNAL_ERROR", "Algo falló en el servidor. Inténtalo de nuevo. / Something went wrong.")


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


async def _image(upload: UploadFile | None, lang: str) -> bytes | None:
    if upload is None:
        return None
    raw = await upload.read(int(settings.IMAGE_MAX_MB * 1024 * 1024) + 1)
    if not raw:
        return None
    return guard.image(raw, lang)


@app.get("/health", response_model=Health)
async def health(request: Request):
    return Health(llm="up" if await request.app.state.llm.is_up() else "down")


@app.post("/read", response_model=ReadResponse)
async def read(request: Request, image: UploadFile = File(...), lang: Literal["es", "en"] = Form("es")):
    guard.rate(client_ip(request), lang)
    img = await _image(image, lang)
    if img is None:
        raise GuardError("EMPTY_INPUT", MSG[lang]["empty"])
    try:
        reading, is_math, problems = await request.app.state.llm.read(img, lang)
    except LLMUnavailable:
        return ReadResponse(reading="", is_math=False, problems=[], lang=lang, source="fallback")
    return ReadResponse(reading=reading, is_math=is_math, problems=problems, lang=lang, source="llm")


@app.post("/solve", response_model=SolveResponse)
async def solve(
    request: Request,
    image: UploadFile | None = File(None),
    text: str = Form(""),
    reading: str = Form(""),
    lang: Literal["es", "en"] = Form("es"),
):
    guard.rate(client_ip(request), lang)
    text = await guard.text(text, lang)
    reading = await guard.text(reading, lang)
    img = await _image(image, lang)
    if img is None and not text and not reading:
        raise GuardError("EMPTY_INPUT", MSG[lang]["empty"])

    llm: LLMClient = request.app.state.llm
    try:
        if img is not None and not reading:
            # No pasó por /read (o lo saltó): leemos primero para poder verificar.
            reading, is_math, _ = await llm.read(img, lang)
            if not is_math and not text:
                return SolveResponse(reading="", steps=NOT_MATH[lang], answer=None, verification="not_math",
                                     note=NOT_MATH[lang], lang=lang, source="llm")
        steps, answer = await llm.solve(img, text, reading, lang)
    except LLMUnavailable:
        return SolveResponse(reading=reading, steps=FALLBACK[lang], answer=None, verification="unverified",
                             note=FALLBACK[lang], lang=lang, source="fallback")

    problem = reading or text
    result = verify.check(problem, answer, lang, steps)
    return SolveResponse(reading=problem, steps=steps, answer=answer, verification=result.status,
                         sympy_answer=result.sympy_answer, note=result.note, lang=lang, source="llm")


@app.post("/report", response_model=ReportResponse)
async def report(body: ReportRequest, request: Request):
    if body.website:  # honeypot: un humano nunca lo rellena
        log.info("Reporte descartado por honeypot")
        return ReportResponse()
    guard.rate(client_ip(request), "es")
    path = Path(settings.REPORT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message": body.message.strip(),
        "reading": (body.reading or "").strip() or None,
        "answer": (body.answer or "").strip() or None,
        "email": body.email,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ReportResponse()
