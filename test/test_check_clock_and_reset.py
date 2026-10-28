"""The check clock follows the audio received, and reset() clears all state.

The listener feeds the plugin one chunk per loop: update(chunk) then
found_wake_word(). A check must run after `time_between_checks` seconds of
audio, whatever the chunk size, and reset() must leave no audio, check
progress or recognizer state behind.
"""
import wave
from pathlib import Path

import pytest

from ovos_ww_plugin_vosk import VoskWakeWordPlugin, VoskMultiWakeWordPlugin

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CONFIG = {
    "lang": "en-us",
    "samples": ["hey computer"],
    "rule": "fuzzy",
    "time_between_checks": 1.0,
}


def _read_pcm(name: str) -> bytes:
    with wave.open(str(FIXTURES / name)) as wf:
        assert wf.getframerate() == SAMPLE_RATE
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == BYTES_PER_SAMPLE
        return wf.readframes(wf.getnframes())


def _silence(seconds: float) -> bytes:
    return b"\x00" * int(seconds * SAMPLE_RATE * BYTES_PER_SAMPLE)


CHUNK_SIZES = [1000, 1280, 1600, 2048, 4096]
HEY_COMPUTER = _silence(0.1) + _read_pcm("hey_computer.wav") + _silence(2.0)
COMMAND = _read_pcm("command.wav")


def _stream(engine, pcm: bytes, chunk_samples: int) -> bool:
    """Run the listener loop over pcm; True once a wake word is found."""
    step = chunk_samples * BYTES_PER_SAMPLE
    for i in range(0, len(pcm), step):
        engine.update(pcm[i:i + step])
        if engine.found_wake_word():
            return True
    return False


@pytest.fixture(scope="module")
def engine():
    return VoskWakeWordPlugin("hey computer", CONFIG)


@pytest.fixture(autouse=True)
def _fresh(engine):
    engine.buffer.clear()
    engine._counter = 0
    yield


@pytest.mark.parametrize("chunk_samples", CHUNK_SIZES)
def test_detection_does_not_depend_on_chunk_size(engine, chunk_samples):
    assert _stream(engine, HEY_COMPUTER, chunk_samples)


