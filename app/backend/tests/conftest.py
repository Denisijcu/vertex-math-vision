"""Configuración de las pruebas: sin modelo real, sin tocar data/ y con un rate limit alto."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["RATE_LIMIT_PER_MIN"] = "1000"
os.environ["REPORT_LOG_PATH"] = str(Path(tempfile.mkdtemp()) / "reports.jsonl")
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9/v1"   # puerto cerrado: el modelo "está caído"
os.environ["PORTERO_URL"] = ""
