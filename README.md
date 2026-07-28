# VoiceTranslator TelegramBot

> Telegram-бот для транскрипции голосовых сообщений в текст. Использует Faster Whisper (CTranslate2) локально на GPU/CPU.

## Описание

Бот принимает голосовые сообщения в Telegram, распознаёт речь через выбранный STT-провайдер (Vosk / Google / Faster Whisper) и при необходимости исправляет пунктуацию через OpenAI-совместимый API. При старте доступен интерактивный выбор модели.

**Особенности:**
- CUDA / CPU авто-детект, float16 на GPU
- Интерактивный выбор модели при каждом запуске
- Умное разбитие длинных сообщений (>4096 символов) по границе предложений
- Модели хранятся локально в `models/` — без постоянных скачиваний

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

Скопируйте `.env.example` в `.env` и укажите свои параметры.

### Запуск

```bash
start.bat
# или
python VoiceTranslator.py
```

При запуске появится меню выбора STT:

```
=== VoiceTranslator ===
Выберите режим распознавания речи:
  1 — Vosk (локально, слабое качество)
  2 — Google Speech Recognition (онлайн, + коррекция пунктуации)
  3 — Whisper tiny (локально, ~75MB)
  4 — Whisper base (локально, ~150MB)
  5 — Whisper small (локально, ~500MB)
  6 — Whisper large-v3-turbo (локально, ~1.2GB, лучшее качество)
  Enter — оставить текущий: faster_whisper / small
>>>
```

## Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен Telegram-бота (получить у @BotFather) |
| `OPENAI_API_KEY` | — | API-ключ для OpenAI-совместимого API (только для `google` STT) |
| `OPENAI_BASE_URL` | `http://192.168.0.250:1234/v1` | Базовый URL API |
| `OPENAI_MODEL` | `mistral-medium-latest` | Модель для коррекции пунктуации |
| `PROXY_STRING` | — | SOCKS5/HTTP прокси для Telegram API |
| `STT_PROVIDER` | `faster_whisper` | Провайдер: `google`, `vosk`, `faster_whisper` |
| `VOSK_MODEL_PATH` | `models/vosk-model-small-ru-0.22` | Путь к модели Vosk |
| `WHISPER_MODEL_SIZE` | `small` | Размер модели: `tiny`, `base`, `small`, `large-v3-turbo` |

## Speech-to-Text провайдеры

| Провайдер | Тип | Русский | Требует API-ключ | Интернет | Качество |
|-----------|-----|---------|-----------------|----------|----------|
| `google` | Google Speech Recognition | ✓ | нет | требуется | среднее |
| `vosk` | Vosk (локально) | ✓ | нет | не требуется | низкое |
| `faster_whisper` | CTranslate2 Whisper | ✓ | нет | не требуется | **отличное** |

### Whisper модели

| Размер | Вес | GPU | CPU |
|--------|-----|-----|-----|
| `tiny` | ~75 MB | ✓ | ✓ |
| `base` | ~150 MB | ✓ | ✓ |
| `small` | ~500 MB | ✓ | ✓ |
| `large-v3-turbo` | ~1.2 GB | ✓ | ± |

### GPU ускорение

При наличии CUDA-совместимой видеокарты детект происходит автоматически через `nvcuda.dll`. Модель загружается с `device="cuda"` и `compute_type="float16"` для максимальной производительности. На CPU используется `compute_type="auto"`.

## Использование

1. Напишите боту `/start`
2. Отправьте голосовое сообщение
3. Бот вернёт распознанный текст

В групповых чатах бот обрабатывает голосовые сообщения:
- в личных сообщениях с ботом
- при ответе на сообщение бота
- при упоминании бота в подписи к голосовому (`@BotUsername`)

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
