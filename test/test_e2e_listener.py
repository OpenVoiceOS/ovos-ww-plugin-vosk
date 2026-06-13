"""E2E listener test for ovos-ww-plugin-vosk using ovoscope.

Tests drive the VoskWakeWordPlugin directly via update()/found_wake_word()
and verify that:
 - Positive: wakeword audio ("hey mycroft") triggers detection.
 - Negative: unrelated command audio does not trigger detection.
"""
import wave
from pathlib import Path

import pytest

pytest.importorskip("ovoscope")
pytest.importorskip("vosk")

from ovos_ww_plugin_vosk import VoskWakeWordPlugin

FIXTURES = Path(__file__).parent / "fixtures"
WAKEWORD_WAV = FIXTURES / "wakeword.wav"
COMMAND_WAV = FIXTURES / "command.wav"

# Wakeword configured — must match the TTS fixture audio
WAKEWORD = "hey mycroft"
# Use FUZZY rule so minor ASR differences still match
CONFIG = {
    "lang": "en-us",
    "samples": [WAKEWORD],
    "rule": "fuzzy",
    "threshold": 0.5,
    "time_between_checks": 1.0,
    "debug": True,
}

CHUNK_SIZE = 3200  # 0.1 s @ 16 kHz, 16-bit mono


def _read_chunks(wav_path: Path, chunk_size: int = CHUNK_SIZE):
    """Return list of raw PCM byte chunks from a WAV file."""
    with wave.open(str(wav_path)) as wf:
        assert wf.getframerate() == 16000, "fixture must be 16 kHz"
        assert wf.getnchannels() == 1, "fixture must be mono"
        assert wf.getsampwidth() == 2, "fixture must be 16-bit"
        pcm = wf.readframes(wf.getnframes())
    return [pcm[i: i + chunk_size] for i in range(0, len(pcm), chunk_size)]


def _drive(engine: VoskWakeWordPlugin, chunks, max_calls: int = 30) -> bool:
    """Feed chunks and poll found_wake_word(); return True if detected."""
    # Reset internal counter so we process from scratch
    engine._counter = 0.0
    engine.buffer.clear()

    detected = False
    # Feed all audio first
    for chunk in chunks:
        engine.update(chunk)

    # Then poll — each call advances _counter by SEC_BETWEEN_WW_CHECKS (0.2)
    # Audio is processed when _counter >= time_between_checks (1.0), i.e. 5 calls
    for _ in range(max_calls):
        if engine.found_wake_word():
            detected = True
            break
    return detected


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """Instantiate the plugin once; model download cached in XDG_DATA_HOME."""
    eng = VoskWakeWordPlugin(hotword=WAKEWORD, config=CONFIG)
    yield eng


def test_positive_wakeword_detection(engine):
    """Wakeword audio ('hey mycroft') must be detected."""
    chunks = _read_chunks(WAKEWORD_WAV)
    detected = _drive(engine, chunks)
    assert detected, (
        "VoskWakeWordPlugin failed to detect 'hey mycroft' in TTS wakeword audio. "
        "If the Vosk small-en model consistently misrecognises TTS audio, "
        "the fixture or threshold may need tuning."
    )


def test_negative_no_detection_on_command(engine):
    """Non-wakeword audio must not trigger detection."""
    chunks = _read_chunks(COMMAND_WAV)
    detected = _drive(engine, chunks)
    assert not detected, (
        "VoskWakeWordPlugin falsely detected a wakeword in command.wav"
    )


def test_engine_loads_and_processes_without_error(engine):
    """Sanity check: engine must accept audio without raising."""
    silent = b"\x00" * CHUNK_SIZE
    engine.update(silent)
    # found_wake_word must not raise even on silence
    _ = engine.found_wake_word()
