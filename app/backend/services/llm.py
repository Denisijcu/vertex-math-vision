"""Cliente del modelo Vertex-Math-Vision en formato OpenAI (LM Studio en local, el servidor del Space en producción).

Cada llamada es una conversación nueva: system + un solo mensaje del estudiante (imagen y/o texto).
Así se entrenó el modelo, y en LM Studio vimos que en un chat largo arrastra el idioma y la imagen anterior.
"""
import base64
import logging

import httpx

from config import Settings
from services.answers import extract_answer
from services.prompts import READ_PROMPT, SYSTEM_PROMPT, build_ask, parse_reading  # noqa: F401

log = logging.getLogger("llm")


class LLMUnavailable(Exception):
    """El servidor del modelo no respondió o devolvió algo inservible."""


class LLMClient:
    def __init__(self, settings: Settings):
        self.s = settings
        headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"} if settings.LLM_API_KEY else {}
        self.client = httpx.AsyncClient(base_url=settings.LLM_BASE_URL.rstrip("/"), headers=headers)

    async def close(self) -> None:
        await self.client.aclose()

    async def is_up(self) -> bool:
        try:
            r = await self.client.get("/models", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    async def _chat(self, content: list[dict], max_tokens: int) -> str:
        payload = {
            "model": self.s.LLM_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
            "temperature": self.s.LLM_TEMPERATURE,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            r = await self.client.post("/chat/completions", json=payload, timeout=self.s.LLM_TIMEOUT_S)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            log.warning("El modelo no respondió: %s", type(exc).__name__)
            raise LLMUnavailable from exc
        if not isinstance(text, str) or not text.strip():
            raise LLMUnavailable
        return text.strip()

    @staticmethod
    def _content(image_jpeg: bytes | None, text: str) -> list[dict]:
        parts: list[dict] = []
        if image_jpeg:
            b64 = base64.b64encode(image_jpeg).decode()
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        parts.append({"type": "text", "text": text})
        return parts

    async def read(self, image_jpeg: bytes, lang: str) -> tuple[str, bool, list[str]]:
        """Transcribe sin resolver. Devuelve (lectura, es_matemática, lista de ejercicios)."""
        raw = await self._chat(self._content(image_jpeg, READ_PROMPT[lang]), max_tokens=300)
        return parse_reading(raw)

    async def solve(self, image_jpeg: bytes | None, student_text: str, confirmed_reading: str, lang: str) -> tuple[str, str | None]:
        """Resuelve paso a paso. Devuelve (pasos, respuesta extraída de \\boxed{})."""
        ask = build_ask(student_text, confirmed_reading, lang)
        steps = await self._chat(self._content(image_jpeg, ask), max_tokens=self.s.LLM_MAX_TOKENS)
        return steps, extract_answer(steps)
