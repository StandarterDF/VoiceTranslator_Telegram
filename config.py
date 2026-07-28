import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OpenAI-compatible API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://192.168.0.250:1234/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "mistral-medium-latest")

# Proxy
PROXY_STRING = os.getenv("PROXY_STRING", "")
