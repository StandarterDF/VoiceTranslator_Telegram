import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("config")

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OpenAI-compatible API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://192.168.0.250:1234/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "mistral-medium-latest")

# Proxy
PROXY_STRING = os.getenv("PROXY_STRING", "")
PROXY_SCHEME = PROXY_STRING.split("://")[0] if "://" in PROXY_STRING else ""
PROXY_NETLOC = PROXY_STRING.split("://", 1)[1] if "://" in PROXY_STRING else ""
IS_SOCKS = PROXY_SCHEME.startswith("socks")

# Speech-to-Text
# google          — Google Speech Recognition (онлайн, бесплатно)
# vosk            — Vosk (локально, без интернета)
# faster_whisper  — Faster Whisper (локально, CTranslate2, наилучшее качество)
STT_PROVIDER = os.getenv("STT_PROVIDER", "google")
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-ru-0.22")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_MODEL_PATH = f"models/whisper-{WHISPER_MODEL_SIZE}"

import ctypes

try:
    ctypes.CDLL("nvcuda.dll")
    WHISPER_DEVICE = "cuda"
    WHISPER_COMPUTE = "float16"
except OSError:
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE = "auto"

# Кто может пользоваться ботом (ChatID через запятую). Пусто = бот закрыт для всех.
ALLOWED_CHAT_IDS = [
    int(x.strip())
    for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
    if x.strip() and x.strip().lstrip("-").isdigit()
]

# LLM постпроцессинг (коррекция пунктуации), по умолчанию выключен
LLM_POSTPROCESS = os.getenv("LLM_POSTPROCESS", "off").lower() in (
    "1",
    "true",
    "yes",
    "on",
)


# Режим "мышления" LLM (аналог reasoning_effort из AILibreTranslater).
# off / none / пусто -> мышление отключено; low / high / max -> включено.
def _parse_reasoning_effort(value: str | None) -> str | None:
    if value is None or value.strip().lower() in ("", "off", "none"):
        return None
    return value


LLM_REASONING_EFFORT = _parse_reasoning_effort(os.getenv("LLM_REASONING_EFFORT", "off"))

# Тип API: "deepseek" — нативный DeepSeek (top-level "thinking"),
# "openai" — OpenAI-совместимый (reasoning_effort).
# Если не задан явно — определяется автоматически по OPENAI_BASE_URL.
LLM_API_TYPE = os.getenv("LLM_API_TYPE", "").strip().lower()
if LLM_API_TYPE not in ("openai", "deepseek"):
    LLM_API_TYPE = "deepseek" if "deepseek" in OPENAI_BASE_URL.lower() else "openai"

# HTTP health-эндпоинт для UptimeKuma и т.п.
HEALTH_ENABLED = os.getenv("HEALTH_ENABLED", "on").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
HEALTH_HOST = os.getenv("HEALTH_HOST", "0.0.0.0")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))


def get_proxy_dict() -> dict | None:
    if not PROXY_STRING:
        return None
    return {"http": PROXY_STRING, "https": PROXY_STRING}


def check_proxy_connection() -> bool:
    if not PROXY_STRING:
        log.info("No proxy configured, using direct connections")
        return True
    try:
        from urllib.parse import urlparse
        import socket

        parsed = urlparse(PROXY_STRING)
        host = parsed.hostname
        port = parsed.port or 2080
        with socket.create_connection((host, port), timeout=5):
            log.info("Proxy connection OK: %s (%s)", PROXY_STRING, PROXY_SCHEME)
            return True
    except Exception as e:
        log.warning("Proxy connection failed (%s), will use direct connections", e)
        return False
