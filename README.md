# VoiceTranslator TelegramBot

> Telegram-бот для транскрипции голосовых сообщений в текст с автоматической коррекцией пунктуации через OpenAI-совместимый API.

## Описание

Бот принимает голосовые сообщения в Telegram, распознаёт речь (Google Speech Recognition или Vosk — настраивается в `.env`), затем исправляет пунктуацию через OpenAI-совместимый API (локальный или внешний). Поддерживает длинные аудиосообщения (разбивает на сегменты по 15 секунд).

## Установка

### Требования
- Python 3.10+
- pip
- FFmpeg (для обработки аудио — `pydub`)

### Установка зависимостей

```bash
git clone https://github.com/your-username/VoiceTranslator_TelegramBot
cd VoiceTranslator_TelegramBot
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
pip install -r requirements.txt
```

### Настройка

Скопируйте `.env.example` в `.env` и укажите свои параметры:

```
BOT_TOKEN=your-telegram-bot-token-here
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=http://192.168.0.250:1234/v1
OPENAI_MODEL=mistral-medium-latest
PROXY_STRING=socks5://127.0.0.1:2080
STT_PROVIDER=vosk
VOSK_MODEL_PATH=models/vosk-model-small-ru-0.22
```

### Запуск

```bash
python VoiceTranslator.py
```

## Использование

1. Напишите боту `/start`
2. Отправьте голосовое сообщение
3. Бот вернёт распознанный текст с исправленной пунктуацией

В групповых чатах бот обрабатывает голосовые сообщения:
- в личных сообщениях с ботом
- при ответе на сообщение бота
- при упоминании бота в подписи к голосовому (`@BotUsername`)

## Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен Telegram-бота (получить у @BotFather) |
| `OPENAI_API_KEY` | — | API-ключ для OpenAI-совместимого API |
| `OPENAI_BASE_URL` | `http://192.168.0.250:1234/v1` | Базовый URL API (локальный или внешний) |
| `OPENAI_MODEL` | `mistral-medium-latest` | Модель для коррекции пунктуации |
| `PROXY_STRING` | — | SOCKS5/HTTP прокси для всех внешних запросов (Telegram API, OpenAI, Google STT) |
| `STT_PROVIDER` | `google` | Провайдер распознавания речи: `google`, `vosk`, `faster_whisper` |
| `VOSK_MODEL_PATH` | `models/vosk-model-small-ru-0.22` | Путь к модели Vosk (только для STT_PROVIDER=vosk) |
| `WHISPER_MODEL_SIZE` | `small` | Размер модели Whisper: `tiny`, `base`, `small`, `large-v3-turbo` |

## Speech-to-Text провайдеры

| Провайдер | Тип | Русский | API-ключ | Интернет | Качество |
|-----------|-----|---------|----------|----------|----------|
| `google` | Google Speech Recognition | ✓ | не нужен | требуется | среднее |
| `vosk` | Vosk (локально) | ✓ | не нужен | не требуется | низкое |
| `faster_whisper` | Faster Whisper (локально, CTranslate2) | ✓ | не нужен | не требуется (модель кешируется) | **отличное** |

**Рекомендация:** `faster_whisper` с `tiny` — ~75MB, отличное качество, работает на CPU.

## Зависимости

```
pyTelegramBotAPI
SpeechRecognition
pydub
python-dotenv
requests[socks]
vosk
faster-whisper
```

## Лицензия

MIT
