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
            log.info("Proxy connection OK: %s", PROXY_STRING)
            return True
    except Exception as e:
        log.warning("Proxy connection failed (%s), will use direct connections", e)
        return False
