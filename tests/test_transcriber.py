import transcriber


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeInfo:
    duration = 5.0


class FakeModel:
    def transcribe(self, path, **kwargs):
        assert path == "note.m4a"
        return [FakeSegment(" привет "), FakeSegment(" мир ")], FakeInfo()


def test_idle_unload_seconds_defaults_and_parsing(monkeypatch):
    monkeypatch.delenv("WHISPER_IDLE_UNLOAD_SECONDS", raising=False)
    assert transcriber.idle_unload_seconds() == 600

    monkeypatch.setenv("WHISPER_IDLE_UNLOAD_SECONDS", "120")
    assert transcriber.idle_unload_seconds() == 120

    monkeypatch.setenv("WHISPER_IDLE_UNLOAD_SECONDS", "0")
    assert transcriber.idle_unload_seconds() == 0

    monkeypatch.setenv("WHISPER_IDLE_UNLOAD_SECONDS", "abc")
    assert transcriber.idle_unload_seconds() == 600

    monkeypatch.setenv("WHISPER_IDLE_UNLOAD_SECONDS", "-5")
    assert transcriber.idle_unload_seconds() == 0


def test_unload_model_clears_an_idle_model(monkeypatch):
    monkeypatch.setattr(transcriber, "_MODEL", object())
    monkeypatch.setattr(transcriber, "_ACTIVE", 0)

    assert transcriber.unload_model() is True
    assert transcriber._MODEL is None


def test_unload_model_keeps_a_busy_model(monkeypatch):
    model = object()
    monkeypatch.setattr(transcriber, "_MODEL", model)
    monkeypatch.setattr(transcriber, "_ACTIVE", 1)

    assert transcriber.unload_model() is False
    assert transcriber._MODEL is model


def test_schedule_unload_is_disabled_by_zero(monkeypatch):
    monkeypatch.setenv("WHISPER_IDLE_UNLOAD_SECONDS", "0")
    monkeypatch.setattr(transcriber, "_UNLOAD_TIMER", None)

    transcriber._schedule_unload()

    assert transcriber._UNLOAD_TIMER is None


def test_transcribe_returns_text_and_schedules_unload(monkeypatch):
    calls = []
    monkeypatch.setattr(transcriber, "_MODEL", FakeModel())
    monkeypatch.setattr(transcriber, "_ACTIVE", 0)
    monkeypatch.setattr(transcriber, "_schedule_unload", lambda: calls.append(True))

    text, duration = transcriber.transcribe("note.m4a")

    assert text == "привет мир"
    assert duration == 5
    assert calls
    assert transcriber._ACTIVE == 0
