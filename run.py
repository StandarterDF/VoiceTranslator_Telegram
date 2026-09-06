import os
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))

import config as cfg
import VoiceTranslator as vt


def main():
    parser = argparse.ArgumentParser(
        description="VoiceTranslator Telegram Bot — CLI-запуск"
    )
    parser.add_argument(
        "--provider",
        choices=["vosk", "google", "faster_whisper"],
        default=None,
        help="STT-провайдер: vosk, google, faster_whisper (по умолчанию из .env)",
    )
    parser.add_argument(
        "--size",
        choices=["tiny", "base", "small", "large-v3-turbo"],
        default=None,
        help="Размер Whisper-модели (только для faster_whisper, по умолчанию из .env)",
    )
    parser.add_argument(
        "--llm",
        choices=["on", "off"],
        default=None,
        help="LLM-постпроцессинг (коррекция пунктуации): on / off (по умолчанию из .env)",
    )

    args = parser.parse_args()

    # Применяем аргументы CLI поверх значений из .env
    if args.provider is not None:
        vt.STT_PROVIDER = args.provider
    if args.size is not None:
        vt.WHISPER_MODEL_SIZE = args.size
        vt.WHISPER_MODEL_PATH = f"models/whisper-{args.size}"
    if args.llm is not None:
        vt.LLM_POSTPROCESS = args.llm == "on"

    # Читаемый вывод конфигурации
    model_label = vt.WHISPER_MODEL_SIZE if vt.STT_PROVIDER == "faster_whisper" else "--"
    llm_status = "ВКЛ" if vt.LLM_POSTPROCESS else "ВЫКЛ"

    print(f"\n=== VoiceTranslator ===")
    print(f"  STT-провайдер : {vt.STT_PROVIDER}")
    print(f"  Модель        : {model_label}")
    print(f"  LLM-постпроцессинг: {llm_status}")
    print(f"  Proкси        : {cfg.PROXY_STRING or 'нет'}")
    print(f"  Device        : {cfg.WHISPER_DEVICE}")
    print()

    # Запускаем бота
    vt.start_polling()


if __name__ == "__main__":
    main()
