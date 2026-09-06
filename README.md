# VoiceTranslator TelegramBot

> Telegram-бот для транскрипции голосовых сообщений в текст. Использует Faster Whisper (CTranslate2) локально на GPU/CPU.

## Описание

Бот принимает голосовые сообщения в Telegram, распознаёт речь через выбранный STT-провайдер (Vosk / Google / Faster Whisper) и при необходимости исправляет пунктуацию через OpenAI-совместимый API. Управление LLM-постпроцессингом (коррекцией пунктуации) доступно для ЛЮБОГО провайдера через флаг `--llm` или переменную `LLM_POSTPROCESS`.

**Особенности:**
- CUDA / CPU авто-детект, float16 на GPU
- Управление LLM-постпроцессингом для любого STT-провайдера
- Умное разбитие длинных сообщений (>4096 символов) по границе предложений
- Модели хранятся локально в `models/` — без постоянных скачиваний
- Запуск через TUI, CMD или прямой вызов скрипта

## Установка

### Требования

- Python 3.10+
- pip
- FFmpeg (для обработки аудио — `pydub`)

### Автоматическая установка

Запустите скрипт установки — он создаст виртуальное окружение, установит зависимости и скопирует `.env.example` в `.env` (если `.env` ещё нет).

**Windows:**
```
setup.bat
```

**Linux / macOS:**
```bash
chmod +x setup.sh
bash setup.sh
```

### Ручная установка (альтернатива)

```bash
git clone https://github.com/your-username/VoiceTranslator_TelegramBot
cd VoiceTranslator_TelegramBot
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
pip install -r requirements.txt
```

## Настройка (.env)

Скопируйте `.env.example` в `.env` (или используйте `setup.bat` / `setup.sh`) и укажите свои параметры.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен Telegram-бота (получить у @BotFather) |
| `OPENAI_API_KEY` | — | API-ключ для OpenAI-совместимого API (нужен для коррекции пунктуации, если включена) |
| `OPENAI_BASE_URL` | `http://192.168.0.250:1234/v1` | Базовый URL API |
| `OPENAI_MODEL` | `mistral-medium-latest` | Модель для коррекции пунктуации |
| `PROXY_STRING` | — | SOCKS5/HTTP прокси для Telegram API |
| `STT_PROVIDER` | `faster_whisper` | Провайдер: `google`, `vosk`, `faster_whisper` |
| `VOSK_MODEL_PATH` | `models/vosk-model-small-ru-0.22` | Путь к модели Vosk |
| `WHISPER_MODEL_SIZE` | `small` | Размер модели: `tiny`, `base`, `small`, `large-v3-turbo` |
| `LLM_POSTPROCESS` | `off` | Включить LLM-постпроцессинг (коррекцию пунктуации): `on`, `off` |

## Запуск

### Через start.bat (Windows)

```
start.bat
```

Откроется меню выбора режима запуска:

1. **TUI-интерфейс** — рекомендуемый способ. Интерактивный терминальный UI на базе Textual.
2. **CMD** — выбор модели и LLM-постпроцессинга прямо в консоли.

### TUI

```bash
python tui_app.py
```

TUI построен на фреймворке [Textual](https://textual.textualize.io/) и предоставляет:
- Окно выбора STT-провайдера и модели при запуске (F1 — смена в любое время)
- Панель логов с цветовой раскраской (ошибки, транскрипции, статус)
- Статистика: провайдер, модель, устройство (GPU/CPU), количество сообщений и ошибок, uptime
- Горячие клавиши: `F1` — выбор модели, `F3` — перезапуск бота, `F5` — очистка лога, `Ctrl+C` — выход

### CLI (run.py)

Файл `run.py` — CLI-точка входа для запуска бота без интерактивного TUI.

| Аргумент | Допустимые значения | По умолчанию | Описание |
|---|---|---|---|
| `--provider` | `vosk`, `google`, `faster_whisper` | из `.env` | STT-провайдер |
| `--size` | `tiny`, `base`, `small`, `large-v3-turbo` | из `.env` | Размер Whisper-модели |
| `--llm` | `on`, `off` | из `.env` | Включить LLM-постпроцессинг |

**Примеры:**

```bash
# Whisper локально с размером small
python run.py --provider faster_whisper --size small

# Google + LLM-постпроцессинг
python run.py --provider google --llm on

# Vosk без коррекции
python run.py --provider vosk --llm off

# По умолчанию из .env
python run.py
```

**Важно:** `--llm` включает коррекцию пунктуации через LLM-модель для **любого** STT-провайдера (раньше была доступна только для `google`).

## Конфигурация (.env)

### Speech-to-Text провайдеры

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
textual>=0.41.0
```

## Лицензия

MIT
