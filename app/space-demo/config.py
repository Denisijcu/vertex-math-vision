"""Configuración del backend. Todo sale del archivo .env (ver .env.example); nada va escrito a mano en el código."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # Orígenes del frontend que pueden llamar a la API, separados por comas.
    ALLOWED_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"

    # Servidor del modelo, compatible con OpenAI (LM Studio en local).
    LLM_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LLM_MODEL: str = "vertex-math-vision-v2"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_S: float = 120.0          # un modelo de visión en CPU puede tardar
    LLM_MAX_TOKENS: int = 900
    LLM_TEMPERATURE: float = 0.2

    # Portero (V-SRT) opcional.
    PORTERO_URL: str = ""

    # Reportes de error: solo texto, nunca fotos.
    REPORT_LOG_PATH: str = str(BASE_DIR / "data" / "reports.jsonl")

    # Límites de entrada.
    TEXT_MAX_CHARS: int = 1000
    IMAGE_MAX_MB: float = 8.0
    IMAGE_MAX_SIDE: int = 1280
    RATE_LIMIT_PER_MIN: int = 10

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
