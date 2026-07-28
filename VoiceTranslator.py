import os
import logging
import telebot
import speech_recognition as sr
from speech_recognition import Recognizer, AudioFile
from pydub import AudioSegment
import datetime
import requests
import json
import time

from config import BOT_TOKEN, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, PROXY_STRING

# Создаем папку logs/, если её нет
os.makedirs("logs", exist_ok=True)

# Настройка логирования
log_filename = f"logs/{os.path.basename(__file__).replace('.py', '')}_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем FileHandler
handler = logging.FileHandler(log_filename, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class OpenAIClient:
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.base_url = OPENAI_BASE_URL

    def correct_punctuation(self, text):
        try:
            logger.info(f"Отправка запроса к OpenAI API для коррекции текста: {text[:50]}...")
            logger.info(f"Параметры запроса: model=mistral-medium-latest, temperature=0.2")

            # Логирование запроса
            request_data = {
                "model": "mistral-medium-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": """Вы редактор текста. Ваша задача — добавить правильную пунктуацию и форматирование к входному тексту, строго сохраняя:
                            полную длину текста (ничего не удалять и не добавлять по смыслу);
                            структуру предложений, за исключением необходимых знаков препинания.
                            Не выводи ничего, кроме изменённого текста. Никаких пояснений, комментариев или дополнительного форматирования, кроме исправления пунктуации и расстановки пробелов по правилам русского языка.
                            Текст для обработки:
                        """
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }
            logger.info(f"Данные запроса: {request_data}")

            # Отправка запроса через requests
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Accept-Encoding": "identity"  # Отключаем gzip-кодировку
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(request_data)
            )
            
            logger.info(f"Получен ответ от сервера. Статус: {response.status_code}")
            logger.info(f"Заголовки ответа: {response.headers}")
            logger.info(f"Полный ответ от сервера: {response.text}")
            
            # Проверка успешности ответа
            if response.status_code == 503:
                logger.error("Сервер временно недоступен (503). Повторная попытка через 2 секунды...")
                time.sleep(2)
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(request_data),
                    proxies=proxies
                )
                logger.info(f"Повторный запрос. Статус: {response.status_code}")
                logger.info(f"Полный ответ от сервера: {response.text}")
                
            if response.status_code != 200:
                logger.error(f"Ошибка сервера: {response.status_code}")
                return text
            
            # Парсинг ответа
            try:
                response_json = response.json()
                logger.info(f"Ответ в формате JSON: {response_json}")
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON: {str(e)}")
                return text
            
            # Проверка наличия choices
            if "choices" not in response_json:
                logger.error("Ответ от API не содержит поле 'choices'")
                return text
            
            # Проверка, что choices не пустой
            if not response_json["choices"] or len(response_json["choices"]) == 0:
                logger.error("OpenAI API вернул пустой ответ")
                return text
            
            # Проверка наличия message и content
            if "message" not in response_json["choices"][0] or "content" not in response_json["choices"][0]["message"]:
                logger.error("Ответ от API не содержит message или content")
                return text
            
            corrected_text = response_json["choices"][0]["message"]["content"]
            logger.info(f"Получен исправленный текст: {corrected_text[:50]}...")
            return corrected_text
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI API: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return text

# Инициализация бота
API_TOKEN = BOT_TOKEN

# Настройка прокси, если указана PROXY_STRING
if PROXY_STRING:
    proxies = {
        "http": PROXY_STRING,
        "https": PROXY_STRING
    }
    logger.info(f"Бот настроен для работы через прокси: {PROXY_STRING}")
else:
    proxies = None
    logger.info("Бот работает без прокси")

# Конфигурация OpenAI API
openai_client = OpenAIClient()

# Настройка прокси для Telegram-бота
try:
    if PROXY_STRING:
        import telebot.apihelper
        telebot.apihelper.proxy = {'https': PROXY_STRING}
        bot = telebot.TeleBot(API_TOKEN)
        logger.info(f"Бот настроен для работы через прокси: {PROXY_STRING}")
    else:
        bot = telebot.TeleBot(API_TOKEN)
        logger.info("Бот работает без прокси")
except Exception as e:
    logger.error(f"Ошибка настройки прокси для Telegram-бота: {str(e)}")
    logger.info("Бот будет работать без прокси")
    bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'Привет! Отправьте голосовое сообщение для транскрипции.')

def convert_ogg_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="wav")


def split_audio_file(input_path, output_dir, segment_length_ms=60000):
    """
    Разбивает аудиофайл на сегменты заданной длины.
    
    Args:
        input_path: Путь к исходному аудиофайлу.
        output_dir: Директория для сохранения сегментов.
        segment_length_ms: Длина каждого сегмента в миллисекундах (по умолчанию 60 секунд).
    
    Returns:
        Список путей к сегментам.
    """
    audio = AudioSegment.from_file(input_path)
    segments = []
    
    # Создаем директорию для сегментов, если ее нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Разбиваем аудио на сегменты
    for i, chunk in enumerate(audio[::segment_length_ms]):
        segment_path = os.path.join(output_dir, f"segment_{i}.wav")
        chunk.export(segment_path, format="wav")
        segments.append(segment_path)
    
    return segments

