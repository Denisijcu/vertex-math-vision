"""Modelos de petición y respuesta. El frontend Angular usa exactamente estos contratos."""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Lang = Literal["es", "en"]
Verification = Literal["verified", "mismatch", "ill_posed", "steps_ok", "steps_wrong", "unverified", "not_math"]
Source = Literal["llm", "fallback"]


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    llm: Literal["up", "down"]


class ReadResponse(BaseModel):
    reading: str = Field(description="Lo que el modelo leyó en la imagen, sin resolver")
    is_math: bool
    problems: list[str] = Field(default_factory=list, description="Si la foto trae varios ejercicios, uno por elemento")
    lang: Lang
    source: Source


class SolveResponse(BaseModel):
    reading: str
    steps: str
    answer: str | None
    verification: Verification
    sympy_answer: str | None = None
    note: str | None = Field(default=None, description="Explicación corta de la verificación, en el idioma del estudiante")
    lang: Lang
    source: Source


class ReportRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    reading: str | None = Field(default=None, max_length=1000)
    answer: str | None = Field(default=None, max_length=300)
    email: EmailStr | None = None
    website: str | None = None  # honeypot: si viene con valor, es un bot


class ReportResponse(BaseModel):
    ok: bool = True


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
