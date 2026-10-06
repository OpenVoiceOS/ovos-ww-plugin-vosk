import gc
import shutil
import threading
import time
import wave
import weakref
from pathlib import Path

import pytest

pytest.importorskip("vosk")

import ovos_ww_plugin_vosk as plugin
from ovos_ww_plugin_vosk import ModelContainer, VoskWakeWordPlugin

FIXTURES = Path(__file__).parent / "fixtures"
CHUNK_SIZE = 3200


@pytest.fixture(scope="module")
def model_path():
    return ModelContainer.download_language("en")


@pytest.fixture
def built(monkeypatch):
    """Records every KaldiModel the plugin constructs."""
    plugin._MODELS.clear()
    gc.collect()
    models = []
    real = plugin.KaldiModel

    def spy(path):
        model = real(path)
        models.append(weakref.ref(model))
        return model

    monkeypatch.setattr(plugin, "KaldiModel", spy)
    return models


def _config(model_path, sample):
    return {"model": model_path, "samples": [sample], "rule": "equals",
            "threshold": 0.9, "time_between_checks": 1.0}


def _detect(engine, wav_name):
    with wave.open(str(FIXTURES / wav_name)) as wf:
        pcm = wf.readframes(wf.getnframes())
    engine._counter = 0.0
    engine.buffer.clear()
    for i in range(0, len(pcm), CHUNK_SIZE):
        engine.update(pcm[i:i + CHUNK_SIZE])
    for _ in range(30):
        if engine.found_wake_word():
            return True
    return False


def test_same_model_path_loads_one_model(model_path, built):
    first = VoskWakeWordPlugin("hey computer", _config(model_path, "hey computer"))
    second = VoskWakeWordPlugin("wake up", _config(model_path, "wake up"))
    assert len(built) == 1
    assert first.model.engine is not second.model.engine


def test_same_language_shares_model(built):
    first = VoskWakeWordPlugin("hey computer", {"lang": "en-us", "samples": ["hey computer"]})
    second = VoskWakeWordPlugin("wake up", {"lang": "en-us", "samples": ["wake up"]})
    assert len(built) == 1


def test_different_model_paths_do_not_share(model_path, built, tmp_path):
    copy = str(tmp_path / "copy")
    shutil.copytree(model_path, copy)
    first = VoskWakeWordPlugin("hey computer", _config(model_path, "hey computer"))
    second = VoskWakeWordPlugin("hey computer", _config(copy, "hey computer"))
    assert len(built) == 2
    assert built[0]() is not built[1]()


def test_model_lives_until_last_instance_is_released(model_path, built):
    first = VoskWakeWordPlugin("hey computer", _config(model_path, "hey computer"))
    second = VoskWakeWordPlugin("wake up", _config(model_path, "wake up"))
    model = built[0]
    del first
    gc.collect()
    assert model() is not None
    del second
    gc.collect()
    assert model() is None


def test_instances_with_different_samples_detect_only_their_phrase(model_path):
    computer = VoskWakeWordPlugin("hey computer", _config(model_path, "hey computer"))
    wakeup = VoskWakeWordPlugin("wake up", _config(model_path, "wake up"))
    assert _detect(computer, "hey_computer.wav")
    assert _detect(wakeup, "wake_up.wav")
    assert not _detect(computer, "wake_up.wav")
    assert not _detect(wakeup, "hey_computer.wav")


def test_concurrent_downloads_of_one_url_fetch_once(monkeypatch, tmp_path):
    calls = []

    def slow_download(url, folder, skill_folder_name):
        calls.append(url)
        time.sleep(0.3)
        (Path(folder) / skill_folder_name).mkdir(parents=True)

    monkeypatch.setattr(plugin, "xdg_data_home", lambda: str(tmp_path))
    monkeypatch.setattr(plugin, "download_extract_zip", slow_download)
    url = "https://example.invalid/vosk-model-race.zip"
    threads = [threading.Thread(target=ModelContainer.download_model, args=(url,))
               for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls == [url]