@pytest.mark.parametrize("chunk_samples", CHUNK_SIZES)
def test_check_runs_after_time_between_checks_of_audio(engine, chunk_samples):
    fed = []
    checks = []
    process_audio = engine.model.process_audio
    engine.model.process_audio = \
        lambda audio, lang=None: (checks.append(sum(fed)),
                                  process_audio(audio, lang))[1]
    update = engine.update
    engine.update = lambda chunk: (fed.append(len(chunk)), update(chunk))[1]
    try:
        _stream(engine, _silence(6.0), chunk_samples)
    finally:
        engine.model.process_audio = process_audio
        engine.update = update
    # a check fires on the first chunk that holds 1.0 s of audio, counted in
    # whole bytes so that no chunk size drifts
    chunk_bytes = chunk_samples * BYTES_PER_SAMPLE
    second = SAMPLE_RATE * BYTES_PER_SAMPLE
    per_check = -(-second // chunk_bytes) * chunk_bytes
    assert len(checks) >= 3
    assert checks == [per_check * (i + 1) for i in range(len(checks))]


def test_window_holds_the_last_window_seconds(engine):
    seen = []
    process_audio = engine.model.process_audio
    engine.model.process_audio = \
        lambda audio, lang=None: (seen.append(len(audio)),
                                  process_audio(audio, lang))[1]
    try:
        _stream(engine, _silence(5.0), 2048)
    finally:
        engine.model.process_audio = process_audio
    assert max(seen) == 2 * SAMPLE_RATE * BYTES_PER_SAMPLE


@pytest.mark.parametrize("lead_step", range(16))
def test_detection_does_not_depend_on_where_the_phrase_falls(engine, lead_step):
    # 16 lead positions across one 1.0 s check interval
    pcm = _silence(lead_step / 16) + _read_pcm("hey_computer.wav") + _silence(2.5)
    assert _stream(engine, pcm, 2048)


def test_one_utterance_gives_one_detection(engine):
    pcm = _silence(0.3) + _read_pcm("hey_computer.wav") + _silence(4.0)
    step = 2048 * BYTES_PER_SAMPLE
    detections = 0
    for i in range(0, len(pcm), step):
        engine.update(pcm[i:i + step])
        detections += engine.found_wake_word()
    assert detections == 1


def test_reset_clears_buffered_audio_and_check_progress(engine):
    engine.update(COMMAND[:16000])
    assert len(engine.buffer) > 0 and engine._counter > 0
    engine.reset()
    assert len(engine.buffer) == 0
    assert engine._counter == 0


def test_clip_after_leftover_audio_detects_like_alone(engine):
    assert _stream(engine, HEY_COMPUTER, 2048)
    engine.reset()
    # leftover from an earlier utterance that no check consumed
    engine.update(COMMAND[:12800])
    engine.reset()
    assert _stream(engine, HEY_COMPUTER, 2048)


def test_reset_clears_recognizer_state(engine):
    engine.reset()
    # half a phrase fed to Kaldi without a final result
    engine.model.process_audio(_read_pcm("hey_computer.wav")[:20000], "en")
    engine.reset()
    assert engine.model.get_final_transcription("en") == ""
    assert _stream(engine, HEY_COMPUTER, 2048)


def test_multi_plugin_clock_follows_audio_and_reset_clears(monkeypatch):
    import ovos_ww_plugin_vosk
    monkeypatch.setattr(ovos_ww_plugin_vosk, "get_mycroft_bus", lambda: None)
    multi = VoskMultiWakeWordPlugin("hey computer", {
        "lang": "en-us",
        "keywords": {"hey_computer": {"samples": ["hey computer"],
                                      "rule": "fuzzy"}}})
    assert _stream(multi, HEY_COMPUTER, 2048)
    multi.update(COMMAND[:16000])
    multi.model.process_audio(_read_pcm("hey_computer.wav")[:20000], "en")
    multi.reset()
    assert len(multi.buffer) == 0
    assert multi._counter == 0
    assert multi.model.get_final_transcription("en") == ""
    assert _stream(multi, HEY_COMPUTER, 2048)


def test_multi_plugin_detects_a_later_keyword(monkeypatch):
    import ovos_ww_plugin_vosk
    monkeypatch.setattr(ovos_ww_plugin_vosk, "get_mycroft_bus", lambda: None)
    multi = VoskMultiWakeWordPlugin("hey computer", {
        "lang": "en-us",
        "keywords": {"hey_robot": {"samples": ["hey robot"], "rule": "fuzzy"},
                     "hey_computer": {"samples": ["hey computer"],
                                      "rule": "fuzzy"}}})
    assert _stream(multi, HEY_COMPUTER, 2048)


def _multi(monkeypatch):
    import ovos_ww_plugin_vosk
    monkeypatch.setattr(ovos_ww_plugin_vosk, "get_mycroft_bus", lambda: None)
    return VoskMultiWakeWordPlugin("hey computer", {
        "lang": "en-us",
        "keywords": {"hey_robot": {"samples": ["hey robot"], "rule": "fuzzy"},
                     "hey_computer": {"samples": ["hey computer"],
                                      "rule": "fuzzy"},
                     "hey_mycroft": {"samples": ["hey mycroft"],
                                     "rule": "fuzzy"}}})


def test_multi_plugin_one_utterance_gives_one_detection(monkeypatch):
    multi = _multi(monkeypatch)
    pcm = _silence(0.3) + _read_pcm("hey_computer.wav") + _silence(4.0)
    step = 2048 * BYTES_PER_SAMPLE
    detections = 0
    for i in range(0, len(pcm), step):
        multi.update(pcm[i:i + step])
        detections += multi.found_wake_word()
    assert detections == 1


def test_multi_plugin_decodes_the_window_once_per_language(monkeypatch):
    multi = _multi(monkeypatch)
    decoded = []
    process_audio = multi.model.process_audio
    multi.model.process_audio = \
        lambda audio, lang=None: (decoded.append(lang),
                                  process_audio(audio, lang))[1]
    _stream(multi, _silence(3.0), 2048)
    assert len(decoded) == 2  # checks at 1.024 s and 2.048 s, three keywords


def test_window_smaller_than_check_interval_is_raised_to_it():
    plugin = VoskWakeWordPlugin("hey computer", {
        **CONFIG, "window_seconds": 0.5, "time_between_checks": 1.0})
    assert plugin.window_seconds == 1.0
    assert plugin._window_bytes == SAMPLE_RATE * BYTES_PER_SAMPLE


def test_window_is_a_whole_number_of_samples():
    plugin = VoskWakeWordPlugin("hey computer", {
        **CONFIG, "window_seconds": 2.00003125})
    assert plugin._window_bytes % BYTES_PER_SAMPLE == 0


def test_default_window_is_raised_silently(caplog):
    with caplog.at_level("WARNING"):
        plugin = VoskWakeWordPlugin("hey computer", {
            **CONFIG, "time_between_checks": 2.5})
    assert plugin.window_seconds == 2.5
    assert "window_seconds" not in caplog.text


def test_configured_window_raised_with_a_warning(monkeypatch):
    import ovos_ww_plugin_vosk
    warnings = []
    monkeypatch.setattr(ovos_ww_plugin_vosk.LOG, "warning", warnings.append)
    VoskWakeWordPlugin("hey computer", {
        **CONFIG, "window_seconds": 0.5, "time_between_checks": 1.0})
    assert any("window_seconds" in w for w in warnings)


@pytest.mark.parametrize("checks", [0, -1, 0.1])
def test_time_between_checks_is_floored(monkeypatch, checks):
    import ovos_ww_plugin_vosk
    warnings = []
    monkeypatch.setattr(ovos_ww_plugin_vosk.LOG, "warning", warnings.append)
    plugin = VoskWakeWordPlugin("hey computer", {
        **CONFIG, "time_between_checks": checks, "window_seconds": 0})
    assert plugin.time_between_checks == 0.2
    assert any(w.startswith(f"time_between_checks ({checks}) is below") for w in warnings)
    _stream(plugin, _silence(10.0), 2048)
    assert len(plugin.buffer) <= int(0.2 * SAMPLE_RATE) * BYTES_PER_SAMPLE
