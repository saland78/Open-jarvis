"""Request-scoped, numeric-only Ollama terminal metrics; no extra inference."""
from contextlib import contextmanager
from contextvars import ContextVar

_active = ContextVar('andrea_native_metrics', default=None)
_DURATIONS = {
    'totalMs': 'total_duration', 'loadMs': 'load_duration',
    'promptEvalMs': 'prompt_eval_duration', 'evalMs': 'eval_duration',
}
_COUNTS = {
    'promptEvalCount': 'prompt_eval_count',
    'promptEvalCachedCount': 'prompt_eval_cached_count', 'evalCount': 'eval_count',
}


def integer(value):
    # Booleans, estimates, strings, negative and non-JSON-safe values are absent.
    return value if type(value) is int and 0 <= value <= 2**53-1 else None


def empty():
    return {'source': 'ollama_terminal_frame', 'durationUnit': 'ms',
            'terminalFrameReceived': False,
            **dict.fromkeys(_DURATIONS), **dict.fromkeys(_COUNTS),
            'evalTokensPerSecond': None}


@contextmanager
def bind(measurement):
    """Context propagates into the collector task and is reset on every exit."""
    measurement.record['ollamaNative'] = empty()
    token = _active.set(measurement)
    try:
        yield
    finally:
        _active.reset(token)


def capture(frame):
    measurement = _active.get()
    if measurement is None or not isinstance(frame, dict) or frame.get('done') is not True:
        return
    result = empty()
    result['terminalFrameReceived'] = True
    for destination, key in _DURATIONS.items():
        value = integer(frame.get(key))
        result[destination] = round(value/1_000_000, 3) if value is not None else None
    for destination, key in _COUNTS.items():
        result[destination] = integer(frame.get(key))
    count, duration = result['evalCount'], integer(frame.get('eval_duration'))
    if count is not None and duration is not None and duration > 0:
        rate = count * 1_000_000_000 / duration
        result['evalTokensPerSecond'] = round(rate, 3) if rate <= 2**53-1 else None
    # Never retain the raw terminal frame, content, model identity or timestamps.
    measurement.record['ollamaNative'] = result
