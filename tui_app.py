import os
import sys
import queue
import threading
import logging
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))

log_queue: queue.Queue = queue.Queue()
event_queue: queue.Queue = queue.Queue()
stop_flag = threading.Event()


class QueueLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
            )
        )

    def emit(self, record):
        try:
            self.q.put(self.format(record))
        except Exception:
            pass


root_logger = logging.getLogger()
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)
root_logger.addHandler(QueueLogHandler(log_queue))
root_logger.setLevel(logging.INFO)

for name in ("telebot", "urllib3", "requests", "faster_whisper", "vosk"):
    logging.getLogger(name).setLevel(logging.WARNING)

import config as cfg

if not cfg.BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set. Copy .env.example to .env and add your token.")
    input("Press Enter to exit...")
    sys.exit(1)

import VoiceTranslator as vt

for h in root_logger.handlers[:]:
    if isinstance(h, logging.StreamHandler):
        root_logger.removeHandler(h)


PROVIDER_KEYS = {
    "1": ("vosk", None),
    "2": ("google", None),
    "3": ("faster_whisper", "tiny"),
    "4": ("faster_whisper", "base"),
    "5": ("faster_whisper", "small"),
    "6": ("faster_whisper", "large-v3-turbo"),
}

PROVIDER_LABELS = [
    ("1", "Vosk (local, low quality)"),
    ("2", "Google Speech (online, + punctuation)"),
    ("3", "Whisper tiny  (~75 MB)"),
    ("4", "Whisper base  (~150 MB)"),
    ("5", "Whisper small (~500 MB)"),
    ("6", "Whisper large-v3-turbo (~1.2 GB, best)"),
]


def fmt_provider(prov: str, size: str | None = None) -> str:
    if prov == "faster_whisper" and size:
        return f"faster-whisper / {size}"
    return prov


class BotThread:
    def __init__(self):
        self._thread: threading.Thread | None = None

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_alive:
            return
        stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0):
        stop_flag.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    def restart(self):
        event_queue.put({"type": "status", "text": "Restarting bot..."})
        self.stop()
        vt._whisper_model = None
        vt._vosk_model = None

        new_bot = vt.create_bot()
        new_bot.message_handler(content_types=["voice"])(vt.handle_voice)
        new_bot.message_handler(content_types=["text"])(vt.handle_text)
        vt.bot = new_bot

        self.start()

    def _run(self):
        event_queue.put(
            {
                "type": "status",
                "text": f"Bot running ({fmt_provider(vt.STT_PROVIDER, vt.WHISPER_MODEL_SIZE)})",
            }
        )

        vt.start_health_server()
        vt.set_polling_active(True)

        while not stop_flag.is_set():
            try:
                vt.set_health_error(None)
                vt.bot.polling(none_stop=True, interval=1, timeout=30)
            except Exception as e:
                if stop_flag.is_set():
                    break
                vt.set_health_error(f"{type(e).__name__}: {e}")
                event_queue.put({"type": "error", "text": str(e)})
                time.sleep(5)

        vt.set_polling_active(False)
        event_queue.put({"type": "status", "text": "Bot stopped"})


bot_thread = BotThread()


from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, RichLog, Static, Button, Label
from textual.screen import ModalScreen
from textual.binding import Binding


class ModelSelectScreen(ModalScreen):
    BINDINGS = [
        Binding("up", "prev_button", "", show=False),
        Binding("down", "next_button", "", show=False),
    ]

    def compose(self):
        with Vertical(id="dialog"):
            yield Label("Select speech recognition mode:", id="dlg-title")
            for key, label in PROVIDER_LABELS:
                yield Button(label, id=f"m{key}", variant="primary")
            yield Button("Use default (env)", id="cancel", variant="default")
            yield Label(
                "[dim]Up/Down or Tab — navigate | Enter — select[/dim]", id="dlg-hint"
            )

    def action_next_button(self):
        self.focus_next()

    def action_prev_button(self):
        self.focus_previous()

    def on_button_pressed(self, event):
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id.startswith("m"):
            self.dismiss(event.button.id[1:])


