"""Сбор и агрегация статистики обработки голосовых сообщений.

Модуль намеренно не тянет внешних зависимостей: события пишутся построчно
(JSON Lines) в ``stats/events.jsonl``, а агрегация выполняется при чтении.
Аналогичный подход используется в проекте AILibreTranslater.
"""

import datetime
import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SESSION_START = time.time()

STATS_DIR = Path(__file__).parent / "stats"
EVENTS_FILE = STATS_DIR / "events.jsonl"

_lock = threading.Lock()

# Гистограмма длительности аудио (секунды).
DURATION_BUCKETS = [
    ("0-15s", 0, 15),
    ("15-30s", 15, 30),
    ("30-60s", 30, 60),
    ("1-3m", 60, 180),
    ("3m+", 180, None),
]

# Гистограмма полного времени обработки (секунды).
LATENCY_BUCKETS = [
    ("0-2s", 0, 2),
    ("2-5s", 2, 5),
    ("5-10s", 5, 10),
    ("10-30s", 10, 30),
    ("30s+", 30, None),
]


def _ensure_stats_dir():
    STATS_DIR.mkdir(parents=True, exist_ok=True)


def log_event(
    event_type: str,
    *,
    provider: str = "",
    stt_model: str = "",
    duration_s: float | None = None,
    latency_s: float | None = None,
    stt_s: float | None = None,
    llm_s: float | None = None,
    chars_in: int = 0,
    chars_out: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    llm_used: bool = False,
    user_id: int | None = None,
    chat_type: str = "",
    preview: str = "",
    error: str | None = None,
) -> None:
    record: dict = {"ts": round(time.time(), 3), "type": event_type}
    if provider:
        record["provider"] = provider
    if stt_model:
        record["stt_model"] = stt_model
    if duration_s is not None:
        record["duration_s"] = round(duration_s, 3)
    if latency_s is not None:
        record["latency_s"] = round(latency_s, 3)
    if stt_s is not None:
        record["stt_s"] = round(stt_s, 3)
    if llm_s is not None:
        record["llm_s"] = round(llm_s, 3)
    if chars_in:
        record["chars_in"] = chars_in
    if chars_out:
        record["chars_out"] = chars_out
    if prompt_tokens:
        record["prompt_tokens"] = prompt_tokens
    if completion_tokens:
        record["completion_tokens"] = completion_tokens
    if llm_used:
        record["llm_used"] = True
    if user_id is not None:
        record["user_id"] = user_id
    if chat_type:
        record["chat_type"] = chat_type
    if preview:
        record["preview"] = preview[:80]
    if error:
        record["error"] = error[:300]
    try:
        _ensure_stats_dir()
        line = json.dumps(record, ensure_ascii=False)
        with _lock:
            with EVENTS_FILE.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        logger.debug("Stats event logged: %s", event_type)
    except OSError as e:
        logger.warning("Failed to write stats event: %s", e)


def read_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    events: list[dict] = []
    try:
        with EVENTS_FILE.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if isinstance(data, dict):
                        events.append(data)
                    else:
                        logger.warning("Skipping non-object stats line %d", line_no)
                except ValueError:
                    logger.warning("Skipping corrupt stats line %d", line_no)
    except OSError as e:
        logger.warning("Failed to read stats events: %s", e)
    return events


