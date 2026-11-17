import audio_limits


def test_default_is_eight_mb(monkeypatch):
    monkeypatch.delenv("MAX_AUDIO_MB", raising=False)
    assert audio_limits.max_audio_mb() == 8
    assert audio_limits.max_audio_bytes() == 8 * 1024 * 1024


def test_clamps_to_supported_range(monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_MB", "0")
    assert audio_limits.max_audio_mb() == 1
    monkeypatch.setenv("MAX_AUDIO_MB", "99")
    assert audio_limits.max_audio_mb() == 20


def test_invalid_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_MB", "not-a-number")
    assert audio_limits.max_audio_mb() == 8
