"""The engine checks for the wake word once per ``time_between_checks`` seconds of
audio, whatever the chunk size of the microphone, and finds a wake word that
crosses a check boundary."""
import wave
from pathlib import Path

import pytest

from ovos_ww_plugin_vosk import VoskMultiWakeWordPlugin, VoskWakeWordPlugin

WAKEWORD_WAV = Path(__file__).parent / "fixtures" / "wakeword.wav"
CONFIG = {"lang": "en-us", "samples": ["hey mycroft"], "rule": "fuzzy", "threshold": 0.5}


@pytest.fixture(scope="module")
def engine():
    return VoskWakeWordPlugin("hey mycroft", CONFIG)


def detected(engine, audio: bytes, chunk_bytes: int) -> bool:
    engine.buffer.clear()
    engine._counter = 0
    found = False
    for i in range(0, len(audio) - chunk_bytes + 1, chunk_bytes):
        engine.update(audio[i:i + chunk_bytes])
        found = engine.found_wake_word() or found
    return found


@pytest.fixture(scope="module")
def pcm():
    with wave.open(str(WAKEWORD_WAV)) as wf:
        return wf.readframes(wf.getnframes())


@pytest.mark.parametrize("chunk_bytes", [2048, 4096, 6400])
def test_listener_loop_detects_with_any_chunk_size(engine, pcm, chunk_bytes):
    silence = bytes(32000)
    assert detected(engine, silence + pcm + silence * 2, chunk_bytes)


@pytest.mark.parametrize("lead_ms", range(0, 1000, 128))
def test_wake_word_across_a_check_boundary(engine, pcm, lead_ms):
    lead = bytes(32 * lead_ms)
    assert detected(engine, lead + pcm + bytes(64000), 4096)


def test_one_wake_word_is_detected_once(engine, pcm):
    """A hit clears the buffer, so the next check does not hear it again."""
    engine.buffer.clear()
    engine._counter = 0
    audio = bytes(32000) + pcm + bytes(96000)
    hits = 0
    for i in range(0, len(audio) - 4095, 4096):
        engine.update(audio[i:i + 4096])
        hits += engine.found_wake_word()
    assert hits == 1


MULTI_CONFIG = {"keywords": {"hey_mycroft": {
    "lang": "en-us", "samples": ["hey"], "rule": "starts", "threshold": 0.75}}}
COMMAND_WAV = Path(__file__).parent / "fixtures" / "command.wav"
PORTUGUESE_WAV = Path(__file__).parent / "fixtures" / "portuguese.wav"


FLOYD_CONFIG = {"keywords": {"hey_floyd": {
    "lang": "en-us", "samples": ["hey floyd"], "rule": "equals"}}}


def multi_hits(audio: bytes, config: dict = MULTI_CONFIG) -> int:
    return plugin_hits(VoskMultiWakeWordPlugin("hey xxx", config), audio)


def plugin_hits(multi: VoskMultiWakeWordPlugin, audio: bytes) -> int:
    hits = 0
    for i in range(0, len(audio) - 4095, 4096):
        multi.update(audio[i:i + 4096])
        hits += multi.found_wake_word()
    return hits


def test_multi_plugin_detects_wake_word(pcm, monkeypatch):
    """The model lacks 'mycroft', so it hears 'hey [unk]'; the rule matches 'hey'."""
    monkeypatch.setattr("ovos_ww_plugin_vosk.get_mycroft_bus", lambda: None)
    assert multi_hits(bytes(32000) + pcm + bytes(96000)) == 1


def test_multi_plugin_ignores_speech_without_wake_word(monkeypatch):
    monkeypatch.setattr("ovos_ww_plugin_vosk.get_mycroft_bus", lambda: None)
    with wave.open(str(COMMAND_WAV)) as wf:
        command = wf.readframes(wf.getnframes())
    assert multi_hits(bytes(32000) + command + bytes(96000)) == 0


def test_multi_plugin_with_device_language_no_keyword_speaks(pcm, monkeypatch):
    """A pt-PT device with only en-us keywords builds and detects them."""
    monkeypatch.setattr("ovos_ww_plugin_vosk.get_mycroft_bus", lambda: None)
    monkeypatch.setattr("ovos_ww_plugin_vosk.Configuration", lambda: {"lang": "pt-PT"})
    multi = VoskMultiWakeWordPlugin("hey xxx", MULTI_CONFIG)
    assert multi.lang == "pt-PT"
    assert multi.langs == ["en-us"]
    assert multi.model.lang_samples == {"en": ["hey", "[unk]"]}
    assert multi_hits(bytes(32000) + pcm + bytes(96000)) == 1


def pcm_of(path: Path) -> bytes:
    with wave.open(str(path)) as wf:
        return wf.readframes(wf.getnframes())


@pytest.mark.parametrize("speech, config", [(COMMAND_WAV, MULTI_CONFIG), (PORTUGUESE_WAV, FLOYD_CONFIG)],
                         ids=["command", "portuguese"])
def test_multi_plugin_on_pt_device_ignores_speech_without_wake_word(speech, config, monkeypatch):
    """The keyword grammar keeps [unk], so speech that is not the keyword is not
    decoded as the keyword when the device language has no keyword."""
    monkeypatch.setattr("ovos_ww_plugin_vosk.get_mycroft_bus", lambda: None)
    monkeypatch.setattr("ovos_ww_plugin_vosk.Configuration", lambda: {"lang": "pt-PT"})
    assert multi_hits(bytes(32000) + pcm_of(speech) + bytes(96000), config) == 0


def test_reloaded_plugin_hears_its_own_keyword(pcm, monkeypatch):
    """A hotword reload builds a new plugin with a new keyword grammar. Each
    plugin decodes with its own grammar, whatever plugin loaded first."""
    monkeypatch.setattr("ovos_ww_plugin_vosk.get_mycroft_bus", lambda: None)
    audio = bytes(32000) + pcm + bytes(96000)
    old = VoskMultiWakeWordPlugin("old", {"keywords": {"computer": {"lang": "en-us", "samples": ["computer"]}}})
    new = VoskMultiWakeWordPlugin("new", MULTI_CONFIG)
    assert old.model.get_engine("en") is not new.model.get_engine("en")
    assert plugin_hits(old, audio) == 0
    assert plugin_hits(new, audio) == 1