def _day_key(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def _local_midnight(days_back: int) -> float:
    lt = time.localtime()
    d = datetime.date(lt.tm_year, lt.tm_mon, lt.tm_mday) - datetime.timedelta(
        days=days_back
    )
    return time.mktime(d.timetuple())


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def summarize(events: list[dict]) -> dict:
    n_success = sum(1 for e in events if e.get("type") == "voice")
    n_errors = sum(1 for e in events if e.get("type") == "error")
    latencies = [e["latency_s"] for e in events if e.get("latency_s") is not None]
    durations = [e["duration_s"] for e in events if e.get("duration_s") is not None]
    stt_times = [e["stt_s"] for e in events if e.get("stt_s") is not None]
    llm_times = [e["llm_s"] for e in events if e.get("llm_s") is not None]
    llm_calls = sum(1 for e in events if e.get("llm_used"))
    total = n_success + n_errors
    return {
        "requests": total,
        "success": n_success,
        "errors": n_errors,
        "error_rate": round(n_errors / total, 4) if total else None,
        "avg_latency_s": _avg(latencies),
        "avg_stt_s": _avg(stt_times),
        "avg_llm_s": _avg(llm_times),
        "avg_duration_s": _avg(durations),
        "total_duration_s": round(sum(durations), 1) if durations else 0,
        "llm_calls": llm_calls,
        "prompt_tokens": sum(int(e.get("prompt_tokens", 0)) for e in events),
        "completion_tokens": sum(int(e.get("completion_tokens", 0)) for e in events),
        "chars_in": sum(int(e.get("chars_in", 0)) for e in events),
        "chars_out": sum(int(e.get("chars_out", 0)) for e in events),
    }


def _bucket_index(n: float, buckets: list) -> int:
    for i, (_, lo, hi) in enumerate(buckets):
        if n >= lo and (hi is None or n < hi):
            return i
    return len(buckets) - 1


def _histogram(events: list[dict], field: str, buckets: list) -> list[dict]:
    counts = [0] * len(buckets)
    for e in events:
        val = e.get(field)
        if val is None:
            continue
        counts[_bucket_index(float(val), buckets)] += 1
    return [{"label": buckets[i][0], "count": counts[i]} for i in range(len(buckets))]


def _aggregate(events: list[dict]) -> dict:
    hourly = [0] * 24
    users: dict[int, int] = {}
    largest: list[dict] = []

    for e in events:
        ts = e.get("ts", 0)
        hourly[time.localtime(ts).tm_hour] += 1
        uid = e.get("user_id")
        if uid is not None:
            users[uid] = users.get(uid, 0) + 1
        if e.get("type") != "error":
            largest.append(
                {
                    "ts": ts,
                    "chars": int(e.get("chars_in", 0)),
                    "duration_s": e.get("duration_s"),
                    "latency_s": e.get("latency_s"),
                    "provider": e.get("provider", ""),
                    "preview": e.get("preview", ""),
                }
            )

    largest.sort(key=lambda x: x["chars"], reverse=True)
    top_users = sorted(users.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "hourly": hourly,
        "top_users": [{"user_id": u, "count": n} for u, n in top_users],
        "user_count": len(users),
        "duration_buckets": _histogram(events, "duration_s", DURATION_BUCKETS),
        "latency_buckets": _histogram(events, "latency_s", LATENCY_BUCKETS),
        "largest": largest[:10],
    }


def build_stats(
    settings: dict | None = None,
    custom_start: float | None = None,
    custom_end: float | None = None,
) -> dict:
    events = read_events()

    t = summarize(events)

    range_defs = {
        "1d": _local_midnight(0),
        "7d": _local_midnight(6),
        "30d": _local_midnight(29),
        "all": 0.0,
    }
    ranges = {}
    for rkey, cut in range_defs.items():
        evts = [e for e in events if e.get("ts", 0) >= cut]
        ranges[rkey] = {
            **summarize(evts),
            **_aggregate(evts),
            "since": time.strftime("%Y-%m-%d", time.localtime(cut)) if cut else None,
        }

    if custom_start is not None and custom_end is not None:
        evts = [e for e in events if custom_start <= e.get("ts", 0) < custom_end]
        ranges["custom"] = {
            **summarize(evts),
            **_aggregate(evts),
            "since": time.strftime("%Y-%m-%d", time.localtime(custom_start)),
            "until": time.strftime(
                "%Y-%m-%d", time.localtime(max(0.0, custom_end - 1))
            ),
        }

    timeline: dict[str, dict] = {}
    for e in events:
        etype = e.get("type", "")
        ts = e.get("ts", 0)
        day = _day_key(ts)
        slot = timeline.setdefault(day, {"date": day, "voice": 0, "error": 0})
        if etype in slot:
            slot[etype] += 1

    days = sorted(timeline.keys())
    filled: list[dict] = []
    if days:
        first = time.strptime(days[0], "%Y-%m-%d")
        last = time.strptime(days[-1], "%Y-%m-%d")
        cur_ts = time.mktime(first)
        end = time.mktime(last)
        limit = cur_ts - 400 * 86400
        while cur_ts <= end and cur_ts >= limit:
            key = time.strftime("%Y-%m-%d", time.localtime(cur_ts))
            filled.append(timeline.get(key, {"date": key, "voice": 0, "error": 0}))
            cur_ts += 86400

    recent = [
        {
            "ts": e.get("ts", 0),
            "type": e.get("type", ""),
            "provider": e.get("provider", ""),
            "stt_model": e.get("stt_model", ""),
            "duration_s": e.get("duration_s"),
            "latency_s": e.get("latency_s"),
            "stt_s": e.get("stt_s"),
            "llm_s": e.get("llm_s"),
            "chars_in": e.get("chars_in", 0),
            "chars_out": e.get("chars_out", 0),
            "prompt_tokens": e.get("prompt_tokens", 0),
            "completion_tokens": e.get("completion_tokens", 0),
            "llm_used": bool(e.get("llm_used")),
            "user_id": e.get("user_id"),
            "preview": e.get("preview", ""),
            "error": e.get("error"),
        }
        for e in reversed(events[-25:])
    ]

    session_events = [e for e in events if e.get("ts", 0) >= SESSION_START]

    session_slots: dict[int, dict] = {}
    for e in session_events:
        h = int(e.get("ts", 0) // 3600) * 3600
        slot = session_slots.setdefault(h, {"voice": 0, "error": 0})
        etype = e.get("type", "")
        if etype in slot:
            slot[etype] += 1

    now_hour = int(time.time() // 3600) * 3600
    start_hour = int(SESSION_START // 3600) * 3600
    min_hour = now_hour - 167 * 3600
    session_timeline = []
    h = start_hour
    while h <= now_hour:
        counts = session_slots.get(h)
        if h >= min_hour:
            session_timeline.append({"ts": h, **(counts or {"voice": 0, "error": 0})})
        h += 3600

    return {
        "settings": settings or {},
        "totals": {
            **t,
            "first_activity": days[0] if days else None,
        },
        "session": {
            **summarize(session_events),
            **_aggregate(session_events),
            "started_at": SESSION_START,
        },
        "session_timeline": session_timeline,
        "ranges": ranges,
        "timeline": filled,
        "recent": recent,
    }