def transcribe_audio(file_path, max_retries=3):
    logger.info(f"Начало транскрипции: {file_path}")
    for attempt in range(max_retries):
        try:
            with AudioFile(file_path) as source:
                logger.info(f"Загрузка аудио файла: {file_path}")
                audio = recognizer.record(source)
                logger.info(f"Аудио файл загружен, начало распознавания (попытка {attempt + 1}/{max_retries})")
            
            # Пробуем распознать речь с тайм-аутом
            try:
                # Устанавливаем прокси для запросов к Google Speech Recognition
                import os
                if PROXY_STRING:
                    os.environ['HTTP_PROXY'] = PROXY_STRING
                    logger.info(f"Установлен прокси для SpeechRecognition: {PROXY_STRING}")
                
                # Устанавливаем тайм-аут для распознавания
                result = recognizer.recognize_google(audio, language='ru-RU', show_all=False)
                logger.info(f"Транскрипция завершена. Текст: {result[:50]}...")
                return result
            except sr.UnknownValueError:
                logger.error("Google Speech Recognition не смог распознать аудио")
                return None
            except sr.RequestError as e:
                logger.error(f"Ошибка запроса к Google Speech Recognition: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Повторная попытка через 2 секунды... (попытка {attempt + 2}/{max_retries})")
                    time.sleep(2)
                    continue
                return None
            finally:
                # Удаляем переменные окружения прокси после распознавания
                if PROXY_STRING:
                    os.environ.pop('HTTP_PROXY', None)
                    os.environ.pop('HTTPS_PROXY', None)
        except Exception as e:
            logger.error(f"Ошибка транскрипции (попытка {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Повторная попытка через 2 секунды... (попытка {attempt + 2}/{max_retries})")
                time.sleep(2)
                continue
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return None
    return None

# Инициализация распознавателя речи
recognizer = Recognizer()

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    # Проверяем, является ли сообщение ответом на сообщение бота
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id
    
    # В личных сообщениях бот всегда обрабатывает голосовые сообщения
    is_private_chat = message.chat.type == 'private'
    
    # Проверяем, упоминается ли бот в подписи к голосовому сообщению
    is_mention = False
    if hasattr(message, 'caption') and message.caption:
        is_mention = f'@{bot.get_me().username}' in message.caption
    
    # Если это не ответ на сообщение бота, не личное сообщение и не упоминание, игнорируем
    if not is_reply_to_bot and not is_private_chat and not is_mention:
        return
    
    return handle_voice_message(message)


@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Проверяем, является ли сообщение ответом на голосовое сообщение и упоминается ли бот
    if message.reply_to_message and message.reply_to_message.content_type == 'voice':
        is_mention = f'@{bot.get_me().username}' in message.text
        
        if is_mention:
            # Обрабатываем голосовое сообщение, на которое отвечают
            return handle_replied_voice(message)
    
    # Проверяем, является ли сообщение ответом на сообщение бота
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id
    
    # Если это ответ на сообщение бота, отвечаем
    if is_reply_to_bot:
        bot.reply_to(message, "Я обрабатываю только голосовые сообщения. Пожалуйста, отправьте голосовое сообщение.")


def handle_replied_voice(message):
    """Обрабатывает голосовое сообщение, на которое отвечают с упоминанием бота."""
    # Получаем голосовое сообщение, на которое отвечают
    voice_message = message.reply_to_message
    file_id = voice_message.voice.file_id
    
    new_file = bot.get_file(file_id)
    logger.info(f"Получение файла: {new_file.file_path}")

    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f'{file_id}.ogg')
    downloaded_file = bot.download_file(new_file.file_path)

    with open(file_path, 'wb') as f:
        logger.info(f"Сохраняю файл: {file_path}")
        f.write(downloaded_file)

    try:
        # Конвертация OGG в WAV
        wav_file_path = file_path.replace('.ogg', '.wav')
        convert_ogg_to_wav(file_path, wav_file_path)
        
        # Проверяем длину аудиофайла
        audio = AudioSegment.from_file(wav_file_path)
        audio_duration_ms = len(audio)
        
        if audio_duration_ms > 60000:  # Если длина больше 60 секунд
            logger.info(f"Аудиофайл слишком длинный ({audio_duration_ms / 1000} секунд). Разбиваем на части...")
            bot.reply_to(message, "Голосовое сообщение длинное. Обрабатываю по частям...")
            
            # Разбиваем аудиофайл на сегменты (15 секунд каждый)
            segments_dir = os.path.join(temp_dir, f'{file_id}_segments')
            segments = split_audio_file(wav_file_path, segments_dir, segment_length_ms=15000)
            
            # Обрабатываем каждый сегмент (только транскрипция)
            full_text = ""
            for i, segment_path in enumerate(segments):
                logger.info(f"Обработка сегмента {i + 1}/{len(segments)}: {segment_path}")
                segment_text = transcribe_audio(segment_path, max_retries=3)
                
                if segment_text is None:
                    bot.reply_to(message, f"Не удалось распознать речь в сегменте {i + 1}.")
                    continue
                
                logger.info(f"Текст сегмента {i + 1}: {segment_text[:100]}...")
                full_text += segment_text + " "
            
            # Логируем полный текст перед отправкой в нейронку
            logger.info(f"Полный текст перед коррекцией: {full_text[:200]}...")
            logger.info(f"Длина полного текста: {len(full_text)} символов")
            
            # Коррекция пунктуации для всего текста
            corrected_text = openai_client.correct_punctuation(full_text.strip())
            
            # Логируем результат коррекции
            logger.info(f"Текст после коррекции: {corrected_text[:200]}...")
            logger.info(f"Длина текста после коррекции: {len(corrected_text)} символов")
            
            # Отправляем весь текст как Markdown
            bot.reply_to(message, corrected_text, parse_mode='Markdown')
        else:
            # Транскрипция
            text = transcribe_audio(wav_file_path, max_retries=3)
            
            if text is None:
                bot.reply_to(message, "Не удалось распознать речь. Пожалуйста, попробуйте еще раз.")
                return

            # Коррекция пунктуации
            corrected_text = openai_client.correct_punctuation(text)

            # Если текст был успешно обработан нейронкой (не вернулся оригинальный текст),
            # отправляем как Markdown, иначе как обычный текст
            if corrected_text != text:
                bot.reply_to(message, corrected_text, parse_mode='Markdown')
            else:
                bot.reply_to(message, corrected_text)
    finally:
        os.remove(file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)