class StatusPanel(Static):
    pass


STATUS_ON = "[ ON ]"
STATUS_OFF = "[OFF]"
STATUS_WAIT = "[WAIT]"


class BotTUI(App):
    CSS = """
    Screen {
        background: #0a0a0a;
    }

    *:focus {
        border: solid #888 !important;
        background: #2a2a2a !important;
    }

    #sidebar {
        width: 34;
        min-width: 30;
        border: solid #333;
        padding: 0 1;
        margin: 0 1 0 0;
        background: #141414;
    }

    #main-panel {
        height: 100%;
    }

    #log-widget {
        height: 1fr;
        border: solid #333;
        background: #0a0a0a;
    }

    #status {
        height: auto;
    }

    #stats-bar {
        height: 3;
        content-align: center middle;
        border: solid #cc7000;
        background: #1a0d00;
        color: #ff8800;
        margin: 1 0 0 0;
    }

    #dialog {
        width: 56;
        height: auto;
        padding: 1 2;
        border: thick #cc7000;
        background: #141414;
    }

    #dlg-title {
        text-align: center;
        padding: 0 0 1 0;
        text-style: bold;
        color: #ff8800;
    }

    #dlg-hint {
        text-align: center;
        padding: 1 0 0 0;
        color: #666;
    }

    #dialog Button {
        margin: 1 0;
    }

    Button {
        background: #222;
        color: #d4d4d4;
        border: solid #444;
    }

    ModelSelectScreen {
        align: center middle;
    }

    Header {
        background: #1a0d00;
        color: #ff8800;
    }

    Footer {
        background: #0a0a0a;
        color: #666;
    }

    RichLog {
        scrollbar-color: #333 #0a0a0a;
        scrollbar-size: 1 1;
    }
    """

    COLORS = {
        "primary": "#cc7000",
        "secondary": "#444",
        "accent": "#ff8800",
        "surface": "#141414",
        "panel": "#1c1c1c",
        "boost": "#1a0d00",
        "background": "#0a0a0a",
        "text": "#d4d4d4",
        "text-disabled": "#666",
        "error": "#cc3333",
        "success": "#33aa33",
    }

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "select_model", "Model"),
        Binding("f5", "clear_log", "Clear log"),
        Binding("f3", "restart_bot", "Restart"),
    ]

    def __init__(self):
        super().__init__()
        self.msg_count = 0
        self.err_count = 0
        self.start_time = datetime.now()
        self.status_msg = "Waiting for selection..."
        self._bot_started = False

    def compose(self):
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield StatusPanel(id="status")
                yield Static("", id="stats-bar")
            with Vertical(id="main-panel"):
                yield RichLog(
                    id="log-widget", highlight=True, markup=True, max_lines=2000
                )
        yield Footer()

    def on_mount(self):
        self.push_screen(ModelSelectScreen(), self._on_model_selected)

    def _on_model_selected(self, key: str | None):
        if key and key in PROVIDER_KEYS:
            prov, size = PROVIDER_KEYS[key]
            vt.STT_PROVIDER = prov
            if size:
                vt.WHISPER_MODEL_SIZE = size
                vt.WHISPER_MODEL_PATH = f"models/whisper-{size}"
            label = dict(PROVIDER_LABELS).get(key, key)
            self._write_raw(f"[bold #ff8800]>> Selected: {label}[/bold #ff8800]")
        else:
            self._write_raw("[dim]Using default (env) provider[/dim]")

        self.start_time = datetime.now()
        bot_thread.start()
        self._bot_started = True
        self.set_interval(0.05, self._poll_queues)

    def _poll_queues(self):
        log = self.query_one("#log-widget", RichLog)

        while not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                self._write_log(log, msg)
            except queue.Empty:
                break

        while not event_queue.empty():
            try:
                ev = event_queue.get_nowait()
                self._handle_event(ev)
            except queue.Empty:
                break

    def _write_log(self, log: RichLog, msg: str):
        if "ERROR" in msg or "Error" in msg or "Ошибк" in msg:
            log.write(f"[#cc3333]{msg}[/#cc3333]")
        elif "WARNING" in msg or "Warning" in msg or "предупрежд" in msg.lower():
            log.write(f"[#ffaa33]{msg}[/#ffaa33]")
        elif "Транскрипция" in msg or "transcri" in msg.lower():
            log.write(f"[bold #33aa33]{msg}[/bold #33aa33]")
            if "символов" in msg:
                self.msg_count += 1
        elif (
            "Отправлено" in msg or "отправл" in msg.lower() or "коррекци" in msg.lower()
        ):
            log.write(f"[#44bbdd]{msg}[/#44bbdd]")
        elif "запущен" in msg.lower() or "running" in msg.lower():
            log.write(f"[bold #44bbdd]{msg}[/bold #44bbdd]")
        else:
            log.write(f"[#d4d4d4]{msg}[/#d4d4d4]")

        self._update_status()

    def _handle_event(self, ev: dict):
        t = ev.get("type", "")
        text = ev.get("text", "")

        if t == "status":
            self.status_msg = text
        elif t == "error":
            self.err_count += 1
            self.status_msg = f"Error: {text}"
            log = self.query_one("#log-widget", RichLog)
            log.write(f"[bold #cc3333][!] {text}[/bold #cc3333]")

        self._update_status()

    def _update_status(self):
        provider = vt.STT_PROVIDER
        model_size = vt.WHISPER_MODEL_SIZE if provider == "faster_whisper" else "--"
        device = "GPU" if cfg.WHISPER_DEVICE == "cuda" else "CPU"
        uptime = str(datetime.now() - self.start_time).split(".")[0]

        if not self._bot_started:
            icon = STATUS_WAIT
        elif (
            "running" in self.status_msg.lower() or "запущен" in self.status_msg.lower()
        ):
            icon = STATUS_ON
        elif "ошибк" in self.status_msg.lower() or "error" in self.status_msg.lower():
            icon = STATUS_OFF
        else:
            icon = STATUS_WAIT

        status = self.query_one("#status", StatusPanel)
        status.update(
            "[bold #ff8800]>>> STATUS <<<[/bold #ff8800]\n"
            "──────────────────────────\n"
            f"[bold]Provider:[/bold]  [#44bbdd]{provider}[/#44bbdd]\n"
            f"[bold]Model:[/bold]     [#44bbdd]{model_size}[/#44bbdd]\n"
            f"[bold]Device:[/bold]    [#ffaa33]{device}[/#ffaa33]\n"
            f"[bold]Messages:[/bold]  [#33aa33]{self.msg_count}[/#33aa33]\n"
            f"[bold]Errors:[/bold]    [#cc3333]{self.err_count}[/#cc3333]\n"
            f"[bold]Uptime:[/bold]    {uptime}\n"
            "──────────────────────────"
        )

        stats = self.query_one("#stats-bar", Static)
        stats.update(f"{icon}  {self.status_msg}")

    def _write_raw(self, text: str):
        log = self.query_one("#log-widget", RichLog)
        log.write(text)

    def action_select_model(self):
        def callback(key: str | None):
            if key and key in PROVIDER_KEYS:
                prov, size = PROVIDER_KEYS[key]
                vt.STT_PROVIDER = prov
                if size:
                    vt.WHISPER_MODEL_SIZE = size
                    vt.WHISPER_MODEL_PATH = f"models/whisper-{size}"

                label = dict(PROVIDER_LABELS).get(key, key)
                self._write_raw(f"[bold #ff8800]>> Selected: {label}[/bold #ff8800]")
                self._write_raw("[dim]  Press F3 to apply[/dim]")
                self._update_status()

        self.push_screen(ModelSelectScreen(), callback)

    def action_restart_bot(self):
        self._write_raw("[bold #ffaa33]>> Restarting bot...[/bold #ffaa33]")
        self.start_time = datetime.now()
        bot_thread.restart()

    def action_clear_log(self):
        self.query_one("#log-widget", RichLog).clear()


def main():
    app = BotTUI()
    app.run()


if __name__ == "__main__":
    main()
