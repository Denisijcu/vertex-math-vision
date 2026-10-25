"""Guardrails de entrada: texto, imagen, rate limit e intentos de inyección. Portero (V-SRT) opcional."""
import io
import logging
import re
import time
import unicodedata
from collections import defaultdict, deque

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from config import Settings

log = logging.getLogger("guard")

Image.MAX_IMAGE_PIXELS = 40_000_000  # una foto de móvil cabe de sobra; una "bomba" de píxeles no

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

INJECTION_PATTERNS = [
    r"ignor(a|e|ar)\s+(todas\s+)?(las\s+|tus\s+|the\s+|your\s+|all\s+)?(instrucciones|instructions|reglas|rules)",
    r"olvida\s+(tus|las)\s+(instrucciones|reglas)",
    r"forget\s+(your|all|the)\s+(instructions|rules)",
    r"system\s*prompt",
    r"prompt\s+del\s+sistema",
    r"(act|act[uú]a)\s+(as|como)\s+(si|if|un|a)\b",
    r"jailbreak",
    r"developer\s+mode|modo\s+desarrollador",
    r"<\|im_start\|>|<\|im_end\|>",
]
_INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


class GuardError(Exception):
    """Entrada rechazada. `code` y `status` van tal cual al cliente; `message` está en el idioma del estudiante."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


MSG = {
    "es": {
        "too_long": "El texto es demasiado largo. Escribe solo el ejercicio.",
        "injection": "Solo puedo ayudarte con ejercicios de matemáticas.",
        "rate": "Has enviado muchos ejercicios seguidos. Espera un minuto y vuelve a intentarlo.",
        "image_big": "La foto es demasiado grande. Prueba con una de menos de {mb:.0f} MB.",
        "image_bad": "No pude abrir la imagen. Usa una foto JPG, PNG o WEBP.",
        "empty": "Envía una foto del ejercicio o escríbelo.",
    },
    "en": {
        "too_long": "The text is too long. Please write only the exercise.",
        "injection": "I can only help with math exercises.",
        "rate": "You have sent many exercises in a row. Wait a minute and try again.",
        "image_big": "The photo is too large. Try one under {mb:.0f} MB.",
        "image_bad": "I couldn't open the image. Please use a JPG, PNG or WEBP photo.",
        "empty": "Send a photo of the exercise or type it.",
    },
}


def clean_text(text: str | None) -> str:
    """Quita caracteres de control (salvo saltos de línea) y espacios sobrantes."""
    if not text:
        return ""
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c)[0] != "C")
    return text.strip()


class RateLimiter:
    """Ventana deslizante de 60 s por IP, en memoria. Suficiente para un solo proceso (el Space)."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


class Guard:
    def __init__(self, settings: Settings):
        self.s = settings
        self.limiter = RateLimiter(settings.RATE_LIMIT_PER_MIN)

    def rate(self, ip: str, lang: str) -> None:
        if not self.limiter.check(ip):
            raise GuardError("RATE_LIMITED", MSG[lang]["rate"], 429)

    async def text(self, text: str | None, lang: str) -> str:
        text = clean_text(text)
        if len(text) > self.s.TEXT_MAX_CHARS:
            raise GuardError("TEXT_TOO_LONG", MSG[lang]["too_long"])
        if text and _INJECTION.search(text):
            raise GuardError("MESSAGE_REJECTED", MSG[lang]["injection"])
        if text and self.s.PORTERO_URL:
            await self._portero(text, lang)
        return text

    async def _portero(self, text: str, lang: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(f"{self.s.PORTERO_URL.rstrip('/')}/check", json={"text": text})
                r.raise_for_status()
                data = r.json()
        except Exception as exc:  # el Portero caído no tumba la app: queda la validación local
            log.warning("Portero no disponible (%s); solo validación local", type(exc).__name__)
            return
        if not data.get("allowed", True):
            log.info("Portero rechazó un mensaje: %s", data.get("reason"))
            raise GuardError("MESSAGE_REJECTED", MSG[lang]["injection"])

    def image(self, raw: bytes, lang: str) -> bytes:
        """Valida la imagen y la devuelve como JPEG limpio: girada según EXIF, sin metadatos
        (ni ubicación GPS) y con el lado mayor limitado a IMAGE_MAX_SIDE."""
        if len(raw) > self.s.IMAGE_MAX_MB * 1024 * 1024:
            raise GuardError("IMAGE_TOO_LARGE", MSG[lang]["image_big"].format(mb=self.s.IMAGE_MAX_MB), 413)
        try:
            img = Image.open(io.BytesIO(raw))
            if img.format not in ALLOWED_FORMATS:
                raise GuardError("IMAGE_UNSUPPORTED", MSG[lang]["image_bad"], 415)
            img.load()
        except GuardError:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
            raise GuardError("IMAGE_UNSUPPORTED", MSG[lang]["image_bad"], 415)
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((self.s.IMAGE_MAX_SIDE, self.s.IMAGE_MAX_SIDE), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)  # se guarda sin EXIF
        return out.getvalue()