def handle_voice_message(message):
    file_id = message.voice.file_id
    new_file = bot.get_file(file_id)
    logger.info(f"Получение файла: {new_file.file_path}")

    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f'{file_id}.ogg')
    downloaded_file = bot.download_file(new_file.file_path)

    with open(file_path, 'wb') as f:
        logger.info(f"Сохраняю файл: {file_path}")
        f.write(downloaded_file)

    try:
        # Конвертация OGG в WAV
        wav_file_path = file_path.replace('.ogg', '.wav')
        convert_ogg_to_wav(file_path, wav_file_path)
        
        # Проверяем длину аудиофайла
        audio = AudioSegment.from_file(wav_file_path)
        audio_duration_ms = len(audio)
        
        if audio_duration_ms > 60000:  # Если длина больше 60 секунд
            logger.info(f"Аудиофайл слишком длинный ({audio_duration_ms / 1000} секунд). Разбиваем на части...")
            bot.reply_to(message, "Ваше голосовое сообщение длинное. Обрабатываю по частям...")
            
            # Разбиваем аудиофайл на сегменты (15 секунд каждый)
            segments_dir = os.path.join(temp_dir, f'{file_id}_segments')
            segments = split_audio_file(wav_file_path, segments_dir, segment_length_ms=15000)
            
            # Обрабатываем каждый сегмент (только транскрипция)
            full_text = ""
            for i, segment_path in enumerate(segments):
                logger.info(f"Обработка сегмента {i + 1}/{len(segments)}: {segment_path}")
                segment_text = transcribe_audio(segment_path, max_retries=3)
                
                if segment_text is None:
                    bot.reply_to(message, f"Не удалось распознать речь в сегменте {i + 1}.")
                    continue
                
                logger.info(f"Текст сегмента {i + 1}: {segment_text[:100]}...")
                full_text += segment_text + " "
            
            # Логируем полный текст перед отправкой в нейронку
            logger.info(f"Полный текст перед коррекцией: {full_text[:200]}...")
            logger.info(f"Длина полного текста: {len(full_text)} символов")
            
            # Коррекция пунктуации для всего текста
            corrected_text = openai_client.correct_punctuation(full_text.strip())
            
            # Логируем результат коррекции
            logger.info(f"Текст после коррекции: {corrected_text[:200]}...")
            logger.info(f"Длина текста после коррекции: {len(corrected_text)} символов")
            
            # Отправляем весь текст как Markdown
            bot.reply_to(message, corrected_text, parse_mode='Markdown')
        else:
            # Транскрипция
            text = transcribe_audio(wav_file_path, max_retries=3)
            
            if text is None:
                bot.reply_to(message, "Не удалось распознать речь. Пожалуйста, попробуйте еще раз.")
                return

            # Коррекция пунктуации
            corrected_text = openai_client.correct_punctuation(text)

            # Если текст был успешно обработан нейронкой (не вернулся оригинальный текст),
            # отправляем как Markdown, иначе как обычный текст
            if corrected_text != text:
                bot.reply_to(message, corrected_text, parse_mode='Markdown')
            else:
                bot.reply_to(message, corrected_text)
    finally:
        os.remove(file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

if __name__ == '__main__':
    logger.info("Бот запущен")
    while True:
        try:
            logger.info("Запуск бота...")
            bot.polling()
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            logger.info("Перезапуск бота через 5 секунд...")
            time.sleep(5)
